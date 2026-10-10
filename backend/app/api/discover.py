"""Keşfet directory endpoints (PLAN R.1, docs/kesfet-tasarim.md)."""

import uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_session, get_verified_principal
from app.core.config import settings
from app.core.errors import ApiError
from app.services import discover
from app.services.authorization import Principal
from app.services.rate_limit import RateLimitExceeded


def require_discover_enabled() -> None:
    """Kill switch: with the feature off the routes do not exist (404, before auth)."""
    if not settings.discover_enabled:
        raise ApiError(status_code=404, code="NOT_FOUND", message="Kayıt bulunamadı")


def _validation_error(fields: dict[str, str]) -> RequestValidationError:
    """422 in the same envelope as FastAPI's own validation errors (core/errors.py)."""
    return RequestValidationError(
        [{"loc": ("query", name), "msg": message, "type": "value_error"} for name, message in fields.items()]
    )


def _only_params(*allowed: str):
    """
    Reject unknown query parameters with 422. The directory's scope is fixed on
    the server; a client-sent `visibility`, `organization_id` or `role` must not
    be silently ignored (docs/kesfet-tasarim.md §4). Authentication is resolved
    first, so an anonymous caller always gets 401.
    """
    allowed_set = frozenset(allowed)

    def dependency(request: Request, _principal: Principal = Depends(get_verified_principal)) -> None:
        unknown = sorted(set(request.query_params) - allowed_set)
        if unknown:
            raise _validation_error({name: "Bilinmeyen parametre." for name in unknown})

    return dependency


router = APIRouter(prefix="/discover", tags=["discover"], dependencies=[Depends(require_discover_enabled)])


# ============================================================================
# Pydantic Response Schemas — allowlists; ORM models are never returned
# ============================================================================


class DiscoverTalentResponse(BaseModel):
    """Card in GET /discover/talents. No e-mail, no internal ids, no self-claimed skills."""

    public_slug: str
    full_name: str
    headline: str | None
    department: str | None
    city: str | None
    institution_name: str | None
    sealed_skills: list[str]
    verified_experience_count: int


class DiscoverTalentListResponse(BaseModel):
    items: list[DiscoverTalentResponse]
    next_cursor: str | None
    has_more: bool


class DiscoverOrganizationResponse(BaseModel):
    """Card in GET /discover/organizations. `domain` is null unless verified (T2+)."""

    id: uuid.UUID
    name: str
    verification_level: str
    domain: str | None


class DiscoverOrganizationListResponse(BaseModel):
    items: list[DiscoverOrganizationResponse]
    next_cursor: str | None
    has_more: bool


def _rate_limited(exc: RateLimitExceeded) -> ApiError:
    return ApiError(
        429,
        "RATE_LIMITED",
        "Çok fazla arama yapıldı. Lütfen biraz sonra tekrar deneyin.",
        headers={"Retry-After": str(exc.retry_after)},
    )


def _invalid_cursor() -> RequestValidationError:
    return _validation_error({"cursor": "Geçersiz sayfa imleci."})


@router.get(
    "/talents",
    response_model=DiscoverTalentListResponse,
    dependencies=[Depends(_only_params("q", "skill_id", "institution_id", "department", "city", "limit", "cursor"))],
)
def list_discover_talents(
    q: str | None = Query(None, min_length=2, max_length=64),
    skill_id: list[uuid.UUID] = Query(default_factory=list, max_length=discover.MAX_SKILL_FILTERS),
    institution_id: uuid.UUID | None = None,
    department: str | None = Query(None, min_length=1, max_length=100),
    city: str | None = Query(None, min_length=1, max_length=100),
    limit: int = Query(discover.DEFAULT_LIMIT, ge=1, le=discover.MAX_LIMIT),
    cursor: str | None = Query(None, max_length=512),
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
) -> DiscoverTalentListResponse:
    """
    List PUBLIC talent profiles (any authenticated, e-mail-verified user).

    Only profiles already readable anonymously at /p/{slug} are listed; an
    unknown skill_id / institution_id gives 200 + [] rather than 404.

    Errors: 401 (anonymous / EMAIL_NOT_VERIFIED), 422 (invalid or unknown
    parameter, bad cursor), 429 RATE_LIMITED (60/min/user).
    """
    try:
        page = discover.list_talents(
            session,
            principal,
            q=q,
            skill_ids=skill_id,
            institution_id=institution_id,
            department=department,
            city=city,
            limit=limit,
            cursor=cursor,
        )
    except RateLimitExceeded as exc:
        raise _rate_limited(exc)
    except discover.InvalidCursorError:
        raise _invalid_cursor()

    return DiscoverTalentListResponse(
        items=[DiscoverTalentResponse.model_validate(card, from_attributes=True) for card in page.items],
        next_cursor=page.next_cursor,
        has_more=page.next_cursor is not None,
    )


@router.get(
    "/organizations",
    response_model=DiscoverOrganizationListResponse,
    dependencies=[Depends(_only_params("q", "limit", "cursor"))],
)
def list_discover_organizations(
    q: str | None = Query(None, min_length=2, max_length=64),
    limit: int = Query(discover.DEFAULT_LIMIT, ge=1, le=discover.MAX_LIMIT),
    cursor: str | None = Query(None, max_length=512),
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
) -> DiscoverOrganizationListResponse:
    """
    List ACTIVE organizations (any authenticated, e-mail-verified user).

    Errors: 401, 422, 429 RATE_LIMITED (60/min/user, shared with /discover/talents).
    """
    try:
        page = discover.list_organizations(session, principal, q=q, limit=limit, cursor=cursor)
    except RateLimitExceeded as exc:
        raise _rate_limited(exc)
    except discover.InvalidCursorError:
        raise _invalid_cursor()

    return DiscoverOrganizationListResponse(
        items=[DiscoverOrganizationResponse.model_validate(card, from_attributes=True) for card in page.items],
        next_cursor=page.next_cursor,
        has_more=page.next_cursor is not None,
    )
