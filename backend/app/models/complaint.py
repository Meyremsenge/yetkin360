"""
Complaint (Şikayet) models — sikayet-backend, C1.

A talent complains to the platform admin when an approval they are waiting for
(engagement approval/evaluation or a certificate check decision) stays unanswered.

- complaints: mutable workflow row (status + version). DELETE is forbidden and a
  terminal status (DISMISSED/RESOLVED/UPHELD) can never change again — both by
  DB trigger (migration q7c1m2p3l4n5).
- complaint_events: append-only timeline (UPDATE/DELETE forbidden by trigger).
- complaint_attachments: documents the talent deliberately shares with the admin.
  Stored as complaints/{complaint_id}/{uuid}.{ext}; never Evidence rows.

Subject and target are typed FK pairs (exactly one set, CHECK) instead of a bare
polymorphic id, so referential integrity lives in the database.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default

COMPLAINT_STATUSES = (
    "OPEN",
    "UNDER_REVIEW",
    "EXPLANATION_REQUESTED",
    "EXPLANATION_SUBMITTED",
    "ESCALATED",
    "DISMISSED",
    "RESOLVED",
    "UPHELD",
)
TERMINAL_STATUSES = ("DISMISSED", "RESOLVED", "UPHELD")
ATTACHMENT_MIME_TYPES = ("application/pdf", "image/jpeg", "image/png")


class Complaint(Base, TimestampMixin):
    __tablename__ = "complaints"
    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN','UNDER_REVIEW','EXPLANATION_REQUESTED','EXPLANATION_SUBMITTED',"
            "'ESCALATED','DISMISSED','RESOLVED','UPHELD')",
            name="ck_complaints_status",
        ),
        CheckConstraint(
            "(subject_type = 'ENGAGEMENT' AND engagement_id IS NOT NULL AND certificate_check_id IS NULL) OR "
            "(subject_type = 'CERTIFICATE_CHECK' AND certificate_check_id IS NOT NULL AND engagement_id IS NULL)",
            name="ck_complaints_subject",
        ),
        CheckConstraint(
            "(target_type = 'INSTITUTION' AND target_institution_id IS NOT NULL AND target_organization_id IS NULL) OR "
            "(target_type = 'ORGANIZATION' AND target_organization_id IS NOT NULL AND target_institution_id IS NULL)",
            name="ck_complaints_target",
        ),
        CheckConstraint("char_length(description) BETWEEN 10 AND 4000", name="ck_complaints_description_length"),
        CheckConstraint(
            "(status IN ('DISMISSED','RESOLVED','UPHELD')) = (closed_at IS NOT NULL)",
            name="ck_complaints_closed_at",
        ),
        CheckConstraint(
            "status <> 'DISMISSED' OR resolution_reason IS NOT NULL", name="ck_complaints_dismiss_reason"
        ),
        CheckConstraint("version >= 1", name="ck_complaints_version"),
        Index(
            "uq_complaints_open_engagement",
            "engagement_id",
            unique=True,
            postgresql_where=text("engagement_id IS NOT NULL AND status NOT IN ('DISMISSED','RESOLVED','UPHELD')"),
        ),
        Index(
            "uq_complaints_open_certificate_check",
            "certificate_check_id",
            unique=True,
            postgresql_where=text(
                "certificate_check_id IS NOT NULL AND status NOT IN ('DISMISSED','RESOLVED','UPHELD')"
            ),
        ),
        Index("ix_complaints_status_created_at", "status", "created_at"),
        Index("ix_complaints_talent_created_at", "talent_id", "created_at"),
        Index("ix_complaints_respondent_user_id", "respondent_user_id"),
        Index(
            "ix_complaints_upheld_institution",
            "target_institution_id",
            postgresql_where=text("status = 'UPHELD'"),
        ),
        Index(
            "ix_complaints_upheld_organization",
            "target_organization_id",
            postgresql_where=text("status = 'UPHELD'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
    talent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("talent_profiles.id"), nullable=False)

    subject_type: Mapped[str] = mapped_column(String(30), nullable=False)
    engagement_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("engagements.id"))
    certificate_check_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("certificate_checks.id")
    )
    # The subject's pending state when the complaint was opened (AC-21: "still pending?").
    subject_state: Mapped[str] = mapped_column(String(30), nullable=False)

    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id")
    )
    target_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id")
    )
    respondent_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="OPEN")

    request_note: Mapped[str | None] = mapped_column(Text)
    explanation_text: Mapped[str | None] = mapped_column(Text)
    resolution_reason: Mapped[str | None] = mapped_column(Text)

    explanation_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    explanation_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    explanation_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    @property
    def subject_id(self) -> uuid.UUID:
        subject = self.engagement_id if self.subject_type == "ENGAGEMENT" else self.certificate_check_id
        assert subject is not None  # ck_complaints_subject
        return subject

    @property
    def target_id(self) -> uuid.UUID:
        target = self.target_institution_id if self.target_type == "INSTITUTION" else self.target_organization_id
        assert target is not None  # ck_complaints_target
        return target


class ComplaintEvent(Base):
    __tablename__ = "complaint_events"
    __table_args__ = (
        CheckConstraint("actor_role IN ('TALENT','ADMIN','RESPONDENT')", name="ck_complaint_events_actor_role"),
        CheckConstraint(
            "event_type IN ('CREATED','REVIEW_STARTED','DISMISSED','EXPLANATION_REQUESTED','EXPLANATION_SUBMITTED',"
            "'EXPLANATION_ACCEPTED','EXPLANATION_REJECTED','RESOLVED','UPHELD','ATTACHMENT_ADDED')",
            name="ck_complaint_events_event_type",
        ),
        Index("ix_complaint_events_complaint_created_at", "complaint_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
    complaint_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("complaints.id"), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ComplaintAttachment(Base):
    __tablename__ = "complaint_attachments"
    __table_args__ = (
        CheckConstraint(
            "mime_type IN ('application/pdf','image/jpeg','image/png')", name="ck_complaint_attachments_mime_type"
        ),
        CheckConstraint("size_bytes > 0 AND size_bytes <= 10485760", name="ck_complaint_attachments_size"),
        Index("uq_complaint_attachments_storage_key", "storage_key", unique=True),
        Index("ix_complaint_attachments_complaint_id", "complaint_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
    complaint_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("complaints.id"), nullable=False)
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_etag: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
