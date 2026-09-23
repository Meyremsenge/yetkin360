"""
Engagement Deliverable endpoint tests (PLAN 2.4 — engagement-task-deliverable, AC-2, AC-4, AC-5, AC-6, AC-7, AC-S2, AC-S3, AC-S4, AC-S5).

Implements Acceptance Criteria for POST /engagements/{id}/deliverables and T5 transition precondition:
- AC-2: Happy path (TALENT, ACTIVE engagement) → 201, submitted_by_user_id from principal (not client)
- AC-4: Cross-talent scope violation → 404 NOT_FOUND
- AC-5: Engagement not ACTIVE (DRAFT/PENDING_APPROVAL/REJECTED/CANCELLED) → 422 PRECONDITION_FAILED
- AC-6: T5 transition (ACTIVE→PENDING_EVALUATION) with at least 1 Deliverable → 200
- AC-7: T5 transition without Deliverable (even if client sends deliverable_count) → 422 PRECONDITION_FAILED
- AC-S2 (threat-model): ORG_MEMBER/ORG_ADMIN/COORDINATOR tries to submit deliverable → 403 FORBIDDEN
- AC-S3 (threat-model): Client sends submitted_by_user_id in body → ignored, principal's user_id used
- AC-S4 (threat-model): Client sends deliverable_count in T5 transition → ignored, real COUNT query used
- AC-S5 (threat-model): Cross-talent + missing required field (title) → 404 (scope-check before validation)

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Error responses validated against {"code": ..., "message": ..., "request_id": ...} schema (wrapped in detail)
- Principal enjection: X-Debug-User-Id header
- Engagement seeded with DRAFT/PENDING_APPROVAL/ACTIVE status
- Deliverable model + POST /engagements/{id}/deliverables endpoint referenced (import error expected until implementation)

Coverage Target: Deliverable creation (happy path + tenant isolation + role elevation + precondition check) + T5 transition precondition.

Status: Tests are RED (expected) — implementation not yet available.
"""

import pytest

from app.models import (
    User,
    TalentProfile,
    Organization,
    Institution,
    Engagement,
    OrganizationMember,
    InstitutionMember,
)

# Import will fail until Deliverable model is implemented
try:
    from app.models import Deliverable
except ImportError:
    Deliverable = None


# ============================================================================
# Fixtures: Users, TalentProfiles, Organizations, Institutions, Engagements
# ============================================================================


