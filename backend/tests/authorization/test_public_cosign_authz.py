"""
"Çift imza" badge and evaluator line on public pages — privacy tests (SPRINT K).

/public/v/{token} and /public/talents/{slug} carry co_signed + evaluator
{display_name: "Ad S.", unit}. These tests pin: the badge needs an organization
member's ORG_TO_TALENT evaluation AND an institution-linked engagement; the
evaluator's full surname, e-mail and private note never leak; a deleted
evaluator profile drops the name only; and nothing of this surfaces for a
non-PUBLIC or fully revoked experience.
"""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from app.models import (
    Attestation,
    Engagement,
    Evaluation,
    Institution,
    Organization,
    OrganizationMember,
    TalentProfile,
    User,
    VerifiedExperience,
)
from app.services.public_profile import short_display_name

PRIVATE_NOTE = "gizli-degerlendirme-notu"


def _user(session, full_name: str | None, *, deleted: bool = False) -> User:
    user = User(email=f"{uuid4().hex[:8]}@lale.example.com", password_hash="hash")
    session.add(user)
    session.flush()
    if full_name is not None:
        session.add(
            TalentProfile(
                user_id=user.id,
                full_name=full_name,
                deleted_at=datetime.now(timezone.utc) if deleted else None,
            )
        )
        session.flush()
    return user


@pytest.fixture
def org(session):
    row = Organization(name="Lale Yazılım", verification_level="T3")
    session.add(row)
    session.flush()
    return row


@pytest.fixture
def institution(session):
    row = Institution(name="Galata Teknik", verification_level="T3")
    session.add(row)
    session.flush()
    return row


@pytest.fixture
def talent(session):
    user = _user(session, None)
    profile = TalentProfile(user_id=user.id, full_name="Ayşe Yılmaz", visibility="PUBLIC", public_slug="ayse-cift-imza")
    session.add(profile)
    session.flush()
    return profile


def _member(session, org, user, unit: str | None = "Yazılım") -> OrganizationMember:
    member = OrganizationMember(organization_id=org.id, user_id=user.id, role="MEMBER", unit=unit)
    session.add(member)
    session.flush()
    return member


def _experience(session, talent, org, token, *, institution=None, visibility="PUBLIC", revoked=False):
    engagement = Engagement(
        id=uuid4(),
        kind="INTERNSHIP",
        talent_id=talent.id,
        organization_id=org.id,
        institution_id=institution.id if institution else None,
        title=f"Rol {token}",
        started_on=date(2026, 7, 1),
        ended_on=date(2026, 9, 1),
        status="VERIFIED",
    )
    session.add(engagement)
    session.flush()
    sealer = _user(session, "Mühür Veren")
    session.add(
        Attestation(
            engagement_id=engagement.id,
            talent_id=talent.id,
            subject_type="ENGAGEMENT",
            claim_type="COMPETENCE",
            requested_claim_type="COMPETENCE",
            attestor_user_id=sealer.id,
            attestor_org_id=org.id,  # create_attestation always sets it, also for a coordinator's seal
            revoked_at=datetime.now(timezone.utc) if revoked else None,
            revoke_reason="test" if revoked else None,
        )
    )
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
    return engagement


def _evaluate(session, engagement, evaluator: User, direction: str = "ORG_TO_TALENT") -> None:
    session.add(
        Evaluation(
            engagement_id=engagement.id,
            evaluator_user_id=evaluator.id,
            direction=direction,
            submitted_at=datetime.now(timezone.utc),
            private_note=PRIVATE_NOTE,
        )
    )
    session.flush()


def _profile_card(client, token):
    data = client.get("/public/talents/ayse-cift-imza").json()
    return next(ve for ve in data["verified_experiences"] if ve["public_token"] == token)


# ----------------------------------------------------------------------------
# Positive: co-signed record
# ----------------------------------------------------------------------------


def test_co_signed_record_shows_badge_and_short_evaluator(client, session, org, institution, talent):
    evaluator = _user(session, "Mehmet Ali Kaya")
    _member(session, org, evaluator, unit="Yazılım")
    engagement = _experience(session, talent, org, "tok-cift", institution=institution)
    _evaluate(session, engagement, evaluator)

    response = client.get("/public/v/tok-cift")

    assert response.status_code == 200
    data = response.json()
    assert data["co_signed"] is True
    assert data["evaluator"] == {"display_name": "Mehmet Ali K.", "unit": "Yazılım"}
    card = _profile_card(client, "tok-cift")
    assert card["co_signed"] is True
    assert card["evaluator"] == {"display_name": "Mehmet Ali K.", "unit": "Yazılım"}


