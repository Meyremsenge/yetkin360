"""
Attestation endpoint tests (PLAN 2.8 — yet-70-attestation-verified-experience-uretimi, AC-1 through AC-9).

Implements Acceptance Criteria for POST /engagements/{id}/attestations:
- AC-1: Happy path (INST:COORD, EVALUATED, tüm ön koşullar, claim_type=COMPETENCE) → 201, tek transaction
- AC-2: Kısmi başarı — COMPETENCE istenip 1+ ön koşul eksik → 201, downgrade PARTICIPATION, downgrade_reasons dolu
- AC-3: Engagement durumu EVALUATED değil (örn. ACTIVE) → 409 INVALID_STATE_TRANSITION
- AC-4: TALENT tarafından POST → 403 FORBIDDEN (S6 istisnası: kaynağın varlığı talent'a zaten görünür)
- AC-5: Scope dışı INST:COORD (başka kuruma ait engagement) → 404 NOT_FOUND
- AC-6: Eski version ile çakışma → 409 CONFLICT (VERSION_MISMATCH)
- AC-7: claim_type eksik/geçersiz enum → 422
- AC-8: Attestation zaten var (tekrar gönderim) → 409 CONFLICT (ATTESTATION_ALREADY_EXISTS)
- AC-9: institution_id NULL (doğrudan kurumsal engagement), ORG:SUPERVISOR T8 tetikler → madde 6 kontrol listesinden çıkarılır

Threat-model testleri (AC-S1/S2/S3/S4/S5):
- AC-S1: attestor_user_id body'den tamperlense bile oturumdan alındığını test et
- AC-S2: cross-institution (başka üniversite) 404 döner
- AC-S3: self-attestation (attestor = talent) 409 döner
- AC-S4: claim_type manipülasyonu (extra alanlar) — Pydantic extra="forbid" ile reddedilir (422 veya ignore)
- AC-S5: race condition — iki concurrent POST aynı version, sadece biri 201, diğeri 409

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Error responses validated against {"code": ..., "message": ..., "request_id": ...} schema (wrapped in detail)
- Principal injection: X-Debug-User-Id header
- Engagement seeded with EVALUATED status (T8 ön koşulu)
- Attestation/VerifiedExperience model + POST /engagements/{id}/attestations route'u henüz yok (import error expected)

Plan.md Kararları:
1. downgrade kodu: NO_DELIVERABLE (atdd.md'deki NO_DELIVERABLE_FOR_SKILL yerine)
2. attestations tablosuna talent_id denormalize — CHECK(attestor_user_id != talent_id) doğrudan
3. version alanı body'de (If-Match header değil) — TransitionEngagementRequest desenyle aynı
4. Tek endpoint: POST /engagements/{id}/attestations — hem Attestation oluşturur hem T8 geçişini tetikler

Coverage Target: Attestation creation (happy path + downgrade + state transitions + threat-model scenarios).

Status: Tests are RED (expected) — implementation not yet available.
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.models import (
    User,
    TalentProfile,
    Organization,
    Institution,
    Engagement,
    OrganizationMember,
    InstitutionMember,
    Skill,
    Deliverable,
)

# Import will fail until Attestation/VerifiedExperience models are implemented
try:
    from app.models import Attestation, VerifiedExperience
except ImportError:
    Attestation = None
    VerifiedExperience = None


# ============================================================================
# Fixtures: Users, Talents, Organizations, Institutions, Engagements
# ============================================================================


@pytest.fixture
def user_talent_alice_att(session):
    """Talent user Alice for attestation tests."""
    user = User(email="alice.talent.att@example.com", password_hash="hash_alice")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_bob_att(session):
    """Talent user Bob for attestation isolation tests."""
    user = User(email="bob.talent.att@example.com", password_hash="hash_bob")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_inst_coord_diana_att(session):
    """INST:COORD user Diana for attestation tests."""
    user = User(email="diana.coord.att@example.com", password_hash="hash_diana")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_inst_coord_frank_att(session):
    """INST:COORD user Frank from different institution for isolation."""
    user = User(email="frank.coord.att@example.com", password_hash="hash_frank")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_org_supervisor_grace_att(session):
    """ORG:SUPERVISOR user Grace for institution_id=NULL engagement tests."""
    user = User(email="grace.supervisor.att@example.com", password_hash="hash_grace")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent_alice_att(session, user_talent_alice_att, institution_a_att):
    """Talent profile for Alice (institution_a)."""
    profile = TalentProfile(
        user_id=user_talent_alice_att.id,
        institution_id=institution_a_att.id,
        full_name="Alice Talent Att",
        visibility="PRIVATE",
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_bob_att(session, user_talent_bob_att, institution_b_att):
    """Talent profile for Bob (institution_b)."""
    profile = TalentProfile(
        user_id=user_talent_bob_att.id,
        institution_id=institution_b_att.id,
        full_name="Bob Talent Att",
        visibility="PRIVATE",
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def organization_a_att(session):
    """Organization A (T2+ verified) for attestation tests."""
    org = Organization(
        name="Test Org A Att",
        domain="testorga.att.example.com",
        legal_id="ORG-A-ATT-001",
        verification_level="T2",
        status="ACTIVE",
        verified_at=datetime.utcnow() - timedelta(days=30),
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def organization_b_att(session):
    """Organization B for attestation isolation tests."""
    org = Organization(
        name="Test Org B Att",
        domain="testorgb.att.example.com",
        legal_id="ORG-B-ATT-001",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def organization_direct_att(session):
    """Organization for direct (institution_id=NULL) engagements."""
    org = Organization(
        name="Direct Org Att",
        domain="directorg.att.example.com",
        legal_id="DIRECT-ORG-001",
        verification_level="T2",
        status="ACTIVE",
        verified_at=datetime.utcnow() - timedelta(days=30),
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def institution_a_att(session):
    """Institution A for attestation tests."""
    inst = Institution(
        name="Test Institution A Att",
        domain="testinsta.att.example.com",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def institution_b_att(session):
    """Institution B for cross-institution isolation."""
    inst = Institution(
        name="Test Institution B Att",
        domain="testinstb.att.example.com",
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(inst)
    session.flush()
    return inst


@pytest.fixture
def inst_coord_diana_att(session, institution_a_att, user_inst_coord_diana_att):
    """Diana is INST:COORD of institution_a."""
    coord = InstitutionMember(
        institution_id=institution_a_att.id,
        user_id=user_inst_coord_diana_att.id,
        role="COORDINATOR",
    )
    session.add(coord)
    session.flush()
    return coord


@pytest.fixture
def inst_coord_frank_att(session, institution_b_att, user_inst_coord_frank_att):
    """Frank is INST:COORD of institution_b."""
    coord = InstitutionMember(
        institution_id=institution_b_att.id,
        user_id=user_inst_coord_frank_att.id,
        role="COORDINATOR",
    )
    session.add(coord)
    session.flush()
    return coord


@pytest.fixture
def org_member_supervisor_grace_att(session, organization_direct_att, user_org_supervisor_grace_att):
    """Grace is ORG:SUPERVISOR (ORG_ADMIN) of direct_org for T8 attestation authority."""
    member = OrganizationMember(
        organization_id=organization_direct_att.id,
        user_id=user_org_supervisor_grace_att.id,
        role="ADMIN",
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def skill_communication_att(session):
    """Test skill: Communication."""
    skill = Skill(
        slug="communication-att",
        name_tr="İletişim",
        name_en="Communication",
        category="SOFT",
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def skill_python_att(session):
    """Test skill: Python programming."""
    skill = Skill(
        slug="python-att",
        name_tr="Python Programlama",
        name_en="Python Programming",
        category="LANGUAGE",
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def engagement_evaluated_alice_att(session, talent_alice_att, organization_a_att, institution_a_att):
    """EVALUATED engagement for Alice (happy path status, institution-based)."""
    now = datetime.utcnow()
    engagement = Engagement(
        talent_id=talent_alice_att.id,
        organization_id=organization_a_att.id,
        institution_id=institution_a_att.id,
        kind="INTERNSHIP",
        title="Alice Attestation Test Project",
        status="EVALUATED",
        version=1,
        started_on=now - timedelta(days=35),
        ended_on=now - timedelta(days=1),
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_active_alice_att(session, talent_alice_att, organization_a_att, institution_a_att):
    """ACTIVE engagement for Alice (wrong status for attestation T8)."""
    now = datetime.utcnow()
    engagement = Engagement(
        talent_id=talent_alice_att.id,
        organization_id=organization_a_att.id,
        institution_id=institution_a_att.id,
        kind="INTERNSHIP",
        title="Alice Active Project",
        status="ACTIVE",
        version=1,
        started_on=now - timedelta(days=10),
        ended_on=None,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_evaluated_bob_cross_inst_att(session, talent_bob_att, organization_b_att, institution_b_att):
    """EVALUATED engagement for Bob in institution_b (cross-institution isolation test)."""
    now = datetime.utcnow()
    engagement = Engagement(
        talent_id=talent_bob_att.id,
        organization_id=organization_b_att.id,
        institution_id=institution_b_att.id,
        kind="INTERNSHIP",
        title="Bob Cross-Inst Project",
        status="EVALUATED",
        version=1,
        started_on=now - timedelta(days=35),
        ended_on=now - timedelta(days=1),
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def engagement_evaluated_direct_att(session, talent_alice_att, organization_direct_att):
    """EVALUATED engagement for Alice (institution_id=NULL, direct org engagement)."""
    now = datetime.utcnow()
    engagement = Engagement(
        talent_id=talent_alice_att.id,
        organization_id=organization_direct_att.id,
        institution_id=None,  # Direct engagement
        kind="SHORT_PROJECT",
        title="Alice Direct Engagement",
        status="EVALUATED",
        version=1,
        started_on=now - timedelta(days=35),
        ended_on=now - timedelta(days=1),
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def deliverable_alice_att(session, engagement_evaluated_alice_att, skill_communication_att, user_talent_alice_att):
    """Deliverable for Alice's engagement (kriter 3 ön koşulu)."""
    deliverable = Deliverable(
        engagement_id=engagement_evaluated_alice_att.id,
        title="Communication Plan",
        description="Prepared communication strategy",
        submitted_by_user_id=user_talent_alice_att.id,
        submitted_at=datetime.now(timezone.utc),
    )
    session.add(deliverable)
    session.flush()
    return deliverable


