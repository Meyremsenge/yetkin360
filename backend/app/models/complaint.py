"""
Complaint model: a student's complaint about an engagement, decided by the platform admin.

The student (the engagement's talent) reports that the organization side is not
approving a task/certificate or raises a personal problem. The organization is
notified; the admin upholds the complaint (the organization deliberately did
not verify) or dismisses it.

Like fraud_flags this is a mutable review-queue row, not evidence: the admin's
decision updates status. The "deliberate non-verification" mark of an
organization is not stored — it is the count of its UPHELD complaints.

Schema:
  - id: UUIDv7 PK
  - engagement_id, organization_id, talent_id: the engagement and its two sides
    (copied at creation: the organization is who the decision counts against)
  - created_by_user_id: the student's user
  - category: CHECK IN ('TASK_APPROVAL','CERTIFICATE_APPROVAL','PERSONAL')
  - description: the student's statement (PII — never logged, never in outbox)
  - evidence_id: optional document, one of the student's evidence on this engagement
  - status: CHECK IN ('OPEN','UPHELD','DISMISSED'), default OPEN
  - decision_note, decided_by_user_id, decided_at: set together with the decision
  - one OPEN complaint per engagement (partial unique index)
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid7_default


class Complaint(Base):
    """A student's complaint about an engagement; the admin decides."""

    __tablename__ = "complaints"
    __table_args__ = (
        CheckConstraint(
            "category IN ('TASK_APPROVAL','CERTIFICATE_APPROVAL','PERSONAL')", name="ck_complaints_category"
        ),
        CheckConstraint("status IN ('OPEN','UPHELD','DISMISSED')", name="ck_complaints_status"),
        CheckConstraint(
            "(status = 'OPEN') = (decided_at IS NULL)", name="ck_complaints_decided_at_matches_status"
        ),
        CheckConstraint(
            "(decided_at IS NULL) = (decided_by_user_id IS NULL)", name="ck_complaints_decision_has_admin"
        ),
        CheckConstraint("char_length(btrim(description)) > 0", name="ck_complaints_description_not_blank"),
        Index("ix_complaints_status_created_at", "status", "created_at"),
        Index("ix_complaints_organization_status", "organization_id", "status"),
        Index(
            "uq_complaints_one_open_per_engagement",
            "engagement_id",
            unique=True,
            postgresql_where=text("status = 'OPEN'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("engagements.id"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    talent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("talent_profiles.id"), nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="OPEN")
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
