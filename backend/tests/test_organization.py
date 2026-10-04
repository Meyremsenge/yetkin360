"""
Organization endpoint tests (YET-9 — organization-domain-dogrulama).

Implements AC-1 through AC-11 (functional acceptance criteria) from atdd.md.

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Parametric tests for error cases
- Each AC has one or more test functions
- DNS resolver mocked (no real DNS queries in unit tests)

Status: Tests are RED/IMPORT-ERROR — implementation not yet written.
This is expected behavior. Tests implement behavior contract (ATDD).
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.models import Organization, OrganizationMember, User


# ============================================================================
# Fixtures: Users, Organizations
# ============================================================================


@pytest.fixture
def user_admin(session):
    """User who will create an organization (becomes ADMIN)."""
    user = User(email="admin@example.com", password_hash="hash_admin")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_member(session):
    """User who will be invited as MEMBER."""
    user = User(email="member@example.com", password_hash="hash_member")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_another_admin(session):
    """Another user to be invited as ADMIN."""
    user = User(email="another-admin@example.com", password_hash="hash_another_admin")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_no_role(session):
    """User with no organization role (for access denial tests)."""
    user = User(email="nouser@example.com", password_hash="hash_nouser")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def organization_a(session):
    """Test organization A (for tenant isolation tests)."""
    org = Organization(
        name="Test Organization A",
        domain="testorga.com",
        legal_id="ORG-A-001",
        verification_level="T1",
        status="ACTIVE"
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def organization_b(session):
    """Test organization B (for tenant isolation tests)."""
    org = Organization(
        name="Test Organization B",
        domain="testorgb.com",
        legal_id="ORG-B-001",
        verification_level="T1",
        status="ACTIVE"
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def organization_a_admin_member(session, organization_a, user_admin):
    """OrganizationMember: user_admin is ADMIN of organization_a."""
    member = OrganizationMember(
        organization_id=organization_a.id,
        user_id=user_admin.id,
        role="ADMIN",
        status="ACTIVE"
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def organization_a_member(session, organization_a, user_member):
    """OrganizationMember: user_member is MEMBER of organization_a."""
    member = OrganizationMember(
        organization_id=organization_a.id,
        user_id=user_member.id,
        role="MEMBER",
        status="ACTIVE"
    )
    session.add(member)
    session.flush()
    return member


# ============================================================================
# AC-1: Organization creation (POST /organizations) → 201, T1, caller becomes ADMIN
# ============================================================================


class TestOrganizationCreation:
    """AC-1: POST /organizations creates organization with T1 verification level."""

    def test_create_organization_basic(self, client, session, user_admin):
        """
        AC-1: POST /organizations with valid name → 201, caller becomes ADMIN.

        Acceptance Criteria:
        - Status code: 201 Created
        - Organization created with verification_level = T1
        - Caller (user_admin) automatically becomes OrganizationMember(role=ADMIN)
        """
        payload = {
            "name": "Test Corp",
            "domain": "testcorp.com",
            "legal_id": "ORG-TEST-001"
        }

        response = client.post("/organizations", json=payload, headers={"X-Debug-User-Id": str(user_admin.id)})

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        assert data["name"] == "Test Corp"
        assert data["domain"] == "testcorp.com"
        assert data["legal_id"] == "ORG-TEST-001"
        assert data["verification_level"] == "T1"
        assert data["status"] == "ACTIVE"

        # Verify: caller is automatically ADMIN
        organization_id = data["id"]
        org_member = session.query(OrganizationMember).filter_by(
            organization_id=organization_id,
            user_id=user_admin.id
        ).first()
        assert org_member is not None, "Caller should be added as OrganizationMember"
        assert org_member.role == "ADMIN", "Caller should have role ADMIN"

    def test_create_organization_without_domain(self, client, session, user_admin):
        """AC-1: POST /organizations without domain is valid (domain optional)."""
        payload = {
            "name": "Another Corp",
            "legal_id": "ORG-ANOTHER-001"
            # domain omitted
        }

        response = client.post("/organizations", json=payload, headers={"X-Debug-User-Id": str(user_admin.id)})

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Another Corp"
        assert data["verification_level"] == "T1"

    def test_create_organization_without_legal_id(self, client, session, user_admin):
        """AC-1: POST /organizations without legal_id is valid (legal_id optional)."""
        payload = {
            "name": "Yet Another Corp",
            "domain": "yetanother.com"
            # legal_id omitted
        }

        response = client.post("/organizations", json=payload, headers={"X-Debug-User-Id": str(user_admin.id)})

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Yet Another Corp"
        assert data["verification_level"] == "T1"

    @pytest.mark.parametrize("invalid_input,expected_status", [
        ({"domain": "test.com"}, 422),  # Missing name
        ({}, 422),  # Missing name and others
        ({"name": "", "domain": "test.com"}, 422),  # Empty name
    ])
    def test_create_organization_invalid_input(self, client, invalid_input, expected_status, user_admin):
        """AC-1 error case: Invalid input → 422 Unprocessable Entity."""
        response = client.post("/organizations", json=invalid_input, headers={"X-Debug-User-Id": str(user_admin.id)})

        assert response.status_code == expected_status

    def test_create_organization_tampering_verification_level(self, client, session, user_admin):
        """
        AC-S3: POST /organizations with verification_level in payload → ignored.

        Server must ignore client-supplied verification_level (always starts at T1).
        """
        payload = {
            "name": "Tamper Corp",
            "domain": "tamper.com",
            "verification_level": "T2"  # Attempted tampering
        }

        response = client.post("/organizations", json=payload, headers={"X-Debug-User-Id": str(user_admin.id)})

        assert response.status_code == 201
        data = response.json()
        assert data["verification_level"] == "T1", "Client-supplied verification_level must be ignored"

    def test_create_organization_tampering_verified_at(self, client, session, user_admin):
        """AC-S3: POST /organizations with verified_at in payload → ignored."""
        payload = {
            "name": "Tamper Corp 2",
            "domain": "tamper2.com",
            "verified_at": "2025-09-22T00:00:00Z"  # Attempted tampering
        }

        response = client.post("/organizations", json=payload, headers={"X-Debug-User-Id": str(user_admin.id)})

        assert response.status_code == 201
        data = response.json()
        assert data.get("verified_at") is None, "Client-supplied verified_at must be ignored"


# ============================================================================
# AC-2: Duplicate legal_id → 409 LEGAL_ID_TAKEN
# ============================================================================


class TestDuplicateLegalId:
    """AC-2: Creating organization with duplicate legal_id → 409 Conflict."""

    def test_duplicate_legal_id_returns_409(self, client, session, user_admin, organization_a):
        """
        AC-2: POST /organizations with legal_id matching existing org → 409.

        Acceptance Criteria:
        - Status code: 409 Conflict
        - Error indicates legal_id is taken
        - No new organization created
        """
        payload = {
            "name": "Another Name",
            "domain": "different.com",
            "legal_id": organization_a.legal_id  # Same legal_id as organization_a
        }

        response = client.post("/organizations", json=payload, headers={"X-Debug-User-Id": str(user_admin.id)})

        assert response.status_code == 409
        data = response.json()
        assert "legal_id" in str(data).lower() or "taken" in str(data).lower()


# ============================================================================
# AC-3: Invite member to organization (POST /organizations/{id}/members) → 201
# ============================================================================


class TestOrganizationMemberInvitation:
    """AC-3: POST /organizations/{id}/members invites member."""

    def test_admin_invites_member(self, session, user_admin, user_member, organization_a, organization_a_admin_member, client):
        """
        AC-3: ADMIN invites user as MEMBER → 202, member created, outbox event enqueued.

        Acceptance Criteria:
        - Status code: 202 Accepted (request queued)
        - Response: {"status": "queued"}
        - OrganizationMember record created with role=MEMBER
        - Outbox event is created (same transaction)
        """
        payload = {
            "email": user_member.email,
            "role": "MEMBER"
        }

        response = client.post(f"/organizations/{organization_a.id}/members", json=payload, headers={"X-Debug-User-Id": str(user_admin.id)})

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "queued"

        # Verify in database
        member = session.query(OrganizationMember).filter_by(
            organization_id=organization_a.id,
            user_id=user_member.id
        ).first()
        assert member is not None
        assert member.role == "MEMBER"

    def test_admin_invites_admin(self, session, user_admin, user_another_admin, organization_a, organization_a_admin_member, client):
        """AC-3: ADMIN invites another ADMIN → 202."""
        payload = {
            "email": user_another_admin.email,
            "role": "ADMIN"
        }

        response = client.post(f"/organizations/{organization_a.id}/members", json=payload, headers={"X-Debug-User-Id": str(user_admin.id)})

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "queued"

        member = session.query(OrganizationMember).filter_by(
            organization_id=organization_a.id,
            user_id=user_another_admin.id
        ).first()
        assert member is not None
        assert member.role == "ADMIN"

    @pytest.mark.parametrize("invalid_role", ["SUPERVISOR", "OWNER", "GUEST"])
    def test_invite_member_invalid_role(self, session, user_admin, user_member, organization_a, organization_a_admin_member, client, invalid_role):
        """
        AC-S2: POST /organizations/{id}/members with invalid role → 422.

        Only ADMIN and MEMBER roles allowed.
        """
        payload = {
            "email": user_member.email,
            "role": invalid_role
        }

        response = client.post(f"/organizations/{organization_a.id}/members", json=payload, headers={"X-Debug-User-Id": str(user_admin.id)})

        assert response.status_code == 422


# ============================================================================
# AC-4: Duplicate member invitation → 409 ALREADY_MEMBER
# ============================================================================


class TestDuplicateMemberInvitation:
    """AC-4: Inviting already-member user → 409 ALREADY_MEMBER."""

    def test_invite_existing_member_202_role_unchanged(self, session, user_admin, user_member, organization_a, organization_a_admin_member, organization_a_member, client):
        """
        AC-4: POST /organizations/{id}/members with user already a member → 202 (no-op).

        Acceptance Criteria:
        - Status code: 202 Accepted (no-op, role unchanged)
        - Response: {"status": "queued"}
        - Member's role remains unchanged (no-op case)
        - Only one member record exists (no duplicate)
        """
        # Record the current role before invitation
        member_before = session.query(OrganizationMember).filter_by(
            organization_id=organization_a.id,
            user_id=user_member.id
        ).first()
        role_before = member_before.role

        payload = {
            "email": user_member.email,
            "role": "MEMBER"
        }

        response = client.post(f"/organizations/{organization_a.id}/members", json=payload, headers={"X-Debug-User-Id": str(user_admin.id)})

        # Expect 202, not 409 (no-op behavior)
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "queued"

        # Verify role unchanged
        member_after = session.query(OrganizationMember).filter_by(
            organization_id=organization_a.id,
            user_id=user_member.id
        ).first()
        assert member_after.role == role_before, "Member's role should not change on duplicate invitation"

        # Verify only one member record exists
        member_count = session.query(OrganizationMember).filter_by(
            organization_id=organization_a.id,
            user_id=user_member.id
        ).count()
        assert member_count == 1


# ============================================================================
# AC-5: Free email domain rejected (POST /organizations/{id}/verify-domain)
# ============================================================================


class TestFreeEmailDomainRejection:
    """AC-5: verify-domain with free email provider domain → 400 FREE_EMAIL_DOMAIN."""

    @pytest.mark.parametrize(
        "free_domain",
        # Last four: YET-243 provider variants and a subdomain, rejected end to end.
        ["gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "googlemail.com", "live.com", "gmx.net", "mail.gmail.com"],
    )
    def test_verify_domain_free_email_provider_400(self, client, session, user_admin, free_domain):
        """
        AC-5: POST /organizations/{id}/verify-domain with free email domain → 400.

        Acceptance Criteria:
        - Status code: 400 Bad Request
        - Error code: FREE_EMAIL_DOMAIN
        - verification_level remains T1
        """
        # Create org with free email domain
        org = Organization(
            name="Free Email Org",
            domain=free_domain,
            verification_level="T1",
            status="ACTIVE"
        )
        session.add(org)
        session.flush()

        # Add user as ADMIN
        member = OrganizationMember(
            organization_id=org.id,
            user_id=user_admin.id,
            role="ADMIN",
            status="ACTIVE"
        )
        session.add(member)
        session.flush()

        response = client.post(f"/organizations/{org.id}/verify-domain", headers={"X-Debug-User-Id": str(user_admin.id)})

        assert response.status_code == 400
        data = response.json()
        assert "free_email_domain" in str(data).lower() or "FREE_EMAIL_DOMAIN" in str(data)

        # Verify: verification_level unchanged
        org_check = session.query(Organization).filter_by(id=org.id).first()
        assert org_check.verification_level == "T1"


# ============================================================================
# AC-6: Domain verification pending (no DNS TXT record yet)
# ============================================================================


class TestDomainVerificationPending:
    """AC-6: verify-domain without DNS TXT record → 200 {status:pending}."""

    def test_verify_domain_pending_no_txt_record(self, client, session, user_admin, organization_a, organization_a_admin_member):
        """
        AC-6 & AC-8: POST /organizations/{id}/verify-domain when TXT not found → 200 {status:pending}.

        Acceptance Criteria:
        - Status code: 200 OK (not error)
        - Response: {dns_txt_record: "...", status: "pending"}
        - verification_level remains T1
        - No verification_level change
        """
        with patch("app.services.organization.dns.resolver") as mock_resolver:
            # Mock DNS resolver to return no TXT record
            mock_resolver.resolve.side_effect = Exception("NXDOMAIN")

            response = client.post(f"/organizations/{organization_a.id}/verify-domain", headers={"X-Debug-User-Id": str(user_admin.id)})

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "pending"
            assert "dns_txt_record" in data

            # Verify: verification_level unchanged
            org_check = session.query(Organization).filter_by(id=organization_a.id).first()
            assert org_check.verification_level == "T1"

    def test_verify_domain_timeout_returns_pending(self, client, session, user_admin, organization_a, organization_a_admin_member):
        """
        AC-8: DNS query timeout (>3s) → 200 {status:pending}, not error.

        Acceptance Criteria:
        - Status code: 200 OK
        - Response: {status: "pending"}
        - verification_level remains T1
        """
        with patch("app.services.organization.dns.resolver") as mock_resolver:
            # Mock DNS resolver to timeout
            mock_resolver.resolve.side_effect = TimeoutError("DNS query timeout")

            response = client.post(f"/organizations/{organization_a.id}/verify-domain", headers={"X-Debug-User-Id": str(user_admin.id)})

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "pending"

            org_check = session.query(Organization).filter_by(id=organization_a.id).first()
            assert org_check.verification_level == "T1"


# ============================================================================
# AC-7: Domain verification success (DNS TXT record found)
# ============================================================================


class TestDomainVerificationSuccess:
    """AC-7: verify-domain with valid DNS TXT record → 200 {status:verified}, verification_level=T2."""

    def test_verify_domain_success_updates_to_t2(self, client, session, user_admin, organization_a, organization_a_admin_member):
        """
        AC-7: POST /organizations/{id}/verify-domain with valid TXT → 200 {status:verified}, T2.

        Acceptance Criteria:
        - Status code: 200 OK
        - Response: {status: "verified"}
        - organization.verification_level = T2
        - organization.verified_at is set
        - organization.verified_by_user_id = user_admin.id
        """
        # Set fixed token to ensure TXT record match
        organization_a.domain_verification_token = "test-fixed-token-123"
        session.flush()

        with patch("dns.resolver.Resolver") as mock_resolver_class:
            # Build expected TXT record with actual token
            expected_txt = f"yetkin360_verify_{organization_a.domain_verification_token}"

            # Create mock instance that will be returned by Resolver()
            mock_resolver_instance = MagicMock()
            mock_resolver_class.return_value = mock_resolver_instance

            # Mock DNS resolver to return matching TXT record
            mock_rdataset = MagicMock()
            mock_txt_data = MagicMock()
            mock_txt_data.strings = [expected_txt.encode()]
            mock_rdataset.__iter__ = lambda self: iter([mock_txt_data])
            mock_resolver_instance.resolve.return_value = mock_rdataset

            response = client.post(f"/organizations/{organization_a.id}/verify-domain", headers={"X-Debug-User-Id": str(user_admin.id)})

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "verified"

            # Verify database: T2 level, verified_at set, verified_by_user_id set
            org_check = session.query(Organization).filter_by(id=organization_a.id).first()
            assert org_check.verification_level == "T2"
            assert org_check.verified_at is not None
            assert org_check.verified_by_user_id == user_admin.id


# ============================================================================
# AC-9: Domain already verified in another organization → 409 DOMAIN_ALREADY_VERIFIED
# ============================================================================


class TestDomainAlreadyVerified:
    """AC-9: verify-domain for domain already T2 in another org → 409 DOMAIN_ALREADY_VERIFIED."""

    def test_verify_domain_already_verified_in_another_org_409(self, client, session, user_admin):
        """
        AC-9: POST /organizations/{id}/verify-domain when same domain is T2 in org_b → 409.

        Acceptance Criteria:
        - Status code: 409 Conflict
        - Error indicates domain already verified
        - Verification attempt is rejected
        """
        # Create organization A with domain test.com
        org_a = Organization(
            name="Org A",
            domain="test.com",
            verification_level="T1",
            status="ACTIVE"
        )
        session.add(org_a)
        session.flush()

        # Create organization B with same domain and T2 verification
        org_b = Organization(
            name="Org B",
            domain="test.com",
            verification_level="T2",
            verified_at=datetime.now(),  # Already verified
            status="ACTIVE"
        )
        session.add(org_b)
        session.flush()

        # Add user as ADMIN to org_a
        member = OrganizationMember(
            organization_id=org_a.id,
            user_id=user_admin.id,
            role="ADMIN",
            status="ACTIVE"
        )
        session.add(member)
        session.flush()

        # Set fixed token on org_a and mock DNS to return matching TXT record
        # This triggers AC-9 check when TXT is found
        org_a.domain_verification_token = "test-token-org-a"
        session.flush()

        with patch("dns.resolver.Resolver") as mock_resolver_class:
            expected_txt = f"yetkin360_verify_{org_a.domain_verification_token}"

            # Create mock instance that will be returned by Resolver()
            mock_resolver_instance = MagicMock()
            mock_resolver_class.return_value = mock_resolver_instance

            mock_rdataset = MagicMock()
            mock_txt_data = MagicMock()
            mock_txt_data.strings = [expected_txt.encode()]
            mock_rdataset.__iter__ = lambda self: iter([mock_txt_data])
            mock_resolver_instance.resolve.return_value = mock_rdataset

            response = client.post(f"/organizations/{org_a.id}/verify-domain", headers={"X-Debug-User-Id": str(user_admin.id)})

        assert response.status_code == 409
        data = response.json()
        assert "domain" in str(data).lower() or "verified" in str(data).lower()


# ============================================================================
# AC-10: Unauthorized user accessing endpoints → 404 (not 403)
# ============================================================================


class TestUnauthorizedAccess404:
    """AC-10: Unauthorized access (no ADMIN role) → 404 (not 403)."""

    def test_non_admin_invite_member_404(self, client, user_no_role, organization_a, user_member):
        """
        AC-10: MEMBER tries POST /organizations/{id}/members → 404 (not 403).

        Acceptance Criteria:
        - Status code: 404 Not Found (403 sızdırmama)
        - No member record created
        """
        payload = {
            "email": user_member.email,
            "role": "MEMBER"
        }

        response = client.post(f"/organizations/{organization_a.id}/members", json=payload, headers={"X-Debug-User-Id": str(user_no_role.id)})

        assert response.status_code == 404

    def test_non_admin_verify_domain_404(self, client, user_no_role, organization_a):
        """AC-10: Non-ADMIN tries verify-domain → 404."""
        response = client.post(f"/organizations/{organization_a.id}/verify-domain", headers={"X-Debug-User-Id": str(user_no_role.id)})

        assert response.status_code == 404

    def test_nonexistent_organization_invite_404(self, client, user_admin, user_member):
        """AC-10: POST /organizations/{invalid_id}/members → 404."""
        nonexistent_id = str(uuid.uuid4())

        payload = {
            "email": user_member.email,
            "role": "MEMBER"
        }

        response = client.post(f"/organizations/{nonexistent_id}/members", json=payload, headers={"X-Debug-User-Id": str(user_admin.id)})

        assert response.status_code == 404


# ============================================================================
# AC-11: Rate limiting (POST /organizations/{id}/verify-domain within 60s)
# ============================================================================


class TestRateLimitVerifyDomain:
    """AC-11: verify-domain called twice within 60s → 429 TOO_MANY_REQUESTS."""

    def test_verify_domain_rate_limit_429(self, client, session, user_admin, organization_a, organization_a_admin_member):
        """
        AC-11: Second verify-domain call within 60s → 429 TOO_MANY_REQUESTS.

        Acceptance Criteria:
        - First call: 200 OK (pending or verified)
        - Second call (within 60s): 429 Too Many Requests
        - DNS resolver not called twice (DoS protection)
        """
        with patch("app.services.organization.dns.resolver") as mock_resolver:
            mock_resolver.resolve.side_effect = Exception("NXDOMAIN")

            # First call
            response1 = client.post(f"/organizations/{organization_a.id}/verify-domain", headers={"X-Debug-User-Id": str(user_admin.id)})
            assert response1.status_code == 200

            # Second call (should be rate-limited)
            response2 = client.post(f"/organizations/{organization_a.id}/verify-domain", headers={"X-Debug-User-Id": str(user_admin.id)})
            assert response2.status_code == 429
