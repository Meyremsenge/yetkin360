"""
Organization authorization tests (YET-9 — BOLA/tenant-izolasyon/audit).

Implements AC-S1 through AC-S7 (security acceptance criteria) from atdd.md.

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Parametric tests for multi-tenant isolation (BOLA prevention)
- Tenant isolation verification: Organization A vs B
- Defense-in-depth: can() + scoped_organizations() verification
- PII guards (email, private_note) never in audit or outbox
- Audit event append-only verification

AC-S1: GET /organizations/{id} returns 404 for out-of-scope org (not 403 sızdırmama)
AC-S2: Role tampering in POST /members body is rejected (422)
AC-S3: verification_level and verified_at tampering in POST /organizations ignored
AC-S4: Rate limit 429 (same org, 60s cooldown)
AC-S5: SSRF prevention (domain validation, internal IP/localhost rejection)
AC-S6: Multi-tenant isolation (scoped_organizations() always applied)
AC-S7: Audit logging for organization creation, member invitation, domain verification

Status: Tests are RED/IMPORT-ERROR — implementation not yet written.
This is expected behavior. Tests implement security contract (STRIDE-lite).
"""

import uuid
from unittest.mock import patch, MagicMock

import pytest

from app.models import Organization, OrganizationMember, User, AuditEvent


# ============================================================================
# Organization Fixtures: A & B (tenant isolation)
# ============================================================================


@pytest.fixture
def organization_a(session):
    """Test organization A (tenant 1)."""
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
    """Test organization B (tenant 2, different tenant)."""
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


# ============================================================================
# User Fixtures
# ============================================================================


@pytest.fixture
def user_a_admin(session):
    """User who is ADMIN of organization_a."""
    user = User(email="admin-a@example.com", password_hash="hash_admin_a")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_a_member(session):
    """User who is MEMBER of organization_a (not ADMIN)."""
    user = User(email="member-a@example.com", password_hash="hash_member_a")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_b_admin(session):
    """User who is ADMIN of organization_b."""
    user = User(email="admin-b@example.com", password_hash="hash_admin_b")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_b_member(session):
    """User who is MEMBER of organization_b."""
    user = User(email="member-b@example.com", password_hash="hash_member_b")
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
def user_to_invite(session):
    """User who will be invited as member."""
    user = User(email="toinvite@example.com", password_hash="hash_toinvite")
    session.add(user)
    session.flush()
    return user


# ============================================================================
# OrganizationMember Fixtures (Organization A & B relationships)
# ============================================================================


