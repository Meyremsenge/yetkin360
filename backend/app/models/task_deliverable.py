"""
Engagement Task and Deliverable models.

YET-66 (engagement-task-deliverable, PLAN 2.4).
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class EngagementTask(Base, TimestampMixin):
    """
    Task within an engagement: represents a unit of work that the talent performs.

    PLAN 2.4 (AC-1): Task creation endpoint POST /engagements/{id}/tasks.
    PLAN 2.3: T5 precondition references deliverables, not tasks.
    PLAN 2.9 (YET-71): Task can be associated with a skill_id for SkillSignal generation.

    Verification: a task added by the talent is unverified (verified_at IS NULL)
    until an organization member or the institution's coordinator verifies it;
    only a verified task produces a SkillSignal. A task added by an organization
    member or coordinator is verified on creation.
    """
    __tablename__ = "engagement_tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PLANNED','IN_PROGRESS','DONE')",
            name="ck_engagement_tasks_status",
        ),
        CheckConstraint(
            "verified_by_user_id IS NULL OR verified_at IS NOT NULL",
            name="ck_engagement_tasks_verifier_needs_verified_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("engagements.id"), nullable=False
    )
    skill_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="PLANNED")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # NULL for rows created before this column existed.
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class Deliverable(Base, TimestampMixin):
    """
    Deliverable submitted by talent: evidence of work completion.

    PLAN 2.4 (AC-2): Deliverable submission endpoint POST /engagements/{id}/deliverables.
    PLAN 2.4 (AC-6/AC-7): T5 precondition requires at least 1 Deliverable.
    PLAN 2.9 (YET-71): Deliverable can be associated with a skill_id for SkillSignal generation.

    Note: Evidence.id linking is deferred to PLAN 2.6 (out of scope for this task).
    """
    __tablename__ = "deliverables"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("engagements.id"), nullable=False
    )
    skill_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    submitted_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
