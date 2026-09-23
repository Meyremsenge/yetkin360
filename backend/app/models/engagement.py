import uuid
from datetime import date

from sqlalchemy import CheckConstraint, ForeignKey, String, false
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class Engagement(Base, TimestampMixin):
    """
    Work engagement: internship, capstone, project, or part-time work.

    YET-7 (engagement-model-olusturma-ucu).
    Append-only table (per CLAUDE.md §3): no UPDATE/DELETE on engagement itself.
    Only status and version can change via ACTIVE/EVALUATED/VERIFIED transitions.
    """
    __tablename__ = "engagements"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('INTERNSHIP','CAPSTONE','SHORT_PROJECT','PART_TIME')",
            name="ck_engagements_kind",
        ),
        CheckConstraint(
            "status IN ('DRAFT','PENDING_APPROVAL','REJECTED','ACTIVE','CANCELLED','PENDING_EVALUATION','EVALUATED','VERIFIED','DISPUTED','RESOLVED')",
            name="ck_engagements_status",
        ),
        CheckConstraint(
            "ended_on IS NULL OR started_on IS NULL OR ended_on >= started_on",
            name="ck_engagements_date_order",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    talent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("talent_profiles.id"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id"), nullable=True
    )
    supervisor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="DRAFT")
    started_on: Mapped[date | None] = mapped_column(nullable=True)
    ended_on: Mapped[date | None] = mapped_column(nullable=True)
    confidential: Mapped[bool] = mapped_column(nullable=False, server_default=false())
    version: Mapped[int] = mapped_column(nullable=False, server_default="1")
