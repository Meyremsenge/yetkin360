# code_diff — yet-217-test-izolasyonu
_Yazan: Haiku alt-ajanları (code-copilot). Orkestratör kod yazmadı; Read ile doğrulandı._

## Yeni
- `backend/tests/_testdb.py` — `resolve_test_database_url`, `assert_safe_test_url`, `maintenance_url` (AC-1,2,3; sözleşme satır 4/8).

## Değişen
- `backend/tests/conftest.py` — import sırası: `app.core.config` sonrası, diğer `app.*` öncesi `settings.database_url` test DB'sine çevrilir (+ `DATABASE_URL` env); session-scope autouse `_test_database`: yerelde DROP(FORCE)+CREATE, ardından `alembic upgrade head` (CI'da yalnız upgrade). AC-1,2,3.
- `backend/alembic/env.py` — `fileConfig(..., disable_existing_loggers=False)`. Kanıt: in-process alembic sonrası `app.workers.outbox_worker` logger'ı `disabled=True` oluyor, `caplog` boş kalıyordu (`test_worker_logs_error_without_payload`). Migration dosyası değil (`versions/` değişmedi). **Plan'da yoktu**, bulgu ile eklendi — kullanıcıya bildirildi.
- `.github/workflows/ci.yml` — frontend job'a `npm run test` (AC-7, onaylı).
- `CONTRIBUTING.md` — "Test veritabanı" bölümü (AC-8).

## Test dosyası dokunuşları (code-copilot kapsamı dışı, düzeltme)
- `backend/tests/test_db_isolation.py` satır 45 çelişkili assert silindi (kendi yazdığımız red testte hata; davranış testi değil).

## Gözlenen kusurlar (verify/red-team'e)
- `conftest._test_database`: `except Exception` → `pytest.exit("Cannot connect…")` tüm hataları (DROP/CREATE yetkisi dahil) "bağlanılamadı" diye maskeler; `maint_engine` create_engine hata verirse `finally`'de tanımsız; `except Exception as e` içinde `e` kullanılmıyor.
- `_testdb.resolve_test_database_url`: aynı değeri döndüren gereksiz iç içe `if` (ölü dal).
- `is_local = dev_url != test_url` — dev DB adı "…test" ile bitiyorsa (nadir) drop yapılmaz ve dev DB'ye migration uygulanır.
