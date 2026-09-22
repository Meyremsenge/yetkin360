# Test Diff — yet-9-organization-domain-dogrulama
_Red step — Haiku alt-ajanı tarafından yazıldı, implementasyon henüz yok_

## Oluşturulan dosyalar
- `backend/tests/test_organization.py` (647 satır, 27 test fonksiyonu) —
  fonksiyonel Acceptance Criteria (AC-1..AC-11)
- `backend/tests/test_organization_authorization.py` (577 satır, 18 test
  fonksiyonu) — güvenlik/tenant-izolasyon Acceptance Criteria (AC-S1..AC-S7)

Her ikisi de `tests/test_institution.py` / `tests/test_institution_authorization.py`
kalıbını birebir takip ediyor: `conftest.py`'nin `session` (gerçek Postgres
transaction + savepoint) ve `client` (TestClient + `X-Debug-User-Id` header)
fixture'ları, `app.models`'tan gerçek `Organization`/`OrganizationMember`/`User`
importu.

## AC → Test eşlemesi
| AC | Test fonksiyon(lar)ı | Dosya |
|---|---|---|
| AC-1 | `test_create_organization_basic`, `test_create_organization_without_domain`, `test_create_organization_without_legal_id`, `test_create_organization_invalid_input` | test_organization.py |
| AC-2 | `test_duplicate_legal_id_returns_409` | test_organization.py |
| AC-3 | `test_admin_invites_member`, `test_admin_invites_admin` | test_organization.py |
| AC-4 | `test_invite_existing_member_returns_409` | test_organization.py |
| AC-5 | `test_verify_domain_free_email_provider_400` (4 parametrik) | test_organization.py |
| AC-6/AC-8 | `test_verify_domain_pending_no_txt_record`, `test_verify_domain_timeout_returns_pending` | test_organization.py |
| AC-7 | `test_verify_domain_success_updates_to_t2` | test_organization.py |
| AC-9 | `test_verify_domain_already_verified_in_another_org_409` | test_organization.py |
| AC-10 | `test_non_admin_invite_member_404`, `test_non_admin_verify_domain_404`, `test_nonexistent_organization_invite_404` | test_organization.py |
| AC-11 | `test_verify_domain_rate_limit_429` | test_organization.py |
| AC-S1 | `test_member_of_org_a_cannot_access_org_b_404`, `test_user_with_no_role_cannot_access_any_org_404`, `test_admin_of_org_a_can_access_org_a` | test_organization_authorization.py |
| AC-S2 | `test_invite_with_invalid_role_422` (4 parametrik), `test_invite_member_invalid_role` | authorization.py + test_organization.py |
| AC-S3 | `test_create_organization_tampering_verification_level`, `test_create_organization_tampering_verified_at`, `test_create_org_with_verification_level_tamper_ignored` | ikisi |
| AC-S4 | `test_verify_domain_second_call_within_60s_429` | authorization.py |
| AC-S5 | `test_verify_domain_rejects_internal_ips` (6 parametrik), `test_verify_domain_hostname_format_validation` | authorization.py |
| AC-S6 | `test_admin_of_org_a_cannot_invite_to_org_b_404`, `test_member_of_org_a_cannot_see_org_b_members_list_404`, `test_member_cannot_invite_to_own_org_404` | authorization.py |
| AC-S7 | `test_create_organization_audit_logged`, `test_invite_member_audit_logged`, `test_verify_domain_audit_logged`, `test_verify_domain_success_audit_logged` | authorization.py |

## Doğrulama (presence check — kalite incelemesi/çalıştırma değil)
`git status --short tests/` ile iki dosyanın da diskte olduğu ve gerçek AC
kapsamına birebir denk düştüğü doğrulandı. Dosyaların içeriği (ilk 100 satır)
okunarak `test_institution.py` deseniyle tutarlı olduğu (fixture'lar, gerçek
model importu) teyit edildi.

## Kritik tasarım kararları (Haiku alt-ajanı tarafından uygulandı)
- Rol enum'u testlerde `ADMIN|MEMBER` (gerçek şema) — atdd.md'nin eski
  `OWNER/SUPERVISOR` ifadeleri yok sayıldı, plan.md "Kararlar" bölümüne uyuldu.
  ana **AC-9/AC-9b/AC-S4/AC-S5 için `alembic` migration henüz yok** — bu
  testler implementasyon + migration olmadan import-error/collection-error
  ile RED kalacak (beklenen).
- DNS resolver `unittest.mock.patch` ile mock'landı — gerçek DNS sorgusu
  yapılmıyor, `verify_domain(..., resolver=...)` enjekte edilebilir arayüz
  varsayımıyla yazıldı (plan.md Kararlar #2 ile tutarlı).
- Rate-limit (AC-11/AC-S4) `last_verify_attempt_at` kolonunun varlığını
  varsayıyor (migration onaylandı, henüz uygulanmadı).

## Beklenen durum
RED — `app/api/organizations.py`, `app/services/organization.py` ve yeni
migration henüz yok. `code-copilot` bunları yazınca testler GREEN olmalı.

## Sonraki adım
`code-copilot` — bu iki test dosyasını referans alarak implementasyonu
yazacak. `dnspython` bağımlılığı ve migration onayı `code-copilot`
başlamadan hemen önce kullanıcıya ayrıca hatırlatılacak (plan.md Kararlar
#2, #3).
