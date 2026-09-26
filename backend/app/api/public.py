"""Public profile endpoint — auth-free access to talent profiles."""

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.errors import ApiError
from app.models import Engagement, Organization, Skill, TalentProfile
from app.services.authorization import get_scoped_or_404, scoped_attestations_for_engagement, scoped_public_talent_profile, scoped_public_verified_experiences, scoped_public_verified_experience_by_token
from app.services.visibility_service import filter_public_experiences

router = APIRouter(tags=["public"], prefix="/public")


# ============================================================================
# Pydantic Response Schemas (Public API)
# ============================================================================


class AttestedSkillResponse(BaseModel):
    """Response schema for attested skill in public verification."""

    name_tr: str
    claim_type: str
    attestor_organization: str | None

    class Config:
        from_attributes = True


class PublicVerificationResponse(BaseModel):
    """Response schema for GET /public/v/{token}."""

    title: str
    talent_name: str
    organization_name: str
    organization_trust_level: str
    institution_name: str | None
    started_on: date | None
    ended_on: date | None
    verified_at: datetime
    attested_skills: list[AttestedSkillResponse]

    class Config:
        from_attributes = True


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


# ============================================================================
# AC-1: GET /public/v/{token} (YET-106)
# ============================================================================


@router.get("/v/{token}")
def get_public_verification(
    token: str,
    session: Session = Depends(get_session),
) -> PublicVerificationResponse:
    """
    AC-1: Return public verification by token (auth-free).

    Route: GET /public/v/{token}

    Path Parameters:
      - token: public_token value (string)

    Returns (200):
      - {title, talent_name, organization_name, organization_trust_level,
         institution_name, started_on, ended_on, verified_at, attested_skills[]}

    Returns (404):
      - ApiError zarfı — {"code": "VERIFICATION_NOT_FOUND", "message": "Kayıt bulunamadı", "request_id": "<uuid>"}
        (identical for nonexistent token or non-PUBLIC visibility)

    Security (AC-S1/AC-S2):
      - Single query with combined WHERE to avoid timing side-channel
      - No distinction between missing token and non-PUBLIC visibility → same 404

    Implements: YET-106 (public-dogrulama-linki), AC-1..AC-7
    """
    # Query: single combined WHERE clause (public_token matches AND visibility='PUBLIC')
    scoped_query = scoped_public_verified_experience_by_token(session, token)
    ve = get_scoped_or_404(scoped_query, session)

    if ve is None:
        # AC-2/AC-3/AC-S2: identical 404 for nonexistent or non-PUBLIC
        raise ApiError(status_code=404, code="VERIFICATION_NOT_FOUND", message="Kayıt bulunamadı")

    # Fetch talent profile (for talent_name)
    talent_profile = session.get(TalentProfile, ve.talent_id)
    if talent_profile is None:
        # Should not happen (FK constraint), but defensive check
        raise ApiError(status_code=500, code="INTERNAL_ERROR", message="Bir hata oluştu")

    # Fetch engagement (for organization_id → organization_trust_level)
    engagement = session.get(Engagement, ve.engagement_id)
    if engagement is None:
        # Should not happen (FK constraint), but defensive check
        raise ApiError(status_code=500, code="INTERNAL_ERROR", message="Bir hata oluştu")

    # Fetch organization (for organization_trust_level)
    org = session.get(Organization, engagement.organization_id)
    if org is None:
        # Should not happen (FK constraint), but defensive check
        raise ApiError(status_code=500, code="INTERNAL_ERROR", message="Bir hata oluştu")

    # Fetch attested skills (Attestation records with engagement_id == ve.engagement_id, skill_id NOT NULL)
    attestations = list(session.execute(scoped_attestations_for_engagement(session, ve.engagement_id)).scalars().all())

    # Build attested_skills list
    attested_skills: list[AttestedSkillResponse] = []
    for att in attestations:
        # Fetch skill (for name_tr)
        skill = session.get(Skill, att.skill_id)
        if skill is None:
            # Should not happen (FK constraint), but skip if missing
            continue

        # Fetch attestor organization (if attestor_org_id is not None)
        attestor_org_name: str | None = None
        if att.attestor_org_id is not None:
            attestor_org = session.get(Organization, att.attestor_org_id)
            if attestor_org is not None:
                attestor_org_name = attestor_org.name

        attested_skills.append(
            AttestedSkillResponse(
                name_tr=skill.name_tr,
                claim_type=att.claim_type,
                attestor_organization=attestor_org_name,
            )
        )

    # Build response (AC-1/AC-5: 9 fields, no PII, no internal IDs)
    return PublicVerificationResponse(
        title=ve.role_snapshot,
        talent_name=talent_profile.full_name,
        organization_name=ve.organization_name_snapshot,
        organization_trust_level=org.verification_level,
        institution_name=ve.institution_name_snapshot,
        started_on=ve.started_on_snapshot,
        ended_on=ve.ended_on_snapshot,
        verified_at=ve.created_at,
        attested_skills=attested_skills,
    )
