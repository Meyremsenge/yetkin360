# Test Diff — engagement-model-olusturma-ucu

## Oluşturulan/Genişletilen Dosyalar
- `backend/tests/test_engagement.py` (yeni, 15 test) — AC-1, AC-2, AC-3, AC-5, AC-S3, response schema
- `backend/tests/test_engagement_authorization.py` (yeni, 13 test) — AC-4, AC-S1, AC-S2, AC-S3, AC-S4, 401 senaryoları
- `backend/tests/authorization/test_matrix.py` (düzenlendi) — `test_engagement_access_org_member_read_own_org`, `test_coordinator_scope_filtering`: sahte `assert True` placeholder'ları gerçek `scoped_engagements()` assertion'larına çevrildi (local import, sadece bu iki test etkileniyor)

## AC → Test eşlemesi
| AC | Test |
|---|---|
| AC-1 (happy path) | `test_post_engagement_happy_path_201`, `test_post_engagement_with_institution_id_201`, `test_post_engagement_optional_fields` |
| AC-2 (validation 422) | `test_post_engagement_empty_title_422`, `test_post_engagement_invalid_kind_422`, `test_post_engagement_missing_required_field_422` |
| AC-3 (FK yok → 404) | `test_post_engagement_nonexistent_talent_id_404`, `test_post_engagement_nonexistent_organization_id_404` |
| AC-4 / AC-S1 (yetkisiz talent_id → 404) | `test_talent_create_engagement_for_another_talent_404`, `test_talent_create_engagement_own_talent_succeeds` |
| AC-S2 (yetkisiz organization_id → 404) | `test_org_member_create_for_unauthorized_org_404`, `test_org_member_create_for_own_org_succeeds` |
| AC-5 / AC-S3 (institution eşleşmezliği → 400, sızıntısız) | `test_post_engagement_institution_mismatch_400`, `test_post_engagement_institution_id_null_talent_400`, `test_institution_mismatch_message_consistency_400`, `test_institution_nonexistent_same_error_400`, `test_post_engagement_institution_error_message_generic` |
| AC-S4 (confidential loglanmaz) | `test_post_with_confidential_title_error_no_leak` |
| — (response şema) | `TestEngagementResponseSchema`, `TestAuthErrorResponseSchema` |
| — (scoped_engagements tenant isolation) | `test_engagement_access_org_member_read_own_org`, `test_coordinator_scope_filtering` (test_matrix.py) |

## Doğrulanan kırmızı durum (2026-09-23)
```
3 failed, 30 passed, 4 skipped, 23 errors in 6.01s
```
Tüm failed/error'lar `Engagement`/`scoped_engagements()` eksikliğinden (ImportError/fixture hatası) — beklenen. 30 passed = dokunulmayan mevcut testler sağlam kaldı.

## Bilinen zayıflık (red-team'e not)
`test_engagement_access_org_member_read_own_org` ve `test_coordinator_scope_filtering`
implementasyon sonrası dönen listenin **boş olması** durumunda da (hiç engagement
seed edilmemişse) for-loop assertion'ı vakumla geçer — pozitif "en az bir kayıt
döndü ve doğru kiracıya ait" doğrulaması yok, sadece negatif "yanlış kiracıya ait
kayıt yoksa" doğrulaması var. `code-copilot` sonrası `verify`/`red-team` aşamasında
bu iki testin gerçek veriyle (org_a'ya ait en az 1 engagement seed edilmiş) pozitif
doğrulama yapıp yapmadığı kontrol edilmeli.
