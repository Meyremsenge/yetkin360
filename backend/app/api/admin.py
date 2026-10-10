"""Admin endpoints (PLAN 3.6 — YET-110/136/137/138/139): kurum doğrulama kuyruğu + skill yönetimi.

Tümü `ADMIN` yetkisi gerektirir (`users.is_platform_admin = true`, docs/API.md §2.10).
Yetkisiz istekte 404 dönülür (CLAUDE.md: 403 kaynağın/ucun varlığını sızdırır) —
app/api/organizations.py'deki ORG:ADMIN kontrolüyle aynı desen.

Kontrol router seviyesindedir (`require_platform_admin`): bu dosyaya eklenen
her uç onu kendiliğinden alır, uç içinde ayrıca çağırmak gerekmez.
"""

import uuid
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import _client_ip
from app.api.deps import get_current_principal, get_session, get_verified_principal
from app.core.deps import get_current_user, require_csrf, require_email_verified
from app.core.errors import ApiError
from app.models import User
from app.services.audit import log_audit_event
from app.services.authorization import Principal
from app.services.complaint import upheld_complaint_counts
from app.services.fraud_flag import NotPendingError as FraudFlagNotPendingError, list_fraud_queue, resolve_fraud_flag
from app.services.fraud_signals import subject_labels
from app.services.organization import (
    DomainAlreadyVerifiedError,
    NotPendingError,
    list_verification_queue,
    reject_verification,
    set_verification_level,
)
from app.services.skill import (
    DuplicateSkillSlugError,
    InvalidSkillReferenceError,
    SkillStatusTransitionError,
    create_skill,
    deprecate_skill,
    list_all_skills,
    merge_skill,
    update_skill,
)

MAX_PAGE_SIZE = 200

def require_platform_admin(
    request: Request,
    user: User = Depends(get_current_user),
    principal: Principal = Depends(get_current_principal),
) -> None:
    """
    Router-level gate for every /admin/* route: non-admins get 404, not 403.

    Order is unchanged from the per-handler checks it replaces: on a write, an
    unverified e-mail is answered first (401 EMAIL_NOT_VERIFIED, AUTHORIZATION G6),
    then the admin check.
    """
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        require_email_verified(user)
    if not principal.is_platform_admin:
        raise ApiError(404, "NOT_FOUND", "Kaynak bulunamadı.")


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_platform_admin)])

VerificationLevel = Literal["T1", "T2", "T3", "T4"]
SkillCategory = Literal["LANGUAGE", "FRAMEWORK", "TOOL", "DOMAIN", "SOFT"]


# ============================================================================
# Pydantic Schemas
# ============================================================================


class VerificationQueueItem(BaseModel):
    id: uuid.UUID
    name: str
    legal_id: Optional[str]
    domain: Optional[str]
    verification_level: str
    created_at: datetime
    upheld_complaint_count: int = 0  # admin-upheld complaints (sikayet-backend C7)

    class Config:
        from_attributes = True


class VerificationQueueResponse(BaseModel):
    items: list[VerificationQueueItem]
    limit: int
    offset: int
    has_more: bool


class VerificationLevelUpdate(BaseModel):
    verification_level: VerificationLevel
    note: Optional[str] = Field(None, max_length=1000)


class VerificationReject(BaseModel):
    note: Optional[str] = Field(None, max_length=1000)


class OrganizationSummary(BaseModel):
    id: uuid.UUID
    name: str
    verification_level: str
    verified_at: Optional[datetime]

    class Config:
        from_attributes = True


class SkillCreateRequest(BaseModel):
    slug: str = Field(..., min_length=1, max_length=100)
    name_tr: str = Field(..., min_length=1)
    name_en: Optional[str] = None
    category: SkillCategory
    parent_id: Optional[uuid.UUID] = None


class SkillUpdateRequest(BaseModel):
    name_tr: Optional[str] = Field(None, min_length=1)
    name_en: Optional[str] = None
    category: Optional[SkillCategory] = None
    parent_id: Optional[uuid.UUID] = None
    status: Optional[Literal["ACTIVE", "DEPRECATED"]] = None  # AC-13: status transitions


class SkillMergeRequest(BaseModel):
    merged_into_id: uuid.UUID


class SkillResponse(BaseModel):
    id: uuid.UUID
    slug: str
    name_tr: str
    name_en: Optional[str]
    category: str
    parent_id: Optional[uuid.UUID]
    status: str
    merged_into_id: Optional[uuid.UUID]

    class Config:
        from_attributes = True


class SkillsListResponse(BaseModel):
    items: list[SkillResponse]
    limit: int
    offset: int
    has_more: bool


