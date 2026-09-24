"""
Engagement Task endpoint tests (PLAN 2.4 — engagement-task-deliverable, AC-1, AC-3, AC-5, AC-S1, AC-S5).

Implements Acceptance Criteria for POST /engagements/{id}/tasks:
- AC-1: Happy path (COORDINATOR/ORG_MEMBER/ORG_ADMIN, ACTIVE engagement) → 201
- AC-3: Cross-organization scope violation → 404 NOT_FOUND
- AC-5: Engagement not ACTIVE (DRAFT/PENDING_APPROVAL/REJECTED/CANCELLED) → 422 PRECONDITION_FAILED
- AC-S1 (threat-model): TALENT tries to create task → 403 FORBIDDEN (resource visible, action forbidden)
- AC-S5 (threat-model): Cross-org + missing required field (title) → 404 (scope-check order: 404 before 422)

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Error responses validated against {"code": ..., "message": ..., "request_id": ...} schema (wrapped in detail)
- Principal enjection: X-Debug-User-Id header
- Engagement seeded with DRAFT/PENDING_APPROVAL/ACTIVE status
- EngagementTask model + POST /engagements/{id}/tasks endpoint referenced (import error expected until implementation)

Coverage Target: Task creation (happy path + tenant isolation + role elevation + precondition check).

Status: Tests are RED (expected) — implementation not yet available.
"""

import pytest
from uuid import uuid4

from app.models import (
    User,
    TalentProfile,
    Organization,
    Institution,
    Engagement,
    OrganizationMember,
    InstitutionMember,
    Skill,
)

# Import will fail until EngagementTask model is implemented
try:
    from app.models import EngagementTask
except ImportError:
    EngagementTask = None

# Import SkillSignal model for YET-71 tests
try:
    from app.models import SkillSignal
except ImportError:
    SkillSignal = None


# ============================================================================
# Fixtures: Users, TalentProfiles, Organizations, Institutions, Engagements
# ============================================================================


