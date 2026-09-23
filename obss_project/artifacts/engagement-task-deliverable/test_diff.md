# Test Diff — engagement-task-deliverable
_Reference: atdd.md, plan.md_

## Oluşturulan Dosyalar (yeni, red step)

- `backend/tests/test_engagement_tasks.py` — 10 test fonksiyonu, 6 sınıf.
- `backend/tests/test_engagement_deliverables.py` — 15 test fonksiyonu, 10 sınıf.

Bu görevde implementasyon (modeller, migration, servis fonksiyonları, API
route'ları) hiçbiri yok — testler `EngagementTask`/`Deliverable` import
hatası ve/veya 404 (route yok) ile **kırmızı** geçmesi beklenen klasik
red step. `code-copilot` bunları yeşile çevirecek.

## AC → Test Eşlemesi

| AC | Test(ler) |
|---|---|
| AC-1 | `TestTaskCreationHappyPath::test_task_creation_org_member_200`, `test_task_creation_org_admin_201`, `test_task_creation_inst_coord_201` |
| AC-2 | `TestDeliverableCreationHappyPath::test_deliverable_creation_talent_201`, `test_deliverable_creation_optional_description_201` |
| AC-3 | `TestTaskCrossOrgIsolation::test_task_creation_cross_org_404`, `test_task_creation_cross_institution_404` |
| AC-4 | `TestDeliverableCrossTalentIsolation::test_deliverable_creation_cross_talent_404` |
| AC-5 | `TestTaskPreconditionNotActive::test_task_creation_draft_engagement_422`, `test_task_creation_pending_approval_engagement_422`, `TestDeliverablePreconditionNotActive::test_deliverable_creation_draft_engagement_422`, `test_deliverable_creation_pending_approval_engagement_422` |
| AC-6 | `TestT5TransitionWithDeliverable::test_t5_transition_with_deliverable_200` |
| AC-7 | `TestT5TransitionWithoutDeliverable::test_t5_transition_without_deliverable_422` |
| AC-S1 | `TestTaskRoleElevation::test_task_creation_talent_forbidden_403` |
| AC-S2 | `TestDeliverableRoleElevation::test_deliverable_creation_org_member_forbidden_403`, `test_deliverable_creation_org_admin_forbidden_403`, `test_deliverable_creation_inst_coord_forbidden_403` |
| AC-S3 | `TestDeliverableSubmittedByUserIdTampering::test_deliverable_creation_submitted_by_user_id_ignored` |
| AC-S4 | `TestT5TransitionWithoutDeliverable::test_t5_transition_with_fake_deliverable_count_field_422` |
| AC-S5 | `TestTaskScopeCheckOrder::test_task_creation_cross_org_missing_title_404`, `TestDeliverableScopeCheckOrder::test_deliverable_creation_cross_talent_missing_title_404` |
| (ek) | `TestTaskResponseSchema`, `TestDeliverableResponseSchema` — response şeması + hata şeması (`code`/`message`/`request_id`) doğrulaması |

Hata kodları (`NOT_FOUND`/`PRECONDITION_FAILED`/`FORBIDDEN`) tam eşleşmeyle
(`==`) doğrulanıyor, substring/`.lower()`/`or` kullanılmamış.

## Varsayımlar (sub-agent'ın kendi notu)
1. Modeller `app/models/task_deliverable.py` altına yazılacak ve
   `app/models/__init__.py`'de export edilecek (plan.md ile uyumlu).
2. API route'ları `app/api/engagements.py` içine eklenecek (plan.md ile uyumlu).
3. `Deliverable.description` nullable.
4. `Engagement.status` CHECK constraint'i zaten `PENDING_EVALUATION`'ı
   içeriyor (plan.md'de doğrulandı).

## Beklenen Sonuç
Kırmızı (red) — `code-copilot` adımına kadar. Testler her iki dosyada da
kendi bağımsız fixture setini kuruyor (mevcut `test_engagement_transitions.py`
fixture'larını paylaşmıyor), bu yüzden implementasyon geldiğinde diğer
dosyaları etkilemeden bağımsız çalışabilirler.
