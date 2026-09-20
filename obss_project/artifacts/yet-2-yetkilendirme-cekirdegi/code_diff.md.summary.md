# Code Diff Summary — yet-2-yetkilendirme-cekirdegi

(Tam diff `code_diff.md`'de — 1466 satır, ham git diff çıktısı.)

## Oluşturulan dosyalar
- `backend/app/services/__init__.py` — yeni paket (`api/ → services/ → models/` katman kuralı için ilk kez oluşturuldu)
- `backend/app/services/authorization.py` — `Principal`, `can()`, `scoped_organizations()`, `scoped_talent_profiles()`, `get_scoped_or_404()`
- `backend/app/services/audit.py` — `log_audit_event()`, `_check_pii_in_metadata()` (private helper)
- `backend/app/models/audit.py` — `AuditEvent` modeli (bigint PK, `event_metadata` Python adı → `metadata` DB kolonu, `TimestampMixin` kullanılmıyor)
- `backend/alembic/versions/a1b2c3d4e5f6_...py` — `audit_events` tablosu + `BEFORE UPDATE OR DELETE` trigger
- `backend/tests/test_authorization.py`, `backend/tests/test_audit_events.py`

## Değiştirilen dosyalar
- `backend/app/models/__init__.py` — `AuditEvent` export'a eklendi, mevcut export'lar korundu

## AC → İmplementasyon eşlemesi
| AC | Karşılandığı yer |
|---|---|
| AC-1 | `Principal` dataclass, 9 `kind` değeri düz string olarak kabul ediliyor |
| AC-2 | `scoped_organizations()`/`scoped_talent_profiles()` `Select` döner |
| AC-3 | `can()` — `User` için sahiplik (`principal.user_id == resource.id`) |
| AC-4 | `AuditEvent` modeli + `log_audit_event()` INSERT |
| AC-5 | `get_scoped_or_404()` boş sonuçta `None` |
| AC-S1 | `can()` tanımsız action/resource kombinasyonunda `False` (default-deny) |
| AC-S2 | `scoped_*()` SQL `WHERE ... IN (...)` ile filtreleme (Org A/B ile gerçek Postgres testinde doğrulandı) |
| AC-S3 | Trigger `RAISE EXCEPTION ... USING ERRCODE = 'integrity_constraint_violation'` — ORM ve raw SQL, UPDATE ve DELETE'in hepsi test edildi |
| AC-S4 | `get_scoped_or_404()` kapsam-dışı ve gerçekten-yok için aynı `None` |
| AC-S5 | `can()` — `Organization` için `admin_update` action'ında `org_admin_ids` kontrolü (scoped_*() bypass edilse bile) |
| AC-S6 | `_check_pii_in_metadata()` — case-insensitive, nested dict, 4 hassas anahtar |

## Kapsam kontrolü
`docs/AUTHORIZATION.md`'nin tam test matrisi (Engagement/Evidence/Attestation) eklenmedi — atdd.md'nin kapsam kararına uygun. Break-glass, RLS, partition eklenmedi.

## CAVEMAN
Yeni dosya sayısı: 5 (hepsi atdd.md/plan.md'de gerekçelendirilmiş, `services/` paketi ilk kez açılıyor). Gereksiz soyutlama/yardımcı fonksiyon yok — `_check_pii_in_metadata()` tek kullanım yeri olan, inline'a yakın bir private helper.
