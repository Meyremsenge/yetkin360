# Test Diff — public-profil-endpoint (red step)

## Oluşturulan Dosyalar
- `backend/tests/test_public_profile.py` (613 satır) — functional/integration testleri
- `backend/tests/authorization/test_public_profile_authz.py` (520 satır) — güvenlik/enumeration testleri

## AC → Test Eşlemesi
| AC | Test | Dosya |
|---|---|---|
| AC-1 | `test_get_public_profile_success_200`, `test_get_public_profile_empty_experiences_200` | test_public_profile.py |
| AC-2 | `test_get_public_profile_nonexistent_slug_404`, `test_nonexistent_slug_404` | her ikisi |
| AC-3 (AC-S1) | `TestSecurityMatrixRow2/3/4Enumeration`, `test_all_404_responses_byte_identical` | authz dosyası |
| AC-4 (AC-S2) | `test_get_public_profile_response_schema_no_pii_fields`, `test_public_talent_no_pii_fields_ac_s2` | her ikisi |
| AC-5 (AC-S3) | `test_get_public_profile_no_private_experiences`, `test_institution_visibility_experience_filtered`, `test_organizations_visibility_experience_filtered` | her ikisi |
| AC-6 | `test_null_slug_talent_404`, `test_null_slug_404_identical_to_nonexistent` | her ikisi |
| AC-7 | `TestDatabaseErrorHandling` (stub — DB hatası simülasyonu sınırlı) | test_public_profile.py |

## Kritik doğrulama
`test_all_404_responses_byte_identical` — var olmayan slug + PRIVATE + INSTITUTION + ORGANIZATIONS için 404 response'ların `response.content` (ham byte) ve `Content-Length` düzeyinde birebir eşit olduğunu doğruluyor. Sadece status_code kontrolü değil.

## Durum
RED (beklenen) — `app.api.public` ve `app.services.visibility_service` henüz yok, testler import hatasıyla başarısız olacak. Sonraki adım: `code-copilot`.

## Varsayımlar (sub-agent notu)
- `VerifiedExperience.engagement_id` NOT NULL olduğu için her senaryoda minimal bir `Engagement` + `Organization` fixture'ı kuruldu.
- Auth-free endpoint olduğu için testlerde `X-Debug-User-Id` header'ı kullanılmadı.
