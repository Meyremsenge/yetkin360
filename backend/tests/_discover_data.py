"""Shared builders for the Keşfet directory tests (PLAN R.1)."""

from datetime import date, datetime, timezone
from itertools import count

from app.models import (
    Attestation,
    Engagement,
    Organization,
    Skill,
    TalentProfile,
    User,
    VerifiedExperience,
)

_seq = count(1)


def make_user(session, email: str) -> User:
    user = User(email=email, password_hash="hash")
    session.add(user)
    session.flush()
    return user


def make_talent(
    session,
    key: str,
    *,
    full_name: str | None = None,
    visibility: str = "PUBLIC",
    with_slug: bool = True,
    **fields,
) -> TalentProfile:
    """Talent profile owned by a fresh user `<key>@example.com`."""
    user = make_user(session, f"{key}@example.com")
    profile = TalentProfile(
        user_id=user.id,
        full_name=full_name or f"Talent {key}",
        visibility=visibility,
        public_slug=f"{key}-slug" if with_slug else None,
        **fields,
    )
    session.add(profile)
    session.flush()
    return profile


def make_org(session, name: str, **fields) -> Organization:
    org = Organization(name=name, **{"verification_level": "T2", "status": "ACTIVE", **fields})
    session.add(org)
    session.flush()
    return org


def make_skill(session, slug: str, name_tr: str) -> Skill:
    skill = Skill(slug=slug, name_en=name_tr, name_tr=name_tr, category="LANGUAGE", status="ACTIVE")
    session.add(skill)
    session.flush()
    return skill


def seal_skill(
    session,
    talent: TalentProfile,
    org: Organization,
    skill: Skill | None,
    *,
    experience_visibility: str = "PUBLIC",
    revoked: bool = False,
) -> VerifiedExperience:
    """
    One engagement + its VerifiedExperience + one attestation by a fresh attestor.
    `skill=None` gives an experience attested without a skill.
    """
    n = next(_seq)
    engagement = Engagement(
        talent_id=talent.id,
        organization_id=org.id,
        kind="INTERNSHIP",
        title=f"Engagement {n}",
        status="VERIFIED",
        started_on=date(2025, 6, 1),
        ended_on=date(2025, 8, 31),
        confidential=False,
    )
    session.add(engagement)
    session.flush()

    experience = VerifiedExperience(
        talent_id=talent.id,
        engagement_id=engagement.id,
        organization_name_snapshot=org.name,
        role_snapshot=engagement.title,
        started_on_snapshot=engagement.started_on,
        ended_on_snapshot=engagement.ended_on,
        institution_name_snapshot=None,
        claim_type="COMPETENCE",
        visibility=experience_visibility,
    )
    session.add(experience)

    attestor = make_user(session, f"attestor-{n}@example.com")
    session.add(
        Attestation(
            engagement_id=engagement.id,
            talent_id=talent.id,
            subject_type="ENGAGEMENT",
            subject_id=engagement.id,
            claim_type="COMPETENCE",
            requested_claim_type="COMPETENCE",
            attestor_user_id=attestor.id,
            attestor_org_id=org.id,
            skill_id=skill.id if skill else None,
            statement="ok",
            revoked_at=datetime.now(timezone.utc) if revoked else None,
            revoke_reason="test" if revoked else None,
        )
    )
    session.flush()
    return experience


def auth(user: User) -> dict[str, str]:
    return {"X-Debug-User-Id": str(user.id)}


def slugs(response) -> list[str]:
    return [item["public_slug"] for item in response.json()["items"]]