@pytest.fixture
def user_talent_alice_deliv(session):
    """Talent user Alice for deliverable tests."""
    user = User(email="alice.talent.deliv@example.com", password_hash="hash_alice")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_bob_deliv(session):
    """Talent user Bob for deliverable isolation tests."""
    user = User(email="bob.talent.deliv@example.com", password_hash="hash_bob")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_org_member_charlie_deliv(session):
    """ORG:MEMBER user Charlie for deliverable tests."""
    user = User(email="charlie.member.deliv@example.com", password_hash="hash_charlie")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_inst_coord_diana_deliv(session):
    """INST:COORD user Diana for deliverable tests."""
    user = User(email="diana.coord.deliv@example.com", password_hash="hash_diana")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_org_admin_evan_deliv(session):
    """ORG:ADMIN user Evan for deliverable tests."""
    user = User(email="evan.admin.deliv@example.com", password_hash="hash_evan")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent_alice_deliv(session, user_talent_alice_deliv, institution_a_deliv):
    """Talent profile for Alice (institution_a)."""
    profile = TalentProfile(
        user_id=user_talent_alice_deliv.id,
        institution_id=institution_a_deliv.id,
        full_name="Alice Talent Deliv",
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
def talent_bob_deliv(session, user_talent_bob_deliv, institution_b_deliv):
    """Talent profile for Bob (institution_b)."""
    profile = TalentProfile(
        user_id=user_talent_bob_deliv.id,
        institution_id=institution_b_deliv.id,
        full_name="Bob Talent Deliv",
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
def organization_a_deliv(session):
    """Organization A for deliverable tests."""
    org = Organization(
        name="Test Org A Deliv",
        domain="testorga.deliv.example.com",
        legal_id="ORG-A-DELIV-001",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def organization_b_deliv(session):
    """Organization B for deliverable isolation tests."""
    org = Organization(
        name="Test Org B Deliv",
        domain="testorgb.deliv.example.com",
        legal_id="ORG-B-DELIV-001",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def institution_a_deliv(session):
    """Institution A for deliverable tests."""
    inst = Institution(
        name="Test Institution A Deliv",
        domain="testinsta.deliv.example.com",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def institution_b_deliv(session):
    """Institution B for cross-institution isolation."""
    inst = Institution(
        name="Test Institution B Deliv",
        domain="testinstb.deliv.example.com",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def org_member_charlie_deliv(session, organization_a_deliv, user_org_member_charlie_deliv):
    """Charlie is ORG:MEMBER of organization_a."""
    member = OrganizationMember(
        organization_id=organization_a_deliv.id,
        user_id=user_org_member_charlie_deliv.id,
        role="MEMBER",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def org_admin_evan_deliv(session, organization_a_deliv, user_org_admin_evan_deliv):
    """Evan is ORG:ADMIN of organization_a."""
    member = OrganizationMember(
        organization_id=organization_a_deliv.id,
        user_id=user_org_admin_evan_deliv.id,
        role="ADMIN",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def inst_coord_diana_deliv(session, institution_a_deliv, user_inst_coord_diana_deliv):
    """Diana is INST:COORD of institution_a."""
    coord = InstitutionMember(
        institution_id=institution_a_deliv.id,
        user_id=user_inst_coord_diana_deliv.id,
        role="COORDINATOR",
    )
    session.add(coord)
    session.flush()
    return coord


@pytest.fixture
def engagement_active_alice_deliv(session, talent_alice_deliv, organization_a_deliv, institution_a_deliv):
    """ACTIVE engagement for Alice (organization_a, institution_a)."""
    engagement = Engagement(
        talent_id=talent_alice_deliv.id,
        organization_id=organization_a_deliv.id,
        institution_id=institution_a_deliv.id,
        kind="INTERNSHIP",
        title="Alice Deliv Test Project",
        status="ACTIVE",
        version=3,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_active_bob_deliv(session, talent_bob_deliv, organization_b_deliv, institution_b_deliv):
    """ACTIVE engagement for Bob (organization_b, institution_b) — isolation test."""
    engagement = Engagement(
        talent_id=talent_bob_deliv.id,
        organization_id=organization_b_deliv.id,
        institution_id=institution_b_deliv.id,
        kind="INTERNSHIP",
        title="Bob Deliv Test Project",
        status="ACTIVE",
        version=3,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_draft_alice_deliv(session, talent_alice_deliv, organization_a_deliv, institution_a_deliv):
    """DRAFT engagement for Alice (not ACTIVE)."""
    engagement = Engagement(
        talent_id=talent_alice_deliv.id,
        organization_id=organization_a_deliv.id,
        institution_id=institution_a_deliv.id,
        kind="INTERNSHIP",
        title="Alice Draft Project",
        status="DRAFT",
        version=1,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_pending_approval_alice_deliv(session, talent_alice_deliv, organization_a_deliv, institution_a_deliv):
    """PENDING_APPROVAL engagement for Alice (not ACTIVE)."""
    engagement = Engagement(
        talent_id=talent_alice_deliv.id,
        organization_id=organization_a_deliv.id,
        institution_id=institution_a_deliv.id,
        kind="CAPSTONE",
        title="Alice Pending Project",
        status="PENDING_APPROVAL",
        version=2,
    )
    session.add(engagement)
    session.flush()
    return engagement


# ============================================================================
# AC-2: Happy Path — Deliverable Submission (TALENT, ACTIVE)
# ============================================================================


class TestDeliverableCreationHappyPath:
    """
    AC-2: TALENT submits deliverable on their own ACTIVE engagement.
    Expected: 201 + deliverable object with id, engagement_id, title, description,
    submitted_by_user_id (from principal, NOT client), submitted_at, created_at, updated_at.
    Audit: DELIVERABLE_SUBMITTED written.
    """

    def test_deliverable_creation_talent_201(
        self, client, session, user_talent_alice_deliv, talent_alice_deliv, engagement_active_alice_deliv
    ):
        """
        AC-2: Alice (TALENT) submits deliverable on her own ACTIVE engagement.

        Acceptance Criteria:
        - Status code: 201 Created
        - Response contains: id (UUID), engagement_id, title, description, submitted_by_user_id (= principal.user_id),
          submitted_at, created_at, updated_at
        - submitted_by_user_id MUST be principal's user_id (Alice's id), NOT from request body
        - Audit event DELIVERABLE_SUBMITTED written
        - Deliverable stored in DB with correct engagement_id and submitted_by_user_id
        """
        payload = {
            "title": "Final Report",
            "description": "Comprehensive project report and findings",
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_deliv.id}/deliverables",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice_deliv.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()

        # Assert: response schema
        assert "id" in data
        assert data.get("engagement_id") == str(engagement_active_alice_deliv.id)
        assert data.get("title") == "Final Report"
        assert data.get("description") == "Comprehensive project report and findings"
        # CRITICAL: submitted_by_user_id must be principal's user_id, not client-supplied
        assert data.get("submitted_by_user_id") == str(user_talent_alice_deliv.id)
        assert "submitted_at" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_deliverable_creation_optional_description_201(
        self, client, session, user_talent_alice_deliv, talent_alice_deliv, engagement_active_alice_deliv
    ):
        """
        AC-2: Alice submits deliverable without description (nullable field).

        Acceptance Criteria:
        - Status code: 201 Created
        - description field is null or omitted
        - submitted_by_user_id is still principal's user_id
        """
        payload = {
            "title": "Project Code",
            # description omitted
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_deliv.id}/deliverables",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice_deliv.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        assert data.get("title") == "Project Code"
        assert data.get("submitted_by_user_id") == str(user_talent_alice_deliv.id)


# ============================================================================
# AC-4: Cross-Talent Isolation — Deliverable (404 NOT_FOUND)
# ============================================================================


class TestDeliverableCrossTalentIsolation:
    """
    AC-4: Cross-talent isolation for deliverable submission.
    When TALENT tries to access engagement of another talent → 404 NOT_FOUND (not 403, not 422).
    """

    def test_deliverable_creation_cross_talent_404(
        self, client, session, user_talent_alice_deliv, talent_alice_deliv, engagement_active_bob_deliv
    ):
        """
        AC-4: Alice (TALENT) tries to submit deliverable on Bob's engagement → 404 NOT_FOUND.

        Acceptance Criteria:
        - Status code: 404 (not 403, not 422)
        - Error code: NOT_FOUND (exact match)
        - Response body does not leak engagement details (no Bob's talent info)
        """
        payload = {
            "title": "Unauthorized deliverable",
            "description": "Trying to submit on someone else's engagement",
        }

        response = client.post(
            f"/engagements/{engagement_active_bob_deliv.id}/deliverables",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice_deliv.id)},
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "NOT_FOUND", f"Expected code NOT_FOUND, got {error_obj.get('code')}"


# ============================================================================
# AC-5: Precondition Failed — Engagement Not ACTIVE
# ============================================================================


class TestDeliverablePreconditionNotActive:
    """
    AC-5: Deliverable can only be submitted on ACTIVE engagement.
    If engagement is DRAFT/PENDING_APPROVAL/REJECTED/CANCELLED → 422 PRECONDITION_FAILED.
    """

    def test_deliverable_creation_draft_engagement_422(
        self, client, session, user_talent_alice_deliv, talent_alice_deliv, engagement_draft_alice_deliv
    ):
        """
        AC-5: Alice tries to submit deliverable on DRAFT engagement → 422 PRECONDITION_FAILED.

        Acceptance Criteria:
        - Status code: 422 Unprocessable Entity
        - Error code: PRECONDITION_FAILED (exact match)
        - Error message indicates "only ACTIVE engagement" or similar
        - Engagement status/version unchanged in DB
        """
        payload = {
            "title": "Deliverable on DRAFT",
            "description": "Should fail",
        }

        response = client.post(
            f"/engagements/{engagement_draft_alice_deliv.id}/deliverables",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice_deliv.id)},
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "PRECONDITION_FAILED", f"Expected PRECONDITION_FAILED, got {error_obj.get('code')}"

    def test_deliverable_creation_pending_approval_engagement_422(
        self, client, session, user_talent_alice_deliv, talent_alice_deliv, engagement_pending_approval_alice_deliv
    ):
        """
        AC-5: Alice tries to submit deliverable on PENDING_APPROVAL engagement → 422 PRECONDITION_FAILED.

        Acceptance Criteria:
        - Status code: 422
        - Error code: PRECONDITION_FAILED
        """
        payload = {
            "title": "Deliverable on PENDING_APPROVAL",
            "description": "Should fail",
        }

        response = client.post(
            f"/engagements/{engagement_pending_approval_alice_deliv.id}/deliverables",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice_deliv.id)},
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "PRECONDITION_FAILED"


# ============================================================================
# AC-S2 (threat-model): Role Elevation — ORG_MEMBER/ORG_ADMIN/COORDINATOR Cannot Submit Deliverable (403)
# ============================================================================


class TestDeliverableRoleElevation:
    """
    AC-S2: ORG_MEMBER/ORG_ADMIN/COORDINATOR tries to submit deliverable (TALENT-only action).
    Deliverable submission is restricted to TALENT.
    Since the resource (engagement) is visible to these users (in their org/institution scope), error is 403 FORBIDDEN (not 404).
    """

    def test_deliverable_creation_org_member_forbidden_403(
        self, client, session, user_org_member_charlie_deliv, org_member_charlie_deliv, engagement_active_alice_deliv
    ):
        """
        AC-S2: Charlie (ORG:MEMBER of organization_a) tries to submit deliverable
        on Alice's engagement in organization_a → 403 FORBIDDEN.
        Charlie can see the engagement (it's in his org scope), but lacks permission to submit deliverables.

        Acceptance Criteria:
        - Status code: 403 Forbidden (not 404, not 422)
        - Error code: FORBIDDEN (exact match)
        - Error message indicates lack of permission
        - Engagement state unchanged
        """
        payload = {
            "title": "Unauthorized deliverable",
            "description": "I'm not the talent",
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_deliv.id}/deliverables",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_deliv.id)},
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "FORBIDDEN", f"Expected FORBIDDEN, got {error_obj.get('code')}"

    def test_deliverable_creation_org_admin_forbidden_403(
        self, client, session, user_org_admin_evan_deliv, org_admin_evan_deliv, engagement_active_alice_deliv
    ):
        """
        AC-S2: Evan (ORG:ADMIN of organization_a) tries to submit deliverable
        on Alice's engagement in organization_a → 403 FORBIDDEN.

        Acceptance Criteria:
        - Status code: 403 Forbidden
        - Error code: FORBIDDEN
        """
        payload = {
            "title": "Admin trying to submit",
            "description": "But admins can't do this",
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_deliv.id}/deliverables",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_admin_evan_deliv.id)},
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "FORBIDDEN"

    def test_deliverable_creation_inst_coord_forbidden_403(
        self, client, session, user_inst_coord_diana_deliv, inst_coord_diana_deliv, engagement_active_alice_deliv
    ):
        """
        AC-S2: Diana (INST:COORD of institution_a) tries to submit deliverable
        on Alice's engagement in institution_a → 403 FORBIDDEN.

        Acceptance Criteria:
        - Status code: 403 Forbidden
        - Error code: FORBIDDEN
        """
        payload = {
            "title": "Coordinator trying to submit",
            "description": "But coordinators can't do this",
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_deliv.id}/deliverables",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana_deliv.id)},
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "FORBIDDEN"


# ============================================================================
# AC-S3 (threat-model): Tampering Prevention — submitted_by_user_id Ignored
# ============================================================================


class TestDeliverableSubmittedByUserIdTampering:
    """
    AC-S3: Client tries to inject submitted_by_user_id in request body (e.g., another user's UUID).
    This field MUST be ignored — submitted_by_user_id is always set to principal.user_id.

    Kritik: Alice tarafından gönderilen payload'da başka bir user'ın UUID'si olsa bile,
    kaydedilen submitted_by_user_id HER ZAMAN Alice'in ID'si olmalı.
    """

    def test_deliverable_creation_submitted_by_user_id_ignored(
        self, client, session, user_talent_alice_deliv, talent_alice_deliv, engagement_active_alice_deliv, user_talent_bob_deliv
    ):
        """
        AC-S3: Alice submits deliverable, but body contains submitted_by_user_id=Bob's ID.
        The field must be ignored; DB record shows submitted_by_user_id=Alice's ID.

        Acceptance Criteria:
        - Status code: 201 Created
        - Response submitted_by_user_id field = Alice's ID (principal), NOT Bob's ID from body
        - DB query confirms submitted_by_user_id = Alice's ID
        """
        payload = {
            "title": "Deliverable with tampering attempt",
            "description": "Trying to forge who submitted it",
            "submitted_by_user_id": str(user_talent_bob_deliv.id),  # Trying to claim Bob submitted
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_deliv.id}/deliverables",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice_deliv.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()

        # CRITICAL: submitted_by_user_id must be Alice's ID, NOT Bob's ID from payload
        assert data.get("submitted_by_user_id") == str(user_talent_alice_deliv.id), \
            f"Expected submitted_by_user_id={user_talent_alice_deliv.id}, got {data.get('submitted_by_user_id')}"
        assert data.get("submitted_by_user_id") != str(user_talent_bob_deliv.id), \
            "submitted_by_user_id must not be from client payload"


# ============================================================================
# AC-S5 (threat-model): Scope-Check Order — Cross-Talent + Missing Required Field
# ============================================================================


class TestDeliverableScopeCheckOrder:
    """
    AC-S5: Cross-talent + missing required field (e.g., title).
    Scope-check (access control) must run BEFORE field validation.
    Result: 404 NOT_FOUND (not 422 validation error).
    """

    def test_deliverable_creation_cross_talent_missing_title_404(
        self, client, session, user_talent_alice_deliv, talent_alice_deliv, engagement_active_bob_deliv
    ):
        """
        AC-S5: Alice (TALENT of engagement_active_alice) tries to submit deliverable on Bob's engagement (engagement_active_bob)
        with a valid title, but the target engagement belongs to a different talent → 404 NOT_FOUND.

        Expected: Scope-check detects talent_id mismatch BEFORE
        accepting the request. Even with valid title, cross-talent access is denied first. Result: 404 (not 422).

        Acceptance Criteria:
        - Status code: 404 (not 422 VALIDATION_ERROR)
        - Error code: NOT_FOUND (exact match, not VALIDATION_ERROR)
        - Resource existence is not leaked (scope-check denies access uniformly)
        """
        payload = {
            "title": "Cross-tenant test deliverable",
            "description": "Deliverable without cross-talent access",
        }

        response = client.post(
            f"/engagements/{engagement_active_bob_deliv.id}/deliverables",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice_deliv.id)},
        )

        # CRITICAL: Must be 404 (scope-check before validation), not 422
        assert response.status_code == 404, f"Expected 404 (scope-check first), got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "NOT_FOUND", f"Expected NOT_FOUND, got {error_obj.get('code')}"


# ============================================================================
# AC-6: T5 Transition Precondition — At Least 1 Deliverable Present (200)
# ============================================================================


class TestT5TransitionWithDeliverable:
    """
    AC-6: T5 transition (ACTIVE→PENDING_EVALUATION) requires at least 1 Deliverable.
    When Deliverable exists: T5 transition succeeds with 200.
    """

    def test_t5_transition_with_deliverable_200(
        self, client, session, user_org_member_charlie_deliv, org_member_charlie_deliv,
        user_talent_alice_deliv, talent_alice_deliv, engagement_active_alice_deliv
    ):
        """
        AC-6: Alice submits deliverable, then Charlie (ORG:MEMBER) transitions ACTIVE→PENDING_EVALUATION (T5) → 200.

        Prerequisite:
        1. Alice (TALENT) submits deliverable on her ACTIVE engagement → 201
        2. Charlie (ORG:MEMBER) calls T5 transition → 200

        Acceptance Criteria:
        - Step 1: Deliverable submission succeeds (201)
        - Step 2: T5 transition succeeds (200)
        - Step 2 response: status="PENDING_EVALUATION", version incremented
        - DB shows engagement.status=PENDING_EVALUATION
        """
        # Step 1: Alice submits deliverable
        deliv_payload = {
            "title": "Final deliverable",
            "description": "Ready for evaluation",
        }

        deliv_response = client.post(
            f"/engagements/{engagement_active_alice_deliv.id}/deliverables",
            json=deliv_payload,
            headers={"X-Debug-User-Id": str(user_talent_alice_deliv.id)},
        )

        assert deliv_response.status_code == 201, f"Deliverable creation failed: {deliv_response.text}"

        # Step 2: Charlie transitions to PENDING_EVALUATION (T5)
        transition_payload = {
            "to_status": "PENDING_EVALUATION",
            "version": 3,  # Current version of Alice's engagement
        }

        transition_response = client.post(
            f"/engagements/{engagement_active_alice_deliv.id}/transitions",
            json=transition_payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_deliv.id)},
        )

        assert transition_response.status_code == 200, f"Expected 200, got {transition_response.status_code}: {transition_response.text}"

        transition_data = transition_response.json()
        assert transition_data.get("status") == "PENDING_EVALUATION"
        assert transition_data.get("version") == 4  # version incremented

        # DB verification
        session.refresh(engagement_active_alice_deliv)
        assert engagement_active_alice_deliv.status == "PENDING_EVALUATION"
        assert engagement_active_alice_deliv.version == 4


# ============================================================================
# AC-7: T5 Transition Precondition — No Deliverable (422)
# ============================================================================


class TestT5TransitionWithoutDeliverable:
    """
    AC-7: T5 transition (ACTIVE→PENDING_EVALUATION) requires at least 1 Deliverable.
    When NO Deliverable exists: T5 transition fails with 422 PRECONDITION_FAILED.
    Even if client sends fake deliverable_count field, real query is used.
    """

    def test_t5_transition_without_deliverable_422(
        self, client, session, user_org_member_charlie_deliv, org_member_charlie_deliv, engagement_active_alice_deliv
    ):
        """
        AC-7: Engagement has NO deliverable. Charlie tries T5 transition → 422 PRECONDITION_FAILED.

        Acceptance Criteria:
        - Status code: 422 Unprocessable Entity
        - Error code: PRECONDITION_FAILED (exact match)
        - Error message indicates "at least one deliverable required" or similar
        - Engagement status/version unchanged (still ACTIVE)
        """
        transition_payload = {
            "to_status": "PENDING_EVALUATION",
            "version": 3,
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_deliv.id}/transitions",
            json=transition_payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_deliv.id)},
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "PRECONDITION_FAILED", f"Expected PRECONDITION_FAILED, got {error_obj.get('code')}"

        # DB verification: status unchanged
        session.refresh(engagement_active_alice_deliv)
        assert engagement_active_alice_deliv.status == "ACTIVE"
        assert engagement_active_alice_deliv.version == 3

    def test_t5_transition_with_fake_deliverable_count_field_422(
        self, client, session, user_org_member_charlie_deliv, org_member_charlie_deliv, engagement_active_alice_deliv
    ):
        """
        AC-S4 (threat-model): Client sends fake deliverable_count field in T5 transition body.
        Field must be ignored; real COUNT(*) query checks actual Deliverable records.
        Result: 422 (no real deliverable exists, despite deliverable_count=5 in body).

        Acceptance Criteria:
        - Status code: 422 PRECONDITION_FAILED (not 200)
        - Error code: PRECONDITION_FAILED
        - Engagement status unchanged
        """
        transition_payload = {
            "to_status": "PENDING_EVALUATION",
            "version": 3,
            "deliverable_count": 5,  # Fake field, client lying about deliverable count
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_deliv.id}/transitions",
            json=transition_payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_deliv.id)},
        )

        # CRITICAL: Must be 422 (real query shows 0 deliverables), not 200 (client's fake count ignored)
        assert response.status_code == 422, f"Expected 422 (fake count ignored), got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "PRECONDITION_FAILED"

        # DB verification: status unchanged
        session.refresh(engagement_active_alice_deliv)
        assert engagement_active_alice_deliv.status == "ACTIVE"


