"""
YET-184: POST /evidence registration validation (file-upload security).

Extension/mime forgery, key format ({uuid}.{ext}, no nested paths), size,
duplicate key, other talent's key. Registration makes no network call — the
object itself is verified by the outbox scan handler (tests/test_evidence_scan.py).
"""

import uuid

import pytest
from sqlalchemy import select

from app.models import Outbox
from tests._evidence_api import CSRF, add_evidence, body as _body, login

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class TestRegisterEvidenceValidation:
    def test_valid_registration_creates_pending_record_and_scan_outbox_row(self, evidence_api, session, user_talent_a, talent_a):
        login(evidence_api, user_talent_a)
        body = _body(talent_a)

        response = evidence_api.post("/evidence", json=body, headers=CSRF)

        assert response.status_code == 201
        assert response.json()["scan_status"] == "PENDING"
        row = session.execute(
            select(Outbox).where(Outbox.topic == "evidence.scan_requested")
        ).scalars().all()
        assert any(r.payload["storage_key"] == body["storage_key"] for r in row)

    def test_other_talents_key_prefix_is_rejected(self, evidence_api, user_talent_a, talent_a, talent_b):
        login(evidence_api, user_talent_a)
        response = evidence_api.post("/evidence", json=_body(talent_b), headers=CSRF)
        assert response.status_code == 404
        assert response.json()["code"] == "NOT_FOUND"

    def test_foreign_key_answer_is_identical_whether_or_not_the_object_exists(
        self, evidence_api, session, user_talent_a, talent_a, talent_b
    ):
        """No existence oracle: a registered foreign object, a fresh foreign key and a garbage key all look alike."""
        theirs = add_evidence(session, talent_b)
        login(evidence_api, user_talent_a)
        keys = [theirs.storage_key, f"evidence/{talent_b.id}/{uuid.uuid4()}.pdf", "evidence/not-a-talent/x.pdf"]

        answers = {
            (r.status_code, r.json()['code'], r.json()['message'])
            for r in (
                evidence_api.post("/evidence", json=_body(talent_a, storage_key=k), headers=CSRF) for k in keys
            )
        }

        assert len(answers) == 1
        assert next(iter(answers))[0] == 404

    def test_malformed_key_under_own_prefix_stays_422(self, evidence_api, user_talent_a, talent_a):
        """Only keys outside the caller's own prefix turn into 404; own-prefix format errors are the caller's to fix."""
        login(evidence_api, user_talent_a)
        key = f"evidence/{talent_a.id}/not-a-uuid.pdf"
        response = evidence_api.post("/evidence", json=_body(talent_a, storage_key=key), headers=CSRF)
        assert response.status_code == 422
        assert response.json()["code"] == "INVALID_STORAGE_KEY"

    @pytest.mark.parametrize("mime", ["application/x-msdownload", "text/html", "application/zip", "image/svg+xml", ""])
    def test_mime_outside_allowlist_is_rejected(self, evidence_api, user_talent_a, talent_a, mime):
        login(evidence_api, user_talent_a)
        response = evidence_api.post("/evidence", json=_body(talent_a, mime_type=mime), headers=CSRF)
        assert response.status_code == 422
        assert response.json()["code"] == "UNSUPPORTED_CONTENT_TYPE"

    def test_extension_must_match_declared_mime(self, evidence_api, user_talent_a, talent_a):
        login(evidence_api, user_talent_a)
        key = f"evidence/{talent_a.id}/{uuid.uuid4()}.exe"
        response = evidence_api.post("/evidence", json=_body(talent_a, storage_key=key), headers=CSRF)
        assert response.status_code == 422
        assert response.json()["code"] == "INVALID_STORAGE_KEY"

    def test_png_extension_with_pdf_mime_is_rejected(self, evidence_api, user_talent_a, talent_a):
        login(evidence_api, user_talent_a)
        key = f"evidence/{talent_a.id}/{uuid.uuid4()}.png"
        response = evidence_api.post("/evidence", json=_body(talent_a, storage_key=key), headers=CSRF)
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "suffix",
        [
            "report.pdf",  # client-chosen name, not {uuid}.{ext}
            "../{uuid}.pdf",  # traversal
            "sub/{uuid}.pdf",  # nested path
            "{uuid}.pdf/",  # trailing slash
            "{uuid}.pdf.exe",  # double extension
            "{uuid}.PDF",  # case games
        ],
    )
    def test_key_must_be_exactly_uuid_dot_ext(self, evidence_api, user_talent_a, talent_a, suffix):
        login(evidence_api, user_talent_a)
        key = f"evidence/{talent_a.id}/" + suffix.format(uuid=uuid.uuid4())
        response = evidence_api.post("/evidence", json=_body(talent_a, storage_key=key), headers=CSRF)
        assert response.status_code == 422
        assert response.json()["code"] == "INVALID_STORAGE_KEY"

    def test_docx_mime_requires_docx_extension(self, evidence_api, user_talent_a, talent_a):
        login(evidence_api, user_talent_a)
        ok_key = f"evidence/{talent_a.id}/{uuid.uuid4()}.docx"
        assert evidence_api.post("/evidence", json=_body(talent_a, storage_key=ok_key, mime_type=DOCX_MIME), headers=CSRF).status_code == 201
        bad_key = f"evidence/{talent_a.id}/{uuid.uuid4()}.pdf"
        assert evidence_api.post("/evidence", json=_body(talent_a, storage_key=bad_key, mime_type=DOCX_MIME), headers=CSRF).status_code == 422

    def test_oversize_declared_size_is_rejected(self, evidence_api, user_talent_a, talent_a):
        login(evidence_api, user_talent_a)
        response = evidence_api.post("/evidence", json=_body(talent_a, size_bytes=10 * 1024 * 1024 + 1), headers=CSRF)
        assert response.status_code == 422
        assert response.json()["code"] == "FILE_TOO_LARGE"

    def test_same_storage_key_cannot_be_registered_twice(self, evidence_api, user_talent_a, talent_a):
        login(evidence_api, user_talent_a)
        body = _body(talent_a)
        assert evidence_api.post("/evidence", json=body, headers=CSRF).status_code == 201
        second = evidence_api.post("/evidence", json=body, headers=CSRF)
        assert second.status_code == 409
        assert second.json()["code"] == "EVIDENCE_ALREADY_REGISTERED"

    def test_key_of_other_talents_registered_object_cannot_be_claimed(self, evidence_api, session, user_talent_a, talent_a, talent_b):
        theirs = add_evidence(session, talent_b)
        login(evidence_api, user_talent_a)
        response = evidence_api.post("/evidence", json=_body(talent_a, storage_key=theirs.storage_key), headers=CSRF)
        assert response.status_code == 404  # wrong prefix; decided from the key alone, so no existence oracle
        assert response.json()["code"] == "NOT_FOUND"

    def test_unauthenticated_register_returns_401(self, evidence_api, talent_a):
        assert evidence_api.post("/evidence", json=_body(talent_a), headers=CSRF).status_code == 401
