"""Talent skill endpoints (POST/GET/DELETE /talents/me/skills)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, get_session, get_verified_principal
from app.core.deps import require_csrf
from app.services.authorization import Principal
from app.services.skill_claim import (
    SkillAlreadyClaimedError,
    SkillClaimNotFoundError,
    SkillNotFoundError,
    add_skill_claim,
    list_skill_claims,
    remove_skill_claim,
)

router = APIRouter(prefix="/talents/me/skills", tags=["skills"])


# ============================================================================
# Pydantic Schemas (Request/Response DTOs)
# ============================================================================


class SkillResponse(BaseModel):
    """Nested skill object in skill claim response."""

    id: str
    slug: str
    name_tr: str
    name_en: str | None
    category: str

    class Config:
        from_attributes = True


class SkillClaimResponse(BaseModel):
    """Response schema for a single skill claim."""

    id: uuid.UUID | None = None  # Not used in list/post, but included for completeness
    skill: SkillResponse
    claimed_level: str | None

    class Config:
        from_attributes = True


class SkillClaimsListResponse(BaseModel):
    """Response schema for GET /talents/me/skills."""

    items: list[SkillClaimResponse]


class PostSkillClaimRequest(BaseModel):
    """Request schema for POST /talents/me/skills."""

    skill_id: str = Field(..., description="UUID of skill to claim")
    claimed_level: str | None = Field(
        None, description="Optional level: BEGINNER/INTERMEDIATE/ADVANCED"
    )


class PostSkillClaimResponse(BaseModel):
    """Response schema for POST /talents/me/skills."""

    skill_id: str
    claimed_level: str | None
    source: str


# ============================================================================
# AC-1: POST /talents/me/skills
# ============================================================================


@router.post("", response_model=PostSkillClaimResponse, status_code=201)
def post_skills(
    payload: PostSkillClaimRequest,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> PostSkillClaimResponse:
    """
    AC-1: Add a new skill to authenticated talent's profile.

    Returns:
        201 + {skill_id, claimed_level, source: "MANUAL"}

    Errors:
        - 404 SKILL_NOT_FOUND: skill does not exist or not ACTIVE
        - 409 ALREADY_CLAIMED: talent already claimed this skill
        - 404/401: unauthenticated or talent_id-less user (AC-S1)

    Security:
        - AC-S2: Body talent_id/user_id fields ignored (N/A in schema)
    """
    if principal.talent_id is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "TALENT_PROFILE_NOT_FOUND", "message": "Talent profili bulunamadı.", "request_id": None},
        )
    try:
        claim = add_skill_claim(
            session,
            principal,
            payload.skill_id,
            payload.claimed_level,
        )
    except SkillNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "SKILL_NOT_FOUND",
                "message": "Beceri bulunamadı.",
                "request_id": None,
            },
        )
    except SkillAlreadyClaimedError:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ALREADY_CLAIMED",
                "message": "Bu beceri zaten eklenmiş.",
                "request_id": None,
            },
        )

    # Commit transaction
    session.commit()

    return PostSkillClaimResponse(
        skill_id=str(claim.skill_id),
        claimed_level=claim.claimed_level,
        source=claim.source,
    )


# ============================================================================
# AC-2: GET /talents/me/skills
# ============================================================================


@router.get("", response_model=SkillClaimsListResponse)
def get_skills(
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> SkillClaimsListResponse:
    """
    AC-2, AC-8: Get all skill claims for authenticated talent.

    Returns:
        200 + {items: [{skill: {...}, claimed_level}, ...]}
        Empty list if no claims (AC-8 — not an error)

    Security:
        - AC-S3: Query returns only authenticated talent's claims
          (scoped_skill_claims enforced)
    """
    if principal.talent_id is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "TALENT_PROFILE_NOT_FOUND", "message": "Talent profili bulunamadı.", "request_id": None},
        )
    claims = list_skill_claims(session, principal)

    # Build response
    items = [
        SkillClaimResponse(
            skill=SkillResponse(**item["skill"]),
            claimed_level=item["claimed_level"],
        )
        for item in claims
    ]

    return SkillClaimsListResponse(items=items)


# ============================================================================
# AC-3, AC-7: DELETE /talents/me/skills/{skill_id}
# ============================================================================


@router.delete("/{skill_id}", status_code=204)
def delete_skills(
    skill_id: str,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> None:
    """
    AC-3, AC-7: Remove a skill claim from authenticated talent's profile.

    Returns:
        204 No Content

    Errors:
        - 404 SKILL_CLAIM_NOT_FOUND: claim does not exist or belongs to another talent
        - 404/401: unauthenticated or talent_id-less user (AC-S1)

    Security:
        - AC-S4: 404 for another talent's claim (indistinguishable from
          "never claimed this skill")
    """
    try:
        remove_skill_claim(session, principal, skill_id)
    except SkillClaimNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "SKILL_CLAIM_NOT_FOUND",
                "message": "Beceri talebiniz bulunamadı.",
                "request_id": None,
            },
        )

    # Commit transaction
    session.commit()
