"""
PLAN 3.56: fraud risk signals — suspicious organizations, colluding/fake
attestations, suspicious institution approvals.

The rules are deterministic (no model) and never decide anything: they only
insert PENDING fraud_flags rows for the admin queue. The single AI call
(organization identity check) receives organization-level data only.

Handlers run against the rolled-back test transaction with a fake httpx.post
(same pattern as tests/test_fraud_flag_handler.py) — no real network.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    Attestation,
    AuditEvent,
    Engagement,
    FraudFlag,
    Institution,
    Organization,
    OrganizationMember,
    Outbox,
    TalentProfile,
    User,
)
from app.services import fraud_signals
from app.services.organization import create_organization
from app.workers import outbox_worker

NOW = datetime.now(timezone.utc)
LONG_STATEMENT = "Öğrenci staj süresince verilen tüm görevleri zamanında ve eksiksiz teslim etti."


def _user(session, email: str) -> User:
    user = User(email=email, password_hash="hash")
    session.add(user)
    session.flush()
    return user


def _talent(session, email: str) -> TalentProfile:
    profile = TalentProfile(user_id=_user(session, email).id, full_name="Sinyal Test Öğrenci", visibility="PRIVATE")
    session.add(profile)
    session.flush()
    return profile


def _org(session, level: str = "T2", age: timedelta = timedelta(days=90), name: str = "Sinyal Test A.Ş.") -> Organization:
    org = Organization(name=name, verification_level=level, created_at=NOW - age)
    session.add(org)
    session.flush()
    return org


def _institution(session) -> Institution:
    institution = Institution(name=f"Sinyal Üniversitesi {uuid.uuid4().hex[:6]}")
    session.add(institution)
    session.flush()
    return institution


def _engagement(session, talent, org, institution=None, age: timedelta = timedelta(days=30)) -> Engagement:
    engagement = Engagement(
        talent_id=talent.id,
        organization_id=org.id,
        institution_id=institution.id if institution else None,
        kind="INTERNSHIP",
        title="Sinyal test çalışması",
        status="VERIFIED",
        version=2,
        created_at=NOW - age,
    )
    session.add(engagement)
    session.flush()
    return engagement


def _attestation(session, engagement, attestor, statement=None, org=None, age: timedelta = timedelta(0)) -> Attestation:
    attestation = Attestation(
        engagement_id=engagement.id,
        talent_id=engagement.talent_id,
        subject_type="ENGAGEMENT",
        subject_id=engagement.id,
        claim_type="COMPETENCE",
        requested_claim_type="COMPETENCE",
        attestor_user_id=attestor.id,
        attestor_org_id=org.id if org else None,
        statement=statement,
        created_at=NOW - age,
    )
    session.add(attestation)
    session.flush()
    return attestation


def _codes(signals) -> set[str]:
    return {signal.signal for signal in signals}


def _attested_engagements(session, org, count: int, same_talent: bool = False, age: timedelta = timedelta(0)):
    """`count` attested engagements at `org`, each with its own witness."""
    shared = _talent(session, f"ortak-{uuid.uuid4().hex[:8]}@uni.example.edu.tr") if same_talent else None
    for _ in range(count):
        talent = shared or _talent(session, f"ogr-{uuid.uuid4().hex[:8]}@uni.example.edu.tr")
        witness = _user(session, f"tanik-{uuid.uuid4().hex[:8]}@firma.example.com")
        _attestation(session, _engagement(session, talent, org), witness, age=age)


class TestAttestationSignals:
    def test_ordinary_attestation_raises_nothing(self, session):
        talent = _talent(session, "ayse@uni.example.edu.tr")
        witness = _user(session, "mentor@firma.example.com")
        attestation = _attestation(session, _engagement(session, talent, _org(session)), witness, LONG_STATEMENT)

        assert fraud_signals.attestation_signals(session, attestation.id) == []

    def test_unknown_attestation_raises_nothing(self, session):
        assert fraud_signals.attestation_signals(session, uuid.uuid4()) == []

    def test_witness_is_the_talents_own_account(self, session):
        talent = _talent(session, "ayse@uni.example.edu.tr")
        own_user = session.get(User, talent.user_id)
        attestation = _attestation(session, _engagement(session, talent, _org(session)), own_user)

        signals = fraud_signals.attestation_signals(session, attestation.id)

        assert _codes(signals) == {"SELF_ATTESTATION"}
        assert signals[0].confidence == "HIGH"
        assert signals[0].subject_type == "ATTESTATION" and signals[0].subject_id == attestation.id

    def test_witness_and_talent_share_a_private_email_domain(self, session):
        talent = _talent(session, "ogrenci@ortak-alan.example.com")
        witness = _user(session, "tanik@ortak-alan.example.com")
        attestation = _attestation(session, _engagement(session, talent, _org(session)), witness)

        signals = fraud_signals.attestation_signals(session, attestation.id)

        assert _codes(signals) == {"SHARED_EMAIL_DOMAIN"}
        assert "@" not in signals[0].reason and "ortak-alan" not in signals[0].reason  # no PII in the reason

    def test_shared_free_mail_provider_is_not_a_signal(self, session):
        talent = _talent(session, "ogrenci.sinyal@gmail.com")
        witness = _user(session, "tanik.sinyal@gmail.com")
        attestation = _attestation(session, _engagement(session, talent, _org(session)), witness)

        assert fraud_signals.attestation_signals(session, attestation.id) == []

    def test_same_statement_reused_for_another_talent(self, session):
        org = _org(session)
        witness = _user(session, "mentor@firma.example.com")
        first = _talent(session, "bir@uni.example.edu.tr")
        second = _talent(session, "iki@uni.example.edu.tr")
        _attestation(session, _engagement(session, first, org), witness, LONG_STATEMENT)
        attestation = _attestation(session, _engagement(session, second, org), witness, f"  {LONG_STATEMENT} \n")

        signals = fraud_signals.attestation_signals(session, attestation.id)

        assert _codes(signals) == {"DUPLICATE_STATEMENT"}
        assert LONG_STATEMENT not in signals[0].reason  # statement text never copied into the reason

    def test_same_statement_for_the_same_talent_is_not_a_signal(self, session):
        org = _org(session)
        witness = _user(session, "mentor@firma.example.com")
        talent = _talent(session, "bir@uni.example.edu.tr")
        _attestation(session, _engagement(session, talent, org), witness, LONG_STATEMENT)
        attestation = _attestation(session, _engagement(session, talent, org), witness, LONG_STATEMENT)

        assert fraud_signals.attestation_signals(session, attestation.id) == []

    def test_short_generic_statement_is_not_compared(self, session):
        org = _org(session)
        witness = _user(session, "mentor@firma.example.com")
        _attestation(session, _engagement(session, _talent(session, "bir@uni.example.edu.tr"), org), witness, "Başarılı.")
        attestation = _attestation(
            session, _engagement(session, _talent(session, "iki@uni.example.edu.tr"), org), witness, "Başarılı."
        )

        assert fraud_signals.attestation_signals(session, attestation.id) == []

    def test_attested_minutes_after_the_engagement_was_created(self, session):
        talent = _talent(session, "ayse@uni.example.edu.tr")
        witness = _user(session, "mentor@firma.example.com")
        engagement = _engagement(session, talent, _org(session), age=timedelta(minutes=12))
        attestation = _attestation(session, engagement, witness)

        signals = fraud_signals.attestation_signals(session, attestation.id)

        assert _codes(signals) == {"RAPID_VERIFICATION"}
        assert "12 dakika" in signals[0].reason


class TestOrganizationSignals:
    def test_established_verified_organization_raises_nothing(self, session):
        org = _org(session, level="T2")
        _attested_engagements(session, org, 6)

        assert fraud_signals.organization_signals(session, org.id) == []

    def test_unknown_organization_raises_nothing(self, session):
        assert fraud_signals.organization_signals(session, uuid.uuid4()) == []

    def test_unverified_organization_with_high_recent_volume(self, session):
        org = _org(session, level="T1")
        _attested_engagements(session, org, fraud_signals.ORG_VOLUME_THRESHOLD)

        signals = fraud_signals.organization_signals(session, org.id)

        assert _codes(signals) == {"UNVERIFIED_HIGH_VOLUME"}
        assert signals[0].subject_type == "ORGANIZATION" and signals[0].subject_id == org.id

    def test_unverified_organization_below_threshold_or_old_volume(self, session):
        below = _org(session, level="T1")
        _attested_engagements(session, below, fraud_signals.ORG_VOLUME_THRESHOLD - 1)
        old = _org(session, level="T1", name="Eski Hacim Ltd.")
        _attested_engagements(session, old, fraud_signals.ORG_VOLUME_THRESHOLD, age=timedelta(days=20))

        assert fraud_signals.organization_signals(session, below.id) == []
        assert fraud_signals.organization_signals(session, old.id) == []

    def test_brand_new_organization_already_attested_several_times(self, session):
        org = _org(session, level="T2", age=timedelta(days=1))
        _attested_engagements(session, org, fraud_signals.NEW_ORG_BURST_THRESHOLD)

        signals = fraud_signals.organization_signals(session, org.id)

        assert _codes(signals) == {"NEW_ORG_BURST"}
        assert signals[0].confidence == "HIGH"

    def test_all_attested_engagements_belong_to_one_talent(self, session):
        org = _org(session, level="T2")
        _attested_engagements(session, org, fraud_signals.SINGLE_TALENT_THRESHOLD, same_talent=True)

        assert _codes(fraud_signals.organization_signals(session, org.id)) == {"SINGLE_TALENT_ONLY"}

    def test_coordinator_witness_still_counts_towards_the_organization(self, session):
        """The witness is the institution's coordinator (attestor_org_id NULL) —
        the organization is still the one being vouched for."""
        org = _org(session, level="T1")
        _attested_engagements(session, org, fraud_signals.ORG_VOLUME_THRESHOLD)
        assert session.query(Attestation).filter(Attestation.attestor_org_id.isnot(None)).count() == 0

        assert "UNVERIFIED_HIGH_VOLUME" in _codes(fraud_signals.organization_signals(session, org.id))


class TestInstitutionApprovalSignals:
    @staticmethod
    def _approval(session, coordinator, engagement, age: timedelta = timedelta(0)) -> None:
        session.add(
            AuditEvent(
                actor_user_id=coordinator.id,
                action="ENGAGEMENT_TRANSITIONED",
                subject_type="engagement",
                subject_id=engagement.id,
                result="SUCCESS",
                event_metadata={"from_status": "PENDING_APPROVAL", "to_status": "ACTIVE"},
                created_at=NOW - age,
            )
        )
        session.flush()

    def test_single_ordinary_approval_raises_nothing(self, session):
        institution, org = _institution(session), _org(session)
        coordinator = _user(session, "koordinator@uni.example.edu.tr")
        engagement = _engagement(session, _talent(session, "ayse@uni.example.edu.tr"), org, institution)
        self._approval(session, coordinator, engagement)

        assert fraud_signals.institution_approval_signals(session, engagement.id, coordinator.id) == []

    def test_engagement_without_institution_raises_nothing(self, session):
        coordinator = _user(session, "koordinator@uni.example.edu.tr")
        engagement = _engagement(session, _talent(session, "ayse@uni.example.edu.tr"), _org(session))

        assert fraud_signals.institution_approval_signals(session, engagement.id, coordinator.id) == []

    def test_approver_is_a_member_of_the_engagements_organization(self, session):
        institution, org = _institution(session), _org(session)
        coordinator = _user(session, "koordinator@uni.example.edu.tr")
        session.add(OrganizationMember(organization_id=org.id, user_id=coordinator.id, role="MEMBER", status="ACTIVE"))
        engagement = _engagement(session, _talent(session, "ayse@uni.example.edu.tr"), org, institution)

        signals = fraud_signals.institution_approval_signals(session, engagement.id, coordinator.id)

        assert _codes(signals) == {"APPROVER_IS_ORG_MEMBER"}
        assert signals[0].subject_type == "INSTITUTION" and signals[0].subject_id == institution.id
        assert signals[0].confidence == "HIGH"

    def test_many_engagements_of_one_organization_approved_in_minutes(self, session):
        institution, org = _institution(session), _org(session)
        coordinator = _user(session, "koordinator@uni.example.edu.tr")
        engagements = [
            _engagement(session, _talent(session, f"ogr{i}@uni.example.edu.tr"), org, institution)
            for i in range(fraud_signals.BULK_APPROVAL_THRESHOLD)
        ]
        for engagement in engagements:
            self._approval(session, coordinator, engagement, age=timedelta(minutes=2))

        signals = fraud_signals.institution_approval_signals(session, engagements[-1].id, coordinator.id)

        assert _codes(signals) == {"RAPID_BULK_APPROVAL"}

    def test_approvals_spread_out_or_for_other_organizations_do_not_count(self, session):
        institution, org, other_org = _institution(session), _org(session), _org(session, name="Başka Ltd.")
        coordinator = _user(session, "koordinator@uni.example.edu.tr")
        target = _engagement(session, _talent(session, "hedef@uni.example.edu.tr"), org, institution)
        self._approval(session, coordinator, target)
        for i in range(fraud_signals.BULK_APPROVAL_THRESHOLD):
            old = _engagement(session, _talent(session, f"eski{i}@uni.example.edu.tr"), org, institution)
            self._approval(session, coordinator, old, age=timedelta(hours=3))
            other = _engagement(session, _talent(session, f"diger{i}@uni.example.edu.tr"), other_org, institution)
            self._approval(session, coordinator, other)

        assert fraud_signals.institution_approval_signals(session, target.id, coordinator.id) == []


class TestRecordSignals:
    @staticmethod
    def _signal(subject_id) -> fraud_signals.RiskSignal:
        return fraud_signals.RiskSignal("ORGANIZATION", subject_id, "NEW_ORG_BURST", "HIGH", "gerekçe")

    def test_new_signal_becomes_a_pending_flag_marked_as_rule_output(self, session):
        org = _org(session)

        assert fraud_signals.record_signals(session, [self._signal(org.id)]) == 1

        flag = session.query(FraudFlag).filter_by(subject_id=org.id).one()
        assert (flag.subject_type, flag.signal, flag.status) == ("ORGANIZATION", "NEW_ORG_BURST", "PENDING")
        assert flag.model == fraud_signals.RULES_MODEL
        assert flag.reviewed_by_user_id is None  # nothing is decided automatically

    def test_same_signal_is_not_queued_twice(self, session):
        org = _org(session)
        fraud_signals.record_signals(session, [self._signal(org.id)])

        assert fraud_signals.record_signals(session, [self._signal(org.id)]) == 0
        assert session.query(FraudFlag).filter_by(subject_id=org.id).count() == 1

    def test_recently_dismissed_signal_is_not_raised_again(self, session):
        org = _org(session)
        fraud_signals.record_signals(session, [self._signal(org.id)])
        session.query(FraudFlag).filter_by(subject_id=org.id).one().status = "DISMISSED"
        session.flush()

        assert fraud_signals.record_signals(session, [self._signal(org.id)]) == 0

    def test_signal_reviewed_long_ago_can_be_raised_again(self, session):
        org = _org(session)
        session.add(
            FraudFlag(
                subject_type="ORGANIZATION",
                subject_id=org.id,
                signal="NEW_ORG_BURST",
                reason="eski",
                confidence="HIGH",
                model=fraud_signals.RULES_MODEL,
                status="DISMISSED",
                created_at=NOW - fraud_signals.REFLAG_COOLDOWN - timedelta(days=1),
            )
        )
        session.flush()

        assert fraud_signals.record_signals(session, [self._signal(org.id)]) == 1

    def test_different_signal_on_the_same_subject_is_its_own_row(self, session):
        org = _org(session)
        other = fraud_signals.RiskSignal("ORGANIZATION", org.id, "SINGLE_TALENT_ONLY", "LOW", "gerekçe")

        assert fraud_signals.record_signals(session, [self._signal(org.id), other]) == 2


@pytest.fixture
def handler_env(session, monkeypatch):
    """Redirect the handler's own engine/sessions onto the rolled-back test connection."""

    class _Engine:
        def dispose(self) -> None:
            pass

    bind = session.get_bind()
    monkeypatch.setattr(sqlalchemy, "create_engine", lambda *a, **k: _Engine())
    monkeypatch.setattr(
        outbox_worker, "Session", lambda engine: Session(bind=bind, join_transaction_mode="create_savepoint")
    )
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    monkeypatch.setattr(settings, "openrouter_model", "anthropic/claude-haiku-4.5")


