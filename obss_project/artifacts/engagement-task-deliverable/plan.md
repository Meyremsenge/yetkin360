# Plan — engagement-task-deliverable
_Reference: atdd.md_

Frontend-pipeline: tetikleyici yok (backend-only görev, `.tsx`/`.css`/UI kriteri yok).

## Keşif Özeti

`backend/app/models/engagement.py`'deki `Engagement` modelinin CHECK
constraint'i (`ck_engagements_status`) **`PENDING_EVALUATION`'ı zaten
içeriyor** — T5 hedefi için şema tarafında ekstra bir CHECK değişikliği
gerekmiyor, sadece `engagement.py`'deki `transition_table`'a yeni bir satır
eklenecek.

`.claude/rules/database.md` (proje kuralı) **`engagement_tasks` tablo adını
ve "Hard delete serbest" politikasını zaten belirtiyor** — bu, atdd.md'nin
tahmin ettiği tablo isimlendirmesini (`EngagementTask` modeli →
`engagement_tasks` tablosu) doğruluyor. `Deliverable` için silme politikası
bu dosyada açıkça yazılmıyor; atdd.md D11 kuralı (en az 1 Evidence) bu
görevde uygulanmadığından, silme politikası netleşmeyen bir alan — Deliverable
şimdilik "Engagement gibi append-only değil, normal CRUD" varsayılıyor (kanıt
zincirinin parçası olsa da henüz Evidence'a bağlı değil), ama `code-copilot`
DELETE ucu YAZMAYACAK (atdd.md Kapsam Dışı), o yüzden bu ayrım bu turda
pratik bir etkiye sahip değil.

`backend/app/services/authorization.py`'deki `scoped_engagements()` +
`get_scoped_or_404()` deseni, **ayrı bir `scoped_tasks()`/
`scoped_deliverables()` fonksiyonu yazmadan doğrudan yeniden kullanılabilir**:
bu görevde sadece POST (oluşturma) uçları var, GET/liste ucu yok — servis
fonksiyonu önce `get_scoped_or_404(scoped_engagements(session, principal)...)`
ile engagement'ı kendi scope'unda bulur (404 zaten burada garanti), sonra
`ACTIVE` precondition'ı ve rol kontrolünü (`can_create_task`/
`can_submit_deliverable` gibi basit bir lambda, `transition_engagement()`'taki
`can_transition` deseniyle aynı) uygular, sonra child satırı oluşturur. Bu,
CAVEMAN ilkesine uygun — yeni bir scoped_*() soyutlaması eklemek gereksiz.

`backend/app/api/engagements.py`'deki mevcut `POST /{engagement_id}/transitions`
route'u, yeni `POST /{engagement_id}/tasks` ve `POST /{engagement_id}/deliverables`
route'ları için birebir takip edilecek şablon: aynı 401 kontrolü, aynı
try/except → HTTPException çevirisi deseni, aynı `session.commit()` sırası.

