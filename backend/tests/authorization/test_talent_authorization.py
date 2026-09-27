"""
Talent profile authorization tests (YET-7 — AC-S1, AC-S2, AC-S3, AC-8).

Implements security criteria and isolation tests from atdd.md.

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient with X-Debug-User-Id header for auth simulation
- Defense-in-depth: server-side authorization verification
- Tenant/user isolation: ensure client-provided IDs don't override server logic

AC-S1: GET /me always returns authenticated user's data (query params ignored)
AC-S2: PATCH /talents/me always updates authenticated user's profile (body IDs ignored)
AC-S3: 409 SLUG_TAKEN response does not leak conflicting profile's owner info
AC-8: talent_id-based authorization (regardless of kind) — tested in functional tests

Status: Tests are RED/IMPORT-ERROR — implementation not yet written.
This is expected behavior. Tests verify authorization logic.
"""

import pytest

from app.models import TalentProfile, User


# ============================================================================
# Fixtures: Multiple users for isolation testing
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
def user_talent_charlie(session):
    """Talent user Charlie (additional user for multi-user scenarios)."""
    user = User(email="charlie@example.com", password_hash="hash_charlie")
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
        city="Istanbul",
        department=None,
        study_year=3,
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
        headline="Lead Developer",
        city="Ankara",
        department="Engineering",
        study_year=None,
        public_slug=None,
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_bob_with_slug(session, user_talent_bob):
    """Talent profile for Bob with public_slug (for conflict tests)."""
    profile = TalentProfile(
        user_id=user_talent_bob.id,
        full_name="Bob Slug Profile",
        visibility="PUBLIC",
        headline=None,
        city=None,
        department=None,
        study_year=None,
        public_slug="bob-unique-slug",
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_charlie(session, user_talent_charlie):
    """Talent profile for Charlie."""
    profile = TalentProfile(
        user_id=user_talent_charlie.id,
        full_name="Charlie Talent",
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


# ============================================================================
# AC-S1: GET /me — server resolves authenticated user, ignores query params
# ============================================================================


class TestGetMeQueryParamIgnored:
    """AC-S1: GET /me ignores query parameters (user_id, talent_id)."""

    def test_get_me_query_user_id_ignored(self, client, session, user_talent_alice, user_talent_bob, talent_alice, talent_bob):
        """
        AC-S1: GET /me?user_id=<bob> still returns Alice's profile.

        Scenario:
        - Alice is authenticated (X-Debug-User-Id: alice)
        - Query string tries to override: ?user_id=<bob>
        - Server should ignore query param and return Alice's profile

        Acceptance Criteria:
        - Status code: 200
        - Response contains Alice's profile (not Bob's)
        - user_id in response == Alice's ID
        """
        response = client.get(
            f"/me?user_id={user_talent_bob.id}",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)}
        )

        assert response.status_code == 200

        data = response.json()

        # Assert: returned user is Alice, not Bob
        assert data["user"]["id"] == str(user_talent_alice.id)
        assert data["talent_profile"]["user_id"] == str(user_talent_alice.id)
        assert data["talent_profile"]["full_name"] == "Alice Talent"

    def test_get_me_query_talent_id_ignored(self, client, session, user_talent_alice, user_talent_bob, talent_alice, talent_bob):
        """AC-S1: GET /me?talent_id=<bob> still returns Alice's profile."""
        response = client.get(
            f"/me?talent_id={talent_bob.id}",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)}
        )

        assert response.status_code == 200

        data = response.json()

        # Assert: Alice's profile, not Bob's
        assert data["user"]["id"] == str(user_talent_alice.id)
        assert data["talent_profile"]["id"] == str(talent_alice.id)

    def test_get_me_multiple_override_attempts_ignored(self, client, session, user_talent_alice, user_talent_bob, user_talent_charlie, talent_alice, talent_bob, talent_charlie):
        """
        AC-S1: GET /me with multiple query params attempting override → still returns authenticated user.

        Scenario:
        - Alice authenticated
        - Query: ?user_id=<bob>&talent_id=<charlie>
        - Server should ignore all and return Alice
        """
        response = client.get(
            f"/me?user_id={user_talent_bob.id}&talent_id={talent_charlie.id}",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)}
        )

        assert response.status_code == 200

        data = response.json()

        # Assert: Alice's profile only
        assert data["user"]["id"] == str(user_talent_alice.id)
        assert data["talent_profile"]["id"] == str(talent_alice.id)


