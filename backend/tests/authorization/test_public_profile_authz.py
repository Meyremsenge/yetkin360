"""
Public profile authorization and enumeration tests (YET-105, YET-123 — AC-S1/S2/S3).

Implements security matrix from atdd.md:
- Test IDOR/enumeration protection for GET /public/talents/{slug}
- Verify PII/internal field filtering (AC-S2)
- Verify VerifiedExperience visibility filtering (AC-S3)

Critical security focus:
1. Enumeration protection: 404 responses must be byte-byte identical
   across all non-PUBLIC scenarios (nonexistent, PRIVATE, INSTITUTION, ORGANIZATIONS)
2. PII protection: response must NOT contain email, user_id, institution_id, etc.
3. Granular visibility: visibility='PRIVATE' VerifiedExperience must be filtered

Mock usage: NONE — real PostgreSQL transactions, real HTTP requests via TestClient.

This test file specifically covers the "Güvenlik Test Matrisi" (Security Test Matrix)
rows 1-7 from atdd.md, with extra emphasis on row 1-4 byte-level comparison.

Status: Tests are RED/IMPORT-ERROR — implementation not yet written.
"""

from datetime import date

import pytest

from app.models import (
    Engagement,
    Organization,
    TalentProfile,
    User,
    VerifiedExperience,
)


# ============================================================================
# Fixtures: Same as test_public_profile.py (reusable across authorization suite)
# ============================================================================


