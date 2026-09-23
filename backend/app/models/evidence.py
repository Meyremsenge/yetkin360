"""
Evidence model: stores file evidence records uploaded by talents.

PLAN 2.6 (YET-84, YET-85): Evidence record creation and download URL generation.
Implements append-only semantics with soft delete (30-day grace period).

Schema:
  - id: UUIDv7 PK
  - owner_talent_id: FK to talent_profiles, NOT NULL
  - kind: evidence type (REPOSITORY/DOCUMENT/IMAGE/LINK/CERTIFICATE)
  - provenance: always SELF_UPLOADED (source indicator)
  - scan_status: PENDING/CLEAN/INFECTED/FAILED (virus scan result)
  - visibility: PRIVATE (current scope: only owner can see)
  - storage_key: MinIO object key (evidence/{talent_id}/{uuid}.{ext})
  - mime_type: MIME type declared by client
  - size_bytes: file size declared by client
  - content_hash: NULL (computed by worker during scanning)
  - deleted_at: NULL until soft-delete (30-day grace period)
  - created_at, updated_at: TimestampMixin timestamps

Mutable fields: scan_status, content_hash (updated by worker), deleted_at (soft delete).
Append-only: evidence + outbox + audit_events written atomically, no UPDATE/DELETE on evidence itself.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    DateTime,
    String,
    Integer,
    CheckConstraint,
    Index,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class Evidence(Base, TimestampMixin):
    """Evidence record for file-based proof of skills/achievements."""

    __tablename__ = "evidence"
    __table_args__ = (
        # Kind allowlist: CHECK constraint at DB level
        CheckConstraint(
            "kind IN ('REPOSITORY', 'DOCUMENT', 'IMAGE', 'LINK', 'CERTIFICATE')",
            name="ck_evidence_kind_allowlist",
        ),
        # Provenance: always SELF_UPLOADED in this scope
        CheckConstraint(
            "provenance = 'SELF_UPLOADED'",
            name="ck_evidence_provenance_self_uploaded",
        ),
        # Scan status: PENDING → CLEAN or INFECTED or FAILED
        CheckConstraint(
            "scan_status IN ('PENDING', 'CLEAN', 'INFECTED', 'FAILED')",
            name="ck_evidence_scan_status",
        ),
        # Visibility: currently always PRIVATE
        CheckConstraint(
            "visibility = 'PRIVATE'",
            name="ck_evidence_visibility_private",
        ),
        # Index for ownership/scope queries (soft-deleted excluded)
        Index(
            "ix_evidence_owner_not_deleted",
            "owner_talent_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    # Primary key: UUIDv7
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7_default)

    # Foreign key: owner (talent who uploaded)
    owner_talent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), nullable=False
    )

    # Evidence metadata
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    provenance: Mapped[str] = mapped_column(String(50), nullable=False, default="SELF_UPLOADED")
    visibility: Mapped[str] = mapped_column(String(50), nullable=False, default="PRIVATE")

    # Scanning result (updated by worker)
    scan_status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")

    # File reference in MinIO
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Content hash computed during scanning (NULL until worker processes)
    content_hash: Mapped[str | None] = mapped_column(String(255))

    # Soft delete: NULL until 30-day grace period expires
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