# ============================================================================
# AC-S2: PATCH /talents/me — server resolves authenticated user, ignores body IDs
# ============================================================================


class TestPatchTalentMeBodyIDIgnored:
    """AC-S2: PATCH /talents/me ignores user_id, id, talent_profile_id in body."""

    def test_patch_talents_me_body_user_id_ignored(self, client, session, user_talent_alice, user_talent_bob, talent_alice, talent_bob):
        """
        AC-S2: PATCH /talents/me with user_id in body → field ignored, Alice updated.

        Scenario:
        - Alice authenticated
        - Body: {"headline": "Alice New", "user_id": <bob>}
        - Server should:
          1. Ignore user_id (cannot override to Bob)
          2. Update Alice's headline
          3. Return 200 with Alice's updated profile

        Acceptance Criteria:
        - Status code: 200
        - Alice's profile updated (headline changed)
        - Bob's profile unchanged
        - Response shows Alice's profile
        """
        payload = {
            "headline": "Alice New Headline",
            "user_id": str(user_talent_bob.id),  # Attempt to override to Bob
        }

        response = client.patch(
            "/talents/me",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)}
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Assert: Alice's profile updated
        tp = data
        assert tp["user_id"] == str(user_talent_alice.id)
        assert tp["headline"] == "Alice New Headline"

        # Verify in database: Alice updated, Bob unchanged
        alice_db = session.query(TalentProfile).filter_by(id=talent_alice.id).first()
        bob_db = session.query(TalentProfile).filter_by(id=talent_bob.id).first()

        assert alice_db.headline == "Alice New Headline"
        assert bob_db.headline == "Lead Developer", "Bob's profile should not be affected"

    def test_patch_talents_me_body_id_ignored(self, client, session, user_talent_alice, user_talent_bob, talent_alice, talent_bob):
        """AC-S2: PATCH /talents/me with id (talent_profile_id) in body → ignored."""
        payload = {
            "city": "Alice New City",
            "id": str(talent_bob.id),  # Attempt to override to Bob's profile ID
        }

        response = client.patch(
            "/talents/me",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)}
        )

        assert response.status_code == 200

        data = response.json()

        # Assert: Alice's profile updated (by user_id from auth, not by id from body)
        tp = data
        assert tp["id"] == str(talent_alice.id), "Should update Alice's profile, not Bob's"
        assert tp["city"] == "Alice New City"

        # Verify: Bob's profile unchanged
        bob_db = session.query(TalentProfile).filter_by(id=talent_bob.id).first()
        assert bob_db.city == "Ankara", "Bob's city should not change"

    def test_patch_talents_me_body_talent_profile_id_ignored(self, client, session, user_talent_alice, user_talent_bob, talent_alice, talent_bob):
        """AC-S2: PATCH /talents/me with talent_profile_id in body → ignored."""
        payload = {
            "department": "Alice Engineering",
            "talent_profile_id": str(talent_bob.id),
        }

        response = client.patch(
            "/talents/me",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)}
        )

        assert response.status_code == 200

        data = response.json()

        # Assert: Alice updated
        tp = data
        assert tp["id"] == str(talent_alice.id)
        assert tp["department"] == "Alice Engineering"

        # Verify: Bob unchanged
        bob_db = session.query(TalentProfile).filter_by(id=talent_bob.id).first()
        assert bob_db.department == "Engineering"

    def test_patch_talents_me_all_id_overrides_in_body_ignored(self, client, session, user_talent_alice, user_talent_bob, talent_alice, talent_bob):
        """
        AC-S2: PATCH /talents/me with multiple ID fields in body → all ignored.

        Scenario:
        - Alice authenticated
        - Body: {
            "headline": "Alice New",
            "user_id": <bob>,
            "id": <bob-profile-id>,
            "talent_profile_id": <bob-profile-id>,
            "institution_id": <some-inst>
          }
        - Server should: ignore all ID fields, update Alice's headline only

        Acceptance Criteria:
        - Status code: 200
        - Alice's profile updated
        - Bob's profile untouched
        - Response shows Alice's profile only
        """
        from app.models import Institution

        inst = Institution(name="Test", domain="test.edu.tr")
        session.add(inst)
        session.flush()

        payload = {
            "headline": "Alice Final Headline",
            "user_id": str(user_talent_bob.id),
            "id": str(talent_bob.id),
            "talent_profile_id": str(talent_bob.id),
            "institution_id": str(inst.id),
        }

        response = client.patch(
            "/talents/me",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)}
        )

        assert response.status_code == 200

        data = response.json()

        # Assert: Alice's profile only
        tp = data
        assert tp["user_id"] == str(user_talent_alice.id)
        assert tp["id"] == str(talent_alice.id)
        assert tp["headline"] == "Alice Final Headline"
        assert tp["institution_id"] is None, "institution_id should be ignored/unchanged"

        # Verify: Bob untouched
        bob_db = session.query(TalentProfile).filter_by(id=talent_bob.id).first()
        assert bob_db.headline == "Lead Developer"


