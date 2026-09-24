"""Add evidence table for file-based proof uploads

Revision ID: 0a1b2c3d4e5f
Revises: i0j1k2l3m4n5
Create Date: 2026-09-23 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision ID and dependencies
revision: str = "0a1b2c3d4e5f"
down_revision: Union[str, None] = "i0j1k2l3m4n5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create evidence table with soft-delete support."""
    op.create_table(
        "evidence",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="UUIDv7 primary key",
        ),
        sa.Column(
            "owner_talent_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="FK to talent_profiles.id",
        ),
        sa.Column(
            "kind",
            sa.String(50),
            nullable=False,
            comment="Evidence type: REPOSITORY, DOCUMENT, IMAGE, LINK, CERTIFICATE",
        ),
        sa.Column(
            "provenance",
            sa.String(50),
            nullable=False,
            server_default="SELF_UPLOADED",
            comment="Always SELF_UPLOADED in current scope",
        ),
        sa.Column(
            "visibility",
            sa.String(50),
            nullable=False,
            server_default="PRIVATE",
            comment="Always PRIVATE in current scope",
        ),
        sa.Column(
            "scan_status",
            sa.String(50),
            nullable=False,
            server_default="PENDING",
            comment="Virus scan result: PENDING, CLEAN, INFECTED, FAILED",
        ),
        sa.Column(
            "storage_key",
            sa.String(512),
            nullable=False,
            comment="MinIO object key: evidence/{talent_id}/{uuid}.{ext}",
        ),
        sa.Column(
            "mime_type",
            sa.String(255),
            nullable=False,
            comment="File MIME type declared by client",
        ),
        sa.Column(
            "size_bytes",
            sa.Integer(),
            nullable=False,
            comment="File size declared by client",
        ),
        sa.Column(
            "content_hash",
            sa.String(255),
            nullable=True,
            comment="Hash computed by worker during scanning",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="Timestamp when evidence was created",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="Timestamp when evidence was last updated",
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Soft delete timestamp (30-day grace period)",
        ),
        sa.ForeignKeyConstraint(
            ["owner_talent_id"],
            ["talent_profiles.id"],
            name="fk_evidence_owner_talent_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evidence"),
        # CHECK constraints: allowlist and singletons
        sa.CheckConstraint(
            "kind IN ('REPOSITORY', 'DOCUMENT', 'IMAGE', 'LINK', 'CERTIFICATE')",
            name="ck_evidence_kind_allowlist",
        ),
        sa.CheckConstraint(
            "provenance = 'SELF_UPLOADED'",
            name="ck_evidence_provenance_self_uploaded",
        ),
        sa.CheckConstraint(
            "scan_status IN ('PENDING', 'CLEAN', 'INFECTED', 'FAILED')",
            name="ck_evidence_scan_status",
        ),
        sa.CheckConstraint(
            "visibility = 'PRIVATE'",
            name="ck_evidence_visibility_private",
        ),
    )

    # Index: ownership queries (soft-delete excluded)
    op.create_index(
        "ix_evidence_owner_not_deleted",
        "evidence",
        ["owner_talent_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Drop evidence table and related indexes."""
    # Drop index first
    op.drop_index("ix_evidence_owner_not_deleted", table_name="evidence")

    # Drop table (cascades to FKs)
    op.drop_table("evidence")