`backend/tests/test_engagement_transitions.py`'deki fixture'lar (`institution_a/b`,
`organization_a/b`, `talent_alice/bob`, `user_inst_coord_diana`,
`user_org_admin_evan`, `engagement_active_alice`) **doğrudan yeniden
kullanılabilir** — yeni task/deliverable testleri aynı dosyaya (veya paralel
bir `test_engagement_tasks.py`/`test_engagement_deliverables.py`'ye) bu
fixture'ları import ederek yazılabilir.

## Files to Modify

| File | Why | Risk |
|------|-----|------|
| `backend/app/models/__init__.py` | Yeni `EngagementTask`, `Deliverable` modellerini export listesine ekle | low |
| `backend/app/services/engagement.py` | `transition_table`'a T5 (`ACTIVE`→`PENDING_EVALUATION`, precondition: en az 1 Deliverable) satırı + yeni `create_engagement_task()`, `create_deliverable()` servis fonksiyonları | medium (mevcut transition mantığına dokunuyor) |
| `backend/app/api/engagements.py` | Yeni `POST /{id}/tasks`, `POST /{id}/deliverables` route'ları + Pydantic request/response şemaları | low (mevcut şablonu birebir takip ediyor) |

## New Files

| File | Purpose |
|------|---------|
| `backend/app/models/task_deliverable.py` | `EngagementTask` ve `Deliverable` SQLAlchemy modelleri (atdd.md §3.8 şemasına göre) |
| `backend/alembic/versions/<yeni_rev>_add_engagement_tasks_deliverables.py` | Migration: `engagement_tasks`, `deliverables` tabloları (down_revision=`h9i0j1k2l3m4`, mevcut tek head) |
| `backend/tests/test_engagement_tasks.py` | Task oluşturma testleri (happy path + tenant isolation + rol-elevation) |
| `backend/tests/test_engagement_deliverables.py` | Deliverable oluşturma testleri + T5 precondition testleri |

## Dependencies

- `app.services.authorization.Principal`, `scoped_engagements`, `get_scoped_or_404` — yeniden kullanılacak, yeni scoped fonksiyonu gerekmiyor.
- `app.services.engagement.transition_engagement` — T5 satırı buraya eklenecek, imza değişmiyor.
- `app.services.audit.log_audit_event` — `TASK_CREATED`/`DELIVERABLE_SUBMITTED` action'ları için mevcut fonksiyon yeniden kullanılacak.
- `app.models.base.Base`, `TimestampMixin`, `uuid7_default` — yeni modeller aynı taban sınıfı kullanacak.

## Migration Required?
**Evet** — iki yeni tablo: `engagement_tasks` (id, engagement_id FK, title,
description nullable, status CHECK IN ('PLANNED','IN_PROGRESS','DONE'),
due_at nullable, completed_at nullable, created_at, updated_at) ve
`deliverables` (id, engagement_id FK, title, description, submitted_by_user_id
FK→users, submitted_at, created_at, updated_at). `task_skills` (n-n) tablosu
bu görevde **oluşturulmayacak** — atdd.md'nin Risks bölümünde belirtildiği
gibi iş mantığı kapsam dışı, boş bir tabloyu şimdiden migration'a eklemek
CAVEMAN ilkesine (spekülatif şema) aykırı; ihtiyaç doğduğunda ayrı bir
migration'da eklenir.

**CLAUDE.md kuralı gereği bu migration'ı oluşturmadan/uygulamadan önce
kullanıcıdan açık onay alınacak** — bu plan.md'nin sunumunda ayrıca sorulacak.

## Risks
- (atdd.md'den taşındı) Migration onayı zorunlu — yukarıda tekrar vurgulandı.
- (atdd.md'den taşındı) `task_skills` kapsamı — **karar verildi: bu görevde
  hiç oluşturulmayacak** (yukarıdaki Migration bölümüne bkz.), atdd.md'nin
  "Risks"teki belirsizliği bu planla çözüldü.
- Deliverable'ın silme politikası netleşmedi ama bu görevde DELETE ucu
  yazılmadığı için pratik etkisi yok — ileride Evidence bağlantısı (2.6)
  eklendiğinde tekrar değerlendirilmeli.
- `transition_table`'a yeni bir satır eklemek mevcut T1-T4/T6 testlerini
  bozmamalı (sadece yeni bir `("ACTIVE","PENDING_EVALUATION")` key ekleniyor,
  var olan key'lere dokunulmuyor) — `verify` adımında tam test paketi
  (`pytest -q`) ile teyit edilecek.

## Open Questions

Yok — kod keşfi (CHECK constraint zaten PENDING_EVALUATION'ı içeriyor,
`engagement_tasks` tablo adı proje kuralında zaten sabit, scoped_engagements()
yeniden kullanılabilir) atdd.md'nin Unknowns/Risks'indeki belirsizlikleri
kapattı. Tek kalan karar noktası (migration onayı) Open Question değil,
CLAUDE.md'nin kendi zorunlu onay adımı — aşağıda ayrıca sorulacak.
