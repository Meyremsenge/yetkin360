"""Complaint request/response DTOs (sikayet-backend). Never ORM models.

Requests use extra="forbid": a client-sent talent_id / organization_id /
respondent_user_id / status is a 422, not silently ignored (AC-S11).
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SubjectType = Literal["ENGAGEMENT", "CERTIFICATE_CHECK"]
StatusLabel = Literal["IN_PROGRESS", "DISMISSED", "RESOLVED", "UPHELD"]
ComplaintStatus = Literal[
    "OPEN",
    "UNDER_REVIEW",
    "EXPLANATION_REQUESTED",
    "EXPLANATION_SUBMITTED",
    "ESCALATED",
    "DISMISSED",
    "RESOLVED",
    "UPHELD",
]
TransitionAction = Literal[
    "START_REVIEW",
    "DISMISS",
    "REQUEST_EXPLANATION",
    "ACCEPT_EXPLANATION",
    "REJECT_EXPLANATION",
    "RESOLVE",
    "UPHOLD",
]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- requests -----------------------------------------------------------------


class ComplaintCreateRequest(_Strict):
    subject_type: SubjectType
    subject_id: uuid.UUID
    description: str = Field(min_length=10, max_length=4000)


class ExplanationRequest(_Strict):
    text: str = Field(min_length=1, max_length=2000)


class TransitionRequest(_Strict):
    action: TransitionAction
    note: str | None = Field(default=None, min_length=1, max_length=2000)
    reason: str | None = Field(default=None, min_length=1, max_length=2000)
    version: int | None = Field(default=None, ge=1)


class AttachmentUploadUrlRequest(_Strict):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str
    size_bytes: int = Field(ge=1)


class AttachmentCreateRequest(_Strict):
    storage_key: str = Field(min_length=1, max_length=512)
    mime_type: str
    size_bytes: int = Field(ge=1)


# --- responses ----------------------------------------------------------------


class AttachmentResponse(BaseModel):
    id: uuid.UUID
    mime_type: str
    size_bytes: int
    created_at: datetime


class AttachmentUploadUrlResponse(BaseModel):
    upload_url: str
    upload_fields: dict[str, str]
    object_key: str
    expires_in: int


class AttachmentDownloadResponse(BaseModel):
    download_url: str
    expires_in: int


class ComplaintCreatedResponse(BaseModel):
    id: uuid.UUID
    status: Literal["OPEN"]
    status_label: StatusLabel
    subject_type: SubjectType
    subject_id: uuid.UUID
    created_at: datetime


class ComplaintStudentView(BaseModel):
    """Owner view: never the internal status, the admin's note or the explanation (AC-19)."""

    id: uuid.UUID
    viewer_role: Literal["OWNER"] = "OWNER"
    subject_type: SubjectType
    subject_id: uuid.UUID
    status_label: StatusLabel
    description: str
    resolution_reason: str | None
    created_at: datetime
    closed_at: datetime | None
    attachments: list[AttachmentResponse]


class ComplaintRespondentView(BaseModel):
    """Respondent / escalated-member view: the admin's request, never the talent's text or files."""

    id: uuid.UUID
    viewer_role: Literal["RESPONDENT"] = "RESPONDENT"
    subject_type: SubjectType
    subject_id: uuid.UUID
    status: ComplaintStatus
    request_note: str | None
    explanation_due_at: datetime | None
    explanation_text: str | None
    created_at: datetime


class ComplaintStudentListResponse(BaseModel):
    items: list[ComplaintStudentView]
    limit: int
    offset: int
    has_more: bool


class ComplaintRespondentListResponse(BaseModel):
    items: list[ComplaintRespondentView]
    limit: int
    offset: int
    has_more: bool


class ComplaintEventResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    from_status: str | None
    to_status: str
    actor_role: str
    actor_user_id: uuid.UUID | None
    note: str | None
    created_at: datetime


class AdminComplaintListItem(BaseModel):
    id: uuid.UUID
    status: ComplaintStatus
    subject_type: SubjectType
    subject_id: uuid.UUID
    subject_pending: bool
    target_type: Literal["INSTITUTION", "ORGANIZATION"]
    target_id: uuid.UUID
    target_name: str | None
    attachment_count: int
    explanation_due_at: datetime | None
    created_at: datetime


class AdminComplaintListResponse(BaseModel):
    items: list[AdminComplaintListItem]
    limit: int
    offset: int
    has_more: bool


class AdminComplaintDetail(AdminComplaintListItem):
    talent_id: uuid.UUID
    talent_name: str | None
    description: str
    respondent_user_id: uuid.UUID | None
    request_note: str | None
    explanation_text: str | None
    resolution_reason: str | None
    version: int
    closed_at: datetime | None
    attachments: list[AttachmentResponse]
    events: list[ComplaintEventResponse]
