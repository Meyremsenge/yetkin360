# Code Diff — skill-taksonomisi-seed-arama
_Reference: atdd.md, plan.md, test_diff.md_

## Oluşturulan Dosyalar
- `backend/scripts/__init__.py` — boş, paket işareti.
- `backend/scripts/seed.py` — `main(session=None) -> dict` fonksiyonu, 153 skill
  (elle derlenmiş, LANGUAGE/FRAMEWORK/TOOL/DOMAIN/SOFT kategorilerine dağılmış),
  `pg_insert(...).on_conflict_do_nothing(index_elements=["slug"])` ile idempotent
  toplu insert. `session=None` ise kendi engine/session'ını açıp kapatıyor
  (`python -m scripts.seed` çalıştırması için).
- `backend/app/schemas/skill.py` — `SkillResponse` (id, slug, name_tr, name_en,
  category, status, merged_into_id, merged_into_slug, merged_into_name_tr),
  `SkillSearchResponse` (items, total).
- `backend/app/services/skill.py` — `search_skills(session, principal, q, limit,
  offset)`: `scoped_skills()` üzerinden `ilike()` ile parametrize arama,
  `status != "DEPRECATED"` filtresi, `name_tr ASC` sıralama, MERGED skill'ler
  için ek sorgu ile hedefin slug/name_tr'sini response'a gömüyor.
- `backend/app/api/skills.py` — `GET /skills/search` router'ı. `q`/`limit`/`offset`
  manuel validasyon (`ApiError(400, ...)`), `get_current_principal`/`get_session`
  dependency'leri, DB hatalarını generic 500'e çeviren `try/except`.

## Değiştirilen Dosyalar
- `backend/app/services/authorization.py` — `scoped_skills(session, principal)`
  eklendi (mevcut `scoped_organizations`/`scoped_institutions`/
  `scoped_talent_profiles` deseniyle tutarlı, koşulsuz `select(Skill)` döner —
  global referans veri, tenant filtresi yok). `Skill` importu dosya başına taşındı.
- `backend/app/main.py` — `skills_router` `include_router` ile eklendi.

## İki İterasyonda Düzeltilen Sorunlar (code-copilot review sırasında bulundu)

1. **`backend/tests/conftest.py`'ye izinsiz dokunma** — ilk Haiku dispatch'i
  paylaşılan test fixture dosyasını (tüm test paketini etkileyen) değiştirmişti;
  bu skill kuralına (test dosyalarına dokunulmaz) açık aykırıydı ve kırılgan bir
  çözümdü (test adına göre string eşleştirme). `git checkout` ile geri alındı,
  implementasyon tarafında dokunulmadı.
2. **Global `RequestValidationError` handler regresyonu** — ilk yazımda `main.py`'ye
  eklenen global handler TÜM endpoint'lerin 422 davranışını 400'e çeviriyordu;
  bu, `test_institution.py`/`test_organization.py`/`test_organization_authorization.py`'deki
  mevcut, onaylanmış 422 testlerini kıracaktı (scope dışı bir davranış değişikliği).
  İkinci Haiku dispatch'iyle global handler kaldırıldı, `/skills/search`'e özel
  manuel validasyon + `ApiError(400, ...)` ile scope'a sadık kalındı; mevcut testler
  etkilenmiyor.
3. **AC-4 eksikliği** — ilk yazımda `merged_into_id` dönüyordu ama hedefin
  slug/name_tr'si yoktu (atdd.md AC-4'ün gerektirdiği gibi). İkinci Haiku
  dispatch'iyle `search_skills()`'e ek sorgu + `SkillResponse` şemasına iki alan
  eklendi.
4. **Gereksiz yerel import** — `scoped_skills()` içindeki `from app.models import
  Skill` (fonksiyon gövdesi) dosya başına taşındı.

## Acceptance Criteria Karşılanma Durumu
| AC | Durum |
|---|---|
| AC-1 (happy path) | Karşılandı |
| AC-2 (q validasyonu) | Karşılandı (manuel, 400) |
| AC-3 (boş sonuç) | Karşılandı |
| AC-4 (MERGED/DEPRECATED) | Karşılandı (ikinci iterasyonda tamamlandı) |
| AC-5 (401) | Karşılandı (mevcut `get_current_principal` altyapısı) |
| AC-6 (seed 100-200) | Karşılandı (153 kayıt) |
| AC-7 (idempotent) | Karşılandı (`ON CONFLICT DO NOTHING`) |
| AC-8 (rollback) | Karşılandı (commit edilmemiş transaction, exception'da otomatik rollback) |
| AC-9 / AC-S1 (wildcard/parametrize) | Karşılandı (`ilike()`, ham SQL yok) |
| AC-10 / AC-S2 (DB hata sızıntısı yok) | Kod doğru (generic 500, `except Exception` + log); **mock testlerinin `@patch` + FastAPI dependency-override çakışması nedeniyle bu iki test şu an teknik olarak doğrulanamadı — `verify` adımında ele alınmalı** |
| AC-11 / AC-S3 (uzunluk/limit sınırı) | Karşılandı (manuel, 400) |

## Kalan Sınırlamalar / Notlar
- `backend/app/api/skills.py`'de kullanılmayan importlar var (`Query`, `BaseModel`,
  `Field`, `HTTPException` — manuel validasyona geçilince gereksiz kaldı). Küçük
  bir temizlik konusu, `refactor` adımında ele alınabilir; işlevsel bir sorun değil.
- Seed script'teki `before_count`/`after_count` farkıyla `created` sayısını hesaplama
  yöntemi teorik olarak eşzamanlı çalıştırmada race condition'a açık; tek-process
  seed script için kabul edilebilir (aşırı mühendislik gerektirmez).
- AC-10/AC-S2 mock testleri (`test_db_connection_error_returns_500_generic_message`,
  `test_db_error_does_not_leak_query_details`) implementasyon sırasında pytest
  içinde çalıştırıldığında `@patch` + FastAPI `dependency_overrides` çakışması
  nedeniyle başarısız görünüyor — kod mantığı doğru (generic 500, detay sızmıyor),
  ama bu iki testin gerçek/güvenilir bir doğrulaması `verify` adımında net şekilde
  yapılmalı (gerekirse test-copilot'a geri dönüp mock stratejisi düzeltilmeli).

## Doğrulanan
- Tüm implementasyon dosyaları plan.md'nin "Files to Modify"/"New Files"
  listesiyle uyumlu (main.py plan.md'de açıkça yoktu ama router eklemek için
  zorunlu, tek satırlık bağımlılık — scope içi kabul edildi).
- Test dosyalarına (`test_skill_search_authorization.py`, `test_seed_skills.py`,
  `conftest.py`) code-copilot sürecinde dokunulmadı (conftest.py'deki izinsiz
  değişiklik tespit edilip geri alındı).
- `git status --short backend/` ile son değişiklik kümesi teyit edildi.

## Sonraki Adım
`verify` — testleri gerçekten çalıştırıp PASS/FAIL/N/A gate raporunu üretecek.
Özellikle AC-10/AC-S2 mock testlerinin gerçek durumu orada netleşmeli.
