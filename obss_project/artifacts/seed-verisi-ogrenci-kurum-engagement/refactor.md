# Refactor — seed-verisi-ogrenci-kurum-engagement

Ön koşul: tüm testler yeşil (verify_report.md gate 6, 8/8 PASS). Kullanıcı onayıyla refactor uygulandı.

## Uygulanan Değişiklik
`backend/scripts/seed.py` — `seed_engagements()` fonksiyonunun ~150-200 satırlık döngü gövdesi (tek bir öğrenci/engagement için `create_engagement` → `transition_engagement` ×3 → tarih ayarlama → `create_engagement_task`+`create_deliverable` → `create_evaluation` → `create_attestation` zinciri) ayrı bir `_create_verified_engagement(session, talent, organization, institution, sample_skill, eng_idx) -> Engagement` yardımcı fonksiyonuna çıkarıldı. Ana döngü artık talent/organization/institution seçimi + helper çağrısı + exception handling'e indirgendi.

**Gerekçe:** Ölçülebilir — tek bir yerde tekrarlanan (döngü içinde) 150+ satırlık fonksiyon gövdesi, uzun fonksiyon/tekrar kriterlerini karşılıyordu (verify_report.md'de tespit edildi).

## Doğrulama
- `ruff check scripts/seed.py tests/test_seed.py` → **All checks passed!**
- `mypy scripts/seed.py` → **Success: no issues found**
- `pytest tests/test_seed.py -v` → **8/8 PASS** (davranış korundu, test dosyasına dokunulmadı)

## Denenip Geri Alınanlar
Yok — tek adımda başarılı oldu.

## Dokunulmayıp Not Düşülenler
Yok — kapsam (tek dosya, tek fonksiyon) içinde başka bir aday görülmedi.

## Sonraki adım
`red-team`.
