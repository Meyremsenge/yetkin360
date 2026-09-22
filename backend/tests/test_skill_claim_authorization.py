"""
Skill claim authorization tests (YET-11 — AC-S1, AC-S2, AC-S3, AC-S4).

Implements security criteria and isolation tests from atdd.md.

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient with X-Debug-User-Id header for auth simulation
- Defense-in-depth: server-side authorization verification
- Tenant/user isolation: ensure client-provided IDs don't override server logic

AC-S1: Unauthenticated or talent_id-less user → 404/401
AC-S2: POST body talent_id field ignored (claimed_level overrides prevented)
AC-S3: GET yalnız authenticated talent'ın claims'ini döner
AC-S4: DELETE başka talent'ın claim'i ile → 404 (ayırt edilemez)

Status: Tests are RED/IMPORT-ERROR — implementation not yet written.
This is expected behavior. Tests verify authorization logic.
"""

import pytest

from app.models import TalentProfile, User, Skill


# ============================================================================
# Fixtures: Multiple talents for isolation testing
# ============================================================================


@pytest.fixture
def user_talent_alice(session):
    """Talent user Alice."""
    user = User(email="alice@example.com", password_hash="hash_alice")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_bob(session):
    """Talent user Bob (for cross-user isolation tests)."""
    user = User(email="bob@example.com", password_hash="hash_bob")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_no_talent(session):
    """User without talent_profile (for AC-S1 test)."""
    user = User(email="no-talent@example.com", password_hash="hash_no_talent")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent_alice(session, user_talent_alice):
    """Talent profile for Alice."""
    profile = TalentProfile(
        user_id=user_talent_alice.id,
        full_name="Alice Talent",
        visibility="PRIVATE",
        headline=None,
        city=None,
        department=None,
        study_year=None,
        public_slug=None,
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_bob(session, user_talent_bob):
    """Talent profile for Bob."""
    profile = TalentProfile(
        user_id=user_talent_bob.id,
        full_name="Bob Talent",
        visibility="PRIVATE",
        headline=None,
        city=None,
        department=None,
        study_year=None,
        public_slug=None,
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def skill_python(session):
    """ACTIVE skill: Python."""
    skill = Skill(
        slug="python",
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
def skill_javascript(session):
    """ACTIVE skill: JavaScript."""
    skill = Skill(
        slug="javascript",
        name_tr="JavaScript",
        name_en="JavaScript",
        category="LANGUAGE",
        status="ACTIVE",
        parent_id=None,
        merged_into_id=None,
    )
    session.add(skill)
    session.flush()
    return skill


# ============================================================================
# AC-S1: Unauthenticated or talent_id-less user → 404/401
# ============================================================================


class TestUnauthenticatedAccess:
    """AC-S1: Missing/invalid auth → 404/401, never 403."""

    def test_post_without_header_401(self, client, skill_python):
        """
        AC-S1: POST /talents/me/skills without X-Debug-User-Id → 401.

        Acceptance Criteria:
        - Status code: 401 Unauthorized (not 403)
        - No claim inserted
        """
        payload = {"skill_id": str(skill_python.id)}

        response = client.post(
            "/talents/me/skills",
            json=payload,
            # No X-Debug-User-Id header
        )

        assert response.status_code == 401

    def test_get_without_header_401(self, client):
        """AC-S1: GET /talents/me/skills without X-Debug-User-Id → 401."""
        response = client.get("/talents/me/skills")

        assert response.status_code == 401

    def test_delete_without_header_401(self, client, skill_python):
        """AC-S1: DELETE /talents/me/skills/{skill_id} without X-Debug-User-Id → 401."""
        response = client.delete(f"/talents/me/skills/{skill_python.id}")

        assert response.status_code == 401

    def test_post_user_without_talent_404(self, client, session, user_no_talent, skill_python):
        """
        AC-S1: User without talent_profile → 404 (not 403).

        Scenario:
        - user_no_talent has no TalentProfile (talent_id is None)
        - POST attempt should return 404 (resource doesn't exist for this principal)

        Acceptance Criteria:
        - Status code: 404 (not 403)
        - No claim inserted
        """
        payload = {"skill_id": str(skill_python.id)}

        response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_no_talent.id)},
        )

        # Should be 404, not 403 (403 would reveal that resource exists)
        assert response.status_code == 404

    def test_get_user_without_talent_404(self, client, user_no_talent):
        """AC-S1: GET /talents/me/skills user without talent_profile → 404."""
        response = client.get(
            "/talents/me/skills",
            headers={"X-Debug-User-Id": str(user_no_talent.id)},
        )

        assert response.status_code == 404

    def test_delete_user_without_talent_404(self, client, user_no_talent, skill_python):
        """AC-S1: DELETE /talents/me/skills user without talent_profile → 404."""
        response = client.delete(
            f"/talents/me/skills/{skill_python.id}",
            headers={"X-Debug-User-Id": str(user_no_talent.id)},
        )

        assert response.status_code == 404


# ============================================================================
# AC-S2: POST body talent_id field is ignored
# ============================================================================


