"""Engagement service: core business logic for work engagements."""

import uuid
from typing import Callable, TypedDict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Engagement, Organization, TalentProfile
from app.services.authorization import Principal, get_scoped_or_404, scoped_engagements
from app.services.audit import log_audit_event
from app.services.outbox import enqueue


class TalentNotFoundError(Exception):
    """Raised when talent_id does not exist or is not accessible to principal."""
    pass


class OrganizationNotFoundError(Exception):
    """Raised when organization_id does not exist or is not accessible to principal."""
    pass


class InstitutionMismatchError(Exception):
    """Raised when institution_id does not match talent's institution."""
    pass


class EngagementNotFoundError(Exception):
    """Raised when engagement_id does not exist or is not accessible to principal."""
    pass


class IllegalTransitionError(Exception):
    """Raised when to_status is not a valid transition from current status."""
    pass


class PreconditionFailedError(Exception):
    """Raised when transition preconditions are not met (institution_id NULL, reason missing)."""
    pass


class TransitionForbiddenError(Exception):
    """Raised when principal is not authorized to perform this transition."""
    pass


class VersionConflictError(Exception):
    """Raised when version from request does not match DB version (optimistic locking)."""
    pass


class TransitionSpec(TypedDict):
    """Type specification for transition table entries."""
    preconditions: list[str]
    can_transition: Callable[[], bool]


def create_engagement(
    session: Session,
    principal: Principal,
    talent_id: str,
    organization_id: str,
    kind: str,
    title: str,
    institution_id: str | None = None,
    confidential: bool = False,
) -> Engagement:
    """
    Create a new engagement record for a talent.

    AC-1: POST /engagements logic.
    - Validates talent exists and is accessible to principal
    - Validates organization exists and is accessible to principal
    - Validates institution_id (if provided) matches talent's institution
    - Creates engagement with status=DRAFT, version=1
    - Logs audit event in same transaction

    Args:
        session: Database session
        principal: Authorization context
        talent_id: UUID of talent (string format)
        organization_id: UUID of organization (string format)
        kind: Engagement kind (INTERNSHIP|CAPSTONE|SHORT_PROJECT|PART_TIME)
        title: Engagement title
        institution_id: Optional UUID of institution (string format)
        confidential: Whether engagement is confidential

    Returns:
        Created Engagement object

    Raises:
        TalentNotFoundError: If talent does not exist or is not accessible
        OrganizationNotFoundError: If organization does not exist or is not accessible
        InstitutionMismatchError: If institution_id doesn't match talent's institution
    """
    # Parse UUIDs
    try:
        talent_uuid = uuid.UUID(talent_id)
    except ValueError:
        raise TalentNotFoundError(f"Invalid talent_id format: {talent_id}")

    try:
        org_uuid = uuid.UUID(organization_id)
    except ValueError:
        raise OrganizationNotFoundError(f"Invalid organization_id format: {organization_id}")

    try:
        inst_uuid = uuid.UUID(institution_id) if institution_id else None
    except ValueError:
        raise InstitutionMismatchError(f"Invalid institution_id format: {institution_id}")

    # Default-deny: only TALENT, ORG_MEMBER, ORG_ADMIN can create engagements
    if principal.kind not in ("TALENT", "ORG_MEMBER", "ORG_ADMIN"):
        raise TalentNotFoundError("Not authorized to create engagements")

    # Validate talent exists and is accessible to principal
    # AC-S1: TALENT can only create for their own talent_id
    # AC-S1: ORG_MEMBER can create for any talent_id, but must check tenant isolation
    if principal.kind == "TALENT":
        # TALENT can only create engagement for themselves
        if principal.talent_id != talent_uuid:
            raise TalentNotFoundError(f"Talent {talent_id} not found or not accessible")

    # Verify talent exists
    talent = session.execute(
        select(TalentProfile).where(TalentProfile.id == talent_uuid)
    ).scalar_one_or_none()

    if not talent:
        raise TalentNotFoundError(f"Talent {talent_id} not found")

    # Validate organization exists and is accessible to principal
    # AC-S2: ORG_MEMBER can only create for their own organizations
    if principal.kind in ("ORG_MEMBER", "ORG_ADMIN"):
        if org_uuid not in principal.org_ids:
            raise OrganizationNotFoundError(f"Organization {organization_id} not found or not accessible")

    org = session.execute(
        select(Organization).where(Organization.id == org_uuid)
    ).scalar_one_or_none()

    if not org:
        raise OrganizationNotFoundError(f"Organization {organization_id} not found")

    # Validate institution_id if provided (AC-5, AC-S3)
    # institution_id must match talent's institution_id
    if inst_uuid is not None:
        if talent.institution_id != inst_uuid:
            # Generic error message that doesn't reveal whether institution exists
            raise InstitutionMismatchError("institution_id does not match talent's institution")

    # Create new engagement (AC-1)
    engagement = Engagement(
        talent_id=talent_uuid,
        organization_id=org_uuid,
        institution_id=inst_uuid,
        kind=kind,
        title=title,
        status="DRAFT",
        version=1,
        confidential=confidential,
    )
    session.add(engagement)
    try:
        session.flush()
    except IntegrityError as e:
        # Check if it's a FK constraint violation
        if "fk_" in str(e).lower() or "foreign key" in str(e).lower():
            raise TalentNotFoundError("Referenced resource not found")
        raise

    # Log audit event in same transaction (AC-1)
    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=None,
        action="ENGAGEMENT_CREATED",
        subject_type="engagement",
        subject_id=engagement.id,
        result="SUCCESS",
        metadata={
            "kind": kind,
            "talent_id": str(talent_uuid),
            "organization_id": str(org_uuid),
        },
    )

    return engagement