def _install_fake_openrouter(monkeypatch, content: str):
    calls: list[dict] = []

    class _Response:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {"choices": [{"message": {"content": content}}]}

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "json": json})
        return _Response()

    monkeypatch.setattr("httpx.post", fake_post)
    return calls


class TestRuleHandlers:
    def test_handlers_are_registered(self):
        handlers = outbox_worker.DEFAULT_HANDLERS
        assert handlers["fraud.attestation_risk_scan_requested"] is outbox_worker.fraud_attestation_risk_scan_handler
        assert handlers["fraud.approval_risk_scan_requested"] is outbox_worker.fraud_approval_risk_scan_handler
        assert (
            handlers["fraud.organization_identity_check_requested"]
            is outbox_worker.organization_identity_check_handler
        )

    def test_attestation_scan_flags_attestation_and_organization_without_any_ai(self, session, handler_env, monkeypatch):
        monkeypatch.setattr("httpx.post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no network")))
        org = _org(session, level="T2", age=timedelta(days=1))
        _attested_engagements(session, org, fraud_signals.NEW_ORG_BURST_THRESHOLD - 1)
        talent = _talent(session, "ayse@uni.example.edu.tr")
        witness = _user(session, "mentor@firma.example.com")
        attestation = _attestation(session, _engagement(session, talent, org, age=timedelta(minutes=5)), witness)

        outbox_worker.fraud_attestation_risk_scan_handler({"attestation_id": str(attestation.id)}, 1)

        flags = {(f.subject_type, f.signal): f for f in session.query(FraudFlag).all()}
        assert set(flags) == {("ATTESTATION", "RAPID_VERIFICATION"), ("ORGANIZATION", "NEW_ORG_BURST")}
        assert flags[("ORGANIZATION", "NEW_ORG_BURST")].subject_id == org.id
        assert all(f.status == "PENDING" and f.model == fraud_signals.RULES_MODEL for f in flags.values())
        audit = session.query(AuditEvent).filter_by(action="fraud_flag.created", subject_id=attestation.id).one()
        assert audit.event_metadata["signals"] == ["NEW_ORG_BURST", "RAPID_VERIFICATION"]

    def test_attestation_scan_is_idempotent_on_redelivery(self, session, handler_env):
        talent = _talent(session, "ayse@uni.example.edu.tr")
        witness = _user(session, "mentor@firma.example.com")
        attestation = _attestation(session, _engagement(session, talent, _org(session), age=timedelta(minutes=5)), witness)
        payload = {"attestation_id": str(attestation.id)}

        outbox_worker.fraud_attestation_risk_scan_handler(payload, 1)
        outbox_worker.fraud_attestation_risk_scan_handler(payload, 1)

        assert session.query(FraudFlag).count() == 1
        assert session.query(AuditEvent).filter_by(action="fraud_flag.created").count() == 1

    def test_clean_attestation_and_unknown_id_create_nothing(self, session, handler_env):
        talent = _talent(session, "ayse@uni.example.edu.tr")
        witness = _user(session, "mentor@firma.example.com")
        attestation = _attestation(session, _engagement(session, talent, _org(session)), witness)

        outbox_worker.fraud_attestation_risk_scan_handler({"attestation_id": str(attestation.id)}, 1)
        outbox_worker.fraud_attestation_risk_scan_handler({"attestation_id": str(uuid.uuid4())}, 1)

        assert session.query(FraudFlag).count() == 0
        assert session.query(AuditEvent).filter_by(action="fraud_flag.created").count() == 0

    def test_approval_scan_flags_the_institution(self, session, handler_env):
        institution, org = _institution(session), _org(session)
        coordinator = _user(session, "koordinator@uni.example.edu.tr")
        session.add(OrganizationMember(organization_id=org.id, user_id=coordinator.id, role="ADMIN", status="ACTIVE"))
        engagement = _engagement(session, _talent(session, "ayse@uni.example.edu.tr"), org, institution)

        outbox_worker.fraud_approval_risk_scan_handler(
            {"engagement_id": str(engagement.id), "approver_user_id": str(coordinator.id)}, 1
        )

        flag = session.query(FraudFlag).one()
        assert (flag.subject_type, flag.subject_id, flag.signal) == (
            "INSTITUTION",
            institution.id,
            "APPROVER_IS_ORG_MEMBER",
        )
        assert flag.status == "PENDING"