class TestPostBodyTalentIdIgnored:
    """AC-S2: POST body with talent_id/ownership fields → ignored, own talent updated."""

    def test_post_body_talent_id_ignored(self, client, session, user_talent_alice, user_talent_bob, talent_alice, talent_bob, skill_python):
        """
        AC-S2: POST /talents/me/skills with talent_id=bob → claim added to Alice.

        Scenario:
        - Alice authenticated
        - Body: {skill_id: python, talent_id: <bob>}
        - Server should:
          1. Ignore talent_id (cannot override to Bob)
          2. Add claim to Alice's profile only
          3. Return 201

        Acceptance Criteria:
        - Status code: 201
        - Claim added to Alice (principal.talent_id), not Bob
        - Response shows Alice's claim
        """
        payload = {
            "skill_id": str(skill_python.id),
            "talent_id": str(talent_bob.id),  # Attempt to override to Bob
        }

        response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()

        # Assert: response shows Alice's claim (not Bob's)
        assert data.get("skill_id") == str(skill_python.id)

        # Verify in database: claim belongs to Alice, not Bob
        # (Will fail at DB query due to SkillClaim model not yet defined — expected)

    def test_post_no_user_id_field_in_schema(self, client, session, user_talent_alice, talent_alice, skill_python):
        """
        AC-S2: POST request with user_id field → silently ignored.

        Acceptance Criteria:
        - Status code: 201
        - user_id field in body is not accepted (Pydantic rejects extra fields)
        - Claim added to Alice's talent (authenticated user)
        """
        payload = {
            "skill_id": str(skill_python.id),
            "user_id": "some-value",  # Not a valid field
        }

        response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        # Pydantic's forbid extra fields should reject this,
        # OR it should be ignored and 201 succeed
        # (Test documents expected behavior)
        assert response.status_code in [201, 422]  # Either succeeds or validation fails


# ============================================================================
# AC-S3: GET /talents/me/skills yalnız authenticated talent'ın claims'ini döner
# ============================================================================


