# Plan — yet-71-skillsignal-turetme-tam-kapsam
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok (backend-only görev).

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `backend/app/models/task_deliverable.py` | `EngagementTask`/`Deliverable`'a nullable `skill_id` FK kolonu eklenir | low |
| `backend/app/services/engagement.py` | `create_engagement_task()`/`create_deliverable()`'a `skill_id` parametresi + SkillSignal(TASK/DELIVERABLE) üretimi (AC-1, AC-2, AC-6, AC-7); yeni `InvalidSkillError` exception sınıfı (dosyada henüz yok, `evaluation.py`'deki desenle aynı) | medium |
| `backend/app/services/evaluation.py` | `create_evaluation()`'a EVALUATION kaynaklı SkillSignal üretimi (AC-3, AC-4, AC-5) — her `EvaluationItem` için skill_id doluysa ve rating≠NOT_OBSERVED ise | medium |
| `backend/app/api/engagements.py` | `PostTaskRequest`/`PostDeliverableRequest` Pydantic modellerine opsiyonel `skill_id: str \| None` eklenir, `create_engagement_task`/`create_deliverable` çağrılarına iletilir, yeni `InvalidSkillError` → 422 HTTPException eşlemesi | low |

## New Files
| File | Purpose |
|------|---------|
| `backend/alembic/versions/<yeni>_add_skill_id_to_tasks_and_deliverables.py` | `engagement_tasks.skill_id`, `deliverables.skill_id` nullable FK → `skills.id` |

## Dependencies
- `app.services.authorization.Principal`, `get_scoped_or_404`, `scoped_engagements` — mevcut desen, değişmiyor.
- `app.services.audit.log_audit_event` — mevcut kullanım korunuyor (TASK_CREATED audit'i zaten var, SkillSignal ek bir audit event'i GEREKTİRMİYOR — atdd.md'nin threat-model bölümünde bilinçli karar).
- `app.models.SkillSignal` (mevcut, `skill_claim.py`/`attestation.py`'deki birebir aynı satır deseni: `SkillSignal(talent_id=..., skill_id=..., source_type=..., source_id=..., strength=..., attested_by_org_id=..., occurred_at=..., superseded_by_id=None)`).
- `app.models.Skill` — skill_id doğrulaması için (`evaluation.py`'deki `InvalidSkillError` deseniyle birebir: `select(Skill).where(Skill.id == skill_uuid)`, `None` ise reddet).
- Route deseni: `backend/app/api/engagements.py`'deki mevcut `post_engagement_tasks`/`post_engagement_deliverables`/`post_engagement_evaluation` — aynı `try/except → HTTPException` eşleme deseni.

**Strength sabitleri (yeni, atdd.md Assumptions'tan):**
```python
TASK_SIGNAL_STRENGTH = "WEAK"
DELIVERABLE_SIGNAL_STRENGTH = "MODERATE"
EVALUATION_RATING_TO_STRENGTH = {"BELOW": "WEAK", "MEETS": "MODERATE", "EXCEEDS": "STRONG"}
# NOT_OBSERVED -> sinyal üretilmez (map'te yok)
```
Bunlar `engagement.py`/`evaluation.py` içinde modül-seviyesi sabit olarak tanımlanabilir (CAVEMAN — ayrı bir `constants.py` dosyası GEREKMİYOR, sadece 2 dosyada kullanılıyor).

## Migration Required?
**Evet.** `engagement_tasks.skill_id` (nullable, FK → `skills.id`) ve `deliverables.skill_id` (nullable, FK → `skills.id`).

`down_revision`: mevcut tek head `f8g9h0i1j2k3` (YET-70'in migration'ı) — doğrulandı (`alembic heads` çalıştırıldı, tek head).

**Migration oluşturmadan/uygulamadan önce kullanıcıya sorulacak** (CLAUDE.md kuralı — bu adımda henüz oluşturulmadı).

## Risks
(atdd.md'den taşınan + yeni bulunanlar)
- `create_engagement_task`/`create_deliverable` şu an `InvalidSkillError` benzeri bir exception fırlatmıyor (skill_id parametresi hiç yok) — yeni exception sınıfı eklenirken mevcut `IllegalTransitionError`/`PreconditionFailedError`/`TransitionForbiddenError` ile karışmaması için isimlendirme netliği önemli (`evaluation.py`'deki `InvalidSkillError` ADI ve DAVRANIŞI birebir kopyalanacak, tutarlılık için).
- `EngagementTask`/`Deliverable` modellerinde `skill_id` eklenmesi, bu iki modelin `__init__`'ini etkilemez (SQLAlchemy declarative, yeni nullable kolon geriye uyumlu) — ama mevcut testlerde (varsa) bu modelleri `skill_id` OLMADAN oluşturan fixture'lar olabilir, nullable olduğu için bozulmamalı (test-copilot bunu regresyon olarak görmeli).

## Open Questions
Yok — atdd.md'nin Assumptions bölümü (strength hiyerarşisi, TASK'ın "oluşturulduğunda" tetiklenmesi) yeterince net, kod keşfi sırasında çelişen/eksik bir nokta bulunmadı.
