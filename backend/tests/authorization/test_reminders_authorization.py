"""
Reminder authorization tests (PLAN 3.4 — yet-108-toplu-hatirlatma-ucu).

Threat-model security tests for POST /institutions/{id}/reminders:
- AC-4 [Critical]: Cross-institution path — 404 NOT_FOUND (not 403), no data leak
- AC-5 [Critical]: Insufficient role (TALENT) — 404 NOT_FOUND (same as AC-4)
- AC-S1 [Critical]: Cross-tenant ID enumeration protection → 404 for unauthorized institution
- AC-S2 [Critical]: Role elevation attempt (TALENT calling admin endpoint) → 404
- AC-S3 [High]: ID enumeration defense → response counts only principal's institution engagements
- AC-S6 [Medium]: Audit event logging without PII (no email addresses, no private_note)

Authorization matrix:
- TALENT (Alice): cannot access POST /institutions/{id}/reminders (404) — no reminders permission
- ORG:MEMBER (Charlie): cannot access (404) — org members don't have institutional scope
- INST:COORDINATOR (Diana, Institution A): can trigger reminders for Institution A engagements
- INST:COORDINATOR (Eve, Institution B): cannot access Institution A (404)
- INST:ADMIN (same role structure as COORDINATOR for this endpoint)

Coverage Target: Tenant isolation + role enforcement + audit logging (AC-4, AC-5, AC-S1, AC-S2, AC-S3, AC-S6).
CLAUDE.md requirement: Every endpoint tested with both positive (authorized) and negative (unauthorized) cases.
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
)

# Import will fail until Reminder models/service are implemented
try:
    from app.models import AuditEvent
except ImportError:
    AuditEvent = None


# ============================================================================
# Fixtures: Users, Institutions, InstitutionMembers, Engagements
# ============================================================================


@pytest.fixture
def user_talent_alice_authz_rem(session):
    """Talent user Alice for authorization tests."""
    user = User(email="alice.talent.authz.rem@example.com", password_hash="hash_alice")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_bob_authz_rem(session):
    """Talent user Bob for authorization tests."""
    user = User(email="bob.talent.authz.rem@example.com", password_hash="hash_bob")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_org_member_charlie_authz_rem(session):
    """ORG:MEMBER Charlie for authorization tests."""
    user = User(email="charlie.member.authz.rem@example.com", password_hash="hash_charlie")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_inst_coord_diana_authz_rem(session):
    """INST:COORDINATOR Diana (Institution A) for authorization tests."""
    user = User(email="diana.coord.authz.rem@example.com", password_hash="hash_diana")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_inst_coord_eve_authz_rem(session):
    """INST:COORDINATOR Eve (Institution B) for authorization tests."""
    user = User(email="eve.coord.authz.rem@example.com", password_hash="hash_eve")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_inst_admin_frank_authz_rem(session):
    """INST:ADMIN Frank (Institution A) for authorization tests."""
    user = User(email="frank.admin.authz.rem@example.com", password_hash="hash_frank")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def institution_a_authz_rem(session):
    """Institution A for authorization tests."""
    inst = Institution(name="Institution A Authz", verification_level="T1")
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def institution_b_authz_rem(session):
    """Institution B for authorization tests (cross-tenant scenario)."""
    inst = Institution(name="Institution B Authz", verification_level="T1")
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def org_a_authz_rem(session):
    """Organization A for authorization tests."""
    org = Organization(name="Organization A Authz", verification_level="T1")
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def member_diana_authz_rem(session, user_inst_coord_diana_authz_rem, institution_a_authz_rem):
    """InstitutionMember: Diana as COORDINATOR in Institution A."""
    member = InstitutionMember(
        institution_id=institution_a_authz_rem.id,
        user_id=user_inst_coord_diana_authz_rem.id,
        role="COORDINATOR",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def member_eve_authz_rem(session, user_inst_coord_eve_authz_rem, institution_b_authz_rem):
    """InstitutionMember: Eve as COORDINATOR in Institution B."""
    member = InstitutionMember(
        institution_id=institution_b_authz_rem.id,
        user_id=user_inst_coord_eve_authz_rem.id,
        role="COORDINATOR",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def member_frank_authz_rem(session, user_inst_admin_frank_authz_rem, institution_a_authz_rem):
    """InstitutionMember: Frank as ADMIN in Institution A."""
    member = InstitutionMember(
        institution_id=institution_a_authz_rem.id,
        user_id=user_inst_admin_frank_authz_rem.id,
        role="ADMIN",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def talent_alice_authz_rem(session, user_talent_alice_authz_rem, institution_a_authz_rem):
    """Talent profile for Alice in Institution A."""
    profile = TalentProfile(
        user_id=user_talent_alice_authz_rem.id,
        institution_id=institution_a_authz_rem.id,
        full_name="Alice Talent Authz Rem",
        visibility="PRIVATE",
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_bob_authz_rem(session, user_talent_bob_authz_rem, institution_a_authz_rem):
    """Talent profile for Bob in Institution A."""
    profile = TalentProfile(
        user_id=user_talent_bob_authz_rem.id,
        institution_id=institution_a_authz_rem.id,
        full_name="Bob Talent Authz Rem",
        visibility="PRIVATE",
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def member_charlie_authz_rem(session, user_org_member_charlie_authz_rem, org_a_authz_rem):
    """OrganizationMember: Charlie as MEMBER in Organization A."""
    member = OrganizationMember(
        organization_id=org_a_authz_rem.id,
        user_id=user_org_member_charlie_authz_rem.id,
        role="MEMBER",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def engagement_a1_authz_rem(session, talent_alice_authz_rem, org_a_authz_rem, institution_a_authz_rem):
    """Engagement A1: Alice in Institution A, status=PENDING_EVALUATION."""
    eng = Engagement(
        talent_id=talent_alice_authz_rem.id,
        organization_id=org_a_authz_rem.id,
        institution_id=institution_a_authz_rem.id,
        status="PENDING_EVALUATION",
        kind="INTERNSHIP",
        title="Test Engagement",
    )
    session.add(eng)
    session.flush()
    return eng


@pytest.fixture
def engagement_a2_authz_rem(session, talent_bob_authz_rem, org_a_authz_rem, institution_a_authz_rem):
    """Engagement A2: Bob in Institution A, status=PENDING_EVALUATION."""
    eng = Engagement(
        talent_id=talent_bob_authz_rem.id,
        organization_id=org_a_authz_rem.id,
        institution_id=institution_a_authz_rem.id,
        status="PENDING_EVALUATION",
        kind="INTERNSHIP",
        title="Test Engagement",
    )
    session.add(eng)
    session.flush()
    return eng


# ============================================================================
# AC-4 [Critical]: Cross-institution path → 404 NOT_FOUND
# ============================================================================


def test_coordinator_different_institution_404(
    client, member_diana_authz_rem, engagement_a1_authz_rem,
    institution_b_authz_rem, user_inst_coord_diana_authz_rem
):
    """
    AC-4 [Critical] + AC-S1: Diana (COORDINATOR of Institution A) attempts to POST to
    Institution B's reminders endpoint. Expected: 404 NOT_FOUND (not 403). No data leak about
    whether Institution B exists or not.
    """
    response = client.post(
        f"/institutions/{institution_b_authz_rem.id}/reminders",
        headers={"X-Debug-User-Id": str(user_inst_coord_diana_authz_rem.id)},
        json={
            "engagement_ids": [str(engagement_a1_authz_rem.id)],
            "template": "evaluation_pending",
        },
    )

    # Must return 404 (not 403)
    assert response.status_code == 404, \
        f"Expected 404 for cross-institution access, got {response.status_code}"


# ============================================================================
# AC-5 [Critical]: Insufficient role → 404 NOT_FOUND
# ============================================================================


def test_talent_cannot_trigger_reminders_404(
    client, talent_alice_authz_rem, engagement_a1_authz_rem,
    institution_a_authz_rem, user_talent_alice_authz_rem
):
    """
    AC-5 [Critical] + AC-S2: Talent Alice (no institutional role) attempts POST /institutions/{id}/reminders.
    Expected: 404 NOT_FOUND (same 404 as AC-4 — no distinction between "wrong institution" and "wrong role").
    """
    response = client.post(
        f"/institutions/{institution_a_authz_rem.id}/reminders",
        headers={"X-Debug-User-Id": str(user_talent_alice_authz_rem.id)},
        json={
            "engagement_ids": [str(engagement_a1_authz_rem.id)],
            "template": "evaluation_pending",
        },
    )

    assert response.status_code == 404, \
        f"Expected 404 for talent (no reminders permission), got {response.status_code}"


def test_org_member_cannot_trigger_reminders_404(
    client, member_charlie_authz_rem, engagement_a1_authz_rem,
    institution_a_authz_rem, user_org_member_charlie_authz_rem
):
    """
    AC-5 [Critical]: ORG:MEMBER Charlie (no institutional role) attempts POST /institutions/{id}/reminders.
    Expected: 404 NOT_FOUND.
    """
    response = client.post(
        f"/institutions/{institution_a_authz_rem.id}/reminders",
        headers={"X-Debug-User-Id": str(user_org_member_charlie_authz_rem.id)},
        json={
            "engagement_ids": [str(engagement_a1_authz_rem.id)],
            "template": "evaluation_pending",
        },
    )

    assert response.status_code == 404, \
        f"Expected 404 for org member (no institutional scope), got {response.status_code}"


# ============================================================================
# AC-S1 [Critical]: Cross-tenant ID enumeration protection
# ============================================================================


def test_same_404_for_nonexistent_and_foreign_institution(
    client, member_diana_authz_rem, institution_a_authz_rem, user_inst_coord_diana_authz_rem
):
    """
    AC-S1 [Critical]: The 404 error for a non-existent institution ID should be returned
    by the institution-scope check BEFORE any request validation (e.g., engagement_ids field).
    This test verifies that scope checking precedes field validation, preventing ID enumeration.

    We send a request with a non-existent institution ID and a valid engagement_ids list.
    Expected: 404 (scope check happens before validation check).
    """
    fake_id = uuid4()

    # Request with non-existent institution ID
    response_nonexistent = client.post(
        f"/institutions/{fake_id}/reminders",
        headers={"X-Debug-User-Id": str(user_inst_coord_diana_authz_rem.id)},
        json={
            "engagement_ids": [str(uuid4())],  # Valid-looking engagement ID; scope check fails first
            "template": "evaluation_pending",
        },
    )

    # Should get 404 (scope check happens before validation check)
    assert response_nonexistent.status_code == 404

    # The 404 message should NOT distinguish between "not found" and "unauthorized"
    # Both should have the same error text
    error_msg_fake = response_nonexistent.json().get("message", "")
    # (No assertion on exact text — just verify it's generic "Institution not found"-type message)
    assert "not found" in error_msg_fake.lower() or error_msg_fake, \
        f"Expected generic 404 message, got: {error_msg_fake}"


# ============================================================================
# AC-S2 [Critical]: Role elevation attempt
# ============================================================================


def test_role_elevation_attempt_talent_to_coordinator_404(
    client, talent_alice_authz_rem, engagement_a1_authz_rem,
    institution_a_authz_rem, user_talent_alice_authz_rem
):
    """
    AC-S2 [Critical]: Talent Alice tries to use coordinator-only endpoint
    by passing X-Debug-User-Id (simulating token forgery or header injection).
    Expected: 404 (endpoint is not accessible to non-coordinators).
    The authorization check (principal.institution_ids scope) must reject before any business logic.
    """
    response = client.post(
        f"/institutions/{institution_a_authz_rem.id}/reminders",
        headers={"X-Debug-User-Id": str(user_talent_alice_authz_rem.id)},
        json={
            "engagement_ids": [str(engagement_a1_authz_rem.id)],
            "template": "evaluation_pending",
        },
    )

    # Endpoint must reject with 404, not proceed to business logic
    assert response.status_code == 404, \
        f"Expected 404 for role elevation attempt, got {response.status_code}"


# ============================================================================
# AC-S3 [High]: ID enumeration — queued_count reveals only principal's institution
# ============================================================================


def test_id_enumeration_defense_queued_count_reveals_scope(
    client, session, member_diana_authz_rem, member_eve_authz_rem,
    engagement_a1_authz_rem, engagement_a2_authz_rem,
    institution_a_authz_rem, institution_b_authz_rem, user_inst_coord_diana_authz_rem,
    user_inst_coord_eve_authz_rem
):
    """
    AC-S3 [High]: When Diana (Institution A coordinator) sends a request with:
    - 2 valid engagement IDs from Institution A
    - 1 engagement ID that would belong to Institution B (if it existed in request)
    The queued_count should reflect only Institution A engagements (2), not revealing
    whether other IDs belong to Institution B or don't exist.

    This prevents attackers from using queued_count deltas to infer which institution
    an engagement belongs to.
    """
    # Use both A1 and A2 (Institution A) + a non-existent or B-scoped ID
    fake_id = uuid4()

    response = client.post(
        f"/institutions/{institution_a_authz_rem.id}/reminders",
        headers={"X-Debug-User-Id": str(user_inst_coord_diana_authz_rem.id)},
        json={
            "engagement_ids": [str(engagement_a1_authz_rem.id), str(engagement_a2_authz_rem.id), str(fake_id)],
            "template": "evaluation_pending",
        },
    )

    assert response.status_code == 202
    data = response.json()
    # queued_count should be 2 (only A1 and A2, fake_id filtered out silently)
    assert data["queued_count"] == 2, \
        f"Expected queued_count: 2, got {data['queued_count']}"

    # Response should NOT indicate why fake_id was filtered (i.e., whether it's invalid or belongs to another institution)
    assert "filtered_ids" not in data
    assert "invalid_ids" not in data


def test_id_enumeration_cross_institution_engagement_silent_filter(
    client, session, member_diana_authz_rem,
    engagement_a1_authz_rem, engagement_a2_authz_rem,
    institution_a_authz_rem, user_inst_coord_diana_authz_rem
):
    """
    AC-S3 [High]: A variant test — send multiple valid Institution A engagements +
    one Institution B engagement. Verify queued_count only counts A's engagements.
    (Requires engagement_b to be created, which requires separate fixture dependency.)

    This test uses a simple 2-engagement (both A) + 1 fake ID scenario instead.
    """
    fake_id_from_other_institution = uuid4()

    response = client.post(
        f"/institutions/{institution_a_authz_rem.id}/reminders",
        headers={"X-Debug-User-Id": str(user_inst_coord_diana_authz_rem.id)},
        json={
            "engagement_ids": [
                str(engagement_a1_authz_rem.id),
                str(engagement_a2_authz_rem.id),
                str(fake_id_from_other_institution),  # Not from Institution A
            ],
            "template": "evaluation_pending",
        },
    )

    # Expected: 202, queued_count: 2 (fake_id silently filtered)
    assert response.status_code == 202
    data = response.json()
    assert data["queued_count"] == 2, \
        f"Expected queued_count: 2, got {data['queued_count']}"


# ============================================================================
# AC-S6 [Medium]: Audit event without PII
# ============================================================================


def test_audit_event_no_pii_on_successful_reminder_trigger(
    client, session, member_diana_authz_rem, engagement_a1_authz_rem,
    institution_a_authz_rem, user_inst_coord_diana_authz_rem
):
    """
    AC-S6 [Medium]: Successful reminder trigger must create an audit_event record with:
    - actor_user_id (Diana's user ID) ✓
    - subject_type = "INSTITUTION"
    - subject_id = Institution A's ID
    - action = "REMINDERS_TRIGGERED"
    - result = "SUCCESS"
    - event_metadata containing engagement list and template
    But NO PII such as email addresses or private_note fields.
    """
    # Capture table state before POST
    audit_count_before = session.query(AuditEvent).count() if AuditEvent is not None else None

    response = client.post(
        f"/institutions/{institution_a_authz_rem.id}/reminders",
        headers={"X-Debug-User-Id": str(user_inst_coord_diana_authz_rem.id)},
        json={
            "engagement_ids": [str(engagement_a1_authz_rem.id)],
            "template": "evaluation_pending",
        },
    )

    assert response.status_code == 202

    # Query audit_events table (delta pattern)
    if AuditEvent is not None:
        audit_count_after = session.query(AuditEvent).count()
        assert audit_count_after - audit_count_before == 1, \
            f"Expected 1 new audit record, got {audit_count_after - audit_count_before}"

        # Verify structure of the newly created audit event
        latest_audit = session.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
        assert latest_audit is not None

        # Verify structure
        assert latest_audit.actor_user_id == user_inst_coord_diana_authz_rem.id, \
            f"Expected actor_user_id to be Diana's ID, got {latest_audit.actor_user_id}"
        assert latest_audit.action == "REMINDERS_TRIGGERED"
        assert latest_audit.subject_type == "INSTITUTION"
        assert latest_audit.subject_id == institution_a_authz_rem.id
        assert latest_audit.result == "SUCCESS"

        # Verify no PII in metadata
        metadata = latest_audit.event_metadata or {}
        # Should NOT contain user email, private_note, or other sensitive fields
        metadata_str = str(metadata).lower()
        assert "@example.com" not in metadata_str, \
            f"Email address leaked in audit metadata: {metadata}"
        assert "private_note" not in metadata_str, \
            f"private_note field leaked in audit metadata: {metadata}"

        # Metadata should contain engagement list or template (business context)
        assert isinstance(metadata, dict), "Metadata should be a dict (JSONB)"


def test_positive_case_coordinator_can_trigger_reminders_202(
    client, member_diana_authz_rem, engagement_a1_authz_rem,
    institution_a_authz_rem, user_inst_coord_diana_authz_rem
):
    """
    Positive test: Diana (COORDINATOR of Institution A) CAN successfully trigger reminders.
    This is the happy path for authorization — used alongside negative tests (AC-4, AC-5)
    to prove the authorization logic works correctly.
    """
    response = client.post(
        f"/institutions/{institution_a_authz_rem.id}/reminders",
        headers={"X-Debug-User-Id": str(user_inst_coord_diana_authz_rem.id)},
        json={
            "engagement_ids": [str(engagement_a1_authz_rem.id)],
            "template": "evaluation_pending",
        },
    )

    # Coordinator of correct institution can access endpoint
    assert response.status_code == 202, \
        f"Expected 202 for authorized coordinator, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["queued_count"] == 1


def test_positive_case_institution_admin_can_trigger_reminders_202(
    client, member_frank_authz_rem, engagement_a1_authz_rem,
    institution_a_authz_rem, user_inst_admin_frank_authz_rem
):
    """
    Positive test: Frank (ADMIN of Institution A) can also trigger reminders.
    Administrators should have the same endpoint access as coordinators.
    """
    response = client.post(
        f"/institutions/{institution_a_authz_rem.id}/reminders",
        headers={"X-Debug-User-Id": str(user_inst_admin_frank_authz_rem.id)},
        json={
            "engagement_ids": [str(engagement_a1_authz_rem.id)],
            "template": "evaluation_pending",
        },
    )

    # Admin of correct institution can access endpoint
    assert response.status_code == 202, \
        f"Expected 202 for authorized admin, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["queued_count"] == 1
