"""FastAPI dependencies (database session, authentication context)."""

from typing import Generator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models import InstitutionMember, OrganizationMember, TalentProfile, User
from app.services.authorization import Principal

# TEMPORARY: YET-4 (real JWT auth) will replace this.
# Right now, X-Debug-User-Id header is used for testing and local dev.

# Database session factory
from sqlalchemy import create_engine

_engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency: returns database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_principal(
    x_debug_user_id: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> Principal:
    """
    Build Principal from debug header (user_id) and database state.

    TEMPORARY: YET-4 will replace with real JWT/token validation.

    For now, reads X-Debug-User-Id header (test-only mechanism) and constructs
    a real Principal by querying database for the user's organization/institution
    memberships and talent profile.

    If header missing or user not found → 401 Unauthorized.
    """
    if not x_debug_user_id:
        raise HTTPException(status_code=401, detail="Missing X-Debug-User-Id header")

    try:
        user_id = x_debug_user_id  # Assume it's already a valid UUID string
        user = session.query(User).filter_by(id=user_id).first()
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid X-Debug-User-Id")

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Determine user's organization memberships
    org_memberships = session.query(OrganizationMember).filter_by(user_id=user.id).all()
    org_ids = [m.organization_id for m in org_memberships]
    org_admin_ids = [m.organization_id for m in org_memberships if m.role == "ADMIN"]

    # Determine user's institution memberships
    institution_memberships = session.query(InstitutionMember).filter_by(user_id=user.id).all()
    institution_ids = [m.institution_id for m in institution_memberships]
    institution_admin_ids = [m.institution_id for m in institution_memberships if m.role == "ADMIN"]

    # Determine user's talent profile
    talent = session.query(TalentProfile).filter_by(user_id=user.id).first()
    talent_id = talent.id if talent else None

    # Infer kind based on memberships/profile (highest privilege level)
    if institution_admin_ids:
        kind = "INST_ADMIN"
    elif institution_ids:
        kind = "COORDINATOR"
    elif org_admin_ids:
        kind = "ORG_ADMIN"
    elif org_ids:
        kind = "ORG_MEMBER"
    elif talent_id:
        kind = "TALENT"
    else:
        kind = "USER"

    return Principal(
        user_id=user.id,
        kind=kind,
        talent_id=talent_id,
        org_ids=org_ids,
        org_admin_ids=org_admin_ids,
        institution_ids=institution_ids,
        institution_admin_ids=institution_admin_ids,
        is_platform_admin=False,
        is_suspended=user.status == "SUSPENDED",
    )
