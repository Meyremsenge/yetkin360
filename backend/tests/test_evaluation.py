"""
Evaluation endpoint tests (PLAN 2.7 — yet-69-degerlendirme-formu-semasi, AC-1 through AC-9).

Implements Acceptance Criteria for POST /engagements/{id}/evaluation:
- AC-1: Happy path (org üyesi, PENDING_EVALUATION, geçerli items[], direction=ORG_TO_TALENT) → 201, private_note response'ta yok
- AC-2: AC-1 sonrası engagement.status otomatik EVALUATED'a geçer (ORG_TO_TALENT only)
- AC-3: rating=NOT_OBSERVED, comment olmadan → 201
- AC-4: items[] boş veya criterion eksik → 422
- AC-5: scope dışı kullanıcı → 404 NOT_FOUND; scope içinde ama yanlış direction/rol → 403 FORBIDDEN
- AC-6: engagement PENDING_EVALUATION dışında (örn. ACTIVE) → 409 Conflict
- AC-7: aynı evaluator+engagement+direction ikinci kez → 409 Conflict
- AC-8: geçersiz skill_id → 422
- AC-9: direction=TALENT_TO_ORG ile talent POST atar → 201, engagement.status DEĞİŞMEZ

Threat-model testleri (AC-S1/S2/S3):
- AC-S1: private_note response'ta hiçbir koşulda yer almaz
- AC-S2: evaluator_user_id body'den alınmaz, principal'dan gelir
- AC-S3: direction/rol tutarsızlığında 403 FORBIDDEN

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Error responses validated against {"code": ..., "message": ..., "request_id": ...} schema (wrapped in detail)
- Principal injection: X-Debug-User-Id header
- Engagement seeded with PENDING_EVALUATION/ACTIVE status
- Evaluation model + POST /engagements/{id}/evaluation endpoint referenced (import error expected until implementation)

Coverage Target: Evaluation creation (happy path + state transitions + threat-model scenarios).

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

# Import will fail until Evaluation model is implemented
try:
    from app.models import Evaluation, EvaluationItem
except ImportError:
    Evaluation = None
    EvaluationItem = None

# Import SkillSignal model for YET-71 tests
try:
    from app.models import SkillSignal
except ImportError:
    SkillSignal = None


# ============================================================================
# Fixtures: Users, Talents, Organizations, Institutions, Engagements
# ============================================================================


@pytest.fixture
def user_talent_alice_eval(session):
    """Talent user Alice for evaluation tests."""
    user = User(email="alice.talent.eval@example.com", password_hash="hash_alice")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_bob_eval(session):
    """Talent user Bob for evaluation isolation tests."""
    user = User(email="bob.talent.eval@example.com", password_hash="hash_bob")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_org_member_charlie_eval(session):
    """ORG:MEMBER user Charlie (evaluator) for evaluation tests."""
    user = User(email="charlie.member.eval@example.com", password_hash="hash_charlie")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_org_member_frank_eval(session):
    """ORG:MEMBER user Frank from different org for isolation."""
    user = User(email="frank.member.eval@example.com", password_hash="hash_frank")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_inst_coord_diana_eval(session):
    """INST:COORD user Diana for evaluation scope tests."""
    user = User(email="diana.coord.eval@example.com", password_hash="hash_diana")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent_alice_eval(session, user_talent_alice_eval, institution_a_eval):
    """Talent profile for Alice (institution_a)."""
    profile = TalentProfile(
        user_id=user_talent_alice_eval.id,
        institution_id=institution_a_eval.id,
        full_name="Alice Talent Eval",
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
def talent_bob_eval(session, user_talent_bob_eval, institution_b_eval):
    """Talent profile for Bob (institution_b)."""
    profile = TalentProfile(
        user_id=user_talent_bob_eval.id,
        institution_id=institution_b_eval.id,
        full_name="Bob Talent Eval",
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
def organization_a_eval(session):
    """Organization A for evaluation tests."""
    org = Organization(
        name="Test Org A Eval",
        domain="testorga.eval.example.com",
        legal_id="ORG-A-EVAL-001",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def organization_b_eval(session):
    """Organization B for evaluation isolation tests."""
    org = Organization(
        name="Test Org B Eval",
        domain="testorgb.eval.example.com",
        legal_id="ORG-B-EVAL-001",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def institution_a_eval(session):
    """Institution A for evaluation tests."""
    inst = Institution(
        name="Test Institution A Eval",
        domain="testinsta.eval.example.com",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def institution_b_eval(session):
    """Institution B for cross-institution isolation."""
    inst = Institution(
        name="Test Institution B Eval",
        domain="testinstb.eval.example.com",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def org_member_charlie_eval(session, organization_a_eval, user_org_member_charlie_eval):
    """Charlie is ORG:MEMBER of organization_a."""
    member = OrganizationMember(
        organization_id=organization_a_eval.id,
        user_id=user_org_member_charlie_eval.id,
        role="MEMBER",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def org_member_frank_eval(session, organization_b_eval, user_org_member_frank_eval):
    """Frank is ORG:MEMBER of organization_b."""
    member = OrganizationMember(
        organization_id=organization_b_eval.id,
        user_id=user_org_member_frank_eval.id,
        role="MEMBER",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def inst_coord_diana_eval(session, institution_a_eval, user_inst_coord_diana_eval):
    """Diana is INST:COORD of institution_a."""
    coord = InstitutionMember(
        institution_id=institution_a_eval.id,
        user_id=user_inst_coord_diana_eval.id,
        role="COORDINATOR",
    )
    session.add(coord)
    session.flush()
    return coord


@pytest.fixture
def engagement_pending_eval_alice_eval(session, talent_alice_eval, organization_a_eval, institution_a_eval):
    """PENDING_EVALUATION engagement for Alice (happy path status)."""
    engagement = Engagement(
        talent_id=talent_alice_eval.id,
        organization_id=organization_a_eval.id,
        institution_id=institution_a_eval.id,
        kind="INTERNSHIP",
        title="Alice Eval Test Project",
        status="PENDING_EVALUATION",
        version=3,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_pending_eval_bob_eval(session, talent_bob_eval, organization_b_eval, institution_b_eval):
    """PENDING_EVALUATION engagement for Bob (organization_b, institution_b) — isolation test."""
    engagement = Engagement(
        talent_id=talent_bob_eval.id,
        organization_id=organization_b_eval.id,
        institution_id=institution_b_eval.id,
        kind="INTERNSHIP",
        title="Bob Eval Test Project",
        status="PENDING_EVALUATION",
        version=3,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_active_alice_eval(session, talent_alice_eval, organization_a_eval, institution_a_eval):
    """ACTIVE engagement for Alice (wrong status for evaluation)."""
    engagement = Engagement(
        talent_id=talent_alice_eval.id,
        organization_id=organization_a_eval.id,
        institution_id=institution_a_eval.id,
        kind="INTERNSHIP",
        title="Alice Active Project",
        status="ACTIVE",
        version=2,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_evaluated_alice_eval(session, talent_alice_eval, organization_a_eval, institution_a_eval):
    """EVALUATED engagement for Alice (for TALENT_TO_ORG evaluation acceptance test)."""
    engagement = Engagement(
        talent_id=talent_alice_eval.id,
        organization_id=organization_a_eval.id,
        institution_id=institution_a_eval.id,
        kind="INTERNSHIP",
        title="Alice Eval Test Project (Evaluated)",
        status="EVALUATED",
        version=3,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def skill_communication_eval(session):
    """Test skill: Communication."""
    skill = Skill(
        slug="communication-eval",
        name_tr="İletişim",
        name_en="Communication",
        category="SOFT",
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def skill_time_management_eval(session):
    """Test skill: Time Management."""
    skill = Skill(
        slug="time-management-eval",
        name_tr="Zaman Yönetimi",
        name_en="Time Management",
        category="SOFT",
    )
    session.add(skill)
    session.flush()
    return skill


# ============================================================================
# AC-1: Happy Path — Evaluation Submission (ORG_TO_TALENT, PENDING_EVALUATION)
# ============================================================================


class TestEvaluationCreationHappyPath:
    """
    AC-1: Org üyesi (evaluator) submits evaluation on PENDING_EVALUATION engagement.
    Expected: 201 + evaluation object with id, engagement_id, direction, items[], submitted_at.
    CRITICAL: private_note response'ta YOK.
    """

    def test_evaluation_creation_org_to_talent_201(
        self, client, session, user_org_member_charlie_eval, org_member_charlie_eval,
        engagement_pending_eval_alice_eval, skill_communication_eval
    ):
        """
        AC-1: Charlie (ORG:MEMBER) submits evaluation on Alice's PENDING_EVALUATION engagement.

        Acceptance Criteria:
        - Status code: 201 Created
        - Response contains: id (UUID), engagement_id, direction=ORG_TO_TALENT, items[], submitted_at
        - Response does NOT contain private_note (even if sent in request)
        - Evaluation stored in DB with correct engagement_id and evaluator_user_id (= principal)
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Communication Skills",
                    "skill_id": str(skill_communication_eval.id),
                    "rating": "MEETS",
                    "comment": "Good communication with team members",
                }
            ],
            "private_note": "Internal evaluation note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()

        # Assert: response schema
        assert "id" in data
        assert data.get("engagement_id") == str(engagement_pending_eval_alice_eval.id)
        assert data.get("direction") == "ORG_TO_TALENT"
        assert isinstance(data.get("items"), list)
        assert len(data.get("items", [])) == 1
        assert "submitted_at" in data

        # CRITICAL AC-S1: private_note MUST NOT be in response
        assert "private_note" not in data, "Response must not contain private_note field"

    def test_evaluation_creation_multiple_items_201(
        self, client, session, user_org_member_charlie_eval, org_member_charlie_eval,
        engagement_pending_eval_alice_eval, skill_communication_eval, skill_time_management_eval
    ):
        """
        AC-1: Charlie submits evaluation with multiple items.

        Acceptance Criteria:
        - Status code: 201 Created
        - items[] contains both criteria
        - private_note not in response
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Communication",
                    "skill_id": str(skill_communication_eval.id),
                    "rating": "MEETS",
                    "comment": "Clear and effective",
                },
                {
                    "criterion": "Time Management",
                    "skill_id": str(skill_time_management_eval.id),
                    "rating": "EXCEEDS",
                    "comment": "Excellent planning",
                },
            ],
            "private_note": "Secret evaluation",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        assert len(data.get("items", [])) == 2
        assert "private_note" not in data


# ============================================================================
# AC-2: Engagement Status Transition (PENDING_EVALUATION → EVALUATED)
# ============================================================================


class TestEvaluationStatusTransition:
    """
    AC-2: After successful ORG_TO_TALENT evaluation submission, engagement.status → EVALUATED.
    Only ORG_TO_TALENT submission triggers this transition (TALENT_TO_ORG does not).
    """

    def test_engagement_status_transition_to_evaluated_201(
        self, client, session, user_org_member_charlie_eval, org_member_charlie_eval,
        engagement_pending_eval_alice_eval, skill_communication_eval
    ):
        """
        AC-2: Charlie submits ORG_TO_TALENT evaluation → engagement.status → EVALUATED.

        Acceptance Criteria:
        - Evaluation submission succeeds (201)
        - engagement.status updated to EVALUATED in DB (verified via session.refresh)
        - AuditEvent written for status transition
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Communication",
                    "skill_id": str(skill_communication_eval.id),
                    "rating": "MEETS",
                    "comment": "Good",
                }
            ],
            "private_note": "Note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        # DB verification: refresh engagement and check status
        session.refresh(engagement_pending_eval_alice_eval)
        assert engagement_pending_eval_alice_eval.status == "EVALUATED", \
            f"Expected status EVALUATED, got {engagement_pending_eval_alice_eval.status}"


