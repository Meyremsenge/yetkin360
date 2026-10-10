"""
Authorization core: Principal dataclass, can() function, scoped_*() queries, and get_scoped_or_404() helper.

Implements access control and data scoping per atdd.md (yet-2-yetkilendirme-cekirdegi).
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import Attestation, CertificateCheck, Complaint, Deliverable, Engagement, EngagementTask, Evaluation, Evidence, Institution, InstitutionLinkRequest, Organization, OrganizationMember, PortfolioItem, SkillClaim, SkillSignal, TalentProfile, User, VerifiedExperience


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


def scoped_organization_directory(session: Session, principal: Principal) -> Select:
    """
    Return a SQLAlchemy Select query over ALL active organizations — a
    deliberate exception to tenant scoping, used only by the org-picker
    flow (PLAN 3.53: talent starting a new engagement searches/browses the
    organization directory to choose one, since any authenticated talent
    may begin a relationship with any organization — there is no prior
    membership to scope by). Requires authentication (route dependency),
    but not membership. Excludes soft-deleted/non-ACTIVE rows.

    Never use this for anything that should be tenant-isolated — use
    scoped_organizations() for that.
    """
    return select(Organization).where(
        Organization.status == "ACTIVE", Organization.deleted_at.is_(None)
    )


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


def scoped_own_portfolio_items(session: Session, principal: Principal) -> Select:
    """
    The principal's own, not soft-deleted portfolio items (docs/arastirma-ogrenci-profili.md §4.3).

    Ownership comes from principal.talent_id (the session), never from the URL or body.
    Another talent's item, an unknown id and a talent-less principal are all out of
    scope, so callers answer an identical 404.
    """
    if principal.talent_id is not None:
        return select(PortfolioItem).where(
            PortfolioItem.talent_id == principal.talent_id,
            PortfolioItem.deleted_at.is_(None),
        )
    return select(PortfolioItem).where(PortfolioItem.id.in_([]))


def scoped_public_portfolio_items(session: Session, talent_id: uuid.UUID) -> Select:
    """
    (PortfolioItem, CertificateCheck | None) rows the owner consented to show publicly.

    Used only by the public profile, after the talent was resolved via
    scoped_public_talent_profile() — talent visibility is not re-checked here.
    Kept: show_on_profile AND not deleted. The certificate check is joined only
    through evidence that is the same talent's and not deleted, so a badge can
    never be borrowed from someone else's file. Callers must not expose the
    check's extracted_name/qr_raw_data/page_name or the evidence file.
    """
    return (
        select(PortfolioItem, CertificateCheck)
        .outerjoin(
            Evidence,
            and_(
                Evidence.id == PortfolioItem.evidence_id,
                Evidence.owner_talent_id == PortfolioItem.talent_id,
                Evidence.deleted_at.is_(None),
            ),
        )
        .outerjoin(CertificateCheck, CertificateCheck.evidence_id == Evidence.id)
        .where(
            PortfolioItem.talent_id == talent_id,
            PortfolioItem.show_on_profile.is_(True),
            PortfolioItem.deleted_at.is_(None),
        )
    )


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


def _not_fully_revoked():
    """
    GUV-05 filter for VerifiedExperience queries: visible if the engagement has
    no attestations at all, or at least one non-revoked attestation. An
    experience whose attestations were all revoked is hidden everywhere.
    """
    has_any_attestation = select(1).where(
        Attestation.engagement_id == VerifiedExperience.engagement_id,
    ).exists()
    has_active_attestation = select(1).where(
        Attestation.engagement_id == VerifiedExperience.engagement_id,
        Attestation.revoked_at.is_(None),
    ).exists()
    return (~has_any_attestation) | has_active_attestation


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
    return select(VerifiedExperience).where(
        VerifiedExperience.talent_id == talent_id,
        # GUV-05: Include if no attestations exist OR at least one is active
        _not_fully_revoked(),
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
        return select(VerifiedExperience).where(
            VerifiedExperience.talent_id == principal.talent_id,
            # GUV-05: Include if no attestations exist OR at least one is active
            _not_fully_revoked(),
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
            _not_fully_revoked(),
        )
    )


def scoped_public_organization(session: Session, organization_id: uuid.UUID) -> Select:
    """
    Return a SQLAlchemy Select query for an organization shown on its public
    showcase page (GET /public/organizations/{id}, auth-free).

    Only ACTIVE, non-deleted organizations: a suspended or deleted organization
    is indistinguishable from an unknown id (same 404). The same set is already
    listed in the Keşfet directory (scoped_organization_directory).
    """
    return select(Organization).where(
        Organization.id == organization_id,
        Organization.status == "ACTIVE",
        Organization.deleted_at.is_(None),
    )


def scoped_public_org_showcase_experiences(session: Session, organization_id: uuid.UUID) -> Select:
    """
    Return a SQLAlchemy Select query for the VerifiedExperience rows shown on an
    organization's public showcase, joined with their TalentProfile.

    Double consent: the experience is PUBLIC (the talent opted this record in)
    AND the talent profile itself is PUBLIC with a slug and not deleted. A
    PUBLIC record of a non-PUBLIC profile never surfaces. GUV-05 applies.

    The caller must first resolve the organization via scoped_public_organization()
    and check its showcase_public switch; this query only scopes the records.

    Returns rows of (VerifiedExperience, TalentProfile).
    """
    return (
        select(VerifiedExperience, TalentProfile)
        .join(Engagement, Engagement.id == VerifiedExperience.engagement_id)
        .join(TalentProfile, TalentProfile.id == VerifiedExperience.talent_id)
        .where(
            Engagement.organization_id == organization_id,
            VerifiedExperience.visibility == "PUBLIC",
            TalentProfile.visibility == "PUBLIC",
            TalentProfile.public_slug.is_not(None),
            TalentProfile.deleted_at.is_(None),
            _not_fully_revoked(),
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


def scoped_public_engagement_evaluations(session: Session, engagement_id: uuid.UUID) -> Select:
    """
    Return a SQLAlchemy Select query for the ORG_TO_TALENT evaluations of an
    engagement, for the "çift imza" badge and the evaluator line on public pages.

    Only call this for an engagement whose VerifiedExperience was already
    resolved as PUBLIC (scoped_public_verified_experience_by_token() /
    scoped_public_verified_experiences()); it does not re-check visibility.

    Only evaluations written by a member of the engagement's own organization.
    Returns rows of (Evaluation, unit, evaluator_full_name):
      - unit: OrganizationMember.unit (may be None)
      - evaluator_full_name: the evaluator's own TalentProfile name, None when
        the profile is missing or deleted. Never the e-mail.
    Oldest evaluation first. private_note is on the row; callers must not expose it.
    """
    return (
        select(Evaluation, OrganizationMember.unit, TalentProfile.full_name)
        .join(Engagement, Engagement.id == Evaluation.engagement_id)
        .join(
            OrganizationMember,
            and_(
                OrganizationMember.organization_id == Engagement.organization_id,
                OrganizationMember.user_id == Evaluation.evaluator_user_id,
            ),
        )
        .outerjoin(
            TalentProfile,
            and_(
                TalentProfile.user_id == Evaluation.evaluator_user_id,
                TalentProfile.deleted_at.is_(None),
            ),
        )
        .where(
            Evaluation.engagement_id == engagement_id,
            Evaluation.direction == "ORG_TO_TALENT",
        )
        .order_by(Evaluation.submitted_at, Evaluation.id)
    )


def scoped_attestations_for_engagements(session: Session, engagement_ids: list[uuid.UUID]) -> Select:
    """
    Batch form of scoped_attestations_for_engagement() for several already
    visibility-checked engagements at once (organization showcase: one query
    instead of one per record). Same filters: skill set, not revoked (GUV-05).
    """
    return select(Attestation).where(
        Attestation.engagement_id.in_(engagement_ids),
        Attestation.skill_id.isnot(None),
        Attestation.revoked_at.is_(None),
    )


# ============================================================================
# Keşfet directory (PLAN R.1, docs/kesfet-tasarim.md)
# ============================================================================


def scoped_discoverable_talent_profiles(session: Session, principal: Principal) -> Select:
    """
    Return a SQLAlchemy Select query over the talent profiles listed in Keşfet.

    A deliberate exception to tenant scoping, like scoped_organization_directory():
    any authenticated principal may list profiles the talent has already made
    readable anonymously via /p/{slug}. Nothing that is not already public is
    reachable through this query:
    - visibility='PUBLIC' (ORGANIZATIONS / INSTITUTION / PRIVATE never listed)
    - public_slug IS NOT NULL (the card links to the public profile)
    - deleted_at IS NULL

    Anonymous principals get an empty scope (defense-in-depth; the route already
    requires authentication).

    Never use this for per-talent data — use scoped_talent_profiles() for that.
    """
    if principal.user_id is None:
        return select(TalentProfile).where(TalentProfile.id.in_([]))
    return select(TalentProfile).where(
        TalentProfile.visibility == "PUBLIC",
        TalentProfile.public_slug.is_not(None),
        TalentProfile.deleted_at.is_(None),
    )


def scoped_discoverable_verified_experiences(session: Session, talent_ids: list[uuid.UUID]) -> Select:
    """
    Return a SQLAlchemy Select query for the PUBLIC VerifiedExperience rows of
    already-discoverable talents (ids must come from
    scoped_discoverable_talent_profiles()).

    Same visibility rule as the public profile: visibility='PUBLIC', and
    GUV-05 — an experience whose attestations are all revoked is hidden.
    """
    return select(VerifiedExperience).where(
        VerifiedExperience.talent_id.in_(talent_ids),
        VerifiedExperience.visibility == "PUBLIC",
        _not_fully_revoked(),
    )


def scoped_discoverable_attestations(session: Session) -> Select:
    """
    Return a SQLAlchemy Select query for the attestations that seal a skill on a
    PUBLIC VerifiedExperience — the only source of the skill chips in Keşfet.

    A skill attested on a non-PUBLIC experience must never surface here: the
    public profile does not show it either. Revoked attestations are excluded
    (GUV-05). Callers add their own talent / skill filters.
    """
    return (
        select(Attestation)
        .join(VerifiedExperience, VerifiedExperience.engagement_id == Attestation.engagement_id)
        .where(
            VerifiedExperience.talent_id == Attestation.talent_id,
            VerifiedExperience.visibility == "PUBLIC",
            Attestation.skill_id.is_not(None),
            Attestation.revoked_at.is_(None),
        )
    )


def scoped_public_skill_signals(
    session: Session, talent_id: uuid.UUID, engagement_ids: list[uuid.UUID]
) -> Select:
    """
    Return (SkillSignal, engagement_id) rows backing the public skill map.

    Used only by the public profile, after the talent was resolved via
    scoped_public_talent_profile() and engagement_ids were taken from its PUBLIC
    experiences (scoped_public_verified_experiences + visibility filter). Signals
    are resolved to their engagement through their source row:
      - ATTESTATION → attestations (revoked ones excluded)
      - TASK        → engagement_tasks
      - DELIVERABLE → deliverables
    and kept only when that engagement is in engagement_ids, so a PRIVATE
    experience can never leak a skill or strength onto the public page.
    Superseded signals (revocation tombstones' predecessors) are excluded.
    """
    if not engagement_ids:
        return select(SkillSignal, Attestation.engagement_id).where(SkillSignal.id.in_([]))
    source_engagement = func.coalesce(
        Attestation.engagement_id, EngagementTask.engagement_id, Deliverable.engagement_id
    ).label("engagement_id")
    return (
        select(SkillSignal, source_engagement)
        .outerjoin(
            Attestation,
            and_(
                SkillSignal.source_type == "ATTESTATION",
                Attestation.id == SkillSignal.source_id,
                Attestation.revoked_at.is_(None),
            ),
        )
        .outerjoin(
            EngagementTask,
            and_(SkillSignal.source_type == "TASK", EngagementTask.id == SkillSignal.source_id),
        )
        .outerjoin(
            Deliverable,
            and_(SkillSignal.source_type == "DELIVERABLE", Deliverable.id == SkillSignal.source_id),
        )
        .where(
            SkillSignal.talent_id == talent_id,
            SkillSignal.superseded_by_id.is_(None),
            SkillSignal.strength != "NONE",
            source_engagement.in_(engagement_ids),
        )
    )


def scoped_institution_students(
    session: Session, principal: Principal, institution_id: uuid.UUID
) -> Select:
    """
    Talent profiles linked to an institution, as seen by that institution's members.

    Coordinator panel student list. A profile is in scope only when:
      - the principal is a member of the institution (institution_ids: COORDINATOR,
        ADMIN, SUPERVISOR); anyone else gets an empty query (caller answers 404),
      - the student's link was approved (TalentProfile.institution_id is set by the
        D10 link-request workflow, so the student consented),
      - the student did not choose PRIVATE (INSTITUTION and wider levels include
        their own institution),
      - the profile is not deleted and the user account is ACTIVE.
    """
    if institution_id not in principal.institution_ids:
        return select(TalentProfile).where(TalentProfile.id.in_([]))
    return (
        select(TalentProfile)
        .join(User, User.id == TalentProfile.user_id)
        .where(
            TalentProfile.institution_id == institution_id,
            TalentProfile.visibility != "PRIVATE",
            TalentProfile.deleted_at.is_(None),
            User.status == "ACTIVE",
        )
    )


# ============================================================================
# Complaints (sikayet-backend)
# ============================================================================


def scoped_owned_complaints(session: Session, principal: Principal) -> Select:
    """The talent's own complaints — the only scope that may list or download attachments."""
    if principal.talent_id is None:
        return select(Complaint).where(Complaint.id.in_([]))
    return select(Complaint).where(Complaint.talent_id == principal.talent_id)


