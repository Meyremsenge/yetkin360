"""
Evidence endpoints — presigned upload/download URL generation and evidence creation.

PLAN 2.5 (YET-82, YET-83): POST /evidence/upload-url generates a presigned
MinIO URL for client-side file uploads. Validates content-type, file size,
enforces rate limiting, and returns secure presigned URL with Content-Type
and Content-Length constraints (AC-S2).

PLAN 2.6 (YET-84, YET-85): POST /evidence creates evidence record (with outbox + audit),
GET /evidence/{id}/download-url generates presigned download URL with ownership + scan checks.
"""

import uuid

from botocore.exceptions import ConnectTimeoutError, EndpointConnectionError
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, get_session, get_verified_principal
from app.core.deps import require_csrf
from app.core.config import settings
from app.core.errors import ApiError
from app.schemas.evidence import (
    EvidenceUploadUrlRequest,
    EvidenceUploadUrlResponse,
    EvidenceCreateRequest,
    EvidenceResponse,
    EvidenceDownloadUrlResponse,
)
from app.services.authorization import Principal
from app.services.evidence import create_evidence, get_download_url, list_evidence
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
    principal: Principal = Depends(get_verified_principal),
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
    # Authorization: User must have a talent profile to upload evidence
    # (endpoint restricted to TALENT role; other roles have talent_id=None)
    if principal.talent_id is None:
        raise ApiError(403, "TALENT_PROFILE_REQUIRED", "Bu işlem için talent profili gereklidir.")

    # AC-S3: Rate limiting (checked first, before other validations)
    if not check_rate_limit(str(principal.talent_id)):
        raise ApiError(
            429,
            "RATE_LIMIT_EXCEEDED",
            "Çok hızlı istek gönderdiniz. Lütfen daha sonra tekrar deneyin.",
        )

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
        raise ApiError(
            503,
            "STORAGE_UNAVAILABLE",
            "Dosya depolama servisi şu anda kullanılamıyor. Lütfen daha sonra tekrar deneyin.",
        )

    # AC-1, AC-8: Return presigned POST form data with TTL
    return EvidenceUploadUrlResponse(
        upload_url=presigned_post["url"],
        upload_fields=presigned_post["fields"],
        object_key=object_key,
        expires_in=settings.s3_presigned_url_ttl_seconds,
    )