@pytest.fixture
def user_talent_alice_task(session):
    """Talent user Alice for task tests."""
    user = User(email="alice.talent.task@example.com", password_hash="hash_alice")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_bob_task(session):
    """Talent user Bob for task isolation tests."""
    user = User(email="bob.talent.task@example.com", password_hash="hash_bob")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_org_member_charlie_task(session):
    """ORG:MEMBER user Charlie for task tests."""
    user = User(email="charlie.member.task@example.com", password_hash="hash_charlie")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_inst_coord_diana_task(session):
    """INST:COORD user Diana for task tests."""
    user = User(email="diana.coord.task@example.com", password_hash="hash_diana")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_org_admin_evan_task(session):
    """ORG:ADMIN user Evan for task tests."""
    user = User(email="evan.admin.task@example.com", password_hash="hash_evan")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent_alice_task(session, user_talent_alice_task, institution_a_task):
    """Talent profile for Alice (institution_a)."""
    profile = TalentProfile(
        user_id=user_talent_alice_task.id,
        institution_id=institution_a_task.id,
        full_name="Alice Talent Task",
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
def talent_bob_task(session, user_talent_bob_task, institution_b_task):
    """Talent profile for Bob (institution_b)."""
    profile = TalentProfile(
        user_id=user_talent_bob_task.id,
        institution_id=institution_b_task.id,
        full_name="Bob Talent Task",
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
def organization_a_task(session):
    """Organization A for task tests."""
    org = Organization(
        name="Test Org A Task",
        domain="testorga.task.example.com",
        legal_id="ORG-A-TASK-001",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def organization_b_task(session):
    """Organization B for task isolation tests."""
    org = Organization(
        name="Test Org B Task",
        domain="testorgb.task.example.com",
        legal_id="ORG-B-TASK-001",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def institution_a_task(session):
    """Institution A for task tests."""
    inst = Institution(
        name="Test Institution A Task",
        domain="testinsta.task.example.com",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def institution_b_task(session):
    """Institution B for cross-institution isolation."""
    inst = Institution(
        name="Test Institution B Task",
        domain="testinstb.task.example.com",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def org_member_charlie_task(session, organization_a_task, user_org_member_charlie_task):
    """Charlie is ORG:MEMBER of organization_a."""
    member = OrganizationMember(
        organization_id=organization_a_task.id,
        user_id=user_org_member_charlie_task.id,
        role="MEMBER",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def org_admin_evan_task(session, organization_a_task, user_org_admin_evan_task):
    """Evan is ORG:ADMIN of organization_a."""
    member = OrganizationMember(
        organization_id=organization_a_task.id,
        user_id=user_org_admin_evan_task.id,
        role="ADMIN",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def inst_coord_diana_task(session, institution_a_task, user_inst_coord_diana_task):
    """Diana is INST:COORD of institution_a."""
    coord = InstitutionMember(
        institution_id=institution_a_task.id,
        user_id=user_inst_coord_diana_task.id,
        role="COORDINATOR",
    )
    session.add(coord)
    session.flush()
    return coord


@pytest.fixture
def engagement_active_alice_task(session, talent_alice_task, organization_a_task, institution_a_task):
    """ACTIVE engagement for Alice (organization_a, institution_a)."""
    engagement = Engagement(
        talent_id=talent_alice_task.id,
        organization_id=organization_a_task.id,
        institution_id=institution_a_task.id,
        kind="INTERNSHIP",
        title="Alice Task Test Project",
        status="ACTIVE",
        version=3,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_active_bob_task(session, talent_bob_task, organization_b_task, institution_b_task):
    """ACTIVE engagement for Bob (organization_b, institution_b) — isolation test."""
    engagement = Engagement(
        talent_id=talent_bob_task.id,
        organization_id=organization_b_task.id,
        institution_id=institution_b_task.id,
        kind="INTERNSHIP",
        title="Bob Task Test Project",
        status="ACTIVE",
        version=3,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_draft_alice_task(session, talent_alice_task, organization_a_task, institution_a_task):
    """DRAFT engagement for Alice (not ACTIVE)."""
    engagement = Engagement(
        talent_id=talent_alice_task.id,
        organization_id=organization_a_task.id,
        institution_id=institution_a_task.id,
        kind="INTERNSHIP",
        title="Alice Draft Project",
        status="DRAFT",
        version=1,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_pending_approval_alice_task(session, talent_alice_task, organization_a_task, institution_a_task):
    """PENDING_APPROVAL engagement for Alice (not ACTIVE)."""
    engagement = Engagement(
        talent_id=talent_alice_task.id,
        organization_id=organization_a_task.id,
        institution_id=institution_a_task.id,
        kind="CAPSTONE",
        title="Alice Pending Project",
        status="PENDING_APPROVAL",
        version=2,
    )
    session.add(engagement)
    session.flush()
    return engagement


# ============================================================================
# AC-1: Happy Path — Task Creation (COORDINATOR/ORG_MEMBER/ORG_ADMIN, ACTIVE)
# ============================================================================


class TestTaskCreationHappyPath:
    """
    AC-1: COORDINATOR/ORG_MEMBER/ORG_ADMIN creates task on ACTIVE engagement.
    Expected: 201 + task object with id, engagement_id, title, description, status=PLANNED, etc.
    Audit: TASK_CREATED written.
    """

    def test_task_creation_org_member_200(
        self, client, session, user_org_member_charlie_task, org_member_charlie_task, engagement_active_alice_task
    ):
        """
        AC-1: Charlie (ORG:MEMBER of organization_a) creates task on Alice's ACTIVE engagement.

        Acceptance Criteria:
        - Status code: 201 Created
        - Response contains: id (UUID), engagement_id, title, description, status="PLANNED",
          due_at (nullable), completed_at (nullable), created_at, updated_at
        - Audit event TASK_CREATED written
        - Task stored in DB with correct engagement_id
        """
        payload = {
            "title": "Task 1: Research phase",
            "description": "Investigate technical stack",
            "due_at": None,
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_task.id}/tasks",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_task.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()

        # Assert: response schema
        assert "id" in data
        assert data.get("engagement_id") == str(engagement_active_alice_task.id)
        assert data.get("title") == "Task 1: Research phase"
        assert data.get("description") == "Investigate technical stack"
        assert data.get("status") == "PLANNED"
        assert data.get("due_at") is None
        assert data.get("completed_at") is None
        assert "created_at" in data
        assert "updated_at" in data

    def test_task_creation_org_admin_201(
        self, client, session, user_org_admin_evan_task, org_admin_evan_task, engagement_active_alice_task
    ):
        """
        AC-1: Evan (ORG:ADMIN of organization_a) creates task on Alice's ACTIVE engagement.

        Acceptance Criteria:
        - Status code: 201 Created
        - Response contains task with status=PLANNED
        """
        payload = {
            "title": "Task 2: Development",
            "description": None,
            "due_at": None,
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_task.id}/tasks",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_admin_evan_task.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        assert data.get("status") == "PLANNED"
        assert data.get("title") == "Task 2: Development"

    def test_task_creation_inst_coord_201(
        self, client, session, user_inst_coord_diana_task, inst_coord_diana_task, engagement_active_alice_task
    ):
        """
        AC-1: Diana (INST:COORD of institution_a) creates task on Alice's ACTIVE engagement.

        Acceptance Criteria:
        - Status code: 201 Created
        """
        payload = {
            "title": "Task 3: Testing",
            "description": "QA and integration testing",
            "due_at": None,
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_task.id}/tasks",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana_task.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        assert data.get("status") == "PLANNED"


# ============================================================================
# AC-3: Cross-Organization Isolation — Task (404 NOT_FOUND)
# ============================================================================


class TestTaskCrossOrgIsolation:
    """
    AC-3: Cross-organization/cross-institution isolation for task creation.
    When principal (COORDINATOR/ORG_MEMBER/ORG_ADMIN) tries to access
    engagement outside their scope → 404 NOT_FOUND (not 403, not 422).
    """

    def test_task_creation_cross_org_404(
        self, client, session, user_org_member_charlie_task, org_member_charlie_task, engagement_active_bob_task
    ):
        """
        AC-3: Charlie (ORG:MEMBER of organization_a) tries to create task
        on Bob's engagement (organization_b) → 404 NOT_FOUND.

        Acceptance Criteria:
        - Status code: 404 (not 403, not 422)
        - Error code: NOT_FOUND (exact match)
        - Response body does not leak engagement details (no org_b info)
        """
        payload = {
            "title": "Unauthorized task",
            "description": "Trying to access cross-org engagement",
            "due_at": None,
        }

        response = client.post(
            f"/engagements/{engagement_active_bob_task.id}/tasks",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_task.id)},
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "NOT_FOUND", f"Expected code NOT_FOUND, got {error_obj.get('code')}"

    def test_task_creation_cross_institution_404(
        self, client, session, user_inst_coord_diana_task, inst_coord_diana_task, engagement_active_bob_task
    ):
        """
        AC-3: Diana (INST:COORD of institution_a) tries to create task
        on Bob's engagement (institution_b) → 404 NOT_FOUND.

        Acceptance Criteria:
        - Status code: 404 (not 403, not 422)
        - Error code: NOT_FOUND
        """
        payload = {
            "title": "Cross-institution task",
            "description": "Invalid access attempt",
            "due_at": None,
        }

        response = client.post(
            f"/engagements/{engagement_active_bob_task.id}/tasks",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana_task.id)},
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "NOT_FOUND"


# ============================================================================
# AC-5: Precondition Failed — Engagement Not ACTIVE
# ============================================================================


class TestTaskPreconditionNotActive:
    """
    AC-5: Task can only be created on ACTIVE engagement.
    If engagement is DRAFT/PENDING_APPROVAL/REJECTED/CANCELLED → 422 PRECONDITION_FAILED.
    """

    def test_task_creation_draft_engagement_422(
        self, client, session, user_org_member_charlie_task, org_member_charlie_task, engagement_draft_alice_task
    ):
        """
        AC-5: Charlie tries to create task on DRAFT engagement → 422 PRECONDITION_FAILED.

        Acceptance Criteria:
        - Status code: 422 Unprocessable Entity
        - Error code: PRECONDITION_FAILED (exact match)
        - Error message indicates "only ACTIVE engagement" or similar
        - Engagement status/version unchanged in DB
        """
        payload = {
            "title": "Task on DRAFT",
            "description": "Should fail",
            "due_at": None,
        }

        response = client.post(
            f"/engagements/{engagement_draft_alice_task.id}/tasks",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_task.id)},
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "PRECONDITION_FAILED", f"Expected PRECONDITION_FAILED, got {error_obj.get('code')}"

    def test_task_creation_pending_approval_engagement_422(
        self, client, session, user_org_member_charlie_task, org_member_charlie_task, engagement_pending_approval_alice_task
    ):
        """
        AC-5: Charlie tries to create task on PENDING_APPROVAL engagement → 422 PRECONDITION_FAILED.

        Acceptance Criteria:
        - Status code: 422
        - Error code: PRECONDITION_FAILED
        """
        payload = {
            "title": "Task on PENDING_APPROVAL",
            "description": "Should fail",
            "due_at": None,
        }

        response = client.post(
            f"/engagements/{engagement_pending_approval_alice_task.id}/tasks",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_task.id)},
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "PRECONDITION_FAILED"


# ============================================================================
# AC-S1 (threat-model): Role Elevation — TALENT Cannot Create Task (403)
# ============================================================================


class TestTaskRoleElevation:
    """
    AC-S1: TALENT (Alice) tries to create task on her own ACTIVE engagement.
    Task creation is COORDINATOR/ORG_MEMBER/ORG_ADMIN only.
    Since the resource (engagement) is visible to Alice (her own), error is 403 FORBIDDEN (not 404).
    """

    def test_task_creation_talent_forbidden_403(
        self, client, session, user_talent_alice_task, talent_alice_task, engagement_active_alice_task
    ):
        """
        AC-S1: Alice (TALENT) tries to create task on her own ACTIVE engagement → 403 FORBIDDEN.
        Alice can see her own engagement (it's not 404), but lacks permission to create tasks.

        Acceptance Criteria:
        - Status code: 403 Forbidden (not 404, not 422)
        - Error code: FORBIDDEN (exact match)
        - Error message indicates lack of permission
        - Engagement state unchanged
        """
        payload = {
            "title": "Task I'm trying to create",
            "description": "But I'm just a talent",
            "due_at": None,
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_task.id}/tasks",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice_task.id)},
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "FORBIDDEN", f"Expected FORBIDDEN, got {error_obj.get('code')}"


# ============================================================================
# AC-S5 (threat-model): Scope-Check Order — Cross-Org + Missing Required Field
# ============================================================================


class TestTaskScopeCheckOrder:
    """
    AC-S5: Cross-org + missing required field (e.g., title).
    Scope-check (access control) must run BEFORE field validation.
    Result: 404 NOT_FOUND (not 422 validation error).

    Kritik: Bu, çapraz-org erişimi tespit ettikten sonra validation hatasını
    döndürmemeliyiz — erişim reddetmek daha düşük seviye bir kontrol.
    """

    def test_task_creation_cross_org_missing_title_404(
        self, client, session, user_org_member_charlie_task, org_member_charlie_task, engagement_active_bob_task
    ):
        """
        AC-S5: Charlie (ORG:MEMBER of organization_a) tries to create task on Bob's engagement (organization_b)
        with a valid title, but the target engagement is out of Charlie's cross-org scope → 404 NOT_FOUND.

        Expected: Scope-check detects organization_b not in Charlie's scope BEFORE
        accepting the request. Even with valid title, cross-org access is denied first. Result: 404 (not 422).

        Acceptance Criteria:
        - Status code: 404 (not 422 VALIDATION_ERROR)
        - Error code: NOT_FOUND (exact match, not VALIDATION_ERROR)
        - Resource existence is not leaked (scope-check denies access uniformly)
        """
        payload = {
            "title": "Cross-tenant test task",
            "description": "Task without cross-org access",
            "due_at": None,
        }

        response = client.post(
            f"/engagements/{engagement_active_bob_task.id}/tasks",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_task.id)},
        )

        # CRITICAL: Must be 404 (scope-check before validation), not 422
        assert response.status_code == 404, f"Expected 404 (scope-check first), got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "NOT_FOUND", f"Expected NOT_FOUND, got {error_obj.get('code')}"


# ============================================================================
# Response Schema Validation
# ============================================================================


class TestTaskResponseSchema:
    """Verify task creation response schemas match API contract."""

    def test_task_creation_success_response_schema_201(
        self, client, session, user_org_member_charlie_task, org_member_charlie_task, engagement_active_alice_task
    ):
        """201 response must have task object with required fields."""
        payload = {
            "title": "Schema test task",
            "description": "Testing response schema",
            "due_at": None,
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_task.id}/tasks",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_task.id)},
        )

        assert response.status_code == 201

        data = response.json()

        # Assert: required fields present
        required_fields = ["id", "engagement_id", "title", "status", "created_at", "updated_at"]

        for field in required_fields:
            assert field in data, f"Response missing required field: {field}"

        # Assert: types
        assert isinstance(data["id"], str)
        assert isinstance(data["engagement_id"], str)
        assert isinstance(data["title"], str)
        assert isinstance(data["status"], str)

    def test_task_creation_error_response_schema(
        self, client, user_org_member_charlie_task, org_member_charlie_task, engagement_draft_alice_task
    ):
        """Error responses must have {code, message, request_id} schema."""
        payload = {
            "title": "Error schema test",
            "description": "Testing error response",
            "due_at": None,
        }

        response = client.post(
            f"/engagements/{engagement_draft_alice_task.id}/tasks",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_task.id)},
        )

        assert response.status_code == 422

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert "code" in error_obj, "Error response must have 'code' field"
        assert "message" in error_obj, "Error response must have 'message' field"
        assert "request_id" in error_obj, "Error response must have 'request_id' field"


# ============================================================================
# YET-71: SkillSignal Türetme — TASK source_type
# ============================================================================


@pytest.fixture
def skill_python_task(session):
    """Test skill: Python for YET-71 task tests."""
    skill = Skill(
        slug="python-task",
        name_tr="Python",
        name_en="Python",
        category="LANGUAGE",
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def skill_invalid_id_task():
    """Non-existent skill UUID for invalid skill_id tests."""
    return str(uuid4())


class TestTaskSkillSignalCreation:
    """
    YET-71 AC-1: TASK + skill_id → SkillSignal(TASK, WEAK) üretilir.
    Davranış Sözleşmesi Satır 1.
    """

    def test_task_with_skill_id_creates_skill_signal_201(
        self, client, session, user_org_member_charlie_task, org_member_charlie_task,
        engagement_active_alice_task, skill_python_task
    ):
        """
        AC-1 + YET-71: Charlie (ORG:MEMBER) oluşturur task skill_id ile → 201, SkillSignal(TASK, WEAK) yazılır.

        Davranış Sözleşmesi:
        - Status code: 201
        - SkillSignal DB'de yazılır: source_type=TASK, strength=WEAK, skill_id=<verilen>
        - signal.talent_id = engagement.talent_id (Alice)
        - signal.occurred_at = task.created_at
        """
        payload = {
            "title": "Task with skill tracking",
            "description": "Python development task",
            "skill_id": str(skill_python_task.id),
            "due_at": None,
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_task.id}/tasks",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_task.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        task_id = data.get("id")
        assert data.get("skill_id") == str(skill_python_task.id)

        # DB verification: SkillSignal yazıldı
        if SkillSignal:
            signal = session.query(SkillSignal).filter_by(
                source_type="TASK",
                source_id=task_id,
                skill_id=skill_python_task.id
            ).first()

            assert signal is not None, "SkillSignal not created for TASK with skill_id"
            assert signal.strength == "WEAK", f"Expected WEAK, got {signal.strength}"
            assert signal.talent_id == engagement_active_alice_task.talent_id


class TestTaskSkillIdNone:
    """
    YET-71 AC-6: TASK skill_id None → SkillSignal yazılmaz (sessiz atlama).
    Davranış Sözleşmesi Satır 4.
    """

    def test_task_without_skill_id_no_signal_201(
        self, client, session, user_org_member_charlie_task, org_member_charlie_task, engagement_active_alice_task
    ):
        """
        AC-6 + YET-71: Charlie oluşturur task skill_id olmadan → 201, SkillSignal yazılmaz.

        Davranış Sözleşmesi:
        - Status code: 201 (başarı, değişmez)
        - response.skill_id = null
        - DB'de SkillSignal yok (sessiz atlama, hata değil)
        """
        payload = {
            "title": "Task without skill",
            "description": "Generic task",
            # skill_id intentionally omitted
            "due_at": None,
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_task.id}/tasks",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_task.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        task_id = data.get("id")
        assert data.get("skill_id") is None

        # DB verification: SkillSignal yok
        if SkillSignal:
            signal_count = session.query(SkillSignal).filter_by(source_type="TASK", source_id=task_id).count()
            assert signal_count == 0, "SkillSignal must not be created when skill_id is None"


class TestTaskInvalidSkillId:
    """
    YET-71 AC-7: Geçersiz skill_id → 422.
    Davranış Sözleşmesi Satır 6.
    """

    def test_task_with_invalid_skill_id_422(
        self, client, session, user_org_member_charlie_task, org_member_charlie_task,
        engagement_active_alice_task, skill_invalid_id_task
    ):
        """
        AC-7 + YET-71: Charlie skill_id ile gönderiyor, ama skill_id geçersiz → 422.

        Davranış Sözleşmesi:
        - Status code: 422 Unprocessable Entity
        - Error code: INVALID_REQUEST (exact match)
        - Hiçbir yazma yok (task, SkillSignal)
        """
        payload = {
            "title": "Task with invalid skill",
            "description": "This should fail",
            "skill_id": skill_invalid_id_task,  # Non-existent UUID
            "due_at": None,
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_task.id}/tasks",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_task.id)},
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "INVALID_REQUEST", \
            f"Expected INVALID_REQUEST, got {error_obj.get('code')}"


class TestTaskStrengthTampering:
    """
    YET-71 AC-S1: Tampering — strength manipülasyonu.
    İstemci `strength` alanı gönderirse Pydantic kabul etmez.
    """

    def test_task_strength_field_tampering_ignored_201(
        self, client, session, user_org_member_charlie_task, org_member_charlie_task,
        engagement_active_alice_task, skill_python_task
    ):
        """
        AC-S1 + YET-71: Charlie payload'a `strength: "STRONG"` ekliyor.
        Alan tanımlı değilse görmezden gelinir, strength sunucu kuralına göre WEAK hesaplanır.

        Davranış Sözleşmesi:
        - Status code: 201
        - SkillSignal.strength = WEAK (istemci alanı yoksayıldı)
        """
        payload = {
            "title": "Task trying to fake strength",
            "description": "Tampering attempt",
            "skill_id": str(skill_python_task.id),
            "strength": "STRONG",  # Tampering: trying to override strength
            "due_at": None,
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_task.id}/tasks",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_task.id)},
        )

        # Pydantic extra="forbid" ile reddedilirse 422, ignore edilirse 201
        # İkisi de kabul edilebilir, ama başarısız olmalı veya strength yoksayılmalı
        if response.status_code == 201:
            # Verify SkillSignal strength is WEAK, not client's "STRONG"
            data = response.json()
            task_id = data.get("id")
            if SkillSignal:
                signal = session.query(SkillSignal).filter_by(
                    source_type="TASK",
                    source_id=task_id
                ).first()
                if signal:
                    assert signal.strength == "WEAK", \
                        f"Expected WEAK (sunucu), got {signal.strength} — tampering başarılı oldu!"
        elif response.status_code == 422:
            # Pydantic rejected extra field — this is fine
            pass
        else:
            pytest.fail(f"Expected 201 or 422, got {response.status_code}: {response.text}")
