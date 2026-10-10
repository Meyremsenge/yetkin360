"""portfolio_items ve certificate_checks kurs adı dallarını birleştir

İki migration aynı revizyondan (237dbae3e129) dallandı:
  - a7c3e9d1f2b4: talent_profiles.about + portfolio_items
  - c4e8a1f7b352: certificate_checks kurs adı alanları + BTK sağlayıcısı
Birbirinden bağımsızlar (farklı tablolar/kolonlar); bu revizyon yalnız
alembic geçmişini tek başlığa indirir, şemaya dokunmaz.

Revision ID: d9f1b2c3a4e5
Revises: a7c3e9d1f2b4, c4e8a1f7b352
Create Date: 2026-10-10 18:30:00.000000

"""
from typing import Sequence, Union


revision: str = 'd9f1b2c3a4e5'
down_revision: Union[str, Sequence[str], None] = ('a7c3e9d1f2b4', 'c4e8a1f7b352')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
