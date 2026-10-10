"""
PLAN 3.54 (faz 1): attestation.fraud_check_requested outbox handler.

AI never writes to attestations and never decides anything — it only may
insert a PENDING fraud_flags row that an admin later confirms/dismisses
(app/services/fraud_flag.py, app/api/admin.py). These tests run the real
handler against the rolled-back test transaction (same pattern as
tests/test_evidence_scan.py's handler_env) with a fake httpx.post — no real
network call, no real OpenRouter key needed.
"""

import uuid

import pytest
import sqlalchemy
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Attestation, Engagement, FraudFlag, Organization, TalentProfile, User
from app.workers import outbox_worker


@pytest.fixture
def handler_env(session, monkeypatch):
    """Redirect the handler's own engine/sessions onto the rolled-back test connection."""

    class _Engine:
        def dispose(self) -> None:
            pass

    bind = session.get_bind()
    monkeypatch.setattr(sqlalchemy, "create_engine", lambda *a, **k: _Engine())
    monkeypatch.setattr(
        outbox_worker,
        "Session",
        lambda engine: Session(bind=bind, join_transaction_mode="create_savepoint"),
    )
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(settings, "openrouter_model", "anthropic/claude-haiku-4.5")
    return None


class _FakeHttpError(Exception):
    pass


def _install_fake_openrouter(monkeypatch, body: dict | None = None, status_code: int = 200, exc: Exception | None = None):
    calls: list[dict] = []

    class _Response:
        def __init__(self, status_code, body):
            self.status_code = status_code
            self._body = body

        def raise_for_status(self):
            if self.status_code >= 400:
                raise _FakeHttpError(f"status={self.status_code}")

        def json(self):
            return self._body

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json})
        if exc is not None:
            raise exc
        return _Response(status_code, body)

    monkeypatch.setattr("httpx.post", fake_post)
    return calls


def _chat_response(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


@pytest.fixture
def user_att_handler(session):
    user = User(email="coord.fraudtest@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent_att_handler(session):
    user = User(email="talent.fraudtest@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    profile = TalentProfile(user_id=user.id, full_name="Fraud Test Talent", visibility="PRIVATE")
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def org_att_handler(session):
    org = Organization(name="Fraud Test Org", verification_level="T2")
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def engagement_att_handler(session, talent_att_handler, org_att_handler):
    engagement = Engagement(
        talent_id=talent_att_handler.id,
        organization_id=org_att_handler.id,
        kind="INTERNSHIP",
        title="Fraud test engagement",
        status="VERIFIED",
        version=2,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def attestation_with_statement(session, engagement_att_handler, talent_att_handler, user_att_handler):
    att = Attestation(
        engagement_id=engagement_att_handler.id,
        talent_id=talent_att_handler.id,
        subject_type="ENGAGEMENT",
        subject_id=engagement_att_handler.id,
        claim_type="COMPETENCE",
        requested_claim_type="COMPETENCE",
        attestor_user_id=user_att_handler.id,
        statement="Bu kişi projeyi gerçekten kendi başına teslim etti.",
    )
    session.add(att)
    session.flush()
    return att


class TestHandlerRegistration:
    def test_handler_is_registered_for_the_topic(self):
        assert outbox_worker.DEFAULT_HANDLERS["attestation.fraud_check_requested"] is (
            outbox_worker.attestation_fraud_check_handler
        )


class TestFraudCheckHandler:
    def test_missing_api_key_is_noop(self, session, attestation_with_statement, handler_env, monkeypatch):
        monkeypatch.setattr(settings, "openrouter_api_key", "")
        calls = _install_fake_openrouter(monkeypatch, body=_chat_response('{"is_suspicious": true}'))

        outbox_worker.attestation_fraud_check_handler(
            {"attestation_id": str(attestation_with_statement.id)}, outbox_id=1
        )

        assert calls == []
        assert session.query(FraudFlag).count() == 0

    def test_unknown_attestation_is_noop(self, handler_env, monkeypatch):
        calls = _install_fake_openrouter(monkeypatch, body=_chat_response('{"is_suspicious": true}'))

        outbox_worker.attestation_fraud_check_handler({"attestation_id": str(uuid.uuid4())}, outbox_id=1)

        assert calls == []

    def test_suspicious_statement_creates_pending_fraud_flag(
        self, session, attestation_with_statement, handler_env, monkeypatch
    ):
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response('{"is_suspicious": true, "confidence": "HIGH", "reason": "Şablon ifade"}'),
        )

        outbox_worker.attestation_fraud_check_handler(
            {"attestation_id": str(attestation_with_statement.id)}, outbox_id=1
        )

        flag = session.query(FraudFlag).filter_by(subject_id=attestation_with_statement.id).one()
        assert flag.subject_type == "ATTESTATION"
        assert flag.status == "PENDING"
        assert flag.confidence == "HIGH"
        assert flag.reason == "Şablon ifade"
        assert flag.model == "anthropic/claude-haiku-4.5"

    def test_non_suspicious_statement_creates_no_flag(
        self, session, attestation_with_statement, handler_env, monkeypatch
    ):
        _install_fake_openrouter(monkeypatch, body=_chat_response('{"is_suspicious": false}'))

        outbox_worker.attestation_fraud_check_handler(
            {"attestation_id": str(attestation_with_statement.id)}, outbox_id=1
        )

        assert session.query(FraudFlag).count() == 0

    def test_malformed_model_output_is_noop_not_error(
        self, session, attestation_with_statement, handler_env, monkeypatch
    ):
        """Model JSON yerine düz metin dönerse: hata fırlatılmaz (retry yok), flag da oluşmaz."""
        _install_fake_openrouter(monkeypatch, body=_chat_response("hayır bu şüpheli değil"))

        outbox_worker.attestation_fraud_check_handler(
            {"attestation_id": str(attestation_with_statement.id)}, outbox_id=1
        )

        assert session.query(FraudFlag).count() == 0

    def test_http_error_propagates_so_outbox_retries(
        self, session, attestation_with_statement, handler_env, monkeypatch
    ):
        _install_fake_openrouter(monkeypatch, status_code=500, body=_chat_response(""))

        with pytest.raises(Exception):
            outbox_worker.attestation_fraud_check_handler(
                {"attestation_id": str(attestation_with_statement.id)}, outbox_id=1
            )

        assert session.query(FraudFlag).count() == 0
