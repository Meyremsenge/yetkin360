"""
Institution endpoint tests (YET-8 — institution-koordinator-ogrenci-bagi).

Implements AC-1, AC-2, AC-3, AC-3b, AC-6, AC-7, AC-8 from atdd.md.

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Parametric tests where appropriate (error cases)
- Each AC has one or more test functions

Status: Tests are RED/IMPORT-ERROR — implementation not yet written.
This is expected behavior. Tests implement behavior contract (ATDD).
"""

import pytest

from app.models import Institution, InstitutionMember, TalentProfile, User


# ============================================================================
# Fixtures: Users, Institutions
# ============================================================================


@pytest.fixture
def user_creator(session):
    """User who will create an institution (becomes ADMIN)."""
    user = User(email="creator@example.com", password_hash="hash_creator")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_coordinator(session):
    """User who will be invited as COORDINATOR."""
    user = User(email="coordinator@example.com", password_hash="hash_coordinator")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_admin_inviter(session):
    """User who will be invited as ADMIN."""
    user = User(email="admin@example.com", password_hash="hash_admin")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_student_a(session):
    """Student who will request institution link."""
    user = User(email="student-a@example.com", password_hash="hash_student_a")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_student_b(session):
    """Another student (for cross-institution tests)."""
    user = User(email="student-b@example.com", password_hash="hash_student_b")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def institution_a(session):
    """Test institution A."""
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
    """Test institution B (for tenant isolation tests)."""
    inst = Institution(
        name="Test Institution B",
        domain="testbbb.edu.tr",
        verification_level="T1",
        status="ACTIVE"
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def institution_a_admin_member(session, institution_a, user_creator):
    """InstitutionMember: user_creator is ADMIN of institution_a."""
    member = InstitutionMember(
        institution_id=institution_a.id,
        user_id=user_creator.id,
        role="ADMIN"
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def institution_a_coordinator_member(session, institution_a, user_coordinator):
    """InstitutionMember: user_coordinator is COORDINATOR of institution_a."""
    member = InstitutionMember(
        institution_id=institution_a.id,
        user_id=user_coordinator.id,
        role="COORDINATOR"
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def institution_b_coordinator(session, institution_b, user_coordinator):
    """InstitutionMember: user_coordinator is COORDINATOR of institution_b."""
    # Use user_coordinator for another institution
    user = User(email="coordinator-b@example.com", password_hash="hash_coord_b")
    session.add(user)
    session.flush()
    member = InstitutionMember(
        institution_id=institution_b.id,
        user_id=user.id,
        role="COORDINATOR"
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def talent_a(session, user_student_a):
    """Talent profile for student_a."""
    profile = TalentProfile(
        user_id=user_student_a.id,
        full_name="Test Student A",
        visibility="PRIVATE"
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_b(session, user_student_b):
    """Talent profile for student_b."""
    profile = TalentProfile(
        user_id=user_student_b.id,
        full_name="Test Student B",
        visibility="PRIVATE"
    )
    session.add(profile)
    session.flush()
    return profile


# ============================================================================
# AC-1: Institution creation (POST /institutions) → 201, T1, caller becomes ADMIN
# ============================================================================


class TestInstitutionCreation:
    """AC-1: POST /institutions creates institution with T1 verification level."""

    def test_create_institution_basic(self, client, session, user_creator):
        """
        AC-1: POST /institutions with valid name → 201, caller becomes ADMIN.

        Acceptance Criteria:
        - Status code: 201 Created
        - Institution created with verification_level = T1
        - Caller (user_creator) automatically becomes InstitutionMember(role=ADMIN)
        """
        # Setup: Simulate authentication (user_creator)
        # NOTE: Real implementation will use auth middleware.
        # For now, test assumes user context is available (to be mocked/setup by middleware).

        payload = {
            "name": "New University",
            "domain": "newuniv.edu.tr"
        }

        response = client.post("/institutions", json=payload, headers={"X-Debug-User-Id": str(user_creator.id)})

        # Assert: 201 Created
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        # Assert: response contains institution data
        data = response.json()
        assert data["verification_level"] == "T1"
        assert data["name"] == "New University"
        assert data["domain"] == "newuniv.edu.tr"
        assert data["status"] == "ACTIVE"

        # Assert: caller is automatically ADMIN
        institution_id = data["id"]
        # Check database directly: user_creator should be ADMIN member
        inst_member = session.query(InstitutionMember).filter_by(
            institution_id=institution_id,
            user_id=user_creator.id
        ).first()
        assert inst_member is not None, "Caller should be added as InstitutionMember"
        assert inst_member.role == "ADMIN", "Caller should have role ADMIN"

    def test_create_institution_without_domain(self, client, session, user_creator):
        """AC-1: POST /institutions without domain is valid (domain optional)."""
        payload = {
            "name": "Another University"
            # domain omitted
        }

        response = client.post("/institutions", json=payload, headers={"X-Debug-User-Id": str(user_creator.id)})

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Another University"
        assert data["verification_level"] == "T1"

    @pytest.mark.parametrize("invalid_input,expected_status", [
        ({"domain": "newuniv.edu.tr"}, 422),  # Missing name
        ({}, 422),  # Missing both name and domain
        ({"name": "", "domain": "test.edu.tr"}, 422),  # Empty name
    ])
    def test_create_institution_invalid_input(self, client, invalid_input, expected_status, user_creator):
        """AC-1 error case: Invalid input → 422 Unprocessable Entity."""
        response = client.post("/institutions", json=invalid_input, headers={"X-Debug-User-Id": str(user_creator.id)})

        assert response.status_code == expected_status


# ============================================================================
# AC-2: Invite member to institution (POST /institutions/{id}/members) → 201
# ============================================================================


class TestInstitutionMemberInvitation:
    """AC-2: POST /institutions/{id}/members invites member with specified role."""

    def test_admin_invites_coordinator(self, session, user_creator, user_coordinator, institution_a, institution_a_admin_member, client):
        """
        AC-2: ADMIN invites user as COORDINATOR → 201, member created/invited.

        Acceptance Criteria:
        - Status code: 201 Created
        - InstitutionMember record created with role=COORDINATOR
        - User receives invitation (outbox event, not tested here)
        """
        payload = {
            "email": user_coordinator.email,
            "role": "COORDINATOR"
        }

        response = client.post(f"/institutions/{institution_a.id}/members", json=payload, headers={"X-Debug-User-Id": str(user_creator.id)})

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "COORDINATOR"

        # Verify in database
        member = session.query(InstitutionMember).filter_by(
            institution_id=institution_a.id,
            user_id=user_coordinator.id
        ).first()
        assert member is not None
        assert member.role == "COORDINATOR"

    def test_admin_invites_admin(self, session, user_creator, user_admin_inviter, institution_a, institution_a_admin_member, client):
        """AC-2: ADMIN invites another ADMIN → 201."""
        payload = {
            "email": user_admin_inviter.email,
            "role": "ADMIN"
        }

        response = client.post(f"/institutions/{institution_a.id}/members", json=payload, headers={"X-Debug-User-Id": str(user_creator.id)})

        assert response.status_code == 201
        member = session.query(InstitutionMember).filter_by(
            institution_id=institution_a.id,
            user_id=user_admin_inviter.id
        ).first()
        assert member is not None
        assert member.role == "ADMIN"


# ============================================================================
# AC-3: Student requests institution link (POST /institutions/{id}/link-requests)
# ============================================================================


class TestInstitutionLinkRequest:
    """AC-3: Student requests to link their profile to institution."""

    def test_student_requests_link_creates_pending(self, session, user_student_a, talent_a, institution_a, client):
        """
        AC-3: Student POST /institutions/{id}/link-requests → PENDING record.

        Acceptance Criteria:
        - Status code: 201 Created (or 202 Accepted)
        - InstitutionLinkRequest record created with status=PENDING
        - TalentProfile.institution_id is NOT set (yet)
        """
        # Assume auth context: user_student_a

        response = client.post(f"/institutions/{institution_a.id}/link-requests", headers={"X-Debug-User-Id": str(user_student_a.id)})

        # Expected: 201 or 202
        assert response.status_code in [201, 202], f"Expected 201/202, got {response.status_code}: {response.text}"

        # Verify: institution_link_requests record exists with PENDING status
        # NOTE: This requires querying the institution_link_requests table (not yet created).
        # The test structure assumes the table exists (migration applied).
        # Once migration is applied, this assertion will work.
        from app.models import InstitutionLinkRequest  # Will import once model is created

        link_req = session.query(InstitutionLinkRequest).filter_by(
            talent_profile_id=talent_a.id,
            institution_id=institution_a.id
        ).first()
        assert link_req is not None
        assert link_req.status == "PENDING"

        # Verify: TalentProfile.institution_id is still None (not set)
        talent = session.query(TalentProfile).filter_by(id=talent_a.id).first()
        assert talent.institution_id is None, "TalentProfile.institution_id should NOT be set until approval"


# ============================================================================
# AC-3b: Approve student link request (POST /institutions/{id}/link-requests/{request_id}/approve)
# ============================================================================


class TestInstitutionLinkRequestApproval:
    """AC-3b: Coordinator/Admin approves student link request."""

    def test_coordinator_approves_link_request(self, session, user_student_a, user_coordinator, talent_a, institution_a, institution_a_coordinator_member, client):
        """
        AC-3b: Coordinator POST /institutions/{id}/link-requests/{request_id}/approve → APPROVED + link.

        Acceptance Criteria:
        - Status code: 200 OK or 202 Accepted
        - InstitutionLinkRequest.status = APPROVED
        - TalentProfile.institution_id is set to institution_a.id (single transaction)
        """
        from app.models import InstitutionLinkRequest

        # Setup: Create PENDING link request first
        link_req = InstitutionLinkRequest(
            talent_profile_id=talent_a.id,
            institution_id=institution_a.id,
            status="PENDING"
        )
        session.add(link_req)
        session.flush()
        request_id = link_req.id

        # Assume auth context: user_coordinator (COORDINATOR of institution_a)

        response = client.post(f"/institutions/{institution_a.id}/link-requests/{request_id}/approve", headers={"X-Debug-User-Id": str(user_coordinator.id)})

        # Expected: 200 or 202
        assert response.status_code in [200, 202], f"Expected 200/202, got {response.status_code}: {response.text}"

        # Verify: request is APPROVED
        link_req = session.query(InstitutionLinkRequest).filter_by(id=request_id).first()
        assert link_req.status == "APPROVED"

        # Verify: TalentProfile.institution_id is set
        talent = session.query(TalentProfile).filter_by(id=talent_a.id).first()
        assert talent.institution_id == institution_a.id, "TalentProfile.institution_id should be set after approval"

    def test_admin_approves_link_request(self, client, session, institution_a, talent_a, user_creator, institution_a_admin_member):
        """AC-3b: ADMIN can also approve link requests."""
        from app.models import InstitutionLinkRequest

        link_req = InstitutionLinkRequest(
            talent_profile_id=talent_a.id,
            institution_id=institution_a.id,
            status="PENDING"
        )
        session.add(link_req)
        session.flush()
        request_id = link_req.id

        # Assume auth: user_creator (ADMIN)
        response = client.post(f"/institutions/{institution_a.id}/link-requests/{request_id}/approve", headers={"X-Debug-User-Id": str(user_creator.id)})

        assert response.status_code in [200, 202]

        talent = session.query(TalentProfile).filter_by(id=talent_a.id).first()
        assert talent.institution_id == institution_a.id


# ============================================================================
# AC-6: Duplicate domain rejected (POST /institutions with existing domain → 409)
# ============================================================================


class TestDuplicateDomain:
    """AC-6: Creating institution with duplicate domain → 409 Conflict."""

    def test_duplicate_domain_returns_409(self, client, session, user_creator, institution_a):
        """
        AC-6: POST /institutions with domain matching existing institution → 409.

        Acceptance Criteria:
        - Status code: 409 Conflict
        - Error message indicates domain is taken
        - No new institution created
        """
        payload = {
            "name": "Another Name",
            "domain": institution_a.domain  # Same domain as institution_a
        }

        response = client.post("/institutions", json=payload, headers={"X-Debug-User-Id": str(user_creator.id)})

        assert response.status_code == 409
        data = response.json()
        # Check for error code or message containing "DOMAIN_TAKEN" or similar
        assert "domain" in data or "DOMAIN_TAKEN" in str(data)


# ============================================================================
# AC-7: Nonexistent institution → 404
# ============================================================================


class TestNonexistentInstitution:
    """AC-7: Operations on nonexistent institution → 404 Not Found."""

    def test_invite_member_to_nonexistent_institution(self, client, user_coordinator):
        """
        AC-7: POST /institutions/{invalid_id}/members → 404.

        Acceptance Criteria:
        - Status code: 404 Not Found
        - No member created
        - Error indicates resource not found
        """
        nonexistent_id = "550e8400-e29b-41d4-a716-446655440099"

        payload = {
            "email": user_coordinator.email,
            "role": "COORDINATOR"
        }

        response = client.post(f"/institutions/{nonexistent_id}/members", json=payload, headers={"X-Debug-User-Id": str(user_coordinator.id)})

        assert response.status_code == 404


# ============================================================================
# AC-8: Duplicate link request → 409 Conflict
# ============================================================================


class TestDuplicateLinkRequest:
    """AC-8: Duplicate pending link request → 409 Conflict (not silent success)."""

    def test_duplicate_pending_link_request_409(self, session, user_student_a, talent_a, institution_a, client):
        """
        AC-8: Student creates second PENDING request for same institution → 409.

        Acceptance Criteria:
        - First request: 201 Created (PENDING)
        - Second request: 409 Conflict
        - No new PENDING record created
        - Error message indicates duplicate active request
        """
        from app.models import InstitutionLinkRequest

        # Create first PENDING request
        link_req_1 = InstitutionLinkRequest(
            talent_profile_id=talent_a.id,
            institution_id=institution_a.id,
            status="PENDING"
        )
        session.add(link_req_1)
        session.flush()

        # Assume auth: user_student_a

        # Attempt second request for same institution
        response = client.post(f"/institutions/{institution_a.id}/link-requests", headers={"X-Debug-User-Id": str(user_student_a.id)})

        # Expected: 409 Conflict
        assert response.status_code == 409

        # Verify: only one PENDING record exists (no new one created)
        pending_count = session.query(InstitutionLinkRequest).filter_by(
            talent_profile_id=talent_a.id,
            institution_id=institution_a.id,
            status="PENDING"
        ).count()
        assert pending_count == 1, "Only one PENDING request should exist"
