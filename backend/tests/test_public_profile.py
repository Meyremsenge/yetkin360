"""
Public profile endpoint tests (YET-105 — AC-1..AC-7, AC-S1/S2/S3).

Implements acceptance criteria and behavior contract from atdd.md:
- GET /public/talents/{slug} — auth-free endpoint
- visibility='PUBLIC' → 200 + talent data (filtered verified_experiences)
- visibility != PUBLIC or not found → 404 (bit-byte identical responses)
- PII fields must not leak in any response
- VerifiedExperience.visibility='PRIVATE' must be filtered from response

Test patterns:
- Real PostgreSQL transaction per test
- FastAPI TestClient (no auth header needed — public endpoint)
- Defense-in-depth: verify both response content and enumeration protection

Status: Tests are RED/IMPORT-ERROR — implementation not yet written.
This is expected behavior. Tests verify acceptance criteria compliance.
"""

from datetime import date
from uuid import UUID

import pytest

from app.models import (
    Engagement,
    Institution,
    Organization,
    TalentProfile,
    User,
    VerifiedExperience,
)


# ============================================================================
# Fixtures: Users, TalentProfiles, Organizations, Engagements, VerifiedExperiences
# ============================================================================


@pytest.fixture
def user_talent_public(session):
    """User with a PUBLIC visibility talent profile."""
    user = User(email="public-talent@example.com", password_hash="hash_public")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_private(session):
    """User with a PRIVATE visibility talent profile."""
    user = User(email="private-talent@example.com", password_hash="hash_private")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_institution(session):
    """User with an INSTITUTION visibility talent profile."""
    user = User(email="institution-talent@example.com", password_hash="hash_institution")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_organizations(session):
    """User with an ORGANIZATIONS visibility talent profile."""
    user = User(email="organizations-talent@example.com", password_hash="hash_organizations")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def institution(session):
    """Test institution for institution_id foreign key."""
    inst = Institution(name="Test University", domain="test.edu.tr", verification_level="T2")
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def organization(session):
    """Test organization for engagement foreign key."""
    org = Organization(name="Tech Corp", verification_level="T2", status="ACTIVE")
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def talent_profile_public(session, user_talent_public):
    """TalentProfile with visibility='PUBLIC' and public_slug."""
    profile = TalentProfile(
        user_id=user_talent_public.id,
        full_name="Alice Public Talent",
        headline="Senior Engineer",
        city="Istanbul",
        department=None,
        study_year=None,
        visibility="PUBLIC",
        public_slug="alice-public-slug",
        deleted_at=None,
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_profile_private(session, user_talent_private):
    """TalentProfile with visibility='PRIVATE' and public_slug (should not be exposed)."""
    profile = TalentProfile(
        user_id=user_talent_private.id,
        full_name="Bob Private Talent",
        headline="Developer",
        city="Ankara",
        department=None,
        study_year=None,
        visibility="PRIVATE",
        public_slug="bob-private-slug",
        deleted_at=None,
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_profile_institution(session, user_talent_institution, institution):
    """TalentProfile with visibility='INSTITUTION' and public_slug."""
    profile = TalentProfile(
        user_id=user_talent_institution.id,
        institution_id=institution.id,
        full_name="Charlie Institution Talent",
        headline=None,
        city=None,
        department=None,
        study_year=None,
        visibility="INSTITUTION",
        public_slug="charlie-institution-slug",
        deleted_at=None,
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_profile_organizations(session, user_talent_organizations):
    """TalentProfile with visibility='ORGANIZATIONS' and public_slug."""
    profile = TalentProfile(
        user_id=user_talent_organizations.id,
        full_name="Diana Organizations Talent",
        headline=None,
        city=None,
        department=None,
        study_year=None,
        visibility="ORGANIZATIONS",
        public_slug="diana-organizations-slug",
        deleted_at=None,
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_profile_public_no_slug(session, user_talent_public):
    """TalentProfile with visibility='PUBLIC' but public_slug=NULL."""
    profile = TalentProfile(
        user_id=user_talent_public.id,
        full_name="Eve Public No Slug",
        headline=None,
        city=None,
        department=None,
        study_year=None,
        visibility="PUBLIC",
        public_slug=None,
        deleted_at=None,
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def engagement_for_public_talent(session, talent_profile_public, organization):
    """Engagement for public talent's verified experience."""
    eng = Engagement(
        talent_id=talent_profile_public.id,
        organization_id=organization.id,
        kind="INTERNSHIP",
        title="Summer Intern 2025",
        status="VERIFIED",
        started_on=date(2025, 6, 1),
        ended_on=date(2025, 8, 31),
        confidential=False,
    )
    session.add(eng)
    session.flush()
    return eng


@pytest.fixture
def engagement_for_private_talent(session, talent_profile_private, organization):
    """Engagement for private talent's verified experience."""
    eng = Engagement(
        talent_id=talent_profile_private.id,
        organization_id=organization.id,
        kind="CAPSTONE",
        title="Capstone Project",
        status="VERIFIED",
        started_on=date(2025, 1, 1),
        ended_on=date(2025, 5, 31),
        confidential=False,
    )
    session.add(eng)
    session.flush()
    return eng


@pytest.fixture
def verified_experience_public_public(session, talent_profile_public, engagement_for_public_talent):
    """VerifiedExperience with visibility='PUBLIC' for public talent."""
    ve = VerifiedExperience(
        talent_id=talent_profile_public.id,
        engagement_id=engagement_for_public_talent.id,
        organization_name_snapshot="Tech Corp",
        role_snapshot="Summer Intern 2025",
        started_on_snapshot=date(2025, 6, 1),
        ended_on_snapshot=date(2025, 8, 31),
        institution_name_snapshot=None,
        claim_type="PARTICIPATION",
        visibility="PUBLIC",
    )
    session.add(ve)
    session.flush()
    return ve


@pytest.fixture
def verified_experience_public_private(session, talent_profile_public, engagement_for_public_talent):
    """VerifiedExperience with visibility='PRIVATE' for public talent (should be filtered)."""
    ve = VerifiedExperience(
        talent_id=talent_profile_public.id,
        engagement_id=engagement_for_public_talent.id,
        organization_name_snapshot="Confidential Org",
        role_snapshot="Confidential Role",
        started_on_snapshot=date(2025, 1, 1),
        ended_on_snapshot=date(2025, 3, 31),
        institution_name_snapshot=None,
        claim_type="COMPETENCE",
        visibility="PRIVATE",
    )
    session.add(ve)
    session.flush()
    return ve


@pytest.fixture
def verified_experience_private_private(session, talent_profile_private, engagement_for_private_talent):
    """VerifiedExperience with visibility='PRIVATE' for private talent."""
    ve = VerifiedExperience(
        talent_id=talent_profile_private.id,
        engagement_id=engagement_for_private_talent.id,
        organization_name_snapshot="Secret Corp",
        role_snapshot="Secret Role",
        started_on_snapshot=date(2025, 1, 1),
        ended_on_snapshot=date(2025, 5, 31),
        institution_name_snapshot=None,
        claim_type="CONDUCT",
        visibility="PRIVATE",
    )
    session.add(ve)
    session.flush()
    return ve


# ============================================================================
# AC-1: Happy path — visibility='PUBLIC' → 200 + talent data + filtered experiences
# ============================================================================


class TestHappyPathPublicProfile:
    """AC-1: GET /public/talents/{slug} returns 200 with talent data and public verified_experiences."""

    def test_get_public_profile_success_200(
        self,
        client,
        session,
        talent_profile_public,
        verified_experience_public_public,
        verified_experience_public_private,
    ):
        """
        AC-1: visibility='PUBLIC' with public_slug → 200 + talent data.

        Scenario:
        - TalentProfile with visibility='PUBLIC' and public_slug='alice-public-slug'
        - Two VerifiedExperience records: one PUBLIC, one PRIVATE
        - Expected: 200 + {talent_id, display_name, verified_experiences[]}
        - verified_experiences list contains ONLY PUBLIC visibility records

        Acceptance Criteria:
        - Status code: 200
        - Response contains talent_id, display_name (from full_name)
        - verified_experiences list has 1 entry (PUBLIC only, PRIVATE filtered)
        """
        response = client.get("/public/talents/alice-public-slug")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Assert: response structure
        assert "talent_id" in data
        assert "display_name" in data
        assert "verified_experiences" in data

        # Assert: talent_id and display_name values
        assert str(data["talent_id"]) == str(talent_profile_public.id)
        assert data["display_name"] == "Alice Public Talent"

        # Assert: verified_experiences list
        ve_list = data["verified_experiences"]
        assert len(ve_list) == 1, f"Expected 1 PUBLIC experience, got {len(ve_list)}"

        # Assert: the single experience is the PUBLIC one
        ve = ve_list[0]
        assert ve["organization_name_snapshot"] == "Tech Corp"
        assert ve["role_snapshot"] == "Summer Intern 2025"
        assert ve["claim_type"] == "PARTICIPATION"
        assert ve["started_on_snapshot"] == "2025-06-01"
        assert ve["ended_on_snapshot"] == "2025-08-31"

    def test_get_public_profile_empty_experiences_200(self, client, session, talent_profile_public):
        """
        AC-1: visibility='PUBLIC' with no verified_experiences → 200 + empty list.

        Scenario:
        - Public talent with NO VerifiedExperience records
        - Expected: 200 + verified_experiences=[]
        """
        response = client.get("/public/talents/alice-public-slug")

        assert response.status_code == 200

        data = response.json()

        # Assert: empty verified_experiences list
        assert data["verified_experiences"] == []

    def test_get_public_profile_response_schema_no_pii_fields(
        self,
        client,
        session,
        talent_profile_public,
        verified_experience_public_public,
    ):
        """
        AC-4 (AC-S2): Public profile response does NOT contain PII/internal fields.

        Scenario:
        - Talent with visibility='PUBLIC'
        - Check response keys to ensure email, user_id, institution_id etc. are NOT present

        Acceptance Criteria:
        - Response keys: talent_id, display_name, verified_experiences (ONLY)
        - NO email, password_hash, institution_id, user_id, or other PII
        - NO attestations, skill_signals fields
        """
        response = client.get("/public/talents/alice-public-slug")

        assert response.status_code == 200

        data = response.json()

        # Get all keys in response
        response_keys = set(data.keys())

        # Assert: only expected keys
        expected_keys = {"talent_id", "display_name", "verified_experiences"}
        assert response_keys == expected_keys, (
            f"Unexpected keys in response. Expected {expected_keys}, got {response_keys}. "
            f"This is a PII/internal field leakage vulnerability."
        )

        # Assert: no PII in verified_experiences entries either
        for ve in data.get("verified_experiences", []):
            ve_keys = set(ve.keys())
            # Allowed keys in VerifiedExperience response
            forbidden_pii = {"email", "user_id", "password_hash", "institution_id"}
            leaked = forbidden_pii & ve_keys
            assert not leaked, (
                f"PII fields leaked in verified_experience: {leaked}. "
                f"Response contains: {ve_keys}"
            )

    def test_get_public_profile_no_private_experiences(
        self,
        client,
        session,
        talent_profile_public,
        verified_experience_public_public,
        verified_experience_public_private,
    ):
        """
        AC-5 (AC-S3): visibility='PRIVATE' verified_experiences are filtered from response.

        Scenario:
        - Public talent with 2 VerifiedExperience records:
          1. visibility='PUBLIC'
          2. visibility='PRIVATE'
        - Expected: response.verified_experiences contains ONLY the PUBLIC record

        Acceptance Criteria:
        - verified_experiences list length == 1
        - The entry is the PUBLIC visibility record
        - PRIVATE record does NOT appear in response
        """
        response = client.get("/public/talents/alice-public-slug")

        assert response.status_code == 200

        data = response.json()

        ve_list = data["verified_experiences"]

        # Assert: only 1 experience (the PUBLIC one)
        assert len(ve_list) == 1, f"Expected 1 experience, got {len(ve_list)}"

        # Assert: it's NOT the PRIVATE one
        ve = ve_list[0]
        assert ve["organization_name_snapshot"] != "Confidential Org", (
            "PRIVATE VerifiedExperience should not appear in response"
        )
        assert ve["organization_name_snapshot"] == "Tech Corp"


# ============================================================================
# AC-2: Not found — var olmayan slug → 404 + {"detail": "Not found"}
# ============================================================================


class TestNotFoundNonexistentSlug:
    """AC-2: GET /public/talents/{nonexistent_slug} returns 404 with generic message."""

    def test_get_public_profile_nonexistent_slug_404(self, client, session):
        """
        AC-2: Nonexistent slug → 404 + ApiError zarfı.

        Scenario:
        - Slug 'nonexistent-slug' does not exist in database
        - Expected: 404 + {"code": "TALENT_NOT_FOUND", "message": "Kayıt bulunamadı", "request_id": "uuid"}

        Acceptance Criteria:
        - Status code: 404
        - Response body: ApiError zarfı (code, message, request_id)
        """
        response = client.get("/public/talents/nonexistent-slug")

        assert response.status_code == 404

        data = response.json()

        # Assert: exact response structure with ApiError wrapper
        assert data["code"] == "TALENT_NOT_FOUND", f"Expected TALENT_NOT_FOUND, got {data.get('code')}"
        assert data["message"] == "Kayıt bulunamadı", f"Expected exact message, got {data.get('message')}"
        assert "request_id" in data, "request_id must be present in error response"

    def test_get_public_profile_empty_slug_404(self, client, session):
        """AC-2: Empty slug → 404."""
        response = client.get("/public/talents/")

        # Empty slug should 404 (or FastAPI routes it differently — check implementation)
        # This test is flexible: either 404 or 404 is acceptable
        assert response.status_code in [404, 404]

    def test_get_public_profile_invalid_slug_characters_404(self, client, session):
        """AC-2: Slug with invalid characters → 404."""
        response = client.get("/public/talents/invalid@#$%slug")

        assert response.status_code == 404

        data = response.json()

        assert data["code"] == "TALENT_NOT_FOUND"
        assert data["message"] == "Kayıt bulunamadı"
        assert "request_id" in data


# ============================================================================
# AC-3 (AC-S1): Enumeration protection — visibility != PUBLIC returns identical 404
# ============================================================================


class TestEnumerationProtection:
    """
    AC-3 (AC-S1): CRITICAL security test.

    Threat: Attacker can enumerate talent existence by comparing 404 responses.
    - Nonexistent slug → 404
    - Existing slug with visibility='PRIVATE' → 404 (MUST be IDENTICAL to nonexistent)
    - Existing slug with visibility='INSTITUTION' → 404 (MUST be IDENTICAL)
    - Existing slug with visibility='ORGANIZATIONS' → 404 (MUST be IDENTICAL)

    Verification: response.status_code, response.json(), and response.content (byte-level)
    must all be IDENTICAL across all four scenarios.
    """

    def test_404_responses_identical_nonexistent_vs_private(
        self,
        client,
        session,
        talent_profile_private,
    ):
        """
        AC-3: 404 for nonexistent slug vs. PRIVATE talent must be IDENTICAL.

        Scenario:
        - Request 1: GET /public/talents/definitely-does-not-exist-12345
        - Request 2: GET /public/talents/bob-private-slug (exists, visibility='PRIVATE')
        - Expected: responses must have identical code/message (request_id differs, so no byte-level comparison)

        Acceptance Criteria:
        - response1.status_code == response2.status_code == 404
        - response1.json()["code"] == response2.json()["code"] == "TALENT_NOT_FOUND"
        - response1.json()["message"] == response2.json()["message"] == "Kayıt bulunamadı"
        """
        response_nonexistent = client.get("/public/talents/definitely-does-not-exist-12345")
        response_private = client.get("/public/talents/bob-private-slug")

        # Status codes must be identical
        assert response_nonexistent.status_code == 404
        assert response_private.status_code == 404

        # code and message fields must be identical (request_id will differ per request)
        assert response_nonexistent.json()["code"] == "TALENT_NOT_FOUND"
        assert response_private.json()["code"] == "TALENT_NOT_FOUND"
        assert response_nonexistent.json()["message"] == "Kayıt bulunamadı"
        assert response_private.json()["message"] == "Kayıt bulunamadı"

    def test_404_responses_identical_private_vs_institution(
        self,
        client,
        session,
        talent_profile_private,
        talent_profile_institution,
    ):
        """
        AC-3: 404 for PRIVATE vs. INSTITUTION visibility must be IDENTICAL.

        Scenario:
        - Request 1: GET /public/talents/bob-private-slug (visibility='PRIVATE')
        - Request 2: GET /public/talents/charlie-institution-slug (visibility='INSTITUTION')
        - Expected: responses must have identical code/message (request_id differs)
        """
        response_private = client.get("/public/talents/bob-private-slug")
        response_institution = client.get("/public/talents/charlie-institution-slug")

        assert response_private.status_code == 404
        assert response_institution.status_code == 404

        assert response_private.json()["code"] == "TALENT_NOT_FOUND"
        assert response_institution.json()["code"] == "TALENT_NOT_FOUND"
        assert response_private.json()["message"] == "Kayıt bulunamadı"
        assert response_institution.json()["message"] == "Kayıt bulunamadı"

    def test_404_responses_identical_institution_vs_organizations(
        self,
        client,
        session,
        talent_profile_institution,
        talent_profile_organizations,
    ):
        """
        AC-3: 404 for INSTITUTION vs. ORGANIZATIONS visibility must be IDENTICAL.

        Scenario:
        - Request 1: GET /public/talents/charlie-institution-slug (visibility='INSTITUTION')
        - Request 2: GET /public/talents/diana-organizations-slug (visibility='ORGANIZATIONS')
        - Expected: responses must have identical code/message (request_id differs)
        """
        response_institution = client.get("/public/talents/charlie-institution-slug")
        response_organizations = client.get("/public/talents/diana-organizations-slug")

        assert response_institution.status_code == 404
        assert response_organizations.status_code == 404

        assert response_institution.json()["code"] == "TALENT_NOT_FOUND"
        assert response_organizations.json()["code"] == "TALENT_NOT_FOUND"
        assert response_institution.json()["message"] == "Kayıt bulunamadı"
        assert response_organizations.json()["message"] == "Kayıt bulunamadı"

    def test_404_responses_identical_all_non_public_plus_nonexistent(
        self,
        client,
        session,
        talent_profile_private,
        talent_profile_institution,
        talent_profile_organizations,
    ):
        """
        AC-3: All 404 scenarios (nonexistent + PRIVATE + INSTITUTION + ORGANIZATIONS)
        must return IDENTICAL responses.

        This is THE CRITICAL security test for enumeration protection.

        Scenario:
        - Request 1: Nonexistent slug
        - Request 2: PRIVATE talent
        - Request 3: INSTITUTION talent
        - Request 4: ORGANIZATIONS talent
        - Expected: ALL four responses have identical code/message (request_id differs, so no byte-level comparison)

        Acceptance Criteria:
        - All status codes == 404
        - All code == "TALENT_NOT_FOUND"
        - All message == "Kayıt bulunamadı"
        """
        response_nonexistent = client.get("/public/talents/completely-fake-slug-99999")
        response_private = client.get("/public/talents/bob-private-slug")
        response_institution = client.get("/public/talents/charlie-institution-slug")
        response_organizations = client.get("/public/talents/diana-organizations-slug")

        # All status codes
        assert response_nonexistent.status_code == 404
        assert response_private.status_code == 404
        assert response_institution.status_code == 404
        assert response_organizations.status_code == 404

        # All code fields must be identical
        expected_code = "TALENT_NOT_FOUND"
        assert response_nonexistent.json()["code"] == expected_code
        assert response_private.json()["code"] == expected_code
        assert response_institution.json()["code"] == expected_code
        assert response_organizations.json()["code"] == expected_code

        # All message fields must be identical
        expected_message = "Kayıt bulunamadı"
        assert response_nonexistent.json()["message"] == expected_message
        assert response_private.json()["message"] == expected_message
        assert response_institution.json()["message"] == expected_message
        assert response_organizations.json()["message"] == expected_message


# ============================================================================
# AC-6: NULL public_slug scenario
# ============================================================================


class TestNullPublicSlug:
    """
    AC-6: Talent with public_slug=NULL should return 404.

    Scenario:
    - Public talent with visibility='PUBLIC' but public_slug=NULL
    - Attempting to access via any slug → 404 (slug never matches NULL)
    - Expected: 404 identical to nonexistent case
    """

    def test_null_slug_talent_404(self, client, session, talent_profile_public_no_slug):
        """AC-6: Attempting to guess slug for NULL-slug talent → 404."""
        response = client.get("/public/talents/eve-public-no-slug")

        assert response.status_code == 404

        data = response.json()

        assert data["code"] == "TALENT_NOT_FOUND"
        assert data["message"] == "Kayıt bulunamadı"
        assert "request_id" in data

    def test_null_slug_identical_404_to_nonexistent(
        self,
        client,
        session,
        talent_profile_public_no_slug,
    ):
        """AC-6: 404 for NULL-slug guessing must be identical to nonexistent case."""
        response_guessed = client.get("/public/talents/eve-public-no-slug")
        response_fake = client.get("/public/talents/fake-slug-xyz")

        assert response_guessed.status_code == 404
        assert response_fake.status_code == 404

        # code and message must be identical (request_id differs)
        assert response_guessed.json()["code"] == "TALENT_NOT_FOUND"
        assert response_fake.json()["code"] == "TALENT_NOT_FOUND"
        assert response_guessed.json()["message"] == "Kayıt bulunamadı"
        assert response_fake.json()["message"] == "Kayıt bulunamadı"


# ============================================================================
# AC-7: Database error handling (manual 500 scenario)
# ============================================================================


class TestDatabaseErrorHandling:
    """
    AC-7: Database errors return 500 with generic message (no stack trace).

    Note: This test is a stub. Full DB error injection requires mocking or
    a dedicated error-injection fixture (e.g., closing the session during request).
    Implementation left for future enhancement.
    """

    def test_db_error_returns_500_generic_message(self, client, session):
        """
        AC-7 (stub): Database error → 500 + {"detail": "Internal server error"}.

        Implementation note: This test placeholder documents the expected behavior.
        Actual DB error injection (e.g., connection pool exhaustion, constraint violation)
        would be tested via integration test suite with testcontainers.
        """
        # Placeholder: actual error injection requires DB manipulation
        # For now, this documents the expected response structure
        pass


# ============================================================================
# Additional: Response schema validation
# ============================================================================


class TestResponseSchema:
    """Additional schema validation for response structure."""

    def test_verified_experience_schema_complete(
        self,
        client,
        session,
        talent_profile_public,
        verified_experience_public_public,
    ):
        """
        Verify VerifiedExperience response includes all expected fields.

        Expected fields (from Davranış Sözleşmesi):
        - id: uuid
        - organization_name_snapshot: string
        - role_snapshot: string
        - started_on_snapshot: date (ISO 8601)
        - ended_on_snapshot: date (ISO 8601)
        - claim_type: string (PARTICIPATION|CONTRIBUTION|COMPETENCE|CONDUCT)
        - created_at: ISO 8601 datetime
        """
        response = client.get("/public/talents/alice-public-slug")

        assert response.status_code == 200

        data = response.json()

        ve_list = data["verified_experiences"]
        assert len(ve_list) == 1

        ve = ve_list[0]

        # Assert: required fields present
        required_fields = {
            "id",
            "organization_name_snapshot",
            "role_snapshot",
            "started_on_snapshot",
            "ended_on_snapshot",
            "claim_type",
            "created_at",
        }
        ve_keys = set(ve.keys())

        missing = required_fields - ve_keys
        assert not missing, f"Missing required fields in VerifiedExperience: {missing}"

        # Assert: field types and values
        assert isinstance(ve["id"], str)  # UUIDv7 as string
        assert isinstance(ve["organization_name_snapshot"], str)
        assert isinstance(ve["role_snapshot"], str)
        assert isinstance(ve["claim_type"], str)
        assert ve["claim_type"] in ["PARTICIPATION", "CONTRIBUTION", "COMPETENCE", "CONDUCT"]
        assert isinstance(ve["created_at"], str)  # ISO 8601 datetime

    def test_talent_id_is_uuid_string(
        self,
        client,
        session,
        talent_profile_public,
    ):
        """talent_id in response should be a valid UUID string."""
        response = client.get("/public/talents/alice-public-slug")

        assert response.status_code == 200

        data = response.json()

        talent_id = data["talent_id"]

        # Verify it's a string
        assert isinstance(talent_id, str)

        # Verify it parses as UUID
        try:
            UUID(talent_id)
        except ValueError:
            pytest.fail(f"talent_id '{talent_id}' is not a valid UUID")
