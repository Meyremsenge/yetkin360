"""
Organization showcase — privacy boundary tests (SPRINT G).

GET /public/organizations/{id} is auth-free. A record appears only with double
consent: the organization switched its showcase on, the record is PUBLIC and
the talent's profile is PUBLIC (with a slug, not deleted). These tests pin
every way a record must stay hidden, the identical 404 for unknown/deleted/
suspended organizations, tenant isolation between organizations, and that no
e-mail or internal id leaks.
"""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from app.models import (
    Attestation,
    Engagement,
    Institution,
    Organization,
    Skill,
    TalentProfile,
    User,
    VerifiedExperience,
)


def _org(session, name: str, *, showcase: bool = True, level: str = "T3", **extra) -> Organization:
    org = Organization(
        name=name,
        verification_level=level,
        domain=f"{uuid4().hex[:8]}.example.com",
        showcase_public=showcase,
        **extra,
    )
    session.add(org)
    session.flush()
    return org


def _talent(session, slug: str | None, *, visibility: str = "PUBLIC", deleted: bool = False) -> TalentProfile:
    user = User(email=f"{uuid4().hex[:8]}@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    profile = TalentProfile(
        user_id=user.id,
        full_name=f"Kişi {slug or uuid4().hex[:6]}",
        visibility=visibility,
        public_slug=slug,
        deleted_at=datetime.now(timezone.utc) if deleted else None,
    )
    session.add(profile)
    session.flush()
    return profile


