"""Public profile endpoint — auth-free access to talent profiles."""

import uuid
from dataclasses import asdict
from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.errors import ApiError
from app.models import Engagement, Institution, Organization, Skill, TalentProfile
from app.services.authorization import get_scoped_or_404, scoped_attestations_for_engagement, scoped_public_talent_profile, scoped_public_verified_experience_by_token
from app.services.public_profile import build_public_profile

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
    # GUV-03 / K2 (b): show who vouches, so a self-created org/institution is visibly unverified.
    # organization_domain is exposed only when verified (T2+); otherwise it is attacker-chosen free text.
    organization_domain: str | None
    institution_name: str | None
    institution_trust_level: str | None
    started_on: date | None
    ended_on: date | None
    verified_at: datetime
    attested_skills: list[AttestedSkillResponse]

    class Config:
        from_attributes = True


class PublicExperienceSkillResponse(BaseModel):
    """A skill attested within one public verified experience."""

    name_tr: str
    category: str
    claim_type: str
    attestor_organization: str | None


class PublicEvidencedSkillResponse(BaseModel):
    """A skill exercised in a task/deliverable of the experience, not separately attested."""

    name_tr: str
    category: str


class PublicVerifiedExperienceResponse(BaseModel):
    """Response schema for VerifiedExperience in public profile."""

    id: uuid.UUID
    organization_name_snapshot: str
    organization_trust_level: str
    role_snapshot: str
    institution_name_snapshot: str | None
    started_on_snapshot: date | None
    ended_on_snapshot: date | None
    claim_type: str
    created_at: datetime
    # Link to /v/{token}; the experience is already PUBLIC, the same token is shareable.
    public_token: str | None
    skills: list[PublicExperienceSkillResponse]
    evidenced_skills: list[PublicEvidencedSkillResponse]

    class Config:
        from_attributes = True


class PublicSkillResponse(BaseModel):
    """Skill map entry, aggregated from PUBLIC experiences' signals only."""

    name_tr: str
    category: str
    strength: str
    # True when at least one organization attested it; otherwise task/deliverable evidence only.
    attested: bool
    experience_count: int


class PublicCertificateResponse(BaseModel):
    """A consented portfolio item. No file, no OCR output (extracted_name/qr_raw_data/page_name)."""

    kind: str
    title: str
    issuer: str | None
    issued_on: date | None
    credential_id: str | None
    # COORDINATOR_CONFIRMED (certificate_checks decision) | SELF_DECLARED — never mixed on the page
    badge: str
    provider: str | None
    # Confirmed only, https on the provider's own domain
    verify_url: str | None
    # Self-declared only: student's https link, shown with its host
    link_url: str | None
    link_host: str | None


class PublicTalentProfileResponse(BaseModel):
    """Response schema for GET /public/talents/{slug}. No e-mail, no internal ids."""

    display_name: str
    headline: str | None
    department: str | None
    study_year: int | None
    city: str | None
    institution_name: str | None
    institution_trust_level: str | None
    about: str | None
    verified_experiences: list[PublicVerifiedExperienceResponse]
    skills: list[PublicSkillResponse]
    attesting_organization_count: int
    certificates: list[PublicCertificateResponse]

    class Config:
        from_attributes = True


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
      - {display_name, headline, department, study_year, city, institution_name,
         institution_trust_level, about, verified_experiences[], skills[],
         attesting_organization_count, certificates[]} (no internal talent_id: YET-230, no e-mail)
      - verified_experiences filtered to visibility='PUBLIC' only; skills derived
        from those experiences' attestations only

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

    # PUBLIC experiences only (AC-5/AC-S3); PII and internal ids excluded (AC-4/AC-S2)
    return PublicTalentProfileResponse.model_validate(asdict(build_public_profile(session, talent_profile)))


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

    institution = (
        session.get(Institution, engagement.institution_id)
        if engagement.institution_id is not None
        else None
    )
    domain_verified = org.verification_level in ("T2", "T3", "T4")

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

    # Build response (AC-1/AC-5: 11 fields, no PII, no internal IDs)
    return PublicVerificationResponse(
        title=ve.role_snapshot,
        talent_name=talent_profile.full_name,
        organization_name=ve.organization_name_snapshot,
        organization_trust_level=org.verification_level,
        organization_domain=org.domain if domain_verified else None,
        institution_name=ve.institution_name_snapshot,
        institution_trust_level=institution.verification_level if institution else None,
        started_on=ve.started_on_snapshot,
        ended_on=ve.ended_on_snapshot,
        verified_at=ve.created_at,
        attested_skills=attested_skills,
    )
