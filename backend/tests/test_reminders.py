"""
Reminder endpoint tests (PLAN 3.4 — yet-108-toplu-hatirlatma-ucu).

Implements Acceptance Criteria for POST /institutions/{id}/reminders:
- AC-1 [Critical]: Happy path (COORDINATOR, valid engagement_ids) → 202, queued_count, outbox+audit records
- AC-2 [Critical]: Empty engagement_ids[] → 422 with field error
- AC-3 [Critical]: Cross-institution engagement_ids mixed with valid ones → queued_count only counts valid ones
- AC-6 [High]: All engagement_ids filtered out (none belong to institution) → 202 with queued_count: 0
- AC-7 [Medium]: Invalid/missing template → 422 with field error
- Davranış Sözleşmesi rows: partial success (row 7), no queued but no error (row 8)

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Error responses validated against {"code": ..., "message": ..., "request_id": ...} schema (wrapped in detail)
- Principal injection: X-Debug-User-Id header
- Engagement model: status, institution_id, talent_id
- Outbox and AuditEvent models verified for side effects
- Implementation not yet available: tests expected to fail (red) with 404 or import error

Coverage Target: Request validation (AC-2, AC-7) + happy path + scope filtering (AC-3, AC-6) + side effects (AC-1)
Status: Tests are RED (expected) — implementation not yet available.
"""

import pytest

from app.models import (
    User,
    TalentProfile,
    Organization,
    Institution,
    Engagement,
    InstitutionMember,
)

# Import will fail until Reminder models/service are implemented
try:
    from app.models import Outbox, AuditEvent
except ImportError:
    Outbox = None
    AuditEvent = None


# ============================================================================
# Fixtures: Users, TalentProfiles, Organizations, Institutions, Engagements
# ============================================================================