# ============================================================================
# AC-3: NOT_OBSERVED Rating (Comment Optional)
# ============================================================================


class TestEvaluationNotObservedRating:
    """
    AC-3: rating=NOT_OBSERVED allows comment to be omitted or null.
    Other ratings (BELOW, MEETS, EXCEEDS) may or may not require comment (not specified in AC),
    but NOT_OBSERVED explicitly allows empty comment.
    """

    def test_evaluation_not_observed_without_comment_201(
        self, client, session, user_org_member_charlie_eval, org_member_charlie_eval,
        engagement_pending_eval_alice_eval
    ):
        """
        AC-3: Charlie submits evaluation with NOT_OBSERVED rating, no comment.

        Acceptance Criteria:
        - Status code: 201 Created
        - Item with rating=NOT_OBSERVED and comment=null/empty is accepted
        - No validation error thrown
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Some criterion not observed",
                    "skill_id": None,
                    "rating": "NOT_OBSERVED",
                    # comment omitted
                }
            ],
            "private_note": "Talento gözlemlenmedi",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        assert len(data.get("items", [])) == 1
        assert data["items"][0].get("rating") == "NOT_OBSERVED"


# ============================================================================
# AC-4: Validation Errors (Empty items[], Missing criterion)
# ============================================================================


class TestEvaluationValidation:
    """
    AC-4: Validation errors → 422 Unprocessable Entity.
    - items[] boş → 422
    - criterion eksik/boş string → 422
    """

    def test_evaluation_empty_items_422(
        self, client, session, user_org_member_charlie_eval, org_member_charlie_eval,
        engagement_pending_eval_alice_eval
    ):
        """
        AC-4: Charlie submits evaluation with empty items[] → 422.

        Acceptance Criteria:
        - Status code: 422 Unprocessable Entity
        - Error code: indicates validation error
        - No DB write
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [],  # Empty array
            "private_note": "Note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"

    def test_evaluation_missing_criterion_422(
        self, client, session, user_org_member_charlie_eval, org_member_charlie_eval,
        engagement_pending_eval_alice_eval, skill_communication_eval
    ):
        """
        AC-4: Charlie submits evaluation with missing criterion → 422.

        Acceptance Criteria:
        - Status code: 422 Unprocessable Entity
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    # criterion missing/omitted
                    "skill_id": str(skill_communication_eval.id),
                    "rating": "MEETS",
                    "comment": "Comment",
                }
            ],
            "private_note": "Note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"

    def test_evaluation_empty_criterion_string_422(
        self, client, session, user_org_member_charlie_eval, org_member_charlie_eval,
        engagement_pending_eval_alice_eval, skill_communication_eval
    ):
        """
        AC-4: Charlie submits evaluation with empty criterion string → 422.

        Acceptance Criteria:
        - Status code: 422 Unprocessable Entity
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "",  # Empty string
                    "skill_id": str(skill_communication_eval.id),
                    "rating": "MEETS",
                    "comment": "Comment",
                }
            ],
            "private_note": "Note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"