def test_no_surname_email_or_private_note_leaks(client, session, org, institution, talent):
    evaluator = _user(session, "Mehmet Kaya")
    _member(session, org, evaluator)
    engagement = _experience(session, talent, org, "tok-pii", institution=institution)
    _evaluate(session, engagement, evaluator)

    for response in (client.get("/public/v/tok-pii"), client.get("/public/talents/ayse-cift-imza")):
        assert "Kaya" not in response.text
        assert evaluator.email not in response.text
        assert PRIVATE_NOTE not in response.text
        assert str(evaluator.id) not in response.text


# ----------------------------------------------------------------------------
# Single signature: no badge
# ----------------------------------------------------------------------------


def test_without_institution_is_not_co_signed(client, session, org, talent):
    evaluator = _user(session, "Zeynep Ak")
    _member(session, org, evaluator, unit=None)
    engagement = _experience(session, talent, org, "tok-kurumsuz")
    _evaluate(session, engagement, evaluator)

    data = client.get("/public/v/tok-kurumsuz").json()

    assert data["co_signed"] is False
    assert data["evaluator"] == {"display_name": "Zeynep A.", "unit": None}


def test_without_org_evaluation_is_not_co_signed(client, session, org, institution, talent):
    engagement = _experience(session, talent, org, "tok-degerlendirmesiz", institution=institution)
    _evaluate(session, engagement, _user(session, "Öğrenci Kendisi"), direction="TALENT_TO_ORG")

    data = client.get("/public/v/tok-degerlendirmesiz").json()

    assert data["co_signed"] is False
    assert data["evaluator"] is None


def test_evaluation_by_non_member_does_not_count(client, session, org, institution, talent):
    outsider = _user(session, "Dış Kişi")
    other_org = Organization(name="Başka A.Ş.", verification_level="T3")
    session.add(other_org)
    session.flush()
    _member(session, other_org, outsider)
    engagement = _experience(session, talent, org, "tok-yabanci", institution=institution)
    _evaluate(session, engagement, outsider)

    data = client.get("/public/v/tok-yabanci").json()

    assert data["co_signed"] is False
    assert data["evaluator"] is None
    assert "Dış" not in client.get("/public/v/tok-yabanci").text


def test_deleted_evaluator_profile_drops_name_keeps_unit(client, session, org, institution, talent):
    evaluator = _user(session, "Silinmiş Değerlendiren", deleted=True)
    _member(session, org, evaluator, unit="Veri")
    engagement = _experience(session, talent, org, "tok-silinmis", institution=institution)
    _evaluate(session, engagement, evaluator)

    response = client.get("/public/v/tok-silinmis")

    assert response.json()["co_signed"] is True
    assert response.json()["evaluator"] == {"display_name": None, "unit": "Veri"}
    assert "Silinmiş" not in response.text


# ----------------------------------------------------------------------------
# AC-S: nothing surfaces for hidden experiences
# ----------------------------------------------------------------------------


@pytest.mark.parametrize("visibility", ["PRIVATE", "INSTITUTION", "ORGANIZATIONS"])
def test_non_public_experience_leaks_no_badge_or_name(client, session, org, institution, talent, visibility):
    evaluator = _user(session, "Gizli Değerlendiren")
    _member(session, org, evaluator)
    token = f"tok-{visibility.lower()}"
    engagement = _experience(session, talent, org, token, institution=institution, visibility=visibility)
    _evaluate(session, engagement, evaluator)

    verification = client.get(f"/public/v/{token}")
    profile = client.get("/public/talents/ayse-cift-imza")

    assert verification.status_code == 404
    assert "Gizli" not in verification.text
    assert profile.status_code == 200
    assert profile.json()["verified_experiences"] == []
    assert "Gizli" not in profile.text
    assert "co_signed\":true" not in profile.text.replace(" ", "")


def test_fully_revoked_experience_has_no_badge(client, session, org, institution, talent):
    evaluator = _user(session, "İptal Değerlendiren")
    _member(session, org, evaluator)
    engagement = _experience(session, talent, org, "tok-iptal", institution=institution, revoked=True)
    _evaluate(session, engagement, evaluator)

    assert client.get("/public/v/tok-iptal").status_code == 404
    profile = client.get("/public/talents/ayse-cift-imza")
    assert profile.json()["verified_experiences"] == []
    assert "İptal" not in profile.text


@pytest.mark.parametrize(
    ("full_name", "expected"),
    [
        ("Mehmet Kaya", "Mehmet K."),
        ("Mehmet Ali Kaya", "Mehmet Ali K."),
        ("ilker ışık", "ilker I."),
        ("Selin  irmak", "Selin İ."),
        ("Ali", "Ali"),
        ("   ", None),
        (None, None),
    ],
)
def test_short_display_name_never_has_full_surname(full_name, expected):
    assert short_display_name(full_name) == expected
