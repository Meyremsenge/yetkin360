"""
Admin directory endpoints (U1, U2, O1, O4, I1): users, organizations, institutions.

Same gate as app/api/admin.py — router-level `require_platform_admin` (non-admin 404,
anonymous / suspended 401). Target ids come only from the path, the actor only from the session;
request bodies carry no identity. `q` is never logged (it may be an e-mail address).
"""

import uuid
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.admin import MAX_PAGE_SIZE, require_platform_admin
from app.api.deps import get_current_principal, get_session, get_verified_principal
from app.core.deps import require_csrf
from app.core.errors import ApiError
from app.models import Institution, Organization, User
from app.services import admin_directory as svc
from app.services.authorization import Principal

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_platform_admin)])

UserStatus = Literal["PENDING", "ACTIVE", "SUSPENDED", "DELETED"]
TenantStatus = Literal["ACTIVE", "SUSPENDED"]
VerificationLevel = Literal["T1", "T2", "T3", "T4"]


# ============================================================================
# Schemas
# ============================================================================


class AdminUserItem(BaseModel):
    id: uuid.UUID
    email: str
    status: str
    is_platform_admin: bool
    email_verified: bool
    created_at: datetime

    @classmethod
    def from_user(cls, user: User) -> "AdminUserItem":
        return cls(
            id=user.id,
            email=user.email,
            status=user.status,
            is_platform_admin=user.is_platform_admin,
            email_verified=user.email_verified_at is not None,
            created_at=user.created_at,
        )


class AdminOrganizationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    legal_id: Optional[str]
    domain: Optional[str]
    verification_level: str
    verified_at: Optional[datetime]
    status: str
    created_at: datetime


class AdminInstitutionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    domain: Optional[str]
    verification_level: str
    status: str
    created_at: datetime


class AdminUserList(BaseModel):
    items: list[AdminUserItem]
    limit: int
    offset: int
    has_more: bool


class AdminOrganizationList(BaseModel):
    items: list[AdminOrganizationItem]
    limit: int
    offset: int
    has_more: bool


class AdminInstitutionList(BaseModel):
    items: list[AdminInstitutionItem]
    limit: int
    offset: int
    has_more: bool


class InstitutionVerificationLevelUpdate(BaseModel):
    verification_level: VerificationLevel
    note: Optional[str] = Field(None, max_length=1000)


def _call(fn, *args, **kwargs):  # type: ignore[no-untyped-def]
    """Map service errors to the HTTP contract (404 for both non-admin and missing target)."""
    try:
        return fn(*args, **kwargs)
    except (svc.NotPlatformAdminError, svc.NotFoundError):
        raise ApiError(404, "NOT_FOUND", "Kaynak bulunamadı.")
    except svc.LastAdminProtectedError:
        raise ApiError(
            409,
            "LAST_ADMIN_PROTECTED",
            "Kendi hesabınızı veya son aktif platform yöneticisini askıya alamazsınız.",
        )


# ============================================================================
# U1 / U2 — users
# ============================================================================


@router.get("/users", response_model=AdminUserList)
def list_users_endpoint(
    q: Optional[str] = Query(None, max_length=200),
    status: Optional[UserStatus] = None,
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> AdminUserList:
    page = _call(svc.list_users, session, principal, q=q, status=status, limit=limit, offset=offset)
    return AdminUserList(
        items=[AdminUserItem.from_user(u) for u in page.items], limit=limit, offset=offset, has_more=page.has_more
    )


def _user_write(user_id: uuid.UUID, suspended: bool, principal: Principal, session: Session) -> AdminUserItem:
    user = _call(svc.set_user_suspended, session, principal, user_id, suspended=suspended)
    return AdminUserItem.from_user(user)


@router.post("/users/{user_id}/suspend", response_model=AdminUserItem)
def suspend_user_endpoint(
    user_id: uuid.UUID,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> AdminUserItem:
    return _user_write(user_id, True, principal, session)


@router.post("/users/{user_id}/reactivate", response_model=AdminUserItem)
def reactivate_user_endpoint(
    user_id: uuid.UUID,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> AdminUserItem:
    return _user_write(user_id, False, principal, session)


# ============================================================================
# O1 / O4 — organizations
# ============================================================================


@router.get("/organizations", response_model=AdminOrganizationList)
def list_organizations_endpoint(
    q: Optional[str] = Query(None, max_length=200),
    verification_level: Optional[VerificationLevel] = None,
    status: Optional[TenantStatus] = None,
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> AdminOrganizationList:
    page = _call(
        svc.list_organizations,
        session,
        principal,
        q=q,
        verification_level=verification_level,
        status=status,
        limit=limit,
        offset=offset,
    )
    return AdminOrganizationList(
        items=[AdminOrganizationItem.model_validate(o) for o in page.items],
        limit=limit,
        offset=offset,
        has_more=page.has_more,
    )


def _org_write(org_id: uuid.UUID, suspended: bool, principal: Principal, session: Session) -> AdminOrganizationItem:
    org: Organization = _call(svc.set_organization_suspended, session, principal, org_id, suspended=suspended)
    return AdminOrganizationItem.model_validate(org)


@router.post("/organizations/{organization_id}/suspend", response_model=AdminOrganizationItem)
def suspend_organization_endpoint(
    organization_id: uuid.UUID,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> AdminOrganizationItem:
    return _org_write(organization_id, True, principal, session)


@router.post("/organizations/{organization_id}/reactivate", response_model=AdminOrganizationItem)
def reactivate_organization_endpoint(
    organization_id: uuid.UUID,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> AdminOrganizationItem:
    return _org_write(organization_id, False, principal, session)


# ============================================================================
# I1 — institutions
# ============================================================================


@router.get("/institutions", response_model=AdminInstitutionList)
def list_institutions_endpoint(
    q: Optional[str] = Query(None, max_length=200),
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> AdminInstitutionList:
    page = _call(svc.list_institutions, session, principal, q=q, limit=limit, offset=offset)
    return AdminInstitutionList(
        items=[AdminInstitutionItem.model_validate(i) for i in page.items],
        limit=limit,
        offset=offset,
        has_more=page.has_more,
    )


@router.post("/institutions/{institution_id}/verification-level", response_model=AdminInstitutionItem)
def update_institution_verification_level(
    institution_id: uuid.UUID,
    payload: InstitutionVerificationLevelUpdate,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> AdminInstitutionItem:
    inst: Institution = _call(
        svc.set_institution_verification_level,
        session,
        principal,
        institution_id,
        payload.verification_level,
        len(payload.note or ""),
    )
    return AdminInstitutionItem.model_validate(inst)


def _inst_write(inst_id: uuid.UUID, suspended: bool, principal: Principal, session: Session) -> AdminInstitutionItem:
    inst: Institution = _call(svc.set_institution_suspended, session, principal, inst_id, suspended=suspended)
    return AdminInstitutionItem.model_validate(inst)


@router.post("/institutions/{institution_id}/suspend", response_model=AdminInstitutionItem)
def suspend_institution_endpoint(
    institution_id: uuid.UUID,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> AdminInstitutionItem:
    return _inst_write(institution_id, True, principal, session)


@router.post("/institutions/{institution_id}/reactivate", response_model=AdminInstitutionItem)
def reactivate_institution_endpoint(
    institution_id: uuid.UUID,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> AdminInstitutionItem:
    return _inst_write(institution_id, False, principal, session)