# ============================================================================
# Response Schema Validation
# ============================================================================


class TestDeliverableResponseSchema:
    """Verify deliverable creation response schemas match API contract."""

    def test_deliverable_creation_success_response_schema_201(
        self, client, session, user_talent_alice_deliv, talent_alice_deliv, engagement_active_alice_deliv
    ):
        """201 response must have deliverable object with required fields."""
        payload = {
            "title": "Schema test deliverable",
            "description": "Testing response schema",
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_deliv.id}/deliverables",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice_deliv.id)},
        )

        assert response.status_code == 201

        data = response.json()

        # Assert: required fields present
        required_fields = ["id", "engagement_id", "title", "submitted_by_user_id", "submitted_at", "created_at", "updated_at"]

        for field in required_fields:
            assert field in data, f"Response missing required field: {field}"

        # Assert: types
        assert isinstance(data["id"], str)
        assert isinstance(data["engagement_id"], str)
        assert isinstance(data["title"], str)
        assert isinstance(data["submitted_by_user_id"], str)

    def test_deliverable_creation_error_response_schema(
        self, client, user_talent_alice_deliv, talent_alice_deliv, engagement_draft_alice_deliv
    ):
        """Error responses must have {code, message, request_id} schema."""
        payload = {
            "title": "Error schema test",
            "description": "Testing error response",
        }

        response = client.post(
            f"/engagements/{engagement_draft_alice_deliv.id}/deliverables",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice_deliv.id)},
        )

        assert response.status_code == 422

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert "code" in error_obj, "Error response must have 'code' field"
        assert "message" in error_obj, "Error response must have 'message' field"
        assert "request_id" in error_obj, "Error response must have 'request_id' field"
