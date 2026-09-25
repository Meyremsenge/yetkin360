"""Public profile endpoint — auth-free access to talent profiles."""

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.errors import ApiError
from app.services.authorization import get_scoped_or_404, scoped_public_talent_profile, scoped_public_verified_experiences
from app.services.visibility_service import filter_public_experiences

router = APIRouter(tags=["public"], prefix="/public")


# ============================================================================
# Pydantic Response Schemas (Public API)
# ============================================================================


class PublicVerifiedExperienceResponse(BaseModel):
    """Response schema for VerifiedExperience in public profile."""

    id: uuid.UUID
    organization_name_snapshot: str
    role_snapshot: str
    started_on_snapshot: date | None
    ended_on_snapshot: date | None
    claim_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class PublicTalentProfileResponse(BaseModel):
    """Response schema for GET /public/talents/{slug}."""

    talent_id: uuid.UUID
    display_name: str
    verified_experiences: list[PublicVerifiedExperienceResponse]


# ============================================================================
# AC-1: GET /public/talents/{slug}
# ============================================================================


@router.get("/talents/{slug}")
def get_public_profile(
    slug: str,
    session: Session = Depends(get_session),
) -> PublicTalentProfileResponse:
    """
    AC-1: Return public talent profile by slug (auth-free).

    Route: GET /public/talents/{slug}

    Path Parameters:
      - slug: public_slug value (string)

    Returns (200):
      - {talent_id, display_name, verified_experiences[]}
      - verified_experiences filtered to visibility='PUBLIC' only

    Returns (404):
      - ApiError zarfı — {"code": "TALENT_NOT_FOUND", "message": "Kayıt bulunamadı", "request_id": "<uuid>"}
        (identical for nonexistent, PRIVATE, INSTITUTION, ORGANIZATIONS)

    Security (AC-S1):
      - No distinction between missing slug and non-PUBLIC visibility → same 404
      - Single query with combined WHERE to avoid timing side-channel

    Implements: YET-105 (public-profil-endpoint), AC-1..AC-6
    """
    # Query: single combined WHERE clause (talent visibility='PUBLIC' AND public_slug matches AND not deleted)
    scoped_query = scoped_public_talent_profile(session, slug)
    talent_profile = get_scoped_or_404(scoped_query, session)

    if talent_profile is None:
        # AC-2/AC-3/AC-6: identical 404 for nonexistent, PRIVATE, INSTITUTION, ORGANIZATIONS, or NULL slug
        raise ApiError(status_code=404, code="TALENT_NOT_FOUND", message="Kayıt bulunamadı")

    # Load verified experiences for this talent (via scoped query)
    verified_experiences = list(session.execute(
        scoped_public_verified_experiences(session, talent_profile.id)
    ).scalars().all())

    # AC-5 (AC-S3): filter to PUBLIC visibility only
    public_experiences = filter_public_experiences(verified_experiences)

    # Build response (AC-4/AC-S2: PII fields excluded — only talent_id, display_name, verified_experiences)
    return PublicTalentProfileResponse(
        talent_id=talent_profile.id,
        display_name=talent_profile.full_name,
        verified_experiences=[
            PublicVerifiedExperienceResponse.from_orm(exp) for exp in public_experiences
        ],
    )
