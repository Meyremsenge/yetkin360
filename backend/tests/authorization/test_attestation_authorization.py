"""
Attestation authorization tests (PLAN 2.8 — yet-70-attestation-verified-experience-uretimi).

Threat-model security tests for POST /engagements/{id}/attestations:
- AC-S1: attestor_user_id body'den tamperlense bile oturumdan alındığını test et
- AC-S2: cross-institution (başka üniversite) 404 döner — scoped_engagements() kullanılır
- AC-S3: self-attestation (attestor = talent) 409 döner — DB CHECK constraint ikinci savunma hattı
- AC-S4: claim_type manipülasyonu (extra alanlar) — Pydantic extra="forbid"
- AC-S5: race condition — iki concurrent POST, sadece biri 201, diğeri 409

Coverage Target: Threat-model scenarios (AC-S1/S2/S3/S4/S5) + scope enforcement.

Status: Tests are RED (expected) — implementation not yet available.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from app.models import (
    User,
    TalentProfile,
    Organization,
    Institution,
    Engagement,
    InstitutionMember,
    OrganizationMember,
    Deliverable,
)

# Import will fail until Attestation/VerifiedExperience models are implemented
try:
    from app.models import Attestation, VerifiedExperience
except ImportError:
    Attestation = None
    VerifiedExperience = None


# ============================================================================
# Fixtures (shared with test_attestation.py, defined locally for isolation)
# ============================================================================


@pytest.fixture
def user_talent_authz(session):
    """Talent user for authorization tests."""
    user = User(email="talent.authz@example.com", password_hash="hash_talent")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_inst_coord_authz(session):
    """INST:COORD user for authorization tests."""
    user = User(email="coord.authz@example.com", password_hash="hash_coord")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_attacker_coord_authz(session):
    """INST:COORD user from different institution (attacker trying to access cross-tenant resource)."""
    user = User(email="attacker.coord.authz@example.com", password_hash="hash_attacker")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_self_attestor_authz(session):
    """User who is both coordinator AND talent (self-attestation risk)."""
    user = User(email="self.attestor.authz@example.com", password_hash="hash_self")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def organization_authz(session):
    """Organization A for authorization tests (T2+ verified)."""
    org = Organization(
        name="Test Org Authz",
        domain="testorgauthz.example.com",
        legal_id="ORG-AUTHZ-001",
        verification_level="T2",
        status="ACTIVE",
        verified_at=datetime.utcnow() - timedelta(days=30),
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def organization_attacker_authz(session):
    """Organization B for cross-tenant isolation test."""
    org = Organization(
        name="Attacker Org Authz",
        domain="attacker.org.example.com",
        legal_id="ORG-ATTACKER-001",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def institution_authz(session):
    """Institution A for authorization tests."""
    inst = Institution(
        name="Test Institution Authz",
        domain="testinstauthorz.example.com",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def institution_attacker_authz(session):
    """Institution B for cross-institution isolation test."""
    inst = Institution(
        name="Attacker Institution Authz",
        domain="attacker.inst.example.com",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def talent_authz(session, user_talent_authz, institution_authz):
    """Talent profile for authorization tests."""
    profile = TalentProfile(
        user_id=user_talent_authz.id,
        institution_id=institution_authz.id,
        full_name="Talent Authz",
        visibility="PRIVATE",
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_self_attestor_authz(session, user_self_attestor_authz, institution_authz):
    """Talent profile for self-attestor (same user who will be coordinator)."""
    profile = TalentProfile(
        user_id=user_self_attestor_authz.id,
        institution_id=institution_authz.id,
        full_name="Self Attestor Talent",
        visibility="PRIVATE",
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def inst_coord_authz(session, institution_authz, user_inst_coord_authz):
    """INST:COORD member for authorization tests."""
    coord = InstitutionMember(
        institution_id=institution_authz.id,
        user_id=user_inst_coord_authz.id,
        role="COORDINATOR",
    )
    session.add(coord)
    session.flush()
    return coord


@pytest.fixture
def inst_coord_self_attestor_authz(session, institution_authz, user_self_attestor_authz):
    """INST:COORD who is also the talent (for self-attestation bypass test)."""
    coord = InstitutionMember(
        institution_id=institution_authz.id,
        user_id=user_self_attestor_authz.id,
        role="COORDINATOR",
    )
    session.add(coord)
    session.flush()
    return coord


@pytest.fixture
def inst_coord_attacker_authz(session, institution_attacker_authz, user_attacker_coord_authz):
    """INST:COORD from attacker institution (for cross-institution isolation test)."""
    coord = InstitutionMember(
        institution_id=institution_attacker_authz.id,
        user_id=user_attacker_coord_authz.id,
        role="COORDINATOR",
    )
    session.add(coord)
    session.flush()
    return coord


@pytest.fixture
def skill_authz(session):
    """Test skill for authorization tests."""
    from app.models import Skill
    skill = Skill(
        slug="skill-authz",
        name_tr="Test Skill",
        name_en="Test Skill",
        category="SOFT",
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def engagement_evaluated_authz(session, talent_authz, organization_authz, institution_authz):
    """EVALUATED engagement for authorization tests."""
    now = datetime.utcnow()
    engagement = Engagement(
        talent_id=talent_authz.id,
        organization_id=organization_authz.id,
        institution_id=institution_authz.id,
        kind="INTERNSHIP",
        title="Auth Test Engagement",
        status="EVALUATED",
        version=1,
        started_on=now - timedelta(days=35),
        ended_on=now - timedelta(days=1),
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_self_attestor_authz(session, talent_self_attestor_authz, organization_authz, institution_authz):
    """EVALUATED engagement for self-attestor (talent and coordinator are same user)."""
    now = datetime.utcnow()
    engagement = Engagement(
        talent_id=talent_self_attestor_authz.id,
        organization_id=organization_authz.id,
        institution_id=institution_authz.id,
        kind="INTERNSHIP",
        title="Self Attestor Engagement",
        status="EVALUATED",
        version=1,
        started_on=now - timedelta(days=35),
        ended_on=now - timedelta(days=1),
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_attacker_institution_authz(session, talent_authz, organization_attacker_authz, institution_attacker_authz):
    """EVALUATED engagement in attacker institution (for cross-institution test)."""
    now = datetime.utcnow()
    engagement = Engagement(
        talent_id=talent_authz.id,
        organization_id=organization_attacker_authz.id,
        institution_id=institution_attacker_authz.id,
        kind="INTERNSHIP",
        title="Attacker Institution Engagement",
        status="EVALUATED",
        version=1,
        started_on=now - timedelta(days=35),
        ended_on=now - timedelta(days=1),
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def deliverable_authz(session, engagement_evaluated_authz, skill_authz, user_talent_authz):
    """Deliverable for authorization test engagement."""
    deliverable = Deliverable(
        engagement_id=engagement_evaluated_authz.id,
        title="Test Deliverable",
        description="Test deliverable for auth tests",
        submitted_by_user_id=user_talent_authz.id,
        submitted_at=datetime.now(timezone.utc),
    )
    session.add(deliverable)
    session.flush()
    return deliverable


@pytest.fixture
def user_org_member_non_admin_authz(session):
    """ORG_MEMBER (not ADMIN) user for authorization tests."""
    user = User(email="org_member_nonAdmin.authz@example.com", password_hash="hash_member")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def org_member_non_admin_authz(session, organization_authz, user_org_member_non_admin_authz):
    """ORG_MEMBER (role=MEMBER, not ADMIN) for authorization tests."""
    member = OrganizationMember(
        organization_id=organization_authz.id,
        user_id=user_org_member_non_admin_authz.id,
        role="MEMBER",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def engagement_org_no_institution_authz(session, talent_authz, organization_authz):
    """EVALUATED engagement with institution_id NULL (platform collaboration, no institution)."""
    now = datetime.utcnow()
    engagement = Engagement(
        talent_id=talent_authz.id,
        organization_id=organization_authz.id,
        institution_id=None,  # NULL institution_id
        kind="INTERNSHIP",
        title="Platform Collaboration (No Institution)",
        status="EVALUATED",
        version=1,
        started_on=now - timedelta(days=35),
        ended_on=now - timedelta(days=1),
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def deliverable_org_no_institution_authz(session, engagement_org_no_institution_authz, skill_authz, user_talent_authz):
    """Deliverable for organization (no institution) engagement."""
    deliverable = Deliverable(
        engagement_id=engagement_org_no_institution_authz.id,
        title="Platform Collaboration Deliverable",
        description="Test deliverable for org-only engagement",
        submitted_by_user_id=user_talent_authz.id,
        submitted_at=datetime.now(timezone.utc),
    )
    session.add(deliverable)
    session.flush()
    return deliverable


@pytest.fixture
def user_inst_admin_non_coordinator_authz(session):
    """INST_ADMIN (not COORDINATOR) user for authorization tests."""
    user = User(email="inst_admin_nonCoord.authz@example.com", password_hash="hash_admin")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def inst_admin_non_coordinator_authz(session, institution_authz, user_inst_admin_non_coordinator_authz):
    """INST_ADMIN (role=ADMIN, not COORDINATOR) for authorization tests."""
    admin = InstitutionMember(
        institution_id=institution_authz.id,
        user_id=user_inst_admin_non_coordinator_authz.id,
        role="ADMIN",
    )
    session.add(admin)
    session.flush()
    return admin


# ============================================================================
# AC-S1: Tampering — attestor_user_id from body ignored
# ============================================================================


class TestAttestationS1Tampering:
    """
    AC-S1: Even if attacker sends attestor_user_id in request body, server ignores it.
    Actual attestor_user_id always derives from authenticated principal (X-Debug-User-Id header).
    """

    def test_attestation_attestor_tampering_ignored_201(
        self, client, session, user_inst_coord_authz, inst_coord_authz,
        engagement_evaluated_authz, deliverable_authz
    ):
        """
        AC-S1: Diana (INST:COORD) submits attestation, but request body contains fake attestor_user_id.
        Expected: Server rejects or ignores fake attestor_user_id, always uses principal from X-Debug-User-Id.

        Acceptance Criteria:
        - Status code: 201 Created (field silently ignored) or 422 Unprocessable Entity (extra field rejected outright)
        - Either response is safe: fake_user_id never becomes attestor_user_id
        - If 201: Attestation.attestor_user_id must be Diana's id (from header), NOT fake id from body
        """
        fake_user_id = str(uuid4())

        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,
            "attestor_user_id": fake_user_id,  # Attacker tries to set different user
        }

        response = client.post(
            f"/engagements/{engagement_evaluated_authz.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_authz.id)},
        )

        # Either 422 (extra field rejected outright) or 201 (field silently ignored) —
        # both are safe: fake_user_id never becomes attestor_user_id.
        assert response.status_code in [201, 422], \
            f"Expected 201 or 422, got {response.status_code}: {response.text}"

        if response.status_code == 201:
            # If accepted, verify the REAL principal's id was used, not the fake one
            if Attestation:
                att_id = response.json()["id"]
                att = session.query(Attestation).filter_by(id=att_id).first()
                assert att is not None
                assert att.attestor_user_id == user_inst_coord_authz.id, \
                    f"attestor_user_id must come from session (header), not request body: got {att.attestor_user_id}"
                assert att.attestor_user_id != fake_user_id, \
                    "Fake attestor_user_id from body must never be used"


# ============================================================================
# AC-S2: Elevation/Tenant Isolation — cross-institution 404
# ============================================================================


class TestAttestationS2TenantIsolation:
    """
    AC-S2: INST:COORD from different institution cannot access engagement.
    scoped_engagements() filters by institution → 404 NOT_FOUND.
    """

    def test_attestation_cross_institution_denied_404(
        self, client, session, user_attacker_coord_authz, inst_coord_attacker_authz,
        engagement_evaluated_authz
    ):
        """
        AC-S2: Frank (INST:COORD of institution_b) tries to attest engagement in institution_a → 404.
        scoped_engagements() returns None (outside scope), EngagementNotFoundError → 404 response.

        Acceptance Criteria:
        - Status code: 404 Not Found (not 403, not 422)
        - Error code: NOT_FOUND
        - No Attestation/VerifiedExperience written
        - kaynağın varlığı cross-tenant user'a sızdırılmaz
        """
        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_evaluated_authz.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_attacker_coord_authz.id)},
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") == "NOT_FOUND", \
            f"Expected NOT_FOUND, got {error_obj.get('code')}"


# ============================================================================
# AC-S3: Tampering — Self-Attestation Bypass
# ============================================================================


class TestAttestationS3SelfAttestationForbidden:
    """
    AC-S3: User cannot attest own skill claim (attestor = talent).
    Service-layer check catches this → 409 CONFLICT (SELF_ATTESTATION_FORBIDDEN).
    DB CHECK constraint (attestor_user_id != talent_id) is second defense line.
    """

    def test_attestation_self_attestation_409(
        self, client, session, user_self_attestor_authz, inst_coord_self_attestor_authz,
        engagement_self_attestor_authz, deliverable_authz
    ):
        """
        AC-S3: User X is both talent and coordinator of own engagement.
        When User X tries to attest own engagement → 409 CONFLICT (SELF_ATTESTATION_FORBIDDEN).

        Acceptance Criteria:
        - Status code: 409 Conflict
        - Error code: SELF_ATTESTATION_FORBIDDEN
        - No Attestation/VerifiedExperience written
        - DB CHECK constraint (attestor_user_id != talent_id) is second defense: if service check fails,
          DB throws IntegrityError → converted to same 409 response
        """
        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_self_attestor_authz.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_self_attestor_authz.id)},
        )

        assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") == "SELF_ATTESTATION_FORBIDDEN", \
            f"Expected SELF_ATTESTATION_FORBIDDEN, got {error_obj.get('code')}"


# ============================================================================
# AC-S4: Tampering — Claim_type/Downgrade Manipülasyonu
# ============================================================================


class TestAttestationS4ClaimManipulation:
    """
    AC-S4: Client cannot manipulate claim_type or downgrade_reasons via request body.
    Pydantic schema with extra="forbid" rejects unknown fields (e.g., deliverable_id, prerequisites_met).
    §3.11 evaluation is done server-side only, based on real DB state.
    """

    def test_attestation_extra_fields_rejected_422(
        self, client, session, user_inst_coord_authz, inst_coord_authz,
        engagement_evaluated_authz
    ):
        """
        AC-S4: Diana submits attestation with extra fields (fake deliverable_id, prerequisites_met).
        Pydantic extra="forbid" rejects → 422 Unprocessable Entity.

        Acceptance Criteria:
        - Status code: 422 Unprocessable Entity (or 201 if extra="ignore", depending on implementation)
        - If 422: error indicates extra field not allowed
        - If 201: extra fields silently ignored, downgrade_reasons computed from DB only
        - No "prerequisites_met" field in final Attestation
        """
        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,
            "deliverable_id": str(uuid4()),  # Extra field — not part of schema
            "prerequisites_met": True,        # Extra field — attacker tries to bypass checks
        }

        response = client.post(
            f"/engagements/{engagement_evaluated_authz.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_authz.id)},
        )

        # Either 422 (extra fields forbidden) or 201 (extra fields ignored)
        assert response.status_code in [422, 201], \
            f"Expected 422 or 201, got {response.status_code}: {response.text}"

        if response.status_code == 422:
            data = response.json()
            # Error should indicate extra field validation
            error_obj = data.get("detail") if "detail" in data else data
            assert isinstance(error_obj, (dict, list)), \
                f"422 response must have a structured validation error body, got: {data}"


# ============================================================================
# AC-S5: Race Condition — Çifte Verified Prevention
# ============================================================================


class TestAttestationS5RaceCondition:
    """
    AC-S5: Two concurrent POST requests on same EVALUATED engagement with same version.
    DB-level `UPDATE ... WHERE version = X` ensures only one succeeds (201, version increments).
    Other fails with 409 CONFLICT (VERSION_MISMATCH).
    Prevents double VERIFIED state, double SkillSignal creation.
    """

    def test_attestation_race_condition_concurrent_posts(
        self, client, session, user_inst_coord_authz, inst_coord_authz,
        engagement_evaluated_authz, deliverable_authz
    ):
        """
        AC-S5: Version-based optimistic locking prevents double VERIFIED transition.

        Not: Gerçek thread concurrency, conftest.py'nin tek paylaşılan SQLAlchemy
        Session'ı (thread-safe değil) nedeniyle bu fixture mimarisiyle güvenilir
        test edilemiyor. Bunun yerine sıralı senaryo ile aynı invariant'ı doğruluyoruz:
        version=1 ile ilk istek başarılı olup version'ı 2'ye çıkarır; version=1 ile
        yapılan İKİNCİ istek (artık eskimiş) reddedilmeli — iki VERIFIED geçişi/iki
        VerifiedExperience asla oluşmamalı.

        Acceptance Criteria:
        - First POST with version=1: 201 Created, engagement transitions to VERIFIED, version→2
        - Second POST with version=1 (stale): 409 CONFLICT (VERSION_MISMATCH or INVALID_STATE_TRANSITION)
        - DB has exactly one Attestation for this engagement (append-only)
        - DB has exactly one VerifiedExperience snapshot (no double writes)
        - engagement.version = 2 (incremented exactly once)
        """
        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,  # Current version
        }

        # First POST — should succeed
        response1 = client.post(
            f"/engagements/{engagement_evaluated_authz.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_authz.id)},
        )
        assert response1.status_code == 201, f"First request should succeed: {response1.text}"

        # Second POST with SAME (now stale) version — should fail
        response2 = client.post(
            f"/engagements/{engagement_evaluated_authz.id}/attestations",
            json=payload,  # version still 1, but engagement is now version=2/status=VERIFIED
            headers={"X-Debug-User-Id": str(user_inst_coord_authz.id)},
        )
        assert response2.status_code == 409, \
            f"Second (stale-version) request must be rejected with 409: {response2.text}"

        # DB verification: exactly 1 Attestation and 1 VerifiedExperience
        if Attestation and VerifiedExperience:
            att_count = session.query(Attestation).filter_by(
                engagement_id=engagement_evaluated_authz.id
            ).count()
            ve_count = session.query(VerifiedExperience).filter_by(
                engagement_id=engagement_evaluated_authz.id
            ).count()
            assert att_count == 1, f"Expected exactly 1 Attestation, got {att_count}"
            assert ve_count == 1, f"Expected exactly 1 VerifiedExperience, got {ve_count}"

        # Engagement state
        session.refresh(engagement_evaluated_authz)
        assert engagement_evaluated_authz.status == "VERIFIED", \
            f"Expected VERIFIED status, got {engagement_evaluated_authz.status}"
        assert engagement_evaluated_authz.version == 2, \
            f"Expected version 2 after one successful write, got {engagement_evaluated_authz.version}"


# ============================================================================
# Authorization Matrix — Denied Operations
# ============================================================================


class TestAttestationAuthorizationMatrixDenied:
    """
    Additional authorization matrix tests for completeness.
    """

    def test_attestation_talent_always_forbidden_403(
        self, client, session, user_talent_authz, talent_authz,
        engagement_evaluated_authz
    ):
        """
        TALENT role cannot submit attestation in any scenario.
        Expected: 403 FORBIDDEN (not 404, because TALENT is engagement participant).
        """
        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_evaluated_authz.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_authz.id)},
        )

        assert response.status_code == 403, f"Expected 403 FORBIDDEN, got {response.status_code}"

    def test_attestation_unauthenticated_no_header_401(
        self, client, engagement_evaluated_authz
    ):
        """
        No X-Debug-User-Id header (or invalid) → 401 Unauthorized.
        """
        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_evaluated_authz.id}/attestations",
            json=payload,
            # No X-Debug-User-Id header
        )

        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


# ============================================================================
# Role Suitability Tests (Red-team fix: STATE_MACHINE.md T8 role enforcement)
# ============================================================================


class TestAttestationOrgMemberNonAdminForbidden:
    """
    Red-team finding: ORG_MEMBER (role=MEMBER, not ADMIN) cannot attest engagement.
    STATE_MACHINE.md T8: institution_id NULL requires ORG:SUPERVISOR (ORG_ADMIN).

    ORG_MEMBER is a regular member, not a supervisor — scoped_engagements() allows
    them to see the engagement (tenant isolation), but create_attestation() must check
    role suitability and return 404 (not 403, per CLAUDE.md).
    """

    def test_attestation_org_member_non_admin_forbidden_404(
        self, client, session, user_org_member_non_admin_authz, org_member_non_admin_authz,
        engagement_org_no_institution_authz, deliverable_org_no_institution_authz
    ):
        """
        AC-NEW: Dave (ORG_MEMBER, role=MEMBER) attempts to attest engagement
        with institution_id=NULL (organization supervision role).

        Expected: 404 NOT_FOUND (role not authorized for this action).

        Acceptance Criteria:
        - Status code: 404 Not Found (not 403, not 201)
        - Error code: NOT_FOUND
        - No Attestation/VerifiedExperience written
        - engagement stays EVALUATED, version unchanged
        """
        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_org_no_institution_authz.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_non_admin_authz.id)},
        )

        assert response.status_code == 404, \
            f"Expected 404 NOT_FOUND, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") == "NOT_FOUND", \
            f"Expected NOT_FOUND, got {error_obj.get('code')}"

        # Verify engagement unchanged
        session.refresh(engagement_org_no_institution_authz)
        assert engagement_org_no_institution_authz.status == "EVALUATED", \
            "Engagement should remain EVALUATED"
        assert engagement_org_no_institution_authz.version == 1, \
            "Engagement version should not change"


class TestAttestationInstAdminNonCoordinatorForbidden:
    """
    Red-team finding: INST_ADMIN (role=ADMIN, not COORDINATOR) cannot attest engagement.
    STATE_MACHINE.md T8: institution_id NOT NULL requires COORDINATOR only.

    INST_ADMIN is an administrator, not a coordinator of evaluations — scoped_engagements()
    allows them to see the engagement (tenant isolation), but create_attestation() must
    check role suitability and return 404 (not 403, per CLAUDE.md).
    """

    def test_attestation_inst_admin_non_coordinator_forbidden_404(
        self, client, session, user_inst_admin_non_coordinator_authz, inst_admin_non_coordinator_authz,
        engagement_evaluated_authz, deliverable_authz
    ):
        """
        AC-NEW: Eve (INST_ADMIN, role=ADMIN) attempts to attest engagement
        with institution_id NOT NULL (coordinator evaluation role).

        Expected: 404 NOT_FOUND (role not authorized for this action).

        Acceptance Criteria:
        - Status code: 404 Not Found (not 403, not 201)
        - Error code: NOT_FOUND
        - No Attestation/VerifiedExperience written
        - engagement stays EVALUATED, version unchanged
        """
        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_evaluated_authz.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_admin_non_coordinator_authz.id)},
        )

        assert response.status_code == 404, \
            f"Expected 404 NOT_FOUND, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") == "NOT_FOUND", \
            f"Expected NOT_FOUND, got {error_obj.get('code')}"

        # Verify engagement unchanged
        session.refresh(engagement_evaluated_authz)
        assert engagement_evaluated_authz.status == "EVALUATED", \
            "Engagement should remain EVALUATED"
        assert engagement_evaluated_authz.version == 1, \
            "Engagement version should not change"
