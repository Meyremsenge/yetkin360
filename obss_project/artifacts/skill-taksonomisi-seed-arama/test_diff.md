# Test Diff — skill-taksonomisi-seed-arama
_Reference: atdd.md, plan.md_

## Oluşturulan Dosyalar

### 1. `backend/tests/test_skill_search_authorization.py` (Haiku alt-ajanı, red step)
`GET /skills/search` endpoint'i için authorization + contract testleri.

| AC | Test fonksiyonu |
|---|---|
| AC-1 (happy path) | `test_search_python_returns_200_with_results`, `test_search_results_sorted_alphabetically_by_name_tr`, `test_search_different_principal_kinds_all_200` |
| AC-2 (q validasyonu) | `test_search_missing_q_parameter_400`, `test_search_q_one_char_400`, `test_search_q_two_chars_200_or_empty` |
| AC-3 (boş sonuç) | `test_search_no_matches_200_empty_list`, `test_response_shape_empty` |
| AC-4 (MERGED/DEPRECATED) | `test_search_includes_merged_skills_with_target`, `test_search_excludes_deprecated_skills` |
| AC-5 (401) | `test_search_no_token_401`, `test_search_invalid_user_id_401` |
| AC-9 / AC-S1 (wildcard) | `test_search_with_percent_wildcard_no_error`, `test_search_with_underscore_wildcard_no_error`, `test_search_with_percent_and_underscore_safe` |
| AC-10 / AC-S2 (DB hata sızıntısı yok) | `test_db_connection_error_returns_500_generic_message`, `test_db_error_does_not_leak_query_details` |
| AC-11 / AC-S3 (uzunluk/limit sınırı) | `test_search_q_over_200_chars_400`, `test_search_limit_over_100_400`, `test_search_limit_100_valid`, `test_search_limit_default_20` |
| Sayfalama (varsayım) | `test_search_with_offset_parameter` |
| Response sözleşmesi | `test_response_shape_success`, `test_validation_error_400_has_detail` |

Toplam 24 test. Şu an RED (endpoint yok, 404/import hatası bekleniyor).

### 2. `backend/tests/test_seed_skills.py` (Haiku alt-ajanı, red step + düzeltme)
`backend/scripts/seed.py`'nin `main(session=None)` fonksiyonu için testler.
**Düzeltme notu:** İlk yazımda testlerin çoğu `scripts.seed`'i hiç çağırmadan
manuel SQLAlchemy insert ile PostgreSQL constraint davranışını doğruluyordu —
bu, seed.py hiç yazılmasa da testlerin yeşil kalmasına yol açardı (red step
ihlali). İkinci bir Haiku dispatch'iyle düzeltildi: dosyanın en üstüne
`from scripts.seed import main as seed_main` eklendi (modül seviyesinde —
seed.py yokken tüm dosya collection error verir, doğru "red" davranışı) ve
her test fonksiyonu artık `seed_main(session=session)` çağırıyor.

| AC | Test fonksiyonu |
|---|---|
| AC-6 (boş DB, 100-200 kayıt) | `test_seed_script_creates_100_to_200_skills`, `test_seed_script_slugs_are_unique`, `test_seed_script_categories_satisfy_check_constraint`, `test_seed_script_no_duplicate_slug_error_on_empty_db` |
| AC-7 (idempotency) | `test_seed_script_on_populated_db_does_not_add_duplicates`, `test_seed_script_idempotent_exit_code_0`, `test_seed_script_logs_correct_counts` |
| AC-8 (transaction rollback) | `test_seed_script_accepts_session_parameter`, `test_seed_script_single_transaction_all_or_nothing`, `test_seed_script_idempotent_transaction_safety` (contract-level testler — gerçek rollback senaryosu seed verisi hep valid olacağı için tetiklenemiyor, docstring'de not düşülü) |
| Subprocess entegrasyon (opsiyonel) | `test_seed_script_via_subprocess_empty_db`, `test_seed_script_via_subprocess_idempotency` (`@pytest.mark.skip` ile kapalı, seed.py yazılana kadar) |
| Smoke | `test_seed_creates_at_least_one_skill`, `test_seed_skills_have_all_required_fields`, `test_seed_handles_unicode_names` |

Toplam 15 test (+2 skip). Şu an RED (ImportError — `scripts.seed` modülü yok).

## code-copilot İçin Bağlayıcı Sözleşmeler

- **Seed script imzası:** `def main(session: Session | None = None) -> dict[str, int]` —
  session verilirse onu kullanır, verilmezse kendi session'ını açar. Dönüş değeri
  özet dict (`created`/`skipped`/`total` gibi anahtarlar, testler dönüş değerinin
  tam şeklini zorlamıyor, sadece çağrılabilir olmasını ve DB durumunu bekliyor).
- **Modül yolu:** `backend/scripts/seed.py`, `backend/scripts/__init__.py` (boş,
  paket için).
- **Arama endpoint'i status kodları:** 400 (Pydantic validasyon — testler 422 değil
  400 bekliyor, atdd.md'nin Davranış Sözleşmesi tablosuyla uyumlu, code-copilot'un
  FastAPI'nin varsayılan 422'sini 400'e çeviren bir exception handler/validator
  yazması gerekecek).
- **Response şekli:** `{"items": [...], "total": N}`, her item: `id, slug, name_tr,
  name_en, category, status`, MERGED ise ek olarak `merged_into_id` (+ hedefin
  slug/name_tr'si — test bunu doğrudan doğrulamıyor ama atdd.md AC-4 gerektiriyor).
- **500 hata mesajı:** response body'sinde `OperationalError`, `IntegrityError`,
  `Traceback`, `sqlalchemy`, tablo adı (`skills`) gibi detaylar geçmemeli.

## Doğrulanan
- Her iki dosya da `git status --short` ile diskte izlenmemiş yeni dosya olarak görüldü.
- İçerikleri Read ile incelendi: AC kapsamı eksiksiz, seed testleri gerçek `seed_main()`
  çağrısı üzerinden kuruluyor (manuel ORM insert ile "sahte yeşil" sorunu giderildi).
- Testler bu adımda ÇALIŞTIRILMADI (verify adımının işi) — sadece dosya varlığı ve
  AC kapsaması doğrulandı.

## Sonraki Adım
`code-copilot` — bu plan.md'nin "Files to Modify"/"New Files" listesini ve bu
test_diff.md'deki bağlayıcı sözleşmeleri (seed imzası, status kodları, response şekli)
dosya kapsamı olarak kullanacak.
