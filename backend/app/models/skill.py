import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class Skill(Base, TimestampMixin):
    __tablename__ = "skills"
    __table_args__ = (
        CheckConstraint(
            "category IN ('LANGUAGE','FRAMEWORK','TOOL','DOMAIN','SOFT')",
            name="ck_skills_category",
        ),
        CheckConstraint(
            "status IN ('ACTIVE','MERGED','DEPRECATED')",
            name="ck_skills_status",
        ),
        CheckConstraint(
            "status <> 'MERGED' OR merged_into_id IS NOT NULL",
            name="ck_skills_merged_requires_target",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
    slug: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    name_tr: Mapped[str] = mapped_column(String, nullable=False)
    name_en: Mapped[str | None] = mapped_column(String)
    category: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.id"))
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="ACTIVE")
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.id"))
