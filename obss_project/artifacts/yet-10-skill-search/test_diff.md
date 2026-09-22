# Test Diff — yet-10-skill-search
_Red step — Haiku alt-ajanı tarafından yazıldı, implementasyon henüz yok_

## Oluşturulan dosyalar
- `backend/tests/test_skill_search.py` (566 satır, ~20 test) — fonksiyonel AC-1..AC-9
- `backend/tests/test_skill_search_authorization.py` (328 satır, ~12 test) —
  AC-S1 (iç alan sızıntısı), AC-S2 (SQL injection), AC-8 (kimlik doğrulama)

`git status --short tests/` ile ikisinin de diskte olduğu doğrulandı. İlk
90 satır `Read` edildi — `test_talent.py` kalıbı (gerçek Postgres session,
`X-Debug-User-Id` header, gerçek `Skill`/`User` modelleri) birebir takip
edilmiş.

## AC → Test eşlemesi
| AC | Test sınıf(lar)ı/fonksiyon(lar)ı | Dosya |
|---|---|---|
| AC-1 | `TestSkillSearchHappyPath` (name_en/tr/slug arama, sadece ACTIVE) | test_skill_search.py |
| AC-2 | `TestSkillSearchNoQuery` (varsayılan limit 50) | test_skill_search.py |
| AC-3 | `TestSkillSearchNoResults` (boş liste, 404 değil) | test_skill_search.py |
| AC-4 | `TestSkillSearchByCategory` | test_skill_search.py |
| AC-5 | `TestSkillSearchInvalidCategory` (422) | test_skill_search.py |
| AC-6 | `TestSkillSearchLimitValidation` (>100 → 422, =100 geçerli, ≤0 → 422) | test_skill_search.py |
| AC-7 | `TestSkillSearchFiltersInactiveStatus` (MERGED/DEPRECATED asla görünmez) | test_skill_search.py |
| AC-8 | `TestSkillSearchAuthentication`/`TestSkillSearchAuthenticationRequired` (401) | ikisi |
| AC-9 | `TestSkillSearchSeeded::test_skill_distribution_across_categories` | test_skill_search.py |
| AC-S1 | `TestSkillSearchResponseSchema` (status/merged_into_id/created_at/updated_at sızmıyor) | authorization.py |
| AC-S2 | `TestSkillSearchSQLInjection` (7 varyant: quote, DROP TABLE, OR, UNION, kategori parametresi, özel karakterler) | authorization.py |

## Kritik tasarım kararları (Haiku alt-ajanı tarafından uygulandı)
- Hata gövdesi testleri `response.json()["code"]` ile TAM EŞLEŞME yapıyor —
  YET-7/YET-9/YET-11'de kurulan gerçek hata sözleşmesiyle tutarlı.
- MERGED/DEPRECATED testleri hem "sonuçlarda hiç görünmüyor" hem "o skill'in
  slug'ıyla direkt arama yapılırsa da bulunamıyor" senaryolarını ayrı ayrı
  kapsıyor.
- SQL injection testleri 7 farklı varyantla (klasik `' OR 1=1`, `DROP TABLE`,
  `UNION SELECT`, kategori parametresinde de) ve "DB bozulmadı, sonraki
  normal arama hâlâ çalışıyor" kontrolüyle kapsamlı.
- Kimlik doğrulama testleri `TalentProfile` gerektirmiyor — `Skill` platform-
  geneli bir kaynak olduğu için düz bir `User` yeterli (atdd.md'nin
  "TALENT'a özel değil" notuna uygun).

## Beklenen durum
RED — `app/api/skills.py`, `app/services/skill.py`, `backend/scripts/seed.py`
henüz yok. `code-copilot` bunları yazınca testler GREEN olmalı.

## Sonraki adım
`code-copilot` — bu iki test dosyasını referans alarak implementasyonu
yazacak. Migration gerekmiyor (Skill tablosu zaten var). Seed script'i
(`~30-50` temsili skill) ve `search_skills()` servis fonksiyonu (merkezi
filtreli sorgu, plan.md Kararlar #1'e göre) code-copilot'ta yazılacak.