# ============================================================================
# AC-S3: 409 SLUG_TAKEN — does not leak conflicting profile owner's identity
# ============================================================================


class TestSlugTakenNoLeakage:
    """AC-S3: 409 SLUG_TAKEN response does not contain owner's PII."""

    def test_slug_taken_no_user_id_leaked(self, client, session, user_talent_alice, user_talent_bob, talent_alice, talent_bob_with_slug):
        """
        AC-S3: 409 response does not contain Bob's user_id (conflicting owner).

        Scenario:
        - Alice tries to set slug = "bob-unique-slug" (already taken by Bob)
        - Response: 409 SLUG_TAKEN
        - Response body must NOT contain Bob's user_id, email, or name

        Acceptance Criteria:
        - Status code: 409
        - Response contains only: code, message, request_id
        - No user_id, email, full_name of conflicting profile
        """
        payload = {"public_slug": "bob-unique-slug"}

        response = client.patch(
            "/talents/me",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)}
        )

        assert response.status_code == 409

        data = response.json()

        # Assert: error code
        assert data.get("code") == "SLUG_TAKEN"

        # Assert: response does not leak Bob's identity
        response_str = str(data)

        assert str(user_talent_bob.id) not in response_str, "Bob's user_id should not be in response"
        assert "bob@example.com" not in response_str, "Bob's email should not be in response"
        assert "Bob Slug Profile" not in response_str, "Bob's profile name should not be in response"

    def test_slug_taken_response_keys_minimal(self, client, session, user_talent_alice, talent_alice, talent_bob_with_slug):
        """
        AC-S3: 409 response contains ONLY {code, message, request_id}.

        Acceptance Criteria:
        - Response keys: code, message, request_id (no extras)
        """
        payload = {"public_slug": "bob-unique-slug"}

        response = client.patch(
            "/talents/me",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)}
        )

        assert response.status_code == 409

        data = response.json()

        # Assert: only expected keys
        expected_keys = {"code", "message", "request_id"}
        actual_keys = set(data.keys())

        assert actual_keys == expected_keys, f"Expected keys {expected_keys}, got {actual_keys}"

    def test_slug_taken_message_is_generic(self, client, session, user_talent_alice, talent_alice, talent_bob_with_slug):
        """
        AC-S3: 409 error message is generic (does not reveal owner).

        Acceptance Criteria:
        - Message is Türkçe
        - Message does not mention Bob's name/email/ID
        - Message is generic (e.g., "Bu slug zaten kullanılıyor")
        """
        payload = {"public_slug": "bob-unique-slug"}

        response = client.patch(
            "/talents/me",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)}
        )

        assert response.status_code == 409

        data = response.json()
        message = data.get("message", "").lower()

        # Assert: message does not mention specific user
        assert "bob" not in message
        assert "bob@example.com" not in message

        # Assert: message is generic (e.g., contains "slug", "kullanıl", etc.)
        # (Actual message TBD in implementation, but should be generic)
        assert len(message) > 0


# ============================================================================
# Cross-user isolation: One user cannot modify/read another's profile
# ============================================================================


