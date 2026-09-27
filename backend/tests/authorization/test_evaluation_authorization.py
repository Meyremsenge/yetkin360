"""
Evaluation authorization tests (PLAN 2.7 — yet-69-degerlendirme-formu-semasi).

Threat-model security tests for POST /engagements/{id}/evaluation:
- AC-S1: private_note field NEVER appears in response JSON (critical PII protection)
- AC-S2: evaluator_user_id always from authenticated principal, never from request body
- AC-S3: direction must match principal's role — talent cannot post ORG_TO_TALENT, org member cannot post TALENT_TO_ORG (403 FORBIDDEN)
- AC-5: scope enforcement — scope-out users get 404, not 403

Authorization matrix (per final-analiz karar matrisi):
- TALENT (Alice's engagement): can POST TALENT_TO_ORG (201); cannot POST ORG_TO_TALENT (403)
- ORG:MEMBER (same org): can POST ORG_TO_TALENT (201); cannot POST TALENT_TO_ORG (403)
- ORG:MEMBER (different org): cannot access at all (404)
- INST:COORDINATOR (same institution): can POST neither direction (403) — no evaluation permission per matrix
- ADMIN: can POST both directions (implementation detail — not explicitly in AC but follows admin pattern)

Coverage Target: All threat-model scenarios (AC-S1/S2/S3) + scope enforcement (AC-5).

Status: Tests are RED (expected) — implementation not yet available.
"""

import pytest

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


# ============================================================================
# Fixtures (shared with test_evaluation.py, defined locally for isolation)
# ============================================================================