def _record(
    session,
    talent,
    org,
    token: str,
    *,
    visibility: str = "PUBLIC",
    started: date = date(2026, 3, 1),
    institution: Institution | None = None,
) -> VerifiedExperience:
    engagement = Engagement(
        id=uuid4(),
        kind="INTERNSHIP",
        talent_id=talent.id,
        organization_id=org.id,
        institution_id=institution.id if institution else None,
        title=f"Rol {token}",
        started_on=started,
        ended_on=date(started.year, started.month + 2, 1),
        status="VERIFIED",
    )
    session.add(engagement)
    session.flush()
    ve = VerifiedExperience(
        talent_id=talent.id,
        engagement_id=engagement.id,
        organization_name_snapshot=org.name,
        role_snapshot=engagement.title,
        institution_name_snapshot=institution.name if institution else None,
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


def _attest(session, ve, org, skill: Skill, *, revoked: bool = False) -> Attestation:
    attestor = User(email=f"attestor-{uuid4().hex[:8]}@example.com", password_hash="hash")
    session.add(attestor)
    session.flush()
    att = Attestation(
        engagement_id=ve.engagement_id,
        talent_id=ve.talent_id,
        subject_type="ENGAGEMENT",
        claim_type="COMPETENCE",
        requested_claim_type="COMPETENCE",
        attestor_user_id=attestor.id,
        attestor_org_id=org.id,
        skill_id=skill.id,
        revoked_at=datetime.now(timezone.utc) if revoked else None,
        revoke_reason="test" if revoked else None,
    )
    session.add(att)
    session.flush()
    return att


def _skill(session, name: str) -> Skill:
    skill = Skill(slug=f"vitrin-{uuid4().hex[:8]}", name_tr=name, category="TOOL")
    session.add(skill)
    session.flush()
    return skill


def _tokens(response) -> list[str]:
    return [item["public_token"] for item in response.json()["experiences"]]


# ----------------------------------------------------------------------------
# Positive: double-consented records are listed
# ----------------------------------------------------------------------------


def test_double_consented_records_are_listed_with_stats(client, session):
    org = _org(session, "Lale Yazılım")
    inst_a = Institution(name="Galata Teknik", verification_level="T3")
    inst_b = Institution(name="Boğaz Üniversitesi", verification_level="T2")
    session.add_all([inst_a, inst_b])
    session.flush()
    ayse = _talent(session, "ayse-vitrin")
    ali = _talent(session, "ali-vitrin")
    _record(session, ayse, org, "tok-ayse", started=date(2026, 7, 1), institution=inst_a)
    _record(session, ali, org, "tok-ali", started=date(2026, 3, 1), institution=inst_b)

    response = client.get(f"/public/organizations/{org.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(org.id)
    assert data["name"] == "Lale Yazılım"
    assert data["showcase_enabled"] is True
    assert data["domain"] == org.domain
    assert data["stats"] == {"verified_public_count": 2, "institution_count": 2}
    # Newest first.
    assert _tokens(response) == ["tok-ayse", "tok-ali"]
    first = data["experiences"][0]
    assert first["talent_display_name"] == ayse.full_name
    assert first["talent_public_slug"] == "ayse-vitrin"
    assert first["institution_name"] == "Galata Teknik"
    assert first["started_on"] == "2026-07-01"


def test_unverified_domain_is_hidden(client, session):
    org = _org(session, "Doğrulanmamış Ltd.", level="T1")

    data = client.get(f"/public/organizations/{org.id}").json()

    assert data["domain"] is None
    assert org.domain not in client.get(f"/public/organizations/{org.id}").text


def test_skills_come_from_active_attestations_only(client, session):
    org = _org(session, "Beceri A.Ş.")
    talent = _talent(session, "beceri-kisi")
    ve = _record(session, talent, org, "tok-beceri")
    _attest(session, ve, org, _skill(session, "React Native"))
    _attest(session, ve, org, _skill(session, "Geri Çekilen Beceri"), revoked=True)

    data = client.get(f"/public/organizations/{org.id}").json()

    assert data["experiences"][0]["skills"] == ["React Native"]


# ----------------------------------------------------------------------------
# AC-S1 / AC-S2 / AC-S3: hidden records
# ----------------------------------------------------------------------------


@pytest.mark.parametrize("visibility", ["PRIVATE", "INSTITUTION", "ORGANIZATIONS"])
def test_non_public_record_never_surfaces(client, session, visibility):
    org = _org(session, "Gizlilik A.Ş.")
    talent = _talent(session, f"kisi-{visibility.lower()}")
    _record(session, talent, org, f"tok-{visibility.lower()}", visibility=visibility)

    response = client.get(f"/public/organizations/{org.id}")

    assert response.status_code == 200
    assert response.json()["experiences"] == []
    assert response.json()["stats"]["verified_public_count"] == 0
    assert f"tok-{visibility.lower()}" not in response.text
    assert talent.full_name not in response.text


@pytest.mark.parametrize("visibility", ["PRIVATE", "INSTITUTION", "ORGANIZATIONS"])
def test_public_record_of_non_public_profile_never_surfaces(client, session, visibility):
    org = _org(session, "Profil Gizli A.Ş.")
    talent = _talent(session, f"profil-{visibility.lower()}", visibility=visibility)
    _record(session, talent, org, f"tok-profil-{visibility.lower()}")

    response = client.get(f"/public/organizations/{org.id}")

    assert response.json()["experiences"] == []
    assert response.json()["stats"]["verified_public_count"] == 0
    assert talent.full_name not in response.text


def test_profile_without_slug_or_deleted_never_surfaces(client, session):
    org = _org(session, "Silinmiş Kişi A.Ş.")
    no_slug = _talent(session, None)
    deleted = _talent(session, "silinmis-kisi", deleted=True)
    _record(session, no_slug, org, "tok-no-slug")
    _record(session, deleted, org, "tok-deleted")

    response = client.get(f"/public/organizations/{org.id}")

    assert response.json()["experiences"] == []
    assert "silinmis-kisi" not in response.text


def test_fully_revoked_record_never_surfaces(client, session):
    org = _org(session, "İptal A.Ş.")
    talent = _talent(session, "iptal-kisi")
    ve = _record(session, talent, org, "tok-revoked")
    _attest(session, ve, org, _skill(session, "Python"), revoked=True)

    response = client.get(f"/public/organizations/{org.id}")

    assert response.json()["experiences"] == []
    assert response.json()["stats"]["verified_public_count"] == 0


# ----------------------------------------------------------------------------
# AC-S4: showcase switched off / organization not public
# ----------------------------------------------------------------------------


def test_showcase_off_returns_card_without_records(client, session):
    org = _org(session, "Kapalı Vitrin A.Ş.", showcase=False)
    talent = _talent(session, "kapali-kisi")
    _record(session, talent, org, "tok-kapali")

    response = client.get(f"/public/organizations/{org.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["showcase_enabled"] is False
    assert data["experiences"] == []
    assert data["stats"] == {"verified_public_count": 0, "institution_count": 0}
    assert "tok-kapali" not in response.text


@pytest.mark.parametrize(
    "extra",
    [
        {"deleted_at": datetime(2026, 1, 1, tzinfo=timezone.utc)},
        {"status": "SUSPENDED"},
    ],
    ids=["deleted", "suspended"],
)
def test_hidden_organization_is_indistinguishable_from_unknown(client, session, extra):
    org = _org(session, "Görünmez A.Ş.", **extra)
    talent = _talent(session, "gorunmez-kisi")
    _record(session, talent, org, "tok-gorunmez")

    hidden = client.get(f"/public/organizations/{org.id}")
    unknown = client.get(f"/public/organizations/{uuid4()}")

    assert hidden.status_code == unknown.status_code == 404
    hidden_body, unknown_body = hidden.json(), unknown.json()
    hidden_body.pop("request_id", None)
    unknown_body.pop("request_id", None)
    assert hidden_body == unknown_body
    assert hidden_body["code"] == "ORGANIZATION_NOT_FOUND"


# ----------------------------------------------------------------------------
# Tenant isolation and PII (AC-S5)
# ----------------------------------------------------------------------------


def test_other_organizations_records_never_surface(client, session):
    org_a = _org(session, "A Kuruluşu")
    org_b = _org(session, "B Kuruluşu")
    talent = _talent(session, "iki-kurulus")
    _record(session, talent, org_a, "tok-a")
    _record(session, talent, org_b, "tok-b")

    assert _tokens(client.get(f"/public/organizations/{org_a.id}")) == ["tok-a"]
    assert _tokens(client.get(f"/public/organizations/{org_b.id}")) == ["tok-b"]


def test_no_email_or_internal_ids_leak(client, session):
    org = _org(session, "Sızıntı Yok A.Ş.")
    talent = _talent(session, "sizinti-kisi")
    ve = _record(session, talent, org, "tok-sizinti")
    _attest(session, ve, org, _skill(session, "SQL"))
    owner = session.get(User, talent.user_id)

    response = client.get(f"/public/organizations/{org.id}")
    text = response.text

    assert "@" not in text
    assert owner.email not in text
    for internal_id in (talent.id, talent.user_id, ve.id, ve.engagement_id):
        assert str(internal_id) not in text
    assert set(response.json()["experiences"][0]) == {
        "role_snapshot",
        "started_on",
        "ended_on",
        "talent_display_name",
        "talent_public_slug",
        "institution_name",
        "public_token",
        "skills",
    }