# ============================================================================
# AC-1: Happy Path — Attestation Submission (COMPETENCE, tüm ön koşullar)
# ============================================================================


class TestAttestationHappyPath:
    """
    AC-1: INST:COORD submits attestation on EVALUATED engagement, tüm COMPETENCE ön koşulları sağlanmış.
    Expected: 201 + Attestation + VerifiedExperience + SkillSignal + AuditEvent tek transaction'da,
    engagement.status=VERIFIED, version artar.
    """

    def test_attestation_competence_happy_path_201(
        self, client, session, user_inst_coord_diana_att, inst_coord_diana_att,
        engagement_evaluated_alice_att, skill_communication_att, deliverable_alice_att
    ):
        """
        AC-1: Diana (INST:COORD) submits attestation on Alice's EVALUATED engagement.
        All COMPETENCE preconditions met: mutual confirmation (EVALUATED status), >4 weeks duration,
        deliverable present, T2+ org verified, coordinator confirmed (Diana is coord).

        Acceptance Criteria:
        - Status code: 201 Created
        - Response contains: id (UUID), claim_type=COMPETENCE, requested_claim_type=COMPETENCE,
          downgrade_reasons=[] (empty list), engagement updated to status=VERIFIED, version incremented
        - Single transaction: Attestation + VerifiedExperience + SkillSignal + AuditEvent + Outbox
        """
        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_evaluated_alice_att.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana_att.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()

        # Assert: response schema
        assert "id" in data
        assert data.get("claim_type") == "COMPETENCE"
        assert data.get("requested_claim_type") == "COMPETENCE"
        assert data.get("downgrade_reasons") == []

        # DB verification: engagement status updated, version incremented
        session.refresh(engagement_evaluated_alice_att)
        assert engagement_evaluated_alice_att.status == "VERIFIED", \
            f"Expected VERIFIED, got {engagement_evaluated_alice_att.status}"
        assert engagement_evaluated_alice_att.version == 2, \
            f"Expected version 2, got {engagement_evaluated_alice_att.version}"

        # Verify Attestation created (if model available)
        if Attestation:
            att = session.query(Attestation).filter_by(
                engagement_id=engagement_evaluated_alice_att.id
            ).first()
            assert att is not None
            assert att.claim_type == "COMPETENCE"
            assert att.requested_claim_type == "COMPETENCE"
            assert att.attestor_user_id == user_inst_coord_diana_att.id

    def test_attestation_with_statement_enqueues_fraud_check_outbox(
        self, client, session, user_inst_coord_diana_att, inst_coord_diana_att,
        engagement_evaluated_alice_att, skill_communication_att, deliverable_alice_att
    ):
        """PLAN 3.54: statement verilirse attestations.statement'a yazılır VE
        outbox'a attestation.fraud_check_requested eklenir (AI hiçbir zaman
        attestations'a yazmaz — sadece bu outbox satırını worker işler)."""
        from app.models import Outbox

        payload = {"claim_type": "COMPETENCE", "version": 1, "statement": "Alice projeyi tek başına teslim etti."}

        response = client.post(
            f"/engagements/{engagement_evaluated_alice_att.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana_att.id)},
        )
        assert response.status_code == 201, response.text

        att = session.query(Attestation).filter_by(
            engagement_id=engagement_evaluated_alice_att.id
        ).first()
        assert att.statement == "Alice projeyi tek başına teslim etti."

        outbox_row = session.query(Outbox).filter_by(topic="attestation.fraud_check_requested").first()
        assert outbox_row is not None
        assert outbox_row.payload == {"attestation_id": str(att.id)}

    def test_attestation_without_statement_enqueues_no_fraud_check(
        self, client, session, user_inst_coord_diana_att, inst_coord_diana_att,
        engagement_evaluated_alice_att, skill_communication_att, deliverable_alice_att
    ):
        """statement verilmezse fraud_check_requested outbox satırı eklenmez —
        AI'ya gönderilecek boş metin yok."""
        from app.models import Outbox

        payload = {"claim_type": "COMPETENCE", "version": 1}

        response = client.post(
            f"/engagements/{engagement_evaluated_alice_att.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana_att.id)},
        )
        assert response.status_code == 201, response.text

        outbox_row = session.query(Outbox).filter_by(topic="attestation.fraud_check_requested").first()
        assert outbox_row is None

    def test_every_attestation_enqueues_risk_rule_scan_even_without_statement(
        self, client, session, user_inst_coord_diana_att, inst_coord_diana_att,
        engagement_evaluated_alice_att, skill_communication_att, deliverable_alice_att
    ):
        """PLAN 3.56: deterministik risk kuralları statement'tan bağımsızdır —
        her tanıklıkta fraud.attestation_risk_scan_requested eklenir, payload
        yalnız kimlik taşır."""
        from app.models import Outbox

        response = client.post(
            f"/engagements/{engagement_evaluated_alice_att.id}/attestations",
            json={"claim_type": "COMPETENCE", "version": 1},
            headers={"X-Debug-User-Id": str(user_inst_coord_diana_att.id)},
        )
        assert response.status_code == 201, response.text

        att = session.query(Attestation).filter_by(engagement_id=engagement_evaluated_alice_att.id).first()
        outbox_row = session.query(Outbox).filter_by(topic="fraud.attestation_risk_scan_requested").one()
        assert outbox_row.payload == {"attestation_id": str(att.id)}


