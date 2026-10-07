"""
YET-230 (L-05) regression: public endpoints must not expose internal talent/user
UUIDs, and GET /public/v/{token} must not resolve for a soft-deleted talent.

- GET /public/talents/{slug} used to return `talent_id`, which an ORG member could
  feed to POST /engagements (GUV-08).
- GET /public/v/{token} ignored talent_profiles.deleted_at, while
  GET /public/talents/{slug} honours it.
"""

from datetime import date, datetime, timezone

import pytest

from app.models import Engagement, Organization, TalentProfile, User, VerifiedExperience

SLUG = "l05-public-talent"
TOKEN = "l05-public-token"


@pytest.fixture
def user(session):
    row = User(email="l05-talent@example.com", password_hash="hash_l05")
    session.add(row)
    session.flush()
    return row


@pytest.fixture
def profile(session, user):
    row = TalentProfile(user_id=user.id, full_name="L05 Talent", visibility="PUBLIC", public_slug=SLUG)
    session.add(row)
    session.flush()
    return row


@pytest.fixture
def public_ve(session, profile):
    org = Organization(name="L05 Org", verification_level="T2", status="ACTIVE")
    session.add(org)
    session.flush()
    engagement = Engagement(
        talent_id=profile.id,
        organization_id=org.id,
        kind="INTERNSHIP",
        title="L05 Engagement",
        status="VERIFIED",
        started_on=date(2025, 1, 1),
        ended_on=date(2025, 6, 30),
        confidential=False,
    )
    session.add(engagement)
    session.flush()
    ve = VerifiedExperience(
        talent_id=profile.id,
        engagement_id=engagement.id,
        organization_name_snapshot="L05 Org",
        role_snapshot="Intern",
        started_on_snapshot=date(2025, 1, 1),
        ended_on_snapshot=date(2025, 6, 30),
        institution_name_snapshot=None,
        claim_type="COMPETENCE",
        visibility="PUBLIC",
        public_token=TOKEN,
    )
    session.add(ve)
    session.flush()
    return ve


def _error_body(response) -> dict:
    body = dict(response.json())
    body.pop("request_id", None)
    return body


def test_public_profile_does_not_expose_talent_or_user_id(client, profile, user, public_ve):
    response = client.get(f"/public/talents/{SLUG}")

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"display_name", "verified_experiences"}
    assert str(profile.id) not in response.text
    assert str(user.id) not in response.text


def test_public_verification_does_not_expose_talent_or_user_id(client, profile, user, public_ve):
    response = client.get(f"/public/v/{TOKEN}")

    assert response.status_code == 200
    assert "talent_id" not in response.json()
    assert str(profile.id) not in response.text
    assert str(user.id) not in response.text


def test_public_verification_resolves_for_live_talent(client, profile, public_ve):
    response = client.get(f"/public/v/{TOKEN}")

    assert response.status_code == 200
    assert response.json()["talent_name"] == "L05 Talent"


def test_public_verification_of_deleted_talent_is_indistinguishable_from_unknown_token(
    client, session, profile, public_ve
):
    unknown = client.get("/public/v/l05_token_that_does_not_exist")

    profile.deleted_at = datetime.now(timezone.utc)
    session.flush()
    deleted = client.get(f"/public/v/{TOKEN}")

    assert unknown.status_code == deleted.status_code == 404
    assert deleted.json()["code"] == "VERIFICATION_NOT_FOUND"
    assert _error_body(deleted) == _error_body(unknown)


def test_public_profile_of_deleted_talent_is_404(client, session, profile, public_ve):
    profile.deleted_at = datetime.now(timezone.utc)
    session.flush()

    response = client.get(f"/public/talents/{SLUG}")

    assert response.status_code == 404
    assert response.json()["code"] == "TALENT_NOT_FOUND"
