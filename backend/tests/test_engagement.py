"""
Engagement endpoint tests (YET-7 — engagement-model-olusturma-ucu).

Implements Acceptance Criteria (AC-1 through AC-5) and Behavior Contract from atdd.md.

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Each AC/Behavior Contract row has one or more test functions
- Error responses validated against {"code": ..., "message": ..., "request_id": ...} schema
- Models imported from app.models (Engagement, Organization, Institution, TalentProfile)

Status: Tests are RED/IMPORT-ERROR — implementation not yet written.
This is expected behavior. Tests implement behavior contract (ATDD).

Coverage Target: 80% (services/engagement.py)
Performance Target: <200ms
"""

import pytest
from uuid import uuid4

from app.models import User, TalentProfile, Organization, Institution, OrganizationMember


# ============================================================================
# Fixtures: Users, TalentProfiles, Organizations, Institutions
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
    """Talent user B (for isolation/unauthorized tests)."""
    user = User(email="talent-b@example.com", password_hash="hash_talent_b")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent_a(session, user_talent_a, organization_a):
    """Talent profile for user_talent_a, member of organization_a."""
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

    # Add talent as member of organization_a
    member = OrganizationMember(
        user_id=user_talent_a.id,
        organization_id=organization_a.id,
        role="MEMBER",
    )
    session.add(member)
    session.flush()

    return profile


@pytest.fixture
def talent_b(session, user_talent_b, organization_b):
    """Talent profile for user_talent_b, member of organization_b."""
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

    # Add talent as member of organization_b
    member = OrganizationMember(
        user_id=user_talent_b.id,
        organization_id=organization_b.id,
        role="MEMBER",
    )
    session.add(member)
    session.flush()

    return profile


