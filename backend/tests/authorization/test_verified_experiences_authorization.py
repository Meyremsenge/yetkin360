"""
Verified Experience authorization tests (YET-111 — PLAN 3.7 profil sayfası).

Implements AC-7, AC-8, AC-9/AC-S1, AC-10/AC-S2, AC-11/AC-S3 from atdd.md.

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Talent isolation verification: Talent A vs B
- Defense-in-depth: scoped_own_verified_experiences() verification

AC-7: Authenticated talent returns own verified experiences (all visibility levels, including PRIVATE)
AC-8: Talent with no verified experiences returns 200 + empty list (not 404)
AC-9/AC-S1: Authenticated talent sees ONLY own records — cross-talent data never leaks
AC-10/AC-S2: Unauthenticated request → 401
AC-11/AC-S3: Authenticated but talent-less principal → 404 (not 401 — "talent not found")

Key principle: "404 sızdırmama ve talent filtresi" — verified experiences scoped to principal.talent_id
(from session principal), not from URL/body. Talent olmayan principal'a 404 (401 değil) dönmesi,
talent'ın kendi PRIVATE kayıtlarını görmesi tasarım kararı.
"""

import pytest
from datetime import date, datetime
from uuid import uuid4

from app.models import (
    User,
    Organization,
    Institution,
    Engagement,
    VerifiedExperience,
)


@pytest.fixture
def user_no_talent(session):
    """Authenticated user with NO talent profile (ORG_MEMBER/COORDINATOR, etc.)."""
    user = User(email="org-member@example.com", password_hash="hash_org_member")
    session.add(user)
    session.flush()
    return user


# ============================================================================
# Organization & Institution Fixtures (for verified experience snapshots)
# ============================================================================