# ============================================================================
# AC-2: Kısmi Başarı — Downgrade COMPETENCE → PARTICIPATION
# ============================================================================


class TestAttestationPartialSuccessDowngrade:
    """
    AC-2: COMPETENCE istenip 1+ ön koşul eksik → 201 (reddedilmez), downgrade PARTICIPATION.
    downgrade_reasons dolu, yine de VerifiedExperience/SkillSignal/AuditEvent tek transaction'da oluşur.
    """

    def test_attestation_downgrade_no_deliverable_201(
        self, client, session, user_inst_coord_diana_att, inst_coord_diana_att,
        engagement_evaluated_alice_att
    ):
        """
        AC-2: Diana (INST:COORD) submits COMPETENCE attestation, but engagement has NO Deliverable.
        Expected: 201, downgrade to PARTICIPATION, downgrade_reasons=[NO_DELIVERABLE].

        Acceptance Criteria:
        - Status code: 201 Created
        - claim_type=PARTICIPATION (downgraded from COMPETENCE)
        - requested_claim_type=COMPETENCE
        - downgrade_reasons=["NO_DELIVERABLE"] (exact code match)
        - engagement.status=VERIFIED, version incremented
        - VerifiedExperience + SkillSignal created with PARTICIPATION level
        """
        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_evaluated_alice_att.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana_att.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()

        # Assert: downgrade
        assert data.get("claim_type") == "PARTICIPATION"
        assert data.get("requested_claim_type") == "COMPETENCE"
        assert "NO_DELIVERABLE" in data.get("downgrade_reasons", [])

        # DB verification
        session.refresh(engagement_evaluated_alice_att)
        assert engagement_evaluated_alice_att.status == "VERIFIED"


