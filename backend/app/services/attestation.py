"""
Attestation service: T8 transition logic (EVALUATED → VERIFIED) with COMPETENCE precondition checks.

PLAN 2.8 (YET-70, YET-88, YET-89, YET-90): Implements AC-1 through AC-9, AC-S1 through AC-S5.
- Validates engagement exists, is EVALUATED, not already attested
- Checks 6 COMPETENCE preconditions (DOMAIN.md §3.11)
- Downgrades to PARTICIPATION if 1+ preconditions missing
- Creates Attestation + VerifiedExperience + SkillSignal + AuditEvent in single transaction
- Updates engagement.status=VERIFIED, version+1
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Attestation,
    Deliverable,
    Engagement,
    Institution,
    Organization,
    Skill,
    SkillSignal,
    TalentProfile,
    VerifiedExperience,
)
from app.models.outbox import Outbox
from app.services.authorization import (
    EngagementRelation,
    Principal,
    engagement_relation,
    get_scoped_or_404,
    scoped_engagements,
)
from app.services.audit import log_audit_event
from app.models.verified_experience import generate_public_token


# Exception classes
class EngagementNotFoundError(Exception):
    """Raised when engagement_id does not exist or is not accessible to principal."""

    pass


class IllegalTransitionError(Exception):
    """Raised when engagement is not in EVALUATED status."""

    pass


class TransitionForbiddenError(Exception):
    """Raised when principal is not authorized to attest (role/scope mismatch)."""

    pass


class SelfAttestationError(Exception):
    """Raised when attestor_user_id == talent_id."""

    pass


class AttestationAlreadyExistsError(Exception):
    """Raised when attestation for same engagement+attestor already exists (UNIQUE violation)."""

    pass


class VersionMismatchError(Exception):
    """Raised when request version does not match engagement.version (optimistic locking)."""

    pass


def attestation_role_allowed(rel: EngagementRelation, engagement: Engagement) -> bool:
    """
    Role rule for T8 (STATE_MACHINE.md): who may seal this engagement.

    institution_id NOT NULL -> a COORDINATOR of that institution only;
    institution_id NULL -> an ORG_ADMIN of the organization only.
    rel is masked for the subject, so the talent never qualifies.
    Shared by create_attestation() and the detail view's viewer.can_attest.
    """
    if engagement.institution_id is not None:
        return rel.is_coordinator
    return rel.is_org_admin


def _check_competence_preconditions(
    session: Session,
    engagement: Engagement,
    principal: Principal,
) -> tuple[str, list[str]]:
    """
    Check §3.11 COMPETENCE preconditions. Return (final_claim_type, downgrade_reasons).

    6 criteria (plan.md decision: criterion 3 simplified to just "has Deliverable", no skill_id check):
    1. Mutual confirmation (both sides evaluated) — implicit if engagement is EVALUATED (T7 ORG_TO_TALENT done)
    2. Duration ≥4 weeks — check started_on/ended_on difference
    3. At least 1 Deliverable exists (no skill_id requirement) — NO_DELIVERABLE if missing
    4. Principal authorized to call T8 (role/scope already verified in create_attestation()) AND org verification_level ≥T2
       → ATTESTOR_NOT_VERIFIED_SUPERVISOR if org not ≥T2
    5. Structural (attestor_user_id always required) — no code generated
    6. institution_id NULL → skip this criterion entirely (no code); institution_id NOT NULL AND attestor is not COORDINATOR
       → COORDINATOR_CONFIRMATION_MISSING if not met

    Args:
        session: Database session
        engagement: Engagement object (already fetched, status=EVALUATED)
        principal: Authorization context (already validated as COORDINATOR or ORG:SUPERVISOR)

    Returns:
        tuple (final_claim_type, downgrade_reasons):
          - final_claim_type: "COMPETENCE" or "PARTICIPATION" (downgraded if any criterion missing)
          - downgrade_reasons: list of codes (empty if all criteria met)
    """
    downgrade_reasons = []

    # Criterion 1: Mutual confirmation (implicit in EVALUATED status — EVALUATED requires both sides)
    # Status check already done by caller; this criterion essentially always met at this point
    # Code: ENGAGEMENT_NOT_MUTUALLY_CONFIRMED (reserved for completeness, unlikely to trigger)
    # (skipped in this implementation as it's redundant with status check)

    # Criterion 2: Duration ≥ 4 weeks
    if engagement.started_on and engagement.ended_on:
        duration_days = (engagement.ended_on - engagement.started_on).days
        if duration_days < 28:  # 4 weeks = 28 days
            downgrade_reasons.append("ENGAGEMENT_DURATION_BELOW_THRESHOLD")
    elif engagement.started_on is None or engagement.ended_on is None:
        # Missing dates — treat as criterion not met
        downgrade_reasons.append("ENGAGEMENT_DURATION_BELOW_THRESHOLD")

    # Criterion 3: At least 1 Deliverable (simplified: no skill_id requirement per plan.md decision)
    deliverable_count = session.query(Deliverable).filter_by(
        engagement_id=engagement.id
    ).count()
    if deliverable_count == 0:
        downgrade_reasons.append("NO_DELIVERABLE")

    # Criterion 4: Principal authorized to call T8 (already verified in create_attestation()) AND org ≥T2 verified
    # Fetch organization to check verification level
    org = session.execute(
        select(Organization).where(Organization.id == engagement.organization_id)
    ).scalar_one_or_none()
    org_verified = org is not None and org.verification_level in ("T2", "T3", "T4")

    if not org_verified:
        downgrade_reasons.append("ATTESTOR_NOT_VERIFIED_SUPERVISOR")

    # Criterion 5: Structural (attestor_user_id always provided from principal) — no code

    # Criterion 6: Coordinator confirmation
    # If institution_id is NULL, skip this criterion entirely (no downgrade reason)
    # If institution_id NOT NULL, attestor must be COORDINATOR of that institution
    if engagement.institution_id is not None:
        # Principal must be COORDINATOR of this institution
        is_coordinator = engagement.institution_id in principal.coordinator_institution_ids
        if not is_coordinator:
            downgrade_reasons.append("COORDINATOR_CONFIRMATION_MISSING")

    # Determine final claim type
    final_claim_type = "PARTICIPATION" if downgrade_reasons else "COMPETENCE"

    return final_claim_type, downgrade_reasons


def create_attestation(
    session: Session,
    principal: Principal,
    engagement_id: str,
    requested_claim_type: str,
    version: int,
    skill_id: str | None = None,
    statement: str | None = None,
) -> tuple[Attestation, VerifiedExperience]:
    """
    Create attestation for EVALUATED engagement, triggering T8 (EVALUATED → VERIFIED) transition.

    Single transaction: Attestation + VerifiedExperience + SkillSignal (if skill_id provided) + AuditEvent + Outbox + Engagement.status update.

    Args:
        session: Transactional database session
        principal: Authorization context (authenticated user)
        engagement_id: UUID of engagement (string format)
        requested_claim_type: Client's requested claim type (COMPETENCE/PARTICIPATION/CONTRIBUTION/CONDUCT)
        version: Current engagement.version (for optimistic locking)
        skill_id: Optional UUID of skill (string format) for SkillSignal creation. If provided and valid, SkillSignal is created with strength based on final_claim_type.

    Returns:
        tuple (Attestation, VerifiedExperience) — both created in single transaction

    Raises:
        EngagementNotFoundError: Engagement not found or out-of-scope (404)
        IllegalTransitionError: Engagement not EVALUATED (409 INVALID_STATE_TRANSITION)
        TransitionForbiddenError: Principal not authorized (403 for TALENT, 404 for scope)
        SelfAttestationError: Attestor == talent (409 SELF_ATTESTATION_FORBIDDEN)
        AttestationAlreadyExistsError: Already attested (409 ATTESTATION_ALREADY_EXISTS)
        VersionMismatchError: Version mismatch (409 CONFLICT)
    """
    # Parse engagement_id
    try:
        engagement_uuid = uuid.UUID(engagement_id)
    except ValueError:
        raise EngagementNotFoundError(f"Invalid engagement_id format: {engagement_id}")

    # Fetch engagement scoped to principal (404 for out-of-scope)
    engagement = get_scoped_or_404(
        scoped_engagements(session, principal).where(Engagement.id == engagement_uuid),
        session
    )
    if engagement is None:
        raise EngagementNotFoundError(f"Engagement {engagement_id} not found or not accessible")

    # Compute engagement relation (AC-S1: masking rule for self-dealing prevention)
    rel = engagement_relation(principal, engagement)

    # AC-4: TALENT forbidden to attest (S6 exception: return 403, not 404)
    if rel.is_subject:
        # If talent has no org-side membership, they cannot attest in any scenario
        if not rel.has_org_side_link:
            raise TransitionForbiddenError("Talent cannot submit attestations")
        # If talent DOES have org-side membership (coordinator or org admin), they still cannot
        # attest their own engagement (self-attestation prevention)
        else:
            raise SelfAttestationError("Cannot attest own engagement")

    # Role check per STATE_MACHINE.md T8 (see attestation_role_allowed). scoped_engagements()
    # only enforces tenant isolation (right org/institution); this enforces role suitability
    # within that tenant. Out-of-role principals get 404 (S2 tenant-isolation style — they ARE
    # in scope via scoped_engagements but not authorized for THIS action; not TALENT, so not
    # the S6 403 case).
    if not attestation_role_allowed(rel, engagement):
        raise EngagementNotFoundError(
            f"Engagement {engagement_id} not accessible for attestation (role not authorized)"
        )

    # AC-3: Engagement must be EVALUATED
    if engagement.status != "EVALUATED":
        raise IllegalTransitionError(
            f"Engagement must be EVALUATED for attestation, got {engagement.status}"
        )

    # AC-6: Version check (optimistic locking)
    if engagement.version != version:
        raise VersionMismatchError(
            f"Version mismatch: expected {engagement.version}, got {version}"
        )

    # AC-S3: Self-attestation check (service-layer first defense)
    # talent_id comes from Engagement (not from request)
    talent_profile = session.query(TalentProfile).filter_by(
        id=engagement.talent_id
    ).first()
    if talent_profile and talent_profile.user_id == principal.user_id:
        raise SelfAttestationError("Cannot attest own engagement")

    # Check COMPETENCE preconditions and determine final claim_type
    final_claim_type, downgrade_reasons = _check_competence_preconditions(
        session, engagement, principal
    )

    # Parse skill_id if provided (must be valid UUID and exist in skills table)
    skill_id_uuid = None
    if skill_id:
        try:
            skill_id_uuid = uuid.UUID(skill_id)
            # Verify skill exists in database
            skill_exists = session.query(Skill).filter_by(id=skill_id_uuid).first() is not None
            if not skill_exists:
                # Invalid skill_id — silently treat as None (no SkillSignal will be created)
                skill_id_uuid = None
        except ValueError:
            # Invalid UUID format — silently treat as None
            skill_id_uuid = None

    # Create Attestation record
    # AC-S1: attestor_user_id from principal, not from request
    now = datetime.now(timezone.utc)
    attestation = Attestation(
        engagement_id=engagement.id,
        talent_id=engagement.talent_id,  # Denormalized for CHECK constraint
        subject_type="ENGAGEMENT",  # Only ENGAGEMENT supported in this task
        subject_id=engagement.id,
        claim_type=final_claim_type,
        requested_claim_type=requested_claim_type,
        attestor_user_id=principal.user_id,
        attestor_org_id=engagement.organization_id,
        skill_id=skill_id_uuid,
        statement=statement.strip() if statement and statement.strip() else None,
        downgrade_reasons=downgrade_reasons if downgrade_reasons else [],
        created_at=now,
    )

    # Try to add attestation; catch UNIQUE constraint violation
    try:
        session.add(attestation)
        session.flush()  # Force constraint check
    except IntegrityError as e:
        session.rollback()
        # Check if it's self-attestation (CHECK constraint) or duplicate (UNIQUE)
        if "ck_attestations_no_self_attestation" in str(e.orig):
            raise SelfAttestationError("Self-attestation forbidden")
        elif "uq_attestations_engagement_attestor_subject" in str(e.orig):
            raise AttestationAlreadyExistsError(
                "Attestation already exists for this engagement+attestor+subject"
            )
        else:
            raise

    # Fetch organization and institution for snapshot
    org = session.execute(
        select(Organization).where(Organization.id == engagement.organization_id)
    ).scalar_one_or_none()
    org_name = org.name if org else ""

    inst = None
    inst_name = None
    if engagement.institution_id:
        inst = session.execute(
            select(Institution).where(Institution.id == engagement.institution_id)
        ).scalar_one_or_none()
        inst_name = inst.name if inst else None

    # Create VerifiedExperience snapshot
    # AC-1 (IS-01): Generate public_token for public verification link
    verified_exp = VerifiedExperience(
        talent_id=engagement.talent_id,
        engagement_id=engagement.id,
        organization_name_snapshot=org_name,
        role_snapshot=engagement.title,
        started_on_snapshot=engagement.started_on,
        ended_on_snapshot=engagement.ended_on,
        institution_name_snapshot=inst_name,
        claim_type=final_claim_type,
        visibility="PRIVATE",  # Default visibility (DOMAIN.md D6: mutable in future)
        public_token=generate_public_token(),  # AC-1: Generate token for potential public access
        created_at=now,
    )
    session.add(verified_exp)
    session.flush()

    # Create SkillSignal if skill_id is provided and valid (ATDD AC-1/AC-2)
    # Strength mapping: COMPETENCE → STRONG, PARTICIPATION → WEAK
    if skill_id_uuid is not None:
        signal_strength = "STRONG" if final_claim_type == "COMPETENCE" else "WEAK"
        skill_signal = SkillSignal(
            talent_id=engagement.talent_id,
            skill_id=skill_id_uuid,
            source_type="ATTESTATION",
            source_id=attestation.id,
            strength=signal_strength,
            attested_by_org_id=engagement.organization_id,
            occurred_at=now,
        )
        session.add(skill_signal)

    # Update Engagement.status → VERIFIED, version+1 (optimistic locking)
    updated_rows = session.execute(
        update(Engagement)
        .where(Engagement.id == engagement.id)
        .where(Engagement.version == version)
        .where(Engagement.status == "EVALUATED")
        .values(status="VERIFIED", version=version + 1)
    )
    if updated_rows.rowcount == 0:
        # This shouldn't happen (we already checked version and status), but paranoia
        session.rollback()
        raise VersionMismatchError(
            "Concurrent update detected; engagement version or status changed"
        )

    # Log audit event
    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=None,  # Not available in this context (set by middleware if needed)
        action="ATTESTATION_CREATED",
        subject_type="ATTESTATION",
        subject_id=attestation.id,
        result="SUCCESS",
        metadata={
            "engagement_id": str(engagement.id),
            "talent_id": str(engagement.talent_id),
            "claim_type": final_claim_type,
            "downgrade_reasons": downgrade_reasons,
        },
    )

    # Enqueue notification to outbox (transaction-safe)
    outbox_entry = Outbox(
        topic="attestation.created",
        payload={
            "attestation_id": str(attestation.id),
            "engagement_id": str(engagement.id),
            "talent_id": str(engagement.talent_id),
            "claim_type": final_claim_type,
            "downgrade_reasons": downgrade_reasons,
        },
    )
    session.add(outbox_entry)

    # PLAN 3.54: statement varsa AI'nin sahtekarlık/şüpheli-içerik taraması için
    # outbox'a ekle (statement metni payload'a gömülmez — worker DB'den okur,
    # evidence_scan_requested_handler'daki "payload sadece konum taşır" deseniyle aynı).
    if attestation.statement:
        session.add(Outbox(topic="attestation.fraud_check_requested", payload={"attestation_id": str(attestation.id)}))

    # PLAN 3.56: deterministic collusion / organization risk rules run for every
    # attestation (no AI, no statement needed) — they only raise admin-review flags.
    session.add(Outbox(topic="fraud.attestation_risk_scan_requested", payload={"attestation_id": str(attestation.id)}))

    # Transaction is committed by caller (route layer)
    return attestation, verified_exp


# ============================================================================
# Attestation Revoke (PLAN 2.10 — YET-72)
# ============================================================================


class AttestationNotFoundError(Exception):
    """Raised when attestation_id does not exist."""

    pass


class RevokeForbiddenError(Exception):
    """Raised when principal is not the attestor."""

    pass


class AttestationAlreadyRevokedError(Exception):
    """Raised when attestation has already been revoked (revoked_at IS NOT NULL)."""

    pass


def revoke_attestation(
    session: Session,
    principal: Principal,
    attestation_id: str,
    revoke_reason: str,
) -> Attestation:
    """
    Revoke an attestation (set revoked_at and revoke_reason).

    Implements PLAN 2.10 (YET-72): AC-1 through AC-8, AC-S1 through AC-S3.
    Single transaction: Attestation update + tombstone SkillSignal + superseded_by_id update + AuditEvent.

    Args:
        session: Transactional database session
        principal: Authorization context (authenticated user, must be attestor)
        attestation_id: UUID of attestation (string format)
        revoke_reason: Non-empty revocation reason (required by Pydantic, but safeguard here)

    Returns:
        Attestation object (refreshed with revoked_at and revoke_reason set)

    Raises:
        AttestationNotFoundError: Attestation not found (404)
        RevokeForbiddenError: Principal is not the attestor (403)
        AttestationAlreadyRevokedError: Attestation already revoked (409)
    """
    # Parse attestation_id
    try:
        attestation_uuid = uuid.UUID(attestation_id)
    except ValueError:
        raise AttestationNotFoundError(f"Invalid attestation_id format: {attestation_id}")

    # Fetch attestation to get engagement_id (no scope filtering yet)
    # Note: This bare select query fetches the attestation by attestation_uuid without scope
    # filtering to extract engagement_id for subsequent scoped engagement lookup. The attestation
    # object's internals (attestor_user_id, claim_type, etc.) are never exposed to scope-unauthorized
    # users: the subsequent scoped_engagements() check below ensures that if the engagement is
    # out-of-scope, an AttestationNotFoundError (404) is raised regardless. Both branches
    # (attestation not found, OR engagement out-of-scope) result in the same 404, maintaining
    # the AC-3 guarantee that scope boundary is opaque. This is a deliberate optimization:
    # a single bare select to extract engagement_id, then one scoped engagement check, rather
    # than a multi-table join.
    attestation = session.execute(
        select(Attestation).where(Attestation.id == attestation_uuid)
    ).scalar_one_or_none()

    if attestation is None:
        # Attestation doesn't exist — return 404
        raise AttestationNotFoundError(f"Attestation {attestation_id} not found")

    # AC-3: Scope check via engagement (prevents cross-tenant access)
    # Fetch engagement scoped to principal's scope
    engagement = get_scoped_or_404(
        scoped_engagements(session, principal).where(Engagement.id == attestation.engagement_id),
        session
    )

    if engagement is None:
        # Engagement out of scope (AC-3: cross-tenant, etc.) → return 404, don't reveal attestation exists
        raise AttestationNotFoundError(f"Attestation {attestation_id} not found")

    # AC-2: Check if principal is the attestor
    # At this point, engagement is in scope, so if not attestor, return 403 (not 404)
    if attestation.attestor_user_id != principal.user_id:
        raise RevokeForbiddenError("Only the attestor can revoke this attestation")

    # AC-5: Check if already revoked
    if attestation.revoked_at is not None:
        raise AttestationAlreadyRevokedError("Attestation has already been revoked")

    # Revoke: set revoked_at and revoke_reason via UPDATE WHERE revoked_at IS NULL
    now = datetime.now(timezone.utc)
    updated_rows = session.execute(
        update(Attestation)
        .where(Attestation.id == attestation_uuid)
        .where(Attestation.revoked_at.is_(None))
        .values(revoked_at=now, revoke_reason=revoke_reason)
    )

    if updated_rows.rowcount == 0:
        # Race condition: another revoke succeeded first, or attestation already revoked
        raise AttestationAlreadyRevokedError("Attestation has already been revoked")

    # Find and supersede related SkillSignals
    skill_signals = session.execute(
        select(SkillSignal).where(
            SkillSignal.source_type == "ATTESTATION",
            SkillSignal.source_id == attestation_uuid,
            SkillSignal.superseded_by_id.is_(None),
        )
    ).scalars().all()

    # For each signal, create tombstone and update superseded_by_id
    tombstone_ids = {}
    for signal in skill_signals:
        # Create tombstone SkillSignal (strength=NONE)
        tombstone = SkillSignal(
            talent_id=signal.talent_id,
            skill_id=signal.skill_id,
            source_type="ATTESTATION",
            source_id=attestation_uuid,
            strength="NONE",
            attested_by_org_id=None,
            occurred_at=now,
        )
        session.add(tombstone)
        session.flush()
        tombstone_ids[signal.id] = tombstone.id

    # Update old signals' superseded_by_id
    for old_signal_id, new_tombstone_id in tombstone_ids.items():
        session.execute(
            update(SkillSignal)
            .where(SkillSignal.id == old_signal_id)
            .values(superseded_by_id=new_tombstone_id)
        )

    # Log audit event (AC-S1: revoke_reason METNİ metadata'ya YAZILMAZ)
    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=None,
        action="ATTESTATION_REVOKED",
        subject_type="ATTESTATION",
        subject_id=attestation.id,
        result="SUCCESS",
        metadata={
            "engagement_id": str(attestation.engagement_id),
            "attestor_user_id": str(attestation.attestor_user_id),
        },
    )

    # Refresh attestation from DB and return
    session.refresh(attestation)
    return attestation