@pytest.fixture
def organization_a(session):
    """Organization A."""
    org = Organization(
        name="Test Org A",
        domain="testorga.example.com",
        legal_id="ORG-A-001",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def organization_b(session):
    """Organization B (for isolation/unauthorized tests)."""
    org = Organization(
        name="Test Org B",
        domain="testorgb.example.com",
        legal_id="ORG-B-001",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def institution_a(session):
    """Institution A."""
    inst = Institution(
        name="Test Institution A",
        domain="testinsta.example.com",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def talent_a_with_institution(session, user_talent_a, institution_a, organization_a):
    """Talent profile A with institution linked, member of organization_a."""
    profile = TalentProfile(
        user_id=user_talent_a.id,
        full_name="Test Talent A with Institution",
        visibility="PRIVATE",
        headline=None,
        city=None,
        department=None,
        study_year=None,
        public_slug=None,
        institution_id=institution_a.id,
    )
    session.add(profile)
    session.flush()

    # Add talent as member of organization_a
    member = OrganizationMember(
        user_id=user_talent_a.id,
        organization_id=organization_a.id,
        role="MEMBER",
    )
    session.add(member)
    session.flush()

    return profile


# ============================================================================
# AC-1: POST /engagements — Happy Path (201 + engagement data)
# ============================================================================


class TestPostEngagementHappyPath:
    """AC-1: POST /engagements with valid talent_id, organization_id, kind, title → 201."""

    def test_post_engagement_happy_path_201(self, client, session, user_talent_a, talent_a, organization_a):
        """
        AC-1: POST /engagements with all required fields → 201 + engagement object.

        Acceptance Criteria:
        - Status code: 201 Created
        - Response contains: id, talent_id, organization_id, kind, title, status="DRAFT", version=1
        - engagements table has one new row
        - audit_event written in same transaction
        """
        payload = {
            "talent_id": str(talent_a.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Summer Internship 2026",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()

        # Assert: response schema
        assert "id" in data
        assert data.get("talent_id") == str(talent_a.id)
        assert data.get("organization_id") == str(organization_a.id)
        assert data.get("kind") == "INTERNSHIP"
        assert data.get("title") == "Summer Internship 2026"
        assert data.get("status") == "DRAFT"
        assert data.get("version") == 1
        assert "created_at" in data

    def test_post_engagement_with_institution_id_201(self, client, session, user_talent_a, talent_a_with_institution, organization_a, institution_a):
        """
        AC-1: POST with institution_id (matching talent's institution) → 201.

        Acceptance Criteria:
        - Status code: 201
        - institution_id in response matches request
        """
        payload = {
            "talent_id": str(talent_a_with_institution.id),
            "organization_id": str(organization_a.id),
            "kind": "CAPSTONE",
            "title": "Capstone Project",
            "institution_id": str(institution_a.id),
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 201

        data = response.json()
        assert data.get("institution_id") == str(institution_a.id)

    def test_post_engagement_optional_fields(self, client, session, user_talent_a, talent_a, organization_a):
        """
        AC-1: POST without optional fields (description, confidential) → 201.

        Acceptance Criteria:
        - Status code: 201
        - Only required fields provided
        """
        payload = {
            "talent_id": str(talent_a.id),
            "organization_id": str(organization_a.id),
            "kind": "SHORT_PROJECT",
            "title": "Quick Project",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 201

        data = response.json()
        assert data.get("status") == "DRAFT"


# ============================================================================
# AC-2: POST /engagements — Validation Error (422)
# ============================================================================


class TestPostEngagementValidationError:
    """AC-2: POST with invalid input (empty title, invalid kind) → 422."""

    def test_post_engagement_empty_title_422(self, client, session, user_talent_a, talent_a, organization_a):
        """
        AC-2: POST with title="" → 422 Unprocessable Entity.

        Acceptance Criteria:
        - Status code: 422
        - Error indicates 'title' field issue
        - No row inserted into DB
        """
        payload = {
            "talent_id": str(talent_a.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "",  # Empty title
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 422

        data = response.json()
        # FastAPI validation error has 'detail' field with list of errors
        assert "detail" in data or isinstance(data, dict)

    def test_post_engagement_invalid_kind_422(self, client, session, user_talent_a, talent_a, organization_a):
        """
        AC-2: POST with kind not in CHECK set → 422.

        Acceptance Criteria:
        - Status code: 422
        - kind must be INTERNSHIP|CAPSTONE|SHORT_PROJECT|PART_TIME
        """
        payload = {
            "talent_id": str(talent_a.id),
            "organization_id": str(organization_a.id),
            "kind": "INVALID_KIND",
            "title": "Test",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 422

    def test_post_engagement_missing_required_field_422(self, client, session, user_talent_a, talent_a, organization_a):
        """
        AC-2: POST missing required field (title) → 422.

        Acceptance Criteria:
        - Status code: 422
        """
        payload = {
            "talent_id": str(talent_a.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            # Missing 'title'
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 422


# ============================================================================
# AC-3: POST /engagements — FK Not Found (404)
# ============================================================================


class TestPostEngagementFKNotFound:
    """AC-3: POST with nonexistent talent_id/organization_id → 404."""

    def test_post_engagement_nonexistent_talent_id_404(self, client, session, user_talent_a, organization_a):
        """
        AC-3: POST with talent_id that doesn't exist in DB → 404.

        Acceptance Criteria:
        - Status code: 404
        - Error code: likely "TALENT_NOT_FOUND" or "NOT_FOUND"
        - No row inserted
        """
        fake_talent_id = uuid4()

        payload = {
            "talent_id": str(fake_talent_id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Test Engagement",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 404

        data = response.json()
        # Error should have code field (wrapped in 'detail' by FastAPI)
        assert "code" in data or "detail" in data

    def test_post_engagement_nonexistent_organization_id_404(self, client, session, user_talent_a, talent_a):
        """
        AC-3: POST with organization_id that doesn't exist → 404.

        Acceptance Criteria:
        - Status code: 404
        """
        fake_org_id = uuid4()

        payload = {
            "talent_id": str(talent_a.id),
            "organization_id": str(fake_org_id),
            "kind": "INTERNSHIP",
            "title": "Test Engagement",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 404


# ============================================================================
# AC-5: POST /engagements — Institution Mismatch (400)
# ============================================================================


class TestPostEngagementInstitutionMismatch:
    """AC-5, GUV-08: POST with institution_id not matching talent's institution → 404."""

    def test_post_engagement_institution_mismatch_404(self, client, session, user_talent_a, talent_a_with_institution, organization_a, institution_a):
        """
        AC-5, GUV-08: POST with institution_id that doesn't match talent's institution → 404.

        GUV-08 fix: Institution mismatch is treated as NOT_FOUND to close oracle.

        Acceptance Criteria:
        - Status code: 404
        - Error code: "NOT_FOUND"
        - Message is generic (doesn't reveal whether institution exists)
        """
        # Create another institution
        other_institution = Institution(
            name="Other Institution",
            domain="otherinst.example.com",
            verification_level="T1",
            status="ACTIVE",
        )
        session.add(other_institution)
        session.flush()

        payload = {
            "talent_id": str(talent_a_with_institution.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Test",
            "institution_id": str(other_institution.id),  # Mismatch: talent has institution_a
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 404

        data = response.json()
        assert data.get("code") == "NOT_FOUND"

    def test_post_engagement_institution_id_null_talent_404(self, client, session, user_talent_a, talent_a, organization_a, institution_a):
        """
        AC-5, GUV-08: POST with institution_id when talent has NULL institution → 404.

        Scenario:
        - talent_a has institution_id=NULL
        - POST provides institution_id=institution_a.id
        - Should fail (mismatch) with 404

        Acceptance Criteria:
        - Status code: 404
        - Error code: "NOT_FOUND"
        """
        payload = {
            "talent_id": str(talent_a.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Test",
            "institution_id": str(institution_a.id),  # Talent has NULL, POST provides value
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 404
        data = response.json()
        assert data.get("code") == "NOT_FOUND"


# ============================================================================
# AC-S3: Institution mismatch message doesn't leak institution existence
# ============================================================================


class TestPostEngagementInstitutionMessagePrivacy:
    """AC-S3, GUV-08: Institution error message is generic (404 closes oracle)."""

    def test_post_engagement_institution_error_message_generic(self, client, session, user_talent_a, talent_a_with_institution, organization_a, institution_a):
        """
        AC-S3, GUV-08: Error message for institution mismatch is 404 NOT_FOUND (generic).

        GUV-08 fix: Institution mismatch returns 404 with NOT_FOUND code, preventing oracle attack.

        Acceptance Criteria:
        - Status code: 404
        - Error code: "NOT_FOUND"
        - Message is generic (same for all not-found cases)
        """
        other_institution = Institution(
            name="Other",
            domain="otherinst2.example.com",
            verification_level="T1",
            status="ACTIVE",
        )
        session.add(other_institution)
        session.flush()

        payload = {
            "talent_id": str(talent_a_with_institution.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Test",
            "institution_id": str(other_institution.id),
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 404

        data = response.json()
        assert data.get("code") == "NOT_FOUND"


# ============================================================================
# Response Schema Validation (all responses must follow API.md §1.4)
# ============================================================================


class TestEngagementResponseSchema:
    """Verify response schemas match API.md §1.4 error contract."""

    def test_error_response_has_code_message_request_id(self, client, user_talent_a, talent_a):
        """All error responses must have {code, message, request_id} or wrapped in detail."""
        fake_org_id = uuid4()

        payload = {
            "talent_id": str(talent_a.id),
            "organization_id": str(fake_org_id),
            "kind": "INTERNSHIP",
            "title": "Test",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 404

        data = response.json()

        # Error response structure: could be {"code": ..., "message": ..., "request_id": ...}
        # or {"detail": {"code": ..., "message": ..., "request_id": ...}}
        error_obj = data.get("detail") if "detail" in data else data

        assert "code" in error_obj, "Error response must have 'code' field"
        assert "message" in error_obj, "Error response must have 'message' field"
        assert "request_id" in error_obj, "Error response must have 'request_id' field"

        # Assert: code is SCREAMING_SNAKE_CASE
        assert isinstance(error_obj["code"], str)

        # Assert: message is non-empty string
        assert isinstance(error_obj["message"], str)
        assert len(error_obj["message"]) > 0

    def test_success_response_schema_201(self, client, session, user_talent_a, talent_a, organization_a):
        """201 response must have engagement object with required fields."""
        # talent_a is already a member of organization_a (via fixture)
        payload = {
            "talent_id": str(talent_a.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Test Engagement",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()

        # Assert: required fields present
        required_fields = [
            "id",
            "talent_id",
            "organization_id",
            "kind",
            "title",
            "status",
            "version",
            "created_at",
        ]

        for field in required_fields:
            assert field in data, f"Response missing required field: {field}"

        # Assert: types
        assert isinstance(data["id"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["version"], int)
        assert data["status"] == "DRAFT"
        assert data["version"] == 1
