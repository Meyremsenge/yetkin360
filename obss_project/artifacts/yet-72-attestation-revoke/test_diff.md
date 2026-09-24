# Test Diff — yet-72-attestation-revoke

## Oluşturulan Dosyalar
- `backend/tests/test_attestation_revoke.py` (10 test) — AC-1, AC-4, AC-5, AC-6, AC-7, AC-S1, AC-S3
- `backend/tests/test_attestation_revoke_authorization.py` (5 test) — AC-2, AC-3, AC-S2

## AC → Test eşleşmesi
| AC | Test | Dosya |
|---|---|---|
| AC-1 (happy path) | `test_revoke_attestation_happy_path_200`, `test_revoke_attestation_tombstone_skill_signal_created` | test_attestation_revoke.py |
| AC-2 (attestor değil→403) | `test_revoke_not_attestor_403`, `test_revoke_talent_403` | test_attestation_revoke_authorization.py |
| AC-3 (cross-tenant→404) | `test_revoke_cross_tenant_404` | test_attestation_revoke_authorization.py |
| AC-4 (yok→404) | `test_revoke_nonexistent_attestation_404` | test_attestation_revoke.py |
| AC-5 (zaten geri çekilmiş→409) | `test_revoke_already_revoked_409` | test_attestation_revoke.py |
| AC-6 (reason boş→422) | `test_revoke_missing_reason_422`, `test_revoke_empty_reason_422` | test_attestation_revoke.py |
| AC-7 (diğer alanlar değişmez) | `test_revoke_preserves_original_fields` | test_attestation_revoke.py |
| AC-S1 (reason loglanmaz) | `test_revoke_audit_event_no_reason_text` | test_attestation_revoke.py |
| AC-S2 (race condition) | `test_revoke_concurrent_simulation_one_succeeds_one_409`, `test_revoke_concurrent_different_actors_same_result` | test_attestation_revoke_authorization.py |
| AC-S3 (trigger izin verilen alanlarla sınırlı) | `test_trigger_prevents_claim_type_update`, `test_trigger_allows_revoked_at_update` | test_attestation_revoke.py |

## Durum
RED (beklenen) — `revoke_attestation()`, `POST /attestations/{id}/revoke`, `scoped_attestations()`, yeni trigger'lar henüz yok. Sonraki adım: `code-copilot`.
