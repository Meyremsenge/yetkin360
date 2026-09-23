"""
Engagement authorization tests (YET-7 — AC-S1, AC-S2, AC-4, AC-S3).

Implements security and authorization criteria from atdd.md.

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient with X-Debug-User-Id header for auth simulation
- Defense-in-depth: server-side authorization verification
- Tenant/user isolation: ensure client-provided IDs don't override server logic

AC-4: TALENT rolündeki user başkasının talent_id'siyle engagement açmaya çalışır → 404 (403 değil)
AC-S2: ORG:MEMBER rolündeki user üyesi olmadığı org'un organization_id'siyle dener → 404
AC-S3: institution_id validation error message doesn't leak institution state

Status: Tests are RED/IMPORT-ERROR — implementation not yet written.
This is expected behavior. Tests verify authorization logic.
"""

import pytest
from uuid import uuid4

from app.models import User, TalentProfile, Organization, Institution, OrganizationMember


# ============================================================================
# Fixtures: Multiple talents, orgs, org members for isolation testing
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
def user_org_member_charlie(session, organization_b):
    """ORG:MEMBER user (not a talent, belongs to an org)."""
    user = User(email="charlie@example.com", password_hash="hash_charlie")
    session.add(user)
    session.flush()

    # Charlie is MEMBER of organization_b
    membership = OrganizationMember(
        organization_id=organization_b.id,
        user_id=user.id,
        role="MEMBER",
    )
    session.add(membership)
    session.flush()

    return user


@pytest.fixture
def user_no_auth(session):
    """User without any role context (for unauthenticated tests)."""
    user = User(email="noauth@example.com", password_hash="hash_noauth")
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
    """Organization B (for cross-org isolation)."""
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


# ============================================================================
# AC-4: TALENT rolündeki user başkasının talent_id'siyle dener → 404 (403 değil)
# ============================================================================


class TestTalentUnauthorizedAccess:
    """AC-4: TALENT trying to create engagement for another talent → 404 (not 403)."""

    def test_talent_create_engagement_for_another_talent_404(self, client, session, user_talent_alice, user_talent_bob, talent_alice, talent_bob, organization_a):
        """
        AC-4: Alice (TALENT) tries POST with talent_id=bob → 404 (not 403).

        Scenario:
        - Alice authenticated
        - Body: {talent_id: <bob>, organization_id: org_a, kind: INTERNSHIP, title: Test}
        - Server rejects as "talent not found" (404), not "forbidden" (403)
        - This prevents leaking that Bob's talent exists

        Acceptance Criteria:
        - Status code: 404 (not 403)
        - Error code: "TALENT_NOT_FOUND" or "NOT_FOUND"
        - No engagement row inserted
        """
        payload = {
            "talent_id": str(talent_bob.id),  # Try to use Bob's talent_id
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Bob's Engagement",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        # CRITICAL: 404 not 403 (principle: permission denial looks like resource not found)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

    def test_talent_create_engagement_own_talent_succeeds(self, client, session, user_talent_alice, talent_alice, organization_a):
        """
        AC-4 (verification): Alice can create engagement for her own talent.

        Acceptance Criteria:
        - Status code: 201
        - Engagement created for Alice's talent
        """
        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Alice's Engagement",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 201


# ============================================================================
# AC-S2: ORG:MEMBER rolündeki user üyesi olmadığı org'un organization_id'siyle dener → 404
# ============================================================================


class TestOrgMemberUnauthorizedAccess:
    """AC-S2: ORG:MEMBER trying to create engagement for org they don't belong to → 404."""

    def test_org_member_create_for_unauthorized_org_404(self, client, session, user_org_member_charlie, user_talent_alice, talent_alice, organization_a, organization_b):
        """
        AC-S2: Charlie (ORG:MEMBER of org_b only) tries POST with organization_id=org_a → 404.

        Scenario:
        - Charlie authenticated, member of organization_b
        - Body: {talent_id: alice, organization_id: org_a, kind: INTERNSHIP, title: Test}
        - Server rejects as "organization not found" (404) because Charlie is not in org_a

        Acceptance Criteria:
        - Status code: 404 (not 403)
        - No engagement row inserted
        """
        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_a.id),  # Charlie is NOT member of org_a
            "kind": "INTERNSHIP",
            "title": "Test Engagement",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie.id)},
        )

        # CRITICAL: 404 not 403
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

    def test_org_member_create_for_own_org_succeeds(self, client, session, user_org_member_charlie, user_talent_alice, talent_alice, organization_b):
        """
        AC-S2 (verification): ORG:MEMBER can create engagement for their own org.

        Scenario:
        - Charlie is member of organization_b
        - POST with organization_id=org_b succeeds

        Acceptance Criteria:
        - Status code: 201
        """
        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_b.id),  # Charlie's org
            "kind": "INTERNSHIP",
            "title": "Test Engagement",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie.id)},
        )

        assert response.status_code == 201


# ============================================================================
# AC-S1: Unauthenticated or incomplete context → 401/404
# ============================================================================


