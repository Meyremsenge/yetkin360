# test_diff.md — koordinator-dashboard-ucu

## Oluşturulan/Genişletilen Dosyalar
- `backend/tests/test_coordinator_dashboard.py` — YENİ (666 satır), 6 test fonksiyonu
- `backend/tests/test_institution_authorization.py` — GENİŞLETİLDİ, mevcut testler korundu, 8 yeni test + 7 yeni fixture eklendi

## AC → Test Eşleştirme

| AC | Test dosyası / fonksiyonu |
|---|---|
| AC-1 (happy path, sayaçlar) | `test_coordinator_dashboard.py::test_happy_path_summary_counts_and_lists` |
| AC-5 (boş liste → 200, 404 değil) | `test_coordinator_dashboard.py::test_empty_list_200_not_404` |
| AC-6 (geçersiz UUID → 422) | `test_coordinator_dashboard.py::test_invalid_uuid_format_422` |
| AC-2 (geçerli ama scope dışı → 404) | `test_coordinator_dashboard.py::test_valid_uuid_format_but_nonexistent` |
| AC-7 / AC-S3 (confidential karışık, hepsi listelenir) | `test_coordinator_dashboard.py::test_confidential_mixed_both_included` |
| AC-7 / AC-S3 (cross-tenant sızıntı yok) | `test_coordinator_dashboard.py::test_confidential_cross_tenant_never_leaks` |
| AC-2 / AC-S1 (farklı kurum COORDINATOR → 404) | `test_institution_authorization.py::test_coordinator_different_institution_404_no_leak` |
| AC-2 / AC-S1 (farklı kurum ADMIN → 404) | `test_institution_authorization.py::test_admin_different_institution_404_no_leak` |
| AC-3 / AC-S2 (TALENT → 404) | `test_institution_authorization.py::test_talent_principal_404_not_403` |
| AC-3 / AC-S2 (TALENT linked olsa bile → 404) | `test_institution_authorization.py::test_talent_even_with_institution_link_404` |
| AC-3 / AC-S2 (ORG_MEMBER → 404) | `test_institution_authorization.py::test_org_member_404_not_403` |
| AC-4 / AC-S4 (oturumsuz → 401) | `test_institution_authorization.py::test_unauthenticated_no_header_401`, `test_unauthenticated_empty_header_401` |
| AC-4 (geçersiz kullanıcı → 401) | `test_institution_authorization.py::test_invalid_user_id_401` |

## Durum
RED (beklenen) — endpoint (`GET /institutions/{institution_id}/dashboard`) ve servis fonksiyonu (`get_coordinator_dashboard`) henüz yok. `code-copilot` bu testleri yeşile çevirecek implementasyonu yazacak.

## Varsayımlar (sub-agent raporundan)
- Response şeması: atdd.md'deki JSON örneğiyle birebir (`institution_id`, `summary.{pending_approval,pending_evaluation}`, `pending_approval[]`, `pending_evaluation[]`).
- Servis fonksiyonu imzası: `get_coordinator_dashboard(session, principal, institution_id)` — `backend/app/services/engagement.py`'ye eklenecek.
- Yetkilendirme testleri mevcut `X-Debug-User-Id` header test kimlik doğrulama deseniyle uyumlu (conftest.py).