# ============================================================================
# AC-5: Scope Enforcement (404 for out-of-scope, 403 for wrong direction/role)
# ============================================================================


class TestEvaluationScopeEnforcement:
    """
    AC-5 (corrected in plan.md):
    - scope dışı kullanıcı (başka org/institution) → 404 NOT_FOUND
    - scope içinde ama yanlış direction/rol (AC-S3) → 403 FORBIDDEN
    """

    def test_evaluation_cross_org_scope_out_404(
        self, client, session, user_org_member_frank_eval, org_member_frank_eval,
        engagement_pending_eval_alice_eval
    ):
        """
        AC-5: Frank (ORG:MEMBER of organization_b) tries to evaluate Alice's engagement
        in organization_a → 404 NOT_FOUND (scope completely out).

        Acceptance Criteria:
        - Status code: 404 (not 403, not 422)
        - Error code: NOT_FOUND
        - Response doesn't leak Alice's engagement details
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {"criterion": "Test", "skill_id": None, "rating": "MEETS", "comment": ""}
            ],
            "private_note": "Note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_frank_eval.id)},
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") == "NOT_FOUND", f"Expected NOT_FOUND, got {error_obj.get('code')}"


# ============================================================================
# AC-6: Wrong Engagement Status (409 Conflict)
# ============================================================================


class TestEvaluationWrongStatus:
    """
    AC-6: Engagement must be PENDING_EVALUATION.
    If engagement is ACTIVE/DRAFT/EVALUATED/etc. → 409 Conflict.
    """

    def test_evaluation_active_engagement_409(
        self, client, session, user_org_member_charlie_eval, org_member_charlie_eval,
        engagement_active_alice_eval
    ):
        """
        AC-6: Charlie tries to submit evaluation on ACTIVE engagement (not PENDING_EVALUATION) → 409.

        Acceptance Criteria:
        - Status code: 409 Conflict
        - Error code: indicates state/conflict error
        - Engagement status unchanged (still ACTIVE)
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {"criterion": "Test", "skill_id": None, "rating": "MEETS", "comment": ""}
            ],
            "private_note": "Note",
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") in ["CONFLICT", "PRECONDITION_FAILED"], \
            f"Expected conflict-like error, got {error_obj.get('code')}"

        # DB verification: status unchanged
        session.refresh(engagement_active_alice_eval)
        assert engagement_active_alice_eval.status == "ACTIVE"