class FraudFlagItem(BaseModel):
    """PLAN 3.54: AI-generated flag — reason/confidence are the model's output,
    never a verdict; subject_id/subject_type let the admin open the attestation.
    PLAN 3.56: `signal` is the rule/check code (null for 3.54 statement flags);
    `subject_label` is the organization/institution name, when the subject is one."""

    id: uuid.UUID
    subject_type: str
    subject_id: uuid.UUID
    subject_label: str | None = None
    signal: str | None = None
    reason: str
    confidence: Literal["LOW", "MEDIUM", "HIGH"]
    model: str
    created_at: datetime

    class Config:
        from_attributes = True


class FraudQueueResponse(BaseModel):
    items: list[FraudFlagItem]
    limit: int
    offset: int
    has_more: bool


class FraudFlagResolveRequest(BaseModel):
    outcome: Literal["CONFIRMED", "DISMISSED"]


# ============================================================================
# Kurum doğrulama kuyruğu (YET-136)
# ============================================================================


@router.get("/verification-queue", response_model=VerificationQueueResponse)
def get_verification_queue(
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> VerificationQueueResponse:
    """docs/API.md §2.10: T2 + legal_id dolu kurumlar (T3 başvurusu sayılır)."""
    orgs, has_more = list_verification_queue(session, limit=limit, offset=offset)
    upheld = upheld_complaint_counts(session, "ORGANIZATION", [o.id for o in orgs])
    return VerificationQueueResponse(
        items=[
            VerificationQueueItem.model_validate(o).model_copy(update={"upheld_complaint_count": upheld.get(o.id, 0)})
            for o in orgs
        ],
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.post("/organizations/{organization_id}/verification-level", response_model=OrganizationSummary)
def update_verification_level(
    request: Request,
    organization_id: uuid.UUID,
    payload: VerificationLevelUpdate,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> OrganizationSummary:
    """
    Seviyeyi ayarla (onay = yükseltme). Reddetmek için verification-reject ucu kullanılır.
    Her çağrı audit_events'e yazılır; serbest metin `note` yazılmaz, yalnız uzunluğu.
    """

    try:
        org = set_verification_level(
            session,
            organization_id=organization_id,
            verification_level=payload.verification_level,
            admin_user_id=principal.user_id,
        )
    except DomainAlreadyVerifiedError:
        raise ApiError(409, "DOMAIN_ALREADY_VERIFIED", "Alan adı başka bir kurumda doğrulanmış.")
    if org is None:
        raise ApiError(404, "NOT_FOUND", "Kurum bulunamadı.")

    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=_client_ip(request),
        action="ADMIN_SET_VERIFICATION_LEVEL",
        subject_type="organization",
        subject_id=organization_id,
        result="SUCCESS",
        metadata={
            "verification_level": payload.verification_level,
            "note_length": len(payload.note or ""),
        },
    )

    return OrganizationSummary.model_validate(org)


@router.post("/organizations/{organization_id}/verification-reject", response_model=OrganizationSummary)
def reject_verification_endpoint(
    request: Request,
    organization_id: uuid.UUID,
    payload: VerificationReject,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> OrganizationSummary:
    """Bekleyen T3 başvurusunu reddet: kurum kuyruktan çıkar, seviye ve verified_at değişmez (YET-198)."""

    try:
        org = reject_verification(session, organization_id=organization_id)
    except NotPendingError:
        raise ApiError(409, "NOT_PENDING", "Kurum doğrulama kuyruğunda değil.")
    if org is None:
        raise ApiError(404, "NOT_FOUND", "Kurum bulunamadı.")

    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=_client_ip(request),
        action="ADMIN_REJECT_VERIFICATION",
        subject_type="organization",
        subject_id=organization_id,
        result="SUCCESS",
        metadata={"note_length": len(payload.note or "")},
    )

    return OrganizationSummary.model_validate(org)


# ============================================================================
# Skill taksonomi yönetimi (YET-137)
# ============================================================================


@router.get("/skills", response_model=SkillsListResponse)
def list_skills_endpoint(
    limit: int = Query(200, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> SkillsListResponse:
    """Admin taksonomi yönetimi için TÜM skill'leri (durumdan bağımsız) listeler."""
    skills, has_more = list_all_skills(session, limit=limit, offset=offset)
    return SkillsListResponse(
        items=[SkillResponse.model_validate(s) for s in skills],
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.post("/skills", response_model=SkillResponse, status_code=201)
def create_skill_endpoint(
    request: Request,
    payload: SkillCreateRequest,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> SkillResponse:
    try:
        skill = create_skill(
            session,
            slug=payload.slug,
            name_tr=payload.name_tr,
            name_en=payload.name_en,
            category=payload.category,
            parent_id=payload.parent_id,
        )
    except DuplicateSkillSlugError:
        raise ApiError(409, "CONFLICT", "Bu slug zaten kullanımda.")
    except InvalidSkillReferenceError as exc:
        raise ApiError(422, "VALIDATION_ERROR", str(exc))

    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=_client_ip(request),
        action="ADMIN_CREATE_SKILL",
        subject_type="skill",
        subject_id=skill.id,
        result="SUCCESS",
        metadata={"slug": skill.slug, "category": skill.category},
    )
    return SkillResponse.model_validate(skill)


@router.patch("/skills/{skill_id}", response_model=SkillResponse)
def update_skill_endpoint(
    request: Request,
    skill_id: uuid.UUID,
    payload: SkillUpdateRequest,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> SkillResponse:
    try:
        skill = update_skill(
            session,
            skill_id=skill_id,
            name_tr=payload.name_tr,
            name_en=payload.name_en,
            category=payload.category,
            parent_id=payload.parent_id,
            status=payload.status,
        )
    except InvalidSkillReferenceError as exc:
        raise ApiError(422, "VALIDATION_ERROR", str(exc))
    except SkillStatusTransitionError as exc:
        raise ApiError(409, "CONFLICT", str(exc))

    if skill is None:
        raise ApiError(404, "NOT_FOUND", "Skill bulunamadı.")

    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=_client_ip(request),
        action="ADMIN_UPDATE_SKILL",
        subject_type="skill",
        subject_id=skill_id,
        result="SUCCESS",
        metadata=None,
    )
    return SkillResponse.model_validate(skill)


@router.post("/skills/{skill_id}/deprecate", response_model=SkillResponse)
def deprecate_skill_endpoint(
    request: Request,
    skill_id: uuid.UUID,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> SkillResponse:
    skill = deprecate_skill(session, skill_id)
    if skill is None:
        raise ApiError(404, "NOT_FOUND", "Skill bulunamadı.")

    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=_client_ip(request),
        action="ADMIN_DEPRECATE_SKILL",
        subject_type="skill",
        subject_id=skill_id,
        result="SUCCESS",
        metadata=None,
    )
    return SkillResponse.model_validate(skill)


@router.post("/skills/{skill_id}/merge", response_model=SkillResponse)
def merge_skill_endpoint(
    request: Request,
    skill_id: uuid.UUID,
    payload: SkillMergeRequest,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> SkillResponse:
    try:
        skill = merge_skill(session, skill_id, payload.merged_into_id)
    except InvalidSkillReferenceError as exc:
        raise ApiError(422, "VALIDATION_ERROR", str(exc))

    if skill is None:
        raise ApiError(404, "NOT_FOUND", "Skill bulunamadı.")

    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=_client_ip(request),
        action="ADMIN_MERGE_SKILL",
        subject_type="skill",
        subject_id=skill_id,
        result="SUCCESS",
        metadata={"merged_into_id": str(payload.merged_into_id)},
    )
    return SkillResponse.model_validate(skill)


# ============================================================================
# Fraud flag kuyruğu (PLAN 3.54) — AI işaretler, admin karar verir
# ============================================================================


@router.get("/fraud-queue", response_model=FraudQueueResponse)
def get_fraud_queue(
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> FraudQueueResponse:
    """PENDING fraud_flags — AI'nin ürettiği işaretler, henüz admin kararı yok."""
    flags, has_more = list_fraud_queue(session, limit=limit, offset=offset)
    labels = subject_labels(session, flags)
    return FraudQueueResponse(
        items=[
            FraudFlagItem.model_validate(f).model_copy(update={"subject_label": labels.get(f.id)}) for f in flags
        ],
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.post("/fraud-queue/{flag_id}/resolve", response_model=FraudFlagItem)
def resolve_fraud_flag_endpoint(
    request: Request,
    flag_id: uuid.UUID,
    payload: FraudFlagResolveRequest,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> FraudFlagItem:
    """Admin kararı: CONFIRMED (gerçek sahtekarlık) veya DISMISSED (yanlış alarm)."""

    try:
        flag = resolve_fraud_flag(
            session,
            flag_id=flag_id,
            outcome=payload.outcome,
            admin_user_id=principal.user_id,
        )
    except FraudFlagNotPendingError:
        raise ApiError(409, "NOT_PENDING", "Bu işaret zaten incelenmiş.")
    if flag is None:
        raise ApiError(404, "NOT_FOUND", "İşaret bulunamadı.")

    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=_client_ip(request),
        action="ADMIN_RESOLVE_FRAUD_FLAG",
        subject_type="fraud_flag",
        subject_id=flag_id,
        result="SUCCESS",
        metadata={"outcome": payload.outcome},
    )
    return FraudFlagItem.model_validate(flag)
