"""fraud_flags sinyalleri ve profil/sertifika dallarını birleştir

İki migration aynı revizyondan (c4e8a1f7b352) sonra ayrıldı:
  - d9f1b2c3a4e5: portfolio_items + certificate_checks dallarının birleşimi
  - e7b1d9a3c604: fraud_flags kurum/kuruluş özneleri ve signal alanı
Birbirinden bağımsızlar (farklı tablolar/kolonlar); bu revizyon yalnız
alembic geçmişini tek başlığa indirir, şemaya dokunmaz.

Revision ID: f2a6c8e0b913
Revises: d9f1b2c3a4e5, e7b1d9a3c604
Create Date: 2026-10-10 20:30:00.000000

"""
from typing import Sequence, Union


revision: str = 'f2a6c8e0b913'
down_revision: Union[str, Sequence[str], None] = ('d9f1b2c3a4e5', 'e7b1d9a3c604')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
