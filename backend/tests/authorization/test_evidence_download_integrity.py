"""
YET-195 follow-up (TOCTOU): content swapped into the stored object after the scan
said CLEAN must not be handed out as CLEAN.

The presigned POST policy stays valid for 15 minutes and is not single-use, so the
owner can re-upload to the same key (same size/type) after the scan. The scan records
the ETag of the bytes it inspected; the download path HEADs the object (outside any
transaction) and refuses when it differs. Storage is a fake: no real network.
"""

from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy
from botocore.exceptions import ClientError, EndpointConnectionError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models import AuditEvent, Evidence
from app.services.storage import StoredObject, head_object_etag
from app.workers import outbox_worker
from tests._evidence_api import add_evidence, login

PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


class FakeStore:
    """One object per key; ETag changes whenever the content does (like S3/MinIO)."""

    def __init__(self):
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.head_calls = 0

    def put(self, key: str, data: bytes, etag: str) -> None:
        self.objects[key] = (data, etag)

    def fetch_object(self, bucket, key, max_bytes):
        if key not in self.objects:
            return None
        data, etag = self.objects[key]
        return StoredObject(data=data, etag=etag)

    def head_object_etag(self, bucket, key):
        self.head_calls += 1
        return self.objects[key][1] if key in self.objects else None


def _install(monkeypatch, session, store: FakeStore) -> None:
    class _Engine:
        def dispose(self) -> None:
            pass

    bind = session.get_bind()
    monkeypatch.setattr(sqlalchemy, "create_engine", lambda *a, **k: _Engine())
    monkeypatch.setattr(
        outbox_worker, "Session", lambda engine: Session(bind=bind, join_transaction_mode="create_savepoint")
    )
    monkeypatch.setattr("app.services.storage.fetch_object", store.fetch_object)
    monkeypatch.setattr("app.services.evidence.head_object_etag", store.head_object_etag)


def _scan(ev: Evidence) -> None:
    outbox_worker.evidence_scan_requested_handler({"evidence_id": str(ev.id)}, 1)


def _download(evidence_api, user, ev):
    login(evidence_api, user)
    with patch("app.services.storage.boto3.client") as boto:
        boto.return_value.generate_presigned_url.return_value = "https://s3.example/signed"
        return evidence_api.get(f"/evidence/{ev.id}/download-url")


def _scanned_pdf(session, talent, store) -> Evidence:
    ev = add_evidence(session, talent, size_bytes=len(PDF))
    store.put(ev.storage_key, PDF, "etag-original")
    _scan(ev)
    session.expire_all()
    return session.get(Evidence, ev.id)


