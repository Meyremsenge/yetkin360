"""Engagement endpoints (POST /engagements)."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, get_session
from app.services.authorization import Principal
from app.services.engagement import (
    InstitutionMismatchError,
    OrganizationNotFoundError,
    TalentNotFoundError,
    create_engagement,
)

router = APIRouter(prefix="/engagements", tags=["engagements"])


# ============================================================================
# Pydantic Schemas (Request/Response DTOs)
# ============================================================================


class PostEngagementRequest(BaseModel):
    """Request schema for POST /engagements."""

    talent_id: str = Field(..., description="UUID of talent")
    organization_id: str = Field(..., description="UUID of organization")
    kind: Literal["INTERNSHIP", "CAPSTONE", "SHORT_PROJECT", "PART_TIME"] = Field(..., description="Engagement kind")
    title: str = Field(..., min_length=1, description="Engagement title")
    institution_id: str | None = Field(None, description="Optional UUID of institution")
    confidential: bool = Field(False, description="Whether engagement is confidential")

    class Config:
        from_attributes = True


class PostEngagementResponse(BaseModel):
    """Response schema for POST /engagements (201)."""

    id: str
    talent_id: str
    organization_id: str
    institution_id: str | None
    kind: str
    title: str
    status: str
    version: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# AC-1: POST /engagements
# ============================================================================


@router.post("", response_model=PostEngagementResponse, status_code=201)
def post_engagements(
    payload: PostEngagementRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> PostEngagementResponse:
    """
    AC-1: Create a new engagement (internship/capstone/project/part-time work).

    Returns:
        201 + {id, talent_id, organization_id, institution_id, kind, title, status, version, created_at}

    Errors:
        - 404 TALENT_NOT_FOUND: talent does not exist or not accessible to principal
        - 404 ORGANIZATION_NOT_FOUND: organization does not exist or not accessible
        - 400 INSTITUTION_MISMATCH: institution_id doesn't match talent's institution
        - 422: validation error (invalid kind, empty title, etc.)
        - 401: unauthenticated

    Security:
        - AC-S1: TALENT can only create for own talent_id (403→404)
        - AC-S2: ORG_MEMBER can only create for their organizations (403→404)
        - AC-S3: Institution mismatch error message is generic
        - AC-S4: confidential title not logged
    """
    if principal.user_id is None:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Kimlik doğrulama gerekli.",
                "request_id": None,
            },
        )

    try:
        engagement = create_engagement(
            session=session,
            principal=principal,
            talent_id=payload.talent_id,
            organization_id=payload.organization_id,
            kind=payload.kind,
            title=payload.title,
            institution_id=payload.institution_id,
            confidential=payload.confidential,
        )
    except TalentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "TALENT_NOT_FOUND",
                "message": "Talent bulunamadı.",
                "request_id": None,
            },
        )
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "ORGANIZATION_NOT_FOUND",
                "message": "Organizasyon bulunamadı.",
                "request_id": None,
            },
        )
    except InstitutionMismatchError:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INSTITUTION_MISMATCH",
                "message": "institution_id does not match talent's institution",
                "request_id": None,
            },
        )

    # Commit transaction
    session.commit()

    return PostEngagementResponse(
        id=str(engagement.id),
        talent_id=str(engagement.talent_id),
        organization_id=str(engagement.organization_id),
        institution_id=str(engagement.institution_id) if engagement.institution_id else None,
        kind=engagement.kind,
        title=engagement.title,
        status=engagement.status,
        version=engagement.version,
        created_at=engagement.created_at,
    )
