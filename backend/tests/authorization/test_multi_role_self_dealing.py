"""
Multi-role self-dealing authorization tests (PLAN 2.x — yet-187-coklu-rol AC-S1).

Threat-model security tests for user S: talent of engagement E2, ORG_ADMIN of O1, COORDINATOR of K1.

Scenarios 16-24 from authz_test.md:
- 16: S attests own E2 (ORG_ADMIN/COORDINATOR path) → 409 SELF_ATTESTATION_FORBIDDEN, no record
- 17: S evaluates own E2 with ORG_TO_TALENT → 403, no record
- 18: S transitions own E2 PENDING_APPROVAL→ACTIVE/REJECTED (as coordinator) → 403, no DB change
- 19: S transitions own E2 ACTIVE→CANCELLED, ACTIVE→PENDING_EVALUATION, posts task → 403, no DB change
- 20: S performs talent-side actions on own E2 (DRAFT→PENDING, deliverable, TALENT_TO_ORG eval) → 2xx
- 21: S performs org/coordinator actions on E3 (different talent, O1/K1 scope) → 2xx
- 22: S as ORG_MEMBER (not ADMIN) of own engagement: task/PENDING_EVALUATION → 403, no DB change
- 23: S creates engagement with own talent_id → 2xx
- 24: Pure talent T1 (no org/institution membership) attests → 403, no record

Coverage: AC-S1 (self-dealing masking via engagement_relation), AC-S2 (tenant isolation).
Status: Tests validate mevcut uygulama kodu.
"""

import pytest
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
    EngagementTask,
    Evaluation,
    Attestation,
)


# ============================================================================
# Fixtures for multi-role user S and supporting actors
# ============================================================================


@pytest.fixture
def sd_user_s(session):
    """User S: self-dealing scenario — talent + ORG_ADMIN + COORDINATOR."""
    user = User(email="s.multirole@example.com", password_hash="hash_s_multirole")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def sd_talent_s(session, sd_user_s):
    """Talent profile of user S (associated with K1)."""
    talent = TalentProfile(
        user_id=sd_user_s.id,
        institution_id=None,  # Set explicitly below via fixture
        full_name="User S Talent",
        visibility="PRIVATE",
    )
    session.add(talent)
    session.flush()
    return talent


