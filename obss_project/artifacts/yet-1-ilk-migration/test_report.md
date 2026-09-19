# Test Report — yet-1-ilk-migration

## Gerçek Postgres'e karşı (docker-compose, quay.io/minio + postgres:16, healthy)

- `alembic upgrade head` (boş DB) → hatasız, 7 tablo oluştu
- `alembic upgrade head` (zaten head'de, tekrar) → no-op, hatasız (AC-7)
- `alembic downgrade -1` → hatasız, 7 tablo silindi (AC-5)
- `alembic upgrade head` (round-trip) → hatasız, tekrar oluştu (AC-6)
- `pytest tests/ -v` → **10 passed** (test_health.py: 1, test_migration.py: 9)
  - `test_all_seven_tables_exist` — 7 tablonun varlığı (AC-1)
  - `test_users_status_check_rejects_invalid_value` — CHECK ihlali → IntegrityError (AC-3)
  - `test_users_email_unique_constraint` — UNIQUE ihlali → IntegrityError (AC-4)
  - `test_institution_members_role_check_rejects_invalid_value` — CHECK ihlali (AC-3)
  - `test_institution_members_unique_pair` — UNIQUE(institution_id,user_id) ihlali (AC-4)
  - `test_talent_profiles_study_year_check` — CHECK BETWEEN 1 AND 8 ihlali (AC-3)
  - `test_skill_merged_requires_target` — çoklu-kolon CHECK (status<>'MERGED' OR merged_into_id IS NOT NULL) ihlali (AC-3) — autogenerate'in kaçırabileceği türden bir constraint, doğrulandı
  - `test_skill_merged_with_target_succeeds` — aynı CHECK'in geçerli durumda geçtiği (negatif kontrol)
  - `test_organization_legal_id_unique_when_present` — partial UNIQUE semantiği (NULL'lar UNIQUE'te çakışmaz, dolu değerler çakışır)
- `ruff check .` → All checks passed
- `mypy app` → Success: no issues found in 8 source files

## CI simülasyonu (tamamen temiz DB, extension önceden oluşturulmamış)
Gerçek CI akışını taklit etmek için ayrı bir "test" veritabanı oluşturuldu (hiçbir extension/tablo yok), sonra:
- `alembic upgrade head` → hatasız (migration'ın kendi içindeki `CREATE EXTENSION IF NOT EXISTS citext` çalıştı)
- `pytest -q` → 10 passed

Bu, `.github/workflows/ci.yml`'e eklenen postgres service container'ının gerçekten yeterli olduğunu kanıtlıyor — CI'da ayrıca elle `CREATE EXTENSION` çalıştırmaya gerek yok.

## Index düzeltmesi (red-team sonrası)
Red-team incelemesi docs/DATABASE.md'de açıkça istenen 4 index'in migration'da eksik olduğunu buldu (institution_members.user_id, organization_members.user_id, talent_profiles.institution_id partial, users.status partial). Modellere eklendi, migration `b82aa928fbd2` olarak yeniden üretildi (eski `d3696712a323` silindi), tam zincir tekrar doğrulandı: upgrade head → upgrade head (no-op) → downgrade -1 → upgrade head (round-trip) → `pytest -q` (10 passed) → `ruff check .` (All checks passed) → `mypy app` (Success: no issues found in 8 source files).

## Bulunan ve düzeltilen sorunlar
1. Autogenerate ilk halinde `CREATE EXTENSION citext` içermiyordu — temiz bir DB'de migration patlardı. Elle eklendi (upgrade'de CREATE, downgrade'de DROP).
2. `.github/workflows/ci.yml`'de gerçek bir Postgres servisi yoktu, sahte bir `DATABASE_URL` vardı — `test_migration.py` gerçek DB'ye ihtiyaç duyduğu için CI'ı kırardı. Postgres service container eklendi, `alembic upgrade head` adımı pytest'ten önce eklendi.
3. İlk test taslağında `session.commit()` sonrası `pytest.raises` bekleniyordu ama SQLAlchemy Core `execute()` hatayı flush anında fırlatıyor — test düzeltildi.
4. İlk test çalıştırmasında fixture `session.rollback()` kullanıyordu ama testler içeride `session.commit()` çağırdığı için veri kalıcı oluyor, ikinci koşuda UNIQUE ihlaline çarpıyordu — fixture connection+savepoint tabanlı izolasyona çevrildi (`join_transaction_mode="create_savepoint"`).
