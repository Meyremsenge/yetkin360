---
task_slug: sikayet-backend
jira_id: null
saga_task_id: null
threat_model: done
priority: high
coverage_target: 85
performance_target: "GET /admin/complaints (limit=200) <300ms"
memory_target: null
test_strategy:
  unit: 40
  integration: 60
  e2e: 0
affected_modules:
  - backend/alembic/versions/q7c1m2p3l4n5_add_complaints.py (yeni)
  - backend/app/models/complaint.py (yeni)
  - backend/app/schemas/complaint.py (yeni)
  - backend/app/services/complaint.py (yeni)
  - backend/app/api/complaints.py (yeni)
  - backend/app/api/admin_complaints.py (yeni)
  - backend/app/services/authorization.py (scoped_complaints* eklenir)
  - backend/app/workers/outbox_worker.py (3 handler)
  - backend/app/core/email_messages.py, backend/app/core/config.py
  - backend/app/services/discover.py, backend/app/api/discover.py, backend/app/api/organizations.py, backend/app/api/institutions.py (upheld_complaint_count)
  - backend/app/main.py, backend/app/models/__init__.py
  - docs/API.md, docs/AUTHORIZATION.md, .env.example
---

# ATDD — sikayet-backend

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Saga yok → `saga_task_id: null`.
Kaynak: `obss_project/artifacts/admin-eksikler-envanteri/atdd.md` kalemleri C1–C7 (backend), AC-13…AC-21, AC-S9…AC-S14.

