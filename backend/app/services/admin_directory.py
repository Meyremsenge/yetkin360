"""
Admin directory (U1, U2, O1, O4, I1): list/search users, organizations and institutions;
suspend/reactivate them; set an institution's verification level.

Platform-admin only. The router gate (require_platform_admin) is the boundary; every function
here re-checks `principal.is_platform_admin` (default-deny) because these queries are
deliberately NOT tenant-scoped. Each write and its audit row share the caller's transaction —
nothing here commits, so a failed audit rolls the change back (get_session).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Generic, TypeVar

from sqlalchemy import Select, or_, select, update
from sqlalchemy.orm import Session

from app.models import Institution, Organization, RefreshToken, User
from app.services.audit import log_audit_event
from app.services.authorization import Principal

T = TypeVar("T")


class NotPlatformAdminError(Exception):
    """Caller is not a platform admin (router maps to 404)."""


class NotFoundError(Exception):
    """Target does not exist, or is deleted."""


class LastAdminProtectedError(Exception):
    """Suspending would lock the actor out, or leave no active platform admin."""


@dataclass
class Page(Generic[T]):
    items: list[T]
    has_more: bool


def _require_admin(principal: Principal) -> None:
    if not principal.is_platform_admin or principal.user_id is None:
        raise NotPlatformAdminError()


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _contains(term: str) -> str:
    return f"%{_escape_like(term)}%"


def _page(session: Session, stmt: Select, limit: int, offset: int) -> Page:
    rows = list(session.execute(stmt.offset(offset).limit(limit + 1)).scalars().all())
    return Page(items=rows[:limit], has_more=len(rows) > limit)


# ============================================================================
# Lists
# ============================================================================


def list_users(
    session: Session, principal: Principal, *, q: str | None, status: str | None, limit: int, offset: int
) -> Page[User]:
    _require_admin(principal)
    stmt = select(User)
    if q:
        stmt = stmt.where(User.email.ilike(_contains(q), escape="\\"))
    if status:
        stmt = stmt.where(User.status == status)
    return _page(session, stmt.order_by(User.created_at.desc(), User.id), limit, offset)


def list_organizations(
    session: Session,
    principal: Principal,
    *,
    q: str | None,
    verification_level: str | None,
    status: str | None,
    limit: int,
    offset: int,
) -> Page[Organization]:
    _require_admin(principal)
    stmt = select(Organization).where(Organization.deleted_at.is_(None))
    if q:
        pattern = _contains(q)
        stmt = stmt.where(
            or_(
                Organization.name.ilike(pattern, escape="\\"),
                Organization.domain.ilike(pattern, escape="\\"),
                Organization.legal_id.ilike(pattern, escape="\\"),
            )
        )
    if verification_level:
        stmt = stmt.where(Organization.verification_level == verification_level)
    if status:
        stmt = stmt.where(Organization.status == status)
    return _page(session, stmt.order_by(Organization.created_at.desc(), Organization.id), limit, offset)


def list_institutions(
    session: Session, principal: Principal, *, q: str | None, limit: int, offset: int
) -> Page[Institution]:
    _require_admin(principal)
    stmt = select(Institution)
    if q:
        pattern = _contains(q)
        stmt = stmt.where(
            or_(Institution.name.ilike(pattern, escape="\\"), Institution.domain.ilike(pattern, escape="\\"))
        )
    return _page(session, stmt.order_by(Institution.created_at.desc(), Institution.id), limit, offset)


# ============================================================================
# Users: suspend / reactivate
# ============================================================================


def set_user_suspended(session: Session, principal: Principal, user_id: uuid.UUID, *, suspended: bool) -> User:
    """
    Idempotent: a user already in the requested state is returned unchanged, with no audit row.
    Suspending revokes the user's live refresh tokens so a later reactivation does not revive
    old sessions (access tokens are already refused by get_current_user for SUSPENDED).
    """
    _require_admin(principal)
    target = session.execute(
        select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True)
    ).scalars().first()
    if target is None or target.status == "DELETED" or target.deleted_at is not None:
        raise NotFoundError()

    if suspended:
        if target.status == "SUSPENDED":
            return target
        if target.id == principal.user_id:
            raise LastAdminProtectedError()
        if target.is_platform_admin:
            _ensure_other_active_admin_remains(session, principal, target.id)
        target.status = "SUSPENDED"
        session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == target.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        action = "ADMIN_SUSPEND_USER"
    else:
        if target.status != "SUSPENDED":
            return target
        target.status = "ACTIVE"
        action = "ADMIN_REACTIVATE_USER"

    session.flush()
    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=None,
        action=action,
        subject_type="user",
        subject_id=target.id,
        result="SUCCESS",
        metadata={"status": target.status},
    )
    return target


def _ensure_other_active_admin_remains(session: Session, principal: Principal, target_id: uuid.UUID) -> None:
    """
    Lock every active platform admin row (stable order), then re-read: the actor must still be an
    active admin and someone other than the target must stay active. Two admins suspending each
    other concurrently therefore cannot end with zero admins.
    """
    active = session.execute(
        select(User)
        .where(User.is_platform_admin.is_(True), User.status == "ACTIVE", User.deleted_at.is_(None))
        .order_by(User.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalars().all()
    active_ids = {u.id for u in active}
    if principal.user_id not in active_ids or not (active_ids - {target_id}):
        raise LastAdminProtectedError()


# ============================================================================
# Organizations / institutions: suspend / reactivate, verification level
# ============================================================================


def set_organization_suspended(
    session: Session, principal: Principal, organization_id: uuid.UUID, *, suspended: bool
) -> Organization:
    _require_admin(principal)
    org = session.execute(
        select(Organization).where(Organization.id == organization_id).with_for_update()
    ).scalars().first()
    if org is None or org.deleted_at is not None:
        raise NotFoundError()
    if not _toggle_status(org, suspended):
        return org
    session.flush()
    _audit_status(session, principal, "ORGANIZATION", "organization", org.id, suspended)
    return org


def set_institution_suspended(
    session: Session, principal: Principal, institution_id: uuid.UUID, *, suspended: bool
) -> Institution:
    _require_admin(principal)
    inst = session.execute(
        select(Institution).where(Institution.id == institution_id).with_for_update()
    ).scalars().first()
    if inst is None:
        raise NotFoundError()
    if not _toggle_status(inst, suspended):
        return inst
    session.flush()
    _audit_status(session, principal, "INSTITUTION", "institution", inst.id, suspended)
    return inst


def set_institution_verification_level(
    session: Session, principal: Principal, institution_id: uuid.UUID, verification_level: str, note_length: int
) -> Institution:
    _require_admin(principal)
    inst = session.execute(
        select(Institution).where(Institution.id == institution_id).with_for_update()
    ).scalars().first()
    if inst is None:
        raise NotFoundError()
    if inst.verification_level == verification_level:
        return inst
    previous = inst.verification_level
    inst.verification_level = verification_level
    session.flush()
    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=None,
        action="ADMIN_SET_INSTITUTION_VERIFICATION_LEVEL",
        subject_type="institution",
        subject_id=inst.id,
        result="SUCCESS",
        metadata={"from": previous, "to": verification_level, "note_length": note_length},
    )
    return inst


def _toggle_status(row: Organization | Institution, suspended: bool) -> bool:
    """Returns False when the row is already in the requested state (idempotent no-op)."""
    if suspended:
        if row.status == "SUSPENDED":
            return False
        row.status = "SUSPENDED"
    else:
        if row.status != "SUSPENDED":
            return False
        row.status = "ACTIVE"
    return True


def _audit_status(
    session: Session, principal: Principal, noun: str, subject_type: str, subject_id: uuid.UUID, suspended: bool
) -> None:
    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=None,
        action=f"ADMIN_{'SUSPEND' if suspended else 'REACTIVATE'}_{noun}",
        subject_type=subject_type,
        subject_id=subject_id,
        result="SUCCESS",
        metadata={"status": "SUSPENDED" if suspended else "ACTIVE"},
    )
