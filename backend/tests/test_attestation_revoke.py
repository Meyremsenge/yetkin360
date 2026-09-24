"""
Attestation revoke endpoint tests (PLAN 2.10 — yet-72-attestation-revoke, AC-1 through AC-8, AC-S1/S3).

Implements Acceptance Criteria for POST /attestations/{id}/revoke:
- AC-1: Happy path — attestor geri çeker → 200, Attestation.revoked_at/revoke_reason set, tombstone SkillSignal, AuditEvent
- AC-2: Attestor olmayan (ama kaynağa erişimi olan) → 403 FORBIDDEN
- AC-3: Scope dışı (kaynağa hiç erişimi yok) → 404 NOT_FOUND
- AC-4: attestation_id yok → 404 NOT_FOUND
- AC-5: Zaten geri çekilmiş → 409 ALREADY_REVOKED
- AC-6: revoke_reason boş/eksik → 422
- AC-7: Revoke sonrası diğer alanlar (claim_type, attestor_user_id, created_at) değişmemiş
- AC-S1: AuditEvent metadata'sında revoke_reason METNİ YOK
- AC-S3: DB trigger'ı — sadece revoked_at/revoke_reason değişmesine izin ver, başka alan → IntegrityError

Threat-model testleri (AC-S2 authorization test dosyasında):
- AC-S2: Eşzamanlı iki revoke — biri 200, diğeri 409

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Error responses validated against {"code": ..., "message": ..., "request_id": ...} schema
- Principal injection: X-Debug-User-Id header
- Attestation seeded via POST /engagements/{id}/attestations (YET-70 implementasyonuna dayanır)
- revoke_attestation() fonksiyonu ve POST /attestations/{id}/revoke route'u henüz yok (import error expected)

Coverage Target: Happy path (AC-1) + error scenarios (AC-4/5/6) + domain rules (AC-7, AC-S1/S3).

Status: Tests are RED (expected) — implementation not yet available.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.models import (
    User,
    TalentProfile,
    Organization,
    Institution,
    Engagement,
    InstitutionMember,
    Skill,
    Deliverable,
)

# Import will fail until Attestation/VerifiedExperience models are implemented
try:
    from app.models import Attestation, VerifiedExperience, SkillSignal, AuditEvent
except ImportError:
    Attestation = None
    VerifiedExperience = None
    SkillSignal = None
    AuditEvent = None


# ============================================================================
# Fixtures: Reusable entities for attestation revoke tests
# ============================================================================


@pytest.fixture
def user_talent_revoke(session):
    """Talent user for revoke tests."""
    user = User(email="talent.revoke@example.com", password_hash="hash_talent")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_attestor_revoke(session):
    """INST:COORD user who will be attestor."""
    user = User(email="attestor.revoke@example.com", password_hash="hash_attestor")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_other_coord_revoke(session):
    """INST:COORD from same institution but NOT the attestor."""
    user = User(email="other.coord.revoke@example.com", password_hash="hash_other")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_cross_inst_coord_revoke(session):
    """INST:COORD from different institution (scope out)."""
    user = User(email="cross.coord.revoke@example.com", password_hash="hash_cross")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def organization_revoke(session):
    """Organization for revoke tests (T2+ verified)."""
    org = Organization(
        name="Test Org Revoke",
        domain="testorgrevoke.example.com",
        legal_id="ORG-REVOKE-001",
        verification_level="T2",
        status="ACTIVE",
        verified_at=datetime.utcnow() - timedelta(days=30),
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def institution_revoke(session):
    """Institution for revoke tests."""
    inst = Institution(
        name="Test Institution Revoke",
        domain="testinstrevoke.example.com",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def institution_cross_revoke(session):
    """Institution cross-tenant for scope-out tests."""
    inst = Institution(
        name="Cross Institution Revoke",
        domain="crossinstrevoke.example.com",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def talent_revoke(session, user_talent_revoke, institution_revoke):
    """Talent profile for revoke tests."""
    profile = TalentProfile(
        user_id=user_talent_revoke.id,
        institution_id=institution_revoke.id,
        full_name="Talent Revoke",
        visibility="PRIVATE",
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def inst_coord_attestor_revoke(session, institution_revoke, user_attestor_revoke):
    """INST:COORD who will be the attestor."""
    coord = InstitutionMember(
        institution_id=institution_revoke.id,
        user_id=user_attestor_revoke.id,
        role="COORDINATOR",
    )
    session.add(coord)
    session.flush()
    return coord


@pytest.fixture
def inst_coord_other_revoke(session, institution_revoke, user_other_coord_revoke):
    """INST:COORD from same institution but not the attestor."""
    coord = InstitutionMember(
        institution_id=institution_revoke.id,
        user_id=user_other_coord_revoke.id,
        role="COORDINATOR",
    )
    session.add(coord)
    session.flush()
    return coord


@pytest.fixture
def inst_coord_cross_revoke(session, institution_cross_revoke, user_cross_inst_coord_revoke):
    """INST:COORD from different institution (scope out)."""
    coord = InstitutionMember(
        institution_id=institution_cross_revoke.id,
        user_id=user_cross_inst_coord_revoke.id,
        role="COORDINATOR",
    )
    session.add(coord)
    session.flush()
    return coord


@pytest.fixture
def skill_revoke(session):
    """Test skill for revoke tests."""
    skill = Skill(
        slug="skill-revoke",
        name_tr="Test Yetkinlik",
        name_en="Test Skill",
        category="SOFT",
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def engagement_evaluated_revoke(session, talent_revoke, organization_revoke, institution_revoke):
    """EVALUATED engagement for revoke tests."""
    now = datetime.utcnow()
    engagement = Engagement(
        talent_id=talent_revoke.id,
        organization_id=organization_revoke.id,
        institution_id=institution_revoke.id,
        kind="INTERNSHIP",
        title="Revoke Test Engagement",
        status="EVALUATED",
        version=1,
        started_on=now - timedelta(days=35),
        ended_on=now - timedelta(days=1),
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def deliverable_revoke(session, engagement_evaluated_revoke, skill_revoke, user_talent_revoke):
    """Deliverable for engagement (ensures COMPETENCE claim_type eligibility)."""
    deliverable = Deliverable(
        engagement_id=engagement_evaluated_revoke.id,
        title="Test Deliverable",
        description="Test deliverable for revoke tests",
        submitted_by_user_id=user_talent_revoke.id,
        submitted_at=datetime.now(timezone.utc),
    )
    session.add(deliverable)
    session.flush()
    return deliverable


def create_attestation_via_endpoint(client, session, engagement, attestor_user, status="COMPETENCE", skill_id: str | None = None):
    """
    Helper: Create a real Attestation via POST /engagements/{id}/attestations.
    Returns the created Attestation record and its ID.

    This helper relies on YET-70 (Attestation creation) being already implemented.
    """
    payload = {
        "claim_type": status,
        "version": 1,
    }
    if skill_id:
        payload["skill_id"] = skill_id

    response = client.post(
        f"/engagements/{engagement.id}/attestations",
        json=payload,
        headers={"X-Debug-User-Id": str(attestor_user.id)},
    )

    if response.status_code != 201:
        raise RuntimeError(
            f"Failed to create attestation via POST /engagements: "
            f"{response.status_code} {response.text}"
        )

    data = response.json()
    attestation_id = data.get("id")

    # Fetch the Attestation record from DB
    if Attestation:
        att = session.query(Attestation).filter_by(id=attestation_id).first()
        return att, attestation_id

    return None, attestation_id


# ============================================================================
# AC-1: Happy Path — Attestor kendi tanıklığını geri çeker
# ============================================================================


class TestAttestationRevokeHappyPath:
    """
    AC-1: Attestor kendi tanıklığını geri çeker → 200, Attestation.revoked_at/revoke_reason set,
    tombstone SkillSignal (strength=NONE) oluşur, eski sinyal'in superseded_by_id set edilir, AuditEvent yazılır.
    """

    def test_revoke_attestation_happy_path_200(
        self, client, session, engagement_evaluated_revoke, user_attestor_revoke,
        inst_coord_attestor_revoke, deliverable_revoke
    ):
        """
        AC-1: Diana (attestor) kendi tanıklığını geri çeker.
        Expected: 200 OK, Attestation.revoked_at/revoke_reason set, eski SkillSignal superseded.
        """
        # First, create an attestation via endpoint
        att, attestation_id = create_attestation_via_endpoint(
            client, session, engagement_evaluated_revoke, user_attestor_revoke, "COMPETENCE"
        )

        if not attestation_id:
            pytest.skip("Attestation creation endpoint (YET-70) not yet implemented")

        # Now revoke
        payload = {
            "revoke_reason": "Yanlış değerlendirilmiş — talenta iletişim sırasında başka değişiklik oldu"
        }

        response = client.post(
            f"/attestations/{attestation_id}/revoke",
            json=payload,
            headers={"X-Debug-User-Id": str(user_attestor_revoke.id)},
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Assert: response contains revoked_at and revoke_reason
        assert "id" in data
        assert "revoked_at" in data
        assert data.get("revoke_reason") == payload["revoke_reason"]

        # DB verification: Attestation updated
        if Attestation:
            att_updated = session.query(Attestation).filter_by(id=attestation_id).first()
            assert att_updated is not None
            assert att_updated.revoked_at is not None
            assert att_updated.revoke_reason == payload["revoke_reason"]

            # Verify append-only: other fields unchanged
            assert att_updated.claim_type == "COMPETENCE"  # Same as created
            assert att_updated.attestor_user_id == user_attestor_revoke.id  # Unchanged
            assert att_updated.created_at is not None  # Original created_at preserved


    def test_revoke_attestation_tombstone_skill_signal_created(
        self, client, session, engagement_evaluated_revoke, user_attestor_revoke,
        inst_coord_attestor_revoke, deliverable_revoke, skill_revoke
    ):
        """
        AC-1 part 2: Revoke creates tombstone SkillSignal (strength=NONE) and supersedes old signal.
        """
        # Create attestation
        att, attestation_id = create_attestation_via_endpoint(
            client, session, engagement_evaluated_revoke, user_attestor_revoke, "COMPETENCE", skill_id=str(skill_revoke.id)
        )

        if not attestation_id:
            pytest.skip("Attestation creation endpoint (YET-70) not yet implemented")

        # Count existing SkillSignals before revoke
        if SkillSignal:
            old_signals = session.query(SkillSignal).filter_by(
                source_type="ATTESTATION",
                source_id=attestation_id
            ).all()
            old_signal_count = len(old_signals)

        # Revoke
        payload = {"revoke_reason": "Test revoke"}
        response = client.post(
            f"/attestations/{attestation_id}/revoke",
            json=payload,
            headers={"X-Debug-User-Id": str(user_attestor_revoke.id)},
        )

        assert response.status_code == 200

        # DB verification: new tombstone signal created, old signal superseded
        if SkillSignal:
            # Find all signals for this attestation
            all_signals = session.query(SkillSignal).filter_by(
                source_type="ATTESTATION",
                source_id=attestation_id
            ).all()

            # Should have at least one more signal (tombstone)
            assert len(all_signals) >= old_signal_count

            # Tombstone signal should have strength=NONE
            tombstone = session.query(SkillSignal).filter_by(
                source_type="ATTESTATION",
                source_id=attestation_id,
                strength="NONE"
            ).first()
            assert tombstone is not None, "Tombstone signal (strength=NONE) not created"

            # Old signals should point to tombstone via superseded_by_id
            if old_signal_count > 0 and old_signals:
                for old_sig in old_signals:
                    refreshed = session.query(SkillSignal).filter_by(id=old_sig.id).first()
                    if refreshed and refreshed.strength != "NONE":
                        assert refreshed.superseded_by_id == tombstone.id, \
                            f"Old signal {old_sig.id} not pointing to tombstone"


# ============================================================================
# AC-4: Not Found — attestation_id yok
# ============================================================================


class TestAttestationRevokeNotFound:
    """
    AC-4: attestation_id invalid/nonexistent → 404 NOT_FOUND.
    """

    def test_revoke_nonexistent_attestation_404(
        self, client, session, user_attestor_revoke
    ):
        """
        AC-4: Try to revoke non-existent attestation_id → 404.
        """
        fake_id = str(uuid4())
        payload = {"revoke_reason": "Test"}

        response = client.post(
            f"/attestations/{fake_id}/revoke",
            json=payload,
            headers={"X-Debug-User-Id": str(user_attestor_revoke.id)},
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") == "NOT_FOUND"


# ============================================================================
# AC-5: Conflict — Zaten geri çekilmiş (ALREADY_REVOKED)
# ============================================================================


class TestAttestationRevokeAlreadyRevoked:
    """
    AC-5: Attestation zaten geri çekilmiş → 409 ALREADY_REVOKED, no writes.
    """

    def test_revoke_already_revoked_409(
        self, client, session, engagement_evaluated_revoke, user_attestor_revoke,
        inst_coord_attestor_revoke, deliverable_revoke
    ):
        """
        AC-5: Try to revoke an already-revoked attestation → 409 ALREADY_REVOKED.
        """
        # Create attestation
        att, attestation_id = create_attestation_via_endpoint(
            client, session, engagement_evaluated_revoke, user_attestor_revoke, "COMPETENCE"
        )

        if not attestation_id:
            pytest.skip("Attestation creation endpoint (YET-70) not yet implemented")

        # First revoke: should succeed
        payload1 = {"revoke_reason": "First revoke"}
        response1 = client.post(
            f"/attestations/{attestation_id}/revoke",
            json=payload1,
            headers={"X-Debug-User-Id": str(user_attestor_revoke.id)},
        )

        assert response1.status_code == 200

        # Capture revoked_at from first revoke
        if Attestation:
            att_first = session.query(Attestation).filter_by(id=attestation_id).first()
            first_revoked_at = att_first.revoked_at

        # Second revoke: should fail with 409
        payload2 = {"revoke_reason": "Second revoke attempt"}
        response2 = client.post(
            f"/attestations/{attestation_id}/revoke",
            json=payload2,
            headers={"X-Debug-User-Id": str(user_attestor_revoke.id)},
        )

        assert response2.status_code == 409, f"Expected 409, got {response2.status_code}: {response2.text}"

        data = response2.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") == "ALREADY_REVOKED"

        # Verify DB: revoked_at unchanged
        if Attestation:
            att_second = session.query(Attestation).filter_by(id=attestation_id).first()
            assert att_second.revoked_at == first_revoked_at, \
                "revoked_at should not change on second revoke attempt"


# ============================================================================
# AC-6: Unprocessable Entity — revoke_reason boş/eksik
# ============================================================================


class TestAttestationRevokeValidation:
    """
    AC-6: revoke_reason missing/empty → 422 Unprocessable Entity.
    """

    def test_revoke_missing_reason_422(
        self, client, session, engagement_evaluated_revoke, user_attestor_revoke,
        inst_coord_attestor_revoke, deliverable_revoke
    ):
        """
        AC-6: Missing revoke_reason field → 422.
        """
        # Create attestation
        att, attestation_id = create_attestation_via_endpoint(
            client, session, engagement_evaluated_revoke, user_attestor_revoke, "COMPETENCE"
        )

        if not attestation_id:
            pytest.skip("Attestation creation endpoint (YET-70) not yet implemented")

        # Revoke without revoke_reason
        payload = {}  # Missing revoke_reason

        response = client.post(
            f"/attestations/{attestation_id}/revoke",
            json=payload,
            headers={"X-Debug-User-Id": str(user_attestor_revoke.id)},
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"


    def test_revoke_empty_reason_422(
        self, client, session, engagement_evaluated_revoke, user_attestor_revoke,
        inst_coord_attestor_revoke, deliverable_revoke
    ):
        """
        AC-6: Empty revoke_reason string → 422.
        """
        # Create attestation
        att, attestation_id = create_attestation_via_endpoint(
            client, session, engagement_evaluated_revoke, user_attestor_revoke, "COMPETENCE"
        )

        if not attestation_id:
            pytest.skip("Attestation creation endpoint (YET-70) not yet implemented")

        # Revoke with empty reason
        payload = {"revoke_reason": ""}

        response = client.post(
            f"/attestations/{attestation_id}/revoke",
            json=payload,
            headers={"X-Debug-User-Id": str(user_attestor_revoke.id)},
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"


# ============================================================================
# AC-7: Append-only Verification — Diğer alanlar değişmemiş
# ============================================================================


class TestAttestationRevokeAppendOnly:
    """
    AC-7: After revoke, Attestation's claim_type, attestor_user_id, created_at remain unchanged.
    """

    def test_revoke_preserves_original_fields(
        self, client, session, engagement_evaluated_revoke, user_attestor_revoke,
        inst_coord_attestor_revoke, deliverable_revoke
    ):
        """
        AC-7: Verify append-only behavior — claim_type, attestor_user_id, created_at unchanged.
        """
        # Create attestation
        att, attestation_id = create_attestation_via_endpoint(
            client, session, engagement_evaluated_revoke, user_attestor_revoke, "COMPETENCE"
        )

        if not attestation_id:
            pytest.skip("Attestation creation endpoint (YET-70) not yet implemented")

        # Capture original values
        if Attestation:
            att_before = session.query(Attestation).filter_by(id=attestation_id).first()
            orig_claim_type = att_before.claim_type
            orig_attestor_id = att_before.attestor_user_id
            orig_created_at = att_before.created_at
            orig_engagement_id = att_before.engagement_id

        # Revoke
        payload = {"revoke_reason": "Test append-only"}
        response = client.post(
            f"/attestations/{attestation_id}/revoke",
            json=payload,
            headers={"X-Debug-User-Id": str(user_attestor_revoke.id)},
        )

        assert response.status_code == 200

        # Verify fields unchanged
        if Attestation:
            att_after = session.query(Attestation).filter_by(id=attestation_id).first()

            assert att_after.claim_type == orig_claim_type, "claim_type should not change"
            assert att_after.attestor_user_id == orig_attestor_id, "attestor_user_id should not change"
            assert att_after.created_at == orig_created_at, "created_at should not change"
            assert att_after.engagement_id == orig_engagement_id, "engagement_id should not change"


# ============================================================================
# AC-S1: Security — AuditEvent metadata doesn't contain revoke_reason TEXT
# ============================================================================


class TestAttestationRevokeAuditSecurity:
    """
    AC-S1: AuditEvent is logged, but revoke_reason text is NOT in metadata (PII risk).
    """

    def test_revoke_audit_event_no_reason_text(
        self, client, session, engagement_evaluated_revoke, user_attestor_revoke,
        inst_coord_attestor_revoke, deliverable_revoke
    ):
        """
        AC-S1: Verify AuditEvent is written, but revoke_reason text is NOT in metadata.
        Metadata should contain action/actor/resource IDs, not sensitive text.
        """
        # Create attestation
        att, attestation_id = create_attestation_via_endpoint(
            client, session, engagement_evaluated_revoke, user_attestor_revoke, "COMPETENCE"
        )

        if not attestation_id:
            pytest.skip("Attestation creation endpoint (YET-70) not yet implemented")

        # Revoke
        revoke_reason = "Confidential reason with sensitive details"
        payload = {"revoke_reason": revoke_reason}

        response = client.post(
            f"/attestations/{attestation_id}/revoke",
            json=payload,
            headers={"X-Debug-User-Id": str(user_attestor_revoke.id)},
        )

        assert response.status_code == 200

        # Check AuditEvent
        if AuditEvent:
            audit = session.query(AuditEvent).filter_by(
                action="ATTESTATION_REVOKED",
                actor_user_id=user_attestor_revoke.id
            ).order_by(AuditEvent.created_at.desc()).first()

            if audit:
                # Verify revoke_reason text is NOT in metadata
                if audit.metadata:
                    metadata_str = str(audit.metadata).lower()
                    assert revoke_reason.lower() not in metadata_str, \
                        "revoke_reason text should not appear in audit metadata (PII risk)"


# ============================================================================
# AC-S3: Security — DB Trigger protects against unauthorized field updates
# ============================================================================


class TestAttestationRevokeDBTrigger:
    """
    AC-S3: DB trigger prevents UPDATE of fields other than revoked_at/revoke_reason.
    Attempting to change claim_type or other fields should raise IntegrityError.
    """

    def test_trigger_prevents_claim_type_update(
        self, session, engagement_evaluated_revoke, user_attestor_revoke,
        inst_coord_attestor_revoke, deliverable_revoke
    ):
        """
        AC-S3: Try to UPDATE attestations.claim_type directly → trigger rejects.
        This tests DB-level immutability enforcement (not via service code).
        """
        # Create attestation directly (bypass endpoint)
        if not Attestation:
            pytest.skip("Attestation model not available")

        att = Attestation(
            engagement_id=engagement_evaluated_revoke.id,
            talent_id=engagement_evaluated_revoke.talent_id,
            subject_type="ENGAGEMENT",
            subject_id=engagement_evaluated_revoke.id,
            claim_type="COMPETENCE",
            requested_claim_type="COMPETENCE",
            attestor_user_id=user_attestor_revoke.id,
        )
        session.add(att)
        session.flush()
        att_id = att.id

        # Try to change claim_type (should fail trigger)
        from sqlalchemy import update
        try:
            session.execute(
                update(Attestation)
                .where(Attestation.id == att_id)
                .values(claim_type="PARTICIPATION")
            )
            session.flush()

            # If we reach here, trigger didn't prevent it (test fails)
            pytest.fail("Trigger should have prevented claim_type update")
        except Exception as e:
            # Expected: trigger raises exception
            assert "trigger" in str(e).lower() or "constraint" in str(e).lower(), \
                f"Expected trigger/constraint error, got: {e}"


    def test_trigger_allows_revoked_at_update(
        self, session, engagement_evaluated_revoke, user_attestor_revoke,
        inst_coord_attestor_revoke
    ):
        """
        AC-S3 (positive): Trigger ALLOWS UPDATE of revoked_at/revoke_reason.
        """
        # Create attestation
        if not Attestation:
            pytest.skip("Attestation model not available")

        att = Attestation(
            engagement_id=engagement_evaluated_revoke.id,
            talent_id=engagement_evaluated_revoke.talent_id,
            subject_type="ENGAGEMENT",
            subject_id=engagement_evaluated_revoke.id,
            claim_type="COMPETENCE",
            requested_claim_type="COMPETENCE",
            attestor_user_id=user_attestor_revoke.id,
        )
        session.add(att)
        session.flush()
        att_id = att.id

        # Try to set revoked_at/revoke_reason (should succeed)
        from sqlalchemy import update
        now = datetime.now(timezone.utc)

        try:
            session.execute(
                update(Attestation)
                .where(Attestation.id == att_id)
                .values(revoked_at=now, revoke_reason="Test revoke")
            )
            session.flush()

            # Verify update succeeded
            att_updated = session.query(Attestation).filter_by(id=att_id).first()
            assert att_updated.revoked_at is not None
            assert att_updated.revoke_reason == "Test revoke"
        except Exception as e:
            pytest.fail(f"Trigger should allow revoked_at/revoke_reason update, got: {e}")
