"""
Public profile showcase fields — privacy boundary tests.

GET /public/talents/{slug} now carries an identity line, per-experience attested
skills and an aggregated skill map. These tests pin that every derived field comes
from PUBLIC experiences only: a PRIVATE experience's skills, token, attestor org or
strength must never surface, revoked attestations are dropped, and no e-mail leaks.
"""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from app.models import (
    Attestation,
    Deliverable,
    Engagement,
    EngagementTask,
    Institution,
    Organization,
    Skill,
    SkillSignal,
    TalentProfile,
    User,
    VerifiedExperience,
)

SLUG = "showcase-talent"


@pytest.fixture
def owner(session):
    user = User(email="showcase-owner@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def institution(session):
    inst = Institution(name="Showcase Üniversitesi", verification_level="T3")
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def profile(session, owner, institution):
    row = TalentProfile(
        user_id=owner.id,
        full_name="Vitrin Öğrencisi",
        headline="Veri odaklı öğrenci",
        department="Endüstri Mühendisliği",
        study_year=3,
        city="İstanbul",
        institution_id=institution.id,
        visibility="PUBLIC",
        public_slug=SLUG,
    )
    session.add(row)
    session.flush()
    return row


def _skill(session, slug: str, name: str, category: str = "TOOL") -> Skill:
    skill = Skill(slug=slug, name_tr=name, category=category)
    session.add(skill)
    session.flush()
    return skill


def _org(session, name: str, level: str = "T3") -> Organization:
    org = Organization(name=name, verification_level=level)
    session.add(org)
    session.flush()
    return org


def _experience(session, profile, org, visibility: str, token: str, started: date) -> VerifiedExperience:
    engagement = Engagement(
        id=uuid4(),
        kind="INTERNSHIP",
        talent_id=profile.id,
        organization_id=org.id,
        title=f"Rol {token}",
        started_on=started,
        ended_on=date(started.year, started.month + 2, 1),
        status="VERIFIED",
    )
    session.add(engagement)
    session.flush()
    ve = VerifiedExperience(
        talent_id=profile.id,
        engagement_id=engagement.id,
        organization_name_snapshot=org.name,
        role_snapshot=engagement.title,
        started_on_snapshot=engagement.started_on,
        ended_on_snapshot=engagement.ended_on,
        claim_type="COMPETENCE",
        visibility=visibility,
        public_token=token,
        created_at=datetime.now(timezone.utc),
    )
    session.add(ve)
    session.flush()
    return ve


def _attest(session, ve, profile, org, skill, claim: str, strength: str, revoked: bool = False):
    # uq_attestations_engagement_attestor_subject: one ENGAGEMENT attestation per
    # attestor per engagement, so each attested skill gets its own attestor.
    attestor = User(email=f"attestor-{uuid4().hex[:8]}@example.com", password_hash="hash")
    session.add(attestor)
    session.flush()
    att = Attestation(
        engagement_id=ve.engagement_id,
        talent_id=profile.id,
        subject_type="ENGAGEMENT",
        claim_type=claim,
        requested_claim_type=claim,
        attestor_user_id=attestor.id,
        attestor_org_id=org.id,
        skill_id=skill.id,
        revoked_at=datetime.now(timezone.utc) if revoked else None,
        revoke_reason="test" if revoked else None,
    )
    session.add(att)
    session.flush()
    session.add(
        SkillSignal(
            talent_id=profile.id,
            skill_id=skill.id,
            source_type="ATTESTATION",
            source_id=att.id,
            strength=strength,
            attested_by_org_id=org.id,
            occurred_at=datetime.now(timezone.utc),
        )
    )
    session.flush()
    return att


def _evidence(session, ve, profile, skill, kind: str):
    """TASK (WEAK) or DELIVERABLE (MODERATE) signal on the experience's engagement."""
    if kind == "TASK":
        source = EngagementTask(engagement_id=ve.engagement_id, skill_id=skill.id, title="Görev")
        strength = "WEAK"
    else:
        source = Deliverable(
            engagement_id=ve.engagement_id,
            skill_id=skill.id,
            title="Çıktı",
            submitted_by_user_id=profile.user_id,
            submitted_at=datetime.now(timezone.utc),
        )
        strength = "MODERATE"
    session.add(source)
    session.flush()
    session.add(
        SkillSignal(
            talent_id=profile.id,
            skill_id=skill.id,
            source_type=kind,
            source_id=source.id,
            strength=strength,
            occurred_at=datetime.now(timezone.utc),
        )
    )
    session.flush()


@pytest.fixture
def scenario(session, profile):
    public_org = _org(session, "Açık Kuruluş A.Ş.")
    second_public_org = _org(session, "İkinci Açık Kuruluş", level="T1")
    private_org = _org(session, "Gizli Kuruluş Ltd.")
    python = _skill(session, "showcase-python", "Python")
    sql = _skill(session, "showcase-sql", "SQL")
    secret = _skill(session, "showcase-secret", "Gizli Yetkinlik")
    revoked_skill = _skill(session, "showcase-revoked", "Geri Çekilmiş Yetkinlik")

    ve_public = _experience(session, profile, public_org, "PUBLIC", "showcase-public-1", date(2026, 3, 1))
    ve_public_2 = _experience(session, profile, second_public_org, "PUBLIC", "showcase-public-2", date(2025, 9, 1))
    ve_private = _experience(session, profile, private_org, "PRIVATE", "showcase-private", date(2026, 5, 1))

    _attest(session, ve_public, profile, public_org, python, "COMPETENCE", "STRONG")
    _attest(session, ve_public, profile, public_org, revoked_skill, "COMPETENCE", "STRONG", revoked=True)
    _attest(session, ve_public_2, profile, second_public_org, python, "PARTICIPATION", "WEAK")
    _attest(session, ve_public_2, profile, second_public_org, sql, "CONTRIBUTION", "WEAK")
    _attest(session, ve_private, profile, private_org, secret, "COMPETENCE", "STRONG")
    _attest(session, ve_private, profile, private_org, sql, "COMPETENCE", "STRONG")
    react = _skill(session, "showcase-react", "React", category="FRAMEWORK")
    hidden_tool = _skill(session, "showcase-hidden-tool", "Gizli Araç")
    _evidence(session, ve_public, profile, react, "DELIVERABLE")
    _evidence(session, ve_public, profile, python, "TASK")  # already attested here → not repeated
    _evidence(session, ve_private, profile, hidden_tool, "DELIVERABLE")
    return {"ve_public": ve_public, "ve_private": ve_private}


def test_identity_line_is_exposed_without_email(client, owner, scenario):
    response = client.get(f"/public/talents/{SLUG}")

    assert response.status_code == 200
    data = response.json()
    assert data["headline"] == "Veri odaklı öğrenci"
    assert data["department"] == "Endüstri Mühendisliği"
    assert data["study_year"] == 3
    assert data["city"] == "İstanbul"
    assert data["institution_name"] == "Showcase Üniversitesi"
    assert data["institution_trust_level"] == "T3"
    assert owner.email not in response.text
    assert "@" not in response.text


def test_private_experience_never_surfaces(client, scenario):
    response = client.get(f"/public/talents/{SLUG}")
    text = response.text

    assert "Gizli Kuruluş" not in text
    assert "Gizli Yetkinlik" not in text
    assert "Gizli Araç" not in text
    assert "showcase-private" not in text
    assert str(scenario["ve_private"].id) not in text


def test_skill_map_uses_public_experiences_only(client, scenario):
    data = client.get(f"/public/talents/{SLUG}").json()
    skills = {s["name_tr"]: s for s in data["skills"]}

    # Python: STRONG from public experience 1, seen in both public experiences.
    assert skills["Python"]["strength"] == "STRONG"
    assert skills["Python"]["experience_count"] == 2
    # SQL is STRONG only in the PRIVATE experience; public evidence is WEAK.
    assert skills["SQL"]["strength"] == "WEAK"
    assert skills["SQL"]["experience_count"] == 1
    assert skills["Python"]["attested"] is True
    # React: deliverable evidence on a public experience, never attested.
    assert skills["React"]["attested"] is False
    assert skills["React"]["strength"] == "MODERATE"
    assert set(skills) == {"Python", "SQL", "React"}
    # Attested first, then by strength.
    assert [s["name_tr"] for s in data["skills"]] == ["Python", "SQL", "React"]


def test_revoked_attestation_is_dropped(client, scenario):
    data = client.get(f"/public/talents/{SLUG}").json()

    assert "Geri Çekilmiş Yetkinlik" not in {s["name_tr"] for s in data["skills"]}
    for ve in data["verified_experiences"]:
        assert "Geri Çekilmiş Yetkinlik" not in {s["name_tr"] for s in ve["skills"]}


def test_experience_cards_carry_token_trust_and_skills(client, scenario):
    data = client.get(f"/public/talents/{SLUG}").json()
    experiences = data["verified_experiences"]

    # Newest first.
    assert [ve["public_token"] for ve in experiences] == ["showcase-public-1", "showcase-public-2"]
    first, second = experiences
    assert first["organization_trust_level"] == "T3"
    assert second["organization_trust_level"] == "T1"
    assert [s["name_tr"] for s in first["skills"]] == ["Python"]
    assert first["skills"][0]["attestor_organization"] == "Açık Kuruluş A.Ş."
    assert {s["name_tr"] for s in second["skills"]} == {"Python", "SQL"}
    # Evidence-only skills are listed separately; an attested skill is not repeated.
    assert [s["name_tr"] for s in first["evidenced_skills"]] == ["React"]
    assert second["evidenced_skills"] == []


def test_attesting_organization_count_ignores_private(client, scenario):
    data = client.get(f"/public/talents/{SLUG}").json()

    assert data["attesting_organization_count"] == 2


def test_token_links_resolve_to_verification(client, scenario):
    data = client.get(f"/public/talents/{SLUG}").json()

    for ve in data["verified_experiences"]:
        assert client.get(f"/public/v/{ve['public_token']}").status_code == 200
