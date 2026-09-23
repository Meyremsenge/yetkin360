"""
Evidence endpoint — presigned upload URL generation.

PLAN 2.5 (YET-82, YET-83): POST /evidence/upload-url generates a presigned
MinIO URL for client-side file uploads. Validates content-type, file size,
enforces rate limiting, and returns secure presigned URL with Content-Type
and Content-Length constraints (AC-S2).
"""

from botocore.exceptions import ConnectTimeoutError, EndpointConnectionError
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, get_session
from app.core.deps import require_csrf
from app.core.config import settings
from app.core.errors import ApiError
from app.schemas.evidence import EvidenceUploadUrlRequest, EvidenceUploadUrlResponse
from app.services.authorization import Principal
from app.services.storage import (
    build_object_key,
    check_rate_limit,
    generate_presigned_post,
    validate_content_type,
    validate_file_size,
)

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.post("/upload-url", response_model=EvidenceUploadUrlResponse)
def upload_url(
    request_body: EvidenceUploadUrlRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> EvidenceUploadUrlResponse:
    """
    AC-1 through AC-S4: Generate a presigned URL for evidence file upload.

    POST /evidence/upload-url
    Content-Type: application/json

    Request Body:
        {
            "filename": "resume.pdf",           (1-255 chars, required)
            "content_type": "application/pdf",  (allowlist: pdf, jpeg, png, docx)
            "size_bytes": 2048                  (0 to 10MB, required)
        }

    Returns:
        200 OK: {
            "upload_url": "https://minio.../bucket",
            "upload_fields": {
                "key": "evidence/{talent_id}/{uuid}.{ext}",
                "policy": "...",
                "x-amz-signature": "...",
                ...
            },
            "object_key": "evidence/{talent_id}/{uuid}.{ext}",
            "expires_in": 900
        }

    Error Responses:
        401 Unauthorized: No valid auth token (AC-2)
        403 CSRF Failed: CSRF token mismatch or missing
        403 Talent Profile Required: User has no talent profile (authorization check)
        422 Unprocessable Entity:
            - UNSUPPORTED_CONTENT_TYPE: Not in allowlist (AC-3)
            - FILE_TOO_LARGE: size_bytes > 10MB (AC-4)
            - (Pydantic validation errors for filename, size_bytes type, etc.) (AC-5)
        429 Too Many Requests: > 10 requests per minute (AC-S3)
        503 Service Unavailable: MinIO unreachable (AC-6)

    Acceptance Criteria:
        AC-1: Happy path returns presigned URL in format with 900s TTL
        AC-2: Unauthenticated → 401 (enforced by get_current_principal)
        AC-3: Unsupported content_type → 422 UNSUPPORTED_CONTENT_TYPE
        AC-4: size_bytes > 10MB → 422 FILE_TOO_LARGE
        AC-5: Invalid filename (empty, > 255) → 422 (Pydantic)
        AC-6: MinIO error → 503 STORAGE_UNAVAILABLE (no leak of details)
        AC-8: expires_in always 900 seconds
        AC-S1: object_key uses principal.talent_id, never from request
        AC-S2: Presigned URL signature bound to Content-Type and Content-Length
        AC-S3: Rate limit 10/minute → 429 (detected before other validations)
        AC-S4: Error messages generic, no MinIO bucket/endpoint/trace leak
    """
    # Authorization: Check if account is suspended
    if principal.is_suspended:
        raise ApiError(403, "ACCOUNT_SUSPENDED", "Hesabınız askıya alınmış.")

    # Authorization: User must have a talent profile to upload evidence
    # (endpoint restricted to TALENT role; other roles have talent_id=None)
    if principal.talent_id is None:
        raise ApiError(403, "TALENT_PROFILE_REQUIRED", "Bu işlem için talent profili gereklidir.")

    # AC-S3: Rate limiting (checked first, before other validations)
    if not check_rate_limit(str(principal.talent_id)):
        raise ApiError(429, "RATE_LIMIT_EXCEEDED", "Çok hızlı istek gönderdiniz. Lütfen daha sonra tekrar deneyin.")

    # AC-3: Validate content_type against allowlist
    if not validate_content_type(request_body.content_type):
        raise ApiError(
            422,
            "UNSUPPORTED_CONTENT_TYPE",
            "Desteklenmeyen dosya türü. İzin verilen türler: PDF, JPEG, PNG, DOCX.",
        )

    # AC-4: Validate file size
    if not validate_file_size(request_body.size_bytes):
        raise ApiError(
            422,
            "FILE_TOO_LARGE",
            f"Dosya çok büyük. Maksimum izin verilen boyut: {settings.evidence_max_size_bytes / (1024 * 1024):.0f}MB.",
        )

    # AC-1, AC-S1: Build object key using authenticated user's talent_id
    # talent_id comes from JWT/auth context, never from request body (elevation defense)
    object_key = build_object_key(
        talent_id=str(principal.talent_id),
        filename=request_body.filename,
        content_type=request_body.content_type,
    )

    # AC-1, AC-S2, AC-6: Generate presigned POST form data with Content-Type and Content-Length constraints
    try:
        presigned_post = generate_presigned_post(
            bucket=settings.s3_bucket,
            object_key=object_key,
            content_type=request_body.content_type,
            size_bytes=request_body.size_bytes,
            ttl=settings.s3_presigned_url_ttl_seconds,
        )
    except (EndpointConnectionError, ConnectTimeoutError):
        # AC-S4: Do not leak MinIO endpoint URL, bucket name, or exception details
        raise ApiError(503, "STORAGE_UNAVAILABLE", "Dosya depolama servisi şu anda kullanılamıyor. Lütfen daha sonra tekrar deneyin.")

    # AC-1, AC-8: Return presigned POST form data with TTL
    return EvidenceUploadUrlResponse(
        upload_url=presigned_post["url"],
        upload_fields=presigned_post["fields"],
        object_key=object_key,
        expires_in=settings.s3_presigned_url_ttl_seconds,
    )
