"""
YET-195 / YET-184: evidence content inspection (magic-byte + size + content-type)
and the evidence.scan_requested outbox handler.

Pure inspection tests need no DB. The handler tests run the real handler against
the rolled-back test transaction (its short sessions are redirected onto the
test connection) with a fake storage reader — no real network / S3.
"""

import io
import uuid
import zipfile

import pytest
import sqlalchemy
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AuditEvent, Evidence
from app.services.evidence_scan import (
    MAX_DOCX_ENTRIES,
    detect_content_type,
    inspect_content,
)
from app.workers import outbox_worker

PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
EXE = b"MZ\x90\x00" + b"\x00" * 60
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in entries.items():
            z.writestr(name, content)
    return buf.getvalue()


def _docx(extra: dict[str, bytes] | None = None) -> bytes:
    entries = {"[Content_Types].xml": b"<Types/>", "word/document.xml": b"<w:document/>"}
    entries.update(extra or {})
    return _zip(entries)


class TestInspectContent:
    @pytest.mark.parametrize(
        "data,mime",
        [(PDF, "application/pdf"), (PNG, "image/png"), (JPEG, "image/jpeg"), (_docx(), DOCX_MIME)],
    )
    def test_matching_content_is_clean_with_hash(self, data, mime):
        verdict = inspect_content(data, declared_mime=mime, declared_size=len(data))
        assert verdict.status == "CLEAN"
        assert verdict.content_hash is not None and len(verdict.content_hash) == 64

    def test_missing_object_fails(self):
        assert inspect_content(None, "application/pdf", 10).reason == "object_missing"

    def test_extension_forgery_exe_declared_as_pdf_fails(self):
        verdict = inspect_content(EXE, "application/pdf", len(EXE))
        assert (verdict.status, verdict.reason) == ("FAILED", "magic_byte_unknown")

    def test_png_declared_as_pdf_fails(self):
        verdict = inspect_content(PNG, "application/pdf", len(PNG))
        assert (verdict.status, verdict.reason) == ("FAILED", "magic_byte_mismatch")

    def test_pdf_declared_as_docx_fails(self):
        verdict = inspect_content(PDF, DOCX_MIME, len(PDF))
        assert verdict.reason == "magic_byte_mismatch"

    def test_size_mismatch_fails(self):
        assert inspect_content(PDF, "application/pdf", len(PDF) + 1).reason == "size_mismatch"

    def test_over_limit_fails(self, monkeypatch):
        monkeypatch.setattr(settings, "evidence_max_size_bytes", len(PDF) - 1)
        assert inspect_content(PDF, "application/pdf", len(PDF)).reason == "size_over_limit"

    def test_disallowed_declared_mime_fails(self):
        assert inspect_content(PDF, "application/x-msdownload", len(PDF)).reason == "mime_not_allowed"

    def test_plain_zip_declared_as_docx_fails(self):
        data = _zip({"readme.txt": b"hi"})
        assert inspect_content(data, DOCX_MIME, len(data)).reason == "docx_not_word_document"

    def test_docx_with_macro_fails(self):
        data = _docx({"word/vbaProject.bin": b"\x00"})
        assert inspect_content(data, DOCX_MIME, len(data)).reason == "docx_contains_macro"

    def test_docx_with_path_traversal_entry_fails(self):
        data = _docx({"../evil.txt": b"x"})
        assert inspect_content(data, DOCX_MIME, len(data)).reason == "docx_unsafe_entry_name"

    def test_docx_too_many_entries_fails(self):
        data = _docx({f"f{i}.txt": b"" for i in range(MAX_DOCX_ENTRIES + 1)})
        assert inspect_content(data, DOCX_MIME, len(data)).reason == "docx_too_many_entries"

    def test_docx_zip_bomb_fails(self, monkeypatch):
        monkeypatch.setattr("app.services.evidence_scan.MAX_DOCX_UNCOMPRESSED_BYTES", 1000)
        data = _docx({"word/big.xml": b"a" * 5000})
        assert inspect_content(data, DOCX_MIME, len(data)).reason == "docx_uncompressed_too_large"

    def test_corrupt_zip_fails(self):
        data = b"PK\x03\x04" + b"garbage" * 10
        assert inspect_content(data, DOCX_MIME, len(data)).reason == "docx_corrupt"

    def test_detect_ignores_everything_but_leading_bytes(self):
        assert detect_content_type(b"hello") is None
        assert detect_content_type(PDF) == "application/pdf"


# ---------------------------------------------------------------------------
# Handler (real code, test transaction, fake storage)
# ---------------------------------------------------------------------------


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
    reads: list[tuple[str, str]] = []

    def install_storage(data):
        def fake_fetch(bucket, key, max_bytes):
            reads.append((bucket, key))
            if isinstance(data, Exception):
                raise data
            return data

        monkeypatch.setattr("app.services.storage.fetch_object_bytes", fake_fetch)

    return install_storage, reads


