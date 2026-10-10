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
        assert check.page_name is None  # udemy.com allowlist'te değil — otomatik çekilmedi
        assert check.page_match is None

    def test_coursera_verify_page_is_fetched_and_compared(self, session, talent_cc, handler_env, monkeypatch):
        """PLAN 3.55b: coursera.org allowlist'te — resmi sayfadan ad çekilip
        sertifikadaki adla DETERMİNİSTİK karşılaştırılır (AI kararı değil)."""
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                '{"provider": "COURSERA", "credential_id": "ABC123", '
                '"extracted_name": "Ahmet Yılmaz", "verify_url": "https://coursera.org/verify/ABC123"}'
            ),
        )

        class _PageResponse:
            status_code = 200
            text = "<div>Completed by <strong>Ahmet Yılmaz</strong></div>"

        page_calls = []

        def fake_get(url, timeout=None, follow_redirects=None, headers=None):
            page_calls.append(url)
            return _PageResponse()

        monkeypatch.setattr("httpx.get", fake_get)

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        assert page_calls == ["https://coursera.org/verify/ABC123"]
        session.refresh(check)
        assert check.page_name == "Ahmet Yılmaz"
        assert check.page_match is True

    def test_coursera_page_name_mismatch_is_flagged_false(self, session, talent_cc, handler_env, monkeypatch):
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                '{"provider": "COURSERA", "credential_id": "ABC123", '
                '"extracted_name": "Ahmet Yılmaz", "verify_url": "https://coursera.org/verify/ABC123"}'
            ),
        )

        class _PageResponse:
            status_code = 200
            text = "<div>Completed by <strong>Başka Bir İsim</strong></div>"

        monkeypatch.setattr("httpx.get", lambda *a, **k: _PageResponse())

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.page_name == "Başka Bir İsim"
        assert check.page_match is False

    def test_arbitrary_host_is_never_fetched_ssrf_guard(self, session, talent_cc, handler_env, monkeypatch):
        """AI'nin ürettiği verify_url'e kör güvenilmez — allowlist dışı hiçbir
        host'a istek atılmaz (SSRF/keyfi URL savunması)."""
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                '{"provider": "UNKNOWN", "credential_id": null, "extracted_name": "Ahmet Yılmaz", '
                '"verify_url": "https://internal.attacker.example/steal?x=1"}'
            ),
        )
        calls = []
        monkeypatch.setattr("httpx.get", lambda *a, **k: calls.append(a) or (_ for _ in ()).throw(AssertionError("should not fetch")))

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        assert calls == []
        session.refresh(check)
        assert check.page_name is None
        assert check.page_match is None

    def test_coursera_page_fetch_failure_does_not_fail_the_handler(self, session, talent_cc, handler_env, monkeypatch):
        """Doğrulama sayfası çekimi opsiyonel bir ek öneri — başarısız olursa
        ana çıkarım (provider/isim/kimlik no) yine DONE olarak kaydedilir."""
        ev = _evidence(session, talent_cc)
        check = _pending_check(session, ev)
        handler_env(_blank_png())
        _install_fake_openrouter(
            monkeypatch,
            body=_chat_response(
                '{"provider": "COURSERA", "credential_id": "ABC123", '
                '"extracted_name": "Ahmet Yılmaz", "verify_url": "https://coursera.org/verify/ABC123"}'
            ),
        )

        def failing_get(*a, **k):
            raise _FakeHttpError("network down")

        monkeypatch.setattr("httpx.get", failing_get)

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        session.refresh(check)
        assert check.status == "DONE"
        assert check.page_name is None
        assert check.page_match is None

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

    def test_jpeg_upload_is_reencoded_to_real_png_before_sending(self, session, talent_cc, handler_env, monkeypatch):
        """Canlı bulgu: JPEG bytes'ı ham haliyle 'image/png' etiketiyle gönderirsek
        sağlayıcı (Anthropic) 400 ile reddediyor ('declared png but is jpeg').
        Her upload gerçek PNG'ye yeniden encode edilmeli — hangi mime_type ile
        yüklendiği fark etmeksizin."""
        import base64

        image = np.full((40, 40, 3), 128, dtype=np.uint8)
        ok, jpeg_buf = cv2.imencode(".jpg", image)
        assert ok
        jpeg_bytes = bytes(jpeg_buf)

        ev = _evidence(session, talent_cc, mime="image/jpeg")
        check = _pending_check(session, ev)
        handler_env(jpeg_bytes)
        calls = _install_fake_openrouter(
            monkeypatch, body=_chat_response('{"provider": "UDEMY", "credential_id": null, "extracted_name": null, "verify_url": null}')
        )

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        assert len(calls) == 1
        content_blocks = calls[0]["json"]["messages"][0]["content"]
        image_block = next(b for b in content_blocks if b["type"] == "image_url")
        data_url = image_block["image_url"]["url"]
        assert data_url.startswith("data:image/png;base64,")
        decoded = base64.b64decode(data_url.split(",", 1)[1])
        assert decoded.startswith(b"\x89PNG\r\n\x1a\n"), "gönderilen bytes gerçek PNG imzasıyla başlamalı"

        session.refresh(check)
        assert check.status == "DONE"

    def test_undecodable_image_marks_failed_without_calling_model(self, session, talent_cc, handler_env, monkeypatch):
        ev = _evidence(session, talent_cc, mime="image/png")
        check = _pending_check(session, ev)
        handler_env(b"not a real image")
        calls = _install_fake_openrouter(monkeypatch, body=_chat_response("{}"))

        outbox_worker.certificate_check_requested_handler({"certificate_check_id": str(check.id)}, 1)

        assert calls == []
        session.refresh(check)
        assert check.status == "FAILED"