@router.post("", response_model=EvidenceResponse, status_code=201)
def create_evidence_record(
    request_body: EvidenceCreateRequest,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> EvidenceResponse:
    """
    AC-1 through AC-S7, AC-4: Register an evidence file and enqueue scanning.

    After client uploads file to MinIO using presigned URL from POST /evidence/upload-url,
    talent submits this request to create the evidence record on the platform.
    Validates storage_key ownership, checks deliverable ownership (if provided),
    enqueues scanning via outbox, logs audit event.

    POST /evidence
    Content-Type: application/json

    Request Body:
        {
            "storage_key": "evidence/{talent_id}/{uuid}.{ext}",  (required)
            "kind": "DOCUMENT",                                   (allowlist: REPOSITORY, DOCUMENT, IMAGE, LINK, CERTIFICATE)
            "mime_type": "application/pdf",                       (required)
            "size_bytes": 2048,                                   (required)
            "deliverable_id": "<optional-uuid>"                   (optional; AC-4: ownership chain check)
        }

    Returns:
        201 Created: {
            "id": "<evidence-uuid>",
            "owner_talent_id": "<talent-uuid>",
            "kind": "DOCUMENT",
            "provenance": "SELF_UPLOADED",
            "storage_key": "evidence/{talent_id}/{uuid}.{ext}",
            "mime_type": "application/pdf",
            "size_bytes": 2048,
            "scan_status": "PENDING",
            "visibility": "PRIVATE",
            "deliverable_id": "<optional-uuid or null>",
            "created_at": "2026-09-23T..."
        }

    Error Responses:
        401 Unauthorized: No valid auth token, or suspended account (AC-2, AC-13 — suspended users are rejected at the auth layer before reaching this endpoint)
        403 CSRF Failed: CSRF token mismatch or missing
        403 Talent Profile Required: User has no talent profile (AC-12)
        404 Not Found: deliverable_id provided but doesn't belong to principal's engagements (AC-4)
        422 Unprocessable Entity:
            - INVALID_STORAGE_KEY: storage_key prefix doesn't match principal.talent_id (AC-3, AC-S1)
            - (Pydantic validation errors for kind, mime_type, size_bytes)
        429 Too Many Requests: > 10 requests per minute (AC-S5)
        503 Service Unavailable: (Unlikely in this endpoint, but handled for consistency)

    Acceptance Criteria:
        AC-1: Creates evidence record with scan_status=PENDING, visibility=PRIVATE, provenance=SELF_UPLOADED
        AC-1: Writes outbox message (evidence.scan_requested) in same transaction
        AC-2: Unauthenticated → 401
        AC-3: Invalid storage_key prefix → 422 INVALID_STORAGE_KEY (elevation defense)
        AC-4: deliverable_id ownership check (Deliverable→Engagement→talent_id), 404 if mismatch
        AC-8: kind must be in allowlist (Pydantic CHECK constraint)
        AC-12: No talent profile → 403 TALENT_PROFILE_REQUIRED
        AC-13: Suspended account → 401 (rejected at auth layer, see app/core/deps.py:get_current_user)
        AC-S1: storage_key validation (elevation defense)
        AC-S4: Error messages generic, no MinIO/internal details
        AC-S5: Rate limit 10/minute (check before other validations)
        AC-S7: Audit event logged with action=evidence.created
    """
    # AC-S5: Rate limiting (checked first, before validation)
    if not check_rate_limit(str(principal.talent_id)):
        raise ApiError(
            429,
            "RATE_LIMIT_EXCEEDED",
            "Çok hızlı istek gönderdiniz. Lütfen daha sonra tekrar deneyin.",
        )

    # Call service layer (performs authorization checks, validation, DB operations)
    response = create_evidence(
        session=session,
        principal=principal,
        storage_key=request_body.storage_key,
        kind=request_body.kind,
        mime_type=request_body.mime_type,
        size_bytes=request_body.size_bytes,
        deliverable_id=request_body.deliverable_id,
    )

    # Commit transaction in endpoint layer
    session.commit()

    return response


@router.get("", response_model=list[EvidenceResponse])
def list_my_evidence(
    deliverable_id: uuid.UUID | None = Query(None, description="Only evidence of this deliverable"),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> list[EvidenceResponse]:
    """
    YET-195: GET /evidence — the authenticated talent's own evidence, newest first.

    Error Responses:
        401 Unauthorized: No valid auth token
        403 TALENT_PROFILE_REQUIRED: User has no talent profile
    Other talents' evidence is never in scope (not listed, no error).
    """
    return list_evidence(session=session, principal=principal, deliverable_id=deliverable_id)


@router.get("/{evidence_id}/download-url", response_model=EvidenceDownloadUrlResponse)
def get_evidence_download_url(
    evidence_id: uuid.UUID = Path(..., description="Evidence UUID"),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> EvidenceDownloadUrlResponse:
    """
    AC-5 through AC-S6: Generate presigned download URL for evidence.

    GET /evidence/{evidence_id}/download-url

    Returns:
        200 OK: {
            "download_url": "https://minio.example.com/presigned-get-url",
            "expires_in": 300
        }

    Error Responses:
        401 Unauthorized: No valid auth token, or suspended account (AC-2, AC-13 — suspended users are rejected at the auth layer before reaching this endpoint)
        403 Talent Profile Required: User has no talent profile (AC-12)
        403 Forbidden: Platform admin trying to download PRIVATE evidence (AC-S3)
        404 Not Found:
            - Evidence not found (AC-9)
            - Evidence belongs to different talent (AC-6, AC-S2)
        409 Conflict: scan_status is not CLEAN (AC-7)
        429 Too Many Requests: > 10 requests per minute (AC-S5)
        503 Service Unavailable: MinIO unreachable (AC-11)

    Acceptance Criteria:
        AC-2: Unauthenticated → 401
        AC-5: Owned CLEAN evidence → 200 with download_url, expires_in=300
        AC-6: Evidence belongs to other talent → 404 (not 409 or other status)
        AC-7: scan_status PENDING/INFECTED/FAILED → 409 SCAN_NOT_CLEAN
        AC-9: Evidence not found → 404
        AC-10: expires_in always 300 seconds
        AC-11: MinIO unreachable → 503 STORAGE_UNAVAILABLE (no info leakage)
        AC-12: No talent profile → 403 TALENT_PROFILE_REQUIRED
        AC-13: Suspended account → 401 (rejected at auth layer, see app/core/deps.py:get_current_user)
        AC-S2: Ownership check before scan_status check (never leak scan_status to non-owners)
        AC-S3: Admin accessing PRIVATE evidence → 403 (not 404)
        AC-S5: Rate limit 10/minute
        AC-S6: Audit event logged with action=evidence.downloaded
    """
    # Authorization checks (same order as create for consistency)
    if principal.talent_id is None and not principal.is_platform_admin:
        raise ApiError(403, "TALENT_PROFILE_REQUIRED", "Bu işlem için talent profili gereklidir.")

    # AC-S5: Rate limiting (fallback to user_id for non-talent users like admin)
    rate_limit_key = str(principal.talent_id or principal.user_id)
    if not check_rate_limit(rate_limit_key):
        raise ApiError(
            429,
            "RATE_LIMIT_EXCEEDED",
            "Çok hızlı istek gönderdiniz. Lütfen daha sonra tekrar deneyin.",
        )

    # Call service layer (performs scoping, scan_status check, URL generation, audit)
    response = get_download_url(
        session=session,
        principal=principal,
        evidence_id=evidence_id,
    )

    # Commit transaction (audit event written)
    session.commit()

    return response