@pytest.fixture
def organization_a(session):
    """Test organization A (used by talent_a engagements)."""
    org = Organization(
        name="Organization-A-Only-Org",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def organization_b(session):
    """Test organization B (used by talent_b engagements) — for cross-talent isolation test."""
    org = Organization(
        name="Organization-B-Only-Org",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def institution_a(session):
    """Test institution A."""
    inst = Institution(
        name="Test Institution A",
        domain="testaaa.edu.tr",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def institution_b(session):
    """Test institution B."""
    inst = Institution(
        name="Test Institution B",
        domain="testbbb.edu.tr",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


# ============================================================================
# Engagement Fixtures (for verified experience creation)
# ============================================================================


@pytest.fixture
def engagement_a1(session, talent_a, organization_a, institution_a):
    """Engagement for talent_a at organization_a (verified → creates VerifiedExperience)."""
    eng = Engagement(
        id=uuid4(),
        kind="INTERNSHIP",
        talent_id=talent_a.id,  # conftest.py's talent_a is TalentProfile, use its id
        organization_id=organization_a.id,
        institution_id=institution_a.id,
        title="Senior Engineer at A",
        started_on=date(2020, 1, 1),
        ended_on=date(2022, 12, 31),
        status="VERIFIED",
    )
    session.add(eng)
    session.flush()
    return eng


@pytest.fixture
def engagement_b1(session, talent_b, organization_b, institution_b):
    """Engagement for talent_b at organization_b (for cross-talent isolation test)."""
    eng = Engagement(
        id=uuid4(),
        kind="INTERNSHIP",
        talent_id=talent_b.id,  # conftest.py's talent_b is TalentProfile
        organization_id=organization_b.id,
        institution_id=institution_b.id,
        title="Product Manager at B",
        started_on=date(2019, 6, 1),
        ended_on=date(2021, 5, 31),
        status="VERIFIED",
    )
    session.add(eng)
    session.flush()
    return eng


# ============================================================================
# VerifiedExperience Fixtures
# ============================================================================


@pytest.fixture
def verified_exp_a1_private(session, talent_a, engagement_a1, organization_a, institution_a):
    """VerifiedExperience for talent_a, PRIVATE visibility."""
    ve = VerifiedExperience(
        id=uuid4(),
        talent_id=talent_a.id,  # conftest.py's talent_a is TalentProfile
        engagement_id=engagement_a1.id,
        organization_name_snapshot=organization_a.name,
        role_snapshot=engagement_a1.title,
        started_on_snapshot=engagement_a1.started_on,
        ended_on_snapshot=engagement_a1.ended_on,
        institution_name_snapshot=institution_a.name,
        claim_type="COMPETENCE",
        visibility="PRIVATE",  # AC-7: PRIVATE records visible to owner
        public_token="token_a1",
        created_at=datetime.now(),
    )
    session.add(ve)
    session.flush()
    return ve


@pytest.fixture
def verified_exp_a2_public(session, talent_a, organization_a):
    """Another VerifiedExperience for talent_a, PUBLIC visibility."""
    eng2 = Engagement(
        id=uuid4(),
        kind="INTERNSHIP",
        talent_id=talent_a.id,
        organization_id=organization_a.id,
        institution_id=None,
        title="Consultant at StartUp",
        started_on=date(2023, 1, 1),
        ended_on=None,  # Ongoing
        status="VERIFIED",
    )
    session.add(eng2)
    session.flush()

    ve = VerifiedExperience(
        id=uuid4(),
        talent_id=talent_a.id,
        engagement_id=eng2.id,
        organization_name_snapshot=organization_a.name,
        role_snapshot=eng2.title,
        started_on_snapshot=eng2.started_on,
        ended_on_snapshot=eng2.ended_on,
        institution_name_snapshot=None,
        claim_type="PARTICIPATION",
        visibility="PUBLIC",
        public_token="token_a2",
        created_at=datetime.now(),
    )
    session.add(ve)
    session.flush()
    return ve


@pytest.fixture
def verified_exp_b1_public(session, talent_b, engagement_b1, organization_b):
    """VerifiedExperience for talent_b (for cross-talent isolation test)."""
    ve = VerifiedExperience(
        id=uuid4(),
        talent_id=talent_b.id,
        engagement_id=engagement_b1.id,
        organization_name_snapshot=organization_b.name,
        role_snapshot=engagement_b1.title,
        started_on_snapshot=engagement_b1.started_on,
        ended_on_snapshot=engagement_b1.ended_on,
        institution_name_snapshot=None,
        claim_type="CONTRIBUTION",
        visibility="PUBLIC",
        public_token="token_b1",
        created_at=datetime.now(),
    )
    session.add(ve)
    session.flush()
    return ve


# ============================================================================
# Tests: AC-7, AC-8, AC-9/AC-S1, AC-10/AC-S2, AC-11/AC-S3
# ============================================================================


def test_ac7_authenticated_talent_gets_own_verified_experiences(
    client, user_talent_a, verified_exp_a1_private, verified_exp_a2_public
):
    """
    AC-7 (Critical): Authenticated talent returns own verified experiences.

    Given: Talent A has ≥1 verified experience (including PRIVATE)
    When: GET /talents/me/verified-experiences is called
    Then: 200 + response items contain ALL fields (id, organization_name_snapshot,
          role_snapshot, started_on_snapshot, ended_on_snapshot, institution_name_snapshot,
          claim_type, visibility, public_token, created_at). PRIVATE records are included.
    """
    response = client.get(
        "/talents/me/verified-experiences",
        headers={"X-Debug-User-Id": str(user_talent_a.id)},
    )

    # Status: exactly 200
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"

    data = response.json()
    assert "items" in data, f"Response missing 'items' key: {data}"
    items = data["items"]

    # Should have 2 verified experiences
    assert len(items) == 2, f"Expected 2 items, got {len(items)}"

    # Verify first item (PRIVATE) has all required fields
    item_private = next((i for i in items if i["visibility"] == "PRIVATE"), None)
    assert item_private is not None, f"Expected PRIVATE visibility in response, got: {items}"

    required_fields = {
        "id",
        "organization_name_snapshot",
        "role_snapshot",
        "started_on_snapshot",
        "ended_on_snapshot",
        "institution_name_snapshot",
        "claim_type",
        "visibility",
        "public_token",
        "created_at",
    }
    assert set(item_private.keys()) >= required_fields, (
        f"Item missing required fields. Expected {required_fields}, "
        f"got {set(item_private.keys())}"
    )

    # Verify second item (PUBLIC) has all fields
    item_public = next((i for i in items if i["visibility"] == "PUBLIC"), None)
    assert item_public is not None, f"Expected PUBLIC visibility in response, got: {items}"
    assert set(item_public.keys()) >= required_fields

    # Spot-check snapshot values
    assert item_private["organization_name_snapshot"] == "Organization-A-Only-Org"
    assert item_private["claim_type"] == "COMPETENCE"
    assert item_private["public_token"] == "token_a1"


def test_ac8_talent_with_no_verified_experiences_returns_empty_list(
    client, user_talent_a, talent_a
):
    """
    AC-8 (High): Talent with no verified experiences returns 200 + empty items.

    Given: Talent A has NO verified experiences
    When: GET /talents/me/verified-experiences is called
    Then: 200 + {"items": []} (not 404, not error)

    Note: talent_a fixture is required to ensure TalentProfile exists for the principal,
    even though it's not directly used in the test logic.
    """
    response = client.get(
        "/talents/me/verified-experiences",
        headers={"X-Debug-User-Id": str(user_talent_a.id)},
    )

    # Status: exactly 200
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"

    data = response.json()
    assert "items" in data, f"Response missing 'items' key: {data}"
    assert data["items"] == [], f"Expected empty list, got {data['items']}"


def test_ac9_ac_s1_talent_a_cannot_see_talent_b_records(
    client, user_talent_a, user_talent_b, verified_exp_a1_private, verified_exp_b1_public
):
    """
    AC-9 (Critical) / AC-S1: Cross-talent data never leaks.

    Given: Talent A and B each have verified experiences
    When: Talent A calls GET /talents/me/verified-experiences
    Then: Response contains ONLY A's records. B's organization_name_snapshot ("Organization-B-Only-Org")
          and any B-specific data never appears in response body (checked by full substring).
    """
    response = client.get(
        "/talents/me/verified-experiences",
        headers={"X-Debug-User-Id": str(user_talent_a.id)},
    )

    # Status: exactly 200
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"

    data = response.json()
    items = data["items"]

    # Should have 1 item (talent_a's PRIVATE record — talent_b's PUBLIC record never appears)
    assert len(items) == 1, f"Expected 1 item for talent_a, got {len(items)}"

    # Verify response body does NOT contain talent_b's organization name
    response_str = str(data)
    assert "Organization-B-Only-Org" not in response_str, (
        f"Talent B's organization leaked in response: {data}"
    )

    # Verify all items belong to talent_a
    for item in items:
        assert item["organization_name_snapshot"] == "Organization-A-Only-Org", (
            f"Non-A organization in A's response: {item}"
        )


def test_ac10_ac_s2_unauthenticated_request_returns_401(client):
    """
    AC-10 (High) / AC-S2: Unauthenticated request returns 401.

    Given: No X-Debug-User-Id header (or invalid auth)
    When: GET /talents/me/verified-experiences is called
    Then: 401 (not 404, not 200)
    """
    response = client.get("/talents/me/verified-experiences")

    # Status: exactly 401
    assert response.status_code == 401, (
        f"Expected 401 for unauthenticated, got {response.status_code}: {response.json()}"
    )


def test_ac11_ac_s3_talent_profile_required_returns_404_not_401(
    client, user_no_talent
):
    """
    AC-11 (High) / AC-S3: Authenticated but talent-less principal returns 404 (not 401).

    Given: Authenticated user (valid session) but NO talent profile (e.g., ORG_MEMBER/COORDINATOR)
    When: GET /talents/me/verified-experiences is called
    Then: 404 (not 401 — talent not found, not unauthenticated)

    Key design decision: talent-less principal → 404 means "this principal has no talent",
    not "resource doesn't exist". Prevents information leakage (404 vs 401 distinction).
    """
    response = client.get(
        "/talents/me/verified-experiences",
        headers={"X-Debug-User-Id": str(user_no_talent.id)},
    )

    # Status: exactly 404 (not 401)
    assert response.status_code == 404, (
        f"Expected 404 for talent-less principal, got {response.status_code}: {response.json()}"
    )
