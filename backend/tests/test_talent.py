"""
Talent profile endpoint tests (YET-7 — user-talent-profili).

Implements AC-1 through AC-8 and behavior contract from atdd.md.

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Each AC has one or more test functions
- Error responses validated against {"code": ..., "message": ..., "request_id": ...} schema

Status: Tests are RED/IMPORT-ERROR — implementation not yet written.
This is expected behavior. Tests implement behavior contract (ATDD).
"""

import pytest

from app.models import TalentProfile, User


# ============================================================================
# Fixtures: Users, TalentProfiles
# ============================================================================


@pytest.fixture
def user_talent_a(session):
    """Talent user A (basic talent profile)."""
    user = User(email="talent-a@example.com", password_hash="hash_talent_a")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_b(session):
    """Talent user B (for slug conflict and isolation tests)."""
    user = User(email="talent-b@example.com", password_hash="hash_talent_b")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent_a(session, user_talent_a):
    """Talent profile for user_talent_a."""
    profile = TalentProfile(
        user_id=user_talent_a.id,
        full_name="Test Talent A",
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
def talent_b(session, user_talent_b):
    """Talent profile for user_talent_b."""
    profile = TalentProfile(
        user_id=user_talent_b.id,
        full_name="Test Talent B",
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
def talent_b_with_slug(session, user_talent_b):
    """Talent profile for user_talent_b with a public_slug (for conflict tests)."""
    profile = TalentProfile(
        user_id=user_talent_b.id,
        full_name="Test Talent B Slug",
        visibility="PUBLIC",
        public_slug="talent-b-slug",
        headline=None,
        city=None,
        department=None,
        study_year=None,
    )
    session.add(profile)
    session.flush()
    return profile


# ============================================================================
# AC-1: GET /me → 200 + {user, talent_profile, organizations[], institutions[]}
# ============================================================================


class TestGetMe:
    """AC-1: GET /me returns current user's profile and associations."""

    @pytest.fixture
    def platform_admin_user(self, session):
        """Platform admin user for testing is_platform_admin field."""
        user = User(
            email="admin@example.com",
            password_hash="hash_admin",
            is_platform_admin=True,
        )
        session.add(user)
        session.flush()
        return user

    @pytest.fixture
    def platform_admin_talent(self, session, platform_admin_user):
        """Talent profile for platform_admin_user."""
        from app.models import TalentProfile

        profile = TalentProfile(
            user_id=platform_admin_user.id,
            full_name="Admin Talent",
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

    def test_get_me_happy_path(self, client, session, user_talent_a, talent_a):
        """
        AC-1: GET /me → 200 + user + talent_profile + organizations[] + institutions[].

        Acceptance Criteria:
        - Status code: 200 OK
        - Response contains user data (id, email)
        - Response contains talent_profile (id, full_name, visibility, etc.)
        - Response contains organizations[] (empty or populated based on user's org memberships)
        - Response contains institutions[] (empty or populated based on user's institution links)
        """
        response = client.get("/me", headers={"X-Debug-User-Id": str(user_talent_a.id)})

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Assert: user present
        assert "user" in data
        assert data["user"]["id"] == str(user_talent_a.id)
        assert data["user"]["email"] == "talent-a@example.com"

        # Assert: talent_profile present
        assert "talent_profile" in data
        assert data["talent_profile"]["user_id"] == str(user_talent_a.id)
        assert data["talent_profile"]["full_name"] == "Test Talent A"
        assert data["talent_profile"]["visibility"] == "PRIVATE"

        # Assert: organizations[] present (may be empty)
        assert "organizations" in data
        assert isinstance(data["organizations"], list)

        # Assert: institutions[] present (may be empty)
        assert "institutions" in data
        assert isinstance(data["institutions"], list)

    def test_get_me_returns_current_user_only(self, client, user_talent_a, user_talent_b, talent_a, talent_b):
        """
        AC-1, AC-S1: GET /me returns only authenticated user's data.

        Even if talent_b exists in DB, GET /me for user_talent_a returns only A's data.
        """
        response = client.get("/me", headers={"X-Debug-User-Id": str(user_talent_a.id)})

        assert response.status_code == 200
        data = response.json()

        assert data["user"]["id"] == str(user_talent_a.id)
        assert data["talent_profile"]["user_id"] == str(user_talent_a.id)

    def test_get_me_unauthenticated_401(self, client):
        """
        AC-2: GET /me without X-Debug-User-Id header → 401 Unauthorized.

        Acceptance Criteria:
        - Status code: 401
        - No user data returned
        """
        response = client.get("/me")

        # Should fail because auth middleware requires X-Debug-User-Id
        assert response.status_code == 401

    def test_get_me_admin_user_is_platform_admin_true(self, client, session, platform_admin_user, platform_admin_talent):
        """
        AC-1 + AC-S2: GET /me for platform_admin=true user returns is_platform_admin: true.

        Acceptance Criteria:
        - Status code: 200
        - response.user.is_platform_admin == True (TAM EŞLEŞME)
        - Response does not contain institution_admin_ids, org_admin_ids, supervisor_institution_ids (AC-S2)
        """
        response = client.get("/me", headers={"X-Debug-User-Id": str(platform_admin_user.id)})

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Assert: user.is_platform_admin is True (TAM EŞLEŞME)
        assert "user" in data
        assert "is_platform_admin" in data["user"], "Response must contain is_platform_admin field"
        assert data["user"]["is_platform_admin"] is True, (
            f"Expected is_platform_admin=True, got {data['user'].get('is_platform_admin')}"
        )

        # Assert: AC-S2 — no extra role fields
        user_obj = data["user"]
        assert "institution_admin_ids" not in user_obj, "Response must not contain institution_admin_ids"
        assert "org_admin_ids" not in user_obj, "Response must not contain org_admin_ids"
        assert "supervisor_institution_ids" not in user_obj, "Response must not contain supervisor_institution_ids"

    def test_get_me_non_admin_user_is_platform_admin_false(self, client, session, user_talent_a, talent_a):
        """
        AC-2 + AC-S2: GET /me for is_platform_admin=false user returns is_platform_admin: false.

        Acceptance Criteria:
        - Status code: 200
        - response.user.is_platform_admin == False (TAM EŞLEŞME)
        - Response does not contain extra role fields (AC-S2)
        """
        response = client.get("/me", headers={"X-Debug-User-Id": str(user_talent_a.id)})

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Assert: user.is_platform_admin is False (TAM EŞLEŞME)
        assert "user" in data
        assert "is_platform_admin" in data["user"], "Response must contain is_platform_admin field"
        assert data["user"]["is_platform_admin"] is False, (
            f"Expected is_platform_admin=False, got {data['user'].get('is_platform_admin')}"
        )

        # Assert: AC-S2 — no extra role fields
        user_obj = data["user"]
        assert "institution_admin_ids" not in user_obj, "Response must not contain institution_admin_ids"
        assert "org_admin_ids" not in user_obj, "Response must not contain org_admin_ids"
        assert "supervisor_institution_ids" not in user_obj, "Response must not contain supervisor_institution_ids"


# ============================================================================
# AC-3: PATCH /talents/me — Update talent profile (valid fields)
# ============================================================================


class TestPatchTalentMe:
    """AC-3: PATCH /talents/me updates talent profile."""

    def test_patch_talents_me_single_field(self, client, session, user_talent_a, talent_a):
        """
        AC-3: PATCH /talents/me with single field (headline) → 200 + updated profile.

        Acceptance Criteria:
        - Status code: 200
        - Only updated field changes (headline)
        - Other fields unchanged
        - Updated talent_profile returned in response
        """
        payload = {"headline": "Senior Software Engineer"}

        response = client.patch("/talents/me", json=payload, headers={"X-Debug-User-Id": str(user_talent_a.id)})

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Assert: response is talent_profile object
        tp = data

        # Assert: headline updated
        assert tp["headline"] == "Senior Software Engineer"

        # Assert: other fields unchanged
        assert tp["full_name"] == "Test Talent A"
        assert tp["visibility"] == "PRIVATE"
        assert tp["city"] is None

        # Verify in database
        db_profile = session.query(TalentProfile).filter_by(id=talent_a.id).first()
        assert db_profile.headline == "Senior Software Engineer"

    def test_patch_talents_me_multiple_fields(self, client, session, user_talent_a, talent_a):
        """AC-3: PATCH /talents/me with multiple fields → all updated."""
        payload = {
            "headline": "Data Scientist",
            "city": "Istanbul",
            "department": "AI/ML",
        }

        response = client.patch("/talents/me", json=payload, headers={"X-Debug-User-Id": str(user_talent_a.id)})

        assert response.status_code == 200
        data = response.json()
        tp = data

        assert tp["headline"] == "Data Scientist"
        assert tp["city"] == "Istanbul"
        assert tp["department"] == "AI/ML"

    def test_patch_talents_me_study_year_valid(self, client, session, user_talent_a, talent_a):
        """AC-3: PATCH /talents/me with valid study_year (1-8) → 200."""
        payload = {"study_year": 3}

        response = client.patch("/talents/me", json=payload, headers={"X-Debug-User-Id": str(user_talent_a.id)})

        assert response.status_code == 200
        data = response.json()
        assert data["study_year"] == 3

    def test_patch_talents_me_visibility_valid(self, client, session, user_talent_a, talent_a):
        """AC-3: PATCH /talents/me with valid visibility enum → 200."""
        payload = {"visibility": "PUBLIC"}

        response = client.patch("/talents/me", json=payload, headers={"X-Debug-User-Id": str(user_talent_a.id)})

        assert response.status_code == 200
        data = response.json()
        assert data["visibility"] == "PUBLIC"

    def test_patch_talents_me_public_slug_valid(self, client, session, user_talent_a, talent_a):
        """AC-3: PATCH /talents/me with valid public_slug → 200."""
        payload = {"public_slug": "my-unique-slug"}

        response = client.patch("/talents/me", json=payload, headers={"X-Debug-User-Id": str(user_talent_a.id)})

        assert response.status_code == 200
        data = response.json()
        assert data["public_slug"] == "my-unique-slug"


# ============================================================================
# AC-4: public_slug collision → 409 SLUG_TAKEN (atomicity)
# ============================================================================


class TestPublicSlugCollision:
    """AC-4: Duplicate public_slug → 409 SLUG_TAKEN, no update."""

    def test_patch_talents_me_slug_taken_409(self, client, session, user_talent_a, talent_a, talent_b_with_slug):
        """
        AC-4: PATCH /talents/me with slug already used by another profile → 409.

        Acceptance Criteria:
        - Status code: 409 Conflict
        - Error code: "SLUG_TAKEN"
        - No fields updated (atomicity)
        - Response does not reveal conflicting profile's owner
        """
        payload = {"public_slug": "talent-b-slug"}  # Already taken by talent_b

        response = client.patch("/talents/me", json=payload, headers={"X-Debug-User-Id": str(user_talent_a.id)})

        assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"

        data = response.json()

        # Assert: error code is SLUG_TAKEN
        assert data.get("code") == "SLUG_TAKEN", f"Expected code='SLUG_TAKEN', got {data.get('code')}"

        # Assert: message is present (Türkçe)
        assert "message" in data
        assert isinstance(data["message"], str)

        # Assert: request_id present
        assert "request_id" in data

        # Verify in database: talent_a's slug unchanged
        db_profile = session.query(TalentProfile).filter_by(id=talent_a.id).first()
        assert db_profile.public_slug is None, "Slug should not be updated after conflict"

    def test_patch_talents_me_slug_taken_no_user_info_in_response(self, client, session, user_talent_a, talent_a, talent_b_with_slug):
        """
        AC-S3: 409 SLUG_TAKEN response does not contain conflicting profile owner's info.

        Acceptance Criteria:
        - Response code: 409
        - Response body does NOT contain conflicting profile's user_id, email, full_name
        - Response body contains only: code, message, request_id
        """
        payload = {"public_slug": "talent-b-slug"}

        response = client.patch("/talents/me", json=payload, headers={"X-Debug-User-Id": str(user_talent_a.id)})

        assert response.status_code == 409

        data = response.json()

        # Assert: only expected keys in response
        # (code, message, request_id; no user data)
        assert set(data.keys()) <= {"code", "message", "request_id"}

        # Assert: response does not mention talent_b's ID or email
        response_str = str(data)
        assert str(talent_b_with_slug.user_id) not in response_str, "Response should not reveal conflicting user's ID"
        assert "talent-b@example.com" not in response_str, "Response should not reveal conflicting user's email"


# ============================================================================
# AC-5: Invalid input (study_year out of range, visibility enum) → 422
# ============================================================================


class TestInvalidInput:
    """AC-5: Validation errors → 422 Unprocessable Entity."""

    @pytest.mark.parametrize("study_year", [0, 9, 10, -1])
    def test_patch_talents_me_study_year_out_of_range_422(self, client, session, user_talent_a, talent_a, study_year):
        """
        AC-5: PATCH /talents/me with study_year outside 1-8 range → 422.

        Acceptance Criteria:
        - Status code: 422 Unprocessable Entity
        - No fields updated (atomicity)
        """
        payload = {"study_year": study_year}

        response = client.patch("/talents/me", json=payload, headers={"X-Debug-User-Id": str(user_talent_a.id)})

        assert response.status_code == 422, f"Expected 422 for study_year={study_year}, got {response.status_code}"

        # Verify: study_year not updated in database
        db_profile = session.query(TalentProfile).filter_by(id=talent_a.id).first()
        assert db_profile.study_year is None, "study_year should not be updated after validation error"

    @pytest.mark.parametrize("invalid_visibility", ["INVALID", "private", "secret", ""])
    def test_patch_talents_me_visibility_invalid_enum_422(self, client, session, user_talent_a, talent_a, invalid_visibility):
        """
        AC-5: PATCH /talents/me with invalid visibility enum → 422.

        Acceptance Criteria:
        - Status code: 422
        - No update occurs
        """
        payload = {"visibility": invalid_visibility}

        response = client.patch("/talents/me", json=payload, headers={"X-Debug-User-Id": str(user_talent_a.id)})

        assert response.status_code == 422, f"Expected 422 for visibility={invalid_visibility}, got {response.status_code}"

        # Verify: visibility unchanged
        db_profile = session.query(TalentProfile).filter_by(id=talent_a.id).first()
        assert db_profile.visibility == "PRIVATE", "visibility should not be updated after validation error"

    def test_patch_talents_me_partial_failure_all_rejected(self, client, session, user_talent_a, talent_a):
        """
        AC-5 (partial failure): PATCH with one invalid field → entire request rejected (atomicity).

        Scenario: headline is valid, study_year is invalid.
        Expected: both rejected, nothing updated.

        Acceptance Criteria:
        - Status code: 422
        - headline NOT updated
        - study_year NOT updated (even though validation failed on study_year, not headline)
        """
        payload = {
            "headline": "Valid Headline",
            "study_year": 99,  # Invalid
        }

        response = client.patch("/talents/me", json=payload, headers={"X-Debug-User-Id": str(user_talent_a.id)})

        assert response.status_code == 422

        # Verify: neither field updated
        db_profile = session.query(TalentProfile).filter_by(id=talent_a.id).first()
        assert db_profile.headline is None, "Valid field should not be updated when request fails validation"
        assert db_profile.study_year is None


# ============================================================================
# AC-6: institution_id field is silently ignored
# ============================================================================


class TestInstitutionIdIgnored:
    """AC-6: PATCH /talents/me ignores institution_id field."""

    def test_patch_talents_me_institution_id_ignored(self, client, session, user_talent_a, talent_a):
        """
        AC-6: PATCH /talents/me with institution_id in body → field is ignored.

        Acceptance Criteria:
        - Status code: 200
        - institution_id NOT updated (remains None or original value)
        - Other fields (if valid) ARE updated
        """
        from app.models import Institution

        # Create an institution to use in the payload
        inst = Institution(name="Test Inst", domain="test.edu.tr")
        session.add(inst)
        session.flush()

        payload = {
            "headline": "New Headline",
            "institution_id": str(inst.id),  # This should be ignored
        }

        response = client.patch("/talents/me", json=payload, headers={"X-Debug-User-Id": str(user_talent_a.id)})

        assert response.status_code == 200

        # Verify: headline updated, institution_id unchanged
        db_profile = session.query(TalentProfile).filter_by(id=talent_a.id).first()
        assert db_profile.headline == "New Headline"
        assert db_profile.institution_id is None, "institution_id should remain None (ignored)"


# ============================================================================
# AC-7: Empty body {} → 200 (no-op, hiçbir şey yapılmadı ama hata değil)
# ============================================================================


class TestEmptyBody:
    """AC-7: PATCH /talents/me with empty body {} → 200, no change."""

    def test_patch_talents_me_empty_body_200(self, client, session, user_talent_a, talent_a):
        """
        AC-7: PATCH /talents/me with empty body → 200, profile unchanged.

        Acceptance Criteria:
        - Status code: 200 OK (not an error)
        - No fields updated
        - Current profile returned as-is
        """
        payload = {}

        response = client.patch("/talents/me", json=payload, headers={"X-Debug-User-Id": str(user_talent_a.id)})

        assert response.status_code == 200, f"Empty body should not be an error, got {response.status_code}"

        data = response.json()

        # Assert: talent_profile returned unchanged
        tp = data
        assert tp["full_name"] == "Test Talent A"
        assert tp["headline"] is None
        assert tp["city"] is None

        # Verify in database: nothing changed
        db_profile = session.query(TalentProfile).filter_by(id=talent_a.id).first()
        assert db_profile.headline is None
        assert db_profile.city is None


# ============================================================================
# AC-8: User with talent_id but kind != "TALENT" can still update their profile
# ============================================================================


class TestTalentUpdateWithMixedRole:
    """AC-8: User with kind != "TALENT" but talent_id non-null can update profile."""

    def test_patch_talents_me_with_mixed_role_200(self, client, session, user_talent_a, talent_a):
        """
        AC-8: User who is TALENT in terms of talent_profile but also has
        other roles (e.g., INST_COORDINATOR) can still PATCH their profile.

        Setup:
        - user_talent_a has a TalentProfile (talent_id is set)
        - Make user_talent_a a COORDINATOR in some institution
        - This changes Principal.kind to "COORDINATOR" (not "TALENT")
        - But Principal.talent_id is still set
        - PATCH /talents/me should still work (return 200)

        Acceptance Criteria:
        - Status code: 200 (authorization passes based on talent_id, not kind)
        - Profile updated successfully
        """
        from app.models import Institution, InstitutionMember

        # Create institution and make user_talent_a a COORDINATOR
        inst = Institution(name="Test Inst for Mixed Role", domain="mixed.edu.tr")
        session.add(inst)
        session.flush()

        member = InstitutionMember(
            institution_id=inst.id,
            user_id=user_talent_a.id,
            role="COORDINATOR"
        )
        session.add(member)
        session.flush()

        # Now Principal.kind will be "COORDINATOR" (not "TALENT")
        # But Principal.talent_id is still set
        payload = {"headline": "Mixed Role Headline"}

        response = client.patch("/talents/me", json=payload, headers={"X-Debug-User-Id": str(user_talent_a.id)})

        # Should succeed because talent_id is present, regardless of kind
        assert response.status_code == 200, (
            f"User with talent_id should be able to update profile even if kind != TALENT. "
            f"Got {response.status_code}: {response.text}"
        )

        data = response.json()
        assert data["headline"] == "Mixed Role Headline"


# ============================================================================
# Response Schema Validation (all responses must follow API.md §1.4)
# ============================================================================


class TestResponseSchema:
    """Verify response schemas match API.md §1.4 error contract."""

    def test_error_response_has_code_message_request_id(self, client, user_talent_a, talent_a):
        """All error responses must have {code, message, request_id}."""
        # Trigger a validation error
        payload = {"study_year": 999}

        response = client.patch("/talents/me", json=payload, headers={"X-Debug-User-Id": str(user_talent_a.id)})

        assert response.status_code == 422

        data = response.json()

        # Assert: error has code, message, request_id
        assert "code" in data, "Error response must have 'code' field"
        assert "message" in data, "Error response must have 'message' field"
        assert "request_id" in data, "Error response must have 'request_id' field"

        # Assert: code is SCREAMING_SNAKE_CASE (not detail)
        assert isinstance(data["code"], str)
        assert data["code"].isupper() or "_" in data["code"]

        # Assert: message is Türkçe (non-empty string)
        assert isinstance(data["message"], str)
        assert len(data["message"]) > 0

    def test_success_response_schema(self, client, user_talent_a, talent_a):
        """Successful GET /me and PATCH /talents/me responses have expected structure."""
        # GET /me
        response = client.get("/me", headers={"X-Debug-User-Id": str(user_talent_a.id)})

        assert response.status_code == 200

        data = response.json()

        # Assert: user, talent_profile, organizations, institutions present
        assert "user" in data
        assert "talent_profile" in data
        assert "organizations" in data
        assert "institutions" in data
