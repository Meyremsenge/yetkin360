# Test Diff — yet-70-attestation-verified-experience-uretimi

## Oluşturulan Dosyalar
- `backend/tests/test_attestation.py` (833 satır, 9 test sınıfı) — AC-1..AC-9
- `backend/tests/test_attestation_authorization.py` (598 satır, 6 test sınıfı) — AC-S1..AC-S5 + yetkilendirme matrisi

## AC → Test eşleşmesi
| AC | Test sınıfı/fonksiyonu | Dosya |
|---|---|---|
| AC-1 (happy path, COMPETENCE) | `TestAttestationHappyPath` | test_attestation.py |
| AC-2 (kısmi başarı, downgrade→PARTICIPATION, `NO_DELIVERABLE`) | `TestAttestationPartialSuccessDowngrade` | test_attestation.py |
| AC-3 (EVALUATED değilse 409) | `TestAttestationInvalidState` | test_attestation.py |
| AC-4 (TALENT dener → 403) | `TestAttestationTalentForbidden` | test_attestation.py |
| AC-5 (scope dışı → 404) | `TestAttestationScopeOut` | test_attestation.py |
| AC-6 (eski version → 409) | `TestAttestationVersionConflict` | test_attestation.py |
| AC-7 (geçersiz girdi → 422) | `TestAttestationValidation` | test_attestation.py |
| AC-8 (tekrar gönderim → 409) | `TestAttestationDuplicate` | test_attestation.py |
| AC-9 (institution_id NULL, ORG:SUPERVISOR) | `TestAttestationDirectEngagement` | test_attestation.py |
| AC-S1 (attestor_user_id tampering yok sayılır) | `TestAttestationS1Tampering` | test_attestation_authorization.py |
| AC-S2 (cross-institution → 404) | `TestAttestationS2TenantIsolation` | test_attestation_authorization.py |
| AC-S3 (self-attestation → 409) | `TestAttestationS3SelfAttestationForbidden` | test_attestation_authorization.py |
| AC-S4 (claim_type/downgrade manipülasyonu reddedilir) | `TestAttestationS4ClaimManipulation` | test_attestation_authorization.py |
| AC-S5 (version race condition) | `TestAttestationS5RaceCondition` | test_attestation_authorization.py |
| Ek yetkilendirme matrisi | `TestAttestationAuthorizationMatrixDenied` | test_attestation_authorization.py |

## Uygulanan plan.md Kararları
1. Deliverable-skill basitleştirmesi: downgrade kodu `NO_DELIVERABLE` (atdd.md'deki `NO_DELIVERABLE_FOR_SKILL` değil).
2. `attestations.talent_id` denormalize kolonu varsayıldı (self-attestation CHECK bu kolonla).
3. `version` request body alanı (header değil).
4. Tek uç: `POST /engagements/{id}/attestations`.

## Durum
RED (beklenen) — Attestation/VerifiedExperience modelleri ve servis/route henüz yok, testler ImportError/404 ile başarısız olacak. Sonraki adım: `code-copilot`.
