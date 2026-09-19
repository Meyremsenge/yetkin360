Frontend-pipeline: tetikleyici yok (backend-only görev — atdd.md "Etkilenen Dosyalar" hepsi backend/, "Görsel/UI kriteri" boş).

# Plan — yet-2-yetkilendirme-cekirdegi
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/app/models/__init__.py | Yeni `AuditEvent` modelini export'a ekle (mevcut pattern: `User`, `Skill` vb. gibi) | low |

## New Files
| File | Purpose |
|------|---------|
| backend/app/services/__init__.py | Yeni `services/` paketi (henüz yok — `app/models/` ve `app/core/` yanına, projenin katman kuralı `api/ → services/ → models/`) |
| backend/app/services/authorization.py | `Principal` dataclass, `can()`, `scoped_talent_profiles()`, `scoped_organizations()`, `get_scoped_or_404()` (AC-1..3, AC-5, AC-S1, AC-S2, AC-S5) |
| backend/app/services/audit.py | `log_audit_event()` — PII-guard içerir (AC-4, AC-S6) |
| backend/app/models/audit.py | `AuditEvent` SQLAlchemy modeli — `bigserial` PK (mevcut `TimestampMixin`'i KULLANMAZ, çünkü audit_events'te `updated_at` yok, sadece `created_at`) |
| backend/alembic/versions/<yeni>.py | `audit_events` tablosu + `BEFORE UPDATE OR DELETE` trigger (raw SQL, `op.execute`) — AC-4, AC-S3 |
| backend/tests/test_authorization.py | `can()`/`scoped_*()` testleri — mevcut `test_migration.py`'deki savepoint-fixture deseniyle aynı yapı |
| backend/tests/test_audit_events.py | `log_audit_event()` + immutability trigger testleri |

## Dependencies
- `backend/app/models/base.py`'deki `Base` (DeclarativeBase) — `AuditEvent` de bundan türeyecek, ama `TimestampMixin`'i KULLANMAYACAK (audit_events'te `updated_at` kolonu yok, docs/DATABASE.md §2.8'de sadece `created_at`).
- `backend/app/core/config.py`'deki `settings.database_url` — testlerde `create_engine(settings.database_url)` mevcut `test_migration.py` deseniyle aynı şekilde kullanılacak.
- `backend/app/models/identity.py`'deki `User`, `Organization`, `TalentProfile` modelleri — `scoped_organizations()`/`scoped_talent_profiles()` bunlar üzerinde `select()` çalıştıracak (docs/AUTHORIZATION.md §3.1'deki `scoped_engagements()` örneğiyle aynı desen, ama `Engagement` yerine mevcut modeller).
- Mevcut `institution_members`/`organization_members` tablolarındaki `role` kolonu — `Principal.org_admin_ids` gibi alanların gerçek veriden nasıl türetileceğine dair örnek teşkil eder (bu görevde `Principal` inşası yok ama `can()`/`scoped_*()` bu alanları TÜKETİR, o yüzden şeklini bilmek gerekiyor).

## Migration Required?
**Evet.** `audit_events` tablosu (bigserial PK, append-only, `BEFORE UPDATE OR DELETE` trigger). `docs/DATABASE.md` §2.8'deki DDL'e birebir uyulacak — `YET-1`'in migration'ında olduğu gibi autogenerate + trigger'ın elle eklenmesi (Alembic autogenerate trigger'ları yakalamaz, `op.execute` ile raw SQL gerekir — `YET-1`'in red-team incelemesinde tespit edilen "autogenerate çoklu-kolon CHECK'i kaçırabilir" riskiyle aynı sınıftan bir dikkat noktası).

## Risks
- (atdd.md'den taşındı) `can()`'ın hem action-bazlı yetki tablosu HEM DE resource sahiplik kontrolünü (AC-S5) kendi içinde yapması karmaşıklığı artırabilir — CAVEMAN ilkesiyle dengelenmeli.
- **Yeni bulunan risk:** `audit_events` trigger'ı hem ORM (`session.execute(update(...))`) hem raw SQL (`text("UPDATE audit_events ...")`) yoluyla test edilmeli — SQLAlchemy ORM'in `bulk update` yolu bazen farklı bir SQL üretebilir, trigger'ın her iki yolu da yakaladığından emin olunmalı (atdd.md AC-8/AC-S3 bunu zaten şart koşuyor, plan'da netleştiriliyor).
- **Yeni bulunan risk:** `backend/app/services/` paketi bu görevle birlikte İLK KEZ oluşturuluyor — sonraki görevler (`YET-4/7/8/9`) bu paketin var olduğunu varsayacak, o yüzden `__init__.py`'nin boş ama var olması (Python paketi olarak tanınması) kritik, unutulmamalı.

## Open Questions
(Boş — atdd.md'deki kapsam kararları ve mevcut kod tabanı keşfi bu görevi netleştirmek için yeterli. `services/` paketinin ilk kez oluşturulması bir "risk" olarak yukarıda not düşüldü ama bir karar gerektirmiyor — CLAUDE.md'nin kendi katman kuralı (`api/ → services/ → models/`) zaten bu paketin adını ve konumunu belirliyor.)
