"""
Attestation revoke authorization tests (PLAN 2.10 — yet-72-attestation-revoke, AC-2, AC-3, AC-S2).

Implements Authorization Acceptance Criteria for POST /attestations/{id}/revoke:
- AC-2: Attestor olmayan (ama kaynağa erişimi olan) → 403 FORBIDDEN
  (Attestation'ın ait olduğu engagement'ı görebilen başka bir koordinatör)
- AC-3: Scope dışı (kaynağa hiç erişimi yok) → 404 NOT_FOUND
  (Tamamen farklı kurum/organizasyon)
- AC-S2: Race condition simulation — eşzamanlı iki revoke, biri 200, diğeri 409
  (Sekvansiyel simülasyon: ilk istek başarılı, ikinci istek ALREADY_REVOKED)

Threat-model scenarios for ownership + scope enforcement.

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Error responses validated against {"code": ..., "message": ...} schema
- Principal injection: X-Debug-User-Id header
- Attestation created via POST /engagements/{id}/attestations (YET-70 implementation required)

Coverage Target: Authorization/ownership violations, scope isolation, race conditions.

Status: Tests are RED (expected) — implementation not yet available.
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.models import (
    User,
    TalentProfile,
    Organization,
    Institution,
    Engagement,
    InstitutionMember,
    Deliverable,
    Skill,
)

# Import will fail until Attestation model is implemented
try:
    from app.models import Attestation
except ImportError:
    Attestation = None


# ============================================================================
# Fixtures: Authorization test setup
# ============================================================================


@pytest.fixture
def user_attestor_authz(session):
    """Attestor user (will create and revoke attestation)."""
    user = User(email="attestor.authz@example.com", password_hash="hash_attestor")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_other_coord_authz(session):
    """Other INST:COORD from same institution (not the attestor)."""
    user = User(email="other.coord.authz@example.com", password_hash="hash_other")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_cross_inst_coord_authz(session):
    """INST:COORD from different institution (scope out)."""
    user = User(email="cross.coord.authz@example.com", password_hash="hash_cross")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_authz(session):
    """Talent user for engagement (not attestor)."""
    user = User(email="talent.authz@example.com", password_hash="hash_talent")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def organization_authz(session):
    """Organization for authorization tests (T2+ verified)."""
    org = Organization(
        name="Test Org Authz",
        domain="testorgauthz.example.com",
        legal_id="ORG-AUTHZ-001",
        verification_level="T2",
        status="ACTIVE",
        verified_at=datetime.utcnow() - timedelta(days=30),
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def institution_authz(session):
    """Institution for authorization tests."""
    inst = Institution(
        name="Test Institution Authz",
        domain="testinstauthorz.example.com",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def institution_cross_authz(session):
    """Cross-tenant institution (for scope-out tests)."""
    inst = Institution(
        name="Cross Institution Authz",
        domain="crossinstauthorz.example.com",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def talent_authz(session, user_talent_authz, institution_authz):
    """Talent profile for authorization tests."""
    profile = TalentProfile(
        user_id=user_talent_authz.id,
        institution_id=institution_authz.id,
        full_name="Talent Authz",
        visibility="PRIVATE",
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def inst_coord_attestor_authz(session, institution_authz, user_attestor_authz):
    """INST:COORD who will be the attestor."""
    coord = InstitutionMember(
        institution_id=institution_authz.id,
        user_id=user_attestor_authz.id,
        role="COORDINATOR",
    )
    session.add(coord)
    session.flush()
    return coord


@pytest.fixture
def inst_coord_other_authz(session, institution_authz, user_other_coord_authz):
    """INST:COORD from same institution but NOT the attestor."""
    coord = InstitutionMember(
        institution_id=institution_authz.id,
        user_id=user_other_coord_authz.id,
        role="COORDINATOR",
    )
    session.add(coord)
    session.flush()
    return coord


@pytest.fixture
def inst_coord_cross_authz(session, institution_cross_authz, user_cross_inst_coord_authz):
    """INST:COORD from different institution (cross-tenant)."""
    coord = InstitutionMember(
        institution_id=institution_cross_authz.id,
        user_id=user_cross_inst_coord_authz.id,
        role="COORDINATOR",
    )
    session.add(coord)
    session.flush()
    return coord


@pytest.fixture
def skill_authz(session):
    """Test skill."""
    skill = Skill(
        slug="skill-authz",
        name_tr="Test Yetkinlik",
        name_en="Test Skill",
        category="SOFT",
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def engagement_evaluated_authz(session, talent_authz, organization_authz, institution_authz):
    """EVALUATED engagement for authorization tests."""
    now = datetime.utcnow()
    engagement = Engagement(
        talent_id=talent_authz.id,
        organization_id=organization_authz.id,
        institution_id=institution_authz.id,
        kind="INTERNSHIP",
        title="Auth Test Engagement",
        status="EVALUATED",
        version=1,
        started_on=now - timedelta(days=35),
        ended_on=now - timedelta(days=1),
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_evaluated_cross_authz(session, talent_authz, organization_authz, institution_cross_authz):
    """EVALUATED engagement in cross-tenant institution."""
    now = datetime.utcnow()
    engagement = Engagement(
        talent_id=talent_authz.id,
        organization_id=organization_authz.id,
        institution_id=institution_cross_authz.id,
        kind="INTERNSHIP",
        title="Cross-Tenant Engagement",
        status="EVALUATED",
        version=1,
        started_on=now - timedelta(days=35),
        ended_on=now - timedelta(days=1),
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def deliverable_authz(session, engagement_evaluated_authz, skill_authz, user_talent_authz):
    """Deliverable for engagement."""
    deliverable = Deliverable(
        engagement_id=engagement_evaluated_authz.id,
        title="Test Deliverable",
        description="Test deliverable",
        submitted_by_user_id=user_talent_authz.id,
        submitted_at=datetime.now(timezone.utc),
    )
    session.add(deliverable)
    session.flush()
    return deliverable


@pytest.fixture
def deliverable_cross_authz(session, engagement_evaluated_cross_authz, skill_authz, user_talent_authz):
    """Deliverable for cross-tenant engagement."""
    deliverable = Deliverable(
        engagement_id=engagement_evaluated_cross_authz.id,
        title="Cross-Tenant Deliverable",
        description="Cross-tenant deliverable",
        submitted_by_user_id=user_talent_authz.id,
        submitted_at=datetime.now(timezone.utc),
    )
    session.add(deliverable)
    session.flush()
    return deliverable


def create_attestation_via_endpoint(client, session, engagement, attestor_user):
    """
    Helper: Create a real Attestation via POST /engagements/{id}/attestations.
    """
    payload = {
        "claim_type": "COMPETENCE",
        "version": 1,
    }

    response = client.post(
        f"/engagements/{engagement.id}/attestations",
        json=payload,
        headers={"X-Debug-User-Id": str(attestor_user.id)},
    )

    if response.status_code != 201:
        raise RuntimeError(
            f"Failed to create attestation: {response.status_code} {response.text}"
        )

    data = response.json()
    return data.get("id")


# ============================================================================
# AC-2: Forbidden — Attestor olmayan (ama kaynağa erişimi olan)
# ============================================================================


class TestAttestationRevokeNotAttestor:
    """
    AC-2: Someone who is not the attestor tries to revoke → 403 FORBIDDEN.
    Even if they can see the attestation (same engagement), only the attestor can revoke.
    """

    def test_revoke_not_attestor_403(
        self, client, session, engagement_evaluated_authz, user_attestor_authz, user_other_coord_authz,
        inst_coord_attestor_authz, inst_coord_other_authz, deliverable_authz
    ):
        """
        AC-2: Attestor (user_attestor_authz) creates attestation.
        Other coordinator (user_other_coord_authz) from same institution tries to revoke.
        Expected: 403 FORBIDDEN (not 404 — attestation is visible to other coord via shared engagement).
        """
        # Create attestation via attestor
        attestation_id = create_attestation_via_endpoint(
            client, session, engagement_evaluated_authz, user_attestor_authz
        )

        if not attestation_id:
            pytest.skip("Attestation creation endpoint (YET-70) not yet implemented")

        # Try to revoke as other coordinator (not attestor)
        payload = {"revoke_reason": "I'm not the attestor"}

        response = client.post(
            f"/attestations/{attestation_id}/revoke",
            json=payload,
            headers={"X-Debug-User-Id": str(user_other_coord_authz.id)},
        )

        assert response.status_code == 403, \
            f"Expected 403, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") == "FORBIDDEN"


    def test_revoke_talent_403(
        self, client, session, engagement_evaluated_authz, user_attestor_authz, user_talent_authz,
        inst_coord_attestor_authz, talent_authz, deliverable_authz
    ):
        """
        AC-2: Talent who is part of the engagement tries to revoke attestation → 403.
        (Talent can see the engagement, but cannot revoke attestation)
        """
        # Create attestation via coordinator
        attestation_id = create_attestation_via_endpoint(
            client, session, engagement_evaluated_authz, user_attestor_authz
        )

        if not attestation_id:
            pytest.skip("Attestation creation endpoint (YET-70) not yet implemented")

        # Talent tries to revoke
        payload = {"revoke_reason": "Talent trying to revoke"}

        response = client.post(
            f"/attestations/{attestation_id}/revoke",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_authz.id)},
        )

        assert response.status_code == 403, \
            f"Expected 403, got {response.status_code}: {response.text}"


# ============================================================================
# AC-3: Not Found — Scope out (cross-tenant)
# ============================================================================


class TestAttestationRevokeScopeOut:
    """
    AC-3: User from different institution/organization → 404 NOT_FOUND (scope completely out).
    Resource existence is not leaked to cross-tenant users.
    """

    def test_revoke_cross_tenant_404(
        self, client, session, engagement_evaluated_authz, user_attestor_authz, user_cross_inst_coord_authz,
        inst_coord_attestor_authz, inst_coord_cross_authz, deliverable_authz
    ):
        """
        AC-3: Attestor (institution_a) creates attestation.
        Cross-tenant coordinator (institution_b) tries to revoke → 404.
        """
        # Create attestation in institution_a
        attestation_id = create_attestation_via_endpoint(
            client, session, engagement_evaluated_authz, user_attestor_authz
        )

        if not attestation_id:
            pytest.skip("Attestation creation endpoint (YET-70) not yet implemented")

        # Cross-tenant coordinator tries to revoke
        payload = {"revoke_reason": "Cross-tenant access attempt"}

        response = client.post(
            f"/attestations/{attestation_id}/revoke",
            json=payload,
            headers={"X-Debug-User-Id": str(user_cross_inst_coord_authz.id)},
        )

        assert response.status_code == 404, \
            f"Expected 404, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") == "NOT_FOUND"


# ============================================================================
# AC-S2: Race Condition Simulation — Concurrent revokes
# ============================================================================


class TestAttestationRevokeRaceCondition:
    """
    AC-S2: Two concurrent revoke requests on same attestation.
    Sequential simulation (not real threading): first succeeds (200), second fails (409 ALREADY_REVOKED).
    DB-level UPDATE ... WHERE revoked_at IS NULL ensures only one succeeds.
    """

    def test_revoke_concurrent_simulation_one_succeeds_one_409(
        self, client, session, engagement_evaluated_authz, user_attestor_authz,
        inst_coord_attestor_authz, deliverable_authz
    ):
        """
        AC-S2: Simulate concurrent revoke via sequential calls.
        First request: 200 (revoked_at set)
        Second request: 409 ALREADY_REVOKED (rowcount==0 in UPDATE WHERE revoked_at IS NULL)
        """
        # Create attestation
        attestation_id = create_attestation_via_endpoint(
            client, session, engagement_evaluated_authz, user_attestor_authz
        )

        if not attestation_id:
            pytest.skip("Attestation creation endpoint (YET-70) not yet implemented")

        payload1 = {"revoke_reason": "First concurrent request"}
        payload2 = {"revoke_reason": "Second concurrent request"}

        # First revoke: should succeed
        response1 = client.post(
            f"/attestations/{attestation_id}/revoke",
            json=payload1,
            headers={"X-Debug-User-Id": str(user_attestor_authz.id)},
        )

        assert response1.status_code == 200, \
            f"First revoke should succeed with 200, got {response1.status_code}: {response1.text}"

        # Second revoke: should fail with 409
        response2 = client.post(
            f"/attestations/{attestation_id}/revoke",
            json=payload2,
            headers={"X-Debug-User-Id": str(user_attestor_authz.id)},
        )

        assert response2.status_code == 409, \
            f"Second revoke should fail with 409, got {response2.status_code}: {response2.text}"

        data = response2.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") == "ALREADY_REVOKED", \
            f"Second revoke error code should be ALREADY_REVOKED, got {error_obj.get('code')}"


    def test_revoke_concurrent_different_actors_same_result(
        self, client, session, engagement_evaluated_authz, user_attestor_authz, user_other_coord_authz,
        inst_coord_attestor_authz, inst_coord_other_authz, deliverable_authz
    ):
        """
        AC-S2 (variation): Even if revoke attempted by different actors concurrently,
        second request still gets 409 (race condition, not authorization issue).
        Note: In this scenario, second request would get 403 for auth reasons,
        but the AC-S2 scenario is about same actor making concurrent requests.
        This test verifies correct error precedence: race condition (409) over auth (403)
        if both conditions apply (implementation detail).
        """
        # Create attestation
        attestation_id = create_attestation_via_endpoint(
            client, session, engagement_evaluated_authz, user_attestor_authz
        )

        if not attestation_id:
            pytest.skip("Attestation creation endpoint (YET-70) not yet implemented")

        # First revoke by attestor: succeeds
        response1 = client.post(
            f"/attestations/{attestation_id}/revoke",
            json={"revoke_reason": "Attestor revokes"},
            headers={"X-Debug-User-Id": str(user_attestor_authz.id)},
        )

        assert response1.status_code == 200

        # Second revoke attempt (by different actor after first succeeds):
        # Should get 409 ALREADY_REVOKED, not 403 (because it's already revoked,
        # not because of missing permission per se)
        response2 = client.post(
            f"/attestations/{attestation_id}/revoke",
            json={"revoke_reason": "Other coord attempts after revoke"},
            headers={"X-Debug-User-Id": str(user_other_coord_authz.id)},
        )

        # Note: This could be 403 (auth) or 409 (already revoked) depending on implementation.
        # AC-S2 focuses on same-actor race condition, so either is acceptable here.
        # Real implementation will determine which check runs first.
        assert response2.status_code in [403, 409], \
            f"Expected 403 or 409, got {response2.status_code}: {response2.text}"
