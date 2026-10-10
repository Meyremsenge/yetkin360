"""Admin complaint endpoints (sikayet-backend, C3/C4).

Router-level gate `require_platform_admin` (imported from app/api/admin.py): non-admins
get 404, anonymous 401; writes also need a verified e-mail. Every attachment download
is audited. Business logic lives in app/services/complaint.py.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.admin import require_platform_admin
from app.api.deps import get_current_principal, get_session
from app.core.deps import require_csrf
from app.schemas.complaint import (
    AdminComplaintDetail,
    AdminComplaintListResponse,
    AttachmentDownloadResponse,
    ComplaintStatus,
    TransitionRequest,
)
from app.services import complaint as service
from app.services.authorization import Principal

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_platform_admin)])

MAX_PAGE_SIZE = 200


@router.get("/complaints", response_model=AdminComplaintListResponse)
def list_complaints(
    status: ComplaintStatus | None = Query(None, description="Omit for the open queue (non-terminal)"),
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> AdminComplaintListResponse:
    """Oldest first. Envelope {items, limit, offset, has_more}; has_more via limit+1."""
    return service.list_admin_complaints(session, principal, status, limit, offset)


@router.get("/complaints/{complaint_id}", response_model=AdminComplaintDetail)
def get_complaint(
    complaint_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> AdminComplaintDetail:
    return service.get_admin_complaint(session, principal, complaint_id)


@router.get("/complaints/{complaint_id}/attachments/{attachment_id}", response_model=AttachmentDownloadResponse)
def download_attachment(
    complaint_id: uuid.UUID,
    attachment_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> AttachmentDownloadResponse:
    """Only documents attached to this complaint; the student's evidence stays closed (AC-S10)."""
    return service.download_admin_attachment(session, principal, complaint_id, attachment_id)


@router.post("/complaints/{complaint_id}/transitions", response_model=AdminComplaintDetail)
def transition_complaint(
    complaint_id: uuid.UUID,
    body: TransitionRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> AdminComplaintDetail:
    """
    Actions: START_REVIEW, DISMISS (reason), REQUEST_EXPLANATION (note), ACCEPT_EXPLANATION,
    REJECT_EXPLANATION (→ ESCALATED), RESOLVE, UPHOLD. Errors: 404, 409 INVALID_TRANSITION /
    VERSION_CONFLICT / NO_RESPONDENT / DEADLINE_NOT_REACHED, 422.
    """
    return service.transition_complaint(
        session, principal, complaint_id, body.action, note=body.note, reason=body.reason, version=body.version
    )
