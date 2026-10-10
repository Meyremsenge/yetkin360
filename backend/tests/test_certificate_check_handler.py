"""
PLAN 3.55: evidence.certificate_check_requested outbox handler. AI never
decides authenticity here — it only transcribes printed text (transformation,
not judgment, final-analiz §11.4.2/§39); name-match is computed by plain
string comparison in the handler, never by the model. Decision stays PENDING
until a coordinator resolves it (tests/authorization/test_certificate_check_authz.py).

Runs the real handler against the rolled-back test transaction (same pattern
as tests/test_evidence_scan.py) with fake storage + fake httpx.post — no real
network/S3.
"""

import uuid

import cv2
import numpy as np
import pytest
import sqlalchemy
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import CertificateCheck, Evidence, Organization, TalentProfile, User
from app.services.storage import StoredObject
from app.workers import outbox_worker


def _blank_png() -> bytes:
    image = np.zeros((50, 50, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".png", image)
    assert ok
    return bytes(buf)


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
        calls.append({"url": url, "json": json})
        if exc is not None:
            raise exc
        return _Response(status_code, body)

    monkeypatch.setattr("httpx.post", fake_post)
    return calls


def _chat_response(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


@pytest.fixture
def handler_env(session, monkeypatch):
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

    reads: list[tuple[str, str]] = []

    def install_storage(data, etag="etag-1"):
        def fake_fetch(bucket, key, max_bytes):
            reads.append((bucket, key))
            if isinstance(data, Exception):
                raise data
            return None if data is None else StoredObject(data=data, etag=etag)

        monkeypatch.setattr("app.services.storage.fetch_object", fake_fetch)

    return install_storage


@pytest.fixture
def talent_cc(session):
    user = User(email="cert-talent@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    profile = TalentProfile(user_id=user.id, full_name="Ahmet Yılmaz", visibility="PRIVATE")
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def org_cc(session):
    org = Organization(name="Cert Org", verification_level="T2")
    session.add(org)
    session.flush()
    return org


def _evidence(session, talent, status="CLEAN", mime="image/png") -> Evidence:
    ev = Evidence(
        owner_talent_id=talent.id,
        kind="CERTIFICATE",
        storage_key=f"evidence/{talent.id}/{uuid.uuid4()}.png",
        mime_type=mime,
        size_bytes=100,
        scan_status=status,
    )
    session.add(ev)
    session.flush()
    return ev


def _pending_check(session, evidence) -> CertificateCheck:
    check = CertificateCheck(evidence_id=evidence.id)
    session.add(check)
    session.flush()
    return check


class TestHandlerRegistration:
    def test_handler_is_registered_for_the_topic(self):
        assert (
            outbox_worker.DEFAULT_HANDLERS["evidence.certificate_check_requested"]
            is outbox_worker.certificate_check_requested_handler
        )


class TestCertificateCheckHandler:
    def test_missing_api_key_is_noop(self, session, talent_cc, handler_env, monkeypatch):
        monkeypatch.setattr(settings, "openrouter_api_key", "")
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        calls = _install_fake_openrouter(monkeypatch, body=_chat_response("{}"))
        install_storage = handler_env
        install_storage(_blank_png())

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        assert calls == []
        session.refresh(check)
        assert check.status == "PENDING"

    def test_successful_extraction_with_matching_name(self, session, talent_cc, handler_env, monkeypatch):
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                '{"provider": "UDEMY", "credential_id": "UC-123", '
                '"extracted_name": "Ahmet Yılmaz", "verify_url": "https://udemy.com/cert/UC-123"}'
            ),
        )

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.status == "DONE"
        assert check.provider == "UDEMY"
        assert check.credential_id == "UC-123"
        assert check.extracted_name == "Ahmet Yılmaz"
        assert check.name_match is True
        assert check.decision == "PENDING"  # AI never decides
        assert check.verify_url == "https://udemy.com/cert/UC-123"

    def test_name_mismatch_is_flagged_false_not_rejected(self, session, talent_cc, handler_env, monkeypatch):
        """Ad uyuşmazlığı AI'nin kararı değil — sadece name_match=False, decision PENDING kalır."""
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                '{"provider": "COURSERA", "credential_id": "XYZ", '
                '"extracted_name": "Başka Bir İsim", "verify_url": null}'
            ),
        )

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.status == "DONE"
        assert check.name_match is False
        assert check.decision == "PENDING"

    def test_qr_data_used_as_verify_url_over_model_text(self, session, talent_cc, handler_env, monkeypatch):
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        ok, qr_buf = cv2.imencode(".png", image)
        assert ok
        handler_env(bytes(qr_buf))
        monkeypatch.setattr(outbox_worker, "_decode_qr", lambda img: "https://coursera.org/verify/ABC123")
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                '{"provider": "COURSERA", "credential_id": "ABC123", '
                '"extracted_name": null, "verify_url": "https://wrong.example.com"}'
            ),
        )

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.qr_raw_data == "https://coursera.org/verify/ABC123"
        assert check.verify_url == "https://coursera.org/verify/ABC123"
        assert check.name_match is None  # extracted_name null -> unknown, not False

    def test_malformed_model_output_marks_failed_not_error(self, session, talent_cc, handler_env, monkeypatch):
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(monkeypatch, body=_chat_response("bu bir sertifika gibi görünüyor"))

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.status == "FAILED"
        assert check.decision == "PENDING"

    def test_http_error_propagates_so_outbox_retries(self, session, talent_cc, handler_env, monkeypatch):
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(monkeypatch, status_code=500, body=_chat_response(""))

        with pytest.raises(Exception):
            outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.status == "PENDING"

    def test_missing_object_marks_failed(self, session, talent_cc, handler_env, monkeypatch):
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(None)
        calls = _install_fake_openrouter(monkeypatch, body=_chat_response("{}"))

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.status == "FAILED"
        assert calls == []  # never reaches the model if the object is missing

    def test_redelivery_of_already_processed_row_is_noop(self, session, talent_cc, handler_env, monkeypatch):
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        check.status = "DONE"
        session.flush()
        calls = _install_fake_openrouter(monkeypatch, body=_chat_response("{}"))
        handler_env(_blank_png())

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        assert calls == []

    def test_unknown_check_id_is_noop(self, handler_env, monkeypatch):
        calls = _install_fake_openrouter(monkeypatch, body=_chat_response("{}"))
        handler_env(_blank_png())

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(uuid.uuid4())}, 1)

        assert calls == []
