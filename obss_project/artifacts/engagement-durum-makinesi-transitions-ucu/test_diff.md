# Test Diff — engagement-durum-makinesi-transitions-ucu

## Oluşturulan Dosya
- `backend/tests/test_engagement_transitions.py` (yeni, 17 test)

## AC → Test eşlemesi
| AC | Test |
|---|---|
| AC-1 (T1 happy path) | `test_transition_draft_to_pending_approval_200` |
| AC-2 (T2 happy path) | `test_transition_pending_to_active_inst_coord_200` |
| AC-3 (T3 happy path) | `test_transition_pending_to_rejected_inst_coord_200` |
| AC-4 (T6 happy path) | `test_transition_active_to_cancelled_org_admin_200`, `test_transition_active_to_cancelled_inst_coord_200` |
| AC-5 (422 ILLEGAL_TRANSITION) | `test_transition_draft_to_verified_illegal_422` |
| AC-6 (422 PRECONDITION_FAILED, institution_id NULL) | `test_transition_institution_null_422` |
| AC-7 (422 PRECONDITION_FAILED, reason boş) | `test_transition_reason_missing_for_reject_422` |
| AC-8 / AC-S3 (403 FORBIDDEN, kaynağa erişimi var) | `test_transition_talent_tries_t2_forbidden_403` (DB'de status değişmediği de assert ediliyor) |
| AC-9 / AC-S1 / AC-S4 (409 CONFLICT) | `test_transition_version_old_409`, `test_transition_concurrent_version_first_wins_second_409`, `test_transition_version_tampering_409` |
| AC-10 (404, kaynak yok) | `test_transition_nonexistent_engagement_404` |
| AC-11 / AC-S2 (404, kaynağa erişimi yok) | `test_transition_no_access_404`, `test_transition_org_member_unauthorized_org_404` |
| Response şema | `TestTransitionResponseSchema` (2 test) |

## Doğrulanan kırmızı durum (2026-09-23)
```
16 failed, 1 passed, 15 warnings in 1.34s
```
16 test route henüz yok olduğu için 404 alıp farklı kod beklediği için fail; 1 test (zaten 404 bekleyen bir senaryo) tesadüfen geçti — implementasyon geldiğinde asıl anlamıyla test edecek.

## Düzeltilen sorun (test-copilot ilk teslimde)
İlk teslimde var olmayan bir model (`InstitutionCoordinator`) import edilmişti — `ImportError` ile TÜM dosyayı (sadece ilgili testi değil) collection aşamasında kırıyordu. Gerçek model `InstitutionMember` (role="COORDINATOR") ile değiştirildi, doğrulandı (`--collect-only` 17 test topladı).

## Bilinen not (red-team'e taşınacak)
`test_transition_concurrent_version_first_wins_second_409` gerçek thread/concurrency değil, sıralı iki çağrı simülasyonu (atdd.md'nin AC-S1'inde de belirtildiği gibi kabul edilebilir — gerçek race condition DB'nin atomik `UPDATE...WHERE` garantisiyle sağlanıyor, test bunu iki sıralı isteğin ikinci başarısız olmasıyla dolaylı doğruluyor).