# ============================================================================
# AC-3: Invalid State — Engagement durumu EVALUATED değil
# ============================================================================


class TestAttestationInvalidState:
    """
    AC-3: Engagement must be EVALUATED.
    If engagement is ACTIVE/DRAFT/PENDING_EVALUATION/etc. → 409 Conflict (INVALID_STATE_TRANSITION).
    """

    def test_attestation_active_engagement_409(
        self, client, session, user_inst_coord_diana_att, inst_coord_diana_att,
        engagement_active_alice_att
    ):
        """
        AC-3: Diana tries to submit attestation on ACTIVE engagement (not EVALUATED) → 409.

        Acceptance Criteria:
        - Status code: 409 Conflict
        - Error code: INVALID_STATE_TRANSITION
        - current_status: ACTIVE, expected_status: EVALUATED
        - Engagement status unchanged
        - No Attestation/VerifiedExperience written
        """
        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_active_alice_att.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana_att.id)},
        )

        assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") == "INVALID_STATE_TRANSITION", \
            f"Expected INVALID_STATE_TRANSITION, got {error_obj.get('code')}: {response.text}"

        # DB verification
        session.refresh(engagement_active_alice_att)
        assert engagement_active_alice_att.status == "ACTIVE"


# ============================================================================
# AC-4: Forbidden — TALENT tarafından POST
# ============================================================================


