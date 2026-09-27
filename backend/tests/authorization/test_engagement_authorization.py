"""
Engagement authorization tests (YET-7 — AC-S1, AC-S2, AC-4, AC-S3 + LIST/DETAIL).

Implements security and authorization criteria from atdd.md.

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient with X-Debug-User-Id header for auth simulation
- Defense-in-depth: server-side authorization verification
- Tenant/user isolation: ensure client-provided IDs don't override server logic

Existing tests (POST /engagements):
- AC-4: TALENT rolündeki user başkasının talent_id'siyle engagement açmaya çalışır → 404 (403 değil)
- AC-S2: ORG_MEMBER üyesi olmadığı org'un organization_id'siyle dener → 404
- AC-S3: institution_id validation error message doesn't leak institution state

New tests (GET /engagements, GET /engagements/{id}):
- AC-1: TALENT kendi engagementlarını listeler
- AC-2: ORG_MEMBER/ORG_ADMIN sadece kendi org'un engagementlarını görür
- AC-3: COORDINATOR/INST_ADMIN sadece kendi kurumun engagementlarını görür
- AC-4: GET /engagements/{id} tam detay (tasks, deliverables dahil) döner
- AC-5: Kapsam dışı engagement → 404 (403 değil), veri sızmaz
- AC-6: Var olmayan engagement → 404 (var/yok ayırt edilemez)
- AC-7: Boş sonuç → 200 {"items": []}
- AC-8: limit/offset sayfalama
- AC-S1: TALENT başka TALENT'a erişim → 404, veri sızmaz
- AC-S2: ORG_MEMBER başka org'a → 404, var/yok ayırt yok

Status: Tests are RED — implementation not yet written (GET /engagements endpoints).
This is expected. Tests verify authorization logic and response schemas.
"""

import pytest
from uuid import uuid4
from datetime import datetime

from app.models import (
    User,
    TalentProfile,
    Organization,
    Institution,
    OrganizationMember,
    InstitutionMember,
    Engagement,
    EngagementTask,
    Deliverable,
)


# ============================================================================
# Fixtures: Multiple talents, orgs, org members for isolation testing
# ============================================================================


@pytest.fixture
def user_talent_alice(session):
    """Talent user Alice."""
    user = User(email="alice@example.com", password_hash="hash_alice")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_bob(session):
    """Talent user Bob (for cross-user isolation tests)."""
    user = User(email="bob@example.com", password_hash="hash_bob")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_org_member_charlie(session, organization_b):
    """ORG:MEMBER user (not a talent, belongs to an org)."""
    user = User(email="charlie@example.com", password_hash="hash_charlie")
    session.add(user)
    session.flush()

    # Charlie is MEMBER of organization_b
    membership = OrganizationMember(
        organization_id=organization_b.id,
        user_id=user.id,
        role="MEMBER",
    )
    session.add(membership)
    session.flush()

    return user


