"""Skill signal endpoints (GET /talents/me/signals)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, get_session
from app.services.authorization import Principal
from app.services.skill_signal import list_skill_signals

router = APIRouter(prefix="/talents/me/signals", tags=["signals"])


# ============================================================================
# Pydantic Schemas (Request/Response DTOs)
# ============================================================================


class SkillInSignalResponse(BaseModel):
    """Nested skill object in signal response."""

    id: str
    slug: str
    name_tr: str
    name_en: str | None
    category: str

    class Config:
        from_attributes = True


class SignalResponse(BaseModel):
    """Response schema for a single skill signal."""

    source_type: str
    strength: str
    occurred_at: str  # ISO 8601 timestamp
    attested_by: dict | None  # null for SELF_CLAIM
    superseded: bool

    class Config:
        from_attributes = True


class SkillSignalsGroupResponse(BaseModel):
    """Response schema for a skill group (skill + signals)."""

    skill: SkillInSignalResponse
    signals: list[SignalResponse]

    class Config:
        from_attributes = True


class SkillSignalsListResponse(BaseModel):
    """Response schema for GET /talents/me/signals."""

    items: list[SkillSignalsGroupResponse]


# ============================================================================
# Routes
# ============================================================================


@router.get("/", response_model=SkillSignalsListResponse)
def get_skill_signals(
    session: Session = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
    skill_id: str | None = Query(None, description="Optional skill UUID to filter by"),
):
    """
    Get skill signals for authenticated talent.

    AC-2: GET /talents/me/signals returns signals grouped by skill.
    AC-3: Optional ?skill_id filter returns single skill group.
    AC-4: Returns {items: []} if no signals (200, not 404).
    AC-S1/AC-S2: Signals scoped to principal.talent_id, no cross-talent access.

    Returns:
        {items: [{skill: {...}, signals: [...]}]}
    """
    # Ensure user is authenticated and has talent profile
    if principal.user_id is None or principal.talent_id is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Get signals via service layer (scoped to talent, grouped by skill)
    items = list_skill_signals(session, principal, skill_id=skill_id)

    return SkillSignalsListResponse(
        items=[SkillSignalsGroupResponse(**item) for item in items]
    )