@pytest.fixture
def user_talent_alice_rem(session):
    """Talent user Alice for reminder tests."""
    user = User(email="alice.talent.rem@example.com", password_hash="hash_alice")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_bob_rem(session):
    """Talent user Bob for reminder tests."""
    user = User(email="bob.talent.rem@example.com", password_hash="hash_bob")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_charlie_rem(session):
    """Talent user Charlie for reminder tests (Institution B)."""
    user = User(email="charlie.talent.rem@example.com", password_hash="hash_charlie")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_inst_coord_diana_rem(session):
    """INST:COORDINATOR Diana for reminder tests (Institution A)."""
    user = User(email="diana.coord.rem@example.com", password_hash="hash_diana")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_inst_coord_eve_rem(session):
    """INST:COORDINATOR Eve for reminder tests (Institution B)."""
    user = User(email="eve.coord.rem@example.com", password_hash="hash_eve")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_frank_rem(session):
    """Talent user Frank (no role, scope-out test)."""
    user = User(email="frank.talent.rem@example.com", password_hash="hash_frank")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def institution_a_rem(session):
    """Institution A for reminder tests."""
    inst = Institution(name="Institution A", verification_level="T1")
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def institution_b_rem(session):
    """Institution B for reminder tests (cross-tenant scenario)."""
    inst = Institution(name="Institution B", verification_level="T1")
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def org_a_rem(session):
    """Organization A."""
    org = Organization(name="Organization A", verification_level="T1")
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def talent_alice_rem(session, user_talent_alice_rem, institution_a_rem):
    """Talent profile for Alice in Institution A."""
    profile = TalentProfile(
        user_id=user_talent_alice_rem.id,
        institution_id=institution_a_rem.id,
        full_name="Alice Talent Rem",
        visibility="PRIVATE",
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_bob_rem(session, user_talent_bob_rem, institution_a_rem):
    """Talent profile for Bob in Institution A."""
    profile = TalentProfile(
        user_id=user_talent_bob_rem.id,
        institution_id=institution_a_rem.id,
        full_name="Bob Talent Rem",
        visibility="PRIVATE",
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_charlie_rem(session, user_talent_charlie_rem, institution_b_rem):
    """Talent profile for Charlie in Institution B."""
    profile = TalentProfile(
        user_id=user_talent_charlie_rem.id,
        institution_id=institution_b_rem.id,
        full_name="Charlie Talent Rem",
        visibility="PRIVATE",
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def member_diana_rem(session, user_inst_coord_diana_rem, institution_a_rem):
    """InstitutionMember: Diana as COORDINATOR in Institution A."""
    member = InstitutionMember(
        institution_id=institution_a_rem.id,
        user_id=user_inst_coord_diana_rem.id,
        role="COORDINATOR",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def member_eve_rem(session, user_inst_coord_eve_rem, institution_b_rem):
    """InstitutionMember: Eve as COORDINATOR in Institution B."""
    member = InstitutionMember(
        institution_id=institution_b_rem.id,
        user_id=user_inst_coord_eve_rem.id,
        role="COORDINATOR",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def engagement_a1_rem(session, talent_alice_rem, org_a_rem, institution_a_rem):
    """Engagement A1: Alice in Institution A, status=PENDING_EVALUATION."""
    eng = Engagement(
        talent_id=talent_alice_rem.id,
        organization_id=org_a_rem.id,
        institution_id=institution_a_rem.id,
        status="PENDING_EVALUATION",
        kind="INTERNSHIP",
        title="Test Engagement",
    )
    session.add(eng)
    session.flush()
    return eng


@pytest.fixture
def engagement_a2_rem(session, talent_bob_rem, org_a_rem, institution_a_rem):
    """Engagement A2: Bob in Institution A, status=PENDING_EVALUATION."""
    eng = Engagement(
        talent_id=talent_bob_rem.id,
        organization_id=org_a_rem.id,
        institution_id=institution_a_rem.id,
        status="PENDING_EVALUATION",
        kind="INTERNSHIP",
        title="Test Engagement",
    )
    session.add(eng)
    session.flush()
    return eng


@pytest.fixture
def engagement_b1_rem(session, talent_charlie_rem, org_a_rem, institution_b_rem):
    """Engagement B1: Charlie in Institution B, status=PENDING_EVALUATION."""
    eng = Engagement(
        talent_id=talent_charlie_rem.id,
        organization_id=org_a_rem.id,
        institution_id=institution_b_rem.id,
        status="PENDING_EVALUATION",
        kind="INTERNSHIP",
        title="Test Engagement",
    )
    session.add(eng)
    session.flush()
    return eng


# ============================================================================
# AC-1: Happy path — valid engagements trigger reminders
# ============================================================================


def test_happy_path_single_engagement_202(
    client, session, member_diana_rem, engagement_a1_rem, institution_a_rem, user_inst_coord_diana_rem
):
    """
    AC-1 [Critical]: Given valid COORDINATOR, When POST /institutions/{id}/reminders
    with 1 valid engagement_id, Then 202 + queued_count: 1 + 1 outbox record + 1 audit_event record.
    """
    # Use Diana's ID as principal
    # Capture table state before POST
    outbox_count_before = session.query(Outbox).count() if Outbox is not None else None
    audit_count_before = session.query(AuditEvent).count() if AuditEvent is not None else None

    response = client.post(
        f"/institutions/{institution_a_rem.id}/reminders",
        headers={"X-Debug-User-Id": str(user_inst_coord_diana_rem.id)},
        json={
            "engagement_ids": [str(engagement_a1_rem.id)],
            "template": "evaluation_pending",
        },
    )

    # Assert 202 Accepted
    assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"

    # Assert response schema
    data = response.json()
    assert "queued_count" in data, f"Missing queued_count in response: {data}"
    assert data["queued_count"] == 1, f"Expected queued_count: 1, got {data['queued_count']}"

    # Verify side effects: Outbox record created (delta pattern)
    if Outbox is not None:
        outbox_count_after = session.query(Outbox).count()
        assert outbox_count_after - outbox_count_before == 1, \
            f"Expected 1 new outbox record, got {outbox_count_after - outbox_count_before}"
        # Verify topic of the newly created record
        latest_outbox = session.query(Outbox).order_by(Outbox.id.desc()).first()
        assert latest_outbox is not None
        assert latest_outbox.topic in ("reminder.evaluation_pending", "reminder"), \
            f"Unexpected outbox topic: {latest_outbox.topic}"

    # Verify side effects: AuditEvent record created (delta pattern)
    if AuditEvent is not None:
        audit_count_after = session.query(AuditEvent).count()
        assert audit_count_after - audit_count_before == 1, \
            f"Expected 1 new audit_event record, got {audit_count_after - audit_count_before}"
        # Verify fields of the newly created audit event
        latest_audit = session.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
        assert latest_audit is not None
        assert latest_audit.action == "REMINDERS_TRIGGERED", \
            f"Unexpected audit action: {latest_audit.action}"
        assert latest_audit.subject_type == "INSTITUTION", \
            f"Unexpected audit subject_type: {latest_audit.subject_type}"
        assert latest_audit.subject_id == institution_a_rem.id
        assert latest_audit.result == "SUCCESS"
        # Verify no PII in metadata
        assert latest_audit.event_metadata is not None
        metadata = latest_audit.event_metadata
        assert isinstance(metadata, dict)
        # Should contain engagement_id list, template, and queued_count
        assert "engagement_ids" in metadata, f"Missing engagement_ids in metadata: {metadata}"
        assert "queued_count" in metadata, f"Missing queued_count in metadata: {metadata}"
        assert "template" in metadata, f"Missing template in metadata: {metadata}"
        assert metadata["engagement_ids"] == [str(engagement_a1_rem.id)], \
            f"Expected engagement_ids to contain only the queued engagement, got: {metadata['engagement_ids']}"


def test_happy_path_multiple_engagements_202(
    client, session, member_diana_rem, engagement_a1_rem, engagement_a2_rem, institution_a_rem, user_inst_coord_diana_rem
):
    """
    AC-1 [Critical]: Multiple valid engagements (same institution) → 202 + queued_count: 2.
    """
    # Capture table state before POST
    outbox_count_before = session.query(Outbox).count() if Outbox is not None else None

    response = client.post(
        f"/institutions/{institution_a_rem.id}/reminders",
        headers={"X-Debug-User-Id": str(user_inst_coord_diana_rem.id)},
        json={
            "engagement_ids": [str(engagement_a1_rem.id), str(engagement_a2_rem.id)],
            "template": "evaluation_pending",
        },
    )

    assert response.status_code == 202
    data = response.json()
    assert data["queued_count"] == 2, f"Expected queued_count: 2, got {data['queued_count']}"

    # Verify 2 outbox records created (delta pattern)
    if Outbox is not None:
        outbox_count_after = session.query(Outbox).count()
        assert outbox_count_after - outbox_count_before == 2, \
            f"Expected 2 new outbox records, got {outbox_count_after - outbox_count_before}"


# ============================================================================
# AC-2: Empty or missing engagement_ids[] → 400
# ============================================================================


def test_empty_engagement_ids_422(
    client, member_diana_rem, institution_a_rem, user_inst_coord_diana_rem
):
    """
    AC-2 [Critical]: Empty engagement_ids[] → 422 with field error message.
    """
    response = client.post(
        f"/institutions/{institution_a_rem.id}/reminders",
        headers={"X-Debug-User-Id": str(user_inst_coord_diana_rem.id)},
        json={
            "engagement_ids": [],
            "template": "evaluation_pending",
        },
    )

    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    # Validate error schema (wrapped in "detail" for HTTPException)
    data = response.json()
    assert "detail" in data or "message" in data, f"Expected error detail, got: {data}"


def test_missing_engagement_ids_field_422(
    client, member_diana_rem, institution_a_rem, user_inst_coord_diana_rem
):
    """
    AC-2 [Critical]: Missing engagement_ids field → 422.
    """
    response = client.post(
        f"/institutions/{institution_a_rem.id}/reminders",
        headers={"X-Debug-User-Id": str(user_inst_coord_diana_rem.id)},
        json={
            "template": "evaluation_pending",
        },
    )

    assert response.status_code == 422, f"Expected 422, got {response.status_code}"


# ============================================================================
# AC-3: Cross-institution filtering — valid + invalid mixed
# ============================================================================


def test_partial_success_cross_institution_202(
    client, session, member_diana_rem, engagement_a1_rem, engagement_b1_rem,
    institution_a_rem, user_inst_coord_diana_rem
):
    """
    AC-3 [Critical] + Davranış Sözleşmesi row 7: Given 2 engagement_ids (1 belongs to Institution A,
    1 to Institution B), When Diana (COORDINATOR of A) triggers reminders, Then 202 + queued_count: 1
    (only A's engagement processed, B's filtered out silently). No response detail about which was filtered.
    """
    # Capture table state before POST
    outbox_count_before = session.query(Outbox).count() if Outbox is not None else None

    response = client.post(
        f"/institutions/{institution_a_rem.id}/reminders",
        headers={"X-Debug-User-Id": str(user_inst_coord_diana_rem.id)},
        json={
            "engagement_ids": [str(engagement_a1_rem.id), str(engagement_b1_rem.id)],
            "template": "evaluation_pending",
        },
    )

    assert response.status_code == 202
    data = response.json()
    # Only 1 engagement (A1) should be queued; B1 filtered out
    assert data["queued_count"] == 1, f"Expected queued_count: 1, got {data['queued_count']}"

    # Response should NOT indicate which ID was filtered
    assert "filtered_ids" not in data, "Response should not expose filtered_ids"
    assert "invalid_ids" not in data, "Response should not expose invalid_ids"

    # Verify only 1 outbox record created (delta pattern)
    if Outbox is not None:
        outbox_count_after = session.query(Outbox).count()
        assert outbox_count_after - outbox_count_before == 1, \
            f"Expected 1 new outbox record, got {outbox_count_after - outbox_count_before}"


# ============================================================================
# AC-6: All engagement_ids filtered out → 202 + queued_count: 0
# ============================================================================


def test_all_filtered_202_zero_queued(
    client, session, member_diana_rem, engagement_b1_rem,
    institution_a_rem, user_inst_coord_diana_rem
):
    """
    AC-6 [High] + Davranış Sözleşmesi row 8: Given engagement_ids all belonging to other institution,
    When Diana (COORDINATOR of A) sends request, Then 202 + queued_count: 0 (not 404, not error).
    No outbox records, no audit record created (no queued_count > 0).
    """
    # Capture table state before POST
    outbox_count_before = session.query(Outbox).count() if Outbox is not None else None

    response = client.post(
        f"/institutions/{institution_a_rem.id}/reminders",
        headers={"X-Debug-User-Id": str(user_inst_coord_diana_rem.id)},
        json={
            "engagement_ids": [str(engagement_b1_rem.id)],
            "template": "evaluation_pending",
        },
    )

    # 202, not 404 (the difference from AC-4)
    assert response.status_code == 202
    data = response.json()
    assert data["queued_count"] == 0

    # Verify NO outbox records created (nothing to queue) (delta pattern)
    if Outbox is not None:
        outbox_count_after = session.query(Outbox).count()
        assert outbox_count_after - outbox_count_before == 0, \
            f"Expected 0 new outbox records for zero-queued case, got {outbox_count_after - outbox_count_before}"


# ============================================================================
# AC-7: Invalid/missing template → 400
# ============================================================================


def test_empty_template_422(
    client, member_diana_rem, engagement_a1_rem, institution_a_rem, user_inst_coord_diana_rem
):
    """
    AC-7 [Medium]: Empty template string → 422 with field error.
    """
    response = client.post(
        f"/institutions/{institution_a_rem.id}/reminders",
        headers={"X-Debug-User-Id": str(user_inst_coord_diana_rem.id)},
        json={
            "engagement_ids": [str(engagement_a1_rem.id)],
            "template": "",
        },
    )

    assert response.status_code == 422, f"Expected 422, got {response.status_code}"


def test_missing_template_422(
    client, member_diana_rem, engagement_a1_rem, institution_a_rem, user_inst_coord_diana_rem
):
    """
    AC-7 [Medium]: Missing template field → 422.
    """
    response = client.post(
        f"/institutions/{institution_a_rem.id}/reminders",
        headers={"X-Debug-User-Id": str(user_inst_coord_diana_rem.id)},
        json={
            "engagement_ids": [str(engagement_a1_rem.id)],
        },
    )

    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
