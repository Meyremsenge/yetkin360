# Test Diff — yet-71-skillsignal-turetme-tam-kapsam

## Genişletilen Dosyalar
- `backend/tests/test_engagement_tasks.py` (+218 satır) — TASK kaynaklı SkillSignal testleri
- `backend/tests/test_engagement_deliverables.py` (+162 satır) — DELIVERABLE kaynaklı SkillSignal testleri
- `backend/tests/test_evaluation.py` (+512 satır) — EVALUATION kaynaklı SkillSignal testleri + GET /talents/me/signals çoklu source_type senaryosu

## AC → Test eşleşmesi
| AC | Test | Dosya |
|---|---|---|
| AC-1 (TASK+skill_id→WEAK) | `test_task_with_skill_id_creates_skill_signal_201` | test_engagement_tasks.py |
| AC-2 (DELIVERABLE+skill_id→MODERATE) | `test_deliverable_with_skill_id_creates_skill_signal_201` | test_engagement_deliverables.py |
| AC-3/AC-4 (EVALUATION rating→strength) | `test_evaluation_meets_creates_skill_signal_201`, `test_evaluation_below_creates_weak_signal_201`, `test_evaluation_exceeds_creates_strong_signal_201`, `test_evaluation_not_observed_no_signal_201` | test_evaluation.py |
| AC-5 (çoklu item → ayrı sinyaller) | `test_evaluation_multiple_items_creates_separate_signals_201`, `test_evaluation_mixed_items_partial_signal_creation_201` | test_evaluation.py |
| AC-6 (skill_id yoksa sessiz atlama) | `test_task_without_skill_id_no_signal_201`, `test_deliverable_without_skill_id_no_signal_201` | test_engagement_tasks.py / test_engagement_deliverables.py |
| AC-7 (geçersiz skill_id→422) | `test_task_with_invalid_skill_id_422`, `test_deliverable_with_invalid_skill_id_422`, `test_evaluation_invalid_skill_id_in_item_422` | ilgili dosyalar |
| AC-8 (SELF_CLAIM/ATTESTATION/GET-ucu regresyonu) | Mevcut testlerle (yeni test yazılmadı, `verify` adımında tam paket regresyon kontrolü) | — |
| AC-9 (GET çoklu source_type) | `test_get_signals_multiple_source_types_200` | test_evaluation.py |
| AC-S1 (strength tampering) | `test_task_strength_field_tampering_ignored_201` | test_engagement_tasks.py |
| AC-S2 (talent_id sunucudan) | Implicit doğrulama (SkillSignal.talent_id == engagement.talent_id) | ilgili testler |

## Düzeltme (bulundu ve giderildi)
İlk yazımda `test_get_signals_multiple_source_types_200` iki yerde `pytest.skip()` kullanıyordu ("endpoint henüz yok olabilir" varsayımıyla) — ama her iki endpoint (`POST /engagements/{id}/tasks`, `GET /talents/me/signals`) GERÇEKTEN var. Bu, testin kırmızı olması gereken durumda sessizce skip olmasına yol açardı (projenin "skip ile gizleme yasak" kuralının ihlali). Test sıfırdan, skip'siz, hem TASK hem EVALUATION source_type'ını gerçekten çalıştıracak şekilde yeniden yazıldı.

## Durum
RED (beklenen) — `skill_id` kolonu/parametresi ve SkillSignal üretim mantığı henüz implemente değil. Sonraki adım: `code-copilot`.