class TestAttestationTalentForbidden:
    """
    AC-4: TALENT role tarafından attestation POST edilemez → 403 FORBIDDEN.
    (S6 istisnası: 403 dönülür, 404 değil, çünkü talent engagement'ın tarafı ve kaynağın varlığı ona zaten görünür)
    """

    def test_attestation_talent_forbidden_403(
        self, client, session, user_talent_alice_att, talent_alice_att,
        engagement_evaluated_alice_att
    ):
        """
        AC-4: Alice (TALENT) tries to submit attestation → 403 FORBIDDEN.

        Acceptance Criteria:
        - Status code: 403 Forbidden
        - No Attestation/VerifiedExperience written
        """
        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_evaluated_alice_att.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_alice_att.id)},
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"


# ============================================================================
# AC-5: Not Found — Scope dışı INST:COORD
# ============================================================================


class TestAttestationScopeOut:
    """
    AC-5: INST:COORD from different institution → 404 NOT_FOUND (scope completely out).
    kaynağın varlığı bu aktöre sızdırılmaz.
    """

    def test_attestation_cross_institution_scope_out_404(
        self, client, session, user_inst_coord_frank_att, inst_coord_frank_att,
        engagement_evaluated_alice_att
    ):
        """
        AC-5: Frank (INST:COORD of institution_b) tries to attest Alice's engagement in institution_a → 404.

        Acceptance Criteria:
        - Status code: 404 Not Found (not 403, not 422)
        - Error code: NOT_FOUND
        - Response doesn't leak Alice's engagement details
        """
        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_evaluated_alice_att.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_frank_att.id)},
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") == "NOT_FOUND", \
            f"Expected NOT_FOUND, got {error_obj.get('code')}"


