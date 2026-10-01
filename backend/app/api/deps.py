"""FastAPI dependencies (database session, authentication context)."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.deps import get_session as core_get_session
from app.core.deps import get_current_user, require_email_verified
from app.models import InstitutionMember, OrganizationMember, TalentProfile, User
from app.services.authorization import Principal

# Re-export get_session from core.deps (real database session factory)
get_session = core_get_session


def get_current_principal(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Principal:
    """
    Build Principal from authenticated user and database state.

    Uses real JWT authentication (httpOnly cookie) via get_current_user
    from app.core.deps. Constructs Principal by querying database for
    the user's organization/institution memberships and talent profile.

    User is already authenticated at this point. Returns 401 if not.
    """
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

    # Infer kind based on memberships/profile (highest privilege level, display only)
    # Note: kind is display-only and never used in authorization decisions (AC-6);
    # authorization uses membership ID lists (org_ids, org_admin_ids, etc.)
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
        is_platform_admin=user.is_platform_admin,
        is_suspended=user.status == "SUSPENDED",
    )


def get_verified_principal(
    _verified: User = Depends(require_email_verified),
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    """
    get_current_principal for WRITE endpoints (docs/AUTHORIZATION.md G6).

    Unauthenticated -> 401 UNAUTHENTICATED; authenticated but unverified e-mail
    -> 401 EMAIL_NOT_VERIFIED. The check runs before the principal is built,
    so it also precedes every resource lookup (no existence leak). Read
    endpoints, /auth/logout and /auth/refresh keep using get_current_principal
    / get_current_user.
    """
    return principal
