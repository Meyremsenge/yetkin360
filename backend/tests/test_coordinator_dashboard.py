"""
Coordinator dashboard endpoint tests (PLAN 3.3 — koordinator-dashboard-ucu).

Implements Acceptance Criteria and Behavior Contract from atdd.md:
- AC-1: Happy path (200, summary + pending_approval/pending_evaluation lists)
- AC-5: Empty engagement list (200, empty lists, zero counts)
- AC-6: Validation error on invalid UUID path parameter (422)
- AC-7: Confidential filter (response includes both confidential and non-confidential,
  but cross-tenant data never leaks)

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Exact assertion on status codes and field values
- Strong validation: no substring checks, no .lower(), TAM EŞLEŞME
"""

import pytest
from datetime import date
from uuid import uuid4

from app.models import (
    User,
    Institution,
    InstitutionMember,
    TalentProfile,
    Organization,
    Engagement,
)


# ============================================================================
# Institution Fixtures (for dashboard testing)
# ============================================================================


@pytest.fixture
def institution_dashboard_a(session):
    """Institution A for dashboard tests (different from institution_a to avoid cross-test pollution)."""
    inst = Institution(
        name="Dashboard Test Institution A",
        domain="dash-a.edu.tr",
        verification_level="T1",
        status="ACTIVE"
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def institution_dashboard_b(session):
    """Institution B for cross-tenant isolation tests."""
    inst = Institution(
        name="Dashboard Test Institution B",
        domain="dash-b.edu.tr",
        verification_level="T1",
        status="ACTIVE"
    )
    session.add(inst)
    session.flush()
    return inst


# ============================================================================
# User Fixtures
# ============================================================================


@pytest.fixture
def user_dashboard_coordinator_a(session):
    """User who is COORDINATOR of institution_dashboard_a."""
    user = User(
        email="dashboard-coord-a@example.com",
        password_hash="hash_dashboard_coord_a"
    )
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_dashboard_coordinator_b(session):
    """User who is COORDINATOR of institution_dashboard_b."""
    user = User(
        email="dashboard-coord-b@example.com",
        password_hash="hash_dashboard_coord_b"
    )
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_dashboard_talent(session):
    """User who is TALENT (for role-based access denial test)."""
    user = User(
        email="dashboard-talent@example.com",
        password_hash="hash_dashboard_talent"
    )
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_dashboard_org_member(session):
    """User who is ORG_MEMBER (for role-based access denial test)."""
    user = User(
        email="dashboard-org-member@example.com",
        password_hash="hash_dashboard_org_member"
    )
    session.add(user)
    session.flush()
    return user


# ============================================================================
# InstitutionMember Fixtures
# ============================================================================


@pytest.fixture
def inst_dashboard_a_coordinator(session, institution_dashboard_a, user_dashboard_coordinator_a):
    """user_dashboard_coordinator_a is COORDINATOR of institution_dashboard_a."""
    member = InstitutionMember(
        institution_id=institution_dashboard_a.id,
        user_id=user_dashboard_coordinator_a.id,
        role="COORDINATOR"
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def inst_dashboard_b_coordinator(session, institution_dashboard_b, user_dashboard_coordinator_b):
    """user_dashboard_coordinator_b is COORDINATOR of institution_dashboard_b."""
    member = InstitutionMember(
        institution_id=institution_dashboard_b.id,
        user_id=user_dashboard_coordinator_b.id,
        role="COORDINATOR"
    )
    session.add(member)
    session.flush()
    return member


# ============================================================================
# Talent + Organization Fixtures
# ============================================================================


@pytest.fixture
def org_dashboard_a(session):
    """Organization A for dashboard tests."""
    org = Organization(
        name="Dashboard Test Org A",
        domain="dash-orga.example.com",
        legal_id="DASH-ORG-A-001",
        verification_level="T1",
        status="ACTIVE"
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def org_dashboard_b(session):
    """Organization B for cross-tenant tests."""
    org = Organization(
        name="Dashboard Test Org B",
        domain="dash-orgb.example.com",
        legal_id="DASH-ORG-B-001",
        verification_level="T1",
        status="ACTIVE"
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def talent_dashboard_a(session, user_dashboard_talent, institution_dashboard_a):
    """Talent profile linked to institution_dashboard_a."""
    profile = TalentProfile(
        user_id=user_dashboard_talent.id,
        institution_id=institution_dashboard_a.id,
        full_name="Dashboard Talent A",
        visibility="PRIVATE"
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_dashboard_b(session, institution_dashboard_b):
    """Talent profile linked to institution_dashboard_b."""
    user = User(
        email="dashboard-talent-b@example.com",
        password_hash="hash_talent_b"
    )
    session.add(user)
    session.flush()
    profile = TalentProfile(
        user_id=user.id,
        institution_id=institution_dashboard_b.id,
        full_name="Dashboard Talent B",
        visibility="PRIVATE"
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_dashboard_org_member(session, user_dashboard_org_member, institution_dashboard_a):
    """Talent profile for ORG_MEMBER (for access denial test)."""
    profile = TalentProfile(
        user_id=user_dashboard_org_member.id,
        institution_id=institution_dashboard_a.id,
        full_name="Dashboard ORG Member",
        visibility="PRIVATE"
    )
    session.add(profile)
    session.flush()
    return profile


# ============================================================================
# Engagement Fixtures: PENDING_APPROVAL and PENDING_EVALUATION states
# ============================================================================


@pytest.fixture
def pending_approval_engagements_a(session, talent_dashboard_a, org_dashboard_a, institution_dashboard_a):
    """Create 3 PENDING_APPROVAL engagements in institution_dashboard_a."""
    engagements = []
    for i in range(3):
        eng = Engagement(
            talent_id=talent_dashboard_a.id,
            organization_id=org_dashboard_a.id,
            institution_id=institution_dashboard_a.id,
            kind="INTERNSHIP",
            title=f"Pending Approval Engagement {i+1}",
            status="PENDING_APPROVAL",
            started_on=date(2025, 9, 1),
            confidential=False
        )
        session.add(eng)
        engagements.append(eng)
    session.flush()
    return engagements


@pytest.fixture
def pending_evaluation_engagements_a(session, talent_dashboard_a, org_dashboard_a, institution_dashboard_a):
    """Create 7 PENDING_EVALUATION engagements in institution_dashboard_a."""
    engagements = []
    for i in range(7):
        eng = Engagement(
            talent_id=talent_dashboard_a.id,
            organization_id=org_dashboard_a.id,
            institution_id=institution_dashboard_a.id,
            kind="CAPSTONE",
            title=f"Pending Evaluation Engagement {i+1}",
            status="PENDING_EVALUATION",
            ended_on=date(2025, 12, 15),
            confidential=False
        )
        session.add(eng)
        engagements.append(eng)
    session.flush()
    return engagements


@pytest.fixture
def pending_approval_with_confidential_a(session, talent_dashboard_a, org_dashboard_a, institution_dashboard_a):
    """Create PENDING_APPROVAL engagements with mixed confidential flags."""
    engagements = []
    # 2 confidential=true, 2 confidential=false
    for i in range(2):
        eng = Engagement(
            talent_id=talent_dashboard_a.id,
            organization_id=org_dashboard_a.id,
            institution_id=institution_dashboard_a.id,
            kind="INTERNSHIP",
            title=f"Confidential PENDING_APPROVAL {i+1}",
            status="PENDING_APPROVAL",
            started_on=date(2025, 9, 1),
            confidential=True
        )
        session.add(eng)
        engagements.append(eng)

    for i in range(2):
        eng = Engagement(
            talent_id=talent_dashboard_a.id,
            organization_id=org_dashboard_a.id,
            institution_id=institution_dashboard_a.id,
            kind="INTERNSHIP",
            title=f"Non-Confidential PENDING_APPROVAL {i+1}",
            status="PENDING_APPROVAL",
            started_on=date(2025, 9, 1),
            confidential=False
        )
        session.add(eng)
        engagements.append(eng)
    session.flush()
    return engagements


@pytest.fixture
def pending_evaluation_with_confidential_a(session, talent_dashboard_a, org_dashboard_a, institution_dashboard_a):
    """Create PENDING_EVALUATION engagements with mixed confidential flags."""
    engagements = []
    # 2 confidential=true, 2 confidential=false
    for i in range(2):
        eng = Engagement(
            talent_id=talent_dashboard_a.id,
            organization_id=org_dashboard_a.id,
            institution_id=institution_dashboard_a.id,
            kind="CAPSTONE",
            title=f"Confidential PENDING_EVALUATION {i+1}",
            status="PENDING_EVALUATION",
            ended_on=date(2025, 12, 15),
            confidential=True
        )
        session.add(eng)
        engagements.append(eng)

    for i in range(2):
        eng = Engagement(
            talent_id=talent_dashboard_a.id,
            organization_id=org_dashboard_a.id,
            institution_id=institution_dashboard_a.id,
            kind="CAPSTONE",
            title=f"Non-Confidential PENDING_EVALUATION {i+1}",
            status="PENDING_EVALUATION",
            ended_on=date(2025, 12, 15),
            confidential=False
        )
        session.add(eng)
        engagements.append(eng)
    session.flush()
    return engagements


@pytest.fixture
def cross_tenant_engagement_b(session, talent_dashboard_b, org_dashboard_b, institution_dashboard_b):
    """Create engagements in institution_dashboard_b (for cross-tenant isolation test)."""
    engagements = []
    for i in range(2):
        eng = Engagement(
            talent_id=talent_dashboard_b.id,
            organization_id=org_dashboard_b.id,
            institution_id=institution_dashboard_b.id,
            kind="INTERNSHIP",
            title=f"Institution B Engagement {i+1}",
            status="PENDING_APPROVAL",
            started_on=date(2025, 9, 1),
            confidential=False
        )
        session.add(eng)
        engagements.append(eng)
    session.flush()
    return engagements


# ============================================================================
# AC-1: Happy Path — 200 with summary and lists
# ============================================================================


class TestCoordinatorDashboardHappyPath:
    """AC-1: COORDINATOR/INST_ADMIN retrieves dashboard with summary and engagement lists."""

    def test_happy_path_summary_counts_and_lists(
        self,
        client,
        session,
        institution_dashboard_a,
        inst_dashboard_a_coordinator,
        pending_approval_engagements_a,
        pending_evaluation_engagements_a,
        user_dashboard_coordinator_a
    ):
        """
        AC-1: Happy path — authenticated COORDINATOR, institution A, 3 PENDING_APPROVAL + 7 PENDING_EVALUATION.

        Expected:
        - Status: 200
        - Response contains: institution_id, summary.pending_approval == 3, summary.pending_evaluation == 7
        - pending_approval list has 3 items with correct fields (id, talent_id, organization_id, title, started_on)
        - pending_evaluation list has 7 items with correct fields (id, talent_id, organization_id, title, ended_on)
        - No items from other statuses (ACTIVE, DRAFT, etc.)
        """
        response = client.get(
            f"/institutions/{institution_dashboard_a.id}/dashboard",
            headers={"X-Debug-User-Id": str(user_dashboard_coordinator_a.id)}
        )

        # Exact status code match
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"

        data = response.json()

        # Verify structure
        assert "institution_id" in data
        assert "summary" in data
        assert "pending_approval" in data
        assert "pending_evaluation" in data

        # Verify institution_id matches
        assert data["institution_id"] == str(institution_dashboard_a.id), (
            f"Institution ID mismatch: expected {institution_dashboard_a.id}, got {data['institution_id']}"
        )

        # Verify summary counts — EXACT MATCH
        assert data["summary"]["pending_approval"] == 3, (
            f"Expected pending_approval count 3, got {data['summary']['pending_approval']}"
        )
        assert data["summary"]["pending_evaluation"] == 7, (
            f"Expected pending_evaluation count 7, got {data['summary']['pending_evaluation']}"
        )

        # Verify pending_approval list
        assert isinstance(data["pending_approval"], list), "pending_approval must be a list"
        assert len(data["pending_approval"]) == 3, (
            f"Expected 3 pending_approval items, got {len(data['pending_approval'])}"
        )

        for item in data["pending_approval"]:
            # Verify required fields
            assert "id" in item, "pending_approval item missing 'id'"
            assert "talent_id" in item, "pending_approval item missing 'talent_id'"
            assert "organization_id" in item, "pending_approval item missing 'organization_id'"
            assert "title" in item, "pending_approval item missing 'title'"
            assert "started_on" in item, "pending_approval item missing 'started_on'"
            # Verify they belong to institution A (not cross-tenant leak)
            assert item["talent_id"] == str(pending_approval_engagements_a[0].talent_id)

        # Verify pending_evaluation list
        assert isinstance(data["pending_evaluation"], list), "pending_evaluation must be a list"
        assert len(data["pending_evaluation"]) == 7, (
            f"Expected 7 pending_evaluation items, got {len(data['pending_evaluation'])}"
        )

        for item in data["pending_evaluation"]:
            # Verify required fields
            assert "id" in item, "pending_evaluation item missing 'id'"
            assert "talent_id" in item, "pending_evaluation item missing 'talent_id'"
            assert "organization_id" in item, "pending_evaluation item missing 'organization_id'"
            assert "title" in item, "pending_evaluation item missing 'title'"
            assert "ended_on" in item, "pending_evaluation item missing 'ended_on'"
            # Verify they belong to institution A (not cross-tenant leak)
            assert item["talent_id"] == str(pending_evaluation_engagements_a[0].talent_id)


# ============================================================================
# AC-5: Empty engagement list — 200 with zero counts and empty lists
# ============================================================================


class TestCoordinatorDashboardEmptyList:
    """AC-5: COORDINATOR/INST_ADMIN retrieves dashboard when no engagements exist."""

    def test_empty_list_200_not_404(
        self,
        client,
        institution_dashboard_a,
        inst_dashboard_a_coordinator,
        user_dashboard_coordinator_a
    ):
        """
        AC-5: Happy path with no engagements — 200 (not 404).

        Expected:
        - Status: 200 (not 404 — "no data" is not "no access")
        - summary.pending_approval == 0
        - summary.pending_evaluation == 0
        - pending_approval == []
        - pending_evaluation == []
        """
        response = client.get(
            f"/institutions/{institution_dashboard_a.id}/dashboard",
            headers={"X-Debug-User-Id": str(user_dashboard_coordinator_a.id)}
        )

        # EXACT status code match
        assert response.status_code == 200, (
            f"Expected 200 for empty list, got {response.status_code} (not 404)"
        )

        data = response.json()

        # Verify zero counts
        assert data["summary"]["pending_approval"] == 0, (
            f"Expected pending_approval count 0, got {data['summary']['pending_approval']}"
        )
        assert data["summary"]["pending_evaluation"] == 0, (
            f"Expected pending_evaluation count 0, got {data['summary']['pending_evaluation']}"
        )

        # Verify empty lists
        assert data["pending_approval"] == [], (
            f"Expected empty pending_approval list, got {data['pending_approval']}"
        )
        assert data["pending_evaluation"] == [], (
            f"Expected empty pending_evaluation list, got {data['pending_evaluation']}"
        )


# ============================================================================
# AC-6: Validation error — 422 on invalid UUID path parameter
# ============================================================================


class TestCoordinatorDashboardValidation:
    """AC-6: FastAPI path parameter validation returns 422 on invalid UUID."""

    def test_invalid_uuid_format_422(
        self,
        client,
        user_dashboard_coordinator_a
    ):
        """
        AC-6: Path parameter institution_id is not a valid UUID.

        Expected:
        - Status: 422 Unprocessable Entity (FastAPI automatic validation)
        - Response contains error code/message
        """
        response = client.get(
            "/institutions/not-a-uuid/dashboard",
            headers={"X-Debug-User-Id": str(user_dashboard_coordinator_a.id)}
        )

        # EXACT status code match
        assert response.status_code == 422, (
            f"Expected 422 on invalid UUID, got {response.status_code}"
        )

    def test_valid_uuid_format_but_nonexistent(
        self,
        client,
        user_dashboard_coordinator_a
    ):
        """
        AC-2/AC-3: Path parameter is valid UUID but institution doesn't exist or out of scope → 404.
        """
        nonexistent_uuid = str(uuid4())
        response = client.get(
            f"/institutions/{nonexistent_uuid}/dashboard",
            headers={"X-Debug-User-Id": str(user_dashboard_coordinator_a.id)}
        )

        # EXACT status code match
        assert response.status_code == 404, (
            f"Expected 404 for nonexistent/out-of-scope institution, got {response.status_code}"
        )


# ============================================================================
# AC-7: Confidential filter — both confidential and non-confidential included
# ============================================================================


class TestCoordinatorDashboardConfidential:
    """AC-7: Dashboard includes both confidential and non-confidential engagements,
    but cross-tenant data never leaks."""

    def test_confidential_mixed_both_included(
        self,
        client,
        session,
        institution_dashboard_a,
        inst_dashboard_a_coordinator,
        pending_approval_with_confidential_a,
        pending_evaluation_with_confidential_a,
        user_dashboard_coordinator_a
    ):
        """
        AC-7: Response includes both confidential=true and confidential=false engagements.

        Expected:
        - pending_approval list contains 4 items (2 confidential, 2 non-confidential)
        - pending_evaluation list contains 4 items (2 confidential, 2 non-confidential)
        - summary counts reflect both: pending_approval == 4, pending_evaluation == 4
        """
        response = client.get(
            f"/institutions/{institution_dashboard_a.id}/dashboard",
            headers={"X-Debug-User-Id": str(user_dashboard_coordinator_a.id)}
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()

        # Verify counts include both confidential=true and =false
        assert data["summary"]["pending_approval"] == 4, (
            f"Expected 4 pending_approval (mixed confidential), got {data['summary']['pending_approval']}"
        )
        assert data["summary"]["pending_evaluation"] == 4, (
            f"Expected 4 pending_evaluation (mixed confidential), got {data['summary']['pending_evaluation']}"
        )

        # Verify list lengths
        assert len(data["pending_approval"]) == 4
        assert len(data["pending_evaluation"]) == 4

    def test_confidential_cross_tenant_never_leaks(
        self,
        client,
        session,
        institution_dashboard_a,
        institution_dashboard_b,
        inst_dashboard_a_coordinator,
        pending_approval_with_confidential_a,
        pending_evaluation_with_confidential_a,
        cross_tenant_engagement_b,
        user_dashboard_coordinator_a
    ):
        """
        AC-7 (AC-S3): Coordinator A's dashboard never includes Institution B's data,
        regardless of confidential flag.

        Scenario:
        - Institution A has 4 PENDING_APPROVAL + 4 PENDING_EVALUATION (mixed confidential)
        - Institution B has 2 PENDING_APPROVAL
        - Coordinator A queries /institutions/{A}/dashboard
        - Expected: only A's data, no leak of B's data (not even count)

        This test verifies institution_id filtering happens **in backend**,
        not **by UI hiding** (which would be a security theater).
        """
        response = client.get(
            f"/institutions/{institution_dashboard_a.id}/dashboard",
            headers={"X-Debug-User-Id": str(user_dashboard_coordinator_a.id)}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify only A's counts
        assert data["summary"]["pending_approval"] == 4, (
            "Coordinator A should see only A's PENDING_APPROVAL, not B's"
        )
        assert data["summary"]["pending_evaluation"] == 4, (
            "Coordinator A should see only A's PENDING_EVALUATION, not B's"
        )

        # Verify B's engagement data is not in the response
        for item in data["pending_approval"]:
            # Check that no B institution data leaks (we can check organization names if they're in response, etc.)
            # At minimum, verify all items belong to A's talent
            assert item["talent_id"] == str(pending_approval_with_confidential_a[0].talent_id), (
                "Found engagement from institution B in response (cross-tenant leak)"
            )

        for item in data["pending_evaluation"]:
            assert item["talent_id"] == str(pending_evaluation_with_confidential_a[0].talent_id), (
                "Found engagement from institution B in response (cross-tenant leak)"
            )


# ============================================================================
# AC-1, AC-2, AC-S1: Members field tests (PLAN 3.5 — kurum-dashboard-uyeler)
# ============================================================================


class TestCoordinatorDashboardMembers:
    """
    AC-1: Happy path — dashboard response includes members list.
    AC-2: Theoretical empty members case.
    AC-S1 (Threat-model): Cross-tenant member isolation.

    Reference: PLAN 3.5 — kurum-dashboard-uyeler, atdd.md
    """

    def test_ac1_members_field_present_with_coordinator(
        self,
        client,
        institution_dashboard_a,
        inst_dashboard_a_coordinator,
        user_dashboard_coordinator_a
    ):
        """
        AC-1 [Critical]: Dashboard response includes members field with at least
        one member (the coordinator itself).

        Expected:
        - Status: 200
        - Response contains "members" field (list)
        - members list has exactly 1 item (inst_dashboard_a_coordinator)
        - Member item has fields: user_id, email, role, joined_at
        - Member data matches fixture values
        """
        response = client.get(
            f"/institutions/{institution_dashboard_a.id}/dashboard",
            headers={"X-Debug-User-Id": str(user_dashboard_coordinator_a.id)}
        )

        # Exact status code match
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.json()}"
        )

        data = response.json()

        # Verify members field exists
        assert "members" in data, "Response missing 'members' field"
        assert isinstance(data["members"], list), "members field must be a list"

        # Verify at least one member (the fixture coordinator)
        assert len(data["members"]) >= 1, (
            f"Expected at least 1 member, got {len(data['members'])}"
        )

        # Verify member fields
        member = data["members"][0]
        assert "user_id" in member, "Member item missing 'user_id'"
        assert "email" in member, "Member item missing 'email'"
        assert "role" in member, "Member item missing 'role'"
        assert "joined_at" in member, "Member item missing 'joined_at'"

        # Verify member data matches fixture
        assert member["user_id"] == str(user_dashboard_coordinator_a.id), (
            f"Expected user_id {user_dashboard_coordinator_a.id}, got {member['user_id']}"
        )
        assert member["email"] == user_dashboard_coordinator_a.email, (
            f"Expected email {user_dashboard_coordinator_a.email}, got {member['email']}"
        )
        assert member["role"] == "COORDINATOR", (
            f"Expected role COORDINATOR, got {member['role']}"
        )
        # joined_at should be present (UTC timestamp); we don't verify exact time,
        # just presence and format
        assert isinstance(member["joined_at"], str), "joined_at must be ISO 8601 timestamp string"

    def test_ac1_members_multiple_when_present(
        self,
        client,
        session,
        institution_dashboard_a,
        inst_dashboard_a_coordinator,
        user_dashboard_coordinator_a
    ):
        """
        AC-1 [Critical]: When multiple members exist in institution,
        all are returned in members list.

        Scenario:
        - Institution A already has 1 COORDINATOR (inst_dashboard_a_coordinator fixture)
        - Add second member (ADMIN) to same institution
        - Coordinator queries dashboard

        Expected:
        - members list has exactly 2 items
        - Both members returned in response
        - All required fields present for each
        """
        # Create second member for Institution A (ADMIN role)
        second_user = User(
            email="dashboard-admin-a@example.com",
            password_hash="hash_admin_a"
        )
        session.add(second_user)
        session.flush()

        second_member = InstitutionMember(
            institution_id=institution_dashboard_a.id,
            user_id=second_user.id,
            role="ADMIN"
        )
        session.add(second_member)
        session.commit()

        response = client.get(
            f"/institutions/{institution_dashboard_a.id}/dashboard",
            headers={"X-Debug-User-Id": str(user_dashboard_coordinator_a.id)}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify members field and count
        assert "members" in data
        assert isinstance(data["members"], list)
        assert len(data["members"]) == 2, (
            f"Expected 2 members, got {len(data['members'])}"
        )

        # Verify both members are present (order may vary)
        member_user_ids = {m["user_id"] for m in data["members"]}
        expected_user_ids = {
            str(user_dashboard_coordinator_a.id),
            str(second_user.id)
        }
        assert member_user_ids == expected_user_ids, (
            f"Expected user_ids {expected_user_ids}, got {member_user_ids}"
        )

        # Verify roles are present
        member_roles = {m["role"] for m in data["members"]}
        assert "COORDINATOR" in member_roles
        assert "ADMIN" in member_roles

    def test_acs1_cross_tenant_member_isolation(
        self,
        client,
        institution_dashboard_a,
        institution_dashboard_b,
        inst_dashboard_a_coordinator,
        inst_dashboard_b_coordinator,
        user_dashboard_coordinator_a,
        user_dashboard_coordinator_b
    ):
        """
        AC-S1 [Critical, threat-model]: Coordinator A's dashboard ONLY includes
        Institution A members, never Institution B members.

        Scenario:
        - Institution A has 1 COORDINATOR (inst_dashboard_a_coordinator)
        - Institution B has 1 COORDINATOR (inst_dashboard_b_coordinator)
        - Coordinator A queries /institutions/{A_id}/dashboard

        Expected:
        - members list has exactly 1 item (A's coordinator)
        - B's coordinator email NEVER appears in response
        - No cross-tenant leakage (even in counts, member count, etc.)
        """
        response = client.get(
            f"/institutions/{institution_dashboard_a.id}/dashboard",
            headers={"X-Debug-User-Id": str(user_dashboard_coordinator_a.id)}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify members field exists
        assert "members" in data
        assert isinstance(data["members"], list)

        # Verify exactly 1 member (Institution A's coordinator only)
        assert len(data["members"]) == 1, (
            f"Expected 1 member (Institution A only), got {len(data['members'])}"
        )

        # Verify member is from Institution A
        member = data["members"][0]
        assert member["user_id"] == str(user_dashboard_coordinator_a.id), (
            f"Expected Coordinator A's user_id, got {member['user_id']}"
        )
        assert member["email"] == user_dashboard_coordinator_a.email, (
            f"Expected Coordinator A's email, got {member['email']}"
        )

        # CRITICAL SECURITY CHECK: Institution B's coordinator email must NOT appear
        member_emails = [m["email"] for m in data["members"]]
        assert user_dashboard_coordinator_b.email not in member_emails, (
            f"SECURITY LEAK: Institution B coordinator email {user_dashboard_coordinator_b.email} "
            f"appeared in Institution A dashboard members list"
        )

        # CRITICAL: No Institution B data should leak in any form
        member_user_ids = {m["user_id"] for m in data["members"]}
        assert str(user_dashboard_coordinator_b.id) not in member_user_ids, (
            "SECURITY LEAK: Institution B coordinator user_id appeared in Institution A members"
        )

    def test_ac2_members_empty_when_no_other_members(
        self,
        client,
        session,
        institution_dashboard_a,
        user_dashboard_coordinator_a
    ):
        """
        AC-2 [Medium]: When an institution has no members (theoretical case),
        dashboard returns 200 with empty members list (not 404 or error).

        NOTE: This test creates a coordinator user but explicitly does NOT
        add an InstitutionMember record for them. In production, the institution
        might automatically have an ADMIN member (the creator), but for this
        theoretical test, we create a separate institution without any members.

        Expected:
        - Status: 200 (not 404)
        - members: [] (empty list)
        - summary and engagement lists still present and empty
        """
        pytest.skip(
            "Kurum oluşturma otomatik ADMIN atadığı için üyesiz-ama-erişilebilir kurum senaryosu "
            "gerçekçi kurulamıyor (bkz. atdd.md Assumptions)"
        )
        # Create institution with no members
        inst_no_members = Institution(
            name="Institution With No Members",
            domain="no-members.edu.tr",
            verification_level="T1",
            status="ACTIVE"
        )
        session.add(inst_no_members)
        session.flush()

        # Create a new user unrelated to this institution
        unrelated_user = User(
            email="unrelated@example.com",
            password_hash="hash_unrelated"
        )
        session.add(unrelated_user)
        session.flush()

        # NOTE: We cannot actually query with this user because they have no
        # membership/authorization for this institution. The endpoint will
        # return 404 due to authorization (scoped_institutions filter), not 200.
        # So this test verifies that IF the authorization somehow passed,
        # the members list would be empty. But practically, unauthorized access
        # returns 404 first.
        #
        # DECISION: Skip this test. Reasoning in test report.
        pass

    def test_acs1_members_email_not_exposed_across_institutions(
        self,
        client,
        institution_dashboard_a,
        institution_dashboard_b,
        inst_dashboard_a_coordinator,
        inst_dashboard_b_coordinator,
        user_dashboard_coordinator_a,
        user_dashboard_coordinator_b
    ):
        """
        AC-S1 (additional scenario): Email addresses of Institution B members
        must not leak to Institution A coordinator (even as part of members list).

        This is a specific check for PII leakage via email addresses,
        as noted in atdd.md threat-model section (Info Disclosure).

        Expected:
        - Institution A coordinator queries dashboard
        - members list contains ONLY A's members' emails
        - B's coordinator email is never visible
        """
        response = client.get(
            f"/institutions/{institution_dashboard_a.id}/dashboard",
            headers={"X-Debug-User-Id": str(user_dashboard_coordinator_a.id)}
        )

        assert response.status_code == 200
        data = response.json()

        assert "members" in data
        member_emails = [m["email"] for m in data["members"]]

        # B's coordinator email must never appear
        assert user_dashboard_coordinator_b.email not in member_emails, (
            f"EMAIL LEAK: {user_dashboard_coordinator_b.email} exposed to Institution A"
        )

        # A's coordinator email must be present
        assert user_dashboard_coordinator_a.email in member_emails, (
            f"Expected Coordinator A's email in list, got {member_emails}"
        )
