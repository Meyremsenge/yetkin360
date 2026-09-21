# Verify Report — yet-5-outbox-worker
_Reference: atdd.md, plan.md, test_diff.md, code_diff.md_

CI komutları `.github/workflows/ci.yml`'den birebir alındı: `ruff check .`,
`mypy app`, `alembic upgrade head`, `pytest -q` (backend/ working-directory).
Python ortamı: `backend/.venv` (proje sanal ortamı, sistem Python değil).
DB: yerel Docker Postgres 16 (`yetkin360-postgres-1`, healthy).

## GÜNCELLEME — ilk turdaki 4 bulgu düzeltildi, tüm gate'ler yeşil

İlk verify turunda (aşağıdaki orijinal tablo) 3 test hatası + 1 lint hatası
bulunmuştu. Bunlar iki ayrı Haiku dispatch'i ile düzeltildi (migration/model/
worker → implementasyon dispatch'i; test_outbox_worker.py'deki SKIP LOCKED
testleri → test-only dispatch'i), sonra bir üçüncü küçük dispatch'le kalan
tek lint hatası (`test_outbox_service.py`'deki kullanılmayan `IntegrityError`)
temizlendi. Her düzeltme orkestratör tarafından `Read` ile bizzat doğrulandı,
ardından TÜM gate'ler baştan çalıştırıldı:

```
ruff check .        → All checks passed!
mypy app             → Success: no issues found in 25 source files
pytest -q            → 136 passed, 6 skipped, 1 warning (0 failed)
alembic downgrade -1 → OK (7c5d3a1b2f4e -> ffcf10979a51)
alembic upgrade head → OK (ffcf10979a51 -> 7c5d3a1b2f4e)
alembic current       → 7c5d3a1b2f4e (head)
```

**Yapılan düzeltmeler:**
1. `outbox.id`: migration'da `sa.Identity()` eklendi (artık gerçek
   PostgreSQL identity/bigserial — `is_identity='YES'`).
2. `outbox.topic`: migration'da `sa.Text()` (önceden `sa.String()` idi,
   `character varying` üretiyordu). `models/outbox.py` ORM tanımı da
   `mapped_column(Text, ...)` ile eşleştirildi.
3. `test_worker_skip_locked_prevents_double_processing` ve
   `test_worker_skip_locked_second_worker_processes_different_row`: test
   tasarımı düzeltildi — satırlar artık bağımsız bir connection'da gerçekten
   `commit()` edilip sonra iki ayrı worker connection'ıyla işleniyor (READ
   COMMITTED izolasyonu altında commit'siz veri görünmüyordu). Cleanup
   `finally` bloğunda elle `DELETE` ile yapılıyor çünkü bu satırlar fixture'ın
   rollback kapsamı dışında commit edildi.
4. 3 kullanılmayan import (`outbox_worker.py`, `test_outbox_service.py`,
   `test_outbox_worker.py`) kaldırıldı.

**Aşağıdaki gate tablosu ve "Bulgular" bölümü ilk turun kaydı olarak
KORUNUYOR** (verify'ın "asla onaysız ✅ konulmaz" ilkesi — ilk kırmızı sonucu
gizlemek yerine, üstüne bu güncelleme eklendi). Genel durum artık **YEŞİL**.

## Verification Gates

