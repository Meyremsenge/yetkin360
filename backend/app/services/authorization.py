"""
Authorization core: Principal dataclass, can() function, scoped_*() queries, and get_scoped_or_404() helper.

Implements access control and data scoping per atdd.md (yet-2-yetkilendirme-cekirdegi).
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import Select, select, or_
from sqlalchemy.orm import Session

from app.models import Attestation, Engagement, Evidence, Institution, InstitutionLinkRequest, Organization, SkillClaim, SkillSignal, TalentProfile, User, VerifiedExperience


@dataclass
class Principal:
    """
    Represents the caller's authorization context.

    Fields:
      - user_id: UUID of the authenticated user (None for ANONYMOUS)
      - kind: Role/type of principal — display use only. Authorization decisions must use
        per-resource ID lists (org_ids, org_admin_ids, institution_ids, institution_admin_ids),
        never kind. kind represents the principal's highest role across all resources
        and is not authoritative for per-resource checks.
      - talent_id: UUID of associated talent profile (if kind == "TALENT")
      - org_ids: List of organization IDs the principal is a member of
      - org_admin_ids: List of organization IDs the principal is an admin of
      - institution_ids: List of institution IDs the principal is associated with
      - is_platform_admin: True if principal is a platform administrator
      - is_suspended: True if principal's account is suspended. Not currently
        read by can()/scoped_*() — suspension is already enforced earlier, at
        app/core/deps.py:get_current_user (status not in PENDING/ACTIVE → 401),
        which is stricter than this field would allow (blocks reads too, not
        just writes). Kept on Principal for API completeness / future use.
      - institution_admin_ids: List of institution IDs the principal is an admin of
    """

    user_id: uuid.UUID | None
    kind: str
    talent_id: uuid.UUID | None
    org_ids: list[uuid.UUID]
    org_admin_ids: list[uuid.UUID]
    institution_ids: list[uuid.UUID]
    is_platform_admin: bool
    is_suspended: bool
    institution_admin_ids: list[uuid.UUID] = field(default_factory=list)
    supervisor_institution_ids: list[uuid.UUID] = field(default_factory=list)

    @property
    def coordinator_institution_ids(self) -> list[uuid.UUID]:
        """
        Derived property: institutions where principal is COORDINATOR (not ADMIN).

        Returns institutions that are in institution_ids but NOT in institution_admin_ids,
        preserving order from institution_ids.

        Implements AC-5 (AC-S4): coordinator role is distinct from admin role;
        coordinator_ids excludes admin institutions to prevent privilege escalation.
        """
        return [
            inst_id
            for inst_id in self.institution_ids
            if inst_id not in self.institution_admin_ids
        ]


@dataclass(frozen=True)
class EngagementRelation:
    """
    Frozen dataclass representing the relationship between a principal and engagement.

    Used to enforce AC-S1 (self-dealing prevention): when principal is both talent
    (subject) and org/coordinator member, org/coordinator flags are masked.
    However, has_org_side_link remains unmasked to track actual membership.

    Fields:
      - is_subject: True if principal.talent_id == engagement.talent_id
      - is_org_member: True if engagement.organization_id in principal.org_ids
        and principal is not the subject
      - is_org_admin: True if engagement.organization_id in principal.org_admin_ids
        and principal is not the subject
      - is_coordinator: True if engagement.institution_id in principal.coordinator_institution_ids
        and principal is not the subject
      - has_org_side_link: True if principal has any org/institution membership link
        (unmasked, even if subject)

    Implements AC-S1 (self-dealing masking), AC-S3 (privacy), AC-5 (union membership).
    """

    is_subject: bool
    is_org_member: bool
    is_org_admin: bool
    is_coordinator: bool
    has_org_side_link: bool


def engagement_relation(principal: Principal, engagement) -> EngagementRelation:
    """
    Helper to compute the relationship between principal and engagement.

    Masking rule (AC-S1): if principal is the subject (talent_id matches),
    org/coordinator flags are False (self-dealing prevention), but has_org_side_link
    remains unmasked to track actual membership.

    Args:
        principal: Principal object with authorization context
        engagement: Object with .talent_id, .organization_id, .institution_id

    Returns:
        EngagementRelation frozen dataclass

    Implements AC-S1 (self-dealing masking), AC-S3 (privacy), AC-5 (multi-role union).
    """
    is_subject = (
        principal.talent_id is not None
        and engagement.talent_id is not None
        and principal.talent_id == engagement.talent_id
    )

    # Membership checks (before masking)
    is_org_admin = (
        engagement.organization_id is not None
        and engagement.organization_id in principal.org_admin_ids
    )
    is_org_member = (
        engagement.organization_id is not None
        and engagement.organization_id in principal.org_ids
    )
    is_coordinator = (
        engagement.institution_id is not None
        and engagement.institution_id in principal.coordinator_institution_ids
    )

    # has_org_side_link: raw membership, subject-independent
    # Includes both org membership (member and admin) and institution membership (both coordinator and admin)
    has_org_side_link = (
        (engagement.organization_id is not None
         and engagement.organization_id in principal.org_ids)
        or (engagement.institution_id is not None
            and engagement.institution_id in principal.institution_ids)
    )

    # Apply masking: if subject, all org/coordinator flags are False
    return EngagementRelation(
        is_subject=is_subject,
        is_org_member=is_org_member and not is_subject,
        is_org_admin=is_org_admin and not is_subject,
        is_coordinator=is_coordinator and not is_subject,
        has_org_side_link=has_org_side_link,
    )


def can(principal: Principal, action: str, resource) -> bool:
    """
    Default-deny authorization check: principal can perform action on resource.

    Args:
      - principal: Principal object with authorization context
      - action: Action name (string, e.g., "read", "admin_update")
      - resource: Resource object being accessed (e.g., User, Organization)

    Returns:
      - bool: True if action is authorized, False otherwise (default-deny)

    Implements AC-S1 (default-deny), AC-S5 (defense-in-depth ownership check).
    Note: Authorization decisions use ID lists (org_admin_ids, institution_admin_ids),
    not kind field (which is display-only per AC-6).
    """
    # Defense-in-depth: check resource ownership directly
    # Handle User resource: can read own User
    if isinstance(resource, User):
        return action == "read" and principal.user_id == resource.id

    # Handle Organization resource: can admin_update if principal is org admin
    if isinstance(resource, Organization):
        return action == "admin_update" and resource.id in principal.org_admin_ids

    # Handle Institution resource: can admin_update if principal is institution admin
    if isinstance(resource, Institution):
        return action == "admin_update" and resource.id in principal.institution_admin_ids

    # Undefined action/resource combination: default-deny
    return False


def scoped_organizations(session: Session, principal: Principal) -> Select:
    """
    Return a SQLAlchemy Select query filtered to organizations in principal's scope.

    Args:
      - session: SQLAlchemy Session
      - principal: Principal object

    Returns:
      - sqlalchemy.sql.Select: Query returning Organization rows in principal's scope

    Implements AC-2, AC-S2 (tenant isolation).
    Uses org_ids, not kind (which is display-only per AC-6).
    """
    return select(Organization).where(Organization.id.in_(principal.org_ids))


def scoped_institutions(session: Session, principal: Principal) -> Select:
    """
    Return a SQLAlchemy Select query filtered to institutions in principal's scope.

    Args:
      - session: SQLAlchemy Session
      - principal: Principal object

    Returns:
      - sqlalchemy.sql.Select: Query returning Institution rows in principal's scope

    Implements AC-2, AC-S2 (tenant isolation).
    Uses institution_ids, not kind (which is display-only per AC-6).
    """
    return select(Institution).where(Institution.id.in_(principal.institution_ids))


def scoped_talent_profiles(session: Session, principal: Principal) -> Select:
    """
    Return a SQLAlchemy Select query filtered to talent profiles in principal's scope.

    Args:
      - session: SQLAlchemy Session
      - principal: Principal object

    Returns:
      - sqlalchemy.sql.Select: Query returning TalentProfile rows in principal's scope

    Implements AC-2, AC-S2 (tenant isolation).
    """
    if principal.talent_id is not None:
        return select(TalentProfile).where(TalentProfile.user_id == principal.user_id)
    # All other kinds: no talent profiles in scope
    return select(TalentProfile).where(TalentProfile.id.in_([]))


def scoped_skill_claims(session: Session, principal: Principal) -> Select:
    """
    Return a SQLAlchemy Select query filtered to skill claims in principal's scope.

    Args:
      - session: SQLAlchemy Session
      - principal: Principal object

    Returns:
      - sqlalchemy.sql.Select: Query returning SkillClaim rows in principal's scope

    Implements AC-S3 (YET-11): only returns claims for authenticated talent.
    """
    if principal.talent_id is not None:
        return select(SkillClaim).where(SkillClaim.talent_id == principal.talent_id)
    # All other kinds: no skill claims in scope
    return select(SkillClaim).where(SkillClaim.id.in_([]))


def scoped_skill_signals(session: Session, principal: Principal) -> Select:
    """
    Return a SQLAlchemy Select query filtered to skill signals in principal's scope.

    Args:
      - session: SQLAlchemy Session
      - principal: Principal object

    Returns:
      - sqlalchemy.sql.Select: Query returning SkillSignal rows in principal's scope

    Implements AC-S1, AC-S2 (YET-104): only returns signals for authenticated talent,
    prevents cross-talent access via skill_id filtering.
    """
    if principal.talent_id is not None:
        return select(SkillSignal).where(SkillSignal.talent_id == principal.talent_id)
    # All other kinds: no skill signals in scope
    return select(SkillSignal).where(SkillSignal.id.in_([]))


def scoped_engagements(session: Session, principal: Principal) -> Select:
    """
    Return a SQLAlchemy Select query filtered to engagements in principal's scope.

    Args:
      - session: SQLAlchemy Session
      - principal: Principal object

    Returns:
      - sqlalchemy.sql.Select: Query returning Engagement rows in principal's scope

    Implements AC-2, AC-S2 (tenant isolation for engagements), AC-5 (multi-role union).
    Scoping is computed as a union (OR) of all membership paths:
    - If principal.talent_id is not None: talent_id == principal.talent_id
    - If principal.org_ids is not empty: organization_id in principal.org_ids
    - If principal.institution_ids is not empty: institution_id in principal.institution_ids
    If all membership lists are empty, returns no engagements (empty result).
    Uses membership lists, not kind (which is display-only per AC-6) — this also
    covers SUPERVISOR (AUTHZ-03/AC-7), whose institution_ids get_current_principal()
    populates like COORDINATOR/INST_ADMIN.
    """
    conditions = []

    # Talent pathway
    if principal.talent_id is not None:
        conditions.append(Engagement.talent_id == principal.talent_id)

    # Organization pathway (both member and admin)
    if principal.org_ids:
        conditions.append(Engagement.organization_id.in_(principal.org_ids))

    # Institution pathway (coordinator, admin, and supervisor)
    if principal.institution_ids:
        conditions.append(Engagement.institution_id.in_(principal.institution_ids))

    # If no conditions, return empty result
    if not conditions:
        return select(Engagement).where(Engagement.id.in_([]))

    # Single condition: no OR needed
    if len(conditions) == 1:
        return select(Engagement).where(conditions[0])

    # Multiple conditions: use OR
    return select(Engagement).where(or_(*conditions))


def scoped_evidence(session: Session, principal: Principal) -> Select:
    """
    Return a SQLAlchemy Select query filtered to evidence in principal's scope.

    Evidence is PRIVATE by design (current scope). Only the owner (talent who uploaded)
    can access their evidence. Platform admin cannot access PRIVATE evidence
    (bilinçli istisna per final analiz §21.2).

    Args:
      - session: SQLAlchemy Session
      - principal: Principal object

    Returns:
      - sqlalchemy.sql.Select: Query returning Evidence rows in principal's scope

    Implements AC-5, AC-6 (ownership), AC-S3 (admin excluded from PRIVATE).
    Uses talent_id membership, not kind (which is display-only per AC-6).
    """
    if principal.talent_id is not None:
        return select(Evidence).where(Evidence.owner_talent_id == principal.talent_id)
    # No talent_id: no evidence in scope
    return select(Evidence).where(Evidence.id.in_([]))


def scoped_own_institution_link_requests(session: Session, principal: Principal) -> Select:
    """
    Return a SQLAlchemy Select query for a talent's own InstitutionLinkRequest rows.

    Owner can see ALL their requests regardless of status (PENDING/APPROVED/REJECTED).
    Used by GET /talents/me/institution-link-requests.

    Args:
      - session: SQLAlchemy Session
      - principal: Principal object (must have talent_id)

    Returns:
      - sqlalchemy.sql.Select: Query returning InstitutionLinkRequest rows for this talent

    Implements YET-197/IS-10 (owner isolation — BOLA across talents).
    """
    if principal.talent_id is not None:
        return select(InstitutionLinkRequest).where(InstitutionLinkRequest.talent_profile_id == principal.talent_id)
    # All other kinds: no link requests in scope
    return select(InstitutionLinkRequest).where(InstitutionLinkRequest.id.in_([]))


def get_scoped_or_404(scoped_select: Select, session: Session):
    """
    Execute a scoped query and return first result or None.

    Args:
      - scoped_select: SQLAlchemy Select query (from scoped_*() functions)
      - session: SQLAlchemy Session

    Returns:
      - Resource object if found in scope, None otherwise

    Implements AC-5, AC-S4 (no distinction between out-of-scope and nonexistent).
    """
    return session.execute(scoped_select).scalars().first()


def scoped_public_talent_profile(session: Session, slug: str) -> Select:
    """
    Return a SQLAlchemy Select query for a PUBLIC talent profile by slug.

    Auth-free endpoint: returns TalentProfile records that are:
    - visibility='PUBLIC'
    - public_slug matches the given slug
    - deleted_at IS NULL

    Single query with combined WHERE clause to avoid timing side-channel
    (both nonexistent slug and non-PUBLIC visibility return identical 404).

    Args:
      - session: SQLAlchemy Session
      - slug: public_slug value (string)

    Returns:
      - sqlalchemy.sql.Select: Query returning TalentProfile rows matching criteria
        (typically 0 or 1 result, due to unique constraint on public_slug)

    Implements AC-1, AC-2, AC-3 (AC-S1), AC-6 (public-profil-endpoint, YET-105)
    """
    return select(TalentProfile).where(
        TalentProfile.public_slug == slug,
        TalentProfile.visibility == "PUBLIC",
        TalentProfile.deleted_at.is_(None),
    )


def scoped_public_verified_experiences(session: Session, talent_id: uuid.UUID) -> Select:
    """
    Return a SQLAlchemy Select query for a talent's VerifiedExperience rows.

    Used only after the talent itself has been verified as visibility='PUBLIC'
    via scoped_public_talent_profile() — this function does not re-check talent
    visibility, only scopes by talent_id.

    GUV-05: Filters out experiences whose attestations are all revoked.
    Visible if: no attestations OR has at least one non-revoked attestation.

    Args:
      - session: SQLAlchemy Session
      - talent_id: UUID of the (already-verified-PUBLIC) talent profile

    Returns:
      - sqlalchemy.sql.Select: Query returning VerifiedExperience rows for this talent

    Implements AC-1, AC-5 (AC-S3) (public-profil-endpoint, YET-105), GUV-05 (AC-4/AC-S3)
    """
    # Subquery: check if engagement has any attestations at all
    has_any_attestation = (
        select(1).where(
            Attestation.engagement_id == VerifiedExperience.engagement_id,
        ).exists()
    )

    # Subquery: check if engagement has at least one non-revoked attestation
    has_active_attestation = (
        select(1).where(
            Attestation.engagement_id == VerifiedExperience.engagement_id,
            Attestation.revoked_at.is_(None),
        ).exists()
    )

    return select(VerifiedExperience).where(
        VerifiedExperience.talent_id == talent_id,
        # GUV-05: Include if no attestations exist OR at least one is active
        (~has_any_attestation) | has_active_attestation,
    )


def scoped_own_verified_experiences(session: Session, principal: Principal) -> Select:
    """
    Return a SQLAlchemy Select query for a talent's own VerifiedExperience rows.

    Owner can see ALL their verified experiences regardless of visibility
    (including PRIVATE records). Used by GET /talents/me/verified-experiences.

    GUV-05: Filters out experiences whose attestations are all revoked.
    Visible if: no attestations OR has at least one non-revoked attestation.

    Args:
      - session: SQLAlchemy Session
      - principal: Principal object (must have talent_id)

    Returns:
      - sqlalchemy.sql.Select: Query returning VerifiedExperience rows for this talent

    Implements AC-7, AC-9/AC-S1 (owner isolation, visibility filter NOT applied), GUV-05 (AC-4/AC-S3)
    """
    if principal.talent_id is not None:
        # Subquery: check if engagement has any attestations at all
        has_any_attestation = (
            select(1).where(
                Attestation.engagement_id == VerifiedExperience.engagement_id,
            ).exists()
        )

        # Subquery: check if engagement has at least one non-revoked attestation
        has_active_attestation = (
            select(1).where(
                Attestation.engagement_id == VerifiedExperience.engagement_id,
                Attestation.revoked_at.is_(None),
            ).exists()
        )

        return select(VerifiedExperience).where(
            VerifiedExperience.talent_id == principal.talent_id,
            # GUV-05: Include if no attestations exist OR at least one is active
            (~has_any_attestation) | has_active_attestation,
        )
    # All other kinds: no verified experiences in scope
    return select(VerifiedExperience).where(VerifiedExperience.id.in_([]))


def scoped_public_verified_experience_by_token(session: Session, token: str) -> Select:
    """
    Return a SQLAlchemy Select query for a PUBLIC VerifiedExperience by public_token.

    Auth-free endpoint: returns VerifiedExperience records that are:
    - public_token matches the given token
    - visibility='PUBLIC'
    - GUV-05: NOT ALL attestations are revoked (if any attestations exist)
      (Visible if: no attestations OR has at least one non-revoked attestation)

    Single query with combined WHERE clause to avoid timing side-channel
    (timing must not distinguish between nonexistent token and non-PUBLIC visibility).

    Args:
      - session: SQLAlchemy Session
      - token: public_token value (string)

    Returns:
      - sqlalchemy.sql.Select: Query returning VerifiedExperience rows matching criteria
        (typically 0 or 1 result, due to unique constraint on public_token)

    Implements AC-1, AC-2, AC-3 (AC-S2), AC-6 (public-dogrulama-linki, YET-106), GUV-05 (AC-4/AC-S3)
    """
    # Subquery: check if engagement has any attestations at all
    has_any_attestation = (
        select(1).where(
            Attestation.engagement_id == VerifiedExperience.engagement_id,
        ).exists()
    )

    # Subquery: check if engagement has at least one non-revoked attestation
    has_active_attestation = (
        select(1).where(
            Attestation.engagement_id == VerifiedExperience.engagement_id,
            Attestation.revoked_at.is_(None),
        ).exists()
    )

    # Join keeps this one query: a soft-deleted talent's token must be
    # indistinguishable from an unknown token (YET-230), same as the slug route.
    return (
        select(VerifiedExperience)
        .join(TalentProfile, TalentProfile.id == VerifiedExperience.talent_id)
        .where(
            VerifiedExperience.public_token == token,
            VerifiedExperience.visibility == "PUBLIC",
            TalentProfile.deleted_at.is_(None),
            # GUV-05: Include if no attestations exist OR at least one is active
            (~has_any_attestation) | has_active_attestation,
        )
    )


def scoped_attestations_for_engagement(session: Session, engagement_id: uuid.UUID) -> Select:
    """
    Return a SQLAlchemy Select query for Attestation rows tied to an engagement.

    Used only after the parent VerifiedExperience has been verified as
    visibility='PUBLIC' via scoped_public_verified_experience_by_token() —
    this function does not re-check visibility, only scopes by engagement_id.

    Filters out revoked attestations (GUV-05: AC-4/AC-S3).

    Args:
      - session: SQLAlchemy Session
      - engagement_id: UUID of the (already-verified-PUBLIC) VerifiedExperience's engagement

    Returns:
      - sqlalchemy.sql.Select: Query returning Attestation rows with skill_id set, for this engagement

    Implements AC-1, AC-5 (public-dogrulama-linki, YET-106), GUV-05 (AC-4/AC-S3)
    """
    return select(Attestation).where(
        Attestation.engagement_id == engagement_id,
        Attestation.skill_id.isnot(None),
        Attestation.revoked_at.is_(None),  # GUV-05: exclude revoked attestations
    )