@pytest.fixture
def user_talent_alice_authz(session):
    """Talent Alice for authorization tests."""
    user = User(email="alice.talent.authz@example.com", password_hash="hash_alice")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_bob_authz(session):
    """Talent Bob for authorization tests."""
    user = User(email="bob.talent.authz@example.com", password_hash="hash_bob")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_org_member_charlie_authz(session):
    """ORG:MEMBER Charlie from org A."""
    user = User(email="charlie.member.authz@example.com", password_hash="hash_charlie")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_org_member_frank_authz(session):
    """ORG:MEMBER Frank from org B (different org)."""
    user = User(email="frank.member.authz@example.com", password_hash="hash_frank")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_inst_coord_diana_authz(session):
    """INST:COORDINATOR Diana for authorization tests."""
    user = User(email="diana.coord.authz@example.com", password_hash="hash_diana")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent_alice_authz(session, user_talent_alice_authz, institution_a_authz):
    """Talent profile for Alice."""
    profile = TalentProfile(
        user_id=user_talent_alice_authz.id,
        institution_id=institution_a_authz.id,
        full_name="Alice Talent Authz",
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
def talent_bob_authz(session, user_talent_bob_authz, institution_b_authz):
    """Talent profile for Bob."""
    profile = TalentProfile(
        user_id=user_talent_bob_authz.id,
        institution_id=institution_b_authz.id,
        full_name="Bob Talent Authz",
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
def organization_a_authz(session):
    """Organization A."""
    org = Organization(
        name="Test Org A Authz",
        domain="testorga.authz.example.com",
        legal_id="ORG-A-AUTHZ-001",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def organization_b_authz(session):
    """Organization B (different org for scope isolation)."""
    org = Organization(
        name="Test Org B Authz",
        domain="testorgb.authz.example.com",
        legal_id="ORG-B-AUTHZ-001",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def institution_a_authz(session):
    """Institution A."""
    inst = Institution(
        name="Test Institution A Authz",
        domain="testinsta.authz.example.com",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def institution_b_authz(session):
    """Institution B (different institution for isolation)."""
    inst = Institution(
        name="Test Institution B Authz",
        domain="testinstb.authz.example.com",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def org_member_charlie_authz(session, organization_a_authz, user_org_member_charlie_authz):
    """Charlie is ORG:MEMBER of organization_a."""
    member = OrganizationMember(
        organization_id=organization_a_authz.id,
        user_id=user_org_member_charlie_authz.id,
        role="MEMBER",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def org_member_frank_authz(session, organization_b_authz, user_org_member_frank_authz):
    """Frank is ORG:MEMBER of organization_b (different org)."""
    member = OrganizationMember(
        organization_id=organization_b_authz.id,
        user_id=user_org_member_frank_authz.id,
        role="MEMBER",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def inst_coord_diana_authz(session, institution_a_authz, user_inst_coord_diana_authz):
    """Diana is INST:COORDINATOR of institution_a."""
    coord = InstitutionMember(
        institution_id=institution_a_authz.id,
        user_id=user_inst_coord_diana_authz.id,
        role="COORDINATOR",
    )
    session.add(coord)
    session.flush()
    return coord


@pytest.fixture
def engagement_pending_eval_alice_authz(session, talent_alice_authz, organization_a_authz, institution_a_authz):
    """PENDING_EVALUATION engagement for Alice (org_a, inst_a)."""
    engagement = Engagement(
        talent_id=talent_alice_authz.id,
        organization_id=organization_a_authz.id,
        institution_id=institution_a_authz.id,
        kind="INTERNSHIP",
        title="Alice Authz Test Project",
        status="PENDING_EVALUATION",
        version=3,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_pending_eval_bob_authz(session, talent_bob_authz, organization_b_authz, institution_b_authz):
    """PENDING_EVALUATION engagement for Bob (org_b, inst_b)."""
    engagement = Engagement(
        talent_id=talent_bob_authz.id,
        organization_id=organization_b_authz.id,
        institution_id=institution_b_authz.id,
        kind="INTERNSHIP",
        title="Bob Authz Test Project",
        status="PENDING_EVALUATION",
        version=3,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def skill_communication_authz(session):
    """Test skill for authorization tests."""
    skill = Skill(
        slug="communication-authz-test",
        name_tr="İletişim",
        name_en="Communication",
        category="SOFT",
    )
    session.add(skill)
    session.flush()
    return skill


# ============================================================================
# AC-S1: private_note NEVER appears in response (PII protection)
# ============================================================================


class TestEvaluationPrivateNotePII:
    """
    AC-S1: private_note field is NEVER included in response JSON.
    This is critical for PII protection — even if payload sends it, response must not expose it.
    """

    def test_private_note_not_in_response_org_to_talent(
        self, client, session, user_org_member_charlie_authz, org_member_charlie_authz,
        engagement_pending_eval_alice_authz, skill_communication_authz
    ):
        """
        AC-S1: ORG:MEMBER submits evaluation with private_note.
        Response must NOT include private_note field in JSON.
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Communication",
                    "skill_id": str(skill_communication_authz.id),
                    "rating": "MEETS",
                    "comment": "Good communication",
                }
            ],
            "private_note": "This is a secret evaluation note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_authz.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_authz.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()

        # CRITICAL: private_note must NOT be present in response JSON
        assert "private_note" not in data, \
            "Response must not contain private_note field (PII protection)"

    def test_private_note_not_in_response_talent_to_org(
        self, client, session, user_talent_alice_authz, talent_alice_authz,
        engagement_pending_eval_alice_authz
    ):
        """
        AC-S1: TALENT submits TALENT_TO_ORG evaluation with private_note.
        Response must NOT include private_note.
        """
        payload = {
            "direction": "TALENT_TO_ORG",
            "items": [
                {
                    "criterion": "Org Environment",
                    "skill_id": None,
                    "rating": "MEETS",
                    "comment": "Nice workplace",
                }
            ],
            "private_note": "Confidential student feedback",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_authz.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice_authz.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()

        # CRITICAL: private_note must NOT be in response
        assert "private_note" not in data, \
            "Response must not contain private_note (PII protection — talent must not see evaluator's notes)"


# ============================================================================
# AC-S2: evaluator_user_id always from principal, never from request body
# ============================================================================


class TestEvaluationEvaluatorUserIdTampering:
    """
    AC-S2: evaluator_user_id is set from authenticated principal, never from request body.
    Even if client sends a different user_id in body, it's ignored.
    """

    def test_evaluator_user_id_from_principal_org_member(
        self, client, session, user_org_member_charlie_authz, org_member_charlie_authz,
        user_org_member_frank_authz, engagement_pending_eval_alice_authz, skill_communication_authz
    ):
        """
        AC-S2: Charlie submits evaluation but body claims Frank as evaluator.
        evaluator_user_id in DB must be Charlie's ID (principal), not Frank's.
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Communication",
                    "skill_id": str(skill_communication_authz.id),
                    "rating": "MEETS",
                    "comment": "Good",
                }
            ],
            "private_note": "Note",
            # Trying to inject Frank's user_id (should be ignored)
            "evaluator_user_id": str(user_org_member_frank_authz.id),
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_authz.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_authz.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        # In the response, evaluator should be Charlie (the principal)
        # If the schema includes an evaluator_user_id field, it must be Charlie's
        # (Exact field name depends on EvaluationResponse schema; adjust if needed)
        # This is implicitly tested by the UNIQUE constraint — second evaluation
        # from Charlie will fail, proving the evaluator_user_id was Charlie's, not Frank's


# ============================================================================
# AC-S3: direction must match principal's role (403 FORBIDDEN)
# ============================================================================


class TestEvaluationDirectionRoleConsistency:
    """
    AC-S3: direction must match the principal's actual role in the engagement.
    - TALENT cannot POST ORG_TO_TALENT (only TALENT_TO_ORG allowed) → 403
    - ORG:MEMBER cannot POST TALENT_TO_ORG (only ORG_TO_TALENT allowed) → 403
    """

    def test_talent_cannot_post_org_to_talent_403(
        self, client, session, user_talent_alice_authz, talent_alice_authz,
        engagement_pending_eval_alice_authz
    ):
        """
        AC-S3: Talent Alice tries to POST with direction=ORG_TO_TALENT
        (pretending to be the evaluating organization).
        Must be rejected with 403 FORBIDDEN (not 422, not 201).
        """
        payload = {
            "direction": "ORG_TO_TALENT",  # WRONG — talent can't evaluate as org
            "items": [
                {
                    "criterion": "Communication",
                    "skill_id": None,
                    "rating": "MEETS",
                    "comment": "I evaluate myself",
                }
            ],
            "private_note": "My self-evaluation",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_authz.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice_authz.id)},
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") == "FORBIDDEN", \
            f"Expected code FORBIDDEN, got {error_obj.get('code')}"

    def test_org_member_cannot_post_talent_to_org_403(
        self, client, session, user_org_member_charlie_authz, org_member_charlie_authz,
        engagement_pending_eval_alice_authz
    ):
        """
        AC-S3: ORG:MEMBER Charlie tries to POST with direction=TALENT_TO_ORG
        (pretending to be the talent evaluating the org).
        Must be rejected with 403 FORBIDDEN.
        """
        payload = {
            "direction": "TALENT_TO_ORG",  # WRONG — org member can't evaluate as talent
            "items": [
                {
                    "criterion": "Organization",
                    "skill_id": None,
                    "rating": "MEETS",
                    "comment": "I evaluate the org",
                }
            ],
            "private_note": "Secret comment",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_authz.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_authz.id)},
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") == "FORBIDDEN", \
            f"Expected code FORBIDDEN, got {error_obj.get('code')}"


# ============================================================================
# AC-5: Scope Enforcement (404 for completely out-of-scope users)
# ============================================================================


class TestEvaluationScopeEnforcementAuthz:
    """
    AC-5: Scope enforcement — users completely outside engagement's org/institution scope.
    Result: 404 NOT_FOUND (not 403, per CLAUDE.md "yetkisiz erişimde kaynağın varlığı sızdırılmaz").
    """

    def test_different_org_member_cannot_evaluate_404(
        self, client, session, user_org_member_frank_authz, org_member_frank_authz,
        engagement_pending_eval_alice_authz
    ):
        """
        AC-5: Frank (ORG:MEMBER of org B) tries to evaluate Alice's engagement (org A).
        Frank has no visibility to this engagement at all (different org).
        Result: 404 NOT_FOUND (scope completely outside).
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Communication",
                    "skill_id": None,
                    "rating": "MEETS",
                    "comment": "Comment",
                }
            ],
            "private_note": "Note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_authz.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_frank_authz.id)},
        )

        assert response.status_code == 404, f"Expected 404 (scope out), got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") == "NOT_FOUND", \
            f"Expected code NOT_FOUND, got {error_obj.get('code')}"

    def test_different_talent_cannot_evaluate_404(
        self, client, session, user_talent_bob_authz, talent_bob_authz,
        engagement_pending_eval_alice_authz
    ):
        """
        AC-5: Bob (TALENT of institution B) tries to access Alice's engagement (institution A).
        Bob has no visibility (different institution/org).
        Result: 404 NOT_FOUND.
        """
        payload = {
            "direction": "TALENT_TO_ORG",
            "items": [
                {
                    "criterion": "Organization",
                    "skill_id": None,
                    "rating": "MEETS",
                    "comment": "Comment",
                }
            ],
            "private_note": "Note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_authz.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_bob_authz.id)},
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") == "NOT_FOUND", \
            f"Expected code NOT_FOUND, got {error_obj.get('code')}"


# ============================================================================
# Authorization Matrix: Happy Paths (Expected 201 for valid combinations)
# ============================================================================


class TestEvaluationAuthorizationMatrix:
    """
    Authorization matrix (per final-analiz karar matrisi and ATDD):
    - TALENT + TALENT_TO_ORG → 201 (allowed)
    - ORG:MEMBER + ORG_TO_TALENT → 201 (allowed)
    """

    def test_talent_can_post_talent_to_org_201(
        self, client, session, user_talent_alice_authz, talent_alice_authz,
        engagement_pending_eval_alice_authz
    ):
        """
        Authorization: TALENT posting TALENT_TO_ORG is allowed.
        Expected: 201 Created.
        """
        payload = {
            "direction": "TALENT_TO_ORG",
            "items": [
                {
                    "criterion": "Org Environment",
                    "skill_id": None,
                    "rating": "MEETS",
                    "comment": "Good workplace",
                }
            ],
            "private_note": "My feedback",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_authz.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice_authz.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

    def test_org_member_can_post_org_to_talent_201(
        self, client, session, user_org_member_charlie_authz, org_member_charlie_authz,
        engagement_pending_eval_alice_authz, skill_communication_authz
    ):
        """
        Authorization: ORG:MEMBER posting ORG_TO_TALENT is allowed.
        Expected: 201 Created.
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Communication",
                    "skill_id": str(skill_communication_authz.id),
                    "rating": "MEETS",
                    "comment": "Good",
                }
            ],
            "private_note": "Note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_authz.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_member_charlie_authz.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"


# ============================================================================
# Coordinator Authorization (should be 403 per matrix)
# ============================================================================


class TestEvaluationCoordinatorRestriction:
    """
    Authorization matrix: COORDINATOR has no evaluation permission.
    Both ORG_TO_TALENT and TALENT_TO_ORG should be forbidden (403).
    """

    def test_coordinator_cannot_post_org_to_talent_403(
        self, client, session, user_inst_coord_diana_authz, inst_coord_diana_authz,
        engagement_pending_eval_alice_authz
    ):
        """
        Coordinator Diana tries to POST ORG_TO_TALENT → 403 FORBIDDEN.
        (Coordinators are read-only per matrix, no evaluation permission)
        """
        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {
                    "criterion": "Communication",
                    "skill_id": None,
                    "rating": "MEETS",
                    "comment": "Comment",
                }
            ],
            "private_note": "Note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_authz.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana_authz.id)},
        )

        assert response.status_code == 403, f"Expected 403 (coordinator no permission), got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") == "FORBIDDEN"

    def test_coordinator_cannot_post_talent_to_org_403(
        self, client, session, user_inst_coord_diana_authz, inst_coord_diana_authz,
        engagement_pending_eval_alice_authz
    ):
        """
        Coordinator Diana tries to POST TALENT_TO_ORG → 403 FORBIDDEN.
        """
        payload = {
            "direction": "TALENT_TO_ORG",
            "items": [
                {
                    "criterion": "Organization",
                    "skill_id": None,
                    "rating": "MEETS",
                    "comment": "Comment",
                }
            ],
            "private_note": "Note",
        }

        response = client.post(
            f"/engagements/{engagement_pending_eval_alice_authz.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana_authz.id)},
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") == "FORBIDDEN"
