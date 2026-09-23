---
task_slug: engagement-task-deliverable
jira_id: YET-66
saga_task_id: null
threat_model: done
priority: medium
coverage_target: 85
performance_target: null
memory_target: null
test_strategy:
  unit: 10
  integration: 80
  e2e: 10
affected_modules:
  - backend/app/models/engagement.py (veya yeni backend/app/models/task_deliverable.py)
  - backend/app/services/engagement.py
  - backend/app/services/authorization.py
  - backend/app/api/engagements.py
  - backend/alembic/versions/ (yeni migration — kullanıcı onayı gerekli)
  - docs/DOMAIN.md (§3.8 status enum bu oturumda zaten güncellendi)
---

# ATDD — engagement-task-deliverable

## Jira Kaynağı
[YET-66 — [PLAN 2.4] Task + Deliverable](https://kuyusuzyusuf123.atlassian.net/browse/YET-66)
Açıklama (Jira'dan birebir): "EngagementTask (PLANNED/IN_PROGRESS/DONE) +
Deliverable modelleri, POST /engagements/{id}/tasks + POST
/engagements/{id}/deliverables uçları. T5 ön koşulu: en az 1 Deliverable."
Alt görevler: YET-79 (EngagementTask modeli+migration+POST /tasks), YET-80
(Deliverable modeli+POST /deliverables, evidence_ids[] bağlantısı — bu
görevde ERTELENDİ, bkz. Kapsam Dışı), YET-81 (T5 ön koşulu: en az 1
Deliverable kontrolü).
PLAN.md madde: 2.4 (Faz 2). 2.1/2.2/2.3 tamamlanmış.

## Persona
**COORDINATOR/ORG_MEMBER/ORG_ADMIN** (engagement'ın ait olduğu organizasyon
tarafı — `EngagementTask` oluşturur, işin planlanmasından sorumlu) ve
**TALENT** (engagement'ın konusu olan öğrenci/çalışan — `Deliverable`
gönderir, kanıt zincirinin "kanıt" adımı).

## Hedef (Neden)
Engagement artık durum makinesiyle (PLAN 2.2/2.3) yönetiliyor ama içi boş —
ne bir iş planı (`EngagementTask`) ne de somut bir çıktı kaydı
(`Deliverable`) yok. Bu görev, `beyan → kanıt → tanıklık → doğrulanmış
deneyim` zincirinin "kanıt" ayağını başlatır ve `ACTIVE → PENDING_EVALUATION`
(T5) geçişine gerçek bir ön koşul (en az 1 Deliverable) bağlar — böylece
değerlendirme aşamasına dayanaksız bir engagement giremez.

## User Story
As a **kurum tarafı kullanıcısı (COORDINATOR/ORG_MEMBER/ORG_ADMIN)**
I want **aktif bir engagement'a iş planı (task) ekleyebilmek**
So that **öğrencinin ne üzerinde çalıştığı kayıt altına alınsın**

As a **TALENT**
I want **kendi aktif engagement'ıma bir çıktı (deliverable) gönderebilmek**
So that **beyanımı somut bir kanıtla destekleyebileyim ve engagement
değerlendirmeye geçebilsin**

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)

1. [Critical] Given COORDINATOR/ORG_MEMBER/ORG_ADMIN (engagement'ın kendi
   organizasyonu/kurumu kapsamında) ve `ACTIVE` durumunda bir engagement,
   When `POST /engagements/{id}/tasks` `{"title":"...", "description":"...",
   "due_at": null}` ile çağrılır, Then **201** döner, body
   `{"id":"...","engagement_id":"...","title":"...","description":"...",
   "status":"PLANNED","due_at":null,"completed_at":null,"created_at":"...",
   "updated_at":"..."}` içerir ve `audit_events`'e `TASK_CREATED` yazılır.
2. [Critical] Given TALENT (engagement'ın kendi talent_id'si) ve `ACTIVE`
   durumunda kendi engagement'ı, When `POST /engagements/{id}/deliverables`
   `{"title":"...", "description":"..."}` ile çağrılır, Then **201** döner,
   body `{"id":"...","engagement_id":"...","title":"...","description":"...",
   "submitted_by_user_id":"<principal.user_id>","submitted_at":"...",
   "created_at":"...","updated_at":"..."}` içerir — `submitted_by_user_id`
   HER ZAMAN principal'dan gelir, request body'sinde bu alan YOKTUR.
3. [Critical] Given başka bir organizasyona/kuruma ait bir engagement, When
   scope dışı bir COORDINATOR/ORG_MEMBER `POST .../tasks` çağırır, Then
   **404** `{"code":"NOT_FOUND"}` döner (çapraz-kurum/çapraz-org tenant
   isolation, §5.1/§5.5 desenine uygun).
4. [Critical] Given başka bir talent'a ait bir engagement, When farklı bir
   TALENT `POST .../deliverables` çağırır, Then **404** döner (çapraz-talent
   tenant isolation).
5. [High] Given `DRAFT`/`PENDING_APPROVAL`/`REJECTED`/`CANCELLED` durumunda
   bir engagement (henüz `ACTIVE` değil), When aynı organizasyon/talent
   `POST .../tasks` veya `.../deliverables` çağırır, Then **422**
   `{"code":"PRECONDITION_FAILED"}` döner — sadece `ACTIVE` engagement'a
   task/deliverable eklenebilir.
6. [High] Given `ACTIVE` bir engagement'ta en az 1 gerçek `Deliverable`
   kaydı, When COORDINATOR `POST /engagements/{id}/transitions`
   `{"to_status":"PENDING_EVALUATION","version":N}` çağırır, Then **200**
   döner ve durum `PENDING_EVALUATION`'a geçer (T5, mevcut
   `transition_table`'a eklenen yeni satır).
7. [High] Given `ACTIVE` bir engagement'ta HİÇ `Deliverable` kaydı yokken,
   When aynı transition denenirse, Then **422**
   `{"code":"PRECONDITION_FAILED","message":"En az bir deliverable gerekli."}`
   döner, durum DEĞİŞMEZ.
8. **AC-S1** [High] (threat-model) — Given TALENT kendi `ACTIVE`
   engagement'ında, When `POST .../tasks` çağırırsa (task oluşturma
   koordinatör/org yetkisidir), Then **403** `{"code":"FORBIDDEN"}` döner —
   404 DEĞİL, çünkü TALENT kendi engagement'ını zaten görebiliyor
   (kaynak görünür, eylem yasak).
