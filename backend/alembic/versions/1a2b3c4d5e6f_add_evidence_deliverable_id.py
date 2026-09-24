"""Add deliverable_id column to evidence table

Revision ID: 1a2b3c4d5e6f
Revises: 0a1b2c3d4e5f
Create Date: 2026-09-23 14:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision ID and dependencies
revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, None] = "0a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add deliverable_id column to evidence table (AC-4)."""
    op.add_column(
        "evidence",
        sa.Column(
            "deliverable_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Optional FK to deliverables.id (AC-4: ownership chain check)",
        ),
    )
    op.create_foreign_key(
        "fk_evidence_deliverable_id",
        "evidence",
        "deliverables",
        ["deliverable_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove deliverable_id column from evidence table."""
    op.drop_constraint("fk_evidence_deliverable_id", "evidence", type_="foreignkey")
    op.drop_column("evidence", "deliverable_id")
