"""Add auth_rate_limits (DB-backed fixed-window counters for identity endpoints).

YET-186 (GUV-11): login, register, forgot/reset-password, verify-email and
refresh had no rate limit. Redis is out of scope (CLAUDE.md), so the counters
live in PostgreSQL and are bumped with one atomic INSERT .. ON CONFLICT, which
holds across workers and restarts.

key_hash is an HMAC of the IP / e-mail (no raw PII). The window_start index
serves the opportunistic cleanup of expired windows.

Revision ID: a5c9e1f37d42
Revises: f4b8d2a60c17
Create Date: 2026-10-03

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "a5c9e1f37d42"
down_revision = "f4b8d2a60c17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_rate_limits",
        sa.Column("bucket", sa.Text(), nullable=False),
        sa.Column("key_hash", sa.Text(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("bucket", "key_hash", "window_start"),
        sa.CheckConstraint("count >= 0", name="ck_auth_rate_limits_count_nonneg"),
    )
    op.create_index("ix_auth_rate_limits_window_start", "auth_rate_limits", ["window_start"])


def downgrade() -> None:
    op.drop_index("ix_auth_rate_limits_window_start", table_name="auth_rate_limits")
    op.drop_table("auth_rate_limits")