9. **AC-S2** [High] (threat-model) — Given ORG_MEMBER/ORG_ADMIN/COORDINATOR
   kendi kapsamındaki bir `ACTIVE` engagement'ta, When
   `POST .../deliverables` çağırırsa (deliverable gönderme TALENT'a özeldir),
   Then **403** döner — 404 DEĞİL (kaynak org kapsamında görünür).
10. **AC-S3** [Critical] (threat-model) — Given bir `POST .../deliverables`
    isteği body'sinde `submitted_by_user_id` alanı istemci tarafından
    (başka bir kullanıcının UUID'siyle) EKLENMEYE çalışılırsa, Then bu alan
    şemada yok/yok sayılır — kaydedilen `submitted_by_user_id` HER ZAMAN
    `principal.user_id`'dir, asla body'den gelen değer değil.
11. **AC-S4** [Critical] (threat-model) — Given `ACTIVE` bir engagement'ta
    gerçek Deliverable sayısı 0 iken, When T5 transition isteği body'sine
    istemci `{"deliverable_count": 5}` gibi UYDURMA bir alan eklerse, Then
    bu alan tamamen yok sayılır — precondition kontrolü HER ZAMAN gerçek bir
    `SELECT COUNT(*) FROM deliverables WHERE engagement_id = ...` sorgusuna
    dayanır, client-supplied hiçbir sayıya güvenilmez; sonuç yine 422.
12. **AC-S5** [Medium] (threat-model) — Given çapraz-kurum/çapraz-org bir
    task/deliverable isteği, When `title` gibi zorunlu bir alan da eksik
    gönderilirse, Then yine **404** döner (422 DEĞİL) — scope-check
    validation'dan önce çalışır (YET-65'te kilitlenen aynı sıra kuralı).

## Threat Model
Çağrıldı — AC-S1 ile AC-S5 arası kriterler yukarıdaki Acceptance Criteria'ya
eklendi. STRIDE-lite özeti: **Elevation** (TALENT'ın task oluşturması,
ORG tarafının deliverable göndermesi, çapraz-kurum/çapraz-talent erişimi) ve
**Tampering** (`submitted_by_user_id` ve T5'in deliverable-sayısı
precondition'ının client girdisine güvenmesi) en kritik iki kategori.
Spoofing (mevcut cookie-auth, değişmiyor), Repudiation (audit_events zaten
her yazmada loglanıyor, bkz. AC-1/AC-2), DoS (rate-limit — kabul edilen
risk, bkz. Risks) bu görevde yeni bir tetikleyici oluşturmadı, atlandı.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path: kurum tarafı, ACTIVE engagement, task oluşturma | `201 + {"id":"...","engagement_id":"...","title":"...","description":null,"status":"PLANNED","due_at":null,"completed_at":null,"created_at":"...","updated_at":"..."}` | DB'ye satır eklenir, `audit_events`'e `TASK_CREATED` yazılır | Task oluşturuldu | AC-1 |
| 2 | Happy path: TALENT, ACTIVE engagement, deliverable gönderme | `201 + {"id":"...","engagement_id":"...","title":"...","description":"...","submitted_by_user_id":"<principal.user_id>","submitted_at":"...","created_at":"...","updated_at":"..."}` | DB'ye satır eklenir, `audit_events`'e `DELIVERABLE_SUBMITTED` yazılır | Deliverable gönderildi | AC-2, AC-S3 |
| 3 | Çapraz-kurum/çapraz-talent (scope dışı) | `404 + {"code":"NOT_FOUND"}` | Yok | "Bulunamadı" | AC-3, AC-4, AC-S5 |
| 4 | Kaynak görünür, rol yanlış (TALENT→task, ORG→deliverable) | `403 + {"code":"FORBIDDEN"}` | Yok | "Yetkiniz yok" | AC-S1, AC-S2 |
| 5 | Engagement ACTIVE değil | `422 + {"code":"PRECONDITION_FAILED"}` | Yok | "Sadece aktif engagement'a eklenebilir" | AC-5 |
| 6 | T5 geçişi, Deliverable var | `200 + {"status":"PENDING_EVALUATION",...}` | Durum değişir, audit yazılır | Geçiş başarılı | AC-6 |
| 7 | T5 geçişi, Deliverable yok (client ne derse desin) | `422 + {"code":"PRECONDITION_FAILED"}` | Durum DEĞİŞMEZ | "En az bir deliverable gerekli" | AC-7, AC-S4 |

Kısmi başarı: Task/Deliverable oluşturma tek bir INSERT + tek bir audit
event — ayrı bir flush/exception riski taşımıyor (YET-2.2/YET-65'teki aynı
desen). `task_skills` (n-n) bu görevin kapsamında UYGULANMIYOR (bkz. Kapsam
Dışı) — o yüzden "bazı skill_id geçerli bazısı değilse ne olur" sorusu bu
turda geçerli değil, ileride eklenirse tam-red (all-or-nothing) önerilir.
Hiçbir şey yapılamadı ama hata da yok: Bu uçlarda böyle bir durum yok — her
çağrı ya bir satır oluşturur (2xx) ya da açık bir hata (404/403/422) döner.
Boş sonuç ↔ hata ayrımı: Bu uçlar liste dönmüyor (tekil oluşturma), boş-liste
belirsizliği yok. Asıl ayrım 404 (scope dışı) ile 403 (scope içi, rol yanlış)
arasında — AC-S1/AC-S2 bunu kilitliyor.

## Test Strategy
Unit: 10% — yeni `scoped_tasks()`/`scoped_deliverables()` (varsa) query-layer testleri.
Integration: 80% — TestClient ile HTTP-uç seviyesinde happy path + tenant
isolation + rol-elevation + T5 precondition testleri (YET-65'teki aynı
desen: `X-Debug-User-Id` + gerçek PostgreSQL fixture).
E2E: 10% — minimal bir akış (ACTIVE engagement → task ekle → deliverable
ekle → T5 transition) tek senaryoda uçtan uca.

## Benchmark / Başarı Ölçütü
Coverage Target: 85%.
Performance Target: yok (MVP/hackathon, tek VPS, düşük hacim).
Memory: yok.
Görsel/UI kriteri: yok (backend-only, frontend 2.11/2.12/2.13'te ayrı).
Diğer ölçülebilir kriterler: `pytest tests/authorization -q` + yeni
task/deliverable testleri tamamı yeşil.

## Kapsam Dışı
- `Deliverable.evidence_ids[]` bağlantısı ve `Evidence` modeli — Evidence
  backend'de henüz yok (PLAN 2.5/2.6), bu görevde Deliverable sadece
  title/description/submitted_by ile oluşturuluyor. D11 kuralı ("en az 1
  Evidence bağlı olmalı") 2.6'da eklenecek.
- `task_skills` (n-n) tablosunun iş mantığı/skill arama-öneri — şema
  isteniyorsa bile bu görevde endpoint'lerde işlenmiyor (Jira alt görev
  açıklamalarında skill_id parametresi geçmiyor).
- Dosya yükleme (2.5, ayrı görev).
- Frontend (2.11/2.12/2.13, ayrı görev).
- Task/Deliverable güncelleme veya silme uçları — bu görev sadece oluşturma
  (POST) uçlarını kapsıyor, Jira açıklamasında GET/PATCH/DELETE geçmiyor.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/models/` — yeni `EngagementTask`, `Deliverable` modelleri
  (muhtemelen `task_deliverable.py`, mevcut `engagement.py`'nin yanına)
- `backend/app/services/engagement.py` — `transition_table`'a T5 satırı +
  yeni `create_task()`/`create_deliverable()` servis fonksiyonları
- `backend/app/services/authorization.py` — `scoped_tasks()`/
  `scoped_deliverables()` (mevcut `scoped_engagements()` deseninde)
- `backend/app/api/engagements.py` — yeni `POST /tasks`, `POST /deliverables`
  route'ları (mevcut `POST /transitions` deseninde)
- `backend/alembic/versions/` — yeni migration (task_deliverable tabloları) —
  **kullanıcı onayı gerekli, `plan` adımından sonra ayrıca sorulacak**

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı (YET-65'teki notla aynı) — sonraki adımlarda arama `backend/`
ve `docs/` ile sınırlı tutulmalı.

## Rollback Beklentisi
Migration geri alınabilir olmalı (`alembic downgrade -1` ile temiz düşmeli —
`verify` adımında test edilecek). Servis kodunda bir authz testi kırmızı
çıkarsa aynı PR içinde düzeltilir (YET-65'teki aynı kural) — 3+ dosyayı
etkileyen bir refactor'a dönüşürse kullanıcı onayı istenir.

## Risks
- **Migration onayı zorunlu** — CLAUDE.md kuralı: yeni tablo(lar)
  oluşturulmadan önce kullanıcıdan açık onay alınmalı, `plan` adımından
  hemen sonra ayrıca sorulacak.
- `task_skills` tablosunun bu görevde şema olarak mı (boş, iş mantığı yok)
  yoksa hiç mi oluşturulacağı net değil — `plan` adımında karar verilip
  kullanıcıya bildirilecek, sessizce eklenmeyecek.
- MCP_DOCKER (Saga) hâlâ bağlı olmayabilir — `saga_task_id` `null`.
- POST uçlarına özel rate limit yok — YET-65'teki kabul edilen risk aynı
  şekilde geçerli (düşük hacimli iç-kullanıcı ucu).

## Assumptions
- Task oluşturma yetkisi COORDINATOR/ORG_MEMBER/ORG_ADMIN'in HEPSİNE açık
  (sadece ADMIN'e değil) — Jira açıklaması bir rol ayrımı belirtmiyor, en
  geniş "kurum tarafı" yorumu varsayıldı; `plan`/kod incelemesinde mevcut
  `scoped_engagements()`'in zaten org_ids/institution_ids bazlı olduğu
  doğrulanacak.
- Deliverable'da `description` zorunlu değil (DOMAIN.md şemasında nullable
  işaretlenmemiş ama Evidence'daki gibi opsiyonel olabilir) — `plan`
  aşamasında DOMAIN.md şemasının nullable alanları netleştirilecek.

## Unknowns
- `due_at` alanının bir iş kuralı var mı (ör. geçmiş tarih reddedilir mi)?
  Jira/DOMAIN.md'de belirtilmiyor — `plan`/`code-copilot` aşamasında
  netleşmezse basit bir "gelecekte olmalı" kontrolü eklenmez (belirtilmeyen
  bir kısıt icat edilmeyecek).

## Sorular ve Cevaplar (ham kayıt)
1. Persona → Task: kurum tarafı (COORDINATOR/ORG_MEMBER/ORG_ADMIN),
   Deliverable: TALENT (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
2. Happy path (Task) → 201 + PLANNED status (Sonnet 5 low alt-ajanı).
3. Happy path (Deliverable) → 201, evidence_ids yok (Sonnet 5 low alt-ajanı,
   kullanıcı kararıyla uyumlu).
4. Çapraz-kurum/talent → 404 (Sonnet 5 low alt-ajanı, YET-65 deseniyle tutarlı).
5. DRAFT/PENDING_APPROVAL'da task/deliverable → 422 precondition (Sonnet 5
   low alt-ajanı — sadece ACTIVE'de yazılabilir varsayımı).
6. Kısmi başarı/task_skills → kapsam dışı bırakıldı (Sonnet 5 low alt-ajanı).
7. YET-81 (T5 precondition) → bu görevin kapsamında, mevcut
   `transition_table`'a satır eklenir (Sonnet 5 low alt-ajanı).
8. Benchmark → %85 coverage, performans hedefi yok (Sonnet 5 low alt-ajanı).
9. Kapsam dışı → Evidence, dosya yükleme, task_skills iş mantığı, frontend
   (Sonnet 5 low alt-ajanı).
10. Test stratejisi → 10/80/10 (Sonnet 5 low alt-ajanı, önceki görevlerle tutarlı).
11. Rollback/migration onayı → aynı PR'da düzeltme, migration için ayrı
    açık onay (Sonnet 5 low alt-ajanı, CLAUDE.md kuralına uygun).
12. task_skills kapsamı + submitted_by_user_id → submitted_by_user_id
    principal'dan (Sonnet 5 low alt-ajanı + threat-model AC-S3 ile
    pekiştirildi); task_skills kapsamı `plan` aşamasında netleşecek
    (Unknowns/Risks'e taşındı).
13. (kullanıcı mesajından) Evidence bağımlılığı → Deliverable evidence_ids[]
    OLMADAN kurulacak, bağlantı 2.6'ya bırakılıyor.
14. (kullanıcı mesajından) EngagementTask.status → PLANNED/IN_PROGRESS/DONE
    (docs/DOMAIN.md bu oturumda güncellendi).
