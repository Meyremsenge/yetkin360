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


# ============================================================================
# Skill claim validation: AC-10 (VER-02)
# ============================================================================


class TestSkillClaimValidation:
    """AC-10 (VER-02): Invalid claimed_level → 400 VALIDATION_ERROR, not 409."""

    def test_post_skills_invalid_claimed_level_returns_400(self, client, session, user_talent_alice, talent_alice):
        """
        AC-10 (VER-02): POST /talents/me/skills with invalid claimed_level → 400.

        Scenario:
        - Alice claims a skill with invalid claimed_level value (e.g., "INVALID", 99, null, etc.)
        - Expected: 400 VALIDATION_ERROR (not 409 ALREADY_CLAIMED)

        Acceptance Criteria:
        - Status code: 400 (exactly)
        - Response contains validation error details
        - No skill claim created in database
        - Error is 400, not 409 (409 would incorrectly suggest duplicate claim)
        """
        from app.models import Skill

        # Create a test skill
        skill = Skill(
            slug="test-skill-validation",
            name_tr="Test Skill",
            name_en="Test Skill",
            category="LANGUAGE",
            status="ACTIVE",
            parent_id=None,
            merged_into_id=None,
        )
        session.add(skill)
        session.flush()

        # Attempt to claim skill with invalid claimed_level
        invalid_claimed_levels = [
            "INVALID",  # Not in enum
            "beginner",  # Lowercase (if case-sensitive)
            99,  # Out of range number
            None,  # Null
            "",  # Empty string
        ]

        for invalid_level in invalid_claimed_levels:
            payload = {
                "skill_id": str(skill.id),
                "claimed_level": invalid_level,
            }

            response = client.post(
                "/talents/me/skills",
                json=payload,
                headers={"X-Debug-User-Id": str(user_talent_alice.id)},
            )

            # Must be 400, not 409 or any other code
            assert response.status_code == 400, (
                f"Expected 400 for invalid claimed_level={invalid_level}, "
                f"got {response.status_code}: {response.text}"
            )

            # Verify no claim was created
            from sqlalchemy import select
            from app.models import SkillClaim

            existing_claims = session.execute(
                select(SkillClaim).where(
                    (SkillClaim.talent_id == talent_alice.id) &
                    (SkillClaim.skill_id == skill.id)
                )
            ).scalars().all()

            assert len(existing_claims) == 0, (
                f"No skill claim should be created for invalid claimed_level={invalid_level}"
            )

    def test_post_skills_missing_claimed_level_returns_400(self, client, session, user_talent_alice, talent_alice):
        """
        AC-10 (VER-02): POST /talents/me/skills without claimed_level field → 400.

        Scenario:
        - Payload missing claimed_level field entirely
        - Expected: 400 VALIDATION_ERROR

        Acceptance Criteria:
        - Status code: 400
        - Response indicates required field missing
        """
        from app.models import Skill

        skill = Skill(
            slug="test-skill-missing-level",
            name_tr="Test Skill Missing Level",
            name_en="Test Skill Missing Level",
            category="LANGUAGE",
            status="ACTIVE",
            parent_id=None,
            merged_into_id=None,
        )
        session.add(skill)
        session.flush()

        # Payload missing claimed_level
        payload = {
            "skill_id": str(skill.id),
            # claimed_level intentionally omitted
        }

        response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        # Must be 400 (validation error)
        assert response.status_code == 400, (
            f"Expected 400 for missing claimed_level, got {response.status_code}: {response.text}"
        )


# ============================================================================
# PATCH /talents/me: AC-14 (L-06) — updated_at regression test
# ============================================================================