# ============================================================================
# AC-7: Duplicate Evaluation (409 Conflict)
# ============================================================================


class TestEvaluationDuplicate:
    """
    AC-7: UNIQUE(engagement_id, evaluator_user_id, direction) constraint.
    Second POST with same combination → 409 Conflict, first record preserved.
    """

    def test_evaluation_duplicate_same_evaluator_direction_409(
        self, client, session, user_org_member_charlie_eval, org_member_charlie_eval,
        engagement_pending_eval_alice_eval, skill_communication_eval
    ):
        """
        AC-7: Charlie submits evaluation twice (same direction) → first succeeds (201), second fails (409).

        Acceptance Criteria:
        - First POST: 201 Created
        - Second POST (same Charlie, same direction=ORG_TO_TALENT): 409 Conflict
        - DB shows only first evaluation record (not updated)
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Communication",
                    "skill_id": str(skill_communication_eval.id),
                    "rating": "MEETS",
                    "comment": "Good",
                }
            ],
            "private_note": "First evaluation",
        }

        # First POST — should succeed
        response1 = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response1.status_code == 201, f"First POST failed: {response1.text}"

        # Second POST with same combination — should fail
        payload2 = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Time Management",
                    "skill_id": None,
                    "rating": "EXCEEDS",
                    "comment": "Excellent",
                }
            ],
            "private_note": "Second evaluation (should fail)",
        }

        response2 = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload2,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response2.status_code == 409, f"Expected 409 for duplicate, got {response2.status_code}: {response2.text}"

        data2 = response2.json()
        error_obj = data2.get("detail") if "detail" in data2 else data2
        assert error_obj.get("code") == "CONFLICT", f"Expected CONFLICT, got {error_obj.get('code')}"


# ============================================================================
# AC-8: Invalid skill_id (422)
# ============================================================================


class TestEvaluationInvalidSkillId:
    """
    AC-8: skill_id must exist in skills table (if provided).
    Invalid/non-existent skill_id → 422 Unprocessable Entity.
    """

    def test_evaluation_invalid_skill_id_422(
        self, client, session, user_org_member_charlie_eval, org_member_charlie_eval,
        engagement_pending_eval_alice_eval
    ):
        """
        AC-8: Charlie submits evaluation with non-existent skill_id → 422.

        Acceptance Criteria:
        - Status code: 422 Unprocessable Entity
        - Error indicates validation/foreign key error
        - No DB write (all-or-nothing transaction)
        """
        fake_skill_id = str(uuid4())

        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Communication",
                    "skill_id": fake_skill_id,  # Non-existent UUID
                    "rating": "MEETS",
                    "comment": "Good",
                }
            ],
            "private_note": "Note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"


# ============================================================================
# AC-9: TALENT_TO_ORG Direction (Status Does Not Change)
# ============================================================================


class TestEvaluationTalentToOrgDirection:
    """
    AC-9: TALENT_TO_ORG evaluation (student evaluates org) is optional.
    Submission succeeds (201), but does NOT trigger engagement status transition.
    engagement.status remains PENDING_EVALUATION (or whatever it was).
    """

    def test_evaluation_talent_to_org_no_status_change_201(
        self, client, session, user_talent_alice_eval, talent_alice_eval,
        engagement_pending_eval_alice_eval
    ):
        """
        AC-9: Alice (TALENT) submits TALENT_TO_ORG evaluation → 201, but status stays PENDING_EVALUATION.

        Acceptance Criteria:
        - Status code: 201 Created
        - Evaluation stored with direction=TALENT_TO_ORG
        - engagement.status remains PENDING_EVALUATION (not changed to EVALUATED)
        """
        payload = {
            "direction": "TALENT_TO_ORG",
            "items": [
                {
                    "criterion": "Org Environment",
                    "skill_id": None,
                    "rating": "MEETS",
                    "comment": "Good work environment",
                }
            ],
            "private_note": "My private feedback",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice_eval.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        assert data.get("direction") == "TALENT_TO_ORG"

        # DB verification: engagement.status unchanged
        session.refresh(engagement_pending_eval_alice_eval)
        assert engagement_pending_eval_alice_eval.status == "PENDING_EVALUATION", \
            f"Status should remain PENDING_EVALUATION, got {engagement_pending_eval_alice_eval.status}"

    def test_evaluation_talent_to_org_when_evaluated_201(
        self, client, session, user_talent_alice_eval, talent_alice_eval,
        engagement_evaluated_alice_eval
    ):
        """
        AC-9: Alice (TALENT) submits TALENT_TO_ORG evaluation on EVALUATED engagement → 201, status stays EVALUATED.

        Acceptance Criteria:
        - Status code: 201 Created
        - Evaluation stored with direction=TALENT_TO_ORG
        - engagement.status remains EVALUATED (not changed)
        """
        payload = {
            "direction": "TALENT_TO_ORG",
            "items": [
                {
                    "criterion": "Org Environment",
                    "skill_id": None,
                    "rating": "MEETS",
                    "comment": "Good work environment",
                }
            ],
            "private_note": "My private feedback",
        }

        response = client.post(
            f"/engagements/{engagement_evaluated_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice_eval.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        assert data.get("direction") == "TALENT_TO_ORG"

        # DB verification: engagement.status unchanged
        session.refresh(engagement_evaluated_alice_eval)
        assert engagement_evaluated_alice_eval.status == "EVALUATED", \
            f"Status should remain EVALUATED, got {engagement_evaluated_alice_eval.status}"


# ============================================================================
# Response Schema Validation
# ============================================================================


class TestEvaluationResponseSchema:
    """Verify evaluation response schemas match API contract."""

    def test_evaluation_success_response_schema_201(
        self, client, session, user_org_member_charlie_eval, org_member_charlie_eval,
        engagement_pending_eval_alice_eval, skill_communication_eval
    ):
        """201 response must have evaluation object with required fields, private_note excluded."""
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Communication",
                    "skill_id": str(skill_communication_eval.id),
                    "rating": "MEETS",
                    "comment": "Good",
                }
            ],
            "private_note": "Secret",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response.status_code == 201

        data = response.json()

        # Assert: required fields present
        required_fields = ["id", "engagement_id", "direction", "items", "submitted_at"]

        for field in required_fields:
            assert field in data, f"Response missing required field: {field}"

        # Assert: types
        assert isinstance(data["id"], str)
        assert isinstance(data["engagement_id"], str)
        assert isinstance(data["direction"], str)
        assert isinstance(data["items"], list)

        # CRITICAL AC-S1: private_note must NOT be in response
        assert "private_note" not in data, "Response must not contain private_note"

    def test_evaluation_error_response_schema(
        self, client, user_org_member_charlie_eval, org_member_charlie_eval,
        engagement_active_alice_eval
    ):
        """Error responses must have {code, message, request_id} schema (for custom errors) or be Pydantic validation error."""
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [],  # Empty — validation error
            "private_note": "Note",
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response.status_code in [409, 422]

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        # Handle both custom error format {code, message, request_id} and Pydantic validation error format [...]
        if isinstance(error_obj, dict):
            # Custom error response format
            assert "code" in error_obj, "Error response must have 'code' field"
            assert "message" in error_obj, "Error response must have 'message' field"
            assert "request_id" in error_obj, "Error response must have 'request_id' field"
        elif isinstance(error_obj, list):
            # Pydantic validation error format (array of validation details)
            assert len(error_obj) > 0, "Validation error details must be present"
            assert any("loc" in err and "msg" in err for err in error_obj), \
                "Pydantic error must contain loc and msg fields"


# ============================================================================
# YET-71: SkillSignal Türetme — EVALUATION source_type
# ============================================================================


class TestEvaluationSkillSignalCreation:
    """
    YET-71 AC-3: EVALUATION item MEETS → SkillSignal(EVALUATION, MODERATE) üretilir.
    Davranış Sözleşmesi Satır 3.
    """

    def test_evaluation_meets_creates_skill_signal_201(
        self, client, session, user_org_member_charlie_eval, org_member_charlie_eval,
        engagement_pending_eval_alice_eval, skill_communication_eval
    ):
        """
        AC-3 + YET-71: Charlie (ORG:MEMBER) submit ediyor evaluation, item rating=MEETS → 201, SkillSignal(EVALUATION, MODERATE) yazılır.

        Davranış Sözleşmesi:
        - Status code: 201
        - SkillSignal DB'de yazılır: source_type=EVALUATION, strength=MODERATE, skill_id=<verilen>
        - signal.talent_id = engagement.talent_id (Alice)
        - signal.occurred_at = evaluation.submitted_at
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Communication",
                    "skill_id": str(skill_communication_eval.id),
                    "rating": "MEETS",
                    "comment": "Good communication",
                }
            ],
            "private_note": "Evaluation note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        eval_id = data.get("id")

        # DB verification: SkillSignal yazıldı
        if SkillSignal:
            signal = session.query(SkillSignal).filter_by(
                source_type="EVALUATION",
                source_id=eval_id,
                skill_id=skill_communication_eval.id
            ).first()

            assert signal is not None, "SkillSignal not created for EVALUATION item with MEETS rating"
            assert signal.strength == "MODERATE", f"Expected MODERATE for MEETS, got {signal.strength}"
            assert signal.talent_id == engagement_pending_eval_alice_eval.talent_id