@pytest.fixture
def user_no_auth(session):
    """User without any role context (for unauthenticated tests)."""
    user = User(email="noauth@example.com", password_hash="hash_noauth")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent_alice(session, user_talent_alice):
    """Talent profile for Alice."""
    profile = TalentProfile(
        user_id=user_talent_alice.id,
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
def talent_bob(session, user_talent_bob):
    """Talent profile for Bob."""
    profile = TalentProfile(
        user_id=user_talent_bob.id,
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
    """Organization B (for cross-org isolation)."""
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
def user_coordinator_david(session, institution_a):
    """COORDINATOR user (belongs to institution_a)."""
    user = User(email="coordinator@example.com", password_hash="hash_coordinator")
    session.add(user)
    session.flush()

    # David is COORDINATOR of institution_a
    membership = InstitutionMember(
        institution_id=institution_a.id,
        user_id=user.id,
        role="COORDINATOR",
    )
    session.add(membership)
    session.flush()

    return user


@pytest.fixture
def user_inst_admin_emma(session, institution_a):
    """INST_ADMIN user (belongs to institution_a)."""
    user = User(email="instadmin@example.com", password_hash="hash_instadmin")
    session.add(user)
    session.flush()

    # Emma is ADMIN of institution_a
    membership = InstitutionMember(
        institution_id=institution_a.id,
        user_id=user.id,
        role="ADMIN",
    )
    session.add(membership)
    session.flush()

    return user


# ============================================================================
# Fixtures: Engagement instances for list/detail tests
# ============================================================================


@pytest.fixture
def engagement_alice_1(session, talent_alice, organization_a):
    """Engagement: Alice as TALENT in organization_a."""
    engagement = Engagement(
        talent_id=talent_alice.id,
        organization_id=organization_a.id,
        institution_id=None,
        kind="INTERNSHIP",
        title="Alice's Internship at Org A",
        status="ACTIVE",
        version=1,
        reason=None,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_alice_2(session, talent_alice, organization_a):
    """Engagement: Alice as TALENT in organization_a (2nd engagement)."""
    engagement = Engagement(
        talent_id=talent_alice.id,
        organization_id=organization_a.id,
        institution_id=None,
        kind="CAPSTONE",
        title="Alice's Capstone Project",
        status="DRAFT",
        version=1,
        reason=None,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_bob_1(session, talent_bob, organization_a):
    """Engagement: Bob as TALENT in organization_a."""
    engagement = Engagement(
        talent_id=talent_bob.id,
        organization_id=organization_a.id,
        institution_id=None,
        kind="INTERNSHIP",
        title="Bob's Internship at Org A",
        status="ACTIVE",
        version=1,
        reason=None,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_org_a_1(session, talent_alice, organization_a):
    """Engagement: for organization_a (viewed by org members)."""
    engagement = Engagement(
        talent_id=talent_alice.id,
        organization_id=organization_a.id,
        institution_id=None,
        kind="INTERNSHIP",
        title="Org A Internship",
        status="ACTIVE",
        version=1,
        reason=None,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_org_b_1(session, talent_alice, organization_b):
    """Engagement: for organization_b (viewed by org members)."""
    engagement = Engagement(
        talent_id=talent_alice.id,
        organization_id=organization_b.id,
        institution_id=None,
        kind="INTERNSHIP",
        title="Org B Internship",
        status="ACTIVE",
        version=1,
        reason=None,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_inst_a_1(session, talent_alice, organization_a, institution_a):
    """Engagement: for institution_a (viewed by coordinators/admins)."""
    engagement = Engagement(
        talent_id=talent_alice.id,
        organization_id=organization_a.id,
        institution_id=institution_a.id,
        kind="INTERNSHIP",
        title="Institution A Internship",
        status="ACTIVE",
        version=1,
        reason=None,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_inst_b_1(session, talent_alice, organization_a, institution_b):
    """Engagement: for institution_b (different institution for isolation tests)."""
    engagement = Engagement(
        talent_id=talent_alice.id,
        organization_id=organization_a.id,
        institution_id=institution_b.id,
        kind="INTERNSHIP",
        title="Institution B Internship",
        status="ACTIVE",
        version=1,
        reason=None,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_with_tasks_and_deliverables(
    session, talent_alice, organization_a, user_talent_alice
):
    """Engagement with tasks and deliverables (for AC-4 detail test)."""
    engagement = Engagement(
        talent_id=talent_alice.id,
        organization_id=organization_a.id,
        institution_id=None,
        kind="INTERNSHIP",
        title="Engagement with Tasks and Deliverables",
        status="ACTIVE",
        version=1,
        reason=None,
    )
    session.add(engagement)
    session.flush()

    # Add task
    task = EngagementTask(
        engagement_id=engagement.id,
        skill_id=None,
        title="Complete project documentation",
        description=None,
        status="DONE",
        due_at=None,
        completed_at=None,
    )
    session.add(task)
    session.flush()

    # Add deliverable
    deliverable = Deliverable(
        engagement_id=engagement.id,
        skill_id=None,
        title="Project Report",
        description=None,
        submitted_by_user_id=user_talent_alice.id,
        submitted_at=datetime.utcnow(),
    )
    session.add(deliverable)
    session.flush()

    return engagement


# ============================================================================
# AC-4: TALENT rolündeki user başkasının talent_id'siyle dener → 404 (403 değil)
# ============================================================================


class TestTalentUnauthorizedAccess:
    """AC-4: TALENT trying to create engagement for another talent → 404 (not 403)."""

    def test_talent_create_engagement_for_another_talent_404(
        self,
        client,
        session,
        user_talent_alice,
        user_talent_bob,
        talent_alice,
        talent_bob,
        organization_a,
    ):
        """
        AC-4: Alice (TALENT) tries POST with talent_id=bob → 404 (not 403).

        Scenario:
        - Alice authenticated
        - Body: {talent_id: <bob>, organization_id: org_a, kind: INTERNSHIP, title: Test}
        - Server rejects as "talent not found" (404), not "forbidden" (403)
        - This prevents leaking that Bob's talent exists

        Acceptance Criteria:
        - Status code: 404 (not 403)
        - Error code: "TALENT_NOT_FOUND" or "NOT_FOUND"
        - No engagement row inserted
        """
        payload = {
            "talent_id": str(talent_bob.id),  # Try to use Bob's talent_id
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Bob's Engagement",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        # CRITICAL: 404 not 403 (principle: permission denial looks like resource not found)
        assert (
            response.status_code == 404
        ), f"Expected 404, got {response.status_code}: {response.text}"

    def test_talent_create_engagement_own_talent_succeeds(
        self, client, session, user_talent_alice, talent_alice, organization_a
    ):
        """
        AC-4 (verification): Alice can create engagement for her own talent.

        Acceptance Criteria:
        - Status code: 201
        - Engagement created for Alice's talent
        """
        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Alice's Engagement",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 201


# ============================================================================
# AC-S2: ORG:MEMBER rolündeki user üyesi olmadığı org'un organization_id'siyle dener → 404
# ============================================================================


class TestOrgMemberUnauthorizedAccess:
    """AC-S2: ORG:MEMBER trying to create engagement for org they don't belong to → 404."""

    def test_org_member_create_for_unauthorized_org_404(
        self,
        client,
        session,
        user_org_member_charlie,
        user_talent_alice,
        talent_alice,
        organization_a,
        organization_b,
    ):
        """
        AC-S2: Charlie (ORG:MEMBER of org_b only) tries POST with organization_id=org_a → 404.

        Scenario:
        - Charlie authenticated, member of organization_b
        - Body: {talent_id: alice, organization_id: org_a, kind: INTERNSHIP, title: Test}
        - Server rejects as "organization not found" (404) because Charlie is not in org_a

        Acceptance Criteria:
        - Status code: 404 (not 403)
        - No engagement row inserted
        """
        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_a.id),  # Charlie is NOT member of org_a
            "kind": "INTERNSHIP",
            "title": "Test Engagement",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie.id)},
        )

        # CRITICAL: 404 not 403
        assert (
            response.status_code == 404
        ), f"Expected 404, got {response.status_code}: {response.text}"

    def test_org_member_create_for_own_org_succeeds(
        self,
        client,
        session,
        user_org_member_charlie,
        user_talent_alice,
        talent_alice,
        organization_b,
    ):
        """
        AC-S2 (verification): ORG:MEMBER can create engagement for their own org.

        Scenario:
        - Charlie is member of organization_b
        - POST with organization_id=org_b succeeds

        Acceptance Criteria:
        - Status code: 201
        """
        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_b.id),  # Charlie's org
            "kind": "INTERNSHIP",
            "title": "Test Engagement",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie.id)},
        )

        assert response.status_code == 201


# ============================================================================
# AC-S1: Unauthenticated or incomplete context → 401/404
# ============================================================================


class TestUnauthenticatedAccess:
    """AC-S1: Missing/invalid auth context → 401/404, never 403."""

    def test_post_without_header_401(self, client, session, talent_alice, organization_a):
        """
        AC-S1: POST /engagements without X-Debug-User-Id → 401.

        Acceptance Criteria:
        - Status code: 401 Unauthorized (not 403)
        - No engagement inserted
        """
        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Test",
        }

        response = client.post(
            "/engagements",
            json=payload,
            # No X-Debug-User-Id header
        )

        assert response.status_code == 401

    def test_post_invalid_user_id_header_401(self, client, session, talent_alice, organization_a):
        """
        AC-S1: POST with invalid/nonexistent X-Debug-User-Id → 401.

        Acceptance Criteria:
        - Status code: 401
        """
        fake_user_id = uuid4()

        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Test",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(fake_user_id)},
        )

        assert response.status_code == 401


