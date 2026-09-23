# Test Diff — yet-69-degerlendirme-formu-semasi
_Reference: atdd.md, plan.md_

## Oluşturulan Dosyalar (Haiku alt-ajanı tarafından yazıldı, doğrulandı)

- `backend/tests/test_evaluation.py` (905 satır, `git status --short` ile diskte doğrulandı)
- `backend/tests/test_evaluation_authorization.py` (632 satır, `git status --short` ile diskte doğrulandı)

## Acceptance Criteria → Test Fonksiyonu Eşlemesi

| AC | Test Fonksiyonu | Dosya |
|---|---|---|
| AC-1 (happy path) | `test_evaluation_creation_org_to_talent_201`, `test_evaluation_creation_multiple_items_201` | test_evaluation.py |
| AC-2 (T7 geçişi, ORG_TO_TALENT→EVALUATED) | `test_engagement_status_transition_to_evaluated_201` | test_evaluation.py |
| AC-3 (NOT_OBSERVED, comment opsiyonel) | `test_evaluation_not_observed_without_comment_201` | test_evaluation.py |
| AC-4 (items[] boş/criterion eksik → 422) | `test_evaluation_empty_items_422`, `test_evaluation_missing_criterion_422`, `test_evaluation_empty_criterion_string_422` | test_evaluation.py |
| AC-5 (scope dışı → 404) | `test_evaluation_cross_org_scope_out_404`, `test_different_org_member_cannot_evaluate_404`, `test_different_talent_cannot_evaluate_404` | test_evaluation.py + test_evaluation_authorization.py |
| AC-6 (yanlış durum → 409) | `test_evaluation_active_engagement_409` | test_evaluation.py |
| AC-7 (UNIQUE ihlali → 409) | `test_evaluation_duplicate_same_evaluator_direction_409` | test_evaluation.py |
| AC-8 (geçersiz skill_id → 422) | `test_evaluation_invalid_skill_id_422` | test_evaluation.py |
| AC-9 (TALENT_TO_ORG, status değişmez) | `test_evaluation_talent_to_org_no_status_change_201` | test_evaluation.py |
| AC-S1 (private_note PII, testing.md'nin en yüksek öncelikli kuralı) | `test_private_note_not_in_response_org_to_talent`, `test_private_note_not_in_response_talent_to_org` | test_evaluation_authorization.py |
| AC-S2 (evaluator_user_id tampering) | `test_evaluator_user_id_from_principal_org_member` | test_evaluation_authorization.py |
| AC-S3 (direction/rol tutarsızlığı → 403, plan aşamasında düzeltildi) | `test_talent_cannot_post_org_to_talent_403`, `test_org_member_cannot_post_talent_to_org_403`, `test_coordinator_cannot_post_org_to_talent_403`, `test_coordinator_cannot_post_talent_to_org_403` | test_evaluation_authorization.py |
| Response şeması | `test_evaluation_success_response_schema_201`, `test_evaluation_error_response_schema` | test_evaluation.py |
| Yetkilendirme matrisi (pozitif) | `test_talent_can_post_talent_to_org_201`, `test_org_member_can_post_org_to_talent_201` | test_evaluation_authorization.py |

## Durum
**RED (beklenen).** `app.models.Evaluation`/`EvaluationItem` henüz yok (import `try/except` ile yumuşatılmış, `None` fallback), `POST /engagements/{id}/evaluation` endpoint'i henüz yok. Testler ya import hatasından ya da 404'ten başarısız olacak — bu, test-first akışının "red" adımıdır.

## Sonraki Adım
`code-copilot` — bu testleri geçirecek implementasyonu (models/evaluation.py, schemas/evaluation.py, services/evaluation.py, engagements.py'ye endpoint, migration) yazacak Haiku alt-ajanını dispatch edecek. plan.md'nin "Files to Modify"/"New Files" listesi + bu test_diff.md dosya kapsamı olarak kullanılmalı.

**Not:** Migration oluşturma/uygulama adımından önce CLAUDE.md gereği kullanıcıdan ayrıca açık onay istenecek — code-copilot bu adıma gelince duracak.