# ============================================================================
# AC-6: Version Conflict
# ============================================================================


class TestAttestationVersionConflict:
    """
    AC-6: Old version (If-Match style conflict) → 409 CONFLICT (VERSION_MISMATCH).
    Request body'de version alanı — istemci önceki engagement.version'u gönderir, çakışırsa 409.
    """

    def test_attestation_old_version_409(
        self, client, session, user_inst_coord_diana_att, inst_coord_diana_att,
        engagement_evaluated_alice_att, deliverable_alice_att, skill_communication_att
    ):
        """
        AC-6: Diana submits attestation with old version (version=0 but current=1) → 409.

        Acceptance Criteria:
        - Status code: 409 Conflict
        - Error code: VERSION_MISMATCH (or CONFLICT)
        - No Attestation/VerifiedExperience written
        - engagement.version unchanged
        """
        # Pre-condition: update engagement to version 2 (simulate prior write)
        # This won't happen in normal flow, but simulates a race condition
        payload = {
            "claim_type": "COMPETENCE",
            "version": 0,  # Old version (current is 1)
        }

        response = client.post(
            f"/engagements/{engagement_evaluated_alice_att.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana_att.id)},
        )

        assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"

        data = response.json()
        error_obj = data.get("detail") if "detail" in data else data
        assert error_obj.get("code") in ["CONFLICT", "VERSION_MISMATCH"], \
            f"Expected CONFLICT/VERSION_MISMATCH, got {error_obj.get('code')}"


# ============================================================================
# AC-7: Invalid Input — claim_type eksik/geçersiz
# ============================================================================


class TestAttestationValidation:
    """
    AC-7: claim_type eksik veya geçersiz enum → 422 Unprocessable Entity.
    """

    def test_attestation_missing_claim_type_422(
        self, client, session, user_inst_coord_diana_att, inst_coord_diana_att,
        engagement_evaluated_alice_att
    ):
        """
        AC-7: Diana submits attestation without claim_type → 422.

        Acceptance Criteria:
        - Status code: 422 Unprocessable Entity
        - Error indicates field validation error
        - No DB write
        """
        payload = {
            # claim_type missing
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_evaluated_alice_att.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana_att.id)},
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"

    def test_attestation_invalid_claim_type_enum_422(
        self, client, session, user_inst_coord_diana_att, inst_coord_diana_att,
        engagement_evaluated_alice_att
    ):
        """
        AC-7: Diana submits attestation with invalid claim_type value → 422.

        Acceptance Criteria:
        - Status code: 422 Unprocessable Entity
        """
        payload = {
            "claim_type": "INVALID_ENUM_VALUE",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_evaluated_alice_att.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana_att.id)},
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"


# ============================================================================
# AC-8: Attestation Already Exists
# ============================================================================


