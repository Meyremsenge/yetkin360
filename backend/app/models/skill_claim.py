import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid7_default

if TYPE_CHECKING:
    from app.models.skill import Skill


class SkillClaim(Base, TimestampMixin):
    """
    Skill claim: talent's declared competency.

    AC-1..AC-8 from YET-11.
    Append-only table (per CLAUDE.md §3): no UPDATE/DELETE on claim itself,
    hard-delete is allowed (claimed_level/source/confirmed_by_user_at may be NULL,
    but row can be deleted entirely).
    """
    __tablename__ = "skill_claims"
    __table_args__ = (
        UniqueConstraint("talent_id", "skill_id", name="uq_skill_claims_talent_skill"),
        CheckConstraint(
            "claimed_level IS NULL OR claimed_level IN ('BEGINNER','INTERMEDIATE','ADVANCED')",
            name="ck_skill_claims_claimed_level",
        ),
        CheckConstraint(
            "source IN ('MANUAL','AI_EXTRACTED')",
            name="ck_skill_claims_source",
        ),
        CheckConstraint(
            "source <> 'AI_EXTRACTED' OR confirmed_by_user_at IS NOT NULL",
            name="ck_skill_claims_ai_requires_confirmation",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    talent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("talent_profiles.id"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False
    )
    claimed_level: Mapped[str | None] = mapped_column(String)
    source: Mapped[str] = mapped_column(String, nullable=False, server_default="MANUAL")
    confirmed_by_user_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    skill: Mapped["Skill"] = relationship("Skill")
