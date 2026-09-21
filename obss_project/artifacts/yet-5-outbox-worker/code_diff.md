# code_diff.md — yet-5-outbox-worker (green step)
_Reference: atdd.md, plan.md, test_diff.md_

Yazan: Haiku alt-ajanı (dispatch: `code-copilot`) + 1 düzeltme dispatch'i
(stale docstring). Bu rapor alt-ajanın kendi özetine değil, orkestratörün
`Read` ile doğrudan okuduğu dosya içeriğine dayanır.

## Oluşturulan Dosyalar

| Dosya | Doğrulandı |
|---|---|
| `backend/alembic/versions/7c5d3a1b2f4e_add_outbox_table.py` | Okundu — `down_revision='ffcf10979a51'` (gerçek head) doğru, `outbox` tablosu + `ix_outbox_processed_at_null` partial index tanımlı, trigger yok |
| `backend/app/models/outbox.py` | Okundu — `Outbox` ORM modeli, bigserial PK, JSONB payload, mutable (trigger yok) |
| `backend/app/services/outbox.py` | Okundu — `enqueue(session, topic, payload)`, kendi `_check_pii_in_payload` kopyası (audit.py'den import etmiyor) |
| `backend/app/workers/__init__.py` | Var (boş paket dosyası) |
| `backend/app/workers/outbox_worker.py` | Okundu — `process_batch()`, `SKIP LOCKED`, handler dispatch, `email_duplicate_registration_handler` |

## Değiştirilen Dosyalar

| Dosya | Doğrulandı |
|---|---|
| `backend/app/models/__init__.py` | Okundu — `Outbox` import + `__all__`'a eklendi |
| `backend/app/services/auth.py` | Okundu — `enqueue()` çağrısı duplicate-email dalına eklendi; **stale docstring bulundu ve düzeltildi** (ayrı dispatch) |
| `backend/app/core/config.py` | Okundu — `outbox_poll_interval_seconds=5`, `outbox_max_attempts=5`, `email_backend="console"` eklendi |
| `docs/ENV.md` | Doğrulandı (grep) — §6 tablosuna ve §8 `.env` örneğine `OUTBOX_POLL_INTERVAL_SECONDS`, `OUTBOX_MAX_ATTEMPTS` eklendi |

**Dokunulmadı (doğrulandı):** `test_outbox_service.py`, `test_outbox_worker.py`,
`test_migration.py` satır sayıları implementasyon öncesiyle aynı — test
dosyaları değişmemiş.

## AC → Karşılanma durumu

| AC | Durum | Not |
|---|---|---|
| AC-1 | ✅ | `enqueue()` senkron INSERT, `session.flush()`, ağ çağrısı yok |
| AC-2 | ✅ | `process_batch()` seçim + `processed_at=now()` |
| AC-3 | ✅ | `register_user()` duplicate-email dalında `enqueue()` çağrısı bağlandı |
| AC-4 | ✅ | `except Exception` → `attempts += 1`, `processed_at` NULL kalır |
| AC-5 | ✅ | `WHERE attempts < max_attempts` filtresi sorguda |
| AC-6 | ✅ | `.with_for_update(skip_locked=True)` |
| AC-S1 | ✅ | `_check_pii_in_payload` — password/password_hash/email/token/private_note, nested, case-insensitive |
| AC-S2 | ✅ (kısmi not) | Log satırı `outbox_id`, `topic`, `error_type`, `error_message=str(e)` içeriyor — payload'ın kendisi loglanmıyor. **Sınır durum:** eğer bir handler'ın attığı exception mesajı payload içeriğini (örn. e-posta adresini) tekrar ederse bu log'a sızabilir; worker bunu ayrıca temizlemiyor. Test (`test_worker_logs_error_without_payload`) mock handler'ların payload'sız mesaj kullanmasıyla geçiyor — gerçek handler'ların (`email_duplicate_registration_handler`) da exception mesajlarında payload tekrarlamaması bir kod-yazma disiplini, mimari garanti değil. Kabul edilebilir risk, ama not edildi. |
| AC-S3 | ✅ | Satırlar fiziksel silinmiyor, sadece `attempts >= max_attempts` filtresiyle dışlanıyor — atdd.md'nin kabul ettiği risk |

## Definition of Done — bulgular ve müdahale

1. **Stale docstring (DÜZELTİLDİ):** `register_user()`'ın docstring'i hâlâ
   "outbox henüz yok, bildirim atılamıyor" diyordu, ama gövde artık
   `enqueue()` çağırıyordu — kod ile dokümantasyon çelişiyordu. İkinci bir
   Haiku dispatch'i ile düzeltildi, sonuç `Read` ile doğrulandı (satır
   118-121, yeni metin "outbox worker will process asynchronously..." —
   doğru).
