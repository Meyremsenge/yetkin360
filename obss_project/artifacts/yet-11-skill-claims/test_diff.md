# Test Diff — yet-11-skill-claims
_Red step — Haiku alt-ajanı tarafından yazıldı, implementasyon henüz yok_

## Oluşturulan dosyalar
- `backend/tests/test_skill_claim.py` (640 satır) — fonksiyonel AC-1..AC-8
- `backend/tests/test_skill_claim_authorization.py` (587 satır) —
  AC-S1..AC-S4 izolasyon/güvenlik testleri

`git status --short tests/` ile ikisinin de diskte olduğu doğrulandı. İlk
80 satır `Read` edildi — `test_talent.py` kalıbı (gerçek Postgres session,
`X-Debug-User-Id` header, gerçek `TalentProfile`/`User`/`Skill` modelleri)
birebir takip edilmiş; `SkillClaim` henüz olmadığı için import RED
vermesi beklenen bir durum.

## AC → Test eşlemesi
| AC | Test fonksiyon(lar)ı | Dosya |
|---|---|---|
| AC-1 | `test_post_skills_happy_path`, `test_post_skills_without_claimed_level`, `test_post_skills_with_claimed_level` | test_skill_claim.py |
| AC-2 | `test_get_skills_happy_path`, `test_get_skills_multiple_claims` | test_skill_claim.py |
| AC-3 | `test_delete_skills_happy_path`, `test_delete_skills_then_get_empty` | test_skill_claim.py |
| AC-4 | `test_post_nonexistent_skill_404` | test_skill_claim.py |
| AC-5 | `test_post_duplicate_skill_409` | test_skill_claim.py |
| AC-6 | `test_post_deprecated_skill_404`, `test_post_merged_skill_404` | test_skill_claim.py |
| AC-7 | `test_delete_unclaimed_skill_404`, `test_delete_nonexistent_skill_id_404` | test_skill_claim.py |
| AC-8 | `test_get_skills_empty_200` | test_skill_claim.py |
| AC-S1 | `test_post/get/delete_without_header_401`, `test_post/get/delete_user_without_talent_404` | authorization.py |
| AC-S2 | `test_post_body_talent_id_ignored`, `test_post_no_user_id_field_in_schema` | authorization.py |
| AC-S3 | `test_get_returns_only_own_claims`, `test_get_with_query_param_talent_id_ignored`, `test_bob_cannot_read_alice_claims` | authorization.py |
| AC-S4 | `test_delete_another_talents_claim_404`, `test_delete_own_claim_succeeds`, `test_delete_same_skill_different_scope` | authorization.py |

## Kritik tasarım kararları (Haiku alt-ajanı tarafından uygulandı)
- Hata gövdesi testleri `response.json()["code"]` ile TAM EŞLEŞME yapıyor
  (`SKILL_NOT_FOUND`, `ALREADY_CLAIMED`, `SKILL_CLAIM_NOT_FOUND`) — YET-7'de
  kurulan gerçek hata sözleşmesiyle tutarlı, `detail` anahtarı kullanılmadı.
- MERGED ve DEPRECATED skill'ler için ayrı ayrı fixture + test (`skill_deprecated`,
  `skill_merged`) — her ikisi de plan.md Kararlar #2'ye göre `404 SKILL_NOT_FOUND`
  bekliyor.
- Hard-delete varsayımı (AC-3) — DATABASE.md §2.2'ye göre `deleted_at` yok,
  test `DELETE` sonrası `GET`'te satırın tamamen kaybolduğunu doğruluyor.
- AC-S1 için `talent_id`'si olmayan bir `User` fixture'ı (`user_no_talent`)
  ile gerçek bir senaryo kuruluyor (varsayımsal değil).

## Beklenen durum
RED — `app/models/skill_claim.py`, `app/services/skill_claim.py`,
`app/api/talent_skills.py` ve migration henüz yok. `code-copilot` bunları
yazınca testler GREEN olmalı.

## Sonraki adım
`code-copilot` — bu iki test dosyasını referans alarak implementasyonu
yazacak. Migration onayı zaten `plan.md`'de alındı (skill_claims tablosu,
tek head üzerine — `045883d11996`), `code-copilot` başlamadan önce
kullanıcıya kısaca hatırlatılacak.
