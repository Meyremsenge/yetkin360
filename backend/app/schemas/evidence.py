"""
Evidence request/response schemas (Pydantic DTOs).

PLAN 2.5 (YET-82, YET-83): Evidence file upload presigned URL generation.
PLAN 2.6 (YET-84, YET-85): Evidence record creation and download URL generation.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EvidenceUploadUrlRequest(BaseModel):
    """
    AC-1, AC-5: Request body for POST /evidence/upload-url.

    Fields:
        filename: File name (1-255 chars, non-empty). Pydantic validates this.
        content_type: MIME type (allowlist: pdf, jpeg, png, docx).
                     Validated by service layer.
        size_bytes: Declared file size in bytes. Must be <= 10485760 (10MB).
                   Validated by service layer.
    """

    filename: str = Field(min_length=1, max_length=255)
    content_type: str
    size_bytes: int = Field(ge=0)


class EvidenceUploadUrlResponse(BaseModel):
    """
    AC-1, AC-8: Response for presigned POST form data generation.

    Fields:
        upload_url: Presigned POST endpoint URL (https://minio.../bucket).
        upload_fields: Form fields and signature for the POST request (policy, x-amz-*).
        object_key: Storage object key (evidence/{talent_id}/{uuid}.{ext}).
        expires_in: Policy expiration time in seconds (TTL = 900 seconds = 15 minutes).
    """

    upload_url: str
    upload_fields: dict[str, str]
    object_key: str
    expires_in: int


class EvidenceCreateRequest(BaseModel):
    """
    AC-1, AC-4: Request body for POST /evidence.

    After client uploads file to MinIO using presigned URL, talent submits
    this request to register the evidence record on the platform.

    Fields:
        storage_key: MinIO object key (evidence/{talent_id}/{uuid}.{ext}) — same as from upload-url.
        kind: Evidence type (REPOSITORY, DOCUMENT, IMAGE, LINK, CERTIFICATE).
        mime_type: MIME type (must match what was uploaded).
        size_bytes: File size in bytes (must match what was uploaded).
        deliverable_id: Optional UUID of related Deliverable (AC-4: ownership checked via Deliverable→Engagement→talent_id).

    Note:
        - provenance: Always SELF_UPLOADED (not set by client).
        - visibility: Always PRIVATE (not set by client).
        - scan_status: Always PENDING initially (worker updates it).
        - content_hash: NULL (worker computes it during scanning).
    """

    storage_key: str = Field(min_length=1)
    kind: str = Field(pattern="^(REPOSITORY|DOCUMENT|IMAGE|LINK|CERTIFICATE)$")
    mime_type: str
    size_bytes: int = Field(ge=0)
    deliverable_id: uuid.UUID | None = None


class EvidenceResponse(BaseModel):
    """
    AC-1, AC-4: Response for evidence creation and download URL endpoints.

    Fields:
        id: Evidence record UUID.
        owner_talent_id: Talent who uploaded (owner).
        kind: Evidence type.
        provenance: Always SELF_UPLOADED.
        storage_key: MinIO object key.
        mime_type: MIME type.
        size_bytes: File size.
        scan_status: PENDING, CLEAN, INFECTED, or FAILED.
        visibility: Always PRIVATE.
        deliverable_id: Optional related Deliverable UUID.
        created_at: Timestamp when evidence was registered.
    """

    id: uuid.UUID
    owner_talent_id: uuid.UUID
    kind: str
    provenance: str
    storage_key: str
    mime_type: str
    size_bytes: int
    scan_status: str
    visibility: str
    deliverable_id: uuid.UUID | None
    created_at: datetime


class EvidenceDownloadUrlResponse(BaseModel):
    """
    AC-5, AC-10: Response for GET /evidence/{id}/download-url.

    Fields:
        download_url: Presigned GET URL (expires in 300 seconds).
        expires_in: URL expiration time (always 300 seconds = 5 minutes).
    """

    download_url: str
    expires_in: int
