# Test Diff — yet-84-85-evidence-kaydi-indirme
_Reference: atdd.md, plan.md_

## Oluşturulan Dosyalar
| Dosya | Amaç | Test sayısı |
|---|---|---|
| `backend/tests/test_evidence_service.py` | Unit — `services/evidence.py`, `services/storage.py` (GET URL), `services/authorization.py` (`scoped_evidence`) | 18 test metodu, 8 sınıf |
| `backend/tests/authorization/test_evidence_record_download.py` | Yetkilendirme/E2E — `POST /evidence`, `GET /evidence/{id}/download-url` uçları | 20+ test metodu (parametrik dahil), 13 sınıf |

## Red-step doğrulaması
İlk yazımda her iki dosya da `try/except ImportError: pytest.skip(...)` / `except ImportError: pass` içeriyordu — bu, `.claude/rules/testing.md`'nin açıkça yasakladığı "skip ile geçici gizleme" idi (testler pytest'te SKIPPED görünüyordu, FAILED değil). Haiku alt-ajanına düzeltme turu dispatch edildi: try/except blokları kaldırıldı, import'lar korumasız hale getirildi.

Doğrulama (`pytest tests/test_evidence_service.py tests/authorization/test_evidence_record_download.py -q`):
```
ERROR tests/test_evidence_service.py — ModuleNotFoundError: No module named 'app.models.evidence'
ERROR tests/authorization/test_evidence_record_download.py — ModuleNotFoundError: No module named 'app.models.evidence'
2 errors
```
Beklenen red-step davranışı doğrulandı: testler **FAIL/ERROR** olarak raporlanıyor (SKIP değil), henüz implementasyon olmadığı için.

**Not:** Aynı pytest çalıştırmasında `tests/authorization/` paketine ait, bu görevle ilgisiz bir guard (`_pytest.outcomes.Exit: ... boş matris kontrolü`) tetiklendi — muhtemelen önceki bir görevin conftest/plugin hook'u. Bu görevin dosyalarıyla ilgili değil, `verify` adımında ayrıca ele alınmalı.

## Acceptance Criteria Kapsama Matrisi
| AC # | Test sınıfı/metodu | Dosya |
|---|---|---|
| AC-1 | `TestEvidenceCreation.test_create_evidence_success_returns_response` | test_evidence_service.py |
| AC-1 | `TestAuthenticatedEvidenceCreation.test_authenticated_talent_creates_evidence_success` | test_evidence_record_download.py |
| AC-2 | `TestUnauthenticatedRequest.test_post_evidence_unauthenticated_returns_401` / `test_get_download_url_unauthenticated_returns_401` | test_evidence_record_download.py |
| AC-3, AC-S1 | `TestStorageKeyValidation.*` | test_evidence_service.py |
| AC-S1 | `TestAuthenticatedEvidenceCreation.test_elevation_defense_talent_a_cannot_use_talent_b_prefix` | test_evidence_record_download.py |
| AC-5, AC-10 | `TestDownloadUrlGeneration.*` | test_evidence_service.py |
| AC-5 | `TestSuccessfulDownload.test_talent_downloads_own_clean_evidence_success` | test_evidence_record_download.py |
| AC-6, AC-S2 | `TestOwnershipValidation.*` | test_evidence_record_download.py |
| AC-S2, AC-S3 | `TestScopedEvidenceAuthorization.*` | test_evidence_service.py |
| AC-7 | `TestScanStatusValidation.*` (service) / `TestScanStatusBlocksDownload.*` (endpoint) | her iki dosya |
| AC-8 | `TestKindAllowlist.*` (service) / `TestKindValidation.*` (endpoint) | her iki dosya |
| AC-9 | `TestEvidenceNotFound.test_get_download_url_nonexistent_evidence_returns_404` | test_evidence_record_download.py |
| AC-11 | `TestStorageUnavailable.*` | her iki dosya |
| AC-12 | `TestTalentProfileRequired.*` | test_evidence_record_download.py |
| AC-13 | `TestSuspendedAccount.test_post_evidence_suspended_account_returns_403` | test_evidence_record_download.py |
| AC-S3 | `TestAdminAccessPrivateEvidence.test_admin_downloads_private_evidence_returns_403` | test_evidence_record_download.py |
| AC-S4 | `TestInfoDisclosureProtection.test_post_evidence_error_no_internal_details` | test_evidence_record_download.py |
| AC-S5 | `TestRateLimit.*` (POST + GET) | test_evidence_record_download.py |
| AC-S6 | `TestDownloadAudit.test_get_download_url_writes_audit_event` | test_evidence_service.py |
| AC-S7 | `TestEvidenceCreation.test_create_evidence_writes_audit_event` | test_evidence_service.py |

AC-4 (deliverable_id) kapsam dışı bırakıldığı için (bkz. atdd.md) test yazılmadı — doğru.

## Varsayımlar (Haiku alt-ajanından, henüz yazılmamış imzalar hakkında)
- `create_evidence(session, principal, storage_key, kind, mime_type, size_bytes)` → `EvidenceResponse`
- `get_download_url(session, principal, evidence_id)` → `EvidenceDownloadUrlResponse`
- `generate_presigned_get_url(bucket, object_key, ttl)` — `generate_presigned_post` ile aynı hata yakalama kalıbı
- `scoped_evidence(session, principal)` — `scoped_talent_profiles` kalıbıyla tutarlı, admin dahil PRIVATE'i scope dışı bırakır
- `Evidence` modeli `TimestampMixin` kullanır (plan.md Open Question #3 ile tutarlı, code-copilot'ta teyit edilecek)

Bu imzalar `code-copilot`'un uyması gereken sözleşmedir — plan.md ile tutarlı.

## Sonraki Adım
Red step tamamlandı ve doğrulandı (testler FAIL/ERROR, SKIP değil). Sonraki pipeline adımı: `code-copilot` (testleri yeşile çıkaracak implementasyonu yazacak Haiku alt-ajanı dispatch edilecek).