def _evidence(session, talent, mime="application/pdf", size=len(PDF), status="PENDING") -> Evidence:
    ext = {"application/pdf": "pdf", "image/png": "png"}[mime]
    ev = Evidence(
        owner_talent_id=talent.id,
        kind="DOCUMENT",
        provenance="SELF_UPLOADED",
        visibility="PRIVATE",
        scan_status=status,
        storage_key=f"evidence/{talent.id}/{uuid.uuid4()}.{ext}",
        mime_type=mime,
        size_bytes=size,
    )
    session.add(ev)
    session.flush()
    return ev


def _payload(ev: Evidence) -> dict:
    return {"evidence_id": str(ev.id), "storage_key": ev.storage_key, "bucket": settings.s3_bucket}


def _reload(session, ev: Evidence) -> Evidence:
    session.expire_all()
    return session.execute(select(Evidence).where(Evidence.id == ev.id)).scalar_one()


class TestScanHandler:
    def test_handler_is_registered_for_the_topic(self):
        assert (
            outbox_worker.DEFAULT_HANDLERS["evidence.scan_requested"]
            is outbox_worker.evidence_scan_requested_handler
        )

    def test_matching_object_becomes_clean_with_hash(self, session, talent_a, handler_env):
        install, reads = handler_env
        install(PDF)
        ev = _evidence(session, talent_a)

        outbox_worker.evidence_scan_requested_handler(_payload(ev), 1)

        got = _reload(session, ev)
        assert got.scan_status == "CLEAN"
        assert got.content_hash and len(got.content_hash) == 64
        # Location comes from the evidence row + settings, not the payload.
        assert reads == [(settings.s3_bucket, ev.storage_key)]

    def test_payload_storage_key_is_not_trusted(self, session, talent_a, talent_b, handler_env):
        install, reads = handler_env
        install(PDF)
        ev = _evidence(session, talent_a)
        payload = _payload(ev)
        payload["storage_key"] = f"evidence/{talent_b.id}/{uuid.uuid4()}.pdf"
        payload["bucket"] = "attacker-bucket"

        outbox_worker.evidence_scan_requested_handler(payload, 1)

        assert reads == [(settings.s3_bucket, ev.storage_key)]

    def test_missing_object_becomes_failed(self, session, talent_a, handler_env):
        install, _ = handler_env
        install(None)
        ev = _evidence(session, talent_a)

        outbox_worker.evidence_scan_requested_handler(_payload(ev), 1)

        assert _reload(session, ev).scan_status == "FAILED"

    def test_type_forgery_becomes_failed_and_is_audited(self, session, talent_a, handler_env):
        install, _ = handler_env
        install(EXE)
        ev = _evidence(session, talent_a, size=len(EXE))

        outbox_worker.evidence_scan_requested_handler(_payload(ev), 1)

        got = _reload(session, ev)
        assert got.scan_status == "FAILED" and got.content_hash is None
        audit = session.execute(
            select(AuditEvent).where(AuditEvent.action == "evidence.scanned", AuditEvent.subject_id == ev.id)
        ).scalar_one()
        assert audit.result == "DENIED"
        assert audit.event_metadata == {"scan_status": "FAILED", "reason": "magic_byte_unknown"}

    def test_size_mismatch_becomes_failed(self, session, talent_a, handler_env):
        install, _ = handler_env
        install(PDF)
        ev = _evidence(session, talent_a, size=len(PDF) + 5)

        outbox_worker.evidence_scan_requested_handler(_payload(ev), 1)

        assert _reload(session, ev).scan_status == "FAILED"

    def test_storage_outage_propagates_so_outbox_retries(self, session, talent_a, handler_env):
        install, _ = handler_env
        install(ConnectionError("down"))
        ev = _evidence(session, talent_a)

        with pytest.raises(ConnectionError):
            outbox_worker.evidence_scan_requested_handler(_payload(ev), 1)

        assert _reload(session, ev).scan_status == "PENDING"

    def test_redelivery_of_already_scanned_row_is_noop(self, session, talent_a, handler_env):
        install, reads = handler_env
        install(PDF)
        ev = _evidence(session, talent_a, status="CLEAN")

        outbox_worker.evidence_scan_requested_handler(_payload(ev), 1)

        assert reads == []  # no storage read, status untouched
        assert _reload(session, ev).scan_status == "CLEAN"

    def test_verdict_does_not_overwrite_status_changed_during_the_read(self, session, talent_a, handler_env, monkeypatch):
        """Another worker finished the row while this one was reading storage: keep that result, write no audit."""
        ev = _evidence(session, talent_a)

        def racing_fetch(bucket, key, max_bytes):
            session.execute(
                sqlalchemy.update(Evidence).where(Evidence.id == ev.id).values(scan_status="FAILED")
            )
            return PDF

        monkeypatch.setattr("app.services.storage.fetch_object_bytes", racing_fetch)

        outbox_worker.evidence_scan_requested_handler(_payload(ev), 1)

        assert _reload(session, ev).scan_status == "FAILED"
        assert session.execute(
            select(AuditEvent).where(AuditEvent.action == "evidence.scanned", AuditEvent.subject_id == ev.id)
        ).first() is None

    def test_unknown_evidence_is_noop(self, handler_env):
        install, reads = handler_env
        install(PDF)
        outbox_worker.evidence_scan_requested_handler(
            {"evidence_id": str(uuid.uuid4()), "storage_key": "x", "bucket": "b"}, 1
        )
        assert reads == []

