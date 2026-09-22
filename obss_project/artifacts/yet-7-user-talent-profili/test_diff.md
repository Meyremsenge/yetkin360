# Test Diff — yet-7-user-talent-profili
_Red step — Haiku alt-ajanı tarafından yazıldı, implementasyon henüz yok_

## Oluşturulan dosyalar
- `backend/tests/test_talent.py` (577 satır, 18 test) — fonksiyonel AC-1..AC-8
- `backend/tests/test_talent_authorization.py` (618 satır, 17 test) —
  AC-S1..AC-S3 + izolasyon/hata-şeması testleri

`git status --short tests/` ile ikisinin de diskte olduğu doğrulandı.
İlk 90 satır `Read` edildi — `test_institution.py` kalıbı (gerçek
Postgres session, `X-Debug-User-Id` header, gerçek `TalentProfile`/`User`
modelleri) birebir takip edilmiş.

## AC → Test eşlemesi
| AC | Test fonksiyon(lar)ı | Dosya |
|---|---|---|
| AC-1 | `test_get_me_happy_path`, `test_get_me_returns_current_user_only` | test_talent.py |
| AC-2 | `test_get_me_unauthenticated_401` | test_talent.py |
| AC-3 | `test_patch_talents_me_single_field`, `test_patch_talents_me_multiple_fields`, `test_patch_talents_me_study_year_valid`, `test_patch_talents_me_visibility_valid`, `test_patch_talents_me_public_slug_valid` | test_talent.py |
| AC-4 | `test_patch_talents_me_slug_taken_409`, `test_slug_conflict_no_other_fields_updated` | test_talent.py + authorization.py |
| AC-5 | `test_patch_talents_me_study_year_out_of_range_422` (4 parametrik), `test_patch_talents_me_visibility_invalid_enum_422` (4 parametrik), `test_patch_talents_me_partial_failure_all_rejected` | test_talent.py |
| AC-6 | `test_patch_talents_me_institution_id_ignored` | test_talent.py |
| AC-7 | `test_patch_talents_me_empty_body_200` | test_talent.py |
| AC-8 | `test_patch_talents_me_with_mixed_role_200` (InstitutionMember ile ADMIN + talent_id birlikte) | test_talent.py |
| AC-S1 | `test_get_me_query_user_id_ignored`, `test_get_me_query_talent_id_ignored`, `test_get_me_multiple_override_attempts_ignored` | authorization.py |
| AC-S2 | `test_patch_talents_me_body_user_id_ignored`, `test_patch_talents_me_body_id_ignored`, `test_patch_talents_me_body_talent_profile_id_ignored` | authorization.py |
| AC-S3 | `test_slug_taken_no_user_id_leaked`, `test_slug_taken_response_keys_minimal`, `test_slug_taken_message_is_generic` | authorization.py |
| Ek | `test_error_response_has_code_message_request_id` (hata şeması genel), `test_patch_talents_me_user_b_cannot_modify_a`, `test_get_me_user_b_cannot_read_a_profile` (cross-user izolasyon) | ikisi |

## Kritik tasarım kararları (Haiku alt-ajanı tarafından uygulandı)
- Hata gövdesi testleri `response.json()["code"]`/`["message"]`/`["request_id"]`
  ile TAM EŞLEŞME yapıyor — plan.md Kararlar #1'e uygun, `detail` anahtarı
  KULLANILMADI (postmortem koşum 1'in "gevşek assert" düzeltmesi ve
  projenin gerçek `api_error_handler` sözleşmesi ile tutarlı).
- AC-8 testi `InstitutionMember(role="ADMIN")` ile bir kullanıcıyı hem
  talent hem institution admin yaparak `Principal.kind != "TALENT"`
  senaryosunu gerçekten kuruyor.
- AC-S3 testleri response anahtarlarının `{"code","message","request_id"}`
  ile sınırlı olduğunu (`set(data.keys()) == ...`) doğruluyor — başka
  kullanıcı bilgisi sızmadığını yapısal olarak kanıtlıyor.

## Beklenen durum
RED — `app/api/me.py`, `app/services/talent.py` henüz yok,
`scoped_talent_profiles()` düzeltmesi henüz yapılmadı. `code-copilot`
bunları yazınca testler GREEN olmalı.

## Sonraki adım
`code-copilot` — bu iki test dosyasını referans alarak implementasyonu
yazacak. `scoped_talent_profiles()` değişikliği (authorization.py) atdd.md
Hard Stop onayı kapsamında zaten onaylı, ayrıca sorulmayacak ama
`code-copilot` sonrası `pytest tests/authorization -q` tam paketi mutlaka
çalıştırılacak (CLAUDE.md doğrulama matrisi).
