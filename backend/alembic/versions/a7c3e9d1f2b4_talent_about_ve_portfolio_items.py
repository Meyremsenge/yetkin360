"""talent_profiles.about ve portfolio_items tablosu eklendi

docs/arastirma-ogrenci-profili.md §4: "Hakkımda" (kendi beyanı, en fazla 1000
karakter) ve çalışma içi/dışı sertifika/çalışma vitrini. Yalnız ekleme — geriye uyumlu.

Revision ID: a7c3e9d1f2b4
Revises: 237dbae3e129
Create Date: 2026-10-10 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7c3e9d1f2b4'
down_revision: Union[str, None] = '237dbae3e129'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('talent_profiles', sa.Column('about', sa.Text(), nullable=True))
    op.create_check_constraint(
        'ck_talent_profiles_about_length',
        'talent_profiles',
        'about IS NULL OR char_length(about) <= 1000',
    )

    op.create_table(
        'portfolio_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('talent_id', sa.UUID(), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=120), nullable=False),
        sa.Column('issuer', sa.String(length=120), nullable=True),
        sa.Column('issued_on', sa.Date(), nullable=True),
        sa.Column('credential_id', sa.String(length=100), nullable=True),
        sa.Column('external_url', sa.String(length=500), nullable=True),
        sa.Column('evidence_id', sa.UUID(), nullable=True),
        sa.Column('show_on_profile', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("kind IN ('CERTIFICATE','WORK')", name='ck_portfolio_items_kind'),
        sa.CheckConstraint('char_length(title) BETWEEN 1 AND 120', name='ck_portfolio_items_title_length'),
        sa.CheckConstraint(
            'issuer IS NULL OR char_length(issuer) <= 120', name='ck_portfolio_items_issuer_length'
        ),
        sa.CheckConstraint(
            'credential_id IS NULL OR char_length(credential_id) <= 100',
            name='ck_portfolio_items_credential_id_length',
        ),
        sa.CheckConstraint(
            "external_url IS NULL OR (external_url LIKE 'https://%' AND char_length(external_url) <= 500)",
            name='ck_portfolio_items_external_url_https',
        ),
        sa.ForeignKeyConstraint(['talent_id'], ['talent_profiles.id']),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('evidence_id', name='uq_portfolio_items_evidence_id'),
    )
    op.create_index(
        'ix_portfolio_items_talent_not_deleted',
        'portfolio_items',
        ['talent_id'],
        unique=False,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )


def downgrade() -> None:
    op.drop_index('ix_portfolio_items_talent_not_deleted', table_name='portfolio_items')
    op.drop_table('portfolio_items')
    op.drop_constraint('ck_talent_profiles_about_length', 'talent_profiles', type_='check')
    op.drop_column('talent_profiles', 'about')
