import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','ACTIVE','SUSPENDED','DELETED')",
            name="ck_users_status",
        ),
        Index(
            "ix_users_status_active",
            "status",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="ACTIVE")
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Institution(Base, TimestampMixin):
    __tablename__ = "institutions"
    __table_args__ = (
        CheckConstraint(
            "verification_level IN ('T1','T2','T3','T4')",
            name="ck_institutions_verification_level",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
    name: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str | None] = mapped_column(CITEXT, unique=True)
    verification_level: Mapped[str] = mapped_column(String, nullable=False, server_default="T1")
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="ACTIVE")


class InstitutionMember(Base, TimestampMixin):
    __tablename__ = "institution_members"
    __table_args__ = (
        UniqueConstraint("institution_id", "user_id", name="uq_institution_members_institution_user"),
        CheckConstraint("role IN ('ADMIN','COORDINATOR')", name="ck_institution_members_role"),
        Index("ix_institution_members_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)


class TalentProfile(Base, TimestampMixin):
    __tablename__ = "talent_profiles"
    __table_args__ = (
        CheckConstraint("study_year BETWEEN 1 AND 8", name="ck_talent_profiles_study_year"),
        CheckConstraint(
            "visibility IN ('PRIVATE','INSTITUTION','ORGANIZATIONS','PUBLIC')",
            name="ck_talent_profiles_visibility",
        ),
        Index(
            "ix_talent_profiles_institution_id_active",
            "institution_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id")
    )
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    headline: Mapped[str | None] = mapped_column(String)
    department: Mapped[str | None] = mapped_column(String)
    study_year: Mapped[int | None] = mapped_column(SmallInteger)
    city: Mapped[str | None] = mapped_column(String)
    visibility: Mapped[str] = mapped_column(String, nullable=False, server_default="INSTITUTION")
    public_slug: Mapped[str | None] = mapped_column(CITEXT, unique=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"
    __table_args__ = (
        UniqueConstraint("legal_id", name="uq_organizations_legal_id"),
        CheckConstraint(
            "verification_level IN ('T1','T2','T3','T4')",
            name="ck_organizations_verification_level",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
    name: Mapped[str] = mapped_column(String, nullable=False)
    legal_id: Mapped[str | None] = mapped_column(String)
    domain: Mapped[str | None] = mapped_column(CITEXT)
    verification_level: Mapped[str] = mapped_column(String, nullable=False, server_default="T1")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="ACTIVE")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrganizationMember(Base, TimestampMixin):
    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_organization_members_organization_user"),
        CheckConstraint("role IN ('ADMIN','MEMBER')", name="ck_organization_members_role"),
        Index("ix_organization_members_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="ACTIVE")