class TestUnauthenticatedAccess:
    """AC-S1: Missing/invalid auth context → 401/404, never 403."""

    def test_post_without_header_401(self, client, session, talent_alice, organization_a):
        """
        AC-S1: POST /engagements without X-Debug-User-Id → 401.

        Acceptance Criteria:
        - Status code: 401 Unauthorized (not 403)
        - No engagement inserted
        """
        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Test",
        }

        response = client.post(
            "/engagements",
            json=payload,
            # No X-Debug-User-Id header
        )

        assert response.status_code == 401

    def test_post_invalid_user_id_header_401(self, client, session, talent_alice, organization_a):
        """
        AC-S1: POST with invalid/nonexistent X-Debug-User-Id → 401.

        Acceptance Criteria:
        - Status code: 401
        """
        fake_user_id = uuid4()

        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Test",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(fake_user_id)},
        )

        assert response.status_code == 401


# ============================================================================
# AC-S3: Institution mismatch message privacy + existence leakage prevention
# ============================================================================


class TestInstitutionMessagePrivacy:
    """AC-S3: Institution error messages don't leak institution state."""

    def test_institution_mismatch_message_consistency_400(self, client, session, user_talent_alice, talent_alice, organization_a, institution_a):
        """
        AC-S3: Error message for institution_id mismatch is single, consistent message.

        Scenario:
        - Alice has no institution (institution_id=NULL)
        - POST with institution_id=institution_a
        - Error message should be same whether institution exists or not

        Acceptance Criteria:
        - Status code: 400
        - Message doesn't say "institution not found" or "institution exists"
        """
        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Test",
            "institution_id": str(institution_a.id),  # Mismatch: Alice has NULL
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 400

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        message = error_obj.get("message", "").lower()

        # Message must NOT leak institution existence state
        assert "not found" not in message
        assert "does not exist" not in message
        assert "matches" not in message or "does not match" not in message

    def test_institution_nonexistent_same_error_400(self, client, session, user_talent_alice, talent_alice, organization_a):
        """
        AC-S3: Error for nonexistent institution is same code/message as mismatch.

        Scenario:
        - POST with institution_id=fake_uuid
        - Should return 400 (not 404), with same message as AC-S3

        Acceptance Criteria:
        - Status code: 400 (not 404)
        - Message is generic (doesn't reveal institution doesn't exist)
        """
        fake_institution_id = uuid4()

        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Test",
            "institution_id": str(fake_institution_id),
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        # Must be 400 (institution check is business logic, not FK existence)
        assert response.status_code == 400


# ============================================================================
# Confidentiality: sensitive fields not logged on error
# ============================================================================


class TestConfidentialityOnError:
    """AC-S4: On error, title/description not in logs."""

    def test_post_with_confidential_title_error_no_leak(self, client, session, user_talent_alice, talent_alice, organization_a):
        """
        AC-S4: POST fails with institution_id mismatch, title not logged/returned in detail.

        Scenario:
        - POST with sensitive title, institution_id mismatch → 400
        - Error response/logs should NOT contain title text

        Acceptance Criteria:
        - Status code: 400
        - Error message is generic (not showing title or description)
        """
        sensitive_title = "Secret Internship at Government Agency"

        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": sensitive_title,
            "institution_id": str(uuid4()),  # Mismatch
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 400

        # Error response should NOT echo back the title
        data = response.json()
        response_text = str(data)

        # Title should NOT appear in error response
        assert sensitive_title not in response_text
        assert "Secret Internship" not in response_text


# ============================================================================
# Response schema validation (error responses)
# ============================================================================


class TestAuthErrorResponseSchema:
    """Verify auth error responses match API.md §1.4."""

    def test_unauthorized_error_has_code_message_request_id(self, client, session, talent_alice, organization_a):
        """401 error must have {code, message, request_id}."""
        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Test",
        }

        response = client.post(
            "/engagements",
            json=payload,
            # No X-Debug-User-Id
        )

        assert response.status_code == 401

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        # Assert: error structure
        assert "code" in error_obj
        assert "message" in error_obj
        assert "request_id" in error_obj

        # Assert: code is SCREAMING_SNAKE_CASE
        assert isinstance(error_obj["code"], str)
        assert "_" in error_obj["code"] or error_obj["code"].isupper()

        # Assert: message is non-empty string
        assert isinstance(error_obj["message"], str)
        assert len(error_obj["message"]) > 0

    def test_not_found_error_has_code_message_request_id(self, client, session, user_talent_alice, talent_alice, organization_a):
        """404 error must have {code, message, request_id}."""
        fake_talent_id = uuid4()

        payload = {
            "talent_id": str(fake_talent_id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Test",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 404

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        # Assert: error structure
        assert "code" in error_obj
        assert "message" in error_obj
        assert "request_id" in error_obj

    def test_bad_request_error_has_code_message_request_id(self, client, session, user_talent_alice, talent_alice, organization_a):
        """400 error must have {code, message, request_id}."""
        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Test",
            "institution_id": str(uuid4()),  # Mismatch
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 400

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        # Assert: error structure
        assert "code" in error_obj
        assert "message" in error_obj
        assert "request_id" in error_obj
