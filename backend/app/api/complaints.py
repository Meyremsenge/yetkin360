"""Complaint endpoints for talents and respondents (sikayet-backend, C2/C5).

Business logic lives in app/services/complaint.py; this module only wires HTTP.
Unauthorized access is 404 (never 403). Writes need a verified e-mail + CSRF.
Admin routes are in app/api/admin_complaints.py.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, get_session, get_verified_principal
from app.core.deps import require_csrf
from app.core.errors import ApiError
from app.schemas.complaint import (
    AttachmentCreateRequest,
    AttachmentDownloadResponse,
    AttachmentResponse,
    AttachmentUploadUrlRequest,
    AttachmentUploadUrlResponse,
    ComplaintCreatedResponse,
    ComplaintCreateRequest,
    ComplaintRespondentListResponse,
    ComplaintRespondentView,
    ComplaintStudentListResponse,
    ComplaintStudentView,
    ExplanationRequest,
)
from app.services import complaint as service
from app.services.authorization import Principal
from app.services.storage import check_rate_limit

router = APIRouter(prefix="/complaints", tags=["complaints"])

MAX_PAGE_SIZE = 200


def _upload_rate_limit(principal: Principal) -> None:
    if not check_rate_limit(f"complaint:{principal.user_id}"):
        raise ApiError(429, "RATE_LIMIT_EXCEEDED", "Çok hızlı istek gönderdiniz. Lütfen daha sonra tekrar deneyin.")


@router.post("", status_code=201, response_model=ComplaintCreatedResponse)
def create_complaint_endpoint(
    body: ComplaintCreateRequest,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> ComplaintCreatedResponse:
    """Errors: 404 (subject not the caller's), 409 TOO_EARLY / ALREADY_OPEN / NOT_PENDING, 422, 429 RATE_LIMITED."""
    return service.create_complaint(session, principal, body.subject_type, body.subject_id, body.description)


@router.get("", response_model=ComplaintStudentListResponse)
def list_my_complaints(
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> ComplaintStudentListResponse:
    """The caller's own complaints (talent view, status_label only), newest first."""
    return service.list_own_complaints(session, principal, limit, offset)


@router.get("/assigned", response_model=ComplaintRespondentListResponse)
def list_assigned_complaints(
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> ComplaintRespondentListResponse:
    """Complaints the caller must explain (after the admin's request) or was escalated to."""
    return service.list_assigned_complaints(session, principal, limit, offset)


@router.get("/{complaint_id}", response_model=ComplaintStudentView | ComplaintRespondentView)
def get_complaint(
    complaint_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> ComplaintStudentView | ComplaintRespondentView:
    """Owner → viewer_role OWNER; respondent / escalated member → viewer_role RESPONDENT; others 404."""
    return service.get_complaint_view(session, principal, complaint_id)


@router.post("/{complaint_id}/explanation", response_model=ComplaintRespondentView)
def submit_explanation(
    complaint_id: uuid.UUID,
    body: ExplanationRequest,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> ComplaintRespondentView:
    """Respondent only, in EXPLANATION_REQUESTED, once. Errors: 404, 409 INVALID_TRANSITION, 422."""
    return service.submit_explanation(session, principal, complaint_id, body.text)


@router.post("/{complaint_id}/attachments/upload-url", response_model=AttachmentUploadUrlResponse)
def attachment_upload_url(
    complaint_id: uuid.UUID,
    body: AttachmentUploadUrlRequest,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> AttachmentUploadUrlResponse:
    """Owner only. Errors: 404, 409 COMPLAINT_CLOSED, 422 UNSUPPORTED_CONTENT_TYPE / FILE_TOO_LARGE, 429, 503."""
    _upload_rate_limit(principal)
    return service.create_attachment_upload_url(session, principal, complaint_id, body.content_type, body.size_bytes)


@router.post("/{complaint_id}/attachments", status_code=201, response_model=AttachmentResponse)
def register_attachment(
    complaint_id: uuid.UUID,
    body: AttachmentCreateRequest,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> AttachmentResponse:
    """
    Owner only. The stored object is read and checked (magic bytes + exact size) before
    it is recorded. Errors: 404, 409 COMPLAINT_CLOSED / ATTACHMENT_LIMIT_REACHED,
    422 INVALID_FILE_CONTENT / UPLOAD_NOT_FOUND / INVALID_STORAGE_KEY, 503.
    (Rate-limited at upload-url; registration is bounded by MAX_ATTACHMENTS.)
    """
    return service.register_attachment(
        session, principal, complaint_id, body.storage_key, body.mime_type, body.size_bytes
    )


@router.get("/{complaint_id}/attachments/{attachment_id}", response_model=AttachmentDownloadResponse)
def download_attachment(
    complaint_id: uuid.UUID,
    attachment_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> AttachmentDownloadResponse:
    """Owner only (respondent → 404). Short-lived presigned URL; audited. 409 ATTACHMENT_CONTENT_CHANGED, 503."""
    return service.download_own_attachment(session, principal, complaint_id, attachment_id)
