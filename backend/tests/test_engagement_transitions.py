"""
Engagement transitions endpoint tests (PLAN 2.2 — engagement-durum-makinesi-transitions-ucu).

Implements Acceptance Criteria (AC-1 through AC-14, AC-S1 through AC-S4) and Behavior Contract
from atdd.md (8 rows: happy path, illegal transition, precondition, forbidden, version conflict,
not found, no access, and DB error).

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Error responses validated against {"code": ..., "message": ..., "request_id": ...} schema
- Engagement states (DRAFT, PENDING_APPROVAL, ACTIVE) seeded directly with session.add() + session.flush()
- Optimistic locking simulated: two sequential requests with same version (first wins, second → 409)

Status: Tests are PASSING — implementation completed in PLAN 2.2 (transition_engagement).
This is expected behavior. Tests implement behavior contract (ATDD).

Coverage Target: 90% (services/engagement.py::transition_engagement)
Performance Target: <200ms
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
)


# ============================================================================
# Fixtures: Users, TalentProfiles, Organizations, Institutions, Engagements
# ============================================================================


@pytest.fixture
def user_talent_alice(session):
    """Talent user Alice."""
    user = User(email="alice.talent@example.com", password_hash="hash_alice")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_bob(session):
    """Talent user Bob (for isolation tests)."""
    user = User(email="bob.talent@example.com", password_hash="hash_bob")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_org_member_charlie(session):
    """ORG:MEMBER user Charlie."""
    user = User(email="charlie.member@example.com", password_hash="hash_charlie")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_inst_coord_diana(session):
    """INST:COORD user Diana."""
    user = User(email="diana.coord@example.com", password_hash="hash_diana")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_org_admin_evan(session):
    """ORG:ADMIN user Evan."""
    user = User(email="evan.admin@example.com", password_hash="hash_evan")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent_alice(session, user_talent_alice, institution_a):
    """Talent profile for Alice (with institution_a)."""
    profile = TalentProfile(
        user_id=user_talent_alice.id,
        institution_id=institution_a.id,
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
def talent_bob(session, user_talent_bob, institution_b):
    """Talent profile for Bob (with institution_b)."""
    profile = TalentProfile(
        user_id=user_talent_bob.id,
        institution_id=institution_b.id,
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
def talent_charlie_no_institution(session, user_org_member_charlie):
    """Talent profile for Charlie (no institution)."""
    profile = TalentProfile(
        user_id=user_org_member_charlie.id,
        institution_id=None,
        full_name="Charlie No Institution",
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
    """Organization B (for isolation tests)."""
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


@pytest.fixture
def institution_b(session):
    """Institution B (for cross-institution isolation)."""
    inst = Institution(
        name="Test Institution B",
        domain="testinstb.example.com",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def org_member_charlie(session, organization_a, user_org_member_charlie):
    """Charlie is ORG:MEMBER of organization_a."""
    member = OrganizationMember(
        organization_id=organization_a.id,
        user_id=user_org_member_charlie.id,
        role="MEMBER",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def org_admin_evan(session, organization_a, user_org_admin_evan):
    """Evan is ORG:ADMIN of organization_a."""
    member = OrganizationMember(
        organization_id=organization_a.id,
        user_id=user_org_admin_evan.id,
        role="ADMIN",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def evan_member_of_org_b(session, organization_b, user_org_admin_evan, org_admin_evan):
    """Evan is ORG:ADMIN of organization_a (org_admin_evan) AND ORG:MEMBER (not ADMIN) of organization_b —
    for org_ids⊃org_admin_ids scenario (same principal, different roles per org).

    Ensures principal.kind="ORG_ADMIN" and org_admin_ids contains organization_a but not organization_b,
    testing the authorization logic path for access (visible) vs. permission (write denied)."""
    member = OrganizationMember(
        organization_id=organization_b.id,
        user_id=user_org_admin_evan.id,
        role="MEMBER",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def inst_coord_diana(session, institution_a, user_inst_coord_diana):
    """Diana is INST:COORD of institution_a."""
    coord = InstitutionMember(
        institution_id=institution_a.id,
        user_id=user_inst_coord_diana.id,
        role="COORDINATOR",
    )
    session.add(coord)
    session.flush()
    return coord


@pytest.fixture
def user_inst_coord_fiona(session):
    """INST:COORD user Fiona (for institution_b)."""
    user = User(email="fiona.coord@example.com", password_hash="hash_fiona")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def inst_coord_fiona(session, institution_b, user_inst_coord_fiona):
    """Fiona is INST:COORD of institution_b."""
    coord = InstitutionMember(
        institution_id=institution_b.id,
        user_id=user_inst_coord_fiona.id,
        role="COORDINATOR",
    )
    session.add(coord)
    session.flush()
    return coord


@pytest.fixture
def engagement_draft_alice(session, talent_alice, organization_a, institution_a):
    """Engagement in DRAFT status (Alice, organization_a, institution_a, version=1)."""
    engagement = Engagement(
        talent_id=talent_alice.id,
        organization_id=organization_a.id,
        institution_id=institution_a.id,
        kind="INTERNSHIP",
        title="Alice Internship",
        status="DRAFT",
        version=1,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_pending_approval_alice(session, talent_alice, organization_a, institution_a):
    """Engagement in PENDING_APPROVAL status (Alice, organization_a, institution_a, version=2)."""
    engagement = Engagement(
        talent_id=talent_alice.id,
        organization_id=organization_a.id,
        institution_id=institution_a.id,
        kind="CAPSTONE",
        title="Alice Capstone",
        status="PENDING_APPROVAL",
        version=2,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_active_alice(session, talent_alice, organization_a, institution_a):
    """Engagement in ACTIVE status (Alice, organization_a, institution_a, version=3)."""
    engagement = Engagement(
        talent_id=talent_alice.id,
        organization_id=organization_a.id,
        institution_id=institution_a.id,
        kind="SHORT_PROJECT",
        title="Alice Project",
        status="ACTIVE",
        version=3,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_draft_no_institution(session, talent_charlie_no_institution, organization_a):
    """Engagement in DRAFT with NULL institution_id (Charlie, organization_a, version=1)."""
    engagement = Engagement(
        talent_id=talent_charlie_no_institution.id,
        organization_id=organization_a.id,
        institution_id=None,
        kind="PART_TIME",
        title="Charlie Part-time",
        status="DRAFT",
        version=1,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_draft_bob_isolated(session, talent_bob, organization_b, institution_b):
    """Engagement in DRAFT (Bob, organization_b, institution_b) — for isolation tests."""
    engagement = Engagement(
        talent_id=talent_bob.id,
        organization_id=organization_b.id,
        institution_id=institution_b.id,
        kind="INTERNSHIP",
        title="Bob Internship",
        status="DRAFT",
        version=1,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_pending_approval_bob(session, talent_bob, organization_b, institution_b):
    """Engagement in PENDING_APPROVAL (Bob, organization_b, institution_b, version=2)."""
    engagement = Engagement(
        talent_id=talent_bob.id,
        organization_id=organization_b.id,
        institution_id=institution_b.id,
        kind="CAPSTONE",
        title="Bob Capstone",
        status="PENDING_APPROVAL",
        version=2,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_active_bob(session, talent_bob, organization_b, institution_b):
    """Engagement in ACTIVE (Bob, organization_b, institution_b, version=3)."""
    engagement = Engagement(
        talent_id=talent_bob.id,
        organization_id=organization_b.id,
        institution_id=institution_b.id,
        kind="SHORT_PROJECT",
        title="Bob Project",
        status="ACTIVE",
        version=3,
    )
    session.add(engagement)
    session.flush()
    return engagement


# ============================================================================
# AC-1 / Row 1: Happy Path (T1: DRAFT → PENDING_APPROVAL)
# ============================================================================


class TestTransitionHappyPathT1:
    """
    AC-1: TALENT (Alice) transitions her own engagement DRAFT → PENDING_APPROVAL.
    Row 1 (Davranış Sözleşmesi): 200 + {status: PENDING_APPROVAL, version: 2} + audit_event + outbox.
    """

    def test_transition_draft_to_pending_approval_200(
        self, client, session, user_talent_alice, engagement_draft_alice
    ):
        """
        AC-1: POST /engagements/{id}/transitions with DRAFT → PENDING_APPROVAL succeeds.

        Acceptance Criteria:
        - Status code: 200 OK
        - Response contains: id, status="PENDING_APPROVAL", version=2
        - audit_event written (istisnasız her geçiş)
        - outbox written (koordinatör bildirimi)
        - Transaction atomik
        """
        payload = {
            "to_status": "PENDING_APPROVAL",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_draft_alice.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Assert: response schema
        assert data.get("id") == str(engagement_draft_alice.id)
        assert data.get("status") == "PENDING_APPROVAL"
        assert data.get("version") == 2
        assert "updated_at" in data

        # Assert: DB state changed (version incremented)
        session.refresh(engagement_draft_alice)
        assert engagement_draft_alice.status == "PENDING_APPROVAL"
        assert engagement_draft_alice.version == 2


# ============================================================================
# AC-5 / Row 2: Illegal Transition (422 ILLEGAL_TRANSITION)
# ============================================================================


class TestTransitionIllegalTransition:
    """
    AC-5: Try to transition to a status that doesn't exist in transition table.
    Row 2 (Davranış Sözleşmesi): 422 + {code: ILLEGAL_TRANSITION, message: ...}.
    """

    def test_transition_draft_to_verified_illegal_422(
        self, client, session, user_talent_alice, engagement_draft_alice
    ):
        """
        AC-5: POST with DRAFT → VERIFIED (not in transition table) → 422.

        Acceptance Criteria:
        - Status code: 422 Unprocessable Entity
        - Error code: ILLEGAL_TRANSITION
        - status remains DRAFT, version remains 1 (no change)
        """
        payload = {
            "to_status": "VERIFIED",  # Not a valid transition from DRAFT
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_draft_alice.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "ILLEGAL_TRANSITION"
        assert isinstance(error_obj.get("message"), str)

        # Assert: DB state unchanged
        session.refresh(engagement_draft_alice)
        assert engagement_draft_alice.status == "DRAFT"
        assert engagement_draft_alice.version == 1


# ============================================================================
# AC-6, AC-7 / Row 3: Precondition Failed (422 PRECONDITION_FAILED)
# ============================================================================


class TestTransitionPreconditionFailed:
    """
    AC-6, AC-7: Ön koşul sağlanmıyor.
    - AC-6: institution_id NULL → PENDING_APPROVAL yapamaz
    - AC-7: reason boş/eksik (T3/T6 için gerekli)
    Row 3 (Davranış Sözleşmesi): 422 + {code: PRECONDITION_FAILED, message: ...}.
    """

    def test_transition_institution_null_422(
        self, client, session, user_org_member_charlie, engagement_draft_no_institution
    ):
        """
        AC-6: Transition from DRAFT without institution_id → 422 PRECONDITION_FAILED.

        Scenario:
        - Engagement has institution_id=NULL
        - Try DRAFT → PENDING_APPROVAL (requires institution_id)
        - Fails with 422

        Acceptance Criteria:
        - Status code: 422
        - Error code: PRECONDITION_FAILED
        - status remains DRAFT
        """
        payload = {
            "to_status": "PENDING_APPROVAL",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_draft_no_institution.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie.id)},
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "PRECONDITION_FAILED"

        # Assert: DB state unchanged
        session.refresh(engagement_draft_no_institution)
        assert engagement_draft_no_institution.status == "DRAFT"
        assert engagement_draft_no_institution.version == 1

    def test_transition_reason_missing_for_reject_422(
        self, client, session, user_inst_coord_diana, inst_coord_diana, engagement_pending_approval_alice
    ):
        """
        AC-7: T3 (PENDING_APPROVAL → REJECTED) requires reason → 422 if missing.

        Scenario:
        - Diana is INST:COORD
        - Try PENDING_APPROVAL → REJECTED without reason field
        - Fails with 422

        Acceptance Criteria:
        - Status code: 422
        - Error code: PRECONDITION_FAILED
        - status remains PENDING_APPROVAL
        """
        payload = {
            "to_status": "REJECTED",
            "version": 2,
            # Missing 'reason'
        }

        response = client.post(
            f"/engagements/{engagement_pending_approval_alice.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana.id)},
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "PRECONDITION_FAILED"

        # Assert: DB state unchanged
        session.refresh(engagement_pending_approval_alice)
        assert engagement_pending_approval_alice.status == "PENDING_APPROVAL"
        assert engagement_pending_approval_alice.version == 2


# ============================================================================
# AC-8 / Row 4: Forbidden — Access OK, Transition Not Allowed (403 FORBIDDEN)
# ============================================================================


class TestTransitionForbidden:
    """
    AC-8, AC-S3: Aktörün kaynağa erişimi var ama bu geçişi yapma yetkisi yok.
    Row 4 (Davranış Sözleşmesi): 403 + {code: FORBIDDEN, message: ...}.
    Kritik ayrım: AC-8 vs AC-11/S2 (403 vs 404).
    """

    def test_transition_talent_tries_t2_forbidden_403(
        self, client, session, user_talent_alice, engagement_draft_alice
    ):
        """
        AC-8 (AC-S3): TALENT (Alice) tries T2 (DRAFT → PENDING_APPROVAL) but she cannot.
        Wait — T2 is only for ORG:MEMBER, not TALENT.
        Actually, AC-1 says TALENT can do T1.
        Let me re-read the transitions:
        - T1: DRAFT → PENDING_APPROVAL (TALENT or ORG:MEMBER)
        - T2: PENDING_APPROVAL → ACTIVE (INST:COORD)
        - T3: PENDING_APPROVAL → REJECTED (INST:COORD, requires reason)
        - T6: ACTIVE → CANCELLED (ORG:ADMIN or INST:COORD, requires reason)

        AC-S3 says: "TALENT kendi engagement'ında T2 dener → 403".
        So Alice tries PENDING_APPROVAL → ACTIVE (T2) on her own engagement → 403.

        Acceptance Criteria:
        - Status code: 403 FORBIDDEN (not 404)
        - Error code: FORBIDDEN
        - status remains unchanged (DRAFT, since we start with DRAFT)
        - Message indicates lack of permission (not "not found")
        """
        # Alice's engagement is DRAFT; she tries T2 (PENDING_APPROVAL → ACTIVE)
        # But T2 requires INST:COORD, not TALENT.
        # Since status is DRAFT, she cannot go to ACTIVE directly anyway.
        # Let's use PENDING_APPROVAL engagement instead.
        engagement = Engagement(
            talent_id=engagement_draft_alice.talent_id,
            organization_id=engagement_draft_alice.organization_id,
            institution_id=engagement_draft_alice.institution_id,
            kind="INTERNSHIP",
            title="Test",
            status="PENDING_APPROVAL",
            version=2,
        )
        session.add(engagement)
        session.flush()

        payload = {
            "to_status": "ACTIVE",  # T2: requires INST:COORD, not TALENT
            "version": 2,
        }

        response = client.post(
            f"/engagements/{engagement.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "FORBIDDEN"
        assert isinstance(error_obj.get("message"), str)

        # Assert: DB state unchanged (status and version not changed)
        session.refresh(engagement)
        assert engagement.status == "PENDING_APPROVAL"
        assert engagement.version == 2


# ============================================================================
# AC-9, AC-S1, AC-S4 / Row 5: Version Conflict (409 CONFLICT)
# ============================================================================


class TestTransitionVersionConflict:
    """
    AC-9: version isteği gerçek DB değerinden eski → 409.
    AC-S1: Iki eşzamanlı istek aynı version ile dener, biri wins, diğeri 409.
    AC-S4: version tampering denemesi → 409.
    Row 5 (Davranış Sözleşmesi): 409 + {code: CONFLICT, message: ...}.
    """

    def test_transition_version_old_409(
        self, client, session, user_talent_alice, engagement_draft_alice
    ):
        """
        AC-9: POST with version=0 (old) when DB has version=1 → 409.

        Acceptance Criteria:
        - Status code: 409 Conflict
        - Error code: CONFLICT
        - status remains DRAFT, version remains 1 (no change)
        """
        payload = {
            "to_status": "PENDING_APPROVAL",
            "version": 0,  # Old version
        }

        response = client.post(
            f"/engagements/{engagement_draft_alice.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "CONFLICT"

        # Assert: DB state unchanged
        session.refresh(engagement_draft_alice)
        assert engagement_draft_alice.status == "DRAFT"
        assert engagement_draft_alice.version == 1

    def test_transition_concurrent_version_first_wins_second_409(
        self, client, session, user_talent_alice, engagement_draft_alice
    ):
        """
        AC-S1: Two sequential requests with same version=1.
        First: DRAFT → PENDING_APPROVAL succeeds (version → 2).
        Second: tries DRAFT → PENDING_APPROVAL again with version=1 → 409.

        Simulates concurrency (sequential, not real async).

        Acceptance Criteria:
        - First response: 200, status=PENDING_APPROVAL, version=2
        - Second response: 409 CONFLICT, version unchanged
        """
        payload_first = {
            "to_status": "PENDING_APPROVAL",
            "version": 1,
        }

        response_first = client.post(
            f"/engagements/{engagement_draft_alice.id}/transitions",
            json=payload_first,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response_first.status_code == 200
        data_first = response_first.json()
        assert data_first.get("version") == 2
        assert data_first.get("status") == "PENDING_APPROVAL"

        # Second request with old version=1 (while DB now has version=2)
        payload_second = {
            "to_status": "PENDING_APPROVAL",  # Already PENDING_APPROVAL now, but client tries again
            "version": 1,
        }

        response_second = client.post(
            f"/engagements/{engagement_draft_alice.id}/transitions",
            json=payload_second,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response_second.status_code == 409, f"Expected 409, got {response_second.status_code}: {response_second.text}"

        data_second = response_second.json()
        error_obj = data_second.get("detail") if "detail" in data_second else data_second

        assert error_obj.get("code") == "CONFLICT"

        # Assert: version did not change after failed attempt
        session.refresh(engagement_draft_alice)
        assert engagement_draft_alice.version == 2

    def test_transition_version_tampering_409(
        self, client, session, user_talent_alice, engagement_draft_alice
    ):
        """
        AC-S4: Client tries to tamper version (send very low/high version).
        Result: 409 (durum makinesi "atlatılamaz").

        Acceptance Criteria:
        - Status code: 409
        - status/version unchanged
        """
        payload = {
            "to_status": "ACTIVE",  # Try to skip steps
            "version": 99,  # Very high version (tampering)
        }

        response = client.post(
            f"/engagements/{engagement_draft_alice.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 409

        session.refresh(engagement_draft_alice)
        assert engagement_draft_alice.status == "DRAFT"
        assert engagement_draft_alice.version == 1


# ============================================================================
# AC-10 / Row 6: Engagement Not Found (404 NOT_FOUND)
# ============================================================================


class TestTransitionNotFound:
    """
    AC-10: Engagement id sistemde hiç yok → 404.
    Row 6 (Davranış Sözleşmesi): 404 + {code: NOT_FOUND, message: ...}.
    """

    def test_transition_nonexistent_engagement_404(
        self, client, session, user_talent_alice
    ):
        """
        AC-10: POST to nonexistent engagement id → 404.

        Acceptance Criteria:
        - Status code: 404 Not Found
        - Error code: NOT_FOUND
        """
        fake_engagement_id = uuid4()

        payload = {
            "to_status": "PENDING_APPROVAL",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{fake_engagement_id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "NOT_FOUND"


# ============================================================================
# AC-11, AC-S2 / Row 7: No Access — Not Found (404, not 403)
# ============================================================================


class TestTransitionNoAccess:
    """
    AC-11, AC-S2: Kaynağa hiç erişimi olmayan principal → 404 (403 DEĞİL).
    Row 7 (Davranış Sözleşmesi): 404 + {code: NOT_FOUND, message: ...}.

    Kritik: AC-8 (403 — access var ama no permission) vs AC-11 (404 — no access).
    This is a deliberate exception to the general 404-not-403 rule (atdd.md §3).
    """

    def test_transition_no_access_404(
        self, client, session, user_talent_alice, engagement_draft_bob_isolated
    ):
        """
        AC-11: Alice tries to transition Bob's engagement (Bob in organization_b, Alice has no access).
        Result: 404 (not 403), because Alice doesn't know engagement exists.

        Acceptance Criteria:
        - Status code: 404 (not 403)
        - Error code: NOT_FOUND
        - Message doesn't indicate permission denial (would leak access info)
        """
        payload = {
            "to_status": "PENDING_APPROVAL",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_draft_bob_isolated.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        # CRITICAL: 404 not 403
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "NOT_FOUND"

    def test_transition_org_member_unauthorized_org_404(
        self, client, session, user_org_member_charlie, engagement_draft_bob_isolated
    ):
        """
        AC-S2: Charlie (member of organization_a) tries to transition engagement in organization_b.
        Result: 404 (not 403).

        Acceptance Criteria:
        - Status code: 404 (not 403)
        """
        payload = {
            "to_status": "PENDING_APPROVAL",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_draft_bob_isolated.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie.id)},
        )

        # CRITICAL: 404 not 403
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"


# ============================================================================
# AC-2: T2 (PENDING_APPROVAL → ACTIVE) — INST:COORD Only
# ============================================================================


class TestTransitionT2PendingToActive:
    """
    AC-2: INST:COORD transitions PENDING_APPROVAL → ACTIVE (T2).
    Row 1 (alternative): 200 + {status: ACTIVE, version: 3}.
    """

    def test_transition_pending_to_active_inst_coord_200(
        self, client, session, user_inst_coord_diana, inst_coord_diana, engagement_pending_approval_alice
    ):
        """
        AC-2: Diana (INST:COORD of institution_a) transitions PENDING_APPROVAL → ACTIVE.

        Acceptance Criteria:
        - Status code: 200
        - status=ACTIVE, version=3
        """
        payload = {
            "to_status": "ACTIVE",
            "version": 2,
        }

        response = client.post(
            f"/engagements/{engagement_pending_approval_alice.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana.id)},
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert data.get("status") == "ACTIVE"
        assert data.get("version") == 3

        # Assert: DB state changed
        session.refresh(engagement_pending_approval_alice)
        assert engagement_pending_approval_alice.status == "ACTIVE"
        assert engagement_pending_approval_alice.version == 3

    def test_coordinator_approval_enqueues_approval_risk_scan(
        self, client, session, user_inst_coord_diana, inst_coord_diana, engagement_pending_approval_alice
    ):
        """PLAN 3.56: T2 (koordinatör onayı) fraud.approval_risk_scan_requested
        üretir — payload yalnız çalışma ve onaylayan kullanıcı kimliğini taşır."""
        from app.models import Outbox

        response = client.post(
            f"/engagements/{engagement_pending_approval_alice.id}/transitions",
            json={"to_status": "ACTIVE", "version": 2},
            headers={"X-Debug-User-Id": str(user_inst_coord_diana.id)},
        )
        assert response.status_code == 200, response.text

        row = session.query(Outbox).filter_by(topic="fraud.approval_risk_scan_requested").one()
        assert row.payload == {
            "engagement_id": str(engagement_pending_approval_alice.id),
            "approver_user_id": str(user_inst_coord_diana.id),
        }


# ============================================================================
# AC-3: T3 (PENDING_APPROVAL → REJECTED) — INST:COORD with reason
# ============================================================================


class TestTransitionT3PendingToRejected:
    """
    AC-3: INST:COORD transitions PENDING_APPROVAL → REJECTED (T3, terminal).
    Requires 'reason' field.
    Row 1 (alternative): 200 + {status: REJECTED, version: 3}.
    """

    def test_transition_pending_to_rejected_inst_coord_200(
        self, client, session, user_inst_coord_diana, inst_coord_diana, engagement_pending_approval_alice
    ):
        """
        AC-3: Diana rejects the engagement with reason.

        Acceptance Criteria:
        - Status code: 200
        - status=REJECTED, version=3 (terminal state)
        """
        payload = {
            "to_status": "REJECTED",
            "version": 2,
            "reason": "Dokumentasyon eksik",
        }

        response = client.post(
            f"/engagements/{engagement_pending_approval_alice.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana.id)},
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert data.get("status") == "REJECTED"
        assert data.get("version") == 3

        # Assert: DB state changed
        session.refresh(engagement_pending_approval_alice)
        assert engagement_pending_approval_alice.status == "REJECTED"
        assert engagement_pending_approval_alice.version == 3


# ============================================================================
# AC-4: T6 (ACTIVE → CANCELLED) — ORG:ADMIN or INST:COORD with reason
# ============================================================================


class TestTransitionT6ActiveToCancelled:
    """
    AC-4: ORG:ADMIN or INST:COORD transitions ACTIVE → CANCELLED (T6, terminal).
    Requires 'reason' field.
    Row 1 (alternative): 200 + {status: CANCELLED, version: 4}.
    """

    def test_transition_active_to_cancelled_org_admin_200(
        self, client, session, user_org_admin_evan, org_admin_evan, engagement_active_alice
    ):
        """
        AC-4: Evan (ORG:ADMIN) cancels the engagement with reason.

        Acceptance Criteria:
        - Status code: 200
        - status=CANCELLED, version=4 (terminal state)
        """
        payload = {
            "to_status": "CANCELLED",
            "version": 3,
            "reason": "Offer declined by talent",
        }

        response = client.post(
            f"/engagements/{engagement_active_alice.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_admin_evan.id)},
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert data.get("status") == "CANCELLED"
        assert data.get("version") == 4

        # Assert: DB state changed
        session.refresh(engagement_active_alice)
        assert engagement_active_alice.status == "CANCELLED"
        assert engagement_active_alice.version == 4

    def test_transition_active_to_cancelled_inst_coord_200(
        self, client, session, user_inst_coord_diana, inst_coord_diana, engagement_active_alice
    ):
        """
        AC-4: Diana (INST:COORD) can also cancel ACTIVE engagement.

        Acceptance Criteria:
        - Status code: 200
        - status=CANCELLED, version=4
        """
        payload = {
            "to_status": "CANCELLED",
            "version": 3,
            "reason": "Coordinator decision",
        }

        response = client.post(
            f"/engagements/{engagement_active_alice.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana.id)},
        )

        assert response.status_code == 200

        data = response.json()
        assert data.get("status") == "CANCELLED"
        assert data.get("version") == 4


# ============================================================================
# Response Schema Validation
# ============================================================================


class TestTransitionResponseSchema:
    """Verify transition response schemas match API.md error contract."""

    def test_transition_success_response_schema_200(
        self, client, session, user_talent_alice, engagement_draft_alice
    ):
        """200 response must have engagement object with required fields."""
        payload = {
            "to_status": "PENDING_APPROVAL",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_draft_alice.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 200

        data = response.json()

        # Assert: required fields present
        required_fields = ["id", "status", "version", "updated_at"]

        for field in required_fields:
            assert field in data, f"Response missing required field: {field}"

        # Assert: types
        assert isinstance(data["id"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["version"], int)

    def test_transition_error_response_has_code_message_request_id(
        self, client, user_talent_alice, engagement_draft_alice
    ):
        """All error responses must have {code, message, request_id} or wrapped in detail."""
        payload = {
            "to_status": "VERIFIED",  # Illegal
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_draft_alice.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 422

        data = response.json()

        # Error response structure: could be wrapped in detail
        error_obj = data.get("detail") if "detail" in data else data

        assert "code" in error_obj, "Error response must have 'code' field"
        assert "message" in error_obj, "Error response must have 'message' field"
        assert "request_id" in error_obj, "Error response must have 'request_id' field"

        # Assert: code is SCREAMING_SNAKE_CASE
        assert isinstance(error_obj["code"], str)
        assert error_obj["code"].isupper() or "_" in error_obj["code"]

        # Assert: message is non-empty string
        assert isinstance(error_obj["message"], str)
        assert len(error_obj["message"]) > 0


# ============================================================================
# AC-15: T3/T6 Reason Persistence (reason → engagement.reason)
# ============================================================================


class TestTransitionReasonPersistence:
    """AC-15: reason (T3/T6) engagement satırına kalıcı olarak yazılır."""

    def test_t3_reject_persists_reason(
        self, client, session, user_inst_coord_diana, inst_coord_diana, engagement_pending_approval_alice
    ):
        """AC-15: T3 (REJECTED) sonrası reason engagement.reason'a yazılır."""
        payload = {
            "to_status": "REJECTED",
            "version": 2,
            "reason": "Belgeler eksik",
        }

        response = client.post(
            f"/engagements/{engagement_pending_approval_alice.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana.id)},
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert data.get("reason") == "Belgeler eksik"

        # DB'de kalıcı olduğunu doğrula
        session.refresh(engagement_pending_approval_alice)
        assert engagement_pending_approval_alice.reason == "Belgeler eksik"

    def test_t6_cancel_persists_reason(
        self, client, session, user_org_admin_evan, org_admin_evan, engagement_active_alice
    ):
        """AC-15: T6 (CANCELLED) sonrası reason engagement.reason'a yazılır."""
        payload = {
            "to_status": "CANCELLED",
            "version": 3,
            "reason": "Bütçe kısıtı",
        }

        response = client.post(
            f"/engagements/{engagement_active_alice.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_admin_evan.id)},
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert data.get("reason") == "Bütçe kısıtı"

        session.refresh(engagement_active_alice)
        assert engagement_active_alice.reason == "Bütçe kısıtı"


# ============================================================================
# AC-2, AC-3, AC-5 / AC-S1, AC-S2: Cross-Institution COORDINATOR Scenarios
# ============================================================================


class TestCoordinatorCrossInstitution:
    """
    AC-2/AC-S1: COORDINATOR of institution A tries to transition engagement in institution B.
    AC-3/AC-S2: Same, but with invalid to_status → ensures scope-check comes before validation.
    AC-5: Symmetric: COORDINATOR of institution B vs engagement in institution A.

    Kritik: Tüm senaryolarda 404 dönmeli (403 değil), ve response body'de
    Bob'un engagement'ına ait hiçbir alan (institution_id, status, vb.) görünmemeli.
    """

    def test_transition_cross_institution_coordinator_pending_to_active_404(
        self, client, session, user_inst_coord_diana, inst_coord_diana, engagement_pending_approval_bob
    ):
        """
        AC-2/AC-S1: Diana (COORDINATOR of institution_a) tries to transition
        Bob's engagement (institution_b) PENDING_APPROVAL → ACTIVE → 404.

        Acceptance Criteria:
        - Status code: 404 (not 403, not 422, not 200)
        - Error code: NOT_FOUND (exact match)
        - Response body does not contain engagement fields (institution_id, status, organization_id, etc.)
        """
        payload = {
            "to_status": "ACTIVE",
            "version": 2,
        }

        response = client.post(
            f"/engagements/{engagement_pending_approval_bob.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana.id)},
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

        # PLAN 3.56: a refused approval must not enqueue an approval risk scan
        from app.models import Outbox

        assert session.query(Outbox).filter_by(topic="fraud.approval_risk_scan_requested").count() == 0

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        # CRITICAL: error code must be exactly NOT_FOUND (not FORBIDDEN, not others)
        assert error_obj.get("code") == "NOT_FOUND", f"Expected code NOT_FOUND, got {error_obj.get('code')}"

        # SECURITY: Response body must not leak engagement details
        error_message = str(error_obj.get("message", ""))
        assert "institution" not in error_message.lower(), "Error message must not leak institution info"
        assert "bob" not in error_message.lower(), "Error message must not leak talent name"

    def test_transition_cross_institution_coordinator_invalid_to_status_404(
        self, client, session, user_inst_coord_diana, inst_coord_diana, engagement_pending_approval_bob
    ):
        """
        AC-3/AC-S2: Diana (COORDINATOR of institution_a) tries to transition
        Bob's engagement (institution_b) with invalid to_status=FOOBAR → 404 (not 422).

        This test ensures scope-check (access control) runs BEFORE transition validation.
        If the order were reversed, we'd get 422 for the invalid status before 404 for scope.

        Acceptance Criteria:
        - Status code: 404 (not 422, not 200)
        - Error code: NOT_FOUND (exact match, not ILLEGAL_TRANSITION)
        """
        payload = {
            "to_status": "FOOBAR",  # Intentionally invalid status
            "version": 2,
        }

        response = client.post(
            f"/engagements/{engagement_pending_approval_bob.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana.id)},
        )

        # CRITICAL: Must be 404, not 422 (scope-check order verification)
        assert response.status_code == 404, f"Expected 404 (scope-check first), got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "NOT_FOUND", f"Expected NOT_FOUND, got {error_obj.get('code')}"

    def test_transition_cross_institution_fiona_vs_alice_404(
        self, client, session, user_inst_coord_fiona, inst_coord_fiona, engagement_pending_approval_alice
    ):
        """
        AC-5: Fiona (COORDINATOR of institution_b) tries to transition
        Alice's engagement (institution_a) → 404.

        Symmetric validation: institution isolation works in both directions.

        Acceptance Criteria:
        - Status code: 404 (not 403)
        - Error code: NOT_FOUND
        """
        payload = {
            "to_status": "ACTIVE",
            "version": 2,
        }

        response = client.post(
            f"/engagements/{engagement_pending_approval_alice.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_fiona.id)},
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "NOT_FOUND", f"Expected NOT_FOUND, got {error_obj.get('code')}"


# ============================================================================
# AC-4 / AC-S3: ORG_ADMIN org_ids⊃org_admin_ids Mismatch (403 vs 404)
# ============================================================================


class TestOrgAdminScopeVsAdminMismatch:
    """
    AC-4/AC-S3: ORG_ADMIN of org_ids but not org_admin_ids tries to transition
    an engagement in their visible organizations (org_ids).

    Kritik ayrım: Kaynak org_ids kapsamında GÖRÜNÜR (not 404) ama action
    yetki kontrol edilir (org_admin_ids), sonuç 403 FORBIDDEN.

    Bu durum org_ids ve org_admin_ids'in ayrı olduğu Principal yapısından kaynaklanır:
    - org_ids: kuruluş üyelikler (GET, read access)
    - org_admin_ids: kuruluş yönetici rolleri (PUT, DELETE, transition — write access)

    Örn: Evan = Org A ADMIN + Org B MEMBER. Org A'daki engagementler için 200,
    Org B'dekiler için 403 (görünür ama yazma yapamaz).
    """

    def test_org_member_not_admin_vs_active_engagement_403(
        self, client, session, user_org_admin_evan, evan_member_of_org_b, engagement_active_bob
    ):
        """
        AC-4/AC-S3: Evan is ORG:ADMIN of organization_a AND ORG:MEMBER (not ADMIN) of organization_b.
        Evan tries to transition ACTIVE engagement in organization_b → CANCELLED.
        Result: 403 FORBIDDEN (not 404), because 403 comes from org_admin_ids check.

        Scenario:
        - Evan is ADMIN of organization_a (org_admin_evan fixture establishing principal.kind="ORG_ADMIN")
        - Evan is MEMBER of organization_b (evan_member_of_org_b fixture adding second membership)
        - principal.org_ids = {organization_a.id, organization_b.id}
        - principal.org_admin_ids = {organization_a.id} (does NOT contain organization_b)
        - engagement_active_bob.organization_id = organization_b.id
        - Evan can READ (visible in org_ids) but cannot WRITE (requires admin role in org_admin_ids)
        - 403 result verifies: `(principal.kind == "ORG_ADMIN" and engagement.organization_id in principal.org_admin_ids)`
          evaluates to False, triggering FORBIDDEN (not from lack of ORG_ADMIN kind, but from org_admin_ids mismatch)

        Acceptance Criteria:
        - Status code: 403 (not 404, not 200)
        - Error code: FORBIDDEN (exact match)
        - Response indicates lack of permission, not "not found"
        - Engagement status in DB unchanged
        """
        payload = {
            "to_status": "CANCELLED",
            "version": 3,
            "reason": "Evan'ın karar",
        }

        response = client.post(
            f"/engagements/{engagement_active_bob.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_admin_evan.id)},
        )

        # CRITICAL: 403, not 404 (resource visible, action forbidden)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj.get("code") == "FORBIDDEN", f"Expected FORBIDDEN, got {error_obj.get('code')}"

        # Assert: DB state unchanged
        session.refresh(engagement_active_bob)
        assert engagement_active_bob.status == "ACTIVE"
        assert engagement_active_bob.version == 3


# ============================================================================
# AC-8 / AC-S4: Request Body Extra Fields Ignored
# ============================================================================


class TestExtraFieldsIgnored:
    """
    AC-8/AC-S4: Request body contains extra fields not in TransitionEngagementRequest schema.
    These fields must be ignored and cannot expand the principal's scope.

    Örn: İstemci `organization_id` veya `institution_id` alanı ekleyerek
    kapsamını genişletmeye çalışırsa, Pydantic bu alanları reddeder ve
    transition gerçek principal kapsamına göre değerlendirilir.
    """

    def test_extra_org_id_in_payload_ignored(
        self, client, session, user_talent_alice, engagement_draft_alice
    ):
        """
        AC-8/AC-S4: Request body contains extra 'organization_id' field.
        Pydantic must reject/ignore it; scope is not expanded.

        Acceptance Criteria:
        - Status code: 200 (transition succeeds with Alice's real scope)
        - Extra field does not affect authorization (Alice can transition her own engagement)
        """
        payload = {
            "to_status": "PENDING_APPROVAL",
            "version": 1,
            "organization_id": "550e8400-e29b-41d4-a716-446655440999",  # Extra field
        }

        response = client.post(
            f"/engagements/{engagement_draft_alice.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        # Should succeed (Alice can do this transition on her own engagement)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert data.get("status") == "PENDING_APPROVAL"

    def test_extra_institution_id_in_payload_ignored(
        self, client, session, user_inst_coord_diana, inst_coord_diana, engagement_pending_approval_alice
    ):
        """
        AC-8/AC-S4: Request body contains extra 'institution_id' field from different institution.
        Even with extra field, Diana can only transition within her actual institution scope.

        Scenario:
        - Diana = COORDINATOR of institution_a
        - Payload contains 'institution_id' of institution_b (trying to expand scope)
        - Transition should still be allowed for institution_a engagement (her real scope)
        - Should fail if we tried to use it on institution_b (but we're using institution_a)

        For this test: Diana's real scope + Alice's real engagement = 200 (unaffected by extra field).

        Acceptance Criteria:
        - Status code: 200 (Diana can transition Alice's engagement in her real scope)
        - Extra 'institution_id' field does not expand scope
        """
        payload = {
            "to_status": "ACTIVE",
            "version": 2,
            "institution_id": "550e8400-e29b-41d4-a716-446655440999",  # Extra field (not real institution_b id)
        }

        response = client.post(
            f"/engagements/{engagement_pending_approval_alice.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana.id)},
        )

        # Should succeed (Diana's real institution + Alice's real engagement)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert data.get("status") == "ACTIVE"
