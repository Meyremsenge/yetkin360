"""User profile endpoints (GET /me, PATCH /talents/me)."""

import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_principal,
    get_current_user,
    get_session,
    get_verified_principal,
)
from app.core.deps import require_csrf
from app.models import User
from app.services.authorization import Principal, get_scoped_or_404, scoped_talent_profiles
from app.services.talent import SlugTakenError, get_me_context, update_talent_profile

router = APIRouter(tags=["me"])


# ============================================================================
# Pydantic Schemas (Request/Response DTOs)
# ============================================================================


class TalentProfileResponse(BaseModel):
    """Response schema for TalentProfile."""

    id: uuid.UUID
    user_id: uuid.UUID
    institution_id: uuid.UUID | None
    full_name: str
    headline: str | None
    department: str | None
    study_year: int | None
    city: str | None
    about: str | None
    visibility: str
    public_slug: str | None
    updated_at: datetime

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """Response schema for User."""

    id: uuid.UUID
    email: str
    email_verified: bool
    is_platform_admin: bool

    class Config:
        from_attributes = True


class OrganizationResponse(BaseModel):
    """Response schema for Organization (in GET /me)."""

    id: uuid.UUID
    name: str

    class Config:
        from_attributes = True


class InstitutionResponse(BaseModel):
    """Response schema for Institution (in GET /me)."""

    id: uuid.UUID
    name: str

    class Config:
        from_attributes = True


class GetMeResponse(BaseModel):
    """Response schema for GET /me."""

    user: UserResponse
    talent_profile: TalentProfileResponse | None = None
    organizations: list[OrganizationResponse]
    institutions: list[InstitutionResponse]


PUBLIC_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class UpdateTalentProfileRequest(BaseModel):
    """Request schema for PATCH /talents/me."""

    full_name: str | None = Field(None, max_length=255)
    headline: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    department: str | None = Field(None, max_length=100)
    study_year: int | None = None
    # Plain text "about me" (self-declared); DB CHECK mirrors the 1000-char limit.
    about: str | None = Field(None, max_length=1000)
    visibility: str | None = None
    public_slug: str | None = Field(None, max_length=100)

    @field_validator("about")
    @classmethod
    def normalize_about(cls, v):
        """Whitespace-only about clears the field instead of storing blanks."""
        if v is None:
            return v
        v = v.strip()
        return v or None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v):
        """full_name gönderildiyse boş/whitespace-only olamaz (NOT NULL alan)."""
        if v is not None and not v.strip():
            raise ValueError("full_name boş olamaz")
        return v

    @field_validator("public_slug")
    @classmethod
    def validate_public_slug(cls, v):
        """public_slug URL-güvenli biçimde olmalı: küçük harf, rakam, tire."""
        if v is not None and not PUBLIC_SLUG_PATTERN.match(v):
            raise ValueError(
                "public_slug yalnızca küçük harf, rakam ve tire (-) içerebilir; "
                "tire ile başlayıp bitemez"
            )
        return v

    @field_validator("study_year")
    @classmethod
    def validate_study_year(cls, v):
        """Validate study_year is in range 1-8 if provided."""
        if v is not None and (v < 1 or v > 8):
            raise ValueError("study_year must be between 1 and 8")
        return v

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v):
        """Validate visibility is a valid enum value."""
        if v is not None:
            valid_values = {"PRIVATE", "INSTITUTION", "ORGANIZATIONS", "PUBLIC"}
            if v not in valid_values:
                raise ValueError(f"visibility must be one of {valid_values}")
        return v


# ============================================================================
# AC-1: GET /me
# ============================================================================


@router.get("/me", response_model=GetMeResponse)
def get_me(
    principal: Principal = Depends(get_current_principal),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> GetMeResponse:
    """
    AC-1: Return current user's profile and associations.

    Returns:
        GET /me → 200 + {user, talent_profile, organizations[], institutions[]}

    Security:
        - AC-S1: Query/body parameters are ignored, authenticated user's context only
    """
    context = get_me_context(principal, user, session)
    talent_profile = context["talent_profile"]

    # Build response
    org_responses = [
        OrganizationResponse(id=o.id, name=o.name) for o in context["organizations"]
    ]
    inst_responses = [
        InstitutionResponse(id=i.id, name=i.name) for i in context["institutions"]
    ]

    return GetMeResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            email_verified=user.email_verified_at is not None,
            is_platform_admin=user.is_platform_admin,
        ),
        talent_profile=(
            TalentProfileResponse.from_orm(talent_profile) if talent_profile is not None else None
        ),
        organizations=org_responses,
        institutions=inst_responses,
    )


# ============================================================================
# AC-3 through AC-7: PATCH /talents/me
# ============================================================================


@router.patch("/talents/me", response_model=TalentProfileResponse)
def patch_talents_me(
    payload: UpdateTalentProfileRequest,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> TalentProfileResponse:
    """
    AC-3 through AC-7: Update current user's talent profile.

    Accepts:
        - full_name, headline, city, department, study_year, about, visibility, public_slug
        - Ignores: institution_id, user_id, id, talent_profile_id (if sent)
        - Explicit null on a clearable field (headline/city/department/study_year/
          about/public_slug) clears it; full_name/visibility cannot be cleared (NOT NULL)

    Returns:
        200 + updated TalentProfile

    Errors:
        - 409 SLUG_TAKEN: public_slug already in use (atomicity: no update)
        - 422: Invalid study_year (not 1-8), visibility (invalid enum), public_slug
          (invalid format), or full_name/visibility explicitly set to null

    Security:
        - AC-S2: Body ID fields ignored, always updates authenticated user's profile (principal.talent_id)
        - AC-8: Authorization based on talent_id, not kind (handles user with multiple roles)
    """
    # Get current user's talent profile (via scoped query for authorization)
    scoped_query = scoped_talent_profiles(session, principal)
    talent_profile = get_scoped_or_404(scoped_query, session)
    if not talent_profile:
        raise HTTPException(status_code=404, detail={"code": "TALENT_PROFILE_NOT_FOUND", "message": "Talent profili bulunamadı.", "request_id": None})

    # Extract only explicitly-provided fields (ignore institution_id, user_id, etc.).
    # Use model_fields_set, not "is not None", so an explicit null on a clearable
    # field (headline/city/department/study_year/public_slug) actually clears it
    # instead of being silently dropped.
    required_fields = {"full_name", "visibility"}
    set_fields = payload.model_fields_set
    updates = {}
    for field in ["full_name", "headline", "city", "department", "study_year", "about", "visibility", "public_slug"]:
        if field not in set_fields:
            continue
        value = getattr(payload, field)
        if value is None and field in required_fields:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "FIELD_REQUIRED",
                    "message": f"{field} alanı boş bırakılamaz.",
                    "request_id": None,
                },
            )
        updates[field] = value

    # Update profile (handles validation, slug uniqueness check, atomicity)
    try:
        updated_profile = update_talent_profile(talent_profile, updates, session)
    except SlugTakenError:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SLUG_TAKEN",
                "message": "Bu kısa bağlantı zaten kullanılıyor.",
                "request_id": None,
            },
        )

    # Commit transaction
    session.commit()

    return TalentProfileResponse.from_orm(updated_profile)