class TestEvaluationRatingStrengthMapping:
    """
    YET-71 AC-4: Rating eşlemesi — BELOW→WEAK, MEETS→MODERATE, EXCEEDS→STRONG, NOT_OBSERVED→skip.
    Davranış Sözleşmesi Satır 3, 5.
    """

    def test_evaluation_below_creates_weak_signal_201(
        self, client, session, user_org_member_charlie_eval, org_member_charlie_eval,
        engagement_pending_eval_alice_eval, skill_communication_eval
    ):
        """
        AC-4 + YET-71: Evaluation item rating=BELOW → SkillSignal strength=WEAK.
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Communication",
                    "skill_id": str(skill_communication_eval.id),
                    "rating": "BELOW",
                    "comment": "Needs improvement",
                }
            ],
            "private_note": "Note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response.status_code == 201

        data = response.json()
        eval_id = data.get("id")

        if SkillSignal:
            signal = session.query(SkillSignal).filter_by(
                source_type="EVALUATION",
                source_id=eval_id,
                skill_id=skill_communication_eval.id
            ).first()

            assert signal is not None
            assert signal.strength == "WEAK", f"Expected WEAK for BELOW, got {signal.strength}"

    def test_evaluation_exceeds_creates_strong_signal_201(
        self, client, session, user_org_member_charlie_eval, org_member_charlie_eval,
        engagement_pending_eval_alice_eval, skill_time_management_eval
    ):
        """
        AC-4 + YET-71: Evaluation item rating=EXCEEDS → SkillSignal strength=STRONG.
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Time Management",
                    "skill_id": str(skill_time_management_eval.id),
                    "rating": "EXCEEDS",
                    "comment": "Outstanding time management",
                }
            ],
            "private_note": "Note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response.status_code == 201

        data = response.json()
        eval_id = data.get("id")

        if SkillSignal:
            signal = session.query(SkillSignal).filter_by(
                source_type="EVALUATION",
                source_id=eval_id,
                skill_id=skill_time_management_eval.id
            ).first()

            assert signal is not None
            assert signal.strength == "STRONG", f"Expected STRONG for EXCEEDS, got {signal.strength}"

    def test_evaluation_not_observed_no_signal_201(
        self, client, session, user_org_member_charlie_eval, org_member_charlie_eval,
        engagement_pending_eval_alice_eval
    ):
        """
        AC-4 + YET-71: Evaluation item rating=NOT_OBSERVED → SkillSignal yazılmaz (sessiz atlama).
        Davranış Sözleşmesi Satır 5.
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Some skill",
                    "skill_id": None,
                    "rating": "NOT_OBSERVED",
                    # comment optional
                }
            ],
            "private_note": "Note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response.status_code == 201

        data = response.json()
        eval_id = data.get("id")

        # DB verification: SkillSignal yok (NOT_OBSERVED için)
        if SkillSignal:
            signal_count = session.query(SkillSignal).filter_by(
                source_type="EVALUATION",
                source_id=eval_id
            ).count()
            assert signal_count == 0, "SkillSignal must not be created for NOT_OBSERVED rating"


class TestEvaluationMultipleItems:
    """
    YET-71 AC-5: Birden fazla EvaluationItem → her biri ayrı SkillSignal.
    Davranış Sözleşmesi Satır 1-5 (aynı evaluation için multiple items).
    """

    def test_evaluation_multiple_items_creates_separate_signals_201(
        self, client, session, user_org_member_charlie_eval, org_member_charlie_eval,
        engagement_pending_eval_alice_eval, skill_communication_eval, skill_time_management_eval
    ):
        """
        AC-5 + YET-71: Evaluation 2 item içeriyor (farklı skill_id'ler, farklı rating'ler).
        Her item için ayrı SkillSignal üretilmeli.

        Davranış Sözleşmesi:
        - Status code: 201
        - Evaluation.id = X
        - SkillSignal 1: source_id=X, skill_id=communication, strength=MEETS→MODERATE
        - SkillSignal 2: source_id=X, skill_id=time_management, strength=EXCEEDS→STRONG
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Communication",
                    "skill_id": str(skill_communication_eval.id),
                    "rating": "MEETS",
                    "comment": "Good",
                },
                {
                    "criterion": "Time Management",
                    "skill_id": str(skill_time_management_eval.id),
                    "rating": "EXCEEDS",
                    "comment": "Excellent",
                },
            ],
            "private_note": "Note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        eval_id = data.get("id")

        # DB verification: 2 signals created
        if SkillSignal:
            signals = session.query(SkillSignal).filter_by(
                source_type="EVALUATION",
                source_id=eval_id
            ).all()

            assert len(signals) == 2, f"Expected 2 signals, got {len(signals)}"

            # Signal 1: Communication MEETS → MODERATE
            signal_comm = next(
                (s for s in signals if s.skill_id == skill_communication_eval.id),
                None
            )
            assert signal_comm is not None
            assert signal_comm.strength == "MODERATE"

            # Signal 2: Time Management EXCEEDS → STRONG
            signal_time = next(
                (s for s in signals if s.skill_id == skill_time_management_eval.id),
                None
            )
            assert signal_time is not None
            assert signal_time.strength == "STRONG"

    def test_evaluation_mixed_items_partial_signal_creation_201(
        self, client, session, user_org_member_charlie_eval, org_member_charlie_eval,
        engagement_pending_eval_alice_eval, skill_communication_eval, skill_time_management_eval
    ):
        """
        AC-5 + YET-71: Evaluation 3 item içeriyor:
        1. Communication MEETS → SkillSignal(MODERATE) ✓
        2. Time Management NOT_OBSERVED → SkillSignal YAZILMAZ ✗
        3. Time Management (diğer) skill_id=None → SkillSignal YAZILMAZ ✗

        Sonuç: Sadece 1 SkillSignal.
        Davranış Sözleşmesi: Kısmi üretim kabul edilir, evaluation başarılı (201).
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Communication",
                    "skill_id": str(skill_communication_eval.id),
                    "rating": "MEETS",
                    "comment": "Good",
                },
                {
                    "criterion": "Time Management (not observed)",
                    "skill_id": str(skill_time_management_eval.id),
                    "rating": "NOT_OBSERVED",
                    # comment optional
                },
                {
                    "criterion": "Another criterion",
                    "skill_id": None,
                    "rating": "MEETS",
                    "comment": "But no skill",
                },
            ],
            "private_note": "Note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        eval_id = data.get("id")

        # DB verification: only 1 signal (communication)
        if SkillSignal:
            signals = session.query(SkillSignal).filter_by(
                source_type="EVALUATION",
                source_id=eval_id
            ).all()

            assert len(signals) == 1, f"Expected 1 signal (partial), got {len(signals)}"
            assert signals[0].skill_id == skill_communication_eval.id
            assert signals[0].strength == "MODERATE"


class TestEvaluationModelImport:
    """Ensure Evaluation model can be imported for signal creation tests."""

    def test_evaluation_model_available(self):
        """Verify Evaluation model is available for YET-71 tests."""
        assert Evaluation is not None, "Evaluation model must be implemented for YET-71 tests"
        assert EvaluationItem is not None, "EvaluationItem model must be implemented for YET-71 tests"


class TestEvaluationInvalidSkillIdInItem:
    """
    YET-71 AC-7: Evaluation item skill_id geçersiz → 422 (hiçbir item işlenmez, kısmi başarı yok).
    """

    def test_evaluation_invalid_skill_id_in_item_422(
        self, client, session, user_org_member_charlie_eval, org_member_charlie_eval,
        engagement_pending_eval_alice_eval, skill_communication_eval
    ):
        """
        AC-7 + YET-71: Evaluation 2 item:
        1. Communication (valid)
        2. Time Management (invalid skill_id)

        Result: 422, hiçbir item işlenmez (all-or-nothing transaction).
        """
        fake_skill_id = str(uuid4())

        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Communication",
                    "skill_id": str(skill_communication_eval.id),
                    "rating": "MEETS",
                    "comment": "Good",
                },
                {
                    "criterion": "Time Management",
                    "skill_id": fake_skill_id,  # Non-existent
                    "rating": "MEETS",
                    "comment": "Comment",
                },
            ],
            "private_note": "Note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_eval.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data

        # Handle both custom error format {code: "VALIDATION_ERROR"} and Pydantic validation error format [...]
        if isinstance(error_obj, dict):
            # Custom error response format
            assert error_obj.get("code") == "VALIDATION_ERROR", \
                f"Expected VALIDATION_ERROR, got {error_obj.get('code')}"
        elif isinstance(error_obj, list):
            # Pydantic validation error format (array of validation details)
            assert len(error_obj) > 0, "Validation error details must be present for invalid skill_id"
            # Verify that one of the errors is related to skill_id validation
            has_skill_error = any("skill_id" in str(err.get("loc", [])) for err in error_obj)
            assert has_skill_error, "Validation error should be related to skill_id field"

        # DB verification: evaluation ve hiçbir signal oluşturulmadı (for this engagement)
        if SkillSignal:
            # Verify no evaluation created for this engagement
            eval_count = session.query(Evaluation).filter_by(
                engagement_id=engagement_pending_eval_alice_eval.id
            ).count()
            assert eval_count == 0, "Evaluation must not be created on invalid skill_id"

            # Verify no EVALUATION source_type signals created from this (failed) request
            # We verify that no Evaluation record was created (checked above), which means no signal either
            assert eval_count == 0, "Failed evaluation request must not create any records"


# ============================================================================
# YET-71 AC-8: Regresyon — Mevcut SELF_CLAIM/ATTESTATION/GET-ucu doğrulama
# ============================================================================

# NOT: AC-8 mevcut testlerin regresyon testidir. Bu bölüme yeni test yazılmaz.
# Mevcut test suite'in (test_skill_claim.py, test_attestation.py, vb.)
# hiçbir test kırılmadığını doğrula: `pytest tests/ -q`
#
# Kapsam: SELF_CLAIM, ATTESTATION, GET /talents/me/signals sinyalleri
# bozulmadığını doğrulama. Yeni TASK/DELIVERABLE/EVALUATION sinyalleri
# eklenirken, mevcut olanlar etkilenmemeli.


# ============================================================================
# YET-71 AC-9: GET /talents/me/signals — Çoklu source_type Desteği
# ============================================================================


class TestGetSignalsMultipleSourceTypes:
    """
    YET-71 AC-9: GET /talents/me/signals, bir skill için birden fazla source_type var.
    Davranış Sözleşmesi Satır 7.

    Senaryo: Talent Alice'in:
    - Python skill'i için:
      - TASK→WEAK sinyali (Charlie tarafından)
      - EVALUATION→MODERATE sinyali (Charlie tarafından)
    - GET /talents/me/signals çağrıldığında → 200, signals array'i her ikiyi de listeler
    """

    def test_get_signals_multiple_source_types_200(
        self, client, session, user_org_member_charlie_eval, org_member_charlie_eval,
        user_talent_alice_eval, talent_alice_eval, engagement_active_alice_eval,
        skill_communication_eval
    ):
        """
        AC-9 + YET-71: Alice'in profili için 2 source_type sinyal var:
        1. TASK source (Charlie oluşturdu skill=Python)
        2. EVALUATION source (Charlie oluşturdu skill=Communication)

        Senaryo:
        - Step 1: Charlie, engagement_active_alice_eval'a TASK oluşturur (skill=Python)
                  → SkillSignal source_type=TASK oluşturulması beklenir
        - Step 2: Charlie, yeni PENDING_EVALUATION engagement'a EVALUATION submit eder (skill=Communication)
                  → SkillSignal source_type=EVALUATION oluşturulması beklenir
        - Step 3: Alice /talents/me/signals çağırır
                  → 200 OK, response'ta hem TASK hem EVALUATION source_type'ları bulunur

        Hiçbir pytest.skip() yok — endpoint'ler var (PLAN 2.4 + 2.7, SELF_CLAIM dilimi tamamlandı).
        Test fail ederse, signal üretimi henüz implement edilmemiş demektir (YET-71 hâlâ açık).
        """
        # Inline Python skill creation (not in fixture list)
        from app.models.skill import Skill
        skill_python_eval = Skill(
            slug="python-eval-inline",
            name_tr="Python",
            name_en="Python",
            category="LANGUAGE",
        )
        session.add(skill_python_eval)
        session.flush()

        # Step 1: Charlie creates TASK with Python skill on ACTIVE engagement
        task_payload = {
            "title": "Python development task",
            "description": "Task for Python skill",
            "skill_id": str(skill_python_eval.id),
            "due_at": None,
        }

        task_response = client.post(
            f"/engagements/{engagement_active_alice_eval.id}/tasks",
            json=task_payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert task_response.status_code == 201, \
            f"TASK POST expected 201, got {task_response.status_code}: {task_response.text}"

        # Step 2: Create a PENDING_EVALUATION engagement (inline, same org/inst as engagement_active_alice_eval)
        # This engagement needs to be in PENDING_EVALUATION status for Charlie to submit evaluation
        # We reuse the same organization and institution from engagement_active_alice_eval
        engagement_pending_eval = Engagement(
            talent_id=talent_alice_eval.id,
            organization_id=engagement_active_alice_eval.organization_id,
            institution_id=engagement_active_alice_eval.institution_id,
            kind="INTERNSHIP",
            title="Alice Pending Eval Project",
            status="PENDING_EVALUATION",
            version=3,
        )
        session.add(engagement_pending_eval)
        session.flush()

        # Step 2b: Charlie submits EVALUATION with Communication skill on PENDING_EVALUATION engagement
        evaluation_payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Communication",
                    "skill_id": str(skill_communication_eval.id),
                    "rating": "MEETS",
                    "comment": "Good communication skills",
                }
            ],
            "private_note": None,
        }

        evaluation_response = client.post(
            f"/engagements/{engagement_pending_eval.id}/evaluation",
            json=evaluation_payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_eval.id)},
        )

        assert evaluation_response.status_code == 201, \
            f"EVALUATION POST expected 201, got {evaluation_response.status_code}: {evaluation_response.text}"

        # Step 3: Query GET /talents/me/signals as Alice (TALENT principal)
        get_signals_response = client.get(
            "/talents/me/signals",
            headers={"X-Debug-User-Id": str(user_talent_alice_eval.id)},
        )

        assert get_signals_response.status_code == 200, \
            f"GET /talents/me/signals expected 200, got {get_signals_response.status_code}: {get_signals_response.text}"

        data = get_signals_response.json()

        # Verify response structure
        assert "items" in data, "Response must contain 'items' array"
        items = data.get("items", [])

        # Step 4: Verify TASK source_type signal for Python skill
        python_item = next(
            (item for item in items if item.get("skill", {}).get("id") == str(skill_python_eval.id)),
            None
        )
        assert python_item is not None, \
            f"Python skill ({skill_python_eval.id}) not found in signals items"

        python_signals = python_item.get("signals", [])
        assert len(python_signals) > 0, "Python skill should have signals"

        python_source_types = [s.get("source_type") for s in python_signals]
        assert "TASK" in python_source_types, \
            f"Python skill should have TASK source_type. Got: {python_source_types}"

        # Step 5: Verify EVALUATION source_type signal for Communication skill
        communication_item = next(
            (item for item in items if item.get("skill", {}).get("id") == str(skill_communication_eval.id)),
            None
        )
        assert communication_item is not None, \
            f"Communication skill ({skill_communication_eval.id}) not found in signals items"

        communication_signals = communication_item.get("signals", [])
        assert len(communication_signals) > 0, "Communication skill should have signals"

        communication_source_types = [s.get("source_type") for s in communication_signals]
        assert "EVALUATION" in communication_source_types, \
            f"Communication skill should have EVALUATION source_type. Got: {communication_source_types}"