class TestUpdatedAtRegression:
    """AC-14 (L-06): PATCH /talents/me updates updated_at automatically via TimestampMixin."""

    def test_patch_talents_me_updates_updated_at_automatically(
        self, client, session, user_talent_alice, talent_alice
    ):
        """
        AC-14 (L-06): PATCH /talents/me automatically updates updated_at via TimestampMixin.

        Scenario:
        - Get Alice's current profile (capture updated_at timestamp)
        - Wait a small delay (to ensure time passes)
        - PATCH /talents/me with valid update (e.g., headline change)
        - Get Alice's profile again
        - Verify: updated_at is now strictly greater than before

        Acceptance Criteria:
        - Status code: 200
        - updated_at (after PATCH) > updated_at (before PATCH)
        - TimestampMixin automatically set updated_at (not manually in service code)
        - No explicit "updated_at" parameter accepted in payload

        Threat model: If service code manually sets updated_at, it might be overridable
        via client payload (AC-14 in plan.md lists this as a potential security issue).
        Test verifies TimestampMixin handles it, not manual code.
        """
        import time

        # Get initial profile and capture updated_at
        response_before = client.get(
            "/me",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )
        assert response_before.status_code == 200

        data_before = response_before.json()
        talent_before = data_before["talent_profile"]
        updated_at_before = talent_before.get("updated_at")

        assert updated_at_before is not None, "Profile should have updated_at timestamp"

        # Small delay to ensure time passes
        time.sleep(0.1)

        # PATCH: update headline
        payload = {"headline": "Updated Headline for Regression Test"}

        response_patch = client.patch(
            "/talents/me",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )
        assert response_patch.status_code == 200

        # Get updated profile
        response_after = client.get(
            "/me",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )
        assert response_after.status_code == 200

        data_after = response_after.json()
        talent_after = data_after["talent_profile"]
        updated_at_after = talent_after.get("updated_at")

        assert updated_at_after is not None, "Profile should have updated_at after PATCH"

        # Verify: updated_at advanced
        # Compare as strings (ISO 8601 format) or parse if they're datetime objects
        assert updated_at_after > updated_at_before, (
            f"updated_at should increase after PATCH. "
            f"Before: {updated_at_before}, After: {updated_at_after}"
        )

        # Verify database record directly
        alice_db = session.query(TalentProfile).filter_by(id=talent_alice.id).first()
        assert alice_db.updated_at is not None, "DB record should have updated_at"
        # Note: If updated_at is a datetime object, compare as such
        # If it's stored/returned as string, the string comparison above is sufficient

    def test_patch_talents_me_cannot_override_updated_at_in_payload(
        self, client, session, user_talent_alice, talent_alice
    ):
        """
        AC-14 (L-06): Sending updated_at in payload should be ignored.

        Scenario:
        - Get current updated_at
        - PATCH with explicit updated_at field set to past timestamp
        - Verify: server's updated_at is NOT the payload value (it's current time)

        Acceptance Criteria:
        - Payload's updated_at is ignored
        - Server's actual updated_at is current time (or newer)
        """
        from datetime import datetime, timedelta, timezone

        # Get initial updated_at
        response_before = client.get(
            "/me",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )
        data_before = response_before.json()
        updated_at_before = data_before["talent_profile"]["updated_at"]

        # Create a fake old timestamp (24 hours ago)
        old_timestamp = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        # PATCH: include updated_at in payload (should be ignored)
        payload = {
            "headline": "New Headline",
            "updated_at": old_timestamp,  # Attempting to set old timestamp
        }

        response_patch = client.patch(
            "/talents/me",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )
        assert response_patch.status_code == 200

        # Get updated profile
        response_after = client.get(
            "/me",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )
        data_after = response_after.json()
        updated_at_after = data_after["talent_profile"]["updated_at"]

        # Verify: updated_at is NOT the old_timestamp (payload was ignored)
        assert updated_at_after != old_timestamp, (
            f"Server should ignore payload's updated_at. "
            f"Payload had: {old_timestamp}, Server returned: {updated_at_after}"
        )

        # Verify: updated_at advanced from before
        assert updated_at_after > updated_at_before, (
            f"updated_at should be current time, not payload value. "
            f"Before: {updated_at_before}, After: {updated_at_after}, "
            f"Attempted payload: {old_timestamp}"
        )
