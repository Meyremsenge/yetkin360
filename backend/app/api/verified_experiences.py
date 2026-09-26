"""Verified experience endpoints (GET /talents/me/verified-experiences)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, get_session
from app.services.authorization import Principal
from app.services.verified_experience import list_own_verified_experiences

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
