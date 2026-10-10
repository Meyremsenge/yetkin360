"""görev doğrulama ve profil/fraud_flags dallarını birleştir

İki migration aynı revizyondan (e7b1d9a3c604) sonra ayrıldı:
  - a9d2f4c7e815: engagement_tasks oluşturan ve doğrulama alanları
  - f2a6c8e0b913: fraud_flags ve profil/sertifika dallarının birleşimi
Birbirinden bağımsızlar (farklı tablolar/kolonlar); bu revizyon yalnız
alembic geçmişini tek başlığa indirir, şemaya dokunmaz.

Revision ID: 53d336a5a854
Revises: a9d2f4c7e815, f2a6c8e0b913
Create Date: 2026-10-10 16:18:12.282136

"""
from typing import Sequence, Union


revision: str = '53d336a5a854'
down_revision: Union[str, Sequence[str], None] = ('a9d2f4c7e815', 'f2a6c8e0b913')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