def transition_engagement(
    session: Session,
    principal: Principal,
    engagement_id: str,
    to_status: str,
    version: int,
    reason: str | None = None,
) -> Engagement:
    """
    Transition engagement status with optimistic locking and authorization checks.

    PLAN 2.2 — engagement-durum-makinesi-transitions-ucu.

    Implements Acceptance Criteria AC-1 through AC-14, AC-S1 through AC-S4.
    Transition table (4 transitions):
    - T1: DRAFT → PENDING_APPROVAL (TALENT/ORG_MEMBER/ORG_ADMIN with matching talent/org)
    - T2: PENDING_APPROVAL → ACTIVE (COORDINATOR with matching institution)
    - T3: PENDING_APPROVAL → REJECTED (COORDINATOR with matching institution, requires reason)
    - T6: ACTIVE → CANCELLED (ORG_ADMIN/COORDINATOR with matching org/institution, requires reason)

    Args:
        session: Database session (must be transactional)
        principal: Authorization context
        engagement_id: UUID of engagement (string format)
        to_status: Target status (must be valid transition from current)
        version: Optimistic locking version from request
        reason: Optional reason for REJECTED/CANCELLED transitions

    Returns:
        Updated Engagement object

    Raises:
        EngagementNotFoundError: Engagement not found or not accessible (404)
        IllegalTransitionError: to_status not valid from current status (422)
        PreconditionFailedError: Preconditions not met (institution_id NULL, reason missing) (422)
        TransitionForbiddenError: Principal not authorized for this transition (403)
        VersionConflictError: Version mismatch (optimistic locking) (409)
    """
    # Parse UUID
    try:
        engagement_uuid = uuid.UUID(engagement_id)
    except ValueError:
        raise EngagementNotFoundError(f"Invalid engagement_id format: {engagement_id}")

    # Fetch engagement scoped to principal (AC-10, AC-11 unified by get_scoped_or_404)
    engagement = get_scoped_or_404(
        scoped_engagements(session, principal).where(Engagement.id == engagement_uuid),
        session
    )
    if engagement is None:
        # Both "engagement doesn't exist" and "no access" return 404 per AC-11
        raise EngagementNotFoundError(f"Engagement {engagement_id} not found")

    current_status = engagement.status

    # Check: version mismatch (optimistic locking) EARLY — before other checks (AC-9, AC-S1, AC-S4)
    # This ensures version conflict is reported before illegal transition or authorization errors
    if engagement.version != version:
        raise VersionConflictError("Version conflict: engagement has been modified since retrieval")

    # Transition table (4 valid transitions)
    # Each entry: from_status -> to_status -> (allowed_roles, preconditions, authorization check)
    transition_table: dict[tuple[str, str], TransitionSpec] = {
        ("DRAFT", "PENDING_APPROVAL"): {
            "preconditions": ["institution_id_not_null"],
            "can_transition": lambda: (
                (principal.kind == "TALENT" and principal.talent_id == engagement.talent_id) or
                (principal.kind in ("ORG_MEMBER", "ORG_ADMIN") and engagement.organization_id in principal.org_ids)
            ),
        },
        ("PENDING_APPROVAL", "ACTIVE"): {
            "preconditions": [],
            "can_transition": lambda: (
                principal.kind == "COORDINATOR" and
                engagement.institution_id in principal.institution_ids
            ),
        },
        ("PENDING_APPROVAL", "REJECTED"): {
            "preconditions": ["reason_not_empty"],
            "can_transition": lambda: (
                principal.kind == "COORDINATOR" and
                engagement.institution_id in principal.institution_ids
            ),
        },
        ("ACTIVE", "CANCELLED"): {
            "preconditions": ["reason_not_empty"],
            "can_transition": lambda: (
                (principal.kind == "ORG_ADMIN" and engagement.organization_id in principal.org_admin_ids) or
                (principal.kind == "COORDINATOR" and engagement.institution_id in principal.institution_ids)
            ),
        },
    }

    # Check: is this transition defined? (AC-5)
    if (current_status, to_status) not in transition_table:
        raise IllegalTransitionError(f"Transition from {current_status} to {to_status} is not allowed")

    transition_spec = transition_table[(current_status, to_status)]

    # Check: preconditions (AC-6, AC-7)
    for precondition in transition_spec["preconditions"]:
        if precondition == "institution_id_not_null":
            if engagement.institution_id is None:
                raise PreconditionFailedError("institution_id is required for this transition")
        elif precondition == "reason_not_empty":
            if not reason or reason.strip() == "":
                raise PreconditionFailedError("reason is required for this transition")

    # Check: authorization (AC-8, AC-S3)
    if not transition_spec["can_transition"]():
        raise TransitionForbiddenError("Not authorized to perform this transition")

    # Optimistic locking: UPDATE with status and version check (defense-in-depth paranoia check)
    # Version was already checked above, but UPDATE includes it for atomic consistency
    from sqlalchemy import update
    values_dict = {"status": to_status, "version": Engagement.version + 1}
    if reason is not None:
        values_dict["reason"] = reason

    result = session.execute(
        update(Engagement)
        .where(
            Engagement.id == engagement_uuid,
            Engagement.status == current_status,
            Engagement.version == version,
        )
        .values(**values_dict)
    )

    # Paranoia check: if rowcount==0, either version or status changed (shouldn't happen)
    if result.rowcount == 0:
        raise VersionConflictError("Update failed: engagement state changed unexpectedly")

    # Refresh engagement from DB to get updated version
    session.refresh(engagement)

    # Log audit event (istisnasız her geçişte) — reason KONULMAMALI audit payload'ına
    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=None,
        action="ENGAGEMENT_TRANSITIONED",
        subject_type="engagement",
        subject_id=engagement.id,
        result="SUCCESS",
        metadata={
            "from_status": current_status,
            "to_status": to_status,
        },
    )

    # Enqueue outbox for notification (T1: PENDING_APPROVAL → koordinatör bildirimi)
    # T2, T3, T6 için de benzer bildirimler olabilir ama bu görevde T1'e fokus
    # reason KONULMAMALI outbox payload'ına (PII riski)
    if to_status == "PENDING_APPROVAL":
        # Notify coordinators of the institution
        enqueue(
            session=session,
            topic="engagement.pending_approval",
            payload={
                "engagement_id": str(engagement.id),
                "talent_id": str(engagement.talent_id),
                "organization_id": str(engagement.organization_id),
                "institution_id": str(engagement.institution_id),
            },
        )

    return engagement