| # | Gate | Sonuç | Kanıt / Gerekçe |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `ls -la` ile 6 dosya (migration, model, servis, worker, 2 test) doğrulandı, boyutları code_diff.md/test_diff.md ile tutarlı |
| 2 | Build/derleme | PASS | `.venv` Python ile `import app.models.outbox; app.services.outbox; app.workers.outbox_worker` → `IMPORT_OK` |
| 3 | Supabase şema/canlı doğrulama | N/A | Proje Supabase kullanmıyor (PostgreSQL + SQLAlchemy + Alembic doğrudan) |
| 4 | Lint (`ruff check .`) | **FAIL** | 3 hata: `outbox_worker.py:19` kullanılmayan `text` import (F401); `test_outbox_service.py:13` kullanılmayan `IntegrityError` import (F401); `test_outbox_worker.py:12` kullanılmayan `text` import (F401). Tümü `--fix` ile otomatik düzeltilebilir ama bu adımda düzeltilmedi (kural: verify kendi düzeltmez) |
| 5 | Type check (`mypy app`) | PASS | "Success: no issues found in 25 source files" |
| 6 | Unit/integration testler | **FAIL** | `pytest -q` (tüm suite, backend/): **133 passed, 3 failed, 6 skipped**. 3 hata aşağıda detaylandırıldı |
| 7 | E2E testler | N/A | Bu görev backend-only altyapı, web UI/e2e senaryosu atdd.md kapsamında yok |
| 8 | Lighthouse (performans) | N/A | Web UI yok |
| 9 | Erişilebilirlik | N/A | Web UI yok |
| 10 | Güvenlik taraması | **INCONCLUSIVE** | `~/.claude/security-tools/venv` ve `scan.py` bu makinede kurulu değil (`ls` ile doğrulandı). Detay: `security_scan.md`. PASS DEĞİL — "bilinen imza taraması yapılamadı" |
| 11 | AI code review | PENDING (red-team) | Ayrı pipeline adımına bırakıldı |
| 12 | Görsel regresyon | N/A | Web UI yok |
| 13 | DAST (ZAP) | N/A | Web UI yok, ayrıca threat-model bu görev için sadece backend/DB seviyesi AC-S üretti (HTTP yüzeyi yok) |
| 14 | İnsan onayı | PENDING | Her zaman son adım, henüz alınmadı |

**Ek doğrulama (CLAUDE.md doğrulama matrisi — "Veritabanı şeması/migration" satırı):**

| Kontrol | Sonuç | Kanıt |
|---|---|---|
| `alembic upgrade head` | PASS | `ffcf10979a51 -> 7c5d3a1b2f4e, add outbox table` — hatasız |
| `alembic downgrade -1` | PASS | `7c5d3a1b2f4e -> ffcf10979a51` — hatasız |
| Tekrar `alembic upgrade head` | PASS | `alembic current` → `7c5d3a1b2f4e (head)` |
| `pytest tests/authorization -q` (auth.py değiştiği için zorunlu) | PASS | 57 passed, 6 skipped |

## AC -> Test Mapping (sonuç ile)

| AC | Test fonksiyonu | Sonuç |
|---|---|---|
| AC-1 | `test_enqueue_inserts_row_in_transaction`, `test_enqueue_creates_unique_row_per_call`, `test_enqueue_with_complex_payload`, `test_enqueue_no_network_call` | PASS |
| AC-2 | `test_worker_processes_unprocessed_row`, `test_worker_ignores_already_processed_rows`, `test_worker_batch_size_limits_rows`, `test_worker_processes_in_created_at_order` | PASS |
| AC-3 | `test_outbox_row_creation_on_duplicate_email` | PASS (ama test_diff.md'de not edildiği gibi zayıf — `register_user()`'ı gerçekten çağırmıyor) |
| AC-4 | `test_worker_handler_failure_increments_attempts`, `test_worker_timeout_is_caught_and_increments_attempts`, `test_worker_multiple_failures_keep_incrementing_attempts` | PASS |
| AC-5 | `test_worker_skips_rows_at_max_attempts`, `test_worker_skips_rows_exceeding_max_attempts`, `test_worker_processes_row_below_max_attempts`, `test_worker_custom_max_attempts_parameter` | PASS |
| AC-6 | `test_worker_skip_locked_prevents_double_processing` | PASS |
| AC-6 | `test_worker_skip_locked_second_worker_processes_different_row` | **FAIL** — bkz. Bulgu 3 |
| AC-S1 | 13 PII guard testi (password/password_hash/token/email/private_note, nested, case-insensitive) | PASS |
| AC-S2 | `test_worker_logs_error_without_payload` | PASS |
| AC-8 | `test_worker_no_unprocessed_rows_returns_zero`, `test_worker_unknown_topic_returns_zero`, `test_worker_partial_success_batch` | PASS |
| Migration/şema | `test_outbox_table_exists`, `test_outbox_has_required_columns`, `test_outbox_payload_jsonb_not_null`, `test_outbox_created_at_timestamptz_not_null`, `test_outbox_processed_at_nullable`, `test_outbox_attempts_int_default_zero`, `test_outbox_partial_index_on_processed_at_null`, `test_outbox_insert_with_default_values`, `test_outbox_insert_without_attempts_uses_default` | PASS |
| Migration/şema | `test_outbox_id_bigserial_primary_key` | **FAIL** — bkz. Bulgu 1 |
| Migration/şema | `test_outbox_topic_text_not_null` | **FAIL** — bkz. Bulgu 2 |

