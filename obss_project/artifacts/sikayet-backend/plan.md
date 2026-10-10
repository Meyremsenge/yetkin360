# Plan — sikayet-backend

Kaynak: `atdd.md` (bu klasör). Sıra: test (kırmızı) → kod (yeşil) → verify.

## Dosya etkisi
| Dosya | İş | AC |
|---|---|---|
| `backend/alembic/versions/q7c1m2p3l4n5_add_complaints.py` (yeni, down=`e7b1d9a3c604`) | 3 tablo, CHECK/FK/partial UNIQUE, `complaint_events` immutability trigger, `complaints` delete + terminal-status guard trigger | C1, S14 |
| `backend/app/models/complaint.py` (yeni) + `models/__init__.py` (+1 import, +3 `__all__`) | ORM | C1 |
| `backend/app/core/config.py` (+2 ayar), `.env.example` (+2 satır) | süreler | 13, 14 |
| `backend/app/services/authorization.py` (+`scoped_complaints`, `scoped_admin_complaints`, `scoped_upheld_complaint_counts`) | merkezî kapsam | S9, 18 |
| `backend/app/schemas/complaint.py` (yeni) | Pydantic DTO (ORM'den ayrı, `extra="forbid"` istekler) | S11, 19 |
| `backend/app/services/complaint.py` (yeni) | tüm iş mantığı: açma, türetme, liste, geçiş, gerekçe, ek, sayaç | 13–21 |
| `backend/app/api/complaints.py` (yeni) | öğrenci + yetkili uçları | C2, C5 |
| `backend/app/api/admin_complaints.py` (yeni, `require_platform_admin` import) | admin uçları | C3, C4 |
| `backend/app/main.py` (+2 import, +2 include) | kayıt | — |
| `backend/app/workers/outbox_worker.py` (+3 handler +1 resolver, DEFAULT_HANDLERS +3) / `core/email_messages.py` (+metinler) | bildirim | C6, S13 |
| `backend/app/services/discover.py`, `api/discover.py`, `api/organizations.py`, `api/institutions.py` | `upheld_complaint_count` | C7, 18 |
| `docs/API.md`, `docs/AUTHORIZATION.md` | uç tablosu | — |

## Uçlar
- `POST /complaints`, `GET /complaints`, `GET /complaints/assigned`, `GET /complaints/{id}`
- `POST /complaints/{id}/attachments/upload-url`, `POST /complaints/{id}/attachments`, `GET /complaints/{id}/attachments/{attachment_id}`
- `POST /complaints/{id}/explanation`
- `GET /admin/complaints`, `GET /admin/complaints/{id}`, `GET /admin/complaints/{id}/attachments/{attachment_id}`, `POST /admin/complaints/{id}/transitions`

## Testler (önce yazılır)
- `backend/tests/test_complaints.py` — servis + uç davranışı, durum makinesi, ekler (storage monkeypatch), sayaç, trigger, handler'lar.
- `backend/tests/authorization/test_complaints_authz.py` — rol × uç matrisi (sahip, başka öğrenci, şikayet edilen yetkili,
  aynı kurumun diğer koordinatörü, ilgisiz kurum, platform admini, oturumsuz) + AC-S10 evidence regresyonu.

## Doğrulama
Ayrı test DB (`TEST_DATABASE_URL=..._sikayet_test`, URL ayarlardan türetilir, ekrana basılmaz) — paralel ajanların
`DROP DATABASE` döngüsünden izolasyon. Komutlar: kendi testlerim → `pytest tests/authorization -q` → `pytest -q` (en son) →
`ruff check . && mypy app` → `alembic heads`, `upgrade head`, `downgrade -1`, `upgrade head`.

## Açık soru
Yok (varsayımlar atdd.md'de).
