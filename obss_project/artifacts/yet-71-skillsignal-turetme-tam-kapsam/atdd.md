---
task_slug: yet-71-skillsignal-turetme-tam-kapsam
jira_id: YET-71
saga_task_id: null
threat_model: done
priority: medium
coverage_target: 85
performance_target: null
memory_target: null
test_strategy:
  unit: 50
  integration: 40
  e2e: 10
affected_modules:
  - backend/app/models/task_deliverable.py (EngagementTask/Deliverable'a skill_id eklenir)
  - backend/app/services/engagement.py (task/deliverable oluşturma servisleri — SkillSignal yan etkisi)
  - backend/app/services/evaluation.py (EVALUATION kaynaklı SkillSignal yan etkisi)
  - backend/app/api/engagements.py (PostTaskRequest/PostDeliverableRequest'e opsiyonel skill_id)
  - backend/alembic/versions/ (yeni migration: deliverables.skill_id, engagement_tasks.skill_id)
---

# ATDD — yet-71-skillsignal-turetme-tam-kapsam

## Jira Kaynağı
[YET-71 — [PLAN 2.9] SkillSignal türetme + GET /talents/me/signals](https://kuyusuzyusuf123.atlassian.net/browse/YET-71)
Açıklama (Jira'dan birebir): "SkillSignal türetme mantığı (source_type=ATTESTATION), GET /talents/me/signals ucu."
Alt görevler: [YET-91](https://kuyusuzyusuf123.atlassian.net/browse/YET-91) (SkillSignal türetme mantığı, source_type=ATTESTATION), [YET-92](https://kuyusuzyusuf123.atlassian.net/browse/YET-92) (GET /talents/me/signals ucu).
Atanan: Meyrem (Jira görünen adı "Meyrsem").

**Kapsam netleştirmesi (kullanıcı onayıyla, bu oturumda):** Jira'nın YET-91/92 başlıkları PLAN.md/koda göre ESKİ — ATTESTATION kaynaklı SkillSignal (YET-70'te) ve GET ucu (YET-104'te) zaten mainde. Kullanıcı bunları kapatmak yerine **YET-71'in TAMAMININ yeniden doğrulanmasını** istedi. Bu görev artık şunu kapsıyor:
1. Mevcut SELF_CLAIM/ATTESTATION/GET-ucu implementasyonunun atdd kriterleri açısından doğrulanması (regresyon testiyle).
2. **DELIVERABLE ve TASK kaynaklı türetme mantığının eklenmesi** (kullanıcı kararı: `deliverables`/`engagement_tasks` tablolarına nullable `skill_id` FK ekleyen yeni migration dahil).
3. **EVALUATION kaynaklı türetme mantığının eklenmesi** (`EvaluationItem.skill_id` zaten var, migration gerekmiyor).

DOMAIN.md §3.14'ün kendi açık sorusu: "Hangi source_type hangi strength üretir final analizde tablolanmamış — PLAN 2.9'da netleşmeli." Bu görev o kararı veriyor (bkz. Assumptions).

## Persona
Ayrı bir kullanıcı/uç değil — mevcut 3 endpoint'in (POST /engagements/{id}/tasks, POST /engagements/{id}/deliverables, POST /engagements/{id}/evaluation) çağıranlarına gömülü bir **yan etki**: TASK için ORG_MEMBER/ORG_ADMIN/COORDINATOR, DELIVERABLE için TALENT, EVALUATION için değerlendirmeyi gönderen taraf.

## Hedef (Neden)
DOMAIN.md'nin "her kanıt olayı bir sinyal üretir" ilkesi (§3.14) platformun `beyan → kanıt → tanıklık → doğrulanmış deneyim` zincirini somut, sorgulanabilir veriye dönüştürür. SkillSignal üretilmezse bir yetkinlik iddiası hiçbir zaman "kanıtla desteklendi" diye işaretlenemez, `GET /talents/me/signals` eksik kalır.

## User Story
As a platform (arka plan yan etkisi)
I want her kanıt olayında (task/deliverable/evaluation) ilgili yetkinlik için bir SkillSignal üretmek
So that talent'ın yetkinlik gücü GET /talents/me/signals üzerinden açıklanabilir şekilde görülebilsin

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)

1. [Critical] Given `ORG_MEMBER`/`ORG_ADMIN`/`COORDINATOR` bir engagement'ta task oluşturuyor, `skill_id` alanı doldurulmuş, When `POST /engagements/{id}/tasks` çağrılır, Then `201` döner (mevcut response şeması değişmez) ve aynı transaction içinde `SkillSignal(source_type=TASK, strength=WEAK, source_id=task.id, skill_id=<verilen>, talent_id=engagement.talent_id, occurred_at=task.created_at)` yazılır.

2. [Critical] Given `TALENT` bir deliverable submit ediyor, `skill_id` alanı doldurulmuş, When `POST /engagements/{id}/deliverables` çağrılır, Then `201` döner (mevcut response şeması değişmez) ve aynı transaction içinde `SkillSignal(source_type=DELIVERABLE, strength=MODERATE, source_id=deliverable.id, skill_id=<verilen>, talent_id=engagement.talent_id, occurred_at=deliverable.submitted_at)` yazılır.

3. [Critical] Given bir `Evaluation`, en az bir `EvaluationItem(skill_id=X, rating=MEETS)` içeriyor, When `POST /engagements/{id}/evaluation` çağrılır, Then `201` döner (mevcut response şeması değişmez) ve o item için `SkillSignal(source_type=EVALUATION, strength=MODERATE, source_id=evaluation.id, skill_id=X, occurred_at=evaluation.submitted_at)` aynı transaction içinde yazılır.

4. [Critical] Given `EvaluationItem.rating` değerleri, When `POST /engagements/{id}/evaluation` işlenir, Then eşleme **BELOW→WEAK, MEETS→MODERATE, EXCEEDS→STRONG** uygulanır; `NOT_OBSERVED` için **hiç SkillSignal üretilmez** (AC-7).

5. [High] Given bir `Evaluation`'da birden fazla `EvaluationItem` var (farklı `skill_id`'ler), When işlem tamamlanır, Then her `skill_id` dolu item için **ayrı** bir `SkillSignal` üretilir (hepsi aynı `source_id=evaluation.id`, aynı transaction).

6. [High] Given `POST /engagements/{id}/tasks` veya `POST /engagements/{id}/deliverables`, `skill_id` alanı **verilmemiş** (null), When istek işlenir, Then `201` döner (davranış değişmez), **hiçbir SkillSignal yazılmaz** — sessizce atlanır, hata fırlatılmaz.

7. [High] Given `skill_id` verilmiş ama `skills` tablosunda yok/ACTIVE değil, When istek işlenir, Then `422` döner (mevcut `evaluation.py`'deki `InvalidSkillError` deseniyle aynı — skill_id doğrulaması yazmadan ÖNCE yapılır), hiçbir yazma olmaz.

8. [Critical] Given mevcut SELF_CLAIM (`skill_claim.py`) ve ATTESTATION (`attestation.py`) kaynaklı SkillSignal üretimi ve `GET /talents/me/signals` ucu, When bu görevin testleri çalıştırılır, Then bunların hâlâ doğru çalıştığı regresyon testleriyle **yeniden doğrulanır** (yeni test yazılmaz, mevcut `tests/authorization` ve genel paket kırmızı olmamalı — kullanıcının "tamamının yeniden doğrulanması" isteği).

9. [Medium] Given `GET /talents/me/signals`, bir skill için birden fazla `source_type`'tan sinyal var (ör. TASK + EVALUATION), When çağrılır, Then mevcut gruplama mantığı (skill'e göre grupla, `signals[]` listesi) değişmeden tüm source_type'ları listeler.

10. [Critical] **AC-S1 (Tampering — strength manipülasyonu)** Given istemci `POST /engagements/{id}/tasks` veya `.../deliverables` isteğinde gövdeye `strength: "STRONG"` (veya `source_type`, `talent_id`) gibi ek bir alan ekliyor, When istek işlenir, Then bu alanlar **Pydantic şemasında tanımlı değildir ve kabul edilmez** (mevcut `AttestationCreateRequest`'teki `extra="forbid"` deseniyle aynı) — `strength` her zaman sunucu tarafında sabit kurala göre hesaplanır (TASK→WEAK, DELIVERABLE→MODERATE, EVALUATION→rating eşlemesi), istemciden hiçbir "güç" sinyali kabul edilmez.

11. [High] **AC-S2 (Tampering — talent_id kaynağı)** Given `SkillSignal.talent_id` alanı, When herhangi bir kaynaktan (TASK/DELIVERABLE/EVALUATION) üretilir, Then bu değer **her zaman `engagement.talent_id`'den** (sunucu tarafında, DB'den okunan engagement kaydından) türetilir — istemciden gelen hiçbir `talent_id`/`user_id` alanı kabul edilmez (zaten mevcut request şemalarında böyle bir alan yok, bu AC bunun kasıtlı bir tasarım kararı olduğunu ve gelecekte eklenirse de bu kurala uyması gerektiğini sabitliyor).

## Threat Model
Çağrıldı — `AC-S1`, `AC-S2` yukarıdaki Acceptance Criteria'ya eklendi (threat-model skill'i, 2026-09-24).

STRIDE-lite değerlendirmesi:
- **S**poofing: Mevcut auth mekanizması değişmiyor — tetikleyici yok.
- **T**ampering: AC-S1 (strength), AC-S2 (talent_id) — istemciden gelen hiçbir alana güvenilmiyor.
- **R**epudiation: SkillSignal, ana kaydın (task/deliverable/evaluation) AYNI transaction'ında üretiliyor — ana kaydın kendi audit/log izi (varsa) SkillSignal'i de kapsıyor, ayrı bir AuditEvent bu görevde gerekmiyor (mevcut task/deliverable/evaluation oluşturma akışları zaten audit üretmiyor, bu görev de yeni bir audit gereksinimi eklemiyor — kapsam dışı).
- **I**nfo disclosure: `GET /talents/me/signals` zaten talent'a scoped (YET-104) — bu görev o ucu değiştirmiyor, ek risk yok.
- **D**oS: Sınırsız task/deliverable oluşturma (spam) zaten bu görevden ÖNCE var olan bir durum (PLAN 2.4'ün kapsamı) — bu görev yeni bir DoS vektörü AÇMIYOR, sadece mevcut oluşturma akışına bir yan etki ekliyor. **Kabul edilen risk** olarak Risks bölümüne taşındı.
- **E**levation: `Skill` taksonomisi platform-geneli paylaşılan bir kaynak (tenant-scoped değil — `evaluation.py`'de de `select(Skill).where(Skill.id==X)` tenant filtresi olmadan çalışıyor) — `skill_id` referansında cross-tenant bir sınır yok, bu yüzden elevation riski bu alan için geçerli değil.

## Davranış Sözleşmesi (hangi durumda ne döner)

| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | TASK oluşturulur, skill_id verilir | `201` (mevcut şema) | `SkillSignal(TASK, WEAK)` yazılır | `{"id":"...","status":"PLANNED","skill_id":"uuid-x",...}` | AC-1 |
| 2 | DELIVERABLE submit edilir, skill_id verilir | `201` (mevcut şema) | `SkillSignal(DELIVERABLE, MODERATE)` yazılır | `{"id":"...","skill_id":"uuid-x",...}` | AC-2 |
| 3 | EVALUATION submit edilir, item MEETS | `201` (mevcut şema) | `SkillSignal(EVALUATION, MODERATE)` yazılır | `{"items":[{"skill_id":"uuid-x","rating":"MEETS"}],...}` | AC-3/4 |
| 4 | TASK/DELIVERABLE'da skill_id verilmez | `201` (değişmez) | SkillSignal **yazılmaz** | `{"skill_id": null, ...}` | AC-6 |
| 5 | EvaluationItem.rating=NOT_OBSERVED | `201` (değişmez) | O item için SkillSignal **yazılmaz** (diğer item'lar için kural uygulanır) | Aynı response, API'de ayrıca belirtilmez | AC-4 |
| 6 | Geçersiz skill_id (skills tablosunda yok/ACTIVE değil) | `422` | Hiçbir yazma yok (transaction rollback) | `{"code":"INVALID_REQUEST","message":"Geçersiz skill_id."}` | AC-7 |
| 7 | GET /talents/me/signals — aynı skill'e çoklu source_type | `200` | Yok (salt okunur) | `{"items":[{"skill":{...},"signals":[{"source_type":"TASK","strength":"WEAK"},{"source_type":"EVALUATION","strength":"MODERATE"}]}]}` | AC-9 |

Kısmi başarı: Bir Evaluation'da birden fazla item varsa (AC-5), bazı item'lar SkillSignal üretir bazıları üretmez (skill_id yok veya NOT_OBSERVED) — bu **kısmi üretim değil, her item kendi kuralına göre bağımsız değerlendirilir**, "hepsi ya da hiçbiri" değildir; Evaluation'ın kendisi (ana kayıt) her koşulda `201` ile başarıyla oluşur.
Hiçbir şey yapılamadı ama hata da yok: `skill_id` verilmemişse (satır 4) — bu **kasıtlı ve dokümante edilmiş** bir "sessiz atlama"dır, sessiz BAŞARISIZLIK değildir (task/deliverable/evaluation'ın kendisi zaten başarıyla oluşuyor, SkillSignal ek/opsiyonel bir yan etkidir).
Boş sonuç ↔ hata ayrımı: `GET /talents/me/signals` sinyal yoksa `{"items": []}` (200) döner — bu zaten mevcut davranış (YET-104 AC-4), değişmiyor.

## Test Strategy
Unit: 50% — strength eşleme mantığı (rating→strength, source_type→strength sabitleri), skill_id-yoksa-atla mantığı, NOT_OBSERVED-atla mantığı.
Integration: 40% — 3 endpoint'in gerçek DB'ye SkillSignal yazması + `GET /talents/me/signals`'ta görünmesi, geçersiz skill_id → 422.
E2E: 10% — task oluştur → deliverable submit et → evaluation gönder → `GET /talents/me/signals` ucunda 3 source_type'ın da (+ mevcut SELF_CLAIM/ATTESTATION) doğru göründüğü uçtan uca senaryo.

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: yok
Diğer: `pytest tests/authorization -q` ve tam paket regresyonsuz kalmalı (mevcut SELF_CLAIM/ATTESTATION/GET ucu davranışı bozulmamalı — AC-8).

## Kapsam Dışı
- **TASK'ın `DONE` durumuna geçince SkillSignal güncellemesi/superseded_by_id zinciri** — çünkü `EngagementTask` için bir durum-güncelleme (PATCH/transition) ucu bu projede henüz yok; task'ın tek sinyali oluşturulduğu anda (status=PLANNED) üretilen `WEAK` sinyaldir, hiçbir zaman supersede edilmez. Ayrı bir görev (yeni PATCH ucu + supersede mantığı) gerektirir.
- `EXTERNAL` source_type — bu görevde ele alınmıyor (dış API entegrasyonu yok, final analiz kapsamı dışı).
- Attestation revoke sonrası `superseded_by_id` zinciri — zaten YET-93/94'e ait, bu görevde dokunulmaz.
- Strength hiyerarşisinin DOMAIN.md/final-analiz dokümanına geri yazılması — kod tarafında karar veriliyor ama doküman güncellemesi ayrı, isteğe bağlı bir takip maddesi (Assumptions'a not düşüldü).

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/models/task_deliverable.py` — `EngagementTask`/`Deliverable`'a nullable `skill_id: Mapped[uuid.UUID | None]` FK eklenir.
- `backend/alembic/versions/` — yeni migration (deliverables.skill_id, engagement_tasks.skill_id, ikisi de `skills.id`'ye FK, nullable).
- Task/Deliverable oluşturma servis fonksiyonları (muhtemelen `backend/app/services/engagement.py` içinde — `plan` adımında kesin dosya doğrulanacak).
- `backend/app/services/evaluation.py` — `create_evaluation()`'a SkillSignal üretim adımı eklenir.
- `backend/app/api/engagements.py` — `PostTaskRequest`/`PostDeliverableRequest` Pydantic modellerine opsiyonel `skill_id: str | None` eklenir.
- Mevcut `backend/app/services/skill_claim.py` (SELF_CLAIM) ve `backend/app/services/attestation.py` (ATTESTATION) — regresyon doğrulaması için referans/test hedefi, DEĞİŞTİRİLMEZ.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulandı — bu oturumda arama `backend/`, `docs/`, `obss_project/artifacts/` alt dizinleriyle sınırlı tutuldu.

## Rollback Beklentisi
SkillSignal üretimi ana kaydın (task/deliverable/evaluation) AYNI transaction'ı içinde olur — SkillSignal yazımı başarısız olursa (ör. beklenmeyen constraint ihlali) tüm transaction (ana kayıt dahil) rollback olur; task/deliverable/evaluation'ın SkillSignal'siz "yarım" oluşması hiçbir koşulda olmaz.

## Risks
- **Kabul edilen risk (DoS):** Task/deliverable oluşturma uçlarında rate-limit yok — bu, bu görevden ÖNCE var olan bir durum (PLAN 2.4 kapsamı), bu görev yeni bir vektör açmıyor, threat-model STRIDE-lite değerlendirmesinde bilinçli olarak kapsam dışı bırakıldı.
- Yeni migration (`deliverables.skill_id`, `engagement_tasks.skill_id`) — CLAUDE.md kuralı gereği oluşturmadan/uygulamadan önce kullanıcı onayı ayrıca istenecek (bu atdd onayı migration onayı YERİNE geçmez).
- Strength hiyerarşisi (NONE < WEAK < MODERATE < STRONG, source_type'lara dağılımı) bu görevde ilk kez karara bağlanıyor — DOMAIN.md'nin kendi açık sorusuydu, dokümana geri yazılması ayrı bir takip maddesi (bkz. Kapsam Dışı).

## Assumptions
- **Strength hiyerarşisi (varsayım, DOMAIN.md'nin açık sorusunu bu görev çözüyor):**
  `SELF_CLAIM→NONE` (mevcut) `< TASK→WEAK < DELIVERABLE→MODERATE < EVALUATION→{BELOW:WEAK, MEETS:MODERATE, EXCEEDS:STRONG} ≈ ATTESTATION→{PARTICIPATION:WEAK, COMPETENCE:STRONG}` (mevcut).
  Gerekçe: TASK/DELIVERABLE kendi kendine raporlu/atanmış, üçüncü taraf doğrulaması yok — EVALUATION üçüncü taraftan puanlama (Attestation kadar resmi/T2+ organizasyon doğrulaması değil, ama SELF_CLAIM'den güçlü).
- TASK sinyali **oluşturulduğu anda** (status=PLANNED) üretilir, "tamamlandığında" değil — çünkü durum-güncelleme ucu yok (bkz. Kapsam Dışı).
- Geçersiz `skill_id` kontrolü, mevcut `evaluation.py`'deki `InvalidSkillError` deseniyle birebir aynı (422, tüm yazmalardan önce doğrulanır).

## Unknowns
- Task/Deliverable oluşturma servis fonksiyonlarının tam dosya/fonksiyon adı — `plan` adımında `backend/app/services/` içinde doğrulanacak (muhtemelen `engagement.py` içinde `create_engagement_task`/`create_deliverable`, YET-70'te import edilen isimlerden anlaşılıyor).

## Sorular ve Cevaplar (ham kayıt)
1. Persona → Mevcut 3 uca gömülü yan etki (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
2. Ana hedef → "Her kanıt olayı sinyal üretir" ilkesi, zincirin somutlaşması (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
3-5. Happy path senaryoları → yukarıdaki AC-1/2/3/4 (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
6-8. Edge case'ler → AC-6/7, davranış sözleşmesi satır 4/5/6 (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
9. Davranış sözleşmesi → yukarıdaki tablo (Sonnet 5 low alt-ajanı tarafından dolduruldu)
10. Benchmark → coverage 85% (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
11. Kapsam dışı → TASK DONE güncellemesi (Sonnet 5 low alt-ajanı tarafından yanıtlandı, orkestratör tarafından teyit edildi — durum-güncelleme ucu gerçekten yok)
12. Bağımlılıklar → yukarıdaki Etkilenen Dosyalar (Sonnet 5 low alt-ajanı + orkestratörün kod taraması)
13. Test oranı → 50/40/10 (Sonnet 5 low alt-ajanı tarafından yanıtlandı)
14. Strength hiyerarşisi → yukarıdaki Assumptions (Sonnet 5 low alt-ajanı tarafından yanıtlandı, kullanıcı onayı gerekir — Hard Stop'ta gösterilecek)