class TestOrganizationIdentityCheck:
    SUSPICIOUS = '{"is_suspicious": true, "confidence": "HIGH", "reason": "Ad bilinen bir markayı taklit ediyor."}'

    def test_missing_api_key_is_a_noop(self, session, handler_env, monkeypatch):
        calls = _install_fake_openrouter(monkeypatch, self.SUSPICIOUS)
        org = _org(session, level="T1")

        outbox_worker.organization_identity_check_handler({"organization_id": str(org.id)}, 1)

        assert calls == []
        assert session.query(FraudFlag).count() == 0

    def test_suspicious_identity_becomes_a_pending_flag_never_a_decision(self, session, handler_env, monkeypatch):
        monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
        _install_fake_openrouter(monkeypatch, f"```json\n{self.SUSPICIOUS}\n```")
        org = _org(session, level="T1", name="Gooogle Türkiye")

        outbox_worker.organization_identity_check_handler({"organization_id": str(org.id)}, 1)

        flag = session.query(FraudFlag).one()
        assert (flag.subject_type, flag.subject_id, flag.signal) == ("ORGANIZATION", org.id, "AI_ORG_IDENTITY")
        assert (flag.status, flag.confidence, flag.model) == ("PENDING", "HIGH", "anthropic/claude-haiku-4.5")
        session.refresh(org)
        assert (org.status, org.verification_level) == ("ACTIVE", "T1")  # AI changed nothing on the organization

    def test_only_organization_level_data_is_sent(self, session, handler_env, monkeypatch):
        monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
        calls = _install_fake_openrouter(monkeypatch, '{"is_suspicious": false, "confidence": "LOW", "reason": ""}')
        owner = _user(session, "kurucu.kisi@sahte-firma.example.com")
        org = Organization(
            name="Sahte Firma", domain="sahte-firma.example.com", legal_id="1234567890", verification_level="T1"
        )
        session.add(org)
        session.flush()
        session.add(OrganizationMember(organization_id=org.id, user_id=owner.id, role="ADMIN", status="ACTIVE"))
        session.flush()

        outbox_worker.organization_identity_check_handler({"organization_id": str(org.id)}, 1)

        prompt = calls[0]["json"]["messages"][0]["content"]
        sent = json.loads(prompt.rsplit("Kuruluş verisi:\n", 1)[1])
        assert sent == {
            "name": "Sahte Firma",
            "domain": "sahte-firma.example.com",
            "domain_is_free_email_provider": False,
            "verification_level": "T1",
            "has_legal_id": True,
        }
        assert "kurucu.kisi" not in prompt and "1234567890" not in prompt
        assert session.query(FraudFlag).count() == 0  # not suspicious -> no flag

    @pytest.mark.parametrize(
        "content",
        [
            "not json at all",
            '{"confidence": "HIGH", "reason": "eksik alan"}',
            '{"is_suspicious": "true", "confidence": "HIGH", "reason": "bool değil"}',
        ],
    )
    def test_malformed_model_output_creates_no_flag(self, session, handler_env, monkeypatch, content):
        monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
        _install_fake_openrouter(monkeypatch, content)
        org = _org(session, level="T1")

        outbox_worker.organization_identity_check_handler({"organization_id": str(org.id)}, 1)

        assert session.query(FraudFlag).count() == 0

    def test_unexpected_confidence_is_stored_as_low(self, session, handler_env, monkeypatch):
        monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
        _install_fake_openrouter(monkeypatch, '{"is_suspicious": true, "confidence": "CERTAIN", "reason": "x"}')
        org = _org(session, level="T1")

        outbox_worker.organization_identity_check_handler({"organization_id": str(org.id)}, 1)

        assert session.query(FraudFlag).one().confidence == "LOW"

    def test_unknown_or_deleted_organization_is_never_sent(self, session, handler_env, monkeypatch):
        monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
        calls = _install_fake_openrouter(monkeypatch, self.SUSPICIOUS)
        deleted = _org(session, level="T1")
        deleted.deleted_at = NOW
        session.flush()

        outbox_worker.organization_identity_check_handler({"organization_id": str(uuid.uuid4())}, 1)
        outbox_worker.organization_identity_check_handler({"organization_id": str(deleted.id)}, 1)

        assert calls == []


class TestOrganizationCreationEnqueuesIdentityCheck:
    def test_new_organization_enqueues_identity_check_with_id_only(self, session):
        creator = _user(session, "kurucu@firma.example.com")

        org = create_organization(
            name="Yeni Firma", domain=None, legal_id=None, caller_user_id=creator.id, session=session
        )

        row = session.query(Outbox).filter_by(topic="fraud.organization_identity_check_requested").one()
        assert row.payload == {"organization_id": str(org.id)}