@pytest.fixture
def user_public(session):
    """User with PUBLIC talent profile."""
    user = User(email="authz-public@example.com", password_hash="hash_authz_public")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_private(session):
    """User with PRIVATE talent profile."""
    user = User(email="authz-private@example.com", password_hash="hash_authz_private")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_institution(session):
    """User with INSTITUTION visibility talent profile."""
    user = User(email="authz-institution@example.com", password_hash="hash_authz_institution")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_organizations(session):
    """User with ORGANIZATIONS visibility talent profile."""
    user = User(email="authz-organizations@example.com", password_hash="hash_authz_organizations")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def org_authz(session):
    """Test organization for engagement FK."""
    org = Organization(name="Authz Test Org", verification_level="T2", status="ACTIVE")
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def profile_public(session, user_public):
    """Public talent profile with slug."""
    profile = TalentProfile(
        user_id=user_public.id,
        full_name="Public Talent Authz",
        headline="Engineer",
        visibility="PUBLIC",
        public_slug="authz-public-slug",
        city=None,
        department=None,
        study_year=None,
        deleted_at=None,
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def profile_private(session, user_private):
    """Private talent profile with slug."""
    profile = TalentProfile(
        user_id=user_private.id,
        full_name="Private Talent Authz",
        headline=None,
        visibility="PRIVATE",
        public_slug="authz-private-slug",
        city=None,
        department=None,
        study_year=None,
        deleted_at=None,
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def profile_institution(session, user_institution):
    """Institution visibility talent profile with slug."""
    profile = TalentProfile(
        user_id=user_institution.id,
        full_name="Institution Talent Authz",
        headline=None,
        visibility="INSTITUTION",
        public_slug="authz-institution-slug",
        city=None,
        department=None,
        study_year=None,
        deleted_at=None,
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def profile_organizations(session, user_organizations):
    """Organizations visibility talent profile with slug."""
    profile = TalentProfile(
        user_id=user_organizations.id,
        full_name="Organizations Talent Authz",
        headline=None,
        visibility="ORGANIZATIONS",
        public_slug="authz-organizations-slug",
        city=None,
        department=None,
        study_year=None,
        deleted_at=None,
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def engagement_public(session, profile_public, org_authz):
    """Engagement for public talent."""
    eng = Engagement(
        talent_id=profile_public.id,
        organization_id=org_authz.id,
        kind="INTERNSHIP",
        title="Authz Test Internship",
        status="VERIFIED",
        started_on=date(2025, 1, 1),
        ended_on=date(2025, 6, 30),
        confidential=False,
    )
    session.add(eng)
    session.flush()
    return eng


@pytest.fixture
def ve_public_public(session, profile_public, engagement_public):
    """VerifiedExperience: PUBLIC talent, PUBLIC visibility."""
    ve = VerifiedExperience(
        talent_id=profile_public.id,
        engagement_id=engagement_public.id,
        organization_name_snapshot="Authz Test Org",
        role_snapshot="Authz Test Role",
        started_on_snapshot=date(2025, 1, 1),
        ended_on_snapshot=date(2025, 6, 30),
        institution_name_snapshot=None,
        claim_type="COMPETENCE",
        visibility="PUBLIC",
    )
    session.add(ve)
    session.flush()
    return ve


@pytest.fixture
def ve_public_private(session, profile_public, engagement_public):
    """VerifiedExperience: PUBLIC talent, PRIVATE visibility (should be filtered)."""
    ve = VerifiedExperience(
        talent_id=profile_public.id,
        engagement_id=engagement_public.id,
        organization_name_snapshot="Secret Org",
        role_snapshot="Secret Role",
        started_on_snapshot=date(2025, 7, 1),
        ended_on_snapshot=date(2025, 12, 31),
        institution_name_snapshot=None,
        claim_type="PARTICIPATION",
        visibility="PRIVATE",
    )
    session.add(ve)
    session.flush()
    return ve


# ============================================================================
# Güvenlik Test Matrisi — Row 1: Nonexistent slug → 404
# ============================================================================


class TestSecurityMatrixRow1Nonexistent:
    """
    Security Matrix Row 1: Nonexistent slug → 404 + {"detail": "Not found"}.

    This is the baseline for enumeration comparison.
    """

    def test_nonexistent_slug_404(self, client):
        """Nonexistent slug returns 404 with generic message."""
        response = client.get("/public/talents/this-slug-definitely-does-not-exist")

        assert response.status_code == 404

        data = response.json()

        assert data["code"] == "TALENT_NOT_FOUND"
        assert data["message"] == "Kayıt bulunamadı"
        assert "request_id" in data

    def test_nonexistent_404_structure(self, client):
        """404 response structure matches expected format."""
        response = client.get("/public/talents/fake-12345-fake")

        assert response.status_code == 404

        # Content-Type header should indicate JSON
        assert "application/json" in response.headers.get("content-type", "").lower()

        # Body should parse as JSON
        data = response.json()

        # Must be a dict with ApiError wrapper fields
        assert isinstance(data, dict)
        assert "code" in data
        assert "message" in data
        assert "request_id" in data
        assert data["code"] == "TALENT_NOT_FOUND"
        assert data["message"] == "Kayıt bulunamadı"


# ============================================================================
# Güvenlik Test Matrisi — Row 2-4: PRIVATE/INSTITUTION/ORGANIZATIONS → 404 (identical to row 1)
# ============================================================================


class TestSecurityMatrixRow2Enumeration:
    """
    Security Matrix Row 2: PRIVATE talent's 404 must be IDENTICAL to nonexistent's.

    This is THE CRITICAL security test for enumeration protection.
    """

    def test_private_talent_404_identical_to_nonexistent(
        self,
        client,
        session,
        profile_private,
    ):
        """
        CRITICAL: 404 for existing PRIVATE talent must have identical code/message to nonexistent.

        Failure means attacker can enumerate talent existence.
        """
        response_nonexistent = client.get("/public/talents/fake-nonexistent-slug")
        response_private = client.get("/public/talents/authz-private-slug")

        # Status codes
        assert response_nonexistent.status_code == 404
        assert response_private.status_code == 404

        # CRITICAL: code and message must be identical (request_id differs)
        assert response_nonexistent.json()["code"] == "TALENT_NOT_FOUND"
        assert response_private.json()["code"] == "TALENT_NOT_FOUND"
        assert response_nonexistent.json()["message"] == "Kayıt bulunamadı"
        assert response_private.json()["message"] == "Kayıt bulunamadı"


class TestSecurityMatrixRow3Enumeration:
    """
    Security Matrix Row 3: INSTITUTION talent's 404 must be IDENTICAL to nonexistent's.
    """

    def test_institution_talent_404_identical_to_nonexistent(
        self,
        client,
        session,
        profile_institution,
    ):
        """
        CRITICAL: 404 for existing INSTITUTION talent must have identical code/message to nonexistent.
        """
        response_nonexistent = client.get("/public/talents/fake-nonexistent-xyz")
        response_institution = client.get("/public/talents/authz-institution-slug")

        # Status codes
        assert response_nonexistent.status_code == 404
        assert response_institution.status_code == 404

        # CRITICAL: code and message must be identical (request_id differs)
        assert response_nonexistent.json()["code"] == "TALENT_NOT_FOUND"
        assert response_institution.json()["code"] == "TALENT_NOT_FOUND"
        assert response_nonexistent.json()["message"] == "Kayıt bulunamadı"
        assert response_institution.json()["message"] == "Kayıt bulunamadı"


class TestSecurityMatrixRow4Enumeration:
    """
    Security Matrix Row 4: ORGANIZATIONS talent's 404 must be IDENTICAL to nonexistent's.
    """

    def test_organizations_talent_404_identical_to_nonexistent(
        self,
        client,
        session,
        profile_organizations,
    ):
        """
        CRITICAL: 404 for existing ORGANIZATIONS talent must have identical code/message to nonexistent.
        """
        response_nonexistent = client.get("/public/talents/fake-nonexistent-abc")
        response_organizations = client.get("/public/talents/authz-organizations-slug")

        # Status codes
        assert response_nonexistent.status_code == 404
        assert response_organizations.status_code == 404

        # CRITICAL: code and message must be identical (request_id differs)
        assert response_nonexistent.json()["code"] == "TALENT_NOT_FOUND"
        assert response_organizations.json()["code"] == "TALENT_NOT_FOUND"
        assert response_nonexistent.json()["message"] == "Kayıt bulunamadı"
        assert response_organizations.json()["message"] == "Kayıt bulunamadı"


class TestSecurityMatrixRows1to4AllIdentical:
    """
    MOST CRITICAL TEST: All four rows (nonexistent, PRIVATE, INSTITUTION, ORGANIZATIONS)
    return IDENTICAL 404 responses.

    This is the defense against enumeration attacks.
    """

    def test_all_404_responses_byte_identical(
        self,
        client,
        session,
        profile_private,
        profile_institution,
        profile_organizations,
    ):
        """
        ALL four scenarios must return IDENTICAL response (including byte-level).

        This test is the highest priority for security.
        """
        # Four requests: nonexistent + three non-PUBLIC visibility levels
        resp_nonexistent = client.get("/public/talents/completely-fake-slug-000")
        resp_private = client.get("/public/talents/authz-private-slug")
        resp_institution = client.get("/public/talents/authz-institution-slug")
        resp_organizations = client.get("/public/talents/authz-organizations-slug")

        # All status codes must be 404
        assert resp_nonexistent.status_code == 404
        assert resp_private.status_code == 404
        assert resp_institution.status_code == 404
        assert resp_organizations.status_code == 404

        # All code fields must be identical
        expected_code = "TALENT_NOT_FOUND"
        assert resp_nonexistent.json()["code"] == expected_code
        assert resp_private.json()["code"] == expected_code
        assert resp_institution.json()["code"] == expected_code
        assert resp_organizations.json()["code"] == expected_code

        # All message fields must be identical
        expected_message = "Kayıt bulunamadı"
        assert resp_nonexistent.json()["message"] == expected_message
        assert resp_private.json()["message"] == expected_message
        assert resp_institution.json()["message"] == expected_message
        assert resp_organizations.json()["message"] == expected_message


# ============================================================================
# Güvenlik Test Matrisi — Row 5: PUBLIC talent → 200 (AC-S2, AC-S3)
# ============================================================================


class TestSecurityMatrixRow5PublicTalent:
    """
    Security Matrix Row 5: PUBLIC talent returns 200 with proper filtering.

    AC-S2: No PII/internal fields (AC-4)
    AC-S3: Only PUBLIC visibility experiences (AC-5)
    """

    def test_public_talent_200_with_data(self, client, session, profile_public, ve_public_public):
        """PUBLIC talent returns 200 with complete data."""
        response = client.get("/public/talents/authz-public-slug")

        assert response.status_code == 200

        data = response.json()

        assert "talent_id" not in data
        assert "display_name" in data
        assert "verified_experiences" in data

        # YET-230: internal talent UUID is not exposed
        assert str(profile_public.id) not in response.text
        assert data["display_name"] == "Public Talent Authz"

    def test_public_talent_no_pii_fields_ac_s2(
        self,
        client,
        session,
        profile_public,
        ve_public_public,
    ):
        """
        AC-S2: PUBLIC talent response must NOT contain PII/internal fields.

        Prohibited fields: email, user_id, password_hash, institution_id, etc.
        """
        response = client.get("/public/talents/authz-public-slug")

        assert response.status_code == 200

        data = response.json()

        # Response keys should be ONLY: display_name, verified_experiences
        response_keys = set(data.keys())
        expected_keys = {"display_name", "verified_experiences"}

        assert response_keys == expected_keys, (
            f"AC-S2 VIOLATION: Unexpected keys in response. "
            f"Expected {expected_keys}, got {response_keys}. "
            f"This indicates PII or internal field leakage."
        )

        # Verify no PII in the response at all
        response_str = str(data)

        # Check for specific PII patterns
        pii_patterns = [
            ("email", "email field leaked"),
            ("password_hash", "password_hash field leaked"),
            ("institution_id", "institution_id field leaked"),
            ("user_id", "user_id field leaked"),
            ("@example.com", "email address leaked"),
        ]

        for pattern, msg in pii_patterns:
            assert pattern not in response_str, f"AC-S2 VIOLATION: {msg} in response: {response_str}"

    def test_public_talent_no_private_experiences_ac_s3(
        self,
        client,
        session,
        profile_public,
        ve_public_public,
        ve_public_private,
    ):
        """
        AC-S3: PUBLIC talent with mixed-visibility experiences → only PUBLIC experiences returned.

        Scenario:
        - Talent has 2 VerifiedExperience records:
          1. visibility='PUBLIC' (organization_name_snapshot="Authz Test Org")
          2. visibility='PRIVATE' (organization_name_snapshot="Secret Org")
        - Response must contain ONLY the PUBLIC one

        Acceptance Criteria:
        - verified_experiences list length == 1
        - The entry is the PUBLIC one
        - "Secret Org" does NOT appear in response
        """
        response = client.get("/public/talents/authz-public-slug")

        assert response.status_code == 200

        data = response.json()

        ve_list = data["verified_experiences"]

        # Must have exactly 1 experience
        assert len(ve_list) == 1, (
            f"AC-S3 VIOLATION: Expected 1 PUBLIC experience, got {len(ve_list)}. "
            f"PRIVATE experiences should be filtered."
        )

        # The single experience must be the PUBLIC one
        ve = ve_list[0]
        assert ve["organization_name_snapshot"] == "Authz Test Org", (
            f"AC-S3 VIOLATION: Got '{ve['organization_name_snapshot']}' instead of public experience."
        )

        # Verify the PRIVATE experience is NOT in response
        response_str = str(data)
        assert "Secret Org" not in response_str, (
            "AC-S3 VIOLATION: PRIVATE VerifiedExperience leaked in response (organization_name_snapshot='Secret Org')"
        )
        assert "Secret Role" not in response_str, (
            "AC-S3 VIOLATION: PRIVATE VerifiedExperience leaked in response (role_snapshot='Secret Role')"
        )

    def test_public_talent_no_attestations_skill_signals(
        self,
        client,
        session,
        profile_public,
        ve_public_public,
    ):
        """
        AC-4 note: Response must NOT contain 'attestations' or 'skill_signals' fields.

        (Per atdd.md Kapsam Dışı: attestations/skill_signals public response'ta yok)
        """
        response = client.get("/public/talents/authz-public-slug")

        assert response.status_code == 200

        data = response.json()

        # These fields must NOT exist
        assert "attestations" not in data, "attestations field should not be in public response"
        assert "skill_signals" not in data, "skill_signals field should not be in public response"

        # Also check in verified_experiences list
        for ve in data.get("verified_experiences", []):
            assert "attestations" not in ve
            assert "skill_signals" not in ve


# ============================================================================
# Güvenlik Test Matrisi — Row 6: Mixed visibility experiences
# ============================================================================


class TestSecurityMatrixRow6MixedVisibility:
    """
    Security Matrix Row 6: PUBLIC talent with PRIVATE/INSTITUTION/ORGANIZATIONS experiences
    must filter all non-PUBLIC ones.
    """

    def test_institution_visibility_experience_filtered(
        self,
        client,
        session,
        profile_public,
        engagement_public,
    ):
        """INSTITUTION-visibility experience must be filtered from PUBLIC talent response."""
        ve_institution = VerifiedExperience(
            talent_id=profile_public.id,
            engagement_id=engagement_public.id,
            organization_name_snapshot="Institution Only Org",
            role_snapshot="Institution Role",
            started_on_snapshot=date(2025, 1, 1),
            ended_on_snapshot=date(2025, 6, 30),
            institution_name_snapshot=None,
            claim_type="COMPETENCE",
            visibility="INSTITUTION",
        )
        session.add(ve_institution)
        session.commit()

        response = client.get("/public/talents/authz-public-slug")

        assert response.status_code == 200

        data = response.json()

        # Must have 0 experiences (no PUBLIC ones, only INSTITUTION)
        assert len(data["verified_experiences"]) == 0

        # Verify INSTITUTION experience is not in response
        assert "Institution Only Org" not in str(data)

    def test_organizations_visibility_experience_filtered(
        self,
        client,
        session,
        profile_public,
        engagement_public,
    ):
        """ORGANIZATIONS-visibility experience must be filtered from PUBLIC talent response."""
        ve_organizations = VerifiedExperience(
            talent_id=profile_public.id,
            engagement_id=engagement_public.id,
            organization_name_snapshot="Organizations Only Org",
            role_snapshot="Organizations Role",
            started_on_snapshot=date(2025, 1, 1),
            ended_on_snapshot=date(2025, 6, 30),
            institution_name_snapshot=None,
            claim_type="COMPETENCE",
            visibility="ORGANIZATIONS",
        )
        session.add(ve_organizations)
        session.commit()

        response = client.get("/public/talents/authz-public-slug")

        assert response.status_code == 200

        data = response.json()

        # Must have 0 experiences
        assert len(data["verified_experiences"]) == 0

        # Verify ORGANIZATIONS experience is not in response
        assert "Organizations Only Org" not in str(data)


# ============================================================================
# Güvenlik Test Matrisi — Row 7: NULL public_slug
# ============================================================================


class TestSecurityMatrixRow7NullSlug:
    """
    Security Matrix Row 7: NULL public_slug (even if visibility='PUBLIC')
    should return 404 identical to nonexistent.
    """

    def test_null_slug_404_identical_to_nonexistent(
        self,
        client,
        session,
        user_public,
    ):
        """
        NULL public_slug talent should return 404 identical to nonexistent.

        Scenario:
        - Create PUBLIC talent but with public_slug=NULL
        - Attempt to access via any slug
        - Expected: 404 identical to nonexistent case
        """
        profile_null_slug = TalentProfile(
            user_id=user_public.id,
            full_name="Null Slug Public",
            visibility="PUBLIC",
            public_slug=None,  # Explicitly NULL
            headline=None,
            city=None,
            department=None,
            study_year=None,
            deleted_at=None,
        )
        session.add(profile_null_slug)
        session.flush()

        # Try to guess the slug
        response_guessed = client.get("/public/talents/null-slug-public")
        response_fake = client.get("/public/talents/fake-slug-zzz")

        # Both must be 404
        assert response_guessed.status_code == 404
        assert response_fake.status_code == 404

        # code and message must be identical (request_id differs)
        assert response_guessed.json()["code"] == "TALENT_NOT_FOUND"
        assert response_fake.json()["code"] == "TALENT_NOT_FOUND"
        assert response_guessed.json()["message"] == "Kayıt bulunamadı"
        assert response_fake.json()["message"] == "Kayıt bulunamadı"


# ============================================================================
# Additional: Auth-free endpoint verification
# ============================================================================


class TestAuthFreeAccess:
    """
    Verify that the endpoint is truly auth-free (no X-Debug-User-Id header required).
    """

    def test_public_profile_no_auth_header_required(self, client, session, profile_public, ve_public_public):
        """PUBLIC profile must be accessible WITHOUT X-Debug-User-Id header."""
        # Make request without any auth header
        response = client.get("/public/talents/authz-public-slug")

        # Should succeed (not 401)
        assert response.status_code == 200

    def test_404_accessible_without_auth_header(self, client):
        """404 response must not require authentication."""
        # Request nonexistent slug without auth header
        response = client.get("/public/talents/nonexistent-no-auth")

        # Should return 404, not 401
        assert response.status_code == 404