## Persona
Öğrenci (talent), şikayet edilen yetkili (kurum koordinatörü / kuruluş supervisor-ADMIN'i), platform admini.

## Hedef (Neden)
Onaya gönderilen staj/sertifika kontrolü uzun süre yanıtsız kalınca öğrencinin yetkiliyi admine şikayet
edebilmesi; admin kararıyla haklı bulunan şikayetin kurum/kuruluşta görünür bir sayı olarak kalması.

## User Story
As a öğrenci, I want onayımı bekleten yetkiliyi belgeyle admine şikayet etmek, so that onay sürecim yürüsün
ve yanıtsız bırakan kurum/kuruluş görünür olsun.

## Acceptance Criteria
(Şemsiyeden birebir; numaralar korunur. Yorum/somutlaştırma "→" ile.)

13. **AC-13 [Critical]** Given öğrencinin onay bekleyen bir engagement'ı (`PENDING_APPROVAL`/`PENDING_EVALUATION`)
    veya sertifika kontrolü (`decision=PENDING`) en az `COMPLAINT_MIN_WAIT_DAYS` (7) gündür yanıtsız, When
    `POST /complaints {"subject_type":"ENGAGEMENT","subject_id":"…","description":"…"}`, Then `201` +
    `{"id":"…","status":"OPEN","status_label":"IN_PROGRESS","subject_type":"ENGAGEMENT","subject_id":"…","created_at":"…"}`;
    hedef kurum/kuruluş ve yetkili sunucuda özneden türetilir.
14. **AC-14 [High]** Süre dolmamış → `409 TOO_EARLY`; aynı özne için açık şikayet → `409 ALREADY_OPEN` (DB partial
    UNIQUE); özne beklemede değil → `409 NOT_PENDING`.
15. **AC-15 [High]** Ek (PDF/JPG/PNG, ≤10 MB) magic-byte ile doğrulanır, `complaints/{complaint_id}/{uuid}.{ext}`
    adıyla saklanır; yalnız şikayet sahibi ve platform admini indirebilir.
16. **AC-16 [Critical]** Admin `REQUEST_EXPLANATION {"note"}` → `EXPLANATION_REQUESTED`, `complaint_events` satırı,
    yetkiliye outbox; `DISMISS {"reason"}` → `DISMISSED`, öğrenciye outbox. `reason`/`note` zorunlu (yoksa 422).
17. **AC-17 [High]** Yetkili `POST /complaints/{id}/explanation {"text"}` → `EXPLANATION_SUBMITTED`; admin
    `ACCEPT_EXPLANATION` → `RESOLVED`, `REJECT_EXPLANATION` → `ESCALATED` + kurum/kuruluşun diğer aktif
    koordinatör/ADMIN üyelerine outbox (şikayet edilen hariç).
18. **AC-18 [High]** `ESCALATED` + `UPHOLD` → `UPHELD`; hedefin `upheld_complaint_count` değeri 1 artar ve
    `/discover/organizations`, `GET /organizations`, `GET /organizations/{id}`, kurum yanıtlarında görünür; 0 ise `0`.
19. **AC-19 [High]** Öğrenci görünümünde terminal olmayan şikayet `"status_label":"IN_PROGRESS"`; iç durum adı,
    admin notu, yetkili gerekçesi dönmez; terminalde `DISMISSED|RESOLVED|UPHELD` + `resolution_reason`.
20. **AC-20 [Medium]** Geçersiz geçiş → `409 INVALID_TRANSITION`, durum/sayaç değişmez; eşzamanlı ikinci karar `409`
    (`SELECT … FOR UPDATE` + opsiyonel `version` → `409 VERSION_CONFLICT`).
21. **AC-21 [Medium]** Şikayet açıkken özne onaylanırsa şikayet kapanmaz; admin yanıtında `subject_pending=false`;
    admin `RESOLVE` ile kapatır.

Güvenlik (threat-model'den aynen taşındı):
- **AC-S9 [Critical] (E)** Başka öğrencinin şikayeti: B öğrencisi `GET /complaints/{A_id}` ve
  `GET /complaints/{A_id}/attachments/{f}` → `404`; ilgisiz kurumun koordinatörü → `404`; şikayet edilen
  yetkili şikayeti görür ama **eki indiremez** (`404`).
- **AC-S10 [Critical] (E/I)** Admin yalnız şikayete bilinçli olarak eklenen belgeyi okur; aynı öğrencinin
  `PRIVATE` evidence'ı için `GET /evidence/{id}` admin'e hâlâ erişimsizdir (AUTHORIZATION §4.1 değişmez).
  Admin'in her ek indirmesi `audit_events`'e yazılır.
- **AC-S11 [High] (T)** `POST /complaints` body'sinde `organization_id`, `respondent_user_id`, `status`,
  `talent_id` gönderilse yok sayılır/422; öğrenci sahibi olmadığı `subject_id` ile → `404`.
- **AC-S12 [High] (D)** Öğrenci başına 24 saatte en çok 3 şikayet → 4.'de `429`; ek başına ≤10 MB, şikayet
  başına ≤5 ek; `.exe` içeriği `.pdf` uzantısıyla → `422` (magic-byte).
- **AC-S13 [High] (I)** Keşfet/profildeki damga yalnız sayı ve "doğrulamayı yanıtsız bıraktı" ibaresi taşır;
  şikayet metni, öğrenci kimliği, yetkilinin adı public yanıtta yer almaz. Bildirim e-postasında şikayet
  metni ve ek bulunmaz (yalnız panele bağlantı). Loglara şikayet/gerekçe metni yazılmaz.
- **AC-S14 [High] (R)** Her geçiş `complaint_events` (append-only, UPDATE/DELETE trigger ile yasak) +
  `audit_events`'e aktörle yazılır; `UPHELD` kararı geri alınamaz, düzeltme yeni bir olayla yapılır.

## Threat Model
Çağrıldı (şemsiye görevde) — AC-S9…AC-S14 değiştirilmeden taşındı; tekrar çalıştırılmadı (orkestratör talimatı).

## Durum makinesi (uygulanan)
| Eylem | İzinli kaynak durum | Hedef | Zorunlu alan / koşul |
|---|---|---|---|
| `START_REVIEW` | OPEN | UNDER_REVIEW | — (ek eylem, bkz. sapmalar) |
| `DISMISS` | OPEN, UNDER_REVIEW | DISMISSED | `reason` |
| `REQUEST_EXPLANATION` | OPEN, UNDER_REVIEW | EXPLANATION_REQUESTED | `note`; yetkili türetilmiş olmalı (`409 NO_RESPONDENT`) |
| (yetkili) explanation | EXPLANATION_REQUESTED | EXPLANATION_SUBMITTED | `text`; yalnız `respondent_user_id` |
| `ACCEPT_EXPLANATION` | EXPLANATION_SUBMITTED | RESOLVED | — |
| `REJECT_EXPLANATION` | EXPLANATION_SUBMITTED; EXPLANATION_REQUESTED **yalnız süre dolduysa** | ESCALATED | süre dolmadan → `409 DEADLINE_NOT_REACHED` |
| `RESOLVE` | ESCALATED; diğer terminal olmayanlar **yalnız `subject_pending=false`** | RESOLVED | — |
| `UPHOLD` | ESCALATED | UPHELD | — |
OPEN'dan gelen DISMISS/REQUEST_EXPLANATION önce `REVIEW_STARTED` olayı yazar. Terminal: DISMISSED/RESOLVED/UPHELD.

## Davranış Sözleşmesi
Hata gövdesi projenin gerçek biçimidir: `{"code":"…","message":"…","request_id":"…"}` (core/errors.py, düz).
Şemsiyedeki `{"error":{…}}` örneği koddaki sözleşmeyle uyuşmuyor → kod korunur (sapma olarak raporlanır).

| # | Durum | Dönen | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy: öğrenci şikayet açar | `201 {"id":"…","status":"OPEN","status_label":"IN_PROGRESS","subject_type":"ENGAGEMENT","subject_id":"…","created_at":"…"}` | complaints + complaint_events(CREATED) + audit | "Şikayetiniz alındı" | 13 |
| 2 | Bekleme dolmadı | `409 {"code":"TOO_EARLY",…}` | yok | süre mesajı | 14 |
| 3 | Açık şikayet var (race dahil) | `409 ALREADY_OPEN` | yok (savepoint) | | 14 |
| 4 | Özne beklemede değil / yetkili çözülemez | `409 NOT_PENDING` | yok | | 14 |
| 5 | Özne yok veya başkasının | `404 NOT_FOUND` | yok | | S11 |
| 6 | Body'de bilinmeyen alan (`talent_id`, `status`…) | `422 VALIDATION_ERROR` (`extra="forbid"`) | yok | | S11 |
| 7 | 24 saatte 4. şikayet | `429 {"code":"RATE_LIMITED",…}` | yok | | S12 |
| 8 | Öğrenci listesi | `200 {"items":[{"id","subject_type","subject_id","status_label","description","resolution_reason":null,"created_at","closed_at":null,"attachments":[]}],"limit":50,"offset":0,"has_more":false}` | yok | | 19 |
| 9 | Boş liste | `200 {"items":[],"limit":50,"offset":0,"has_more":false}` | yok | boş durum | 19 |
| 10 | Başka öğrenci / ilgisiz kurum / admin `GET /complaints/{id}` | `404` | yok | | S9 |
| 11 | Yetkili `GET /complaints/{id}` (talep sonrası) | `200 {"id","viewer_role":"RESPONDENT","status","subject_type","subject_id","request_note","explanation_due_at","explanation_text","created_at"}` (description, talent, ek yok) | yok | | C5 |
| 12 | Yetkili, talepten önce | `404` | yok | | S9 |
| 13 | Ek upload-url | `200 {"upload_url","upload_fields","object_key","expires_in":900}` | yok | | 15 |
| 14 | Ek kaydı | `201 {"id","mime_type","size_bytes","created_at"}` | attachment + event + audit | | 15 |
| 15 | Ek içeriği beyanla uyuşmuyor (`.exe`→pdf) | `422 {"code":"INVALID_FILE_CONTENT",…}` | yok | | S12 |
| 16 | Desteklenmeyen tür / >10 MB | `422 UNSUPPORTED_CONTENT_TYPE` / `422 FILE_TOO_LARGE` | yok | | S12 |
| 17 | 6. ek | `409 ATTACHMENT_LIMIT_REACHED` | yok | | S12 |
| 18 | Yüklenen nesne depoda yok | `422 UPLOAD_NOT_FOUND` | yok | | 15 |
| 19 | Depolama erişilemez | `503 STORAGE_UNAVAILABLE` | yok (ağ çağrısı txn dışında) | | 15 |
| 20 | Ek indirme (sahip / admin) | `200 {"download_url","expires_in":300}` | audit (`complaint.attachment_downloaded`) | | 15, S10 |
| 21 | Ek indirme (yetkili/başkası) | `404` | yok | | S9 |
| 22 | Ek içeriği taramadan sonra değişti | `409 ATTACHMENT_CONTENT_CHANGED` | audit DENIED | | 15 |
| 23 | Admin liste | `200 {"items":[{"id","status","subject_type","subject_id","subject_pending","target_type","target_id","target_name","attachment_count","explanation_due_at":null,"created_at"}],"limit":50,"offset":0,"has_more":false}` | yok | | C3 |
| 24 | Admin liste `limit=0/201`, `offset=-1` | `422` | yok | | C3 |
| 25 | Admin detay | `200 {…liste alanları, "talent_id","talent_name","description","respondent_user_id","request_note","explanation_text","resolution_reason","version","closed_at","attachments":[…],"events":[{"id","event_type","from_status","to_status","actor_role","actor_user_id","note","created_at"}]}` | yok | | C3 |
| 26 | Admin geçiş (geçerli) | `200 <admin detay>` (version+1) | event + audit + (gerekirse) outbox; tek txn | | 16-18 |
| 27 | Geçersiz geçiş / terminal | `409 INVALID_TRANSITION` | yok | | 20 |
| 28 | `version` uyuşmuyor | `409 VERSION_CONFLICT` | yok | | 20 |
| 29 | Admin olmayan `/admin/complaints*` | `404`; oturumsuz `401` | yok | | S9 |
| 30 | Yetkili gerekçe yanlış durumda / başkası | `409 INVALID_TRANSITION` / `404` | yok | | 17 |
| 31 | Var olmayan şikayet id | `404` | yok | | — |

Kısmi başarı: geçiş + complaint_events + audit_events + outbox aynı transaction'da (get_session sonunda tek commit);
biri düşerse hepsi geri alınır. İstisna: ek kaydı/indirme ağ çağrısı için okuma txn'i önce commit edilir, ardından
depo okunur, sonra yazma txn'i açılır (evidence `get_download_url` deseni). Ek yazımı başarısızsa nesne depoda
yetim kalabilir (kayıt yok → indirilemez; kabul edilen risk).
Hiçbir şey yapılamadı ama hata yok: aynı duruma tekrar geçiş yoktur → her zaman `409 INVALID_TRANSITION`
(sessiz 200 yok). Başarı `version` artışı ve `events` satırıyla doğrulanabilir.
Boş ↔ hata: yetkili kullanıcı için boş liste `200 + items:[]`; yetki yok/kaynak yok `404` (gövdede `items` yok).
Nullable alanlar (frontend kararı): `resolution_reason`, `closed_at`, `explanation_due_at`, `request_note`,
`explanation_text`, `respondent_user_id`, `target_name` null → "—"; `status_label` asla null değildir.

## Test Strategy
Unit 40% — durum geçiş tablosu, status_label eşlemesi, servis kuralları (TOO_EARLY/NOT_PENDING/ALREADY_OPEN/429).
Integration 60% — uçlar gerçek DB ile, `tests/authorization/test_complaints_authz.py` rol × uç matrisi, trigger testleri,
outbox handler'ları (SMTP monkeypatch).

## Benchmark / Başarı Ölçütü
Coverage %85 (yeni dosyalar). Her yeni uç ≥1 yetkilendirme testi; mevcut authorization paketi yeşil.
`alembic heads` tek başlı; upgrade/downgrade/upgrade temiz.

## Kapsam Dışı
Frontend (C8), arka plan zamanlayıcı (süre dolumu admin elle), yükseltilmiş üyelerin ayrı yanıt hakkı,
KVKK saklama/silme, admin bildirim e-postası, kurum için ayrı public profil ucu (yok; mevcut yanıtlara alan eklenir).

## Rollback Beklentisi
Tek migration: `alembic downgrade -1` üç tabloyu, trigger'ları ve indeksleri kaldırır. Commit kullanıcıya ait.

## Risks
- "trust score yasak" kuralı kullanıcı kararıyla daraltıldı: yalnız admin UPHOLD kararı sayılır, algoritma yok.
- Bildirim bağlantı yolları (`/sikayetler/{id}`, `/admin/sikayetler/{id}`) frontend ajanının rotasıyla eşleşmeyebilir.
- Paralel ajanlar aynı test DB'sini drop/create ediyor → testler ayrı bir DB'de koşulur (`TEST_DATABASE_URL`).

## Assumptions
- (varsayım, şemsiye) bekleme 7 gün, gerekçe süresi 5 gün — `COMPLAINT_MIN_WAIT_DAYS`, `COMPLAINT_EXPLANATION_DAYS`.
- (varsayım) Engagement'ın "beklemeye girdiği an" = o duruma geçişi yazan son `ENGAGEMENT_TRANSITIONED` audit satırı;
  yoksa `created_at`. Sertifika için `requested_by_talent_at`.
- (varsayım) Hedef/yetkili türetimi: `PENDING_APPROVAL` → kurum (engagement.institution_id), yetkili = kurumun en eski
  COORDINATOR'ı (yoksa en eski ADMIN'i); `PENDING_EVALUATION` → kuruluş, yetkili = `supervisor_user_id`, yoksa en eski
  ACTIVE ADMIN; sertifika → engagement'ın kurumu (yoksa kuruluşu), aynı kural. Hedef yoksa `409 NOT_PENDING`.
- (varsayım) Yetkili şikayeti ancak gerekçe istendikten sonra görür; açıklama metni ve eki görmez, talep notunu görür.
- (varsayım) Yükseltme sonrası hedefin koordinatör/ADMIN üyeleri şikayeti salt-okunur görür.
- (varsayım) Sayaç 1'den itibaren görünür; kalıcıdır.
- (varsayım) Rate limit DB sayımıyla (son 24 saatte açılan şikayet), talent satırı kilitlenerek uygulanır.
- (varsayım) `description` 10–4000, `note`/`reason`/`text` 1–2000 karakter.

## Unknowns
- Kurumun itiraz hakkı, damganın süresi, eşik (şemsiyeden taşındı).

## Sorular ve Cevaplar (ham kayıt)
Netleştirme soruları kullanıcıya sorulmadı (orkestratör talimatı); cevaplar şemsiye atdd.md'den alındı:
persona/hedef/happy path/edge case/sözleşme/kapsam → şemsiye C1–C7, AC-13…21; test oranı → orkestratör uygulaması
(backend API: 40/60/0, e2e frontend ajanında); rollback → tek migration downgrade; kalan boşluklar Assumptions'ta.
