# Code Diff — yet-71-skillsignal-turetme-tam-kapsam

## Oluşturulan Dosyalar
- `backend/alembic/versions/k2l3m4n5o6p7_add_skill_id_to_tasks_and_deliverables.py` — `engagement_tasks.skill_id`, `deliverables.skill_id` (nullable FK→`skills.id`). **Henüz `alembic upgrade head` ile uygulanmadı.**

## Değiştirilen Dosyalar
- `backend/app/models/task_deliverable.py` — `EngagementTask`/`Deliverable`'a `skill_id` nullable FK kolonu.
- `backend/app/services/engagement.py` — `InvalidSkillError`, strength sabitleri (`TASK_SIGNAL_STRENGTH="WEAK"`, `DELIVERABLE_SIGNAL_STRENGTH="MODERATE"`), `create_engagement_task()`/`create_deliverable()`'a `skill_id` parametresi + SkillSignal üretimi.
- `backend/app/services/evaluation.py` — `EVALUATION_RATING_TO_STRENGTH` eşlemesi, `create_evaluation()`'daki item döngüsüne SkillSignal üretimi.
- `backend/app/api/engagements.py` — `PostTaskRequest`/`PostDeliverableRequest`'e opsiyonel `skill_id` + `extra="forbid"` (AC-S1), `InvalidSkillError`→422 eşlemesi.

## Review Sürecinde Bulunan ve Düzeltilen Sorun
İlk migration dosyasında `down_revision` **yanlış** yazılmıştı (`j1k2l3m4n5o6` — eski, zaten başka bir merge migration'ı tarafından birleştirilmiş bir revizyon, gerçek head değil). Bu, orkestratör tarafından raporun kendi metnindeki tutarsızlık fark edilerek tespit edildi (rapor "son evaluation migration" diyordu ama gerçek head YET-70'in migration'ıydı). Düzeltme dispatch edildi: `down_revision` doğru head'e (`f8g9h0i1j2k3`) çevrildi, `alembic heads` ile tek head (`k2l3m4n5o6p7`) doğrulandı.

## AC Karşılanması (özet)
AC-1..AC-9, AC-S1, AC-S2 — TASK/DELIVERABLE/EVALUATION kaynaklı SkillSignal üretimi, strength eşlemesi, skill_id doğrulama (422), sessiz atlama (skill_id yoksa/NOT_OBSERVED ise), strength/talent_id tampering koruması.

## Kalan Sınırlamalar
- Migration oluşturuldu ama **uygulanmadı** — `verify` adımında kullanıcı onayıyla `alembic upgrade head` çalıştırılacak.
- Mevcut SELF_CLAIM/ATTESTATION/GET-ucu davranışı değiştirilmedi (AC-8 — regresyon `verify`'da doğrulanacak).

## CAVEMAN Self-Review
Yeni dosya sayısı minimum (1 migration) — mevcut 3 servis fonksiyonuna (create_engagement_task/create_deliverable/create_evaluation) doğrudan ekleme yapıldı, ayrı bir soyutlama/yardımcı dosya oluşturulmadı.
