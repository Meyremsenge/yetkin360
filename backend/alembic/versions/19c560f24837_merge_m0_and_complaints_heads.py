"""M0 (kuruluş birimi/vitrin) ve şikayet dallarını birleştir

İki migration aynı revizyondan (53d336a5a854) sonra ayrıldı:
  - c15c0d0133f7: organization_members.unit ve organizations.showcase_public
  - q7c1m2p3l4n5: complaints tabloları
Birbirinden bağımsızlar (farklı tablolar/kolonlar); bu revizyon yalnız
alembic geçmişini tek başlığa indirir, şemaya dokunmaz.

Revision ID: 19c560f24837
Revises: c15c0d0133f7, q7c1m2p3l4n5
Create Date: 2026-10-10 23:29:09.304388

"""
from typing import Sequence, Union


revision: str = '19c560f24837'
down_revision: Union[str, Sequence[str], None] = ('c15c0d0133f7', 'q7c1m2p3l4n5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
