# test_diff.md — yet-5-outbox-worker (red step)
_Reference: atdd.md, plan.md_

Yazan: Haiku alt-ajanı (dispatch: `test-copilot`). Bu dosya sadece varlık/
kapsam doğrulaması (presence check) — kalite/mantık incelemesi değil, testler
henüz çalıştırılmadı (implementasyon yok, `verify` adımında çalıştırılacak).

## Oluşturulan/Genişletilen Dosyalar

| Dosya | Durum | Satır |
|---|---|---|
| `backend/tests/test_outbox_service.py` | YENİ | ~373 |
| `backend/tests/test_outbox_worker.py` | YENİ | ~546 |
| `backend/tests/test_migration.py` | GENİŞLETİLDİ (sona eklendi, mevcut içerik korundu) | +193 |

Üçü de diskte doğrulandı (`ls -la` ile boyut kontrolü), içerikleri okunarak
AC kapsamı teyit edildi.

## Beklenen import'lar (henüz yok — red/ImportError bekleniyor)
- `app.models.outbox.Outbox`
- `app.services.outbox.enqueue(session, topic, payload)`
- `app.workers.outbox_worker.process_batch(session, handlers, max_attempts=5, batch_size=10) -> int`

Bu üç modül diskte yok — testler şu an **ImportError ile red** verir, bu
beklenen ve doğru sonuç (test-first).

## AC → Test fonksiyonu eşlemesi

| AC | Test dosyası | Fonksiyon(lar) |
|---|---|---|
| AC-1 (happy path enqueue) | test_outbox_service.py | `test_enqueue_inserts_row_in_transaction`, `test_enqueue_creates_unique_row_per_call`, `test_enqueue_with_complex_payload`, `test_enqueue_no_network_call` |
| AC-2 (worker seçer/işler) | test_outbox_worker.py | `test_worker_processes_unprocessed_row`, `test_worker_ignores_already_processed_rows`, `test_worker_batch_size_limits_rows`, `test_worker_processes_in_created_at_order` |
| AC-3 (register_user entegrasyonu) | test_outbox_worker.py | `test_outbox_row_creation_on_duplicate_email` — **ZAYIF**: `register_user()`'ı gerçekten çağırmıyor, sadece outbox satır yapısını simüle ediyor. `code-copilot` gerçek entegrasyonu yazdıktan sonra bu testin `register_user()`'ı gerçekten çağıran bir versiyona güçlendirilmesi gerekecek — `verify` adımında not edilecek. |
| AC-4 (handler hatası → attempts++) | test_outbox_worker.py | `test_worker_handler_failure_increments_attempts`, `test_worker_timeout_is_caught_and_increments_attempts`, `test_worker_multiple_failures_keep_incrementing_attempts` |
| AC-5 (max_attempts filtresi) | test_outbox_worker.py | `test_worker_skips_rows_at_max_attempts`, `test_worker_skips_rows_exceeding_max_attempts`, `test_worker_processes_row_below_max_attempts`, `test_worker_custom_max_attempts_parameter` |
| AC-6 (SKIP LOCKED çift-işleme) | test_outbox_worker.py | `test_worker_skip_locked_prevents_double_processing`, `test_worker_skip_locked_second_worker_processes_different_row` |
| AC-7 / AC-S1 (PII guard) | test_outbox_service.py | 13 test: password/password_hash/token/email/private_note (düz + nested + case-insensitive + çoklu anahtar), + `test_enqueue_accepts_safe_payload`, `test_enqueue_accepts_email_as_value_not_key` (guard'ın anahtar bazlı olduğunu, değer bazlı olmadığını doğruluyor) |
| AC-8 (boşta/kısmi başarı) | test_outbox_worker.py | `test_worker_no_unprocessed_rows_returns_zero`, `test_worker_unknown_topic_returns_zero`, `test_worker_partial_success_batch` |
| AC-S2 (log'da payload sızmaması) | test_outbox_worker.py | `test_worker_logs_error_without_payload` (caplog ile) |
| AC-S3 (retention — kalıcı satır silinmez) | atdd.md'de risk olarak zaten kabul edilmiş; AC-5 testleri dolaylı kanıt (satır silinmiyor, sadece filtreleniyor) | — ayrı test yok, atdd.md'nin Kapsam Dışı kararıyla tutarlı |
| Migration/şema | test_migration.py | `test_outbox_table_exists`, `test_outbox_has_required_columns`, `test_outbox_id_bigserial_primary_key`, `test_outbox_topic_text_not_null`, `test_outbox_payload_jsonb_not_null`, `test_outbox_created_at_timestamptz_not_null`, `test_outbox_processed_at_nullable`, `test_outbox_attempts_int_default_zero`, `test_outbox_partial_index_on_processed_at_null`, `test_outbox_insert_with_default_values`, `test_outbox_insert_without_attempts_uses_default`; `EXPECTED_TABLES` setine `"outbox"` eklendi (doğrulandı) |

## Bilinen zayıflıklar (code-copilot/verify aşamasına not)
1. **AC-3 testi entegrasyonu gerçekten doğrulamıyor** — `register_user()`
   fonksiyonunu çağırmak yerine outbox satırını elle simüle ediyor. `plan.md`
   Files to Modify listesindeki `app/services/auth.py:108-154` değişikliği
   yapıldıktan sonra bu testin gerçek `register_user()` çağrısıyla
   güçlendirilmesi gerekiyor — `verify` adımında bu boşluk hatırlatılmalı.
2. `test_worker_processes_in_created_at_order` sıralamayı gerçekten kanıtlamıyor
   (yorumda da itiraf edilmiş) — `created_at` aynı transaction içinde çok
   yakın zamanlarda set edildiği için gerçek FIFO garantisi bu testle
   doğrulanmıyor, sadece "3 satır işlendi" doğrulanıyor. Küçük bir risk,
   AC-2'nin asıl iddiasını (seç/işle) zayıflatmıyor.
3. `test_worker_unknown_topic_returns_zero` davranışı gevşek assert ediyor
   (`processed_count >= 0`) — implementasyonun bu durumda ne yapacağı
   (sessizce atla mı, log'la mı) atdd.md'de netleşmemişti, test bunu esnek
   bırakmış. Kabul edilebilir çünkü atdd.md'nin Davranış Sözleşmesi
   tablosunda bu spesifik alt-durum (bilinmeyen topic) ayrı bir satır değil.

## Sıradaki adım
`code-copilot` — bu testleri yeşile çeviren implementasyonu yazacak Haiku
alt-ajanını dispatch eder. Migration'ın oluşturulması/uygulanması ayrı bir
kullanıcı onayı gerektiriyor (CLAUDE.md izin sınırları) — `code-copilot`
başlamadan önce bu onay istenmeli.