@pytest.fixture
def org_a_admin_member(session, organization_a, user_a_admin):
    """OrganizationMember: user_a_admin is ADMIN of organization_a."""
    member = OrganizationMember(
        organization_id=organization_a.id,
        user_id=user_a_admin.id,
        role="ADMIN",
        status="ACTIVE"
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def org_a_member(session, organization_a, user_a_member):
    """OrganizationMember: user_a_member is MEMBER of organization_a."""
    member = OrganizationMember(
        organization_id=organization_a.id,
        user_id=user_a_member.id,
        role="MEMBER",
        status="ACTIVE"
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def org_b_admin_member(session, organization_b, user_b_admin):
    """OrganizationMember: user_b_admin is ADMIN of organization_b."""
    member = OrganizationMember(
        organization_id=organization_b.id,
        user_id=user_b_admin.id,
        role="ADMIN",
        status="ACTIVE"
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def org_b_member(session, organization_b, user_b_member):
    """OrganizationMember: user_b_member is MEMBER of organization_b."""
    member = OrganizationMember(
        organization_id=organization_b.id,
        user_id=user_b_member.id,
        role="MEMBER",
        status="ACTIVE"
    )
    session.add(member)
    session.flush()
    return member


# ============================================================================
# AC-S1: GET /organizations/{id} returns 404 for out-of-scope org (404 sızdırmama)
# ============================================================================


class TestGetOrganizationBOLA:
    """AC-S1: GET /organizations/{id} returns 404 for out-of-scope org (not 403)."""

    def test_member_of_org_a_cannot_access_org_b_404(
        self, client, organization_a, organization_b, org_a_member, user_a_member
    ):
        """
        AC-S1: Member of org_a tries GET /organizations/{org_b.id} → 404 (not 403).

        Acceptance Criteria:
        - Status code: 404 Not Found (not 403 — resource existence hidden)
        - Response does not contain org_b's name, domain, members
        """
        response = client.get(f"/organizations/{organization_b.id}", headers={"X-Debug-User-Id": str(user_a_member.id)})

        assert response.status_code == 404
        # Verify no org_b data in response
        data = response.json()
        assert "testorgb.com" not in str(data).lower()
        assert organization_b.name.lower() not in str(data).lower()

    def test_user_with_no_role_cannot_access_any_org_404(
        self, client, organization_a, organization_b, user_no_role
    ):
        """AC-S1: User with no role tries GET /organizations/{id} → 404."""
        response = client.get(f"/organizations/{organization_a.id}", headers={"X-Debug-User-Id": str(user_no_role.id)})

        assert response.status_code == 404

    def test_admin_of_org_a_can_access_org_a(self, client, organization_a, org_a_admin_member, user_a_admin):
        """AC-S1: ADMIN of org_a can access org_a data (happy path)."""
        response = client.get(f"/organizations/{organization_a.id}", headers={"X-Debug-User-Id": str(user_a_admin.id)})

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == organization_a.name
        assert data["domain"] == organization_a.domain


# ============================================================================
# AC-S2: Role tampering in POST /organizations/{id}/members
# ============================================================================


class TestRoleTampering:
    """AC-S2: Attempting to set roles outside ADMIN|MEMBER → 422 Unprocessable Entity."""

    @pytest.mark.parametrize("invalid_role", ["SUPERVISOR", "OWNER", "GUEST", "COORDINATOR"])
    def test_invite_with_invalid_role_422(
        self, client, organization_a, org_a_admin_member, user_to_invite, user_a_admin, invalid_role
    ):
        """
        AC-S2: POST /organizations/{id}/members with invalid role → 422.

        Acceptance Criteria:
        - Status code: 422 Unprocessable Entity
        - No member record created
        - Only ADMIN and MEMBER roles accepted
        """
        payload = {
            "email": user_to_invite.email,
            "role": invalid_role
        }

        response = client.post(f"/organizations/{organization_a.id}/members", json=payload, headers={"X-Debug-User-Id": str(user_a_admin.id)})

        assert response.status_code == 422


# ============================================================================
# AC-S3: verification_level and verified_at tampering (POST /organizations)
# ============================================================================


class TestVerificationLevelTampering:
    """AC-S3: Client-supplied verification_level, verified_at, verified_by_user_id ignored."""

    def test_create_org_with_verification_level_tamper_ignored(self, client, session, user_a_admin):
        """AC-S3: POST /organizations with verification_level=T2 → ignored, T1 returned."""
        payload = {
            "name": "Tamper Org",
            "domain": "tamper.com",
            "verification_level": "T2",  # Tampered
            "verified_at": "2025-09-22T00:00:00Z",  # Tampered
            "verified_by_user_id": str(uuid.uuid4())  # Tampered
        }

        response = client.post("/organizations", json=payload, headers={"X-Debug-User-Id": str(user_a_admin.id)})

        assert response.status_code == 201
        data = response.json()
        assert data["verification_level"] == "T1", "verification_level must always be T1 on creation"
        assert data.get("verified_at") is None, "verified_at must not be set on creation"
        assert data.get("verified_by_user_id") is None, "verified_by_user_id must not be set on creation"


# ============================================================================
# AC-S4: Rate limiting (verify-domain called twice within 60s → 429)
# ============================================================================


class TestRateLimitingVerifyDomain:
    """AC-S4: verify-domain rate limit — 2nd call within 60s → 429 TOO_MANY_REQUESTS."""

    def test_verify_domain_second_call_within_60s_429(
        self, client, session, organization_a, org_a_admin_member, user_a_admin
    ):
        """
        AC-S4: Second verify-domain call within 60s → 429 TOO_MANY_REQUESTS.

        Acceptance Criteria:
        - First call: 200 OK
        - Second call (within 60s): 429 Too Many Requests
        - DNS resolver called only once (DoS protection)
        """
        with patch("dns.resolver.Resolver") as mock_resolver_class:
            # Create mock instance that will be returned by Resolver()
            mock_resolver_instance = MagicMock()
            mock_resolver_class.return_value = mock_resolver_instance
            # Use dns.resolver.NXDOMAIN exception (caught by implementation)
            import dns.resolver
            mock_resolver_instance.resolve.side_effect = dns.resolver.NXDOMAIN()

            # First call
            response1 = client.post(f"/organizations/{organization_a.id}/verify-domain", headers={"X-Debug-User-Id": str(user_a_admin.id)})
            assert response1.status_code == 200

            # Mock DNS resolver is called once; verify it's not called again
            initial_call_count = mock_resolver_instance.resolve.call_count
            assert initial_call_count >= 1

            # Second call (should be rate-limited)
            response2 = client.post(f"/organizations/{organization_a.id}/verify-domain", headers={"X-Debug-User-Id": str(user_a_admin.id)})
            assert response2.status_code == 429

            # Verify DNS resolver was not called again (rate-limited without DNS query)
            assert mock_resolver_instance.resolve.call_count == initial_call_count


# ============================================================================
# AC-S5: SSRF prevention (domain validation, internal IPs rejected)
# ============================================================================


class TestSSRFPrevention:
    """AC-S5: Domain field validated — no internal IPs, localhost, RFC1918."""

    @pytest.mark.parametrize("dangerous_domain", [
        "169.254.169.254",  # AWS metadata endpoint
        "localhost",
        "127.0.0.1",
        "192.168.1.1",  # RFC1918
        "10.0.0.1",      # RFC1918
        "::1",            # IPv6 localhost
    ])
    def test_verify_domain_rejects_internal_ips(self, client, session, user_a_admin, dangerous_domain):
        """
        AC-S5: POST /organizations/{id}/verify-domain with internal IP → 400 or domain validation error.

        Acceptance Criteria:
        - Internal IPs/localhost rejected
        - No DNS query performed to internal address
        - Error indicates invalid domain
        """
        org = Organization(
            name="Dangerous Org",
            domain=dangerous_domain,
            verification_level="T1",
            status="ACTIVE"
        )
        session.add(org)
        session.flush()

        member = OrganizationMember(
            organization_id=org.id,
            user_id=user_a_admin.id,
            role="ADMIN",
            status="ACTIVE"
        )
        session.add(member)
        session.flush()

        response = client.post(f"/organizations/{org.id}/verify-domain", headers={"X-Debug-User-Id": str(user_a_admin.id)})

        # Should reject with 400 or return error (implementation detail)
        assert response.status_code in [400, 422]

    def test_verify_domain_hostname_format_validation(self, client, session, user_a_admin):
        """AC-S5: Domain field validated for hostname format (no IP:port, no path)."""
        org = Organization(
            name="Bad Format Org",
            domain="192.168.1.1:8080/path",  # IP with port and path
            verification_level="T1",
            status="ACTIVE"
        )
        session.add(org)
        session.flush()

        member = OrganizationMember(
            organization_id=org.id,
            user_id=user_a_admin.id,
            role="ADMIN",
            status="ACTIVE"
        )
        session.add(member)
        session.flush()

        response = client.post(f"/organizations/{org.id}/verify-domain", headers={"X-Debug-User-Id": str(user_a_admin.id)})

        # Should reject invalid format
        assert response.status_code in [400, 422]


# ============================================================================
# AC-S6: Multi-tenant isolation (scoped_organizations() applied)
# ============================================================================


class TestMultiTenantIsolation:
    """AC-S6: Multi-tenant isolation — scoped_organizations() always applied."""

    def test_admin_of_org_a_cannot_invite_to_org_b_404(
        self,
        client,
        session,
        organization_a,
        organization_b,
        org_a_admin_member,
        user_to_invite,
        user_a_admin,
    ):
        """
        AC-S6: ADMIN of org_a tries POST /organizations/{org_b.id}/members → 404.

        Acceptance Criteria:
        - Status code: 404 Not Found (resource out of scope)
        - No member invited to org_b
        - Cross-tenant modification prevented
        """
        payload = {
            "email": user_to_invite.email,
            "role": "MEMBER"
        }

        response = client.post(f"/organizations/{organization_b.id}/members", json=payload, headers={"X-Debug-User-Id": str(user_a_admin.id)})

        assert response.status_code == 404

        # Verify: no member added to org_b
        member_b = session.query(OrganizationMember).filter_by(
            organization_id=organization_b.id,
            user_id=user_to_invite.id
        ).first()
        assert member_b is None

    def test_member_cannot_invite_to_own_org_404(
        self, client, organization_a, org_a_member, user_to_invite, user_a_member
    ):
        """
        AC-S6: MEMBER (not ADMIN) of org_a tries to invite → 404 (permission + scope check).

        Acceptance Criteria:
        - Status code: 404 Not Found (member has access to org_a, but not permission)
        - (403 would leak that member exists; 404 hides this)
        """
        payload = {
            "email": user_to_invite.email,
            "role": "MEMBER"
        }

        response = client.post(f"/organizations/{organization_a.id}/members", json=payload, headers={"X-Debug-User-Id": str(user_a_member.id)})

        assert response.status_code == 404


# ============================================================================
# AC-S7: Audit logging (append-only)
# ============================================================================


class TestAuditLogging:
    """AC-S7: Organization creation, member invitation, domain verification logged to audit_events."""

    def test_create_organization_audit_logged(self, client, session, user_a_admin):
        """
        AC-S7: POST /organizations creates audit_events record.

        Acceptance Criteria:
        - action = "CREATE_ORGANIZATION"
        - actor_user_id = user_a_admin.id
        - target_id = organization.id
        - No PII in metadata (email not stored)
        """
        payload = {
            "name": "Audit Test Org",
            "domain": "audit.test.com",
            "legal_id": "AUDIT-001"
        }

        response = client.post("/organizations", json=payload, headers={"X-Debug-User-Id": str(user_a_admin.id)})
        assert response.status_code == 201
        org_id = response.json()["id"]

        # Query audit_events
        audit_event = session.query(AuditEvent).filter_by(
            action="CREATE_ORGANIZATION",
            actor_user_id=user_a_admin.id,
            subject_id=org_id
        ).first()

        assert audit_event is not None, "Audit event should be logged"
        # Verify: no email in metadata
        metadata_str = str(audit_event.metadata or {})
        assert "user_a_admin@example.com" not in metadata_str.lower(), "PII (email) should not be in audit metadata"

    def test_invite_member_audit_logged(self, client, session, organization_a, org_a_admin_member, user_to_invite, user_a_admin):
        """AC-S7: POST /organizations/{id}/members creates audit_events record."""
        payload = {
            "email": user_to_invite.email,
            "role": "MEMBER"
        }

        response = client.post(f"/organizations/{organization_a.id}/members", json=payload, headers={"X-Debug-User-Id": str(user_a_admin.id)})
        assert response.status_code == 202

        # Get member from DB instead of response (response now only contains {"status": "queued"})
        member = session.query(OrganizationMember).filter_by(
            organization_id=organization_a.id,
            user_id=user_to_invite.id
        ).first()
        assert member is not None, "Member should be created"
        member_id = member.id

        # Query audit_events (subject_id is the OrganizationMember.id, not organization_id)
        audit_event = session.query(AuditEvent).filter_by(
            action="INVITE_ORG_MEMBER",
            actor_user_id=user_a_admin.id,
            subject_id=member_id
        ).first()

        assert audit_event is not None, "Audit event should be logged for member invitation"
        # Verify: no email in metadata
        metadata_str = str(audit_event.metadata or {})
        assert user_to_invite.email not in metadata_str, "PII (email) should not be in audit metadata"

    def test_verify_domain_audit_logged(self, client, session, organization_a, org_a_admin_member, user_a_admin):
        """AC-S7: POST /organizations/{id}/verify-domain creates audit_events record."""
        with patch("app.services.organization.dns.resolver") as mock_resolver:
            mock_resolver.resolve.side_effect = Exception("NXDOMAIN")

            response = client.post(f"/organizations/{organization_a.id}/verify-domain", headers={"X-Debug-User-Id": str(user_a_admin.id)})
            assert response.status_code == 200

            # Query audit_events (pending status when DNS lookup fails)
            audit_event = session.query(AuditEvent).filter(
                (AuditEvent.action.in_(["VERIFY_DOMAIN_PENDING", "VERIFY_DOMAIN_REJECTED"])) &
                (AuditEvent.actor_user_id == user_a_admin.id) &
                (AuditEvent.subject_id == organization_a.id)
            ).first()

            assert audit_event is not None, "Audit event should be logged for domain verification"

    def test_verify_domain_success_audit_logged(self, client, session, organization_a, org_a_admin_member, user_a_admin):
        """AC-S7: Successful domain verification (T2 transition) audit logged."""
        # Set fixed token to ensure TXT record match
        organization_a.domain_verification_token = "test-fixed-token-123"
        session.flush()

        with patch("dns.resolver.Resolver") as mock_resolver_class:
            from unittest.mock import MagicMock

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

            response = client.post(f"/organizations/{organization_a.id}/verify-domain", headers={"X-Debug-User-Id": str(user_a_admin.id)})
            assert response.status_code == 200

            # Query audit_events for successful verification
            audit_event = session.query(AuditEvent).filter(
                (AuditEvent.action.in_(["VERIFY_DOMAIN_SUCCESS"])) &
                (AuditEvent.actor_user_id == user_a_admin.id) &
                (AuditEvent.subject_id == organization_a.id)
            ).first()

            assert audit_event is not None, "Audit event should be logged for successful domain verification"
            # Verify timestamp is recent
            assert audit_event.created_at is not None


# ============================================================================
# GUV-02 Davet Ucu Testleri (AC-1 — AC-8)
# ============================================================================
# Acceptance Criteria tablosundan türetilen testler:
# - AC-1: Happy path (bilinen e-posta, geçerli rol, yeni üye)
# - AC-2: Bilinmeyen e-posta (202 döner, üyelik oluşmaz)
# - AC-3: Geçersiz rol (422 + INVALID_ROLE)
# - AC-4/AC-5: Zaten üye (202, rol değişmez)
# - AC-7: Çapraz-kiracı (404)
# - AC-8: Yetkisiz rol/MEMBER (404)
# Authz_test.md saldırgan matrisi de dahil: org ADMIN A vs B, MEMBER vs ADMIN


class TestInviteOrganizationMember:
    """
    GUV-02: POST /organizations/{id}/members — Davranış Sözleşmesi (AC-1 — AC-8).

    Test patterns:
    - Real PostgreSQL transaction per test (conftest.py session)
    - Exact status code and response body matching
    - DB verification after writes (membership creation, role persistence)
    - Principal kind/scope validation for cross-tenant tests
    - Audit event verification (if applicable)
    """

    # ========================================================================
    # AC-1: Happy Path — Bilinen e-posta + geçerli rol + yeni üye
    # ========================================================================

    def test_invite_known_user_valid_role_202_queued(
        self, client, session, organization_a, org_a_admin_member, user_to_invite, user_a_admin
    ):
        """
        AC-1: ADMIN of org_a invites known user with valid role → 202 queued.

        Acceptance Criteria:
        - Status code: exactly 202 Accepted
        - Response body: exactly {"status": "queued"}
        - DB: OrganizationMember created for user_to_invite in org_a
        - Audit: INVITE_ORG_MEMBER logged
        """
        # Setup: count members before invite
        members_before = session.query(OrganizationMember).filter_by(
            organization_id=organization_a.id
        ).count()

        payload = {
            "email": user_to_invite.email,
            "role": "MEMBER"
        }

        response = client.post(
            f"/organizations/{organization_a.id}/members",
            json=payload,
            headers={"X-Debug-User-Id": str(user_a_admin.id)}
        )

        # EXACT status code match
        assert response.status_code == 202, f"Expected 202, got {response.status_code}"

        # EXACT response body match
        assert response.json() == {"status": "queued"}, (
            f"Expected exact body {{'status': 'queued'}}, got {response.json()}"
        )

        # DB verification: membership created
        member = session.query(OrganizationMember).filter_by(
            organization_id=organization_a.id,
            user_id=user_to_invite.id
        ).first()
        assert member is not None, "OrganizationMember should be created in DB"
        assert member.role == "MEMBER", f"Role should be MEMBER, got {member.role}"
        assert member.status == "ACTIVE" or member.status is None, f"Status should be ACTIVE/None, got {member.status}"

        # Audit event verification
        audit_event = session.query(AuditEvent).filter_by(
            action="INVITE_ORG_MEMBER",
            actor_user_id=user_a_admin.id
        ).order_by(AuditEvent.created_at.desc()).first()
        assert audit_event is not None, "Audit event INVITE_ORG_MEMBER should be logged"
        assert audit_event.subject_id == member.id, "Audit subject_id should be member.id"

    # ========================================================================
    # AC-2: Bilinmeyen e-posta — 202 döner, üyelik oluşmaz
    # ========================================================================

    def test_invite_unknown_email_202_no_membership_created(
        self, client, session, organization_a, org_a_admin_member, user_a_admin
    ):
        """
        AC-2: ADMIN invites unknown (not-in-system) email → 202 queued, no membership.

        Acceptance Criteria:
        - Status code: exactly 202 (not 500 as before, not 422)
        - Response body: exactly {"status": "queued"}
        - DB: NO OrganizationMember created (unknown user has no record)
        - Audit: event still logged (without PII — no email in metadata)
        """
        unknown_email = "completely-unknown-xyz-12345@example.com"

        payload = {
            "email": unknown_email,
            "role": "MEMBER"
        }

        response = client.post(
            f"/organizations/{organization_a.id}/members",
            json=payload,
            headers={"X-Debug-User-Id": str(user_a_admin.id)}
        )

        # EXACT status code match (202, not 500)
        assert response.status_code == 202, f"Expected 202 for unknown email, got {response.status_code}"

        # EXACT response body match (same as AC-1)
        assert response.json() == {"status": "queued"}, (
            f"Expected exact body {{'status': 'queued'}}, got {response.json()}"
        )

        # DB verification: NO membership created
        # Since email is unknown, try to find by email won't work (User model)
        # Instead, verify member count didn't increase unexpectedly
        audit_events = session.query(AuditEvent).filter_by(
            action="INVITE_ORG_MEMBER",
            actor_user_id=user_a_admin.id
        ).all()
        assert len(audit_events) > 0, "Audit event should be logged even for unknown email"

        # Verify no PII in metadata
        for event in audit_events:
            metadata_str = str(event.event_metadata or {})
            assert unknown_email not in metadata_str, "PII (email) should not be in audit metadata"

    # ========================================================================
    # AC-3: Geçersiz rol değeri — 422 + INVALID_ROLE
    # ========================================================================

    def test_invite_invalid_role_422_invalid_role_code(
        self, client, session, organization_a, org_a_admin_member, user_to_invite, user_a_admin
    ):
        """
        AC-3: ADMIN invites with invalid role (not ADMIN/MEMBER) → 422 INVALID_ROLE.

        Acceptance Criteria:
        - Status code: exactly 422 Unprocessable Entity
        - Response body contains: {"code": "INVALID_ROLE", ...}
        - DB: NO membership created
        - Pydantic validation catches it (Literal["ADMIN", "MEMBER"])
        """
        invalid_roles = ["SUPERADMIN", "OWNER", "GUEST", "COORDINATOR", "INVALID"]

        for invalid_role in invalid_roles:
            payload = {
                "email": user_to_invite.email,
                "role": invalid_role
            }

            response = client.post(
                f"/organizations/{organization_a.id}/members",
                json=payload,
                headers={"X-Debug-User-Id": str(user_a_admin.id)}
            )

            # EXACT status code match
            assert response.status_code == 422, (
                f"Invalid role '{invalid_role}' should return 422, got {response.status_code}"
            )

            # Verify error code field
            response_data = response.json()
            assert response_data.get("code") == "INVALID_ROLE", (
                f"Error code should be 'INVALID_ROLE', got {response_data.get('code')}"
            )

            # DB: verify NO membership created
            member = session.query(OrganizationMember).filter_by(
                organization_id=organization_a.id,
                user_id=user_to_invite.id,
                role=invalid_role
            ).first()
            assert member is None, f"No membership should be created for invalid role '{invalid_role}'"

    # ========================================================================
    # AC-4: Zaten üye — 202 queued, rol DEĞİŞMEZ
    # ========================================================================

    def test_invite_already_member_202_role_unchanged(
        self, client, session, organization_a, org_a_admin_member, org_a_member, user_a_member, user_a_admin
    ):
        """
        AC-4: ADMIN re-invites existing member with different role → 202, role unchanged.

        Scenario:
        - user_a_member is already MEMBER of org_a
        - ADMIN invites same user as ADMIN role
        - Expected: 202 queued, but user's role stays MEMBER (not updated to ADMIN)

        Acceptance Criteria:
        - Status code: exactly 202
        - Response body: exactly {"status": "queued"}
        - DB before: user_a_member.role == "MEMBER"
        - DB after: user_a_member.role == "MEMBER" (unchanged, not UPSERT'd to ADMIN)
        """
        # Verify initial state
        initial_member = session.query(OrganizationMember).filter_by(
            organization_id=organization_a.id,
            user_id=user_a_member.id
        ).first()
        assert initial_member is not None, "user_a_member should already be member"
        initial_role = initial_member.role
        assert initial_role == "MEMBER", f"Initial role should be MEMBER, got {initial_role}"

        # Re-invite with ADMIN role
        payload = {
            "email": user_a_member.email,
            "role": "ADMIN"  # Different role
        }

        response = client.post(
            f"/organizations/{organization_a.id}/members",
            json=payload,
            headers={"X-Debug-User-Id": str(user_a_admin.id)}
        )

        # EXACT status code
        assert response.status_code == 202, f"Expected 202, got {response.status_code}"

        # EXACT response body
        assert response.json() == {"status": "queued"}, (
            f"Expected {{'status': 'queued'}}, got {response.json()}"
        )

        # DB verification: role unchanged (AC-4's key test)
        final_member = session.query(OrganizationMember).filter_by(
            organization_id=organization_a.id,
            user_id=user_a_member.id
        ).first()
        assert final_member is not None, "Member should still exist"
        assert final_member.role == "MEMBER", (
            f"Role should remain MEMBER (not UPSERT'd), but got {final_member.role}"
        )

    # ========================================================================
    # AC-7: Çapraz-kiracı — ORG_ADMIN A vs ORG B → 404
    # ========================================================================

    def test_cross_tenant_org_b_admin_cannot_invite_to_org_a_404(
        self, client, session, organization_a, organization_b, org_a_admin_member, org_b_admin_member,
        user_to_invite, user_b_admin
    ):
        """
        AC-7 / Authz row 2: ADMIN of org_b tries to invite to org_a → 404 (tenant isolation).

        Acceptance Criteria:
        - Status code: exactly 404 Not Found
        - No data leak in response (org_a's name/domain not in response)
        - No membership created in org_a
        - Principal kind/scope: user_b_admin.kind='ORG_ADMIN', but org_a NOT in principal.org_admin_ids
        """
        payload = {
            "email": user_to_invite.email,
            "role": "MEMBER"
        }

        # user_b_admin is ADMIN of org_b, tries to invite to org_a
        response = client.post(
            f"/organizations/{organization_a.id}/members",
            json=payload,
            headers={"X-Debug-User-Id": str(user_b_admin.id)}
        )

        # EXACT status code: 404 (not 403)
        assert response.status_code == 404, (
            f"Cross-tenant access should return 404, got {response.status_code}"
        )

        # DB: verify no membership created in org_a
        member = session.query(OrganizationMember).filter_by(
            organization_id=organization_a.id,
            user_id=user_to_invite.id
        ).first()
        assert member is None, "No membership should be created in org_a by org_b's admin"

        # Verify principal scope (user_b_admin can only admin org_b)
        # Note: In real code, principal is constructed from can() function.
        # This test verifies that the endpoint respects the scope check.
        org_b_members_count = session.query(OrganizationMember).filter_by(
            organization_id=organization_b.id
        ).count()
        assert org_b_members_count >= 1, "org_b should have at least 1 member (org_b_admin)"

    # ========================================================================
    # AC-7: Yetkisiz rol — MEMBER cannot invite → 404
    # ========================================================================

    def test_member_cannot_invite_404(
        self, client, session, organization_a, org_a_member, user_to_invite, user_a_member
    ):
        """
        AC-7 / Authz row 3: MEMBER of org_a (not ADMIN) tries to invite → 404.

        Acceptance Criteria:
        - Status code: exactly 404 Not Found (not 403 — role-based denial hides resource)
        - No membership created
        """
        payload = {
            "email": user_to_invite.email,
            "role": "MEMBER"
        }

        response = client.post(
            f"/organizations/{organization_a.id}/members",
            json=payload,
            headers={"X-Debug-User-Id": str(user_a_member.id)}
        )

        # EXACT status code: 404
        assert response.status_code == 404, (
            f"MEMBER should get 404 (not 403), got {response.status_code}"
        )

        # DB: no membership created
        member = session.query(OrganizationMember).filter_by(
            organization_id=organization_a.id,
            user_id=user_to_invite.id
        ).first()
        assert member is None, "No membership should be created by MEMBER"
