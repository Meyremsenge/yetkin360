"""Portfolio item endpoints (/talents/me/portfolio-items) — the owner's certificate/work showcase.

docs/arastirma-ogrenci-profili.md §4.3. Ownership always comes from the session;
another talent's item, an unknown id and a talent-less caller answer an identical 404.
"""

import uuid
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, get_session, get_verified_principal
from app.core.deps import require_csrf
from app.core.errors import ApiError
from app.services.authorization import Principal
from app.services.portfolio import (
    PortfolioEvidenceAlreadyLinkedError,
    PortfolioEvidenceNotFoundError,
    PortfolioLimitReachedError,
    create_own_portfolio_item,
    delete_own_portfolio_item,
    https_host,
    list_own_portfolio,
    update_own_portfolio_item,
)

router = APIRouter(prefix="/talents/me/portfolio-items", tags=["portfolio-items"])


# ============================================================================
# Pydantic Schemas (Request/Response DTOs)
# ============================================================================


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class _PortfolioFields(BaseModel):
    """Shared validation; the DB CHECK constraints mirror every rule here."""

    @field_validator("title", check_fields=False)
    @classmethod
    def validate_title(cls, v):
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("title boş olamaz")
        return v

    @field_validator("issuer", "credential_id", check_fields=False)
    @classmethod
    def strip_text(cls, v):
        return _clean_optional_text(v)

    @field_validator("external_url", check_fields=False)
    @classmethod
    def validate_external_url(cls, v):
        v = _clean_optional_text(v)
        if v is not None and https_host(v) is None:
            raise ValueError("external_url yalnız https:// ile başlayan geçerli bir adres olabilir")
        return v

    @field_validator("issued_on", check_fields=False)
    @classmethod
    def validate_issued_on(cls, v):
        if v is not None and v > datetime.now(timezone.utc).date():
            raise ValueError("issued_on gelecekte olamaz")
        return v


class CreatePortfolioItemRequest(_PortfolioFields):
    kind: Literal["CERTIFICATE", "WORK"]
    title: str = Field(..., max_length=120)
    issuer: str | None = Field(None, max_length=120)
    issued_on: date | None = None
    credential_id: str | None = Field(None, max_length=100)
    external_url: str | None = Field(None, max_length=500)
    evidence_id: uuid.UUID | None = None
    show_on_profile: bool = False


class UpdatePortfolioItemRequest(_PortfolioFields):
    kind: Literal["CERTIFICATE", "WORK"] | None = None
    title: str | None = Field(None, max_length=120)
    issuer: str | None = Field(None, max_length=120)
    issued_on: date | None = None
    credential_id: str | None = Field(None, max_length=100)
    external_url: str | None = Field(None, max_length=500)
    show_on_profile: bool | None = None


class PortfolioItemResponse(BaseModel):
    id: uuid.UUID
    kind: str
    title: str
    issuer: str | None
    issued_on: date | None
    credential_id: str | None
    external_url: str | None
    evidence_id: uuid.UUID | None
    show_on_profile: bool
    # Derived on the server: COORDINATOR_CONFIRMED | COORDINATOR_REJECTED | SELF_DECLARED
    badge: str
    provider: str | None
    created_at: datetime


class EngagementCertificateResponse(BaseModel):
    """A certificate uploaded inside an engagement, candidate for the showcase."""

    evidence_id: uuid.UUID
    created_at: datetime
    provider: str | None
    credential_id: str | None
    # Official page's course name, else the one read off the certificate (default showcase title)
    course_name: str | None
    # None: no check requested yet; otherwise PENDING | CONFIRMED | REJECTED
    decision: str | None
    portfolio_item_id: uuid.UUID | None


class PortfolioListResponse(BaseModel):
    items: list[PortfolioItemResponse]
    engagement_certificates: list[EngagementCertificateResponse]


# Fields that may be cleared with an explicit null; the others are NOT NULL.
_REQUIRED_ON_UPDATE = {"kind", "title", "show_on_profile"}


def _not_found() -> ApiError:
    return ApiError(status_code=404, code="PORTFOLIO_ITEM_NOT_FOUND", message="Kayıt bulunamadı")


# ============================================================================
# Routes
# ============================================================================


@router.get("", response_model=PortfolioListResponse)
def get_portfolio_items(
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> PortfolioListResponse:
    """The caller's own items (any consent state) and engagement certificates. Talent-less → empty."""
    return PortfolioListResponse(**list_own_portfolio(session, principal))


@router.post("", response_model=PortfolioItemResponse, status_code=201)
def post_portfolio_item(
    payload: CreatePortfolioItemRequest,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> PortfolioItemResponse:
    """
    Errors:
        404 EVIDENCE_NOT_FOUND: evidence_id is not the caller's own live evidence (or no talent profile)
        409 EVIDENCE_ALREADY_IN_PORTFOLIO: that evidence already backs another item
        409 PORTFOLIO_LIMIT_REACHED: already 50 live items
        422: validation (title, https-only external_url, future issued_on)
    """
    try:
        item = create_own_portfolio_item(session, principal, payload.model_dump())
    except PortfolioEvidenceNotFoundError:
        raise ApiError(status_code=404, code="EVIDENCE_NOT_FOUND", message="Kanıt bulunamadı.")
    except PortfolioEvidenceAlreadyLinkedError:
        raise ApiError(
            status_code=409,
            code="EVIDENCE_ALREADY_IN_PORTFOLIO",
            message="Bu kanıt zaten vitrininizde.",
        )
    except PortfolioLimitReachedError:
        raise ApiError(
            status_code=409,
            code="PORTFOLIO_LIMIT_REACHED",
            message="En fazla 50 kayıt ekleyebilirsiniz.",
        )
    session.commit()
    return PortfolioItemResponse(**item)


@router.patch("/{item_id}", response_model=PortfolioItemResponse)
def patch_portfolio_item(
    item_id: uuid.UUID,
    payload: UpdatePortfolioItemRequest,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> PortfolioItemResponse:
    """Update fields / "Profilde göster" consent. evidence_id cannot be changed."""
    updates = {}
    for field_name in payload.model_fields_set:
        value = getattr(payload, field_name)
        if value is None and field_name in _REQUIRED_ON_UPDATE:
            raise ApiError(
                status_code=422, code="FIELD_REQUIRED", message=f"{field_name} alanı boş bırakılamaz."
            )
        updates[field_name] = value

    item = update_own_portfolio_item(session, principal, item_id, updates)
    if item is None:
        raise _not_found()
    session.commit()
    return PortfolioItemResponse(**item)


@router.delete("/{item_id}", status_code=204)
def delete_portfolio_item(
    item_id: uuid.UUID,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> Response:
    """Soft delete; the linked evidence file stays (PRIVATE) and is not affected."""
    if not delete_own_portfolio_item(session, principal, item_id):
        raise _not_found()
    session.commit()
    return Response(status_code=204)
