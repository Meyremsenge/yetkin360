"""
Authorization tests for GET /talents/me/institution-link-requests (YET-197/IS-10).

Implements the BOLA/401/404 matrix for a talent's own institution link request history.

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Talent isolation verification: Talent A vs B (same principle as
  test_verified_experiences_authorization.py's AC-9/AC-S1)

Key principle: "404 sızdırmama" — talent-less principal gets 404, not 401
(the principal IS authenticated, just has no talent profile to scope by).
"""

import pytest

from app.models import Institution, InstitutionLinkRequest, TalentProfile, User


@pytest.fixture
def user_talent_a(session):
    user = User(email="link-authz-talent-a@example.com", password_hash="hash_a")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_b(session):
    user = User(email="link-authz-talent-b@example.com", password_hash="hash_b")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_no_talent(session):
    """Authenticated user with NO talent profile (e.g. ORG_MEMBER)."""
    user = User(email="link-authz-no-talent@example.com", password_hash="hash_no_talent")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent_a(session, user_talent_a):
    profile = TalentProfile(user_id=user_talent_a.id, full_name="Link Authz Talent A", visibility="PRIVATE")
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_b(session, user_talent_b):
    profile = TalentProfile(user_id=user_talent_b.id, full_name="Link Authz Talent B", visibility="PRIVATE")
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def institution_z(session):
    inst = Institution(name="Institution Z", domain="z.edu.tr", verification_level="T1", status="ACTIVE")
    session.add(inst)
    session.flush()
    return inst


def test_talent_a_sees_only_own_requests_not_talent_b(
    client, session, talent_a, talent_b, user_talent_a, institution_z
):
    """
    BOLA (core): Talent A's request list never contains Talent B's requests,
    even though both target the same institution.
    """
    req_a = InstitutionLinkRequest(talent_profile_id=talent_a.id, institution_id=institution_z.id, status="PENDING")
    req_b = InstitutionLinkRequest(talent_profile_id=talent_b.id, institution_id=institution_z.id, status="PENDING")
    session.add_all([req_a, req_b])
    session.flush()

    response = client.get(
        "/talents/me/institution-link-requests",
        headers={"X-Debug-User-Id": str(user_talent_a.id)},
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    items = response.json()["items"]
    assert len(items) == 1, f"Expected only A's own request, got {len(items)}"
    assert items[0]["id"] == str(req_a.id)

    # Talent B's request id must never appear in A's response body
    assert str(req_b.id) not in response.text


def test_org_member_without_talent_profile_returns_404(client, user_no_talent):
    """
    Authenticated but talent-less principal → 404 (not 401) — same design decision
    as GET /talents/me/verified-experiences (AC-11/AC-S3).
    """
    response = client.get(
        "/talents/me/institution-link-requests",
        headers={"X-Debug-User-Id": str(user_no_talent.id)},
    )

    assert response.status_code == 404, (
        f"Expected 404 for talent-less principal, got {response.status_code}: {response.text}"
    )
    assert response.json()["code"] == "TALENT_PROFILE_NOT_FOUND"


def test_unauthenticated_returns_401(client):
    """No X-Debug-User-Id header → 401."""
    response = client.get("/talents/me/institution-link-requests")

    assert response.status_code == 401, (
        f"Expected 401 for unauthenticated, got {response.status_code}: {response.text}"
    )


def test_invalid_session_user_returns_401(client):
    """A user id that doesn't exist in the DB → 401 (invalid session), not 404/500."""
    nonexistent_user_id = "550e8400-e29b-41d4-a716-446655440099"

    response = client.get(
        "/talents/me/institution-link-requests",
        headers={"X-Debug-User-Id": nonexistent_user_id},
    )

    assert response.status_code == 401, (
        f"Expected 401 for invalid session user, got {response.status_code}: {response.text}"
    )
