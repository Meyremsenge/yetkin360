"""
Student complaint endpoints: POST/GET /engagements/{id}/complaints.

Only the engagement's talent opens and reads complaints here. The admin side
(queue + decision) lives in app/api/admin.py behind the router-level admin gate.
"""

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, get_session, get_verified_principal
from app.core.deps import require_csrf
from app.core.errors import ApiError
from app.services.authorization import Principal
from app.services.complaint import (
    ComplaintAlreadyOpenError,
    ComplaintEngagementNotFoundError,
    ComplaintEvidenceInvalidError,
    ComplaintForbiddenError,
    ComplaintPreconditionError,
    create_complaint,
    list_engagement_complaints,
)

router = APIRouter(prefix="/engagements", tags=["complaints"])

ComplaintCategory = Literal["TASK_APPROVAL", "CERTIFICATE_APPROVAL", "PERSONAL"]
ComplaintStatus = Literal["OPEN", "UPHELD", "DISMISSED"]


class ComplaintCreateRequest(BaseModel):
    category: ComplaintCategory
    description: str = Field(..., min_length=20, max_length=2000)
    # Optional document: one of the student's clean evidence files on this engagement.
    evidence_id: uuid.UUID | None = None


class ComplaintResponse(BaseModel):
    id: uuid.UUID
    engagement_id: uuid.UUID
    category: ComplaintCategory
    description: str
    evidence_id: uuid.UUID | None
    status: ComplaintStatus
    decision_note: str | None
    decided_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class ComplaintListResponse(BaseModel):
    items: list[ComplaintResponse]


def _not_found() -> ApiError:
    return ApiError(404, "NOT_FOUND", "Çalışma bulunamadı.")


def _forbidden() -> ApiError:
    return ApiError(403, "FORBIDDEN", "Şikayeti yalnız çalışmanın sahibi öğrenci açabilir.")


@router.post("/{engagement_id}/complaints", response_model=ComplaintResponse, status_code=201)
def post_complaint(
    engagement_id: uuid.UUID,
    payload: ComplaintCreateRequest,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> ComplaintResponse:
    """
    The engagement's talent opens a complaint; the organization is notified and
    the platform admin decides.

    Errors: 404 (out of scope), 403 (in scope, not the talent),
    409 COMPLAINT_ALREADY_OPEN, 422 PRECONDITION_FAILED (draft engagement),
    422 INVALID_EVIDENCE.
    """
    try:
        complaint = create_complaint(
            session=session,
            principal=principal,
            engagement_id=engagement_id,
            category=payload.category,
            description=payload.description,
            evidence_id=payload.evidence_id,
        )
    except ComplaintEngagementNotFoundError:
        raise _not_found()
    except ComplaintForbiddenError:
        raise _forbidden()
    except ComplaintPreconditionError:
        raise ApiError(422, "PRECONDITION_FAILED", "Taslak durumundaki çalışma için şikayet açılamaz.")
    except ComplaintEvidenceInvalidError:
        raise ApiError(
            422, "INVALID_EVIDENCE", "Belge bu çalışmaya yüklediğiniz, taraması tamamlanmış bir kanıt olmalıdır."
        )
    except ComplaintAlreadyOpenError:
        raise ApiError(409, "COMPLAINT_ALREADY_OPEN", "Bu çalışma için zaten açık bir şikayetiniz var.")
    return ComplaintResponse.model_validate(complaint)


@router.get("/{engagement_id}/complaints", response_model=ComplaintListResponse)
def get_complaints(
    engagement_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> ComplaintListResponse:
    """The student's own complaints on the engagement, newest first."""
    try:
        complaints = list_engagement_complaints(session, principal, engagement_id)
    except ComplaintEngagementNotFoundError:
        raise _not_found()
    except ComplaintForbiddenError:
        raise _forbidden()
    return ComplaintListResponse(items=[ComplaintResponse.model_validate(c) for c in complaints])