## Bulgular (düzeltilmedi — bu skill'in kuralı gereği)

### Bulgu 1 — `outbox.id` gerçek bigserial/identity değil
**Dosya:** `backend/alembic/versions/7c5d3a1b2f4e_add_outbox_table.py:25`
Migration `sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True)`
kullanıyor. PostgreSQL'de bu, `bigint` tipini üretiyor ama **identity/serial
değil** — `information_schema.columns.is_identity` = `'NO'` dönüyor (test
`'YES'` bekliyor). Not: `audit_events` migration'ı da aynı deseni kullanmıştı
ama onun için bu spesifik identity-kontrolü hiç yazılmamıştı — yani bu proje
genelinde var olan, şimdi ilk kez outbox testiyle ortaya çıkan bir örüntü.
**Düzeltme yönü (uygulanmadı):** `sa.BigInteger().with_variant(...)` yerine
`sa.Identity()` kullanılması veya ham `bigserial` tip belirtimi gerekir —
`code-copilot`'a geri dönülmeli.

### Bulgu 2 — `outbox.topic` `text` değil `varchar`
**Dosya:** `backend/alembic/versions/7c5d3a1b2f4e_add_outbox_table.py:26`
`sa.String()` (parametresiz) PostgreSQL'de `character varying` üretiyor,
`text` değil. atdd.md ve docs/DATABASE.md açıkça `topic text NOT NULL`
istiyor (final analiz §12.2). `audit_events.action` alanı da aynı hatayı
taşıyor (`sa.String()`, migration `a1b2c3d4e5f6` satır 28) — yani bu proje
genelinde tekrarlanan bir kalıp, bu görevde ilk kez test tarafından
yakalandı. **Düzeltme yönü (uygulanmadı):** `sa.Text()` kullanılmalı.

