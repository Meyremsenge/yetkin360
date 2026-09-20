"""
AuditEvent model: append-only audit log for compliance and security monitoring.

Implements AC-4, AC-S3 (immutability via trigger).
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditEvent(Base):
    """
    Append-only audit event log.

    Schema:
      - id: BigInteger PK (autoincrement bigserial)
      - actor_user_id: UUID of actor (nullable)
      - actor_ip: INET address of actor (nullable)
      - action: Event action name (text, not null)
      - subject_type: Type of affected resource (text, not null)
      - subject_id: UUID of affected resource (nullable)
      - result: Outcome: 'SUCCESS', 'DENIED', or 'ERROR' (CHECK constraint)
      - event_metadata: JSONB metadata (DB column name: "metadata", nullable)
      - created_at: Timestamp (timestamptz, not null, server_default)

    Immutability: BEFORE UPDATE OR DELETE trigger blocks all modifications.
    No updated_at column (audit_events are append-only).
    """

    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint(
            "result IN ('SUCCESS','DENIED','ERROR')",
            name="ck_audit_events_result",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actor_ip: Mapped[str | None] = mapped_column(INET)
    action: Mapped[str] = mapped_column(nullable=False)
    subject_type: Mapped[str] = mapped_column(nullable=False)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    result: Mapped[str] = mapped_column(nullable=False)
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
