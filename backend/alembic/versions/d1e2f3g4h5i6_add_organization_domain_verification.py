"""Add organization domain verification columns and partial unique index

Revision ID: d1e2f3g4h5i6
Revises: c5d6e7f8g9h0
Create Date: 2026-09-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1e2f3g4h5i6"
down_revision: Union[str, None] = "c5d6e7f8g9h0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add domain_verification_token and last_verify_attempt_at to organizations table."""
    # Add nullable columns for domain verification
    op.add_column(
        "organizations",
        sa.Column(
            "domain_verification_token",
            sa.String(),
            nullable=True,
            comment="Random token generated for DNS TXT verification",
        ),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "last_verify_attempt_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp of last verify-domain call (for rate-limit cooldown)",
        ),
    )

    # Create partial unique index: organizations(domain) WHERE verification_level = 'T2' AND deleted_at IS NULL
    # This prevents the same domain from being verified (T2) in multiple organizations
    op.create_index(
        "ix_organizations_domain_verified",
        "organizations",
        ["domain"],
        unique=True,
        postgresql_where=sa.text("verification_level = 'T2' AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Remove domain verification columns and index."""
    # Drop partial unique index
    op.drop_index(
        "ix_organizations_domain_verified",
        table_name="organizations",
    )

    # Drop columns
    op.drop_column("organizations", "last_verify_attempt_at")
    op.drop_column("organizations", "domain_verification_token")
