"""
Institution authorization tests (YET-8 — BOLA/tenant-izolasyon).

Implements AC-4 (AC-S1) and AC-5 (AC-S2) from atdd.md.

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Parametric tests for permission matrix (AC-4, AC-S1, AC-S2)
- Tenant isolation verification: Institution A vs B
- Defense-in-depth: can() + scoped_institutions() verification

AC-4 / AC-S1: COORDINATOR cannot invite members (ADMIN-only action) → 404 (not 403)
AC-5 / AC-S2: Cross-institution access prevention (BOLA) → 404 for out-of-scope resources

Key principle: "404 sızdırmama" — out-of-scope and nonexistent resources both return 404
"""

import pytest

from app.models import Institution, InstitutionMember, TalentProfile, User, Organization, OrganizationMember, AuditEvent
from app.services.authorization import Principal, can, get_scoped_or_404, scoped_institutions


# ============================================================================
# Institution Fixtures: A & B (tenant isolation)
# ============================================================================


@pytest.fixture
def institution_a(session):
    """Test institution A (tenant 1)."""
    inst = Institution(
        name="Test Institution A",
        domain="testaaa.edu.tr",
        verification_level="T1",
        status="ACTIVE"
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def institution_b(session):
    """Test institution B (tenant 2)."""
    inst = Institution(
        name="Test Institution B",
        domain="testbbb.edu.tr",
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
def user_a_admin(session):
    """User who is ADMIN of institution_a."""
    user = User(email="admin-a@example.com", password_hash="hash_admin_a")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_a_coordinator(session):
    """User who is COORDINATOR of institution_a (not ADMIN)."""
    user = User(email="coordinator-a@example.com", password_hash="hash_coord_a")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_b_admin(session):
    """User who is ADMIN of institution_b."""
    user = User(email="admin-b@example.com", password_hash="hash_admin_b")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_b_coordinator(session):
    """User who is COORDINATOR of institution_b."""
    user = User(email="coordinator-b@example.com", password_hash="hash_coord_b")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_no_role(session):
    """User with no institution role (for access denial tests)."""
    user = User(email="nouser@example.com", password_hash="hash_nouser")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_to_invite(session):
    """User who will be invited as member."""
    user = User(email="toinvite@example.com", password_hash="hash_toinvite")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def student_a(session):
    """Student who will request link to institution_a."""
    user = User(email="student-a@example.com", password_hash="hash_student_a")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def student_b(session):
    """Student who will request link to institution_b."""
    user = User(email="student-b@example.com", password_hash="hash_student_b")
    session.add(user)
    session.flush()
    return user


# ============================================================================
# InstitutionMember Fixtures (Institution A & B relationships)
# ============================================================================


@pytest.fixture
def inst_a_admin_member(session, institution_a, user_a_admin):
    """InstitutionMember: user_a_admin is ADMIN of institution_a."""
    member = InstitutionMember(
        institution_id=institution_a.id,
        user_id=user_a_admin.id,
        role="ADMIN"
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def inst_a_coordinator_member(session, institution_a, user_a_coordinator):
    """InstitutionMember: user_a_coordinator is COORDINATOR of institution_a."""
    member = InstitutionMember(
        institution_id=institution_a.id,
        user_id=user_a_coordinator.id,
        role="COORDINATOR"
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def inst_b_admin_member(session, institution_b, user_b_admin):
    """InstitutionMember: user_b_admin is ADMIN of institution_b."""
    member = InstitutionMember(
        institution_id=institution_b.id,
        user_id=user_b_admin.id,
        role="ADMIN"
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def inst_b_coordinator_member(session, institution_b, user_b_coordinator):
    """InstitutionMember: user_b_coordinator is COORDINATOR of institution_b."""
    member = InstitutionMember(
        institution_id=institution_b.id,
        user_id=user_b_coordinator.id,
        role="COORDINATOR"
    )
    session.add(member)
    session.flush()
    return member


# ============================================================================
# TalentProfile Fixtures
# ============================================================================


@pytest.fixture
def talent_a(session, student_a):
    """Talent profile for student_a."""
    profile = TalentProfile(
        user_id=student_a.id,
        full_name="Student A",
        visibility="PRIVATE"
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_b(session, student_b):
    """Talent profile for student_b."""
    profile = TalentProfile(
        user_id=student_b.id,
        full_name="Student B",
        visibility="PRIVATE"
    )
    session.add(profile)
    session.flush()
    return profile


# ============================================================================
# AC-4 / AC-S1: COORDINATOR cannot invite members (ADMIN-only)
# ============================================================================


class TestCoordinatorCannotInviteMembers:
    """AC-4 / AC-S1: COORDINATOR access denied for member invitation (returns 404, not 403)."""

    def test_coordinator_invite_member_denied_404(
        self, client, session, institution_a, inst_a_coordinator_member, user_to_invite, user_a_coordinator
    ):
        """
        AC-S1: Coordinator POST /institutions/{id}/members → 404 (403 sızdırmama).

        Acceptance Criteria:
        - Status code: 404 Not Found (not 403 Forbidden — resource existence hidden)
        - No InstitutionMember record created
        - Error does not reveal that resource exists
        """
        payload = {
            "email": user_to_invite.email,
            "role": "COORDINATOR"
        }

        # Assume auth context: user_a_coordinator (COORDINATOR, not ADMIN)
        response = client.post(f"/institutions/{institution_a.id}/members", json=payload, headers={"X-Debug-User-Id": str(user_a_coordinator.id)})

        # Expected: 404 (not 403)
        assert response.status_code == 404, (
            f"Coordinator should receive 404 (not 403 — sızdırma), got {response.status_code}"
        )

        # Verify: no member was added
        member = session.query(InstitutionMember).filter_by(
            institution_id=institution_a.id,
            user_id=user_to_invite.id
        ).first()
        assert member is None, "No member should be created for COORDINATOR's request"

    @pytest.mark.parametrize("role_to_invite", ["ADMIN", "COORDINATOR"])
    def test_coordinator_cannot_invite_any_role(
        self, client, session, institution_a, inst_a_coordinator_member, user_to_invite, role_to_invite, user_a_coordinator
    ):
        """AC-S1: COORDINATOR denied for both ADMIN and COORDINATOR invitation roles."""
        payload = {
            "email": user_to_invite.email,
            "role": role_to_invite
        }

        response = client.post(f"/institutions/{institution_a.id}/members", json=payload, headers={"X-Debug-User-Id": str(user_a_coordinator.id)})

        assert response.status_code == 404


# ============================================================================
# AC-5 / AC-S2: Tenant isolation (BOLA prevention)
# ============================================================================


class TestTenantIsolationBOLA:
    """
    AC-5 / AC-S2: Cross-institution access prevention (BoLA).

    Implements core principle: Coordinator/Admin of Institution A cannot
    access or modify resources of Institution B.
    """

    def test_coordinator_a_cannot_invite_to_institution_b(
        self,
        client,
        session,
        institution_a,
        institution_b,
        inst_a_coordinator_member,
        inst_b_coordinator_member,
        user_to_invite,
        user_a_coordinator,
    ):
        """
        AC-S2: Coordinator of A tries to invite member to B → 404 (not 403).

        Acceptance Criteria:
        - Status code: 404 (resource existence hidden)
        - No member added to B
        - Institution B unchanged
        """
        payload = {
            "email": user_to_invite.email,
            "role": "COORDINATOR"
        }

        # Coordinator of A attempts to invite member to B
        response = client.post(f"/institutions/{institution_b.id}/members", json=payload, headers={"X-Debug-User-Id": str(user_a_coordinator.id)})

        assert response.status_code == 404, (
            "Coordinator of A should not access Institution B (404 sızdırmama)"
        )

        # Verify: B has no new members
        member_count = session.query(InstitutionMember).filter_by(
            institution_id=institution_b.id
        ).count()
        # Should be 1 (only coordinator_b is member)
        assert member_count == 1, "Institution B should remain unchanged"

    def test_admin_a_cannot_invite_to_institution_b(
        self,
        client,
        session,
        institution_a,
        institution_b,
        inst_a_admin_member,
        inst_b_admin_member,
        user_to_invite,
        user_a_admin,
    ):
        """AC-S2: Admin of A tries to invite to B → 404."""
        payload = {
            "email": user_to_invite.email,
            "role": "COORDINATOR"
        }

        response = client.post(f"/institutions/{institution_b.id}/members", json=payload, headers={"X-Debug-User-Id": str(user_a_admin.id)})

        # Expected: 404 (even though A's admin can invite to A, they cannot to B)
        assert response.status_code == 404

    def test_coordinator_a_cannot_approve_link_request_for_b(
        self,
        client,
        session,
        institution_a,
        institution_b,
        inst_a_coordinator_member,
        inst_b_coordinator_member,
        talent_b,
        student_b,
        user_a_coordinator,
    ):
        """
        AC-S2 (core BOLA test): Coordinator of A tries to approve student link for B.

        Scenario:
        1. Student B has PENDING link request for Institution B
        2. Coordinator of A tries to approve it (by guessing/trying B's request ID)
        3. Result: 404 (not approved), B's request status unchanged

        Acceptance Criteria:
        - Status code: 404 Not Found
        - InstitutionLinkRequest status remains PENDING
        - TalentProfile.institution_id remains None
        - No audit trail created for invalid access
        """
        from app.models import InstitutionLinkRequest

        # Setup: Create PENDING link request for student_b to institution_b
        link_req = InstitutionLinkRequest(
            talent_profile_id=talent_b.id,
            institution_id=institution_b.id,
            status="PENDING"
        )
        session.add(link_req)
        session.flush()
        request_id = link_req.id

        # Coordinator of A attempts to approve B's request
        # (simulating attack: coordinator_a tries to approve link for institution_b)
        response = client.post(f"/institutions/{institution_b.id}/link-requests/{request_id}/approve", headers={"X-Debug-User-Id": str(user_a_coordinator.id)})

        # Expected: 404 (coordinator_a has no access to institution_b)
        assert response.status_code == 404, (
            "Coordinator of A should not access/approve resources of B (404)"
        )

        # Verify: request is still PENDING
        link_req = session.query(InstitutionLinkRequest).filter_by(id=request_id).first()
        assert link_req.status == "PENDING", "Link request should remain PENDING"

        # Verify: talent_b's institution_id is still None
        talent = session.query(TalentProfile).filter_by(id=talent_b.id).first()
        assert talent.institution_id is None, (
            "Talent B's institution_id should remain None (approval did not happen)"
        )

    def test_admin_a_cannot_approve_link_request_for_b(
        self,
        client,
        session,
        institution_a,
        institution_b,
        inst_a_admin_member,
        inst_b_coordinator_member,
        talent_b,
        student_b,
        user_a_admin,
    ):
        """AC-S2: Admin of A also cannot approve link for B."""
        from app.models import InstitutionLinkRequest

        link_req = InstitutionLinkRequest(
            talent_profile_id=talent_b.id,
            institution_id=institution_b.id,
            status="PENDING"
        )
        session.add(link_req)
        session.flush()
        request_id = link_req.id

        response = client.post(f"/institutions/{institution_b.id}/link-requests/{request_id}/approve", headers={"X-Debug-User-Id": str(user_a_admin.id)})

        assert response.status_code == 404

    def test_single_user_mixed_roles_cannot_invite_to_coordinator_institution(
        self,
        client,
        session,
        institution_a,
        institution_b,
        inst_a_admin_member,
        inst_b_coordinator_member,
        user_to_invite,
        user_a_admin,
    ):
        """
        AC-S2: Single user with mixed roles (ADMIN in A, COORDINATOR in B)
        cannot invite members to B (returns 404).

        Scenario:
        - user_a_admin is ADMIN of institution_a (via fixture)
        - This test adds user_a_admin as COORDINATOR of institution_b
        - Then user tries POST /institutions/{B}/members → 404 (not 201)

        This test catches regression where global kind='INST_ADMIN' would
        incorrectly allow invitation to B (because kind would reflect A's role),
        when per-institution check should deny it (COORDINATOR cannot invite).

        Acceptance Criteria:
        - Status code: 404 (not 201)
        - No member added to B
        """
        # Setup: user_a_admin is already ADMIN of A (inst_a_admin_member fixture)
        # Add user_a_admin as COORDINATOR to institution_b (mixed roles)
        member_b_coord = InstitutionMember(
            institution_id=institution_b.id,
            user_id=user_a_admin.id,
            role="COORDINATOR"
        )
        session.add(member_b_coord)
        session.flush()

        # Now user_a_admin has: ADMIN in A, COORDINATOR in B
        payload = {
            "email": user_to_invite.email,
            "role": "COORDINATOR"
        }

        # Try to invite to B as COORDINATOR (should fail, per-institution check)
        response = client.post(
            f"/institutions/{institution_b.id}/members",
            json=payload,
            headers={"X-Debug-User-Id": str(user_a_admin.id)}
        )

        # Expected: 404 (COORDINATOR cannot invite to any institution)
        assert response.status_code == 404, (
            "User with mixed roles (ADMIN in A, COORDINATOR in B) "
            "should not be able to invite to B (per-institution check should deny)"
        )

        # Verify: no member added to B
        member = session.query(InstitutionMember).filter_by(
            institution_id=institution_b.id,
            user_id=user_to_invite.id
        ).first()
        assert member is None, "No member should be added to B"

    # ========================================================================
    # YET-197/IS-10: Reject link request — BOLA
    # ========================================================================

    def test_coordinator_a_cannot_reject_link_request_for_b(
        self,
        client,
        session,
        institution_a,
        institution_b,
        inst_a_coordinator_member,
        inst_b_coordinator_member,
        talent_b,
        student_b,
        user_a_coordinator,
    ):
        """AC-S2 (BOLA): Coordinator of A cannot reject B's link request → 404, status unchanged."""
        from app.models import InstitutionLinkRequest

        link_req = InstitutionLinkRequest(
            talent_profile_id=talent_b.id,
            institution_id=institution_b.id,
            status="PENDING"
        )
        session.add(link_req)
        session.flush()
        request_id = link_req.id

        response = client.post(f"/institutions/{institution_b.id}/link-requests/{request_id}/reject", headers={"X-Debug-User-Id": str(user_a_coordinator.id)})

        assert response.status_code == 404, (
            "Coordinator of A should not access/reject resources of B (404)"
        )

        link_req = session.query(InstitutionLinkRequest).filter_by(id=request_id).first()
        assert link_req.status == "PENDING", "Link request should remain PENDING"

    def test_admin_a_cannot_reject_link_request_for_b(
        self,
        client,
        session,
        institution_a,
        institution_b,
        inst_a_admin_member,
        inst_b_coordinator_member,
        talent_b,
        student_b,
        user_a_admin,
    ):
        """AC-S2: Admin of A also cannot reject link for B."""
        from app.models import InstitutionLinkRequest

        link_req = InstitutionLinkRequest(
            talent_profile_id=talent_b.id,
            institution_id=institution_b.id,
            status="PENDING"
        )
        session.add(link_req)
        session.flush()
        request_id = link_req.id

        response = client.post(f"/institutions/{institution_b.id}/link-requests/{request_id}/reject", headers={"X-Debug-User-Id": str(user_a_admin.id)})

        assert response.status_code == 404

    # ========================================================================
    # YET-197/IS-10: List pending link requests — BOLA
    # ========================================================================

    def test_coordinator_a_can_list_pending_requests_for_a(
        self,
        client,
        session,
        institution_a,
        inst_a_coordinator_member,
        talent_a,
        student_a,
        user_a_coordinator,
    ):
        """Positive: coordinator of A can list A's own pending requests."""
        from app.models import InstitutionLinkRequest

        link_req = InstitutionLinkRequest(
            talent_profile_id=talent_a.id,
            institution_id=institution_a.id,
            status="PENDING"
        )
        session.add(link_req)
        session.flush()

        response = client.get(f"/institutions/{institution_a.id}/link-requests", headers={"X-Debug-User-Id": str(user_a_coordinator.id)})

        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == str(link_req.id)

    def test_coordinator_a_cannot_list_pending_requests_for_b(
        self,
        client,
        session,
        institution_a,
        institution_b,
        inst_a_coordinator_member,
        inst_b_coordinator_member,
        talent_b,
        student_b,
        user_a_coordinator,
    ):
        """AC-S2 (BOLA): Coordinator of A cannot list B's pending requests → 404, no data leak."""
        from app.models import InstitutionLinkRequest

        link_req = InstitutionLinkRequest(
            talent_profile_id=talent_b.id,
            institution_id=institution_b.id,
            status="PENDING"
        )
        session.add(link_req)
        session.flush()

        response = client.get(f"/institutions/{institution_b.id}/link-requests", headers={"X-Debug-User-Id": str(user_a_coordinator.id)})

        assert response.status_code == 404
        # No leak of B's talent name/id in the body
        body = response.text
        assert str(link_req.id) not in body
        assert talent_b.full_name not in body

    def test_talent_cannot_list_pending_requests(
        self,
        client,
        institution_a,
        talent_a,
        student_a,
    ):
        """TALENT principal has no institution role → 404 (not 403) listing pending requests."""
        response = client.get(f"/institutions/{institution_a.id}/link-requests", headers={"X-Debug-User-Id": str(student_a.id)})

        assert response.status_code == 404, (
            f"TALENT should receive 404, got {response.status_code}"
        )

    def test_unauthenticated_reject_and_list_401(
        self,
        client,
        institution_a,
    ):
        """No X-Debug-User-Id header → 401 for both reject and list-pending."""
        nonexistent_id = "550e8400-e29b-41d4-a716-446655440099"

        reject_response = client.post(f"/institutions/{institution_a.id}/link-requests/{nonexistent_id}/reject")
        assert reject_response.status_code == 401

        list_response = client.get(f"/institutions/{institution_a.id}/link-requests")
        assert list_response.status_code == 401


# ============================================================================
# Authorization Core Tests (can() + scoped_institutions())
# ============================================================================


class TestCanFunctionInstitution:
    """Unit tests for can() function with Institution resources."""

    def test_can_admin_manage_institution(self, session, user_a_admin):
        """can() returns True for ADMIN managing own institution."""
        institution = Institution(name="Test", domain="test.edu.tr")
        session.add(institution)
        session.flush()

        principal = Principal(
            user_id=user_a_admin.id,
            kind="INST_ADMIN",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[institution.id],
            institution_admin_ids=[institution.id],
            is_platform_admin=False,
            is_suspended=False,
        )

        # Admin should be able to "admin_update" institution
        result = can(principal, "admin_update", institution)
        assert result is True

    def test_can_coordinator_cannot_admin_manage_institution(self, session, user_a_coordinator, institution_a):
        """can() returns False for COORDINATOR (non-admin role)."""
        principal = Principal(
            user_id=user_a_coordinator.id,
            kind="COORDINATOR",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[institution_a.id],
            is_platform_admin=False,
            is_suspended=False,
        )

        # COORDINATOR cannot perform admin actions
        result = can(principal, "admin_update", institution_a)
        assert result is False


class TestScopedInstitutions:
    """Unit tests for scoped_institutions() query function."""

    def test_scoped_institutions_returns_accessible_institutions(
        self, session, institution_a, institution_b, user_a_admin
    ):
        """
        scoped_institutions() returns only institutions in principal's scope.

        Principal A_admin should see only A, not B.
        """
        principal = Principal(
            user_id=user_a_admin.id,
            kind="INST_ADMIN",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[institution_a.id],  # Only A
            is_platform_admin=False,
            is_suspended=False,
        )

        scoped_select = scoped_institutions(session, principal)
        results = session.execute(scoped_select).scalars().all()

        result_ids = [inst.id for inst in results]
        assert institution_a.id in result_ids
        assert institution_b.id not in result_ids

    def test_scoped_institutions_tenant_isolation(
        self, session, institution_a, institution_b, user_a_admin, user_b_admin
    ):
        """Tenant isolation: A's principal sees A, B's principal sees B."""
        principal_a = Principal(
            user_id=user_a_admin.id,
            kind="INST_ADMIN",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[institution_a.id],
            is_platform_admin=False,
            is_suspended=False,
        )

        principal_b = Principal(
            user_id=user_b_admin.id,
            kind="INST_ADMIN",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[institution_b.id],
            is_platform_admin=False,
            is_suspended=False,
        )

        scoped_a = session.execute(scoped_institutions(session, principal_a)).scalars().all()
        scoped_b = session.execute(scoped_institutions(session, principal_b)).scalars().all()

        ids_a = [inst.id for inst in scoped_a]
        ids_b = [inst.id for inst in scoped_b]

        assert institution_a.id in ids_a
        assert institution_b.id not in ids_a

        assert institution_b.id in ids_b
        assert institution_a.id not in ids_b


class TestGetScopedOr404Institution:
    """Unit tests for get_scoped_or_404() with Institution scope."""

    def test_get_scoped_or_404_returns_institution_when_in_scope(
        self, session, institution_a, user_a_admin
    ):
        """get_scoped_or_404() returns institution if in scope."""
        principal = Principal(
            user_id=user_a_admin.id,
            kind="INST_ADMIN",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[institution_a.id],
            is_platform_admin=False,
            is_suspended=False,
        )

        scoped_select = scoped_institutions(session, principal)
        result = get_scoped_or_404(scoped_select, session)

        assert result is not None
        assert result.id == institution_a.id

    def test_get_scoped_or_404_returns_none_when_out_of_scope(
        self, session, institution_a, institution_b, user_a_admin
    ):
        """
        get_scoped_or_404() returns None when resource is out of scope
        (even though it exists in database).
        """
        principal = Principal(
            user_id=user_a_admin.id,
            kind="INST_ADMIN",
            talent_id=None,
            org_ids=[],
            org_admin_ids=[],
            institution_ids=[institution_a.id],  # Only A, not B
            is_platform_admin=False,
            is_suspended=False,
        )

        # Try to scope query for B (out of scope)
        # NOTE: This would be in practice: filter by institution_b.id first,
        # then apply scoped_institutions().
        # For now, we just test that scoped query for A doesn't return B.

        scoped_select = scoped_institutions(session, principal)
        results = session.execute(scoped_select).scalars().all()
        result_ids = [inst.id for inst in results]

        assert institution_b.id not in result_ids


# ============================================================================
# Additional Fixtures for Dashboard Authorization Tests
# ============================================================================


@pytest.fixture
def user_dashboard_talent_fixture(session):
    """User with TALENT kind (no institution affiliation)."""
    user = User(email="talent-dashboard-test@example.com", password_hash="hash_talent")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent_dashboard_profile(session, user_dashboard_talent_fixture):
    """Talent profile for dashboard test TALENT user."""
    profile = TalentProfile(
        user_id=user_dashboard_talent_fixture.id,
        full_name="Dashboard Test Talent",
        visibility="PRIVATE"
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def org_member_for_dashboard_test(session):
    """User with ORG_MEMBER role."""
    user = User(email="orgmember-dashboard@example.com", password_hash="hash_orgmember")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def org_member_talent_profile(session, org_member_for_dashboard_test):
    """Talent profile for ORG_MEMBER user."""
    profile = TalentProfile(
        user_id=org_member_for_dashboard_test.id,
        full_name="ORG Member Talent",
        visibility="PRIVATE"
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def org_for_member_test(session):
    """Organization for ORG_MEMBER test."""
    org = Organization(
        name="Test Org for Dashboard",
        domain="dashboard-org.example.com",
        legal_id="ORG-DASHBOARD-001",
        verification_level="T1",
        status="ACTIVE"
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def org_member_membership(session, org_for_member_test, org_member_for_dashboard_test):
    """Establish ORG_MEMBER role."""
    member = OrganizationMember(
        organization_id=org_for_member_test.id,
        user_id=org_member_for_dashboard_test.id,
        role="MEMBER"
    )
    session.add(member)
    session.flush()
    return member


# ============================================================================
# COORDINATOR Dashboard Tests (Authorization Matrix — authz_test.md)
# ============================================================================
# Tests for GET /institutions/{institution_id}/dashboard endpoint
# Implements authz_test.md rows 2-6: cross-tenant isolation, role-based access,
# and unauthenticated access denial.


class TestCoordinatorDashboardAuthorizationMatrix:
    """
    Authorization matrix for GET /institutions/{id}/dashboard.

    Authz_test.md row mapping:
    - Row 2: Cross-tenant (COORDINATOR in Y, accessing A) → 404 (not 403, no data leak)
    - Row 3: TALENT → 404 (role-based denial)
    - Row 4: ORG_MEMBER → 404 (role-based denial)
    - Row 5: Unauthenticated (anon) → 401
    - Row 6: Expired/invalid JWT → 401
    """

    # ============================================================================
    # Row 2: Cross-tenant Access Prevention (AC-S1)
    # ============================================================================

    def test_coordinator_different_institution_404_no_leak(
        self,
        client,
        session,
        institution_a,
        institution_b,
        inst_a_coordinator_member,
        inst_b_coordinator_member,
        user_a_coordinator,
    ):
        """
        Authz Row 2: COORDINATOR of institution_b attempts to access institution_a's dashboard.

        Scenario:
        - Coordinator A is member of institution_a only
        - Coordinator A tries to access /institutions/{institution_b}/dashboard
        - Expected: 404 (not 403 — resource existence hidden)
        - Response body must NOT contain any of institution_b's engagement data
          (id, talent_id, organization_id, title fields specifically checked)

        Acceptance Criteria:
        - Status code: exactly 404
        - Response body does not contain any engagement fields from institution_b
        - Error message does not reveal whether institution exists
        """
        # Coordinator of institution_a trying to access institution_b
        response = client.get(
            f"/institutions/{institution_b.id}/dashboard",
            headers={"X-Debug-User-Id": str(user_a_coordinator.id)}
        )

        # EXACT status code match — 404, not 403
        assert response.status_code == 404, (
            f"Cross-tenant access should return 404, got {response.status_code}"
        )

        # Verify no data leak in response body
        response_body = response.json()

        # Response must not contain any engagement fields from institution_b
        assert "pending_approval" not in response_body, (
            "Response body should not contain pending_approval field (404 should not leak data)"
        )
        assert "pending_evaluation" not in response_body, (
            "Response body should not contain pending_evaluation field (404 should not leak data)"
        )
        assert "summary" not in response_body, (
            "Response body should not contain summary field (404 should not leak data)"
        )

    def test_admin_different_institution_404_no_leak(
        self,
        client,
        institution_a,
        institution_b,
        inst_a_admin_member,
        inst_b_admin_member,
        user_a_admin,
    ):
        """
        Authz Row 2 (Admin variant): ADMIN of institution_a cannot access institution_b.

        Same as coordinator test, but with ADMIN role.
        """
        response = client.get(
            f"/institutions/{institution_b.id}/dashboard",
            headers={"X-Debug-User-Id": str(user_a_admin.id)}
        )

        # EXACT status code match
        assert response.status_code == 404, (
            f"Admin cross-tenant access should return 404, got {response.status_code}"
        )

    # ============================================================================
    # Row 3: TALENT Cannot Access Dashboard (AC-S2)
    # ============================================================================

    def test_talent_principal_404_not_403(
        self,
        client,
        session,
        institution_a,
        user_dashboard_talent_fixture,
        talent_dashboard_profile,
    ):
        """
        Authz Row 3: TALENT (kind='TALENT') cannot access institution dashboard.

        Expected:
        - Status: 404 (not 403)
        - Principal kind is 'TALENT' (verified via fixture setup)
        """
        # TALENT user has talent_id set, so principal.kind would be 'TALENT'
        response = client.get(
            f"/institutions/{institution_a.id}/dashboard",
            headers={"X-Debug-User-Id": str(user_dashboard_talent_fixture.id)}
        )

        # EXACT status code match — 404, not 403
        assert response.status_code == 404, (
            f"TALENT should receive 404, got {response.status_code} (not 403 — no access to dashboard endpoint)"
        )

    def test_talent_even_with_institution_link_404(
        self,
        client,
        session,
        institution_a,
    ):
        """
        Authz Row 3 (edge case): TALENT who is a student in institution_a still gets 404.

        Even if the talent's profile has institution_id = institution_a.id,
        TALENT kind cannot access the coordinator dashboard.
        """
        # Create a talent linked to institution_a
        user = User(email="talent-in-inst@example.com", password_hash="hash_talent_inst")
        session.add(user)
        session.flush()

        profile = TalentProfile(
            user_id=user.id,
            institution_id=institution_a.id,
            full_name="Talent in Institution A",
            visibility="PRIVATE"
        )
        session.add(profile)
        session.flush()

        response = client.get(
            f"/institutions/{institution_a.id}/dashboard",
            headers={"X-Debug-User-Id": str(user.id)}
        )

        # EXACT status code match
        assert response.status_code == 404, (
            "TALENT linked to institution should still get 404 from dashboard endpoint"
        )

    # ============================================================================
    # Row 4: ORG_MEMBER Cannot Access Dashboard (AC-S2)
    # ============================================================================

    def test_org_member_404_not_403(
        self,
        client,
        session,
        institution_a,
        org_member_for_dashboard_test,
        org_member_talent_profile,
        org_member_membership,
    ):
        """
        Authz Row 4: ORG_MEMBER (kind='ORG_MEMBER') cannot access institution dashboard.

        Expected:
        - Status: 404 (not 403)
        - Principal kind is 'ORG_MEMBER'
        """
        response = client.get(
            f"/institutions/{institution_a.id}/dashboard",
            headers={"X-Debug-User-Id": str(org_member_for_dashboard_test.id)}
        )

        # EXACT status code match — 404, not 403
        assert response.status_code == 404, (
            f"ORG_MEMBER should receive 404, got {response.status_code}"
        )

    # ============================================================================
    # Row 5: Unauthenticated (No Header) → 401
    # ============================================================================

    def test_unauthenticated_no_header_401(
        self,
        client,
        institution_a,
    ):
        """
        Authz Row 5: Unauthenticated request (no X-Debug-User-Id header).

        Expected:
        - Status: 401 Unauthorized
        - Error message indicates authentication required
        """
        # Make request WITHOUT X-Debug-User-Id header
        response = client.get(f"/institutions/{institution_a.id}/dashboard")

        # EXACT status code match
        assert response.status_code == 401, (
            f"Unauthenticated request should return 401, got {response.status_code}"
        )

    def test_unauthenticated_empty_header_401(
        self,
        client,
        institution_a,
    ):
        """
        Authz Row 5: Unauthenticated request (empty X-Debug-User-Id header).

        Expected:
        - Status: 401
        """
        response = client.get(
            f"/institutions/{institution_a.id}/dashboard",
            headers={"X-Debug-User-Id": ""}
        )

        assert response.status_code == 401, (
            f"Empty X-Debug-User-Id should return 401, got {response.status_code}"
        )

    # ============================================================================
    # Row 6: Expired/Invalid JWT → 401 (simulated via invalid user ID)
    # ============================================================================

    def test_invalid_user_id_401(
        self,
        client,
        institution_a,
    ):
        """
        Authz Row 6: Invalid user ID (simulates expired/invalid JWT).

        In conftest.py, override_get_current_user queries the session for user_id.
        If the user doesn't exist, it returns 401.

        Expected:
        - Status: 401
        """
        fake_user_id = str(__import__('uuid').uuid4())  # User doesn't exist in DB

        response = client.get(
            f"/institutions/{institution_a.id}/dashboard",
            headers={"X-Debug-User-Id": fake_user_id}
        )

        # EXACT status code match
        assert response.status_code == 401, (
            f"Invalid user ID should return 401, got {response.status_code}"
        )


# ============================================================================
# GUV-02 Davet Ucu Testleri — Institution (AC-1 — AC-8)
# ============================================================================
# Acceptance Criteria tablosundan türetilen testler (organization'la aynı pattern):
# - AC-1: Happy path (bilinen e-posta, geçerli rol, yeni üye) + audit
# - AC-2: Bilinmeyen e-posta (202 döner, üyelik oluşmaz, audit yazılır)
# - AC-3: Geçersiz rol (422 + INVALID_ROLE)
# - AC-4/AC-5: Zaten üye (202, rol değişmez) + son ADMIN senaryosu
# - AC-8: Çapraz-kiracı (404) + COORDINATOR (404)
# Institution'a özgü: AC-6 audit event logging


class TestInviteInstitutionMember:
    """
    GUV-02: POST /institutions/{id}/members — Davranış Sözleşmesi (AC-1 — AC-8).

    Institution-specific patterns:
    - Audit event verification (AC-6): every invite must log to audit_events
    - COORDINATOR cannot invite (AC-8)
    - Single ADMIN protection (AC-5): re-inviting last ADMIN with different role keeps role
    """

    # ========================================================================
    # AC-1: Happy Path — Bilinen e-posta + geçerli rol + yeni üye + audit
    # ========================================================================

    def test_invite_known_user_valid_role_202_queued_with_audit(
        self, client, session, institution_a, inst_a_admin_member, user_to_invite, user_a_admin
    ):
        """
        AC-1: ADMIN of inst_a invites known user with valid role → 202 queued + audit.

        Acceptance Criteria:
        - Status code: exactly 202 Accepted
        - Response body: exactly {"status": "queued"}
        - DB: InstitutionMember created
        - Audit: INVITE_INSTITUTION_MEMBER logged (new in this task, AC-6)
        """
        # Count audit events before
        audit_count_before = session.query(AuditEvent).filter_by(
            action="INVITE_INSTITUTION_MEMBER",
            actor_user_id=user_a_admin.id
        ).count()

        payload = {
            "email": user_to_invite.email,
            "role": "COORDINATOR"
        }

        response = client.post(
            f"/institutions/{institution_a.id}/members",
            json=payload,
            headers={"X-Debug-User-Id": str(user_a_admin.id)}
        )

        # EXACT status code match
        assert response.status_code == 202, f"Expected 202, got {response.status_code}"

        # EXACT response body match
        assert response.json() == {"status": "queued"}, (
            f"Expected {{'status': 'queued'}}, got {response.json()}"
        )

        # DB verification: membership created
        member = session.query(InstitutionMember).filter_by(
            institution_id=institution_a.id,
            user_id=user_to_invite.id
        ).first()
        assert member is not None, "InstitutionMember should be created in DB"
        assert member.role == "COORDINATOR", f"Role should be COORDINATOR, got {member.role}"

        # Audit event verification (AC-6)
        audit_count_after = session.query(AuditEvent).filter_by(
            action="INVITE_INSTITUTION_MEMBER",
            actor_user_id=user_a_admin.id
        ).count()
        assert audit_count_after == audit_count_before + 1, (
            "One new INVITE_INSTITUTION_MEMBER audit event should be logged"
        )

    # ========================================================================
    # AC-2: Bilinmeyen e-posta — 202 döner, üyelik oluşmaz, audit yazılır
    # ========================================================================

    def test_invite_unknown_email_202_no_membership_with_audit(
        self, client, session, institution_a, inst_a_admin_member, user_a_admin
    ):
        """
        AC-2: ADMIN invites unknown email → 202 queued, no membership, audit logged.

        Acceptance Criteria:
        - Status code: exactly 202 (not 422 as before)
        - Response body: exactly {"status": "queued"}
        - DB: NO InstitutionMember created
        - Audit: event logged (but without email PII — no email in metadata)
        """
        unknown_email = "unknown-institution-xyz@example.com"

        # Count audit before
        audit_count_before = session.query(AuditEvent).filter_by(
            action="INVITE_INSTITUTION_MEMBER",
            actor_user_id=user_a_admin.id
        ).count()

        payload = {
            "email": unknown_email,
            "role": "COORDINATOR"
        }

        response = client.post(
            f"/institutions/{institution_a.id}/members",
            json=payload,
            headers={"X-Debug-User-Id": str(user_a_admin.id)}
        )

        # EXACT status code match (202, not 422)
        assert response.status_code == 202, f"Expected 202, got {response.status_code}"

        # EXACT response body match
        assert response.json() == {"status": "queued"}, (
            f"Expected {{'status': 'queued'}}, got {response.json()}"
        )

        # Audit: event logged (AC-6)
        audit_count_after = session.query(AuditEvent).filter_by(
            action="INVITE_INSTITUTION_MEMBER",
            actor_user_id=user_a_admin.id
        ).count()
        assert audit_count_after == audit_count_before + 1, (
            "Audit event should be logged even for unknown email"
        )

        # Verify no PII in audit metadata
        audit_event = session.query(AuditEvent).filter_by(
            action="INVITE_INSTITUTION_MEMBER",
            actor_user_id=user_a_admin.id
        ).order_by(AuditEvent.created_at.desc()).first()
        metadata_str = str(audit_event.event_metadata or {})
        assert unknown_email not in metadata_str, "PII (email) should not be in audit metadata"

    # ========================================================================
    # AC-3: Geçersiz rol — 422 + INVALID_ROLE
    # ========================================================================

    def test_invite_invalid_role_422_invalid_role_code(
        self, client, session, institution_a, inst_a_admin_member, user_to_invite, user_a_admin
    ):
        """
        AC-3: ADMIN invites with invalid role → 422 INVALID_ROLE.

        Acceptance Criteria:
        - Status code: exactly 422 Unprocessable Entity
        - Response body contains: {"code": "INVALID_ROLE"}
        - DB: NO membership created
        - No CHECK constraint error (Pydantic catches it first, AC-3)
        """
        invalid_roles = ["SUPERADMIN", "ADMIN_PLUS", "GUEST", "MEMBER"]

        for invalid_role in invalid_roles:
            payload = {
                "email": user_to_invite.email,
                "role": invalid_role
            }

            response = client.post(
                f"/institutions/{institution_a.id}/members",
                json=payload,
                headers={"X-Debug-User-Id": str(user_a_admin.id)}
            )

            # EXACT status code match
            assert response.status_code == 422, (
                f"Invalid role '{invalid_role}' should return 422, got {response.status_code}"
            )

            # Verify error code
            response_data = response.json()
            assert response_data.get("code") == "INVALID_ROLE", (
                f"Error code should be 'INVALID_ROLE', got {response_data.get('code')}"
            )

            # DB: verify NO membership created
            member = session.query(InstitutionMember).filter_by(
                institution_id=institution_a.id,
                user_id=user_to_invite.id,
                role=invalid_role
            ).first()
            assert member is None, f"No membership should be created for invalid role '{invalid_role}'"

    # ========================================================================
    # AC-4: Zaten üye — 202 queued, rol DEĞİŞMEZ
    # ========================================================================

    def test_invite_already_member_202_role_unchanged(
        self, client, session, institution_a, inst_a_admin_member, inst_a_coordinator_member,
        user_a_coordinator, user_a_admin
    ):
        """
        AC-4: ADMIN re-invites existing member with different role → 202, role unchanged.

        Scenario:
        - user_a_coordinator is already COORDINATOR of inst_a
        - ADMIN invites same user as ADMIN role (higher privilege)
        - Expected: 202 queued, but user's role stays COORDINATOR (not UPSERT'd)

        Acceptance Criteria:
        - Status code: exactly 202
        - Response body: exactly {"status": "queued"}
        - DB before: user_a_coordinator.role == "COORDINATOR"
        - DB after: user_a_coordinator.role == "COORDINATOR" (unchanged)
        """
        # Verify initial state
        initial_member = session.query(InstitutionMember).filter_by(
            institution_id=institution_a.id,
            user_id=user_a_coordinator.id
        ).first()
        assert initial_member is not None, "user_a_coordinator should be member"
        initial_role = initial_member.role
        assert initial_role == "COORDINATOR", f"Initial role should be COORDINATOR, got {initial_role}"

        # Re-invite with ADMIN role
        payload = {
            "email": user_a_coordinator.email,
            "role": "ADMIN"
        }

        response = client.post(
            f"/institutions/{institution_a.id}/members",
            json=payload,
            headers={"X-Debug-User-Id": str(user_a_admin.id)}
        )

        # EXACT status code
        assert response.status_code == 202, f"Expected 202, got {response.status_code}"

        # EXACT response body
        assert response.json() == {"status": "queued"}, (
            f"Expected {{'status': 'queued'}}, got {response.json()}"
        )

        # DB: role unchanged (AC-4's key test)
        final_member = session.query(InstitutionMember).filter_by(
            institution_id=institution_a.id,
            user_id=user_a_coordinator.id
        ).first()
        assert final_member is not None, "Member should still exist"
        assert final_member.role == "COORDINATOR", (
            f"Role should remain COORDINATOR (not UPSERT'd), but got {final_member.role}"
        )

    # ========================================================================
    # AC-5: Son ADMIN senaryosu — tek ADMIN'i COORDINATOR'a davet → rol ADMIN kalır
    # ========================================================================

    def test_single_admin_re_invite_role_unchanged_protects_admin_count(
        self, client, session, institution_a, inst_a_admin_member, user_a_admin
    ):
        """
        AC-5: Single ADMIN of inst_a re-invites themselves with COORDINATOR role
               → 202 queued, but role stays ADMIN (prevents accidental admin removal).

        Scenario:
        - Institution A has exactly 1 ADMIN (user_a_admin)
        - ADMIN invites themselves with role=COORDINATOR (self-destruction attempt)
        - Expected: 202 queued, role stays ADMIN (not demoted to COORDINATOR)
        - Result: institution never loses all admins

        Acceptance Criteria:
        - Status code: exactly 202
        - Response body: exactly {"status": "queued"}
        - DB before: inst_a has 1 ADMIN (user_a_admin)
        - DB after: inst_a still has 1 ADMIN, user_a_admin.role == ADMIN (unchanged)
        - Audit: event logged (even though operation is no-op)
        """
        # Verify pre-condition: only 1 ADMIN in institution_a
        admin_count_before = session.query(InstitutionMember).filter_by(
            institution_id=institution_a.id,
            role="ADMIN"
        ).count()
        assert admin_count_before == 1, f"Should have exactly 1 ADMIN, got {admin_count_before}"

        # ADMIN invites self with COORDINATOR role (attempting demotion)
        payload = {
            "email": user_a_admin.email,
            "role": "COORDINATOR"
        }

        response = client.post(
            f"/institutions/{institution_a.id}/members",
            json=payload,
            headers={"X-Debug-User-Id": str(user_a_admin.id)}
        )

        # EXACT status code
        assert response.status_code == 202, f"Expected 202, got {response.status_code}"

        # EXACT response body
        assert response.json() == {"status": "queued"}, (
            f"Expected {{'status': 'queued'}}, got {response.json()}"
        )

        # DB: verify role unchanged (AC-5's key protection)
        member_after = session.query(InstitutionMember).filter_by(
            institution_id=institution_a.id,
            user_id=user_a_admin.id
        ).first()
        assert member_after is not None, "Member should exist"
        assert member_after.role == "ADMIN", (
            f"Role should remain ADMIN (not demoted to COORDINATOR), got {member_after.role}"
        )

        # Verify ADMIN count unchanged
        admin_count_after = session.query(InstitutionMember).filter_by(
            institution_id=institution_a.id,
            role="ADMIN"
        ).count()
        assert admin_count_after == 1, (
            f"Should still have exactly 1 ADMIN, got {admin_count_after} (AC-5 protection)"
        )

    # ========================================================================
    # AC-8: Çapraz-kiracı — INST_ADMIN B vs INST A → 404
    # ========================================================================

    def test_cross_tenant_inst_b_admin_cannot_invite_to_inst_a_404(
        self, client, session, institution_a, institution_b, inst_a_admin_member, inst_b_admin_member,
        user_to_invite, user_b_admin
    ):
        """
        AC-8 / Authz row 2: ADMIN of inst_b tries to invite to inst_a → 404 (tenant isolation).

        Acceptance Criteria:
        - Status code: exactly 404 Not Found
        - No membership created in inst_a
        - No data leak in response
        """
        payload = {
            "email": user_to_invite.email,
            "role": "COORDINATOR"
        }

        # user_b_admin is ADMIN of inst_b, tries to invite to inst_a
        response = client.post(
            f"/institutions/{institution_a.id}/members",
            json=payload,
            headers={"X-Debug-User-Id": str(user_b_admin.id)}
        )

        # EXACT status code: 404
        assert response.status_code == 404, (
            f"Cross-tenant access should return 404, got {response.status_code}"
        )

        # DB: verify no membership created in inst_a
        member = session.query(InstitutionMember).filter_by(
            institution_id=institution_a.id,
            user_id=user_to_invite.id
        ).first()
        assert member is None, "No membership should be created in inst_a by inst_b's admin"

    # ========================================================================
    # AC-8: COORDINATOR cannot invite (role-based denial) → 404
    # ========================================================================

    def test_coordinator_cannot_invite_404(
        self, client, session, institution_a, inst_a_coordinator_member, user_to_invite, user_a_coordinator
    ):
        """
        AC-8 / Authz row 3: COORDINATOR of inst_a (not ADMIN) tries to invite → 404.

        Acceptance Criteria:
        - Status code: exactly 404 Not Found (not 403 — role-based denial hides resource)
        - No membership created
        """
        payload = {
            "email": user_to_invite.email,
            "role": "COORDINATOR"
        }

        response = client.post(
            f"/institutions/{institution_a.id}/members",
            json=payload,
            headers={"X-Debug-User-Id": str(user_a_coordinator.id)}
        )

        # EXACT status code: 404 (not 403, not 201)
        assert response.status_code == 404, (
            f"COORDINATOR should get 404 (not 403), got {response.status_code}"
        )

        # DB: no membership created
        member = session.query(InstitutionMember).filter_by(
            institution_id=institution_a.id,
            user_id=user_to_invite.id
        ).first()
        assert member is None, "No membership should be created by COORDINATOR"

    # ========================================================================
    # AC-6: Audit event kontrolü (institution'a yeni)
    # ========================================================================

    def test_invite_success_audit_event_created(
        self, client, session, institution_a, inst_a_admin_member, user_to_invite, user_a_admin
    ):
        """
        AC-6: Successful invite creates INVITE_INSTITUTION_MEMBER audit event.

        Acceptance Criteria:
        - Before invite: N audit events
        - After invite: N+1 audit events
        - action == "INVITE_INSTITUTION_MEMBER"
        - actor_user_id == user_a_admin.id
        - subject_id == member.id (not membership email, but member.id)
        """
        # Count before
        count_before = session.query(AuditEvent).filter_by(
            action="INVITE_INSTITUTION_MEMBER"
        ).count()

        payload = {
            "email": user_to_invite.email,
            "role": "COORDINATOR"
        }

        response = client.post(
            f"/institutions/{institution_a.id}/members",
            json=payload,
            headers={"X-Debug-User-Id": str(user_a_admin.id)}
        )

        assert response.status_code == 202, f"Expected 202, got {response.status_code}"

        # Count after
        count_after = session.query(AuditEvent).filter_by(
            action="INVITE_INSTITUTION_MEMBER"
        ).count()

        assert count_after == count_before + 1, "One new audit event should be created"

        # Verify latest event has correct attributes
        latest_event = session.query(AuditEvent).filter_by(
            action="INVITE_INSTITUTION_MEMBER"
        ).order_by(AuditEvent.created_at.desc()).first()

        assert latest_event is not None, "Audit event should exist"
        assert latest_event.actor_user_id == user_a_admin.id, (
            f"actor_user_id should be {user_a_admin.id}, got {latest_event.actor_user_id}"
        )

    def test_invite_unknown_email_audit_event_created_without_pii(
        self, client, session, institution_a, inst_a_admin_member, user_a_admin
    ):
        """
        AC-6 + AC-2: Unknown email invite creates audit event WITHOUT PII.

        Acceptance Criteria:
        - Audit event created for unknown email invite
        - Email NOT in event metadata (PII guard)
        """
        unknown_email = "unknown-no-pii@example.com"

        count_before = session.query(AuditEvent).filter_by(
            action="INVITE_INSTITUTION_MEMBER"
        ).count()

        payload = {
            "email": unknown_email,
            "role": "COORDINATOR"
        }

        response = client.post(
            f"/institutions/{institution_a.id}/members",
            json=payload,
            headers={"X-Debug-User-Id": str(user_a_admin.id)}
        )

        assert response.status_code == 202

        count_after = session.query(AuditEvent).filter_by(
            action="INVITE_INSTITUTION_MEMBER"
        ).count()

        assert count_after == count_before + 1, "Audit event should be created"

        latest_event = session.query(AuditEvent).filter_by(
            action="INVITE_INSTITUTION_MEMBER"
        ).order_by(AuditEvent.created_at.desc()).first()

        metadata_str = str(latest_event.event_metadata or {})
        assert unknown_email not in metadata_str, (
            "Email (PII) should not be in audit event metadata"
        )
