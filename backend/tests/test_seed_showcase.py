"""
Public profile showcase seed (/p/ayse-yilmaz).

The demo student must reach the public profile with several verified experiences
from different organizations, attested + evidenced skills and working /v links,
all produced through the real state machine (no direct status writes).
"""

from sqlalchemy import func, select

from app.models import Engagement, Organization, TalentProfile, User, VerifiedExperience
from scripts.seed import (
    SHOWCASE_ENGAGEMENTS,
    VERIFIED_ORG_LEGAL_IDS,
    seed_engagements,
    seed_institutions_and_organizations,
    seed_public_experiences,
    seed_showcase_profile,
    seed_skills,
    seed_talents,
    seed_verified_organizations,
)


def _run_full_seed(session) -> None:
    seed_skills(session)
    seed_talents(session)
    seed_institutions_and_organizations(session)
    seed_verified_organizations(session)
    seed_engagements(session)
    seed_showcase_profile(session)
    seed_public_experiences(session)
    session.commit()


def _ayse(session) -> TalentProfile:
    return session.execute(
        select(TalentProfile).join(User, TalentProfile.user_id == User.id).where(User.email == "ogrenci1@seed.local")
    ).scalar_one()


def test_showcase_profile_is_rich_and_public(client, session):
    _run_full_seed(session)

    response = client.get("/public/talents/ayse-yilmaz")

    assert response.status_code == 200
    data = response.json()
    experiences = data["verified_experiences"]
    assert len(experiences) == 1 + len(SHOWCASE_ENGAGEMENTS)
    assert len({ve["organization_name_snapshot"] for ve in experiences}) == len(experiences)
    assert data["attesting_organization_count"] == len(experiences)
    assert 6 <= len(data["skills"]) <= 8
    assert sum(1 for s in data["skills"] if s["attested"]) == len(experiences)
    assert any(not s["attested"] for s in data["skills"])
    # Verified orgs reach COMPETENCE; the short T1 engagement stays PARTICIPATION.
    claim_types = {ve["claim_type"] for ve in experiences}
    assert claim_types == {"COMPETENCE", "PARTICIPATION"}
    for ve in experiences:
        assert client.get(f"/public/v/{ve['public_token']}").status_code == 200


def test_seed_orgs_verified_except_flagged_one(session):
    _run_full_seed(session)

    levels = dict(
        session.execute(select(Organization.legal_id, Organization.verification_level).where(Organization.legal_id.like("ORG%"))).all()
    )
    for legal_id, level in levels.items():
        assert level == ("T3" if legal_id in VERIFIED_ORG_LEGAL_IDS else "T1"), legal_id


def test_all_seed_experiences_public(session):
    _run_full_seed(session)

    non_public = session.execute(
        select(func.count()).select_from(VerifiedExperience).where(VerifiedExperience.visibility != "PUBLIC")
    ).scalar_one()
    assert non_public == 0


def test_showcase_seed_is_idempotent(session):
    _run_full_seed(session)
    ayse = _ayse(session)
    count_before = session.execute(
        select(func.count()).select_from(Engagement).where(Engagement.talent_id == ayse.id)
    ).scalar_one()

    seed_verified_organizations(session)
    seed_showcase_profile(session)
    seed_public_experiences(session)
    session.commit()

    count_after = session.execute(
        select(func.count()).select_from(Engagement).where(Engagement.talent_id == ayse.id)
    ).scalar_one()
    assert count_before == count_after == 1 + len(SHOWCASE_ENGAGEMENTS)
