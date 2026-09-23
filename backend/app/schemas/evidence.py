"""
Evidence upload URL request/response schemas (Pydantic DTOs).

PLAN 2.5 (YET-82, YET-83): Evidence file upload presigned URL generation.
"""

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
