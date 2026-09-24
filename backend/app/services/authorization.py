"""
Authorization core: Principal dataclass, can() function, scoped_*() queries, and get_scoped_or_404() helper.

Implements access control and data scoping per atdd.md (yet-2-yetkilendirme-cekirdegi).
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import Engagement, Evidence, Institution, Organization, SkillClaim, SkillSignal, TalentProfile, User


@dataclass
class Principal:
    """
    Represents the caller's authorization context.

    Fields:
      - user_id: UUID of the authenticated user (None for ANONYMOUS)
      - kind: Role/type of principal (str, plain values: "ANONYMOUS", "TALENT", "ORG_MEMBER", etc.)
        WARNING: Display use only. Authorization decisions must use per-resource ID lists
        (org_ids, org_admin_ids, institution_ids, institution_admin_ids), never kind alone.
        kind represents the principal's highest role across all resources; it is not
        authoritative for per-resource checks.
      - talent_id: UUID of associated talent profile (if kind == "TALENT")
      - org_ids: List of organization IDs the principal is a member of
      - org_admin_ids: List of organization IDs the principal is an admin of
      - institution_ids: List of institution IDs the principal is associated with
      - is_platform_admin: True if principal is a platform administrator
      - is_suspended: True if principal's account is suspended
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
    """
    # Defense-in-depth: check resource ownership directly
    # Handle User resource: can read own User
    if isinstance(resource, User):
        return action == "read" and principal.user_id == resource.id

    # Handle Organization resource: can admin_update if principal is org admin
    if isinstance(resource, Organization):
        return (
            action == "admin_update"
            and principal.kind == "ORG_ADMIN"
            and resource.id in principal.org_admin_ids
        )

    # Handle Institution resource: can admin_update if principal is institution admin
    if isinstance(resource, Institution):
        return (
            action == "admin_update"
            and principal.kind == "INST_ADMIN"
            and resource.id in principal.institution_admin_ids
        )

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
    """
    if principal.kind in ("ORG_MEMBER", "ORG_ADMIN"):
        return select(Organization).where(Organization.id.in_(principal.org_ids))
    # All other kinds: no organizations in scope
    return select(Organization).where(Organization.id.in_([]))


def scoped_institutions(session: Session, principal: Principal) -> Select:
    """
    Return a SQLAlchemy Select query filtered to institutions in principal's scope.

    Args:
      - session: SQLAlchemy Session
      - principal: Principal object

    Returns:
      - sqlalchemy.sql.Select: Query returning Institution rows in principal's scope

    Implements AC-2, AC-S2 (tenant isolation).
    """
    if principal.kind in ("INST_ADMIN", "COORDINATOR"):
        return select(Institution).where(Institution.id.in_(principal.institution_ids))
    # All other kinds: no institutions in scope
    return select(Institution).where(Institution.id.in_([]))


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

    Implements AC-2, AC-S2 (tenant isolation for engagements).
    Scoping rules per AUTHORIZATION.md §5:
    - TALENT: can see engagements where talent_id == principal.talent_id
    - ORG_MEMBER/ORG_ADMIN: can see engagements where organization_id in principal.org_ids
    - COORDINATOR/INST_ADMIN: can see engagements where institution_id in principal.institution_ids
    - All others: no engagements in scope (empty result)
    """
    if principal.kind == "TALENT" and principal.talent_id is not None:
        return select(Engagement).where(Engagement.talent_id == principal.talent_id)
    elif principal.kind in ("ORG_MEMBER", "ORG_ADMIN"):
        return select(Engagement).where(Engagement.organization_id.in_(principal.org_ids))
    elif principal.kind in ("COORDINATOR", "INST_ADMIN"):
        return select(Engagement).where(Engagement.institution_id.in_(principal.institution_ids))
    # All other kinds: no engagements in scope
    return select(Engagement).where(Engagement.id.in_([]))


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

    Implements AC-5, AC-6 (ownership), AC-S3 (admin excluded from PRIVATE)
    """
    if principal.kind == "TALENT" and principal.talent_id is not None:
        return select(Evidence).where(Evidence.owner_talent_id == principal.talent_id)
    # All other kinds (including admin): no evidence in scope
    return select(Evidence).where(Evidence.id.in_([]))


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