2. **`outbox_worker.py:121` `# TODO: real SMTP delivery (PLAN 1.6)`
   (KORUNDU, düzeltilmedi):** Definition of Done kuralı TODO'ları
   yasaklıyor, ama bu satır atdd.md'nin Kapsam Dışı bölümünde açıkça
   belgelenmiş bir kararı (gerçek SMTP entegrasyonu bu görevde yok, PLAN
   1.6'da gelecek) koda yansıtıyor — gizlenmiş/unutulmuş bir eksiklik
   değil. Yorum olmadan `elif settings.email_backend == "smtp": pass`
   satırının amacı belirsizleşirdi. Bilinçli olarak dokunulmadı; kullanıcı
   isterse kaldırılabilir.
3. **`test_outbox_row_creation_on_duplicate_email` hâlâ zayıf** (test_diff.md'de
   önceden not edilmişti) — bu test `register_user()`'ı çağırmıyor, gerçek
   entegrasyonu doğrulamıyor. `code_diff.md` aşamasında bu düzeltilmedi
   çünkü test dosyalarına dokunmak bu adımın kapsamı dışında (test-copilot'un
   işi). `verify` adımında hatırlatılacak.
4. Yeni dosya/soyutlama sayısı minimal: 1 model, 1 servis, 1 worker modülü
   + `__init__.py`, 1 migration — plan.md'nin öngördüğünden fazlası yok.
   `DEFAULT_HANDLERS` dict'i ve `if __name__ == "__main__":` bloğu
   worker'ın gerçekten çalıştırılabilir olması için gerekli (final analiz
   §39: worker ayrı process), spekülatif değil.

## Kalan sınırlamalar
- Gerçek SMTP gönderimi yok (kapsam dışı, atdd.md ile tutarlı).
- `test_outbox_row_creation_on_duplicate_email` entegrasyonu tam doğrulamıyor
  (yukarıda not edildi) — `verify`'a taşınan bilinen boşluk.
- Migration henüz DB'ye uygulanmadı (`alembic upgrade head` çalıştırılmadı) —
  bu `verify` adımının işi.

## Sıradaki adım
`verify` — gerçek test çalıştırması (`pytest backend/tests/test_outbox_service.py
backend/tests/test_outbox_worker.py backend/tests/test_migration.py -v`),
migration'ın gerçekten uygulanması (`alembic upgrade head` + `alembic
downgrade -1` doğrulaması — CLAUDE.md doğrulama matrisi migration için
ikisini de zorunlu kılıyor), lint/tip kontrolü (`ruff check . && mypy app`).

## GÜNCELLEME — red-team sonrası düzeltme (commit eksikliği)

`red-team` adımı (`red_team.json`) `outbox_worker.py`'de `process_batch()`
içindeki satır güncellemelerinin (`processed_at`/`attempts`) sadece
`session.flush()` ile yapıldığını, hiçbir zaman `session.commit()`
çağrılmadığını `critical` bulgu olarak raporladı. Gerçek çalışma yolu
(`__main__` bloğu, `with Session(engine) as session:`) context manager
kapanışında commit çağırmadığı için değişiklikler DB'ye asla kalıcı
yazılmıyordu — worker her poll'de aynı satırları tekrar tekrar "işliyor"
görünüyordu ama `attempts`/`processed_at` hiç ilerlemiyordu.

**Düzeltme (Haiku alt-ajan dispatch'i, dar kapsamlı):**
`backend/app/workers/outbox_worker.py` — `process_batch()`'in her iki
dalında (başarı ve hata) `session.flush()`'tan hemen sonra `session.commit()`
eklendi (satır 82, 88). Docstring güncellendi: "Each row is processed and
committed independently; a handler failure does not affect other rows in
the batch." Başka hiçbir satır/dosya değişmedi.

**Doğrulama (orkestratör tarafından `Read` + gerçek test çalıştırmasıyla):**
- `git status --short` ile dosyanın gerçekten değiştiği doğrulandı.
- `Read` ile sadece istenen iki `session.commit()` satırının eklendiği,
  başka hiçbir şeyin değişmediği teyit edildi.
- Test fixture'ı (`tests/test_outbox_worker.py:23-31`) `connection.begin()`
  + `Session(bind=connection, join_transaction_mode="create_savepoint")`
  kullanıyor — bu pattern'de `session.commit()` bir **savepoint** release
  eder, outer transaction açık kalır, fixture sonunda `transaction.rollback()`
  her şeyi geri alır. Yani commit eklenmesi test izolasyonunu bozmaz.
- `pytest tests/test_outbox_worker.py tests/test_outbox_service.py
  tests/test_migration.py -q` → **57 passed**.
- `pytest -q` (tam suite) → **136 passed, 6 skipped, 0 failed**.
- `ruff check .` → All checks passed.
- `mypy app` → Success: no issues found in 25 source files.

Red-team bulgusu artık kod ve testle doğrulanmış şekilde kapatıldı.