def scoped_complaints(session: Session, principal: Principal) -> Select:
    """
    Complaints readable through the non-admin routes, as a union of:
    - owner: the talent who filed it;
    - respondent: the derived respondent, only once the admin has asked for an
      explanation (before that the respondent must not learn about it);
    - escalated member: after escalation, COORDINATOR/ADMIN members of the target
      institution (not SUPERVISOR) or ADMIN members of the target organization.
    The platform admin gets nothing here (admin routes use scoped_admin_complaints).
    Callers decide which fields each relation may see.
    """
    conditions = []
    if principal.talent_id is not None:
        conditions.append(Complaint.talent_id == principal.talent_id)
    if principal.user_id is not None:
        conditions.append(
            and_(Complaint.respondent_user_id == principal.user_id, Complaint.explanation_requested_at.is_not(None))
        )
    deciding_institution_ids = [
        inst_id for inst_id in principal.institution_ids if inst_id not in principal.supervisor_institution_ids
    ]
    if deciding_institution_ids:
        conditions.append(
            and_(Complaint.escalated_at.is_not(None), Complaint.target_institution_id.in_(deciding_institution_ids))
        )
    if principal.org_admin_ids:
        conditions.append(
            and_(Complaint.escalated_at.is_not(None), Complaint.target_organization_id.in_(principal.org_admin_ids))
        )
    if not conditions:
        return select(Complaint).where(Complaint.id.in_([]))
    return select(Complaint).where(or_(*conditions))


def scoped_admin_complaints(session: Session, principal: Principal) -> Select:
    """Every complaint for a platform admin, nothing for anyone else (defense in depth
    behind the router-level require_platform_admin gate)."""
    if not principal.is_platform_admin:
        return select(Complaint).where(Complaint.id.in_([]))
    return select(Complaint)


def scoped_upheld_complaint_counts(session: Session, target_type: str, target_ids: list[uuid.UUID]) -> Select:
    """
    (target_id, count) of UPHELD complaints — a deliberate public aggregate. Only the
    number leaves this query: no text, no talent, no respondent (AC-S13). A target
    without UPHELD complaints has no row (callers default to 0).
    """
    column = Complaint.target_institution_id if target_type == "INSTITUTION" else Complaint.target_organization_id
    return (
        select(column, func.count())
        .where(Complaint.status == "UPHELD", column.in_(target_ids))
        .group_by(column)
    )