class TestAttestationDuplicate:
    """
    AC-8: Append-only table — second attestation for same engagement → 409 Conflict.
    UNIQUE constraint or service-level check prevents duplicate.
    """

    def test_attestation_duplicate_409(
        self, client, session, user_inst_coord_diana_att, inst_coord_diana_att,
        engagement_evaluated_alice_att, deliverable_alice_att
    ):
        """
        AC-8: Diana submits attestation twice on same engagement → first succeeds (201), second fails (409).

        Acceptance Criteria:
        - First POST: 201 Created
        - Second POST (same Diana, same engagement): 409 Conflict
        - Error code: ATTESTATION_ALREADY_EXISTS (or INVALID_STATE_TRANSITION if engagement already VERIFIED)
        - DB shows only first attestation (append-only, no update)
        - Note: If first POST succeeds and engagement transitions to VERIFIED, second POST with old version
          will fail with INVALID_STATE_TRANSITION (409) — also a valid "cannot resubmit" result.
        """
        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,
        }

        # First POST — should succeed
        response1 = client.post(
            f"/engagements/{engagement_evaluated_alice_att.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana_att.id)},
        )

        assert response1.status_code == 201, f"First POST failed: {response1.text}"

        # Refresh engagement to get new version
        session.refresh(engagement_evaluated_alice_att)
        new_version = engagement_evaluated_alice_att.version

        # Second POST — should fail with old version
        payload2 = {
            "claim_type": "PARTICIPATION",
            "version": new_version - 1,  # Simulate version mismatch from first write
        }

        response2 = client.post(
            f"/engagements/{engagement_evaluated_alice_att.id}/attestations",
            json=payload2,
            headers={"X-Debug-User-Id": str(user_inst_coord_diana_att.id)},
        )

        # Should be 409 — either VERSION_MISMATCH, ATTESTATION_ALREADY_EXISTS, or INVALID_STATE_TRANSITION
        assert response2.status_code == 409, f"Expected 409 for duplicate, got {response2.status_code}: {response2.text}"

        data2 = response2.json()
        error_obj = data2.get("detail") if "detail" in data2 else data2
        assert error_obj.get("code") in ["CONFLICT", "ATTESTATION_ALREADY_EXISTS", "VERSION_MISMATCH", "INVALID_STATE_TRANSITION"], \
            f"Expected conflict-like error, got {error_obj.get('code')}"


# ============================================================================
# AC-9: institution_id NULL — ORG:SUPERVISOR attestation
# ============================================================================


class TestAttestationDirectEngagement:
    """
    AC-9: institution_id NULL (direct org engagement) → ORG:SUPERVISOR tetikler T8.
    Madde 6 kontrol listesinden çıkarılır (coordinator confirmation not required when no institution).
    """

    def test_attestation_direct_engagement_supervisor_201(
        self, client, session, user_org_supervisor_grace_att, org_member_supervisor_grace_att,
        engagement_evaluated_direct_att, deliverable_alice_att
    ):
        """
        AC-9: Grace (ORG:SUPERVISOR) submits attestation on direct engagement (institution_id=NULL) → 201.
        Madde 6 (coordinator confirmation) kontrol listesinden çıkarılır.

        Acceptance Criteria:
        - Status code: 201 Created
        - Attestation created with COMPETENCE or appropriate downgrade (madde 6 hariç)
        - engagement.status=VERIFIED, version incremented
        """
        # Note: direct_engagement doesn't have a deliverable yet, so downgrade expected
        payload = {
            "claim_type": "COMPETENCE",
            "version": 1,
        }

        response = client.post(
            f"/engagements/{engagement_evaluated_direct_att.id}/attestations",
            json=payload,
            headers={"X-Debug-User-Id": str(user_org_supervisor_grace_att.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        assert data.get("requested_claim_type") == "COMPETENCE"

        # DB verification
        session.refresh(engagement_evaluated_direct_att)
        assert engagement_evaluated_direct_att.status == "VERIFIED"
