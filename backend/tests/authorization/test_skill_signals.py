"""
Skill signal authorization tests (YET-104 — skillsignal-self-claim-uretimi).

Implements AC-S1, AC-S2 (threat model: cross-talent isolation).

Test patterns:
- Real Postgres transaction per test
- Principal identity injected via X-Debug-User-Id header
- Cross-talent query filters must not leak other talents' signals

Status: Tests are RED/IMPORT-ERROR — implementation not yet written.
This is expected behavior. Tests implement behavior contract (ATDD).
"""

import pytest

from app.models import TalentProfile, User, Skill


# ============================================================================
# Fixtures: Two talents with separate signals
# ============================================================================


@pytest.fixture
def user_talent_authz_a(session):
    """Talent user A (for cross-talent isolation tests)."""
    user = User(email="authz-talent-a@example.com", password_hash="hash_authz_a")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_authz_b(session):
    """Talent user B (for cross-talent isolation tests)."""
    user = User(email="authz-talent-b@example.com", password_hash="hash_authz_b")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent_authz_a(session, user_talent_authz_a):
    """Talent profile A."""
    profile = TalentProfile(
        user_id=user_talent_authz_a.id,
        full_name="Authz Test Talent A",
        visibility="PRIVATE",
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_authz_b(session, user_talent_authz_b):
    """Talent profile B."""
    profile = TalentProfile(
        user_id=user_talent_authz_b.id,
        full_name="Authz Test Talent B",
        visibility="PRIVATE",
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def skill_authz_shared_python(session):
    """Shared skill for both talents to claim."""
    skill = Skill(
        slug="python-authz-shared",
        name_tr="Python",
        name_en="Python",
        category="LANGUAGE",
        status="ACTIVE",
        parent_id=None,
        merged_into_id=None,
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def skill_authz_only_b(session):
    """Skill claimed only by talent B (for isolation test)."""
    skill = Skill(
        slug="rust-authz-only-b",
        name_tr="Rust",
        name_en="Rust",
        category="LANGUAGE",
        status="ACTIVE",
        parent_id=None,
        merged_into_id=None,
    )
    session.add(skill)
    session.flush()
    return skill


# ============================================================================
# AC-S1: Cross-talent skill_id filter does not leak other talent's signals
# ============================================================================


class TestCrossTalentSignalIsolation:
    """AC-S1: Talent A cannot access/infer existence of Talent B's signals via skill_id filter."""

    def test_talent_a_queries_skill_only_b_claimed_gets_empty_list(
        self, client, session, user_talent_authz_a, talent_authz_a,
        user_talent_authz_b, talent_authz_b, skill_authz_shared_python, skill_authz_only_b
    ):
        """
        AC-S1: Talent A queries ?skill_id=<only_B_claimed> → 200 + empty list.

        Threat model: scoped_skill_signals() must filter by principal.talent_id,
        so Talent B's signals never leak to Talent A, even if Talent A guesses
        a skill_id that Talent B claimed.

        Acceptance Criteria:
        - Talent B claims skill_authz_only_b
        - Talent A queries GET /talents/me/signals?skill_id=<only_B_claimed>
        - Response: 200 + {items: []}
        - Talent A learns nothing about whether Talent B claimed this skill
        """
        # Setup: Talent B claims skill_authz_only_b
        payload_b = {"skill_id": str(skill_authz_only_b.id), "claimed_level": "INTERMEDIATE"}
        response_b = client.post(
            "/talents/me/skills",
            json=payload_b,
            headers={"X-Debug-User-Id": str(user_talent_authz_b.id)},
        )
        assert response_b.status_code == 201

        # Talent A tries to query with skill_authz_only_b
        # (simulating an attacker trying to discover Talent B's signals)
        response_a = client.get(
            f"/talents/me/signals?skill_id={skill_authz_only_b.id}",
            headers={"X-Debug-User-Id": str(user_talent_authz_a.id)},
        )

        assert response_a.status_code == 200

        data_a = response_a.json()
        # Talent A must see empty list, not an error or leakage
        assert data_a["items"] == []

    def test_talent_a_cannot_see_talent_b_signals_in_full_list(
        self, client, session, user_talent_authz_a, talent_authz_a,
        user_talent_authz_b, talent_authz_b, skill_authz_shared_python, skill_authz_only_b
    ):
        """
        AC-S1: GET /talents/me/signals (no filter) from Talent A does not include Talent B's claims.

        Acceptance Criteria:
        - Talent A claims skill_authz_shared_python
        - Talent B claims skill_authz_only_b (and optionally skill_authz_shared_python)
        - Talent A queries GET /talents/me/signals (no ?skill_id)
        - Response contains only Talent A's own signals, never Talent B's
        """
        # Setup: Talent A claims shared skill
        payload_a = {"skill_id": str(skill_authz_shared_python.id), "claimed_level": "INTERMEDIATE"}
        response_a_claim = client.post(
            "/talents/me/skills",
            json=payload_a,
            headers={"X-Debug-User-Id": str(user_talent_authz_a.id)},
        )
        assert response_a_claim.status_code == 201

        # Setup: Talent B claims only-B skill
        payload_b = {"skill_id": str(skill_authz_only_b.id), "claimed_level": "INTERMEDIATE"}
        response_b_claim = client.post(
            "/talents/me/skills",
            json=payload_b,
            headers={"X-Debug-User-Id": str(user_talent_authz_b.id)},
        )
        assert response_b_claim.status_code == 201

        # Talent A queries full signal list
        response_a_list = client.get(
            "/talents/me/signals",
            headers={"X-Debug-User-Id": str(user_talent_authz_a.id)},
        )

        assert response_a_list.status_code == 200
        data_a = response_a_list.json()

        # Talent A should see only 1 skill group (shared skill claimed by A)
        assert len(data_a["items"]) == 1
        assert data_a["items"][0]["skill"]["id"] == str(skill_authz_shared_python.id)

        # Talent A must NOT see Talent B's only_b skill group
        skill_ids_in_response = {item["skill"]["id"] for item in data_a["items"]}
        assert str(skill_authz_only_b.id) not in skill_ids_in_response


# ============================================================================
# AC-S2: scoped_skill_signals() filters by principal.talent_id, not request payload
# ============================================================================


class TestPrincipalTalentIdFromSessionNotRequest:
    """AC-S2: talent_id comes from session principal, not from query/body params."""

    def test_scoped_signals_uses_principal_talent_id_not_query_param(
        self, client, session, user_talent_authz_a, talent_authz_a,
        user_talent_authz_b, talent_authz_b, skill_authz_shared_python
    ):
        """
        AC-S2: scoped_skill_signals(session, principal) filters by principal.talent_id.

        Threat model: even if a malicious client sends ?talent_id=<B>,
        the server must ignore it and use principal.talent_id from auth context.

        This test documents that the implementation MUST NOT read talent_id from:
        - Query parameters
        - Request body
        - Cookies
        - Any client-controlled source

        Only principal.talent_id (derived from JWT/auth session) is trusted.

        Acceptance Criteria:
        - Talent B claims a skill
        - Talent A queries GET /talents/me/signals (Talent A's session)
        - Response contains only Talent A's signals, ignoring any talent_id hint
        - Note: This test assumes the API does NOT accept ?talent_id param
          (REST principle: /talents/me/ implies current user, no override)
        """
        # Setup: Talent B claims a skill
        payload_b = {"skill_id": str(skill_authz_shared_python.id), "claimed_level": "INTERMEDIATE"}
        response_b = client.post(
            "/talents/me/skills",
            json=payload_b,
            headers={"X-Debug-User-Id": str(user_talent_authz_b.id)},
        )
        assert response_b.status_code == 201

        # Talent A queries GET /talents/me/signals
        # (even if Talent A somehow tried to pass ?talent_id=<B>, it's ignored)
        response_a = client.get(
            "/talents/me/signals",
            headers={"X-Debug-User-Id": str(user_talent_authz_a.id)},
        )

        assert response_a.status_code == 200
        data_a = response_a.json()

        # Talent A's list must be empty (no claims)
        # Talent B's signal must NOT appear
        assert data_a["items"] == []

    def test_scope_respects_principal_talent_id_across_requests(
        self, client, session, user_talent_authz_a, talent_authz_a,
        user_talent_authz_b, talent_authz_b, skill_authz_shared_python, skill_authz_only_b
    ):
        """
        AC-S2: Multiple requests from Talent A always see only Talent A's data.

        This test verifies that the principal context (X-Debug-User-Id) is
        correctly isolated per request, and the scoped query respects it.

        Acceptance Criteria:
        - Talent A claims skill_authz_shared_python
        - Talent B claims skill_authz_only_b
        - Talent A queries: GET /talents/me/signals (empty or only shared)
        - Talent A queries: GET /talents/me/signals?skill_id=<shared> (only shared)
        - Talent A queries: GET /talents/me/signals?skill_id=<only_B> (empty)
        - All of Talent A's queries return only Talent A's data
        """
        # Setup: Talent A claims shared skill
        payload_a = {"skill_id": str(skill_authz_shared_python.id), "claimed_level": "INTERMEDIATE"}
        response_a_claim = client.post(
            "/talents/me/skills",
            json=payload_a,
            headers={"X-Debug-User-Id": str(user_talent_authz_a.id)},
        )
        assert response_a_claim.status_code == 201

        # Setup: Talent B claims only-B skill
        payload_b = {"skill_id": str(skill_authz_only_b.id), "claimed_level": "INTERMEDIATE"}
        response_b_claim = client.post(
            "/talents/me/skills",
            json=payload_b,
            headers={"X-Debug-User-Id": str(user_talent_authz_b.id)},
        )
        assert response_b_claim.status_code == 201

        # Talent A query 1: full list
        response_1 = client.get(
            "/talents/me/signals",
            headers={"X-Debug-User-Id": str(user_talent_authz_a.id)},
        )
        assert response_1.status_code == 200
        data_1 = response_1.json()
        assert len(data_1["items"]) == 1
        assert data_1["items"][0]["skill"]["id"] == str(skill_authz_shared_python.id)

        # Talent A query 2: filter by shared skill
        response_2 = client.get(
            f"/talents/me/signals?skill_id={skill_authz_shared_python.id}",
            headers={"X-Debug-User-Id": str(user_talent_authz_a.id)},
        )
        assert response_2.status_code == 200
        data_2 = response_2.json()
        assert len(data_2["items"]) == 1
        assert data_2["items"][0]["skill"]["id"] == str(skill_authz_shared_python.id)

        # Talent A query 3: filter by only-B skill (should be empty, not error)
        response_3 = client.get(
            f"/talents/me/signals?skill_id={skill_authz_only_b.id}",
            headers={"X-Debug-User-Id": str(user_talent_authz_a.id)},
        )
        assert response_3.status_code == 200
        data_3 = response_3.json()
        assert data_3["items"] == []


# ============================================================================
# Authorization edge cases
# ============================================================================


class TestSignalAuthorizationEdgeCases:
    """Additional authorization tests for edge cases."""

    def test_unauthenticated_request_fails(self, client):
        """
        Unauthenticated request (no X-Debug-User-Id header) → 401 error.

        Acceptance Criteria:
        - GET /talents/me/signals without X-Debug-User-Id → 401 Unauthorized
        """
        response = client.get("/talents/me/signals")

        assert response.status_code == 401

    def test_invalid_user_id_in_header_fails(self, client):
        """
        Invalid X-Debug-User-Id header (nonexistent user) → 401 error.

        Acceptance Criteria:
        - GET /talents/me/signals with invalid/nonexistent user ID → 401 Unauthorized
        """
        import uuid

        fake_user_id = uuid.uuid4()

        response = client.get(
            "/talents/me/signals",
            headers={"X-Debug-User-Id": str(fake_user_id)},
        )

        assert response.status_code == 401