class TestDownloadIntegrity:
    def test_unchanged_object_is_served(self, evidence_api, session, user_talent_a, talent_a, monkeypatch):
        store = FakeStore()
        _install(monkeypatch, session, store)
        ev = _scanned_pdf(session, talent_a, store)
        assert (ev.scan_status, ev.storage_etag) == ("CLEAN", "etag-original")

        response = _download(evidence_api, user_talent_a, ev)

        assert response.status_code == 200
        assert response.json()["download_url"] == "https://s3.example/signed"
        assert store.head_calls == 1

    def test_content_swapped_after_scan_is_not_served(self, evidence_api, session, user_talent_a, talent_a, monkeypatch):
        store = FakeStore()
        _install(monkeypatch, session, store)
        ev = _scanned_pdf(session, talent_a, store)

        # Presigned POST reused inside its window: same key, same size and type, new bytes.
        store.put(ev.storage_key, PDF.replace(b"1 0 obj", b"9 9 obj"), "etag-swapped")
        response = _download(evidence_api, user_talent_a, ev)

        assert response.status_code == 409
        assert response.json()["code"] == "EVIDENCE_CONTENT_CHANGED"
        assert "download_url" not in response.text

    def test_blocked_download_is_audited_and_not_logged_as_a_download(
        self, evidence_api, session, user_talent_a, talent_a, monkeypatch
    ):
        store = FakeStore()
        _install(monkeypatch, session, store)
        ev = _scanned_pdf(session, talent_a, store)
        store.put(ev.storage_key, PDF, "etag-swapped")

        _download(evidence_api, user_talent_a, ev)

        session.expire_all()
        actions = {
            a.action: a
            for a in session.query(AuditEvent).filter(AuditEvent.subject_id == ev.id)
            if a.action.startswith("evidence.download")
        }
        assert set(actions) == {"evidence.download_blocked"}
        assert actions["evidence.download_blocked"].result == "DENIED"

    def test_object_deleted_after_scan_is_not_served(self, evidence_api, session, user_talent_a, talent_a, monkeypatch):
        store = FakeStore()
        _install(monkeypatch, session, store)
        ev = _scanned_pdf(session, talent_a, store)
        del store.objects[ev.storage_key]

        response = _download(evidence_api, user_talent_a, ev)

        assert response.status_code == 409
        assert response.json()["code"] == "EVIDENCE_CONTENT_CHANGED"

    def test_clean_row_without_recorded_etag_fails_closed(self, evidence_api, session, user_talent_a, talent_a, monkeypatch):
        """A CLEAN row the scan never stamped (pre-migration / manual) cannot be verified, so it is not served."""
        store = FakeStore()
        _install(monkeypatch, session, store)
        ev = add_evidence(session, talent_a, scan_status="CLEAN")
        store.put(ev.storage_key, PDF, "etag-whatever")

        response = _download(evidence_api, user_talent_a, ev)

        assert response.status_code == 409
        assert response.json()["code"] == "EVIDENCE_CONTENT_CHANGED"

    def test_non_owner_gets_404_without_touching_storage(
        self, evidence_api, session, user_talent_a, talent_a, user_talent_b, talent_b, monkeypatch
    ):
        store = FakeStore()
        _install(monkeypatch, session, store)
        ev = _scanned_pdf(session, talent_a, store)
        store.head_calls = 0

        response = _download(evidence_api, user_talent_b, ev)

        assert response.status_code == 404
        assert store.head_calls == 0

    def test_head_runs_outside_an_open_transaction(self, evidence_api, session, user_talent_a, talent_a, monkeypatch):
        """The HEAD is a network call: the request's read transaction must be closed first."""
        store = FakeStore()
        _install(monkeypatch, session, store)
        ev = _scanned_pdf(session, talent_a, store)
        in_tx: list[bool] = []

        def head(bucket, key):
            in_tx.append(session.in_transaction())
            return store.head_object_etag(bucket, key)

        monkeypatch.setattr("app.services.evidence.head_object_etag", head)
        _download(evidence_api, user_talent_a, ev)

        assert in_tx == [False]


class TestScanRecordsEtag:
    def test_etag_is_recorded_only_for_clean(self, session, talent_a, monkeypatch):
        store = FakeStore()
        _install(monkeypatch, session, store)
        bad = add_evidence(session, talent_a, size_bytes=4)
        store.put(bad.storage_key, b"MZ\x90\x00", "etag-bad")

        _scan(bad)

        session.expire_all()
        got = session.get(Evidence, bad.id)
        assert (got.scan_status, got.storage_etag) == ("FAILED", None)


class TestHeadObjectEtag:
    @staticmethod
    def _s3(boto) -> MagicMock:
        s3 = MagicMock()
        boto.return_value = s3
        return s3

    def test_quoted_etag_is_normalized(self):
        with patch("app.services.storage.boto3.client") as boto:
            self._s3(boto).head_object.return_value = {"ETag": '"abc123"'}
            assert head_object_etag("b", "k") == "abc123"

    def test_missing_object_is_none(self):
        with patch("app.services.storage.boto3.client") as boto:
            self._s3(boto).head_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")
            assert head_object_etag("b", "k") is None

    @pytest.mark.parametrize(
        "error",
        [
            ClientError({"Error": {"Code": "AccessDenied"}}, "HeadObject"),
            EndpointConnectionError(endpoint_url="http://minio:9000"),
        ],
    )
    def test_other_storage_errors_are_503_not_a_pass(self, error):
        with patch("app.services.storage.boto3.client") as boto:
            self._s3(boto).head_object.side_effect = error
            with pytest.raises(ApiError) as exc:
                head_object_etag("b", "k")
            assert exc.value.status_code == 503
