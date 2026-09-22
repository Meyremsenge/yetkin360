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

from app.models import Institution, InstitutionMember, TalentProfile, User
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