### Bulgu 3 — SKIP LOCKED testi transaction izolasyonu yüzünden yanlış varsayımla yazılmış
**Dosya:** `backend/tests/test_outbox_worker.py:381-414`
`test_worker_skip_locked_second_worker_processes_different_row` iki ayrı
DB bağlantısı (`session`, `session2`) kullanıyor ama `session`'ın eklediği
satırlar sadece `flush()` edilmiş, **commit edilmemiş**. PostgreSQL READ
COMMITTED izolasyonunda commit edilmemiş veri başka bir bağlantıya
görünmez — bu, doğrudan bir Python script'iyle doğrulandı (`s2 sees (before
commit): []`). Bu, implementasyon hatası **değil**, test tasarımı hatası:
`test-copilot`'un yazdığı test, aynı fixture deseninin (rollback-only,
commit'siz) çoklu-bağlantı senaryosunda çalışmayacağını hesaba katmamış.
`test_worker_skip_locked_prevents_double_processing` (aynı dosyada, tek
INSERT + tek worker sonra ikinci worker) bu sorunu yaşamıyor çünkü ilk
satır `session` (fixture) tarafından ekleniyor ve `session2` sadece "0
satır" görmesi zaten beklenen davranış (SKIP LOCKED değil, görünürlük
sorunu) ile karışıyor — o test de aslında SKIP LOCKED'ı değil, izolasyonu
test ediyor olabilir, ama assert'i `processed_count_2 == 0` olduğu için
tesadüfen geçiyor.
**Düzeltme yönü (uygulanmadı):** Test, ya `session.commit()` çağırmalı
(fixture'ın rollback-only deseninden sapma) ya da her iki "worker"ın aynı
commit edilmiş veriyi görmesi için satırları ayrı bir setup adımında
(fixture dışında, commit edilmiş) oluşturmalı. Bu, `test-copilot`'a geri
dönülmesi gereken bir test-kalitesi sorunu, implementasyon sorunu değil.

### Bulgu 4 (lint) — 3 kullanılmayan import
`ruff check .` çıktısı: `outbox_worker.py:19` (`text`), `test_outbox_service.py:13`
(`IntegrityError`), `test_outbox_worker.py:12` (`text`). `--fix` ile otomatik
düzeltilebilir, düşük risk, ama bu adımda uygulanmadı.

## Coverage / Quality Notes
- atdd.md'nin AC-S3'ü (retention riski) için ayrı bir test yazılmamıştı —
  bu, atdd.md'nin kendi kararıyla tutarlı (kabul edilen risk, test
  gerektirmiyor).
- `test_outbox_row_creation_on_duplicate_email` (AC-3) gerçek entegrasyonu
  doğrulamıyor — test_diff.md'de zaten flag'lenmişti, code_diff.md'de de
  tekrarlandı. `register_user()`'ı gerçekten çağıran bir versiyon
  eklenmeli.
- Genel test piramidi (60/35/5 unit/integration/e2e hedefi, atdd.md'den):
  gerçekleşen dağılım büyük ölçüde integration-ağırlıklı (gerçek Postgres,
  mock yok) — atdd.md'nin gerekçesiyle (kilitlenme/çift-işleme riski
  gerçek DB olmadan test edilemez) tutarlı.

## Genel Durum (İLK TUR): KIRMIZI — commit'e hazır değildi
_(Bkz. dosya başındaki GÜNCELLEME — düzeltmeler sonrası durum YEŞİL)_

3 test hatası (2 gerçek implementasyon hatası, 1 test-tasarım hatası) ve
1 lint hatası mevcuttu. CLAUDE.md doğrulama matrisi migration için
`alembic upgrade head` + `alembic downgrade -1` + ilgili testleri zorunlu
kılıyor — ilk ikisi PASS ama "ilgili testler" (test_migration.py'nin
outbox kısmı) kısmen FAIL idi.

## Nihai Durum: YEŞİL — insan onayı dışında commit'e hazır

Tüm zorunlu gate'ler PASS: build, lint, type-check, tam pytest suite (136
passed, 0 failed, 6 skipped — skip'ler bu görevden bağımsız, önceden var),
`tests/authorization -q` (57 passed), migration upgrade/downgrade/upgrade
döngüsü. Kalan tek eksik: gate 10 (security-scan) hâlâ **INCONCLUSIVE**
(araç bu makinede kurulu değil — `security_scan.md`), gate 11 (red-team)
**PENDING**, gate 14 (insan onayı) **PENDING**.

## Önerilen sıradaki adım
İmplementasyon/test gate'leri tamam. Sırada: `red-team` (bağımsız kod
incelemesi, commit öncesi son adım) ve ardından kullanıcı onayı + commit.
Security-scan aracının kurulumu ayrı bir konu — kullanıcıya bildirilmeli,
bu görevi bloklamıyor (gate INCONCLUSIVE olarak kaydedildi, PASS değil).