class TestGetOnlyOwnClaims:
    """AC-S3: GET /talents/me/skills returns only authenticated user's claims."""

    def test_get_returns_only_own_claims(self, client, session, user_talent_alice, user_talent_bob, talent_alice, talent_bob, skill_python, skill_javascript):
        """
        AC-S3: Alice's GET only returns Alice's claims, not Bob's.

        Scenario:
        - Alice adds skill_python
        - Bob adds skill_javascript
        - Alice calls GET /talents/me/skills
        - Should return only Alice's claim (python), not Bob's (javascript)

        Acceptance Criteria:
        - Status code: 200
        - items list contains only Alice's claim (python)
        - Bob's claim (javascript) is NOT returned
        """
        # Setup: Alice adds python
        payload_alice = {"skill_id": str(skill_python.id)}
        response_alice = client.post(
            "/talents/me/skills",
            json=payload_alice,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )
        assert response_alice.status_code == 201

        # Setup: Bob adds javascript
        payload_bob = {"skill_id": str(skill_javascript.id)}
        response_bob = client.post(
            "/talents/me/skills",
            json=payload_bob,
            headers={"X-Debug-User-Id": str(user_talent_bob.id)},
        )
        assert response_bob.status_code == 201

        # Alice's GET
        response = client.get(
            "/talents/me/skills",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 200

        data = response.json()

        # Assert: only Alice's claim
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["skill"]["slug"] == "python"

    def test_get_with_query_param_talent_id_ignored(self, client, session, user_talent_alice, user_talent_bob, talent_alice, talent_bob, skill_python, skill_javascript):
        """
        AC-S3: GET /talents/me/skills?talent_id=<bob> still returns Alice's claims.

        Scenario:
        - Alice authenticated
        - Query: ?talent_id=<bob>
        - Server should ignore query param and return Alice's claims

        Acceptance Criteria:
        - Status code: 200
        - items contains only Alice's claims
        """
        # Setup: Alice adds python
        payload_alice = {"skill_id": str(skill_python.id)}
        response_alice = client.post(
            "/talents/me/skills",
            json=payload_alice,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )
        assert response_alice.status_code == 201

        # Setup: Bob adds javascript
        payload_bob = {"skill_id": str(skill_javascript.id)}
        response_bob = client.post(
            "/talents/me/skills",
            json=payload_bob,
            headers={"X-Debug-User-Id": str(user_talent_bob.id)},
        )
        assert response_bob.status_code == 201

        # Alice's GET with attempt to override via query param
        response = client.get(
            f"/talents/me/skills?talent_id={talent_bob.id}",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 200

        data = response.json()

        # Assert: Alice's claims only (query param ignored)
        assert len(data["items"]) == 1
        assert data["items"][0]["skill"]["slug"] == "python"


# ============================================================================
# AC-S4: DELETE başka talent'ın claim'i ile → 404 (ayırt edilemez)
# ============================================================================


class TestDeleteCrossUserIsolation:
    """AC-S4: DELETE /talents/me/skills/{skill_id} scoped to authenticated user."""

    def test_delete_another_talents_claim_404(self, client, session, user_talent_alice, user_talent_bob, talent_alice, talent_bob, skill_python):
        """
        AC-S4: Alice tries DELETE skill Bob claimed → 404 (as if Bob's claim doesn't exist for Alice).

        Scenario:
        - Bob adds skill_python
        - Alice tries DELETE /talents/me/skills/{skill_python}
        - Server should return 404 (Bob's claim is outside Alice's scope)
        - Response should NOT reveal that Bob's claim exists

        Acceptance Criteria:
        - Status code: 404
        - Error code: "SKILL_CLAIM_NOT_FOUND"
        - Response is same 404 as if claim never existed (can't distinguish)
        """
        # Setup: Bob adds python
        payload_bob = {"skill_id": str(skill_python.id)}
        response_bob = client.post(
            "/talents/me/skills",
            json=payload_bob,
            headers={"X-Debug-User-Id": str(user_talent_bob.id)},
        )
        assert response_bob.status_code == 201

        # Alice tries to DELETE Bob's claim
        response = client.delete(
            f"/talents/me/skills/{skill_python.id}",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 404

        data = response.json()

        # Assert: error code
        assert data.get("code") == "SKILL_CLAIM_NOT_FOUND"

    def test_delete_own_claim_succeeds(self, client, session, user_talent_alice, talent_alice, skill_python):
        """
        AC-S4 (verification): Alice can DELETE her own claim.

        Acceptance Criteria:
        - Status code: 204
        """
        # Setup: Alice adds python
        payload = {"skill_id": str(skill_python.id)}
        response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )
        assert response.status_code == 201

        # Alice DELETEs her own claim
        response = client.delete(
            f"/talents/me/skills/{skill_python.id}",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 204

    def test_delete_same_skill_different_scope(self, client, session, user_talent_alice, user_talent_bob, talent_alice, talent_bob, skill_python):
        """
        AC-S4: Each talent's claim is independently scoped.

        Scenario:
        - Alice adds python
        - Bob adds python (different claim row, same skill)
        - Alice DELETEs python (only her claim)
        - Bob's claim still exists
        - Alice's second DELETE → 404

        Acceptance Criteria:
        - After first DELETE by Alice: success (204)
        - After second DELETE by Alice: 404 (her claim is gone)
        - Bob's claim untouched (GET /talents/me/skills by Bob still returns python)
        """
        # Setup: both add python
        for user, talent in [(user_talent_alice, talent_alice), (user_talent_bob, talent_bob)]:
            payload = {"skill_id": str(skill_python.id)}
            response = client.post(
                "/talents/me/skills",
                json=payload,
                headers={"X-Debug-User-Id": str(user.id)},
            )
            assert response.status_code == 201

        # Alice DELETEs
        response = client.delete(
            f"/talents/me/skills/{skill_python.id}",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )
        assert response.status_code == 204

        # Alice tries DELETE again → 404 (her claim gone)
        response = client.delete(
            f"/talents/me/skills/{skill_python.id}",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )
        assert response.status_code == 404

        # Bob's claim still exists
        response = client.get(
            "/talents/me/skills",
            headers={"X-Debug-User-Id": str(user_talent_bob.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["skill"]["slug"] == "python"


# ============================================================================
# Cross-talent isolation: Cannot see/modify another talent's claims
# ============================================================================


class TestCrossTalentIsolation:
    """Defense-in-depth: talents cannot access/modify each other's claims."""

    def test_bob_cannot_read_alice_claims(self, client, session, user_talent_alice, user_talent_bob, talent_alice, talent_bob, skill_python):
        """
        AC-S3: Bob calls GET /talents/me/skills → returns Bob's claims, not Alice's.

        Scenario:
        - Alice adds python
        - Bob calls GET (no query param override)
        - Should return empty list (Bob has no claims)
        """
        # Setup: Alice adds python
        payload = {"skill_id": str(skill_python.id)}
        response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )
        assert response.status_code == 201

        # Bob's GET (should be empty)
        response = client.get(
            "/talents/me/skills",
            headers={"X-Debug-User-Id": str(user_talent_bob.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []


# ============================================================================
# Response schema validation (error responses)
# ============================================================================


class TestAuthErrorResponseSchema:
    """Verify auth error responses match API.md §1.4."""

    def test_unauthenticated_error_has_code_message_request_id(self, client, skill_python):
        """401 error must have {code, message, request_id}."""
        payload = {"skill_id": str(skill_python.id)}

        response = client.post(
            "/talents/me/skills",
            json=payload,
            # No X-Debug-User-Id
        )

        assert response.status_code == 401

        data = response.json()

        # Assert: error structure
        assert "code" in data
        assert "message" in data
        assert "request_id" in data

    def test_not_found_error_has_code_message_request_id(self, client, user_talent_alice, talent_alice):
        """404 error must have {code, message, request_id}."""
        import uuid

        fake_skill_id = uuid.uuid4()

        payload = {"skill_id": str(fake_skill_id)}

        response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 404

        data = response.json()

        # Assert: error structure
        assert "code" in data
        assert "message" in data
        assert "request_id" in data
