"""Verified experience endpoints (GET /talents/me/verified-experiences, PATCH .../{id}/visibility)."""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, get_session, get_verified_principal
from app.core.deps import require_csrf
from app.core.errors import ApiError
from app.services.authorization import Principal
from app.services.verified_experience import (
    change_own_verified_experience_visibility,
    list_own_verified_experiences,
)

router = APIRouter(prefix="/talents/me/verified-experiences", tags=["verified-experiences"])


# ============================================================================
# Pydantic Schemas (Request/Response DTOs)
# ============================================================================


class VerifiedExperienceResponse(BaseModel):
    """Response schema for a single verified experience."""

    id: str
    organization_name_snapshot: str
    role_snapshot: str
    started_on_snapshot: str | None  # ISO 8601 date
    ended_on_snapshot: str | None  # ISO 8601 date
    institution_name_snapshot: str | None
    claim_type: str
    visibility: str
    public_token: str | None
    created_at: str  # ISO 8601 timestamp

    class Config:
        from_attributes = True


class VerifiedExperiencesListResponse(BaseModel):
    """Response schema for GET /talents/me/verified-experiences."""

    items: list[VerifiedExperienceResponse]


class ChangeVisibilityRequest(BaseModel):
    """Request schema for PATCH /talents/me/verified-experiences/{id}/visibility."""

    visibility: Literal["PRIVATE", "INSTITUTION", "ORGANIZATIONS", "PUBLIC"]


# ============================================================================
# Routes
# ============================================================================


@router.get("/", response_model=VerifiedExperiencesListResponse)
def get_verified_experiences(
    session: Session = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    """
    Get verified experiences for authenticated talent.

    AC-7: Returns all verified experiences owned by talent (including PRIVATE)
    AC-8: Returns {items: []} if no verified experiences (200, not 404)
    AC-9/AC-S1: Verified experiences scoped to principal.talent_id, no cross-talent access
    AC-S2: Unauthenticated request → 401
    AC-S3: Authenticated but talent-less principal → 404 (not 401)

    Returns:
        {items: [{id, organization_name_snapshot, role_snapshot, ...}]}
    """
    # Ensure user is authenticated
    if principal.user_id is None:
        raise HTTPException(status_code=401, detail="Kimlik doğrulama gerekli.")

    # Ensure user has talent profile (different from skill_signals.py: returns 404, not 401)
    if principal.talent_id is None:
        raise HTTPException(status_code=404, detail="Talent bulunamadı.")

    # Get verified experiences via service layer (scoped to talent)
    items = list_own_verified_experiences(session, principal)

    return VerifiedExperiencesListResponse(
        items=[VerifiedExperienceResponse(**item) for item in items]
    )


@router.patch("/{experience_id}/visibility", response_model=VerifiedExperienceResponse)
def patch_verified_experience_visibility(
    experience_id: uuid.UUID,
    payload: ChangeVisibilityRequest,
    session: Session = Depends(get_session),
    principal: Principal = Depends(get_verified_principal),
    _csrf: None = Depends(require_csrf),
) -> VerifiedExperienceResponse:
    """
    Change visibility of the caller's own verified experience (D6 change-visibility).

    Owner only — ownership comes from the session principal, never from the URL.
    Unknown id, another talent's record or a talent-less caller → identical 404.
    """
    item = change_own_verified_experience_visibility(
        session, principal, experience_id, payload.visibility
    )
    if item is None:
        raise ApiError(status_code=404, code="VERIFIED_EXPERIENCE_NOT_FOUND", message="Kayıt bulunamadı")
    session.commit()
    return VerifiedExperienceResponse(**item)
