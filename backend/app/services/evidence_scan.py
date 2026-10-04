"""
Evidence content inspection (YET-195 / YET-184): magic-byte + size + content-type.

No antivirus engine (explicit decision: no new process/dependency). This module
is pure — it takes the object's bytes and the values declared at registration
and returns a verdict. The outbox handler (workers/outbox_worker.py) does the
network read outside any transaction and writes the verdict back.

Verdict statuses: CLEAN, or FAILED when the object is missing or violates what
was declared / the policy. INFECTED is reserved for a future AV engine and is
never produced here (a mismatch is not a virus finding).
"""

import hashlib
import io
import zipfile
from dataclasses import dataclass

from app.core.config import settings
from app.services.storage import ALLOWED_CONTENT_TYPES

# Limits for DOCX (ZIP) inspection — zip-bomb and macro defense.
MAX_DOCX_ENTRIES = 1000
MAX_DOCX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
DOCX_REQUIRED_ENTRIES = ("[Content_Types].xml", "word/document.xml")

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True)
class ScanVerdict:
    status: str  # "CLEAN" | "FAILED"
    reason: str  # short machine-readable code, safe to log (no content)
    content_hash: str | None = None  # sha256 hex, set only when CLEAN


def _failed(reason: str) -> ScanVerdict:
    return ScanVerdict(status="FAILED", reason=reason)


def detect_content_type(data: bytes) -> str | None:
    """Detect the MIME type from leading magic bytes. Never trusts the extension."""
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(_PNG_SIGNATURE):
        return "image/png"
    if data.startswith(b"PK\x03\x04"):
        # ZIP container: whether it is a DOCX is decided by inspect_docx().
        return "application/zip"
    return None


def inspect_docx(data: bytes) -> str | None:
    """Return a failure reason for a DOCX that is not a plain Word document, else None."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_DOCX_ENTRIES:
                return "docx_too_many_entries"
            if sum(info.file_size for info in infos) > MAX_DOCX_UNCOMPRESSED_BYTES:
                return "docx_uncompressed_too_large"
            names = [info.filename for info in infos]
            for name in names:
                if name.startswith("/") or ".." in name.split("/"):
                    return "docx_unsafe_entry_name"
            for required in DOCX_REQUIRED_ENTRIES:
                if required not in names:
                    return "docx_not_word_document"
            if any(name.lower().endswith("vbaproject.bin") for name in names):
                return "docx_contains_macro"
    except zipfile.BadZipFile:
        return "docx_corrupt"
    return None


def inspect_content(
    data: bytes | None,
    declared_mime: str,
    declared_size: int,
) -> ScanVerdict:
    """
    Check the stored object against what was declared at registration.

    data is None when the object does not exist in storage.
    """
    if data is None:
        return _failed("object_missing")
    if declared_mime not in ALLOWED_CONTENT_TYPES:
        return _failed("mime_not_allowed")
    if len(data) > settings.evidence_max_size_bytes:
        return _failed("size_over_limit")
    if len(data) != declared_size:
        return _failed("size_mismatch")

    detected = detect_content_type(data)
    if detected is None:
        return _failed("magic_byte_unknown")

    docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if declared_mime == docx_mime:
        if detected != "application/zip":
            return _failed("magic_byte_mismatch")
        docx_failure = inspect_docx(data)
        if docx_failure is not None:
            return _failed(docx_failure)
    elif detected != declared_mime:
        return _failed("magic_byte_mismatch")

    return ScanVerdict(
        status="CLEAN",
        reason="ok",
        content_hash=hashlib.sha256(data).hexdigest(),
    )