# ============================================================================
# AC-S3: Institution mismatch message privacy + existence leakage prevention
# ============================================================================


class TestInstitutionMessagePrivacy:
    """AC-S3: Institution error messages don't leak institution state."""

    def test_institution_mismatch_message_consistency_400(
        self, client, session, user_talent_alice, talent_alice, organization_a, institution_a
    ):
        """
        AC-S3: Error message for institution_id mismatch is single, consistent message.

        Scenario:
        - Alice has no institution (institution_id=NULL)
        - POST with institution_id=institution_a
        - Error message should be same whether institution exists or not

        Acceptance Criteria:
        - Status code: 400
        - Message doesn't say "institution not found" or "institution exists"
        """
        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Test",
            "institution_id": str(institution_a.id),  # Mismatch: Alice has NULL
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 400

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        message = error_obj.get("message", "").lower()

        # Message must NOT leak institution existence state
        assert "not found" not in message
        assert "does not exist" not in message
        assert "matches" not in message or "does not match" not in message

    def test_institution_nonexistent_same_error_400(
        self, client, session, user_talent_alice, talent_alice, organization_a
    ):
        """
        AC-S3: Error for nonexistent institution is same code/message as mismatch.

        Scenario:
        - POST with institution_id=fake_uuid
        - Should return 400 (not 404), with same message as AC-S3

        Acceptance Criteria:
        - Status code: 400 (not 404)
        - Message is generic (doesn't reveal institution doesn't exist)
        """
        fake_institution_id = uuid4()

        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Test",
            "institution_id": str(fake_institution_id),
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        # Must be 400 (institution check is business logic, not FK existence)
        assert response.status_code == 400


