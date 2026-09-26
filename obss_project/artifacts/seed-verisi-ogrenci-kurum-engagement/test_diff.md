# Test Diff — seed-verisi-ogrenci-kurum-engagement
_Red step (test-copilot) — Haiku alt-ajanı tarafından yazıldı, orkestratör tarafından 2 hata bulunup düzeltildi_

## Oluşturulan Dosya
- `backend/tests/test_seed.py` (490 satır, 8 test fonksiyonu)

## AC Kapsama Tablosu
| AC | Test Fonksiyonu | Not |
|---|---|---|
| AC-1 (happy path) | `test_ac1_happy_path_creates_20_talents_5_institutions_15_engagements` | 20/5/≥5/15 sayı + FK doğrulaması |
| AC-2 (idempotency) | `test_ac2_idempotency_second_run_does_not_change_counts` | İki kez çağrı, sayılar aynı |
| AC-3 (append-only zinciri) | `test_ac3_verified_engagements_have_attestation_and_verified_experience` | **Düzeltildi** — `AuditEvent.engagement_id` diye bir alan yoktu, `subject_type="ATTESTATION"`/`subject_id=attestation.id` olarak düzeltildi (koddan doğrulandı: `attestation.py:357,531`) |
| AC-4 (rollback) | `test_ac4_db_error_during_seeding_causes_full_rollback` | **Düzeltildi** — eskiden kendi mock'unu test ediyordu, artık `register_user`'ı 3. çağrıda hata verecek şekilde mock'layıp GERÇEK `seed_talents()`'ı çağırıyor |
| AC-5 (production guard) | `test_ac5_production_environment_prevents_seeding` | `monkeypatch` ile `settings.environment="production"`, DB'de 0 kayıt assert'i dahil |
| AC-6 (DB bağlantı hatası) | `test_ac6_database_connection_error_raises_meaningful_message` | Kapalı session ile simülasyon |
| AC-7 (FK dağılımı) | `test_ac7_engagement_distribution_respects_fk_constraints` | Eşit olmayan dağılım kabul, FK ihlali yok |
| Baseline | `test_seed_skills_baseline` | Mevcut `seed_skills()` regresyon kontrolü |

## Beklenen Durum: RED
`seed_talents()`, `seed_institutions_and_organizations()`, `seed_engagements()` henüz `backend/scripts/seed.py`'de yok — import `try/except ImportError` ile yakalanıp testler `skipif` ile RED/skip olarak işaretleniyor (implementasyon gelince gerçek testler çalışacak).

## Orkestratör Düzeltmeleri (test-copilot adım 6 — "sub-agent çıktısı yanlışsa Edit yerine yeniden dispatch et")
1. **AuditEvent.engagement_id bug'ı**: Gerçek implementasyon yazılsa bile bu test `AttributeError` ile patlardı (implementasyon eksikliğinden değil, test hatasından) — düzeltilmeden bırakılsaydı sahte bir "red" durumu maskeler, code-copilot doğru implementasyon yazsa bile test hep kırmızı kalırdı.
2. **AC-4 zayıf test bug'ı**: Eski hâli kendi tanımladığı mock fonksiyonu çağırıp kendi `session.rollback()`'ini test ediyordu — gerçek `seed_talents()` implementasyonunun rollback davranışını HİÇ kanıtlamıyordu. Artık `register_user`'ı 3. çağrıda hata verecek şekilde mock'layıp gerçek fonksiyonu çağırıyor.

## Çözülen Açık Nokta (3. düzeltme turu)
"20 öğrenci" sayımı ile "her kullanıcı otomatik TalentProfile alır" gerçeği çelişiyordu — `plan.md`'ye **e-posta önek konvansiyonu** kararı eklendi (`ogrenci{1..20}@seed.local` / `kurum{1..5}-admin@seed.local` / `org{1..N}-admin@seed.local`) ve `test_seed.py`'deki TÜM TalentProfile sayımları (AC-1, AC-2, AC-4) `User.email LIKE 'ogrenci%@seed.local'` filtresiyle JOIN edilecek şekilde düzeltildi. AC-5 (production guard) testi ham sayım kullanmaya devam ediyor — o testte hiç seed çalışmadığı için filtre gereksiz, `count==0` zaten doğru. **code-copilot bu e-posta konvansiyonuna birebir uymalı.**