@pytest.fixture
def sd_institution_k1(session):
    """Institution K1 where S is COORDINATOR."""
    inst = Institution(
        name="Institution K1",
        domain="k1.example.com",
        verification_level="T2",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def sd_institution_k2(session):
    """Institution K2 (used in scenario 21, different from S's institution)."""
    inst = Institution(
        name="Institution K2",
        domain="k2.example.com",
        verification_level="T2",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def sd_organization_o1(session):
    """Organization O1 where S is ADMIN."""
    org = Organization(
        name="Organization O1",
        domain="o1.example.com",
        legal_id="ORG-O1-001",
        verification_level="T2",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def sd_organization_o2(session):
    """Organization O2 (used in scenario 21, different from S's organization)."""
    org = Organization(
        name="Organization O2",
        domain="o2.example.com",
        legal_id="ORG-O2-001",
        verification_level="T2",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def sd_s_membership_org_admin(session, sd_user_s, sd_organization_o1):
    """S is ORG_ADMIN of O1."""
    member = OrganizationMember(
        organization_id=sd_organization_o1.id,
        user_id=sd_user_s.id,
        role="ADMIN",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def sd_s_membership_coordinator(session, sd_user_s, sd_institution_k1):
    """S is COORDINATOR of K1."""
    member = InstitutionMember(
        institution_id=sd_institution_k1.id,
        user_id=sd_user_s.id,
        role="COORDINATOR",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def sd_talent_s_with_k1(session, sd_user_s, sd_institution_k1):
    """Update talent S to have K1 as institution."""
    talent = session.query(TalentProfile).filter_by(user_id=sd_user_s.id).first()
    talent.institution_id = sd_institution_k1.id
    session.flush()
    return talent


@pytest.fixture
def sd_engagement_e2_draft(session, sd_talent_s, sd_organization_o1, sd_institution_k1):
    """Engagement E2: DRAFT status, talent=S, org=O1, institution=K1."""
    now = datetime.now(timezone.utc)
    engagement = Engagement(
        talent_id=sd_talent_s.id,
        organization_id=sd_organization_o1.id,
        institution_id=sd_institution_k1.id,
        kind="INTERNSHIP",
        title="E2 (S's Engagement)",
        status="DRAFT",
        version=1,
        started_on=now - timedelta(days=35),
        ended_on=now - timedelta(days=1),
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def sd_engagement_e2_pending(session, sd_talent_s, sd_organization_o1, sd_institution_k1):
    """Engagement E2: PENDING_APPROVAL status (for scenario 18)."""
    now = datetime.now(timezone.utc)
    engagement = Engagement(
        talent_id=sd_talent_s.id,
        organization_id=sd_organization_o1.id,
        institution_id=sd_institution_k1.id,
        kind="INTERNSHIP",
        title="E2 (S's Engagement, PENDING)",
        status="PENDING_APPROVAL",
        version=1,
        started_on=now - timedelta(days=35),
        ended_on=now - timedelta(days=1),
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def sd_engagement_e2_active(session, sd_talent_s, sd_organization_o1, sd_institution_k1):
    """Engagement E2: ACTIVE status (for scenarios 19, 20)."""
    now = datetime.now(timezone.utc)
    engagement = Engagement(
        talent_id=sd_talent_s.id,
        organization_id=sd_organization_o1.id,
        institution_id=sd_institution_k1.id,
        kind="INTERNSHIP",
        title="E2 (S's Engagement, ACTIVE)",
        status="ACTIVE",
        version=1,
        started_on=now - timedelta(days=35),
        ended_on=now - timedelta(days=1),
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def sd_engagement_e2_evaluated(session, sd_talent_s, sd_organization_o1, sd_institution_k1):
    """Engagement E2: EVALUATED status (for scenario 16, attestation test)."""
    now = datetime.now(timezone.utc)
    engagement = Engagement(
        talent_id=sd_talent_s.id,
        organization_id=sd_organization_o1.id,
        institution_id=sd_institution_k1.id,
        kind="INTERNSHIP",
        title="E2 (S's Engagement, EVALUATED)",
        status="EVALUATED",
        version=1,
        started_on=now - timedelta(days=35),
        ended_on=now - timedelta(days=1),
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def sd_engagement_e3_active(session, sd_organization_o1, sd_institution_k1):
    """Engagement E3: different talent (T3), ACTIVE status (for scenario 21)."""
    # Create T3 user and talent
    user_t3 = User(email="t3.talent@example.com", password_hash="hash_t3")
    session.add(user_t3)
    session.flush()

    talent_t3 = TalentProfile(
        user_id=user_t3.id,
        institution_id=sd_institution_k1.id,
        full_name="User T3 Talent",
        visibility="PRIVATE",
    )
    session.add(talent_t3)
    session.flush()

    now = datetime.now(timezone.utc)
    engagement = Engagement(
        talent_id=talent_t3.id,
        organization_id=sd_organization_o1.id,
        institution_id=sd_institution_k1.id,
        kind="INTERNSHIP",
        title="E3 (T3's Engagement)",
        status="ACTIVE",
        version=1,
        started_on=now - timedelta(days=35),
        ended_on=now - timedelta(days=1),
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def sd_user_org_member_only(session, sd_organization_o1):
    """User M: ORG_MEMBER (not ADMIN) of O1, also has talent profile (for scenario 22)."""
    user = User(email="m.orgmember@example.com", password_hash="hash_m_orgmember")
    session.add(user)
    session.flush()

    # Create talent profile for M
    talent = TalentProfile(
        user_id=user.id,
        institution_id=None,
        full_name="User M Talent",
        visibility="PRIVATE",
    )
    session.add(talent)
    session.flush()

    # Add M as ORG_MEMBER (not ADMIN) of O1
    member = OrganizationMember(
        organization_id=sd_organization_o1.id,
        user_id=user.id,
        role="MEMBER",
    )
    session.add(member)
    session.flush()

    return user


@pytest.fixture
def sd_engagement_e2_member_active(session, sd_user_org_member_only, sd_organization_o1):
    """Engagement E2 for user M (ORG_MEMBER, not ADMIN): ACTIVE status (scenario 22)."""
    now = datetime.now(timezone.utc)
    engagement = Engagement(
        talent_id=None,  # Will set below
        organization_id=sd_organization_o1.id,
        institution_id=None,
        kind="INTERNSHIP",
        title="E2 (Member M's Engagement)",
        status="ACTIVE",
        version=1,
        started_on=now - timedelta(days=35),
        ended_on=now - timedelta(days=1),
    )
    # Set talent_id to M's talent_id
    talent_m = session.query(TalentProfile).filter_by(user_id=sd_user_org_member_only.id).first()
    engagement.talent_id = talent_m.id
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def sd_user_pure_talent(session):
    """User T1: pure talent, no org/institution membership."""
    user = User(email="t1.pure@example.com", password_hash="hash_t1_pure")
    session.add(user)
    session.flush()

    # Create talent profile (standalone, no institution)
    talent = TalentProfile(
        user_id=user.id,
        institution_id=None,
        full_name="User T1 Pure Talent",
        visibility="PRIVATE",
    )
    session.add(talent)
    session.flush()

    return user


@pytest.fixture
def sd_deliverable_e2(session, sd_engagement_e2_active, sd_user_s):
    """Deliverable in E2 (needed for ACTIVE→PENDING_EVALUATION transition)."""
    deliverable = Deliverable(
        engagement_id=sd_engagement_e2_active.id,
        skill_id=None,
        title="E2 Deliverable",
        description="Test deliverable",
        submitted_by_user_id=sd_user_s.id,
        submitted_at=datetime.now(timezone.utc),
    )
    session.add(deliverable)
    session.flush()
    return deliverable


# ============================================================================
# Scenario 16: S attests own E2 (ORG_ADMIN/COORDINATOR) → 409 SELF_ATTESTATION_FORBIDDEN
# ============================================================================


class TestMultiRoleSelfDealingScenario16:
    """
    AC-S1, Scenario 16: S attests own engagement E2 via ORG_ADMIN or COORDINATOR path.

    Expected: 409 SELF_ATTESTATION_FORBIDDEN, no Attestation record created.
    """

    def test_s_attestation_own_e2_evaluated_coordinator_path_409(
        self, client, session, sd_user_s, sd_engagement_e2_evaluated,
        sd_s_membership_coordinator, sd_s_membership_org_admin
    ):
        """
        Scenario 16: S is talent of E2, also COORDINATOR of K1.
        When S tries to attest E2 (as coordinator) → 409 SELF_ATTESTATION_FORBIDDEN.
        """
        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,
        }

        # Before request: verify engagement is EVALUATED
        assert sd_engagement_e2_evaluated.status == "EVALUATED"
        att_count_before = session.query(Attestation).filter_by(
            engagement_id=sd_engagement_e2_evaluated.id
        ).count()

        response = client.post(
            f"/engagements/{sd_engagement_e2_evaluated.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(sd_user_s.id)},
        )

        assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") == "SELF_ATTESTATION_FORBIDDEN", \
            f"Expected SELF_ATTESTATION_FORBIDDEN, got {error_obj.get('code')}"

        # Verify no record created
        session.expire_all()
        att_count_after = session.query(Attestation).filter_by(
            engagement_id=sd_engagement_e2_evaluated.id
        ).count()
        assert att_count_after == att_count_before, "Attestation should not be created"

    def test_s_attestation_own_e2_no_institution_org_admin_path_409(
        self, client, session, sd_user_s, sd_talent_s, sd_organization_o1, sd_s_membership_org_admin
    ):
        """
        Scenario 16 (variant): S is talent of engagement E2 (institution_id=None, only O1),
        also ORG_ADMIN of O1. When S tries to attest E2 via ORG_ADMIN → 409 SELF_ATTESTATION_FORBIDDEN.

        Self-dealing masking applies even when institution_id is NULL (engagement tied only to org).
        """
        # Create engagement for S with institution_id=None, org=O1, status=EVALUATED
        talent_s = session.query(TalentProfile).filter_by(user_id=sd_user_s.id).first()
        now = datetime.now(timezone.utc)
        engagement_no_inst = Engagement(
            talent_id=talent_s.id,
            organization_id=sd_organization_o1.id,
            institution_id=None,  # No institution
            kind="INTERNSHIP",
            title="E2 No Institution (S's Engagement)",
            status="EVALUATED",
            version=1,
            started_on=now - timedelta(days=35),
            ended_on=now - timedelta(days=1),
        )
        session.add(engagement_no_inst)
        session.flush()

        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,
        }

        # Before request
        att_count_before = session.query(Attestation).filter_by(
            engagement_id=engagement_no_inst.id
        ).count()

        response = client.post(
            f"/engagements/{engagement_no_inst.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(sd_user_s.id)},
        )

        assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"

        # Verify no record created
        session.expire_all()
        att_count_after = session.query(Attestation).filter_by(
            engagement_id=engagement_no_inst.id
        ).count()
        assert att_count_after == att_count_before, "Attestation should not be created"


# ============================================================================
# Scenario 17: S evaluates own E2 with ORG_TO_TALENT → 403, no record
# ============================================================================


class TestMultiRoleSelfDealingScenario17:
    """
    AC-S1, Scenario 17: S evaluates own engagement E2 with ORG_TO_TALENT evaluation.

    Expected: 403 TransitionForbidden, no Evaluation record created.
    """

    def test_s_eval_org_to_talent_own_e2_active_403(
        self, client, session, sd_user_s, sd_engagement_e2_active,
        sd_s_membership_org_admin, sd_s_membership_coordinator
    ):
        """
        Scenario 17: S is talent of E2, also ORG_ADMIN of O1.
        When S tries to submit ORG_TO_TALENT evaluation on E2 → 403.
        """
        # Engagement must be PENDING_EVALUATION for evaluation submission
        # First set to PENDING_EVALUATION
        sd_engagement_e2_active.status = "PENDING_EVALUATION"
        session.flush()

        payload = {
            "direction": "ORG_TO_TALENT",
            "items": [
                {"criterion": "COMMUNICATION", "rating": "MEETS", "comment": "Good"}
            ],
        }

        # Before request
        eval_count_before = session.query(Evaluation).filter_by(
            engagement_id=sd_engagement_e2_active.id
        ).count()

        response = client.post(
            f"/engagements/{sd_engagement_e2_active.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(sd_user_s.id)},
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

        # Verify no record created
        session.expire_all()
        eval_count_after = session.query(Evaluation).filter_by(
            engagement_id=sd_engagement_e2_active.id
        ).count()
        assert eval_count_after == eval_count_before, "Evaluation should not be created"


# ============================================================================
# Scenario 18: S transitions own E2 PENDING→ACTIVE/REJECTED (coordinator) → 403, no DB change
# ============================================================================


class TestMultiRoleSelfDealingScenario18:
    """
    AC-S1, Scenario 18: S transitions own engagement E2 from PENDING_APPROVAL to ACTIVE/REJECTED
    as COORDINATOR of K1.

    Expected: 403 TransitionForbidden, status and version unchanged in DB.
    """

    def test_s_transition_pending_to_active_coordinator_403(
        self, client, session, sd_user_s, sd_engagement_e2_pending,
        sd_s_membership_coordinator, sd_s_membership_org_admin
    ):
        """
        Scenario 18a: S tries PENDING_APPROVAL→ACTIVE as coordinator of K1 → 403.
        """
        payload = {
            "to_status": "ACTIVE",
            "version": 1,
        }

        # Before request
        assert sd_engagement_e2_pending.status == "PENDING_APPROVAL"
        version_before = sd_engagement_e2_pending.version

        response = client.post(
            f"/engagements/{sd_engagement_e2_pending.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(sd_user_s.id)},
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

        # Verify DB unchanged
        session.expire_all()
        engagement_after = session.query(Engagement).filter_by(
            id=sd_engagement_e2_pending.id
        ).first()
        assert engagement_after.status == "PENDING_APPROVAL", "Status should not change"
        assert engagement_after.version == version_before, "Version should not change"

    def test_s_transition_pending_to_rejected_coordinator_403(
        self, client, session, sd_user_s, sd_engagement_e2_pending,
        sd_s_membership_coordinator, sd_s_membership_org_admin
    ):
        """
        Scenario 18b: S tries PENDING_APPROVAL→REJECTED as coordinator of K1 → 403.
        """
        payload = {
            "to_status": "REJECTED",
            "version": 1,
            "reason": "Self-dealing rejection test",
        }

        # Before request
        assert sd_engagement_e2_pending.status == "PENDING_APPROVAL"
        version_before = sd_engagement_e2_pending.version

        response = client.post(
            f"/engagements/{sd_engagement_e2_pending.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(sd_user_s.id)},
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

        # Verify DB unchanged
        session.expire_all()
        engagement_after = session.query(Engagement).filter_by(
            id=sd_engagement_e2_pending.id
        ).first()
        assert engagement_after.status == "PENDING_APPROVAL", "Status should not change"
        assert engagement_after.version == version_before, "Version should not change"


# ============================================================================
# Scenario 19: S transitions own E2 ACTIVE→CANCELLED/PENDING_EVAL, posts task → 403, no DB change
# ============================================================================


class TestMultiRoleSelfDealingScenario19:
    """
    AC-S1, Scenario 19: S transitions own engagement E2 from ACTIVE to CANCELLED or PENDING_EVALUATION,
    or creates a task, as ORG_ADMIN of O1.

    Expected: 403 TransitionForbidden/TransitionForbiddenError, DB unchanged.
    """

    def test_s_transition_active_to_cancelled_org_admin_403(
        self, client, session, sd_user_s, sd_engagement_e2_active,
        sd_s_membership_org_admin, sd_s_membership_coordinator
    ):
        """
        Scenario 19a: S tries ACTIVE→CANCELLED as ORG_ADMIN of O1 → 403.
        """
        payload = {
            "to_status": "CANCELLED",
            "version": 1,
            "reason": "Self-dealing cancellation test",
        }

        # Before request
        assert sd_engagement_e2_active.status == "ACTIVE"
        version_before = sd_engagement_e2_active.version

        response = client.post(
            f"/engagements/{sd_engagement_e2_active.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(sd_user_s.id)},
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

        # Verify DB unchanged
        session.expire_all()
        engagement_after = session.query(Engagement).filter_by(
            id=sd_engagement_e2_active.id
        ).first()
        assert engagement_after.status == "ACTIVE", "Status should not change"
        assert engagement_after.version == version_before, "Version should not change"

    def test_s_transition_active_to_pending_evaluation_org_admin_403(
        self, client, session, sd_user_s, sd_engagement_e2_active,
        sd_deliverable_e2, sd_s_membership_org_admin, sd_s_membership_coordinator
    ):
        """
        Scenario 19b: S tries ACTIVE→PENDING_EVALUATION as ORG_ADMIN of O1 → 403.
        """
        payload = {
            "to_status": "PENDING_EVALUATION",
            "version": 1,
        }

        # Before request
        assert sd_engagement_e2_active.status == "ACTIVE"
        version_before = sd_engagement_e2_active.version

        response = client.post(
            f"/engagements/{sd_engagement_e2_active.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(sd_user_s.id)},
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

        # Verify DB unchanged
        session.expire_all()
        engagement_after = session.query(Engagement).filter_by(
            id=sd_engagement_e2_active.id
        ).first()
        assert engagement_after.status == "ACTIVE", "Status should not change"
        assert engagement_after.version == version_before, "Version should not change"

    def test_s_create_task_on_own_e2_active_403(
        self, client, session, sd_user_s, sd_engagement_e2_active,
        sd_s_membership_org_admin, sd_s_membership_coordinator
    ):
        """
        Scenario 19c: S tries to create a task on own E2 as ORG_ADMIN → 403.
        """
        payload = {
            "title": "Self-dealing task",
            "description": "Test task creation",
        }

        # Before request
        task_count_before = session.query(EngagementTask).filter_by(
            engagement_id=sd_engagement_e2_active.id
        ).count()

        response = client.post(
            f"/engagements/{sd_engagement_e2_active.id}/tasks",
            json=payload,
            headers={"X-Debug-User-Id": str(sd_user_s.id)},
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

        # Verify no task created
        session.expire_all()
        task_count_after = session.query(EngagementTask).filter_by(
            engagement_id=sd_engagement_e2_active.id
        ).count()
        assert task_count_after == task_count_before, "Task should not be created"


# ============================================================================
# Scenario 20: S performs talent-side actions on own E2 → 2xx (DRAFT→PENDING, deliverable, TALENT_TO_ORG eval)
# ============================================================================


class TestMultiRoleSelfDealingScenario20:
    """
    AC-S1, Scenario 20: S performs talent-side actions on own engagement E2.
    These should succeed (is_subject role, no masking for talent actions).

    Expected: 2xx success for:
    - DRAFT→PENDING_APPROVAL
    - Deliverable submission
    - TALENT_TO_ORG evaluation
    """

    def test_s_transition_draft_to_pending_approval_talent_side_2xx(
        self, client, session, sd_user_s, sd_engagement_e2_draft,
        sd_s_membership_org_admin, sd_s_membership_coordinator
    ):
        """
        Scenario 20a: S (as talent) transitions own E2 DRAFT→PENDING_APPROVAL → 2xx.
        """
        payload = {
            "to_status": "PENDING_APPROVAL",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{sd_engagement_e2_draft.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(sd_user_s.id)},
        )

        assert response.status_code == 200, f"Expected 2xx, got {response.status_code}: {response.text}"

        # Verify status changed
        session.expire_all()
        engagement_after = session.query(Engagement).filter_by(
            id=sd_engagement_e2_draft.id
        ).first()
        assert engagement_after.status == "PENDING_APPROVAL", "Status should change to PENDING_APPROVAL"

    def test_s_submit_deliverable_talent_side_2xx(
        self, client, session, sd_user_s, sd_engagement_e2_active,
        sd_s_membership_org_admin, sd_s_membership_coordinator
    ):
        """
        Scenario 20b: S (as talent) submits deliverable on own E2 → 2xx.
        """
        payload = {
            "title": "Talent-side deliverable",
            "description": "Test deliverable submission",
        }

        # Before request
        deliverable_count_before = session.query(Deliverable).filter_by(
            engagement_id=sd_engagement_e2_active.id
        ).count()

        response = client.post(
            f"/engagements/{sd_engagement_e2_active.id}/deliverables",
            json=payload,
            headers={"X-Debug-User-Id": str(sd_user_s.id)},
        )

        assert response.status_code == 201, f"Expected 2xx, got {response.status_code}: {response.text}"

        # Verify deliverable created
        session.expire_all()
        deliverable_count_after = session.query(Deliverable).filter_by(
            engagement_id=sd_engagement_e2_active.id
        ).count()
        assert deliverable_count_after == deliverable_count_before + 1, "Deliverable should be created"

    def test_s_eval_talent_to_org_talent_side_2xx(
        self, client, session, sd_user_s, sd_engagement_e2_active,
        sd_s_membership_org_admin, sd_s_membership_coordinator
    ):
        """
        Scenario 20c: S (as talent) submits TALENT_TO_ORG evaluation on own E2 → 2xx.

        Engagement must be in PENDING_EVALUATION status first.
        """
        # First set to PENDING_EVALUATION (requires deliverable precondition)
        sd_engagement_e2_active.status = "PENDING_EVALUATION"
        session.flush()

        payload = {
            "direction": "TALENT_TO_ORG",
            "items": [
                {"criterion": "COMMUNICATION", "rating": "MEETS", "comment": "Good"}
            ],
        }

        # Before request
        eval_count_before = session.query(Evaluation).filter_by(
            engagement_id=sd_engagement_e2_active.id
        ).count()

        response = client.post(
            f"/engagements/{sd_engagement_e2_active.id}/evaluation",
            json=payload,
            headers={"X-Debug-User-Id": str(sd_user_s.id)},
        )

        assert response.status_code == 201, f"Expected 2xx, got {response.status_code}: {response.text}"

        # Verify evaluation created
        session.expire_all()
        eval_count_after = session.query(Evaluation).filter_by(
            engagement_id=sd_engagement_e2_active.id
        ).count()
        assert eval_count_after == eval_count_before + 1, "Evaluation should be created"


# ============================================================================
# Scenario 21: S performs org/coordinator actions on E3 (different talent, O1/K1 scope) → 2xx
# ============================================================================


class TestMultiRoleSelfDealingScenario21:
    """
    AC-S1, Scenario 21: S performs org/coordinator actions on E3 (another talent's engagement,
    but within O1/K1 scope). Self-dealing mask applies only to own engagement.

    Expected: 2xx success for:
    - PENDING_APPROVAL→ACTIVE (as coordinator)
    - Task creation (as ORG_ADMIN)
    - ORG_TO_TALENT evaluation (as ORG_ADMIN)
    - Attestation (as coordinator, when E3 is EVALUATED)
    """

    def test_s_transition_e3_pending_to_active_coordinator_2xx(
        self, client, session, sd_user_s, sd_engagement_e3_active,
        sd_s_membership_coordinator, sd_s_membership_org_admin
    ):
        """
        Scenario 21a: S (as COORDINATOR of K1) transitions E3 (different talent) PENDING→ACTIVE → 2xx.

        First, create E3 in PENDING_APPROVAL status.
        """
        # Create E3 in PENDING_APPROVAL status for this test
        user_t3 = session.query(User).filter(User.email == "t3.talent@example.com").first()
        talent_t3 = session.query(TalentProfile).filter_by(user_id=user_t3.id).first()

        now = datetime.now(timezone.utc)
        e3_pending = Engagement(
            talent_id=talent_t3.id,
            organization_id=sd_engagement_e3_active.organization_id,
            institution_id=sd_engagement_e3_active.institution_id,
            kind="INTERNSHIP",
            title="E3 Pending",
            status="PENDING_APPROVAL",
            version=1,
            started_on=now - timedelta(days=35),
            ended_on=now - timedelta(days=1),
        )
        session.add(e3_pending)
        session.flush()

        payload = {
            "to_status": "ACTIVE",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{e3_pending.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(sd_user_s.id)},
        )

        assert response.status_code == 200, f"Expected 2xx, got {response.status_code}: {response.text}"

        # Verify status changed
        session.expire_all()
        engagement_after = session.query(Engagement).filter_by(id=e3_pending.id).first()
        assert engagement_after.status == "ACTIVE", "Status should change to ACTIVE"

    def test_s_create_task_on_e3_org_admin_2xx(
        self, client, session, sd_user_s, sd_engagement_e3_active,
        sd_s_membership_org_admin, sd_s_membership_coordinator
    ):
        """
        Scenario 21b: S (as ORG_ADMIN of O1) creates task on E3 → 2xx.
        """
        payload = {
            "title": "Task for E3 (different talent)",
            "description": "Org-admin task creation",
        }

        # Before request
        task_count_before = session.query(EngagementTask).filter_by(
            engagement_id=sd_engagement_e3_active.id
        ).count()

        response = client.post(
            f"/engagements/{sd_engagement_e3_active.id}/tasks",
            json=payload,
            headers={"X-Debug-User-Id": str(sd_user_s.id)},
        )

        assert response.status_code == 201, f"Expected 2xx, got {response.status_code}: {response.text}"

        # Verify task created
        session.expire_all()
        task_count_after = session.query(EngagementTask).filter_by(
            engagement_id=sd_engagement_e3_active.id
        ).count()
        assert task_count_after == task_count_before + 1, "Task should be created"


# ============================================================================
# Scenario 22: S org MEMBER (not ADMIN) of own engagement: task/PENDING_EVAL → 403, no DB change
# ============================================================================


class TestMultiRoleSelfDealingScenario22:
    """
    AC-S1, Scenario 22: User M (ORG_MEMBER, not ADMIN) of O1, is talent of E2.
    M tries to create task or transition to PENDING_EVALUATION on own E2 → 403.

    Expected: 403 TransitionForbidden for both task creation and PENDING_EVALUATION transition.
    """

    def test_m_create_task_member_not_admin_403(
        self, client, session, sd_user_org_member_only, sd_engagement_e2_member_active
    ):
        """
        Scenario 22a: M (ORG_MEMBER, not ADMIN) tries to create task on own E2 → 403.
        """
        payload = {
            "title": "Member task (should fail)",
            "description": "ORG_MEMBER attempting task creation",
        }

        # Before request
        task_count_before = session.query(EngagementTask).filter_by(
            engagement_id=sd_engagement_e2_member_active.id
        ).count()

        response = client.post(
            f"/engagements/{sd_engagement_e2_member_active.id}/tasks",
            json=payload,
            headers={"X-Debug-User-Id": str(sd_user_org_member_only.id)},
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

        # Verify no task created
        session.expire_all()
        task_count_after = session.query(EngagementTask).filter_by(
            engagement_id=sd_engagement_e2_member_active.id
        ).count()
        assert task_count_after == task_count_before, "Task should not be created"

    def test_m_transition_active_to_pending_evaluation_member_not_admin_403(
        self, client, session, sd_user_org_member_only, sd_engagement_e2_member_active
    ):
        """
        Scenario 22b: M (ORG_MEMBER, not ADMIN) tries ACTIVE→PENDING_EVALUATION on own E2 → 403.
        """
        # Add a deliverable first (precondition for PENDING_EVALUATION)
        deliverable = Deliverable(
            engagement_id=sd_engagement_e2_member_active.id,
            skill_id=None,
            title="Member deliverable",
            description="Test deliverable",
            submitted_by_user_id=sd_user_org_member_only.id,
            submitted_at=datetime.now(timezone.utc),
        )
        session.add(deliverable)
        session.flush()

        payload = {
            "to_status": "PENDING_EVALUATION",
            "version": 1,
        }

        # Before request
        version_before = sd_engagement_e2_member_active.version

        response = client.post(
            f"/engagements/{sd_engagement_e2_member_active.id}/transitions",
            json=payload,
            headers={"X-Debug-User-Id": str(sd_user_org_member_only.id)},
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

        # Verify DB unchanged
        session.expire_all()
        engagement_after = session.query(Engagement).filter_by(
            id=sd_engagement_e2_member_active.id
        ).first()
        assert engagement_after.status == "ACTIVE", "Status should not change"
        assert engagement_after.version == version_before, "Version should not change"


# ============================================================================
# Scenario 23: S creates engagement with own talent_id → 2xx
# ============================================================================


class TestMultiRoleSelfDealingScenario23:
    """
    AC-S1, Scenario 23: S creates an engagement with talent_id=own talent_id.

    Expected: 2xx success (201 CREATED).
    """

    def test_s_create_engagement_own_talent_201(
        self, client, session, sd_user_s, sd_talent_s, sd_talent_s_with_k1, sd_organization_o1,
        sd_institution_k1, sd_s_membership_org_admin, sd_s_membership_coordinator
    ):
        """
        Scenario 23: S (talent) creates engagement for own talent_id → 2xx.

        S's talent profile has institution_id=K1, so payload does not need institution_id
        (or can omit it). This avoids INSTITUTION_MISMATCH error.
        """
        payload = {
            "talent_id": str(sd_talent_s_with_k1.id),
            "organization_id": str(sd_organization_o1.id),
            "kind": "PART_TIME",
            "title": "S's self-created engagement",
        }

        response = client.post(
            "/engagements",
            json=payload,
            headers={"X-Debug-User-Id": str(sd_user_s.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        # Verify engagement created
        session.expire_all()
        engagement = session.query(Engagement).filter_by(
            talent_id=sd_talent_s_with_k1.id,
            organization_id=sd_organization_o1.id,
        ).order_by(Engagement.created_at.desc()).first()

        assert engagement is not None, "Engagement should be created"
        assert engagement.status == "DRAFT", "Initial status should be DRAFT"


# ============================================================================
# Scenario 24: Pure talent T1 (no org/institution membership) attests own engagement → 403, no record
# ============================================================================


class TestMultiRoleSelfDealingScenario24:
    """
    AC-S1, Scenario 24: Pure talent T1 (no org/institution membership, only talent profile)
    tries to attest their own engagement (shared with O1/K1 org/institution).

    Per AC-S1 (mevcut sözleşme, test_attestation_authorization.py): talent cannot submit attestations
    in any scenario (TransitionForbiddenError "Talent cannot submit attestations").

    Expected: 403 TransitionForbiddenError, no Attestation record created.
    """

    def test_pure_talent_attests_own_engagement_403(
        self, client, session, sd_user_pure_talent, sd_organization_o1, sd_institution_k1
    ):
        """
        Scenario 24: T1 (pure talent, yalnız talent profili, org/kurum üyesi DEĞİL)
        kendi EVALUATED engagement'ını (org O1, kurum K1'li) attest eder → 403 TransitionForbiddenError.

        Attestation satırı oluşmaz, DB değişmez.
        """
        # Create T1's talent profile (already done by fixture)
        talent_t1 = session.query(TalentProfile).filter_by(
            user_id=sd_user_pure_talent.id
        ).first()
        assert talent_t1 is not None

        # Create engagement for T1 with O1 and K1 (T1 is talent, O1/K1 provide scope)
        now = datetime.now(timezone.utc)
        engagement_t1 = Engagement(
            talent_id=talent_t1.id,
            organization_id=sd_organization_o1.id,
            institution_id=sd_institution_k1.id,
            kind="INTERNSHIP",
            title="T1 Pure Talent Engagement",
            status="EVALUATED",
            version=1,
            started_on=now - timedelta(days=30),
            ended_on=now - timedelta(days=1),
        )
        session.add(engagement_t1)
        session.flush()

        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,
        }

        # Before request
        att_count_before = session.query(Attestation).filter_by(
            engagement_id=engagement_t1.id
        ).count()

        response = client.post(
            f"/engagements/{engagement_t1.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(sd_user_pure_talent.id)},
        )

        assert response.status_code == 403, f"Expected 403 (talent cannot attest), got {response.status_code}: {response.text}"

        # Verify no record created
        session.expire_all()
        att_count_after = session.query(Attestation).filter_by(
            engagement_id=engagement_t1.id
        ).count()
        assert att_count_after == att_count_before, "Attestation should not be created"

    def test_pure_talent_outside_scope_attestation_404(
        self, client, session, sd_user_pure_talent, sd_engagement_e2_evaluated,
        sd_s_membership_org_admin, sd_s_membership_coordinator
    ):
        """
        Scenario 24 (variant): T1 (pure talent) tries to attest engagement outside scope
        (E2: different talent, O1/K1 org/institution).

        T1 is not in E2's scope (different talent, T1 not org/institution member),
        so scoped_engagements() returns empty (tenant isolation per AC-S2/AC-7).
        Expected: 404 NOT_FOUND.
        """
        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,
        }

        # Before request
        att_count_before = session.query(Attestation).filter_by(
            engagement_id=sd_engagement_e2_evaluated.id
        ).count()

        response = client.post(
            f"/engagements/{sd_engagement_e2_evaluated.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(sd_user_pure_talent.id)},
        )

        assert response.status_code == 404, f"Expected 404 (tenant isolation), got {response.status_code}: {response.text}"

        # Verify no record created
        session.expire_all()
        att_count_after = session.query(Attestation).filter_by(
            engagement_id=sd_engagement_e2_evaluated.id
        ).count()
        assert att_count_after == att_count_before, "Attestation should not be created"