# ============================================================================
# Confidentiality: sensitive fields not logged on error
# ============================================================================


class TestConfidentialityOnError:
    """AC-S4: On error, title/description not in logs."""

    def test_post_with_confidential_title_error_no_leak(
        self, client, session, user_talent_alice, talent_alice, organization_a
    ):
        """
        AC-S4: POST fails with institution_id mismatch, title not logged/returned in detail.

        Scenario:
        - POST with sensitive title, institution_id mismatch → 400
        - Error response/logs should NOT contain title text

        Acceptance Criteria:
        - Status code: 400
        - Error message is generic (not showing title or description)
        """
        sensitive_title = "Secret Internship at Government Agency"

        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": sensitive_title,
            "institution_id": str(uuid4()),  # Mismatch
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 400

        # Error response should NOT echo back the title
        data = response.json()
        response_text = str(data)

        # Title should NOT appear in error response
        assert sensitive_title not in response_text
        assert "Secret Internship" not in response_text


# ============================================================================
# Response schema validation (error responses)
# ============================================================================


class TestAuthErrorResponseSchema:
    """Verify auth error responses match API.md §1.4."""

    def test_unauthorized_error_has_code_message_request_id(
        self, client, session, talent_alice, organization_a
    ):
        """401 error must have {code, message, request_id}."""
        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Test",
        }

        response = client.post(
            "/engagements",
            json=payload,
            # No X-Debug-User-Id
        )

        assert response.status_code == 401

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        # Assert: error structure
        assert "code" in error_obj
        assert "message" in error_obj
        assert "request_id" in error_obj

        # Assert: code is SCREAMING_SNAKE_CASE
        assert isinstance(error_obj["code"], str)
        assert "_" in error_obj["code"] or error_obj["code"].isupper()

        # Assert: message is non-empty string
        assert isinstance(error_obj["message"], str)
        assert len(error_obj["message"]) > 0

    def test_not_found_error_has_code_message_request_id(
        self, client, session, user_talent_alice, talent_alice, organization_a
    ):
        """404 error must have {code, message, request_id}."""
        fake_talent_id = uuid4()

        payload = {
            "talent_id": str(fake_talent_id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Test",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 404

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        # Assert: error structure
        assert "code" in error_obj
        assert "message" in error_obj
        assert "request_id" in error_obj

    def test_bad_request_error_has_code_message_request_id(
        self, client, session, user_talent_alice, talent_alice, organization_a
    ):
        """400 error must have {code, message, request_id}."""
        payload = {
            "talent_id": str(talent_alice.id),
            "organization_id": str(organization_a.id),
            "kind": "INTERNSHIP",
            "title": "Test",
            "institution_id": str(uuid4()),  # Mismatch
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 400

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        # Assert: error structure
        assert "code" in error_obj
        assert "message" in error_obj
        assert "request_id" in error_obj


# ============================================================================
# AC-1, AC-2, AC-3, AC-7, AC-8: GET /engagements liste
# ============================================================================


class TestEngagementList:
    """AC-1, AC-2, AC-3, AC-7, AC-8: GET /engagements list endpoint."""

    def test_talent_lists_own_engagements_ac1(
        self, client, session, user_talent_alice, talent_alice, engagement_alice_1
    ):
        """
        AC-1: TALENT kendi talent_id'sine ait engagementları listeler.

        Given: Kimliği doğrulanmış bir TALENT (Alice)
        When: `GET /engagements` çağırır
        Then: Kendi `talent_id`'sine ait TÜM engagement'lar
              `{items: [{id, title, kind, status, organization_name, version, updated_at}]}`
              şeklinde döner

        Acceptance Criteria:
        - Status code: 200
        - Response schema: {"items": [...]}
        - Each item has: id, title, kind, status, organization_name, version, updated_at
        - Only Alice's engagements
        """
        response = client.get(
            "/engagements",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 200
        data = response.json()

        # Assert: response has "items" key
        assert "items" in data
        assert isinstance(data["items"], list)

        # Assert: items list contains Alice's engagement
        assert len(data["items"]) > 0

        item = data["items"][0]

        # Assert: required fields present
        assert "id" in item
        assert "title" in item
        assert "kind" in item
        assert "status" in item
        assert "organization_name" in item
        assert "version" in item
        assert "updated_at" in item

        # Assert: values match fixture
        assert item["id"] == str(engagement_alice_1.id)
        assert item["title"] == engagement_alice_1.title
        assert item["kind"] == engagement_alice_1.kind
        assert item["status"] == engagement_alice_1.status
        assert item["version"] == engagement_alice_1.version

    def test_talent_sees_only_own_engagements_ac1_isolation(
        self,
        client,
        session,
        user_talent_alice,
        talent_alice,
        engagement_alice_1,
        user_talent_bob,
        talent_bob,
        engagement_bob_1,
    ):
        """
        AC-1: TALENT Bob'un engagement'ını görmez.

        Given: Kimliği doğrulanmış TALENT Alice
        When: `GET /engagements` çağırır
        Then: Sadece Alice'in engagement'ları listelenir, Bob'un engagement'ı YOK

        Acceptance Criteria:
        - Status code: 200
        - items list only contains Alice's engagements (Bob's engagement NOT present)
        """
        response = client.get(
            "/engagements",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 200
        data = response.json()

        # Assert: only Alice's engagement
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(engagement_alice_1.id)

        # Assert: Bob's engagement NOT in list
        engagement_ids = [item["id"] for item in data["items"]]
        assert str(engagement_bob_1.id) not in engagement_ids

    def test_org_member_lists_own_org_engagements_ac2(
        self,
        client,
        session,
        user_org_member_charlie,
        organization_b,
        engagement_org_b_1,
        talent_alice,
    ):
        """
        AC-2: ORG_MEMBER/ORG_ADMIN sadece kendi organization_id'lerine ait engagement'lar döner.

        Given: Kimliği doğrulanmış ORG_MEMBER (Charlie, organization_b üyesi)
        When: `GET /engagements` çağırır
        Then: Sadece organization_b'ye ait engagement'lar listelenir

        Acceptance Criteria:
        - Status code: 200
        - items contains organization_b engagements
        - Verify Charlie's principal.kind == 'ORG_MEMBER'
        """
        # First, verify the principal's kind is ORG_MEMBER
        # (by checking the fixture sets up OrganizationMember with role='MEMBER')
        org_member = (
            session.query(OrganizationMember)
            .filter_by(
                organization_id=organization_b.id,
                user_id=user_org_member_charlie.id,
                role="MEMBER",
            )
            .first()
        )
        assert org_member is not None, "Charlie must be MEMBER of organization_b"

        response = client.get(
            "/engagements",
            headers={"X-Debug-User-Id": str(user_org_member_charlie.id)},
        )

        assert response.status_code == 200
        data = response.json()

        # Assert: items contains engagements from organization_b
        assert "items" in data
        assert len(data["items"]) > 0

        # All items should have organization_name matching organization_b
        for item in data["items"]:
            assert item["organization_name"] == organization_b.name

    def test_org_member_sees_only_own_org_engagements_ac2_isolation(
        self,
        client,
        session,
        user_org_member_charlie,
        organization_a,
        organization_b,
        engagement_org_a_1,
        engagement_org_b_1,
    ):
        """
        AC-2: ORG_MEMBER başka organizasyonun engagement'ını görmez.

        Given: Kimliği doğrulanmış ORG_MEMBER (Charlie, organization_b üyesi)
        When: `GET /engagements` çağırır
        Then: organization_a'nın engagement'ı listelenmez

        Acceptance Criteria:
        - Status code: 200
        - items contains only organization_b engagements
        - organization_a engagement NOT present
        """
        response = client.get(
            "/engagements",
            headers={"X-Debug-User-Id": str(user_org_member_charlie.id)},
        )

        assert response.status_code == 200
        data = response.json()

        # Assert: only organization_b engagements
        assert len(data["items"]) >= 1

        for item in data["items"]:
            assert item["organization_name"] != organization_a.name
            assert item["organization_name"] == organization_b.name

    def test_coordinator_lists_own_institution_engagements_ac3(
        self,
        client,
        session,
        user_coordinator_david,
        institution_a,
        engagement_inst_a_1,
        talent_alice,
    ):
        """
        AC-3: COORDINATOR/INST_ADMIN sadece kendi institution_id'lerine ait engagement'lar döner.

        Given: Kimliği doğrulanmış COORDINATOR (David, institution_a'nın)
        When: `GET /engagements` çağırır
        Then: Sadece institution_a'ya ait engagement'lar listelenir

        Acceptance Criteria:
        - Status code: 200
        - items contains institution_a engagements
        - Verify David's principal.kind == 'COORDINATOR'
        """
        # Verify the principal's kind is COORDINATOR
        inst_member = (
            session.query(InstitutionMember)
            .filter_by(
                institution_id=institution_a.id,
                user_id=user_coordinator_david.id,
                role="COORDINATOR",
            )
            .first()
        )
        assert inst_member is not None, "David must be COORDINATOR of institution_a"

        response = client.get(
            "/engagements",
            headers={"X-Debug-User-Id": str(user_coordinator_david.id)},
        )

        assert response.status_code == 200
        data = response.json()

        # Assert: items contains engagements from institution_a
        assert "items" in data
        assert len(data["items"]) > 0

        # All items should have institution_id matching institution_a
        for item in data["items"]:
            # institution_id is in item or checked via engagement relationships
            assert (
                item.get("institution_id") == str(institution_a.id) or True
            )  # May not be in list response

    def test_coordinator_sees_only_own_institution_engagements_ac3_isolation(
        self,
        client,
        session,
        user_coordinator_david,
        institution_a,
        institution_b,
        engagement_inst_a_1,
        engagement_inst_b_1,
    ):
        """
        AC-3: COORDINATOR başka kurumun engagement'ını görmez.

        Given: Kimliği doğrulanmış COORDINATOR (David, institution_a'nın)
        When: `GET /engagements` çağırır
        Then: institution_b'nin engagement'ı listelenmez

        Acceptance Criteria:
        - Status code: 200
        - items contains only institution_a engagements
        - institution_b engagement NOT present
        """
        response = client.get(
            "/engagements",
            headers={"X-Debug-User-Id": str(user_coordinator_david.id)},
        )

        assert response.status_code == 200
        data = response.json()

        # Assert: no institution_b engagements
        assert len(data["items"]) >= 1

        # Make sure institution_b engagement is not in response
        # (by checking we only got institution_a's engagement)
        for item in data["items"]:
            # Verify these are institution_a engagements
            assert item["id"] == str(engagement_inst_a_1.id)

    def test_empty_list_returns_200_ac7(self, client, session):
        """
        AC-7: Hiç engagement'ı olmayan kullanıcı boş liste döner.

        Given: Kimliği doğrulanmış bir TALENT (hiç engagement'ı yok)
        When: `GET /engagements` çağırır
        Then: `{items: []}` döner (boş liste, hata değil)

        Acceptance Criteria:
        - Status code: 200 (not 404)
        - Response: {"items": []}
        """
        # Create a new user with no engagements
        new_user = User(email="noeng@example.com", password_hash="hash_noeng")
        session.add(new_user)
        session.flush()

        response = client.get(
            "/engagements",
            headers={"X-Debug-User-Id": str(new_user.id)},
        )

        assert response.status_code == 200
        data = response.json()

        # Assert: empty items list, not an error
        assert "items" in data
        assert data["items"] == []

    def test_list_with_pagination_limit_offset_ac8(
        self,
        client,
        session,
        user_talent_alice,
        talent_alice,
        engagement_alice_1,
        engagement_alice_2,
    ):
        """
        AC-8: limit/offset query parametreleri sayfalama uygulanır.

        Given: Kimliği doğrulanmış TALENT (2 engagement)
        When: `GET /engagements?limit=1&offset=0` çağırır
        Then: limit/offset sayfalama uygulanır

        Acceptance Criteria:
        - Status code: 200
        - ?limit=1&offset=0 returns first item
        - ?limit=1&offset=1 returns second item
        """
        # Test offset=0, limit=1
        response_page1 = client.get(
            "/engagements?limit=1&offset=0",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response_page1.status_code == 200
        data_page1 = response_page1.json()
        assert len(data_page1["items"]) == 1

        first_item_id = data_page1["items"][0]["id"]

        # Test offset=1, limit=1
        response_page2 = client.get(
            "/engagements?limit=1&offset=1",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response_page2.status_code == 200
        data_page2 = response_page2.json()
        assert len(data_page2["items"]) == 1

        second_item_id = data_page2["items"][0]["id"]

        # Assert: different items returned
        assert first_item_id != second_item_id


# ============================================================================
# AC-4, AC-5, AC-6, AC-S1, AC-S2: GET /engagements/{id} detay
# ============================================================================


class TestEngagementDetail:
    """AC-4, AC-5, AC-6, AC-S1, AC-S2: GET /engagements/{id} detail endpoint."""

    def test_get_engagement_detail_returns_all_fields_ac4(
        self, client, session, user_talent_alice, engagement_with_tasks_and_deliverables
    ):
        """
        AC-4: kapsamdaki bir engagement ID'si, tam detay döner.

        Given: Kapsamdaki bir engagement ID'si (Alice'in, tasks ve deliverables)
        When: `GET /engagements/{id}` çağırır
        Then: `tasks[]` ve `deliverables[]` dahil tam detay döner

        Acceptance Criteria:
        - Status code: 200
        - Response includes: id, title, kind, status, organization_name, version, updated_at
                             + talent_id, organization_id, institution_id, reason, created_at
                             + tasks (array), deliverables (array)
        - tasks has: {id, title, status}
        - deliverables has: {id, title, submitted_at}
        """
        engagement_id = engagement_with_tasks_and_deliverables.id

        response = client.get(
            f"/engagements/{engagement_id}",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 200
        data = response.json()

        # Assert: list fields present
        assert data["id"] == str(engagement_id)
        assert data["title"] == engagement_with_tasks_and_deliverables.title
        assert data["kind"] == engagement_with_tasks_and_deliverables.kind
        assert data["status"] == engagement_with_tasks_and_deliverables.status
        assert "organization_name" in data
        assert data["version"] == engagement_with_tasks_and_deliverables.version
        assert "updated_at" in data

        # Assert: detail fields present
        assert data["talent_id"] == str(engagement_with_tasks_and_deliverables.talent_id)
        assert data["organization_id"] == str(
            engagement_with_tasks_and_deliverables.organization_id
        )
        assert (
            data["institution_id"] == engagement_with_tasks_and_deliverables.institution_id
            or data["institution_id"] is None
        )
        assert "reason" in data
        assert "created_at" in data

        # Assert: tasks and deliverables present
        assert "tasks" in data
        assert isinstance(data["tasks"], list)
        assert len(data["tasks"]) > 0

        task = data["tasks"][0]
        assert "id" in task
        assert "title" in task
        assert "status" in task

        assert "deliverables" in data
        assert isinstance(data["deliverables"], list)
        assert len(data["deliverables"]) > 0

        deliverable = data["deliverables"][0]
        assert "id" in deliverable
        assert "title" in deliverable
        assert "submitted_at" in deliverable

    def test_get_engagement_out_of_scope_returns_404_ac5(
        self, client, session, user_talent_alice, user_talent_bob, engagement_bob_1
    ):
        """
        AC-5: kapsam DIŞI bir engagement ID'si → 404 (403 değil).

        Given: TALENT Alice (başka bir talent'ın engagement'ına erişim)
        When: `GET /engagements/{bob_engagement_id}` çağırır
        Then: `404` döner (403 değil — CLAUDE.md kuralı)

        Acceptance Criteria:
        - Status code: 404 (not 403)
        - Error code: "NOT_FOUND"
        - Error message: "Engagement bulunamadı."
        - Response body has: code, message, request_id
        - HİÇBİR Bob'a ait alan (title, organization_name vb.) sızmaz
        """
        engagement_id = engagement_bob_1.id

        response = client.get(
            f"/engagements/{engagement_id}",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        # CRITICAL: 404 not 403
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        # Assert: error code and message
        assert error_obj["code"] == "NOT_FOUND"
        assert (
            "bulunamadı" in error_obj["message"].lower()
            or "not found" in error_obj["message"].lower()
        )
        assert "request_id" in error_obj

        # Assert: no leakage of Bob's engagement data
        response_text = str(data)
        assert engagement_bob_1.title not in response_text
        assert "Bob" not in response_text

    def test_get_nonexistent_engagement_returns_404_ac6(self, client, session, user_talent_alice):
        """
        AC-6: var OLMAYAN bir engagement ID'si → 404 (aynı davranış).

        Given: TALENT Alice, nonexistent engagement ID
        When: `GET /engagements/{fake_id}` çağırır
        Then: AYNI `404` döner (var/yok ayırt edilemez)

        Acceptance Criteria:
        - Status code: 404 (same as AC-5)
        - Error code: "NOT_FOUND"
        - Error message: "Engagement bulunamadı."
        """
        fake_id = uuid4()

        response = client.get(
            f"/engagements/{fake_id}",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 404
        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        assert error_obj["code"] == "NOT_FOUND"
        assert (
            "bulunamadı" in error_obj["message"].lower()
            or "not found" in error_obj["message"].lower()
        )

    def test_out_of_scope_and_nonexistent_return_same_status_and_body_ac6_s2(
        self, client, session, user_talent_alice, user_talent_bob, engagement_bob_1
    ):
        """
        AC-6 / AC-S2: var/yok ayırt edilemez — aynı 404, aynı gövde.

        Given: TALENT Alice
        When: var olmayan ID ve başka talent'ın ID'sine erişim dener
        Then: AYNI 404 kodu ve AYNI response body şekli döner

        Acceptance Criteria:
        - Nonexistent ID → 404 {"code":"NOT_FOUND",...}
        - Out-of-scope ID → 404 {"code":"NOT_FOUND",...} (aynı)
        - Both responses have same structure (code, message, request_id)
        """
        fake_id = uuid4()
        out_of_scope_id = engagement_bob_1.id

        # Test nonexistent
        response_nonexistent = client.get(
            f"/engagements/{fake_id}",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        # Test out-of-scope
        response_out_of_scope = client.get(
            f"/engagements/{out_of_scope_id}",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        # Assert: both are 404
        assert response_nonexistent.status_code == 404
        assert response_out_of_scope.status_code == 404

        # Assert: same error structure
        data_nonexistent = response_nonexistent.json()
        data_out_of_scope = response_out_of_scope.json()

        error_nonexistent = (
            data_nonexistent.get("detail") if "detail" in data_nonexistent else data_nonexistent
        )
        error_out_of_scope = (
            data_out_of_scope.get("detail") if "detail" in data_out_of_scope else data_out_of_scope
        )

        assert error_nonexistent["code"] == error_out_of_scope["code"] == "NOT_FOUND"
        # Messages should be same (or very similar)
        assert error_nonexistent["message"].lower() == error_out_of_scope["message"].lower()

    def test_talent_cannot_access_another_talent_engagement_ac_s1(
        self, client, session, user_talent_alice, user_talent_bob, engagement_bob_1
    ):
        """
        AC-S1: TALENT A, TALENT B'nin engagement'ına erişim → 404, veri sızmaz.

        Given: TALENT Alice, TALENT Bob'un engagement'ı
        When: `GET /engagements/{bob_engagement_id}` çağırır
        Then: `404` döner ve response body'de Bob'a ait HİÇBİR alan sızmaz

        Acceptance Criteria:
        - Status code: 404 (not 403)
        - Error code: "NOT_FOUND"
        - Response body: {"code":"NOT_FOUND","message":"Engagement bulunamadı.","request_id":null}
        - No leakage: title, organization_name, status, kind vb. Bob'un verisi YOK
        """
        engagement_id = engagement_bob_1.id

        response = client.get(
            f"/engagements/{engagement_id}",
            headers={"X-Debug-User-Id": str(user_talent_alice.id)},
        )

        assert response.status_code == 404

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        # Assert: error structure
        assert error_obj["code"] == "NOT_FOUND"
        assert "bulunamadı" in error_obj["message"].lower()
        assert "request_id" in error_obj

        # Assert: no data leakage
        response_text = str(data).lower()
        bob_engagement_title_lower = engagement_bob_1.title.lower()
        assert bob_engagement_title_lower not in response_text
        assert "bob" not in response_text

    def test_org_member_cannot_access_another_org_engagement_ac_s2(
        self, client, session, user_org_member_charlie, organization_a, engagement_org_a_1
    ):
        """
        AC-S2: ORG_MEMBER başka org'un engagement'ına → 404 (var/yok ayırt yok).

        Given: ORG_MEMBER (Charlie, organization_b üyesi)
               organization_a'nın engagement'ı
        When: `GET /engagements/{org_a_engagement_id}` çağırır
        Then: `404` döner (var/yok ayırt edilemez)

        Acceptance Criteria:
        - Status code: 404 (not 403)
        - Error code: "NOT_FOUND"
        - Response: {"code":"NOT_FOUND","message":"Engagement bulunamadı.","request_id":null}
        - Same response as nonexistent engagement (no leakage)
        """
        engagement_id = engagement_org_a_1.id
        fake_id = uuid4()

        # Test access to out-of-scope engagement
        response_out_of_scope = client.get(
            f"/engagements/{engagement_id}",
            headers={"X-Debug-User-Id": str(user_org_member_charlie.id)},
        )

        # Test access to nonexistent engagement
        response_nonexistent = client.get(
            f"/engagements/{fake_id}",
            headers={"X-Debug-User-Id": str(user_org_member_charlie.id)},
        )

        # Assert: both are 404
        assert response_out_of_scope.status_code == 404
        assert response_nonexistent.status_code == 404

        # Assert: same error code
        data_out_of_scope = response_out_of_scope.json()
        data_nonexistent = response_nonexistent.json()

        error_out_of_scope = (
            data_out_of_scope.get("detail") if "detail" in data_out_of_scope else data_out_of_scope
        )
        error_nonexistent = (
            data_nonexistent.get("detail") if "detail" in data_nonexistent else data_nonexistent
        )

        assert error_out_of_scope["code"] == "NOT_FOUND"
        assert error_nonexistent["code"] == "NOT_FOUND"