class TestCrossUserIsolation:
    """Defense-in-depth: users cannot access/modify each other's profiles."""

    def test_patch_talents_me_user_b_cannot_modify_a(self, client, session, user_talent_alice, user_talent_bob, talent_alice, talent_bob):
        """
        Bob attempts to PATCH Alice's profile via attempted override.

        Setup:
        - Bob is authenticated
        - Body contains Alice's profile ID
        - Expected: Bob's profile is updated (by his auth context), not Alice's
        """
        payload = {
            "headline": "Hacked Alice",
            "id": str(talent_alice.id),  # Try to override to Alice's ID
        }

        response = client.patch(
            "/talents/me",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_bob.id)}
        )

        assert response.status_code == 200

        data = response.json()

        # Assert: Bob's profile updated, not Alice's
        tp = data
        assert tp["user_id"] == str(user_talent_bob.id)
        assert tp["id"] == str(talent_bob.id)

        # Verify: Alice's headline unchanged
        alice_db = session.query(TalentProfile).filter_by(id=talent_alice.id).first()
        assert alice_db.headline is None, "Alice's headline should not be modified by Bob"

    def test_get_me_user_b_cannot_read_a_profile(self, client, session, user_talent_alice, user_talent_bob, talent_alice, talent_bob):
        """
        Bob attempts to read Alice's profile via query param override.

        Expected: Bob gets his own profile (query params ignored).
        """
        response = client.get(
            f"/me?user_id={user_talent_alice.id}",
            headers={"X-Debug-User-Id": str(user_talent_bob.id)}
        )

        assert response.status_code == 200

        data = response.json()

        # Assert: Bob's profile returned, not Alice's
        assert data["user"]["id"] == str(user_talent_bob.id)
        assert data["talent_profile"]["id"] == str(talent_bob.id)


# ============================================================================
# Atomicity: 409/422 errors don't partially update
# ============================================================================


class TestAtomicityOnError:
    """AC-4/AC-5: Errors cause no database updates (rollback)."""

    def test_slug_conflict_no_other_fields_updated(self, client, session, user_talent_alice, talent_alice, talent_bob_with_slug):
        """
        AC-4: PATCH with slug conflict → 409, nothing updated (including valid fields).

        Scenario:
        - Alice tries: {"headline": "New", "public_slug": "bob-unique-slug"}
        - Both fields are valid individually, but slug conflicts
        - Expected: headline NOT updated (atomicity)
        """
        payload = {
            "headline": "New Headline",
            "public_slug": "bob-unique-slug",  # Conflicts with Bob
        }

        response = client.patch(
            "/talents/me",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)}
        )

        assert response.status_code == 409

        # Verify: headline not updated (atomicity)
        alice_db = session.query(TalentProfile).filter_by(id=talent_alice.id).first()
        assert alice_db.headline is None, "headline should not be updated when slug conflicts"
        assert alice_db.public_slug is None, "slug should not be updated"

    def test_validation_error_no_partial_update(self, client, session, user_talent_alice, talent_alice):
        """
        AC-5: PATCH with one invalid field → nothing updated.

        Scenario:
        - Payload: {"headline": "Valid", "study_year": 99}
        - headline is valid, study_year is invalid
        - Expected: neither field updated
        """
        payload = {
            "headline": "Valid Headline",
            "study_year": 99,  # Out of range
        }

        response = client.patch(
            "/talents/me",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)}
        )

        assert response.status_code == 422

        # Verify: neither field updated
        alice_db = session.query(TalentProfile).filter_by(id=talent_alice.id).first()
        assert alice_db.headline is None
        assert alice_db.study_year == 3


# ============================================================================
# 401 Authentication: Missing/Invalid header
# ============================================================================


class TestAuthentication:
    """Missing X-Debug-User-Id header → 401."""

    def test_get_me_missing_header_401(self, client):
        """GET /me without X-Debug-User-Id → 401."""
        response = client.get("/me")

        assert response.status_code == 401

    def test_patch_talents_me_missing_header_401(self, client):
        """PATCH /talents/me without X-Debug-User-Id → 401."""
        response = client.patch("/talents/me", json={})

        assert response.status_code == 401

    def test_get_me_invalid_user_id_header_401(self, client, session):
        """GET /me with nonexistent user_id → 401."""
        import uuid

        fake_id = uuid.uuid4()

        response = client.get("/me", headers={"X-Debug-User-Id": str(fake_id)})

        assert response.status_code == 401
