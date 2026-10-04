"""Widen the verified-domain partial UNIQUE from T2 to T2/T3/T4.

YET-241 (GUV-09b): ix_organizations_domain_verified only covered verification_level = 'T2',
so a T3/T4 org and another T2/T3/T4 org could hold the same domain (admin promotion, races).
The index is dropped and recreated under the same name over T2/T3/T4 (not deleted).
The applied migration d1e2f3g4h5i6 stays untouched.

Upgrade first checks existing data: a clash would otherwise surface as an opaque
index-build error. Only the number of clashing domains is reported, not the values.

Revision ID: b7d3f19a4e26
Revises: a5c9e1f37d42
Create Date: 2026-10-04

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "b7d3f19a4e26"
down_revision = "a5c9e1f37d42"
branch_labels = None
depends_on = None

_INDEX = "ix_organizations_domain_verified"


def upgrade() -> None:
    clashes = op.get_bind().execute(
        sa.text(
            """
            SELECT count(*) FROM (
                SELECT domain FROM organizations
                WHERE domain IS NOT NULL AND deleted_at IS NULL
                  AND verification_level IN ('T2', 'T3', 'T4')
                GROUP BY domain HAVING count(*) > 1
            ) AS clashing
            """
        )
    ).scalar_one()
    if clashes:
        raise RuntimeError(
            f"{clashes} domain(s) are held by more than one active T2/T3/T4 organization; "
            "resolve them before upgrading (YET-241)."
        )

    op.drop_index(_INDEX, table_name="organizations")
    op.create_index(
        _INDEX,
        "organizations",
        ["domain"],
        unique=True,
        postgresql_where=sa.text("verification_level IN ('T2', 'T3', 'T4') AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(_INDEX, table_name="organizations")
    op.create_index(
        _INDEX,
        "organizations",
        ["domain"],
        unique=True,
        postgresql_where=sa.text("verification_level = 'T2' AND deleted_at IS NULL"),
    )
