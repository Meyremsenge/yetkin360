"""
Authorization core: Principal dataclass, can() function, scoped_*() queries, and get_scoped_or_404() helper.

Implements access control and data scoping per atdd.md (yet-2-yetkilendirme-cekirdegi).
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import Organization, TalentProfile, User


@dataclass
class Principal:
    """
    Represents the caller's authorization context.

    Fields:
      - user_id: UUID of the authenticated user (None for ANONYMOUS)
      - kind: Role/type of principal (str, plain values: "ANONYMOUS", "TALENT", "ORG_MEMBER", etc.)
      - talent_id: UUID of associated talent profile (if kind == "TALENT")
      - org_ids: List of organization IDs the principal is a member of
      - org_admin_ids: List of organization IDs the principal is an admin of
      - institution_ids: List of institution IDs the principal is associated with
      - is_platform_admin: True if principal is a platform administrator
      - is_suspended: True if principal's account is suspended
    """
    user_id: uuid.UUID | None
    kind: str
    talent_id: uuid.UUID | None
    org_ids: list[uuid.UUID]
    org_admin_ids: list[uuid.UUID]
    institution_ids: list[uuid.UUID]
    is_platform_admin: bool
    is_suspended: bool


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
        if action == "read" and principal.user_id == resource.id:
            return True
        return False

    # Handle Organization resource: can admin_update if principal is org admin
    if isinstance(resource, Organization):
        if action == "admin_update" and principal.kind == "ORG_ADMIN" and resource.id in principal.org_admin_ids:
            return True
        return False

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
    if principal.kind == "TALENT" and principal.user_id is not None:
        return select(TalentProfile).where(TalentProfile.user_id == principal.user_id)
    # All other kinds: no talent profiles in scope
    return select(TalentProfile).where(TalentProfile.id.in_([]))


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
