---
task_slug: admin-eksikler-envanteri
jira_id: null
saga_task_id: null
threat_model: done
priority: high
coverage_target: 85
performance_target: "admin liste uçları <300ms (limit=200)"
memory_target: null
test_strategy:
  unit: 60
  integration: 30
  e2e: 10
affected_modules:
  - backend/app/api/admin.py
  - backend/app/services/organization.py
  - backend/app/services/skill.py
  - backend/app/services/fraud_flag.py
  - backend/tests/authorization/test_admin_*.py
  - frontend/lib/api/admin.ts
  - frontend/app/admin/**
  - docs/API.md
  - docs/AUTHORIZATION.md
  - PLAN.md
---

# ATDD — admin-eksikler-envanteri

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Saga MCP bu oturumda bağlı değil (`mcp__saga__*` aracı
bulunamadı) → `saga_task_id: null`; Saga kaydı açılamadı.

## Persona
Geliştirici ekip (plan sahibi) + son kullanıcı olarak platform admini
(`users.is_platform_admin = true`). Jüri dolaylı izleyici.

## Hedef (Neden)
Admin bölümünde "olması gerekip olmayan" her şeyi veri modeline göre envanterlemek;
hackathon sunumunda (9-11 Ekim, Faz 4: "yeni özellik yok, yalnız kırık olan") admin demosunu
kırabilecek/yanıltabilecek kalemleri önce kapatmak, kalanını hackathon sonrası yol haritasına koymak.

## User Story
As a platform admini / geliştirici ekip
I want admin bölümündeki eksiklerin modele göre ayrılmış, önceliklendirilmiş bir planını
So that demo öncesi sessiz hataları kapatıp kalan işleri kontrollü sırayla yapabileyim.

## Envanter (veri modeline göre)

Faz: **F4** = şimdi (kırık/yanıltıcı, yeni özellik değil) · **SONRA** = hackathon sonrası (yeni özellik).
AI modeli: işi `code-copilot`/`test-copilot`'ta yürütecek önerilen model.

### Organization
| # | Eksik | Kanıt | Faz | Öncelik | AI modeli |
|---|---|---|---|---|---|
| O1 | Tüm kuruluşları listeleme/arama ucu + ekranı yok | final-analiz §14.3 `(admin)/orgs`; `admin.py`'de yalnız kuyruk | SONRA | Medium | Sonnet |
| O2 | Onay/ret kararı kuruluşa bildirilmiyor | `set_verification_level`/`reject_verification` outbox `enqueue` çağırmıyor | SONRA | Medium | Sonnet |
| O3 | `note` alınıyor ama saklanmıyor; frontend hiç göndermiyor | `admin.py:229` yalnız `note_length`; `admin.ts` body'de note yok | SONRA | Low | Haiku |
| O4 | Kuruluşu askıya alma ucu yok | `Organization.status` var, set eden uç yok | SONRA | High | Opus (authz) |
| O5 | Kuyruk ekranında sayfalama yok — 50'den sonrası sessizce görünmez | `getVerificationQueue()` limit/offset göndermiyor | **F4** | Critical | Haiku |

### Institution
| # | Eksik | Kanıt | Faz | Öncelik | AI modeli |
|---|---|---|---|---|---|
| I1 | Admin tarafında kurum için hiçbir uç/ekran yok (liste, doğrulama seviyesi, domain atama) | `admin.py`'de institution yok; modelde `verification_level`/`domain`/`status` var | SONRA | High | Opus (authz) |
| I1-not | Herkes `POST /institutions` ile kurum açıp ADMIN olabiliyor (GUV-02) — demo öncesi bilinen risk olarak belgelenmeli | PLAN 3.52 notu, HATA_DUZELTME_PROMPT:865 | **F4** (yalnız doküman) | High | — |

### User
| # | Eksik | Kanıt | Faz | Öncelik | AI modeli |
|---|---|---|---|---|---|
| U1 | Kullanıcı listeleme/arama yok | final-analiz §14.3 `(admin)/users` | SONRA | Medium | Sonnet |
| U2 | Askıya alma/geri açma ucu yok — `SUSPENDED` şemada ve auth katmanında var, set eden yok (yalnız elle SQL) | `identity.py:26`, `auth.py:501`; grep'te yazan kod yok | SONRA | High | Opus (authz) |

### Skill
| # | Eksik | Kanıt | Faz | Öncelik | AI modeli |
|---|---|---|---|---|---|
| S1 | Kullanıcı skill önerisi + admin onayı yok | final-analiz §428, DOMAIN.md:207; API.md:603 açık soru | SONRA | Low | Sonnet |
| S2 | Frontend `parent_id`/`category`/`name_en`/yeniden etkinleştirme düzenleyemiyor (backend destekliyor) | `admin.ts` `createSkill`/`updateSkill` | SONRA | Low | Haiku |
| S3 | `GET /admin/skills` en çok 200 döner, frontend sayfalamıyor; hedef ~300 skill | `admin.py:274`, `getSkills()` | **F4** | Critical | Haiku |
| S4 | Frontend `Skill` tipi backend şemasından sapmış (`created_at` backend'de yok; `SOFT` kategorisi eksik) | `admin.ts:28-38` ↔ `SkillResponse` | **F4** | Medium | Haiku |

### FraudFlag
| # | Eksik | Kanıt | Faz | Öncelik | AI modeli |
|---|---|---|---|---|---|
| F1 | `CONFIRMED` kararı hiçbir sonuç üretmiyor (tanıklık geri çekme / askıya alma bağlantısı yok) | `fraud_flag.py:55-59` | SONRA | High | Opus |
| F2 | İncelenmiş işaret geçmişi listelenemiyor | `list_fraud_queue` yalnız PENDING | SONRA | Low | Haiku |
| F3 | Frontend sayfalama yok — 50'den sonrası görünmez | `getFraudQueue()` | **F4** | Critical | Haiku |

### Engagement
| # | Eksik | Kanıt | Faz | Öncelik | AI modeli |
|---|---|---|---|---|---|
| E1 | T10 `DISPUTED → RESOLVED` aktörü "INST:COORD veya ADMIN" ama servis katmanında bu geçiş yok | STATE_MACHINE.md:110; `services/` grep'inde iz yok | SONRA | Medium | Opus |

### AuditEvent
| # | Eksik | Kanıt | Faz | Öncelik | AI modeli |
|---|---|---|---|---|---|
| A1 | Denetim kaydı görüntüleme ucu/ekranı yok | `admin.py` | SONRA | Medium | Sonnet |
| A2 | Tüm admin audit kayıtlarında `actor_ip=None` | `admin.py` (6 çağrı) | SONRA | Low | Haiku |

### Complaint — Şikayet (YENİ model; kullanıcı talebi 2026-10-10)
Öğrenci, onaya gönderdiği staj/sertifika uzun süre yanıtsız kalırsa yetkiliyi admine şikayet eder.

| # | İş kalemi | Faz | Öncelik | AI modeli |
|---|---|---|---|---|
| C1 | Şema: `complaints` (durum değişir), `complaint_events` (append-only zaman çizelgesi), `complaint_attachments` — migration | SONRA | High | Opus |
| C2 | Öğrenci: şikayet açma + kanıt belgesi yükleme + kendi şikayetlerini görme (`POST/GET /complaints`) | SONRA | High | Sonnet |
| C3 | Admin: şikayet kuyruğu, detay, belgeyi okuma (`GET /admin/complaints`, `/admin/complaints/{id}`, ek indirme) | SONRA | High | Opus (authz) |
| C4 | Admin: kapat / gerekçe iste / gerekçeyi kabul-ret / diğer yetkililere yükselt / haklı bul (`POST /admin/complaints/{id}/transitions`) | SONRA | High | Opus |
| C5 | Yetkili: hakkındaki şikayeti görme + gerekçe yazma (`POST /complaints/{id}/explanation`) | SONRA | High | Sonnet |
| C6 | Bildirimler outbox ile: yetkiliye gerekçe talebi, diğer koordinatörlere/üyelere yükseltme, öğrenciye sonuç | SONRA | Medium | Sonnet |
| C7 | Damga + sayaç: haklı bulunan şikayet sayısı Keşfet'te ve kurum/kuruluş profilinde belirgin gösterilir | SONRA | High | Sonnet |
| C8 | Frontend: öğrenci şikayet formu + durum ekranı, yetkili gerekçe ekranı, `/admin/sikayetler` | SONRA | Medium | Sonnet |

Durum makinesi (öğrenci tüm ara durumlarda "İşlem devam etmekte" görür):
```
OPEN ──admin inceler──► UNDER_REVIEW ──admin haksız bulur──► DISMISSED (kapandı)
                              │
                              └─admin gerekçe ister─► EXPLANATION_REQUESTED ─yetkili yazar─► EXPLANATION_SUBMITTED
                                                              │ (süre doldu)                    │
                                                              ▼                                 ├─admin kabul─► RESOLVED (kapandı, damga yok)
                                                          ESCALATED ◄──────admin reddeder───────┘
                                              (aynı kurum/kuruluşun diğer koordinatör/üyelerine bildirilir)
                                                              │
                                              ├─onay işlemi yapıldı / tatmin edici yanıt─► RESOLVED
                                              └─yanıt yok / yetersiz─► UPHELD (haklı bulundu → damga + sayaç +1)
```
Terminal: `DISMISSED`, `RESOLVED`, `UPHELD`. Yalnız `UPHELD` sayaca yazılır.

### Çapraz (kabuk / doküman)
| # | Eksik | Kanıt | Faz | Öncelik | AI modeli |
|---|---|---|---|---|---|
| X1 | `/admin` kök sayfası ve ortak `layout.tsx` yok → `/admin` 404 | `frontend/app/admin/*.tsx` boş | **F4** | High | Haiku |
| X2 | `docs/API.md` §2.10 tablosunda skill uçları; `AUTHORIZATION.md` uç tablosunda skill + fraud-queue uçları eksik | API.md:567-573, AUTHORIZATION.md:361-363 | **F4** | Medium | Haiku |
| X3 | PLAN.md 3.39/3.49/3.50 kutuları açık (3.49'un ret kısmı kodda var: YET-198) | PLAN.md:313,323,324 | **F4** | Medium | — (elle) |

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)

Faz 4 kalemleri:
1. **AC-1 [Critical] (O5/F3/S3)** Given bir admin liste ucunda `limit`'ten fazla kayıt var, When
   admin ekranı açar, Then ilk sayfa gösterilir, "Sonraki" düğmesi etkindir ve sonraki sayfada
   kalan kayıtlar görünür — hiçbir kayıt sessizce gizlenmez. (Test doğrudan tetikler: limit+1 kayıt seed edilir.)
2. **AC-2 [Critical]** Given `GET /admin/{verification-queue|skills|fraud-queue}?limit=50&offset=50`,
   When admin çağırır, Then `200` + `{"items":[…], "limit":50, "offset":50, "has_more":true|false}`;
   `has_more` limit+1 kayıt çekilerek kesin hesaplanır.
3. **AC-3 [High]** Given `limit=0`, `limit=500` veya `offset=-1`, Then `422` +
   `{"error":{"code":"VALIDATION_ERROR","message":"…"}}`; sessiz kırpma yok. (Mevcut `Query(ge,le)` davranışı korunur.)
4. **AC-4 [Critical]** Given admin olmayan (talent / org admin / kurum koordinatörü) veya oturumsuz
   istek, When herhangi bir `/admin/*` ucuna (yeni parametrelerle dahil) gider, Then admin olmayana
   `404 NOT_FOUND`, oturumsuza mevcut `401`; 403 asla dönmez. Mevcut 42 yetkilendirme testi yeşil kalır.
5. **AC-5 [High] (X1)** Given giriş yapmış admin, When `/admin` adresine gider, Then 404 yerine üç
   admin ekranına bağlantı veren bir sayfa görür; admin olmayan `/admin/giris`'e yönlenir (yalnız UX —
   güvenlik sınırı sunucudadır).
6. **AC-6 [Medium] (S4)** Given `Skill` frontend tipi, Then backend `SkillResponse` ile aynı alanları
   taşır (`created_at` yok; kategori `SOFT` dahil); `npm run typecheck` geçer.
7. **AC-7 [Medium] (X2/X3/I1-not)** Given dokümanlar, Then API.md §2.10 beş skill ucunu, AUTHORIZATION.md
   skill + fraud-queue uçlarını listeler; PLAN.md'de 3.49'un durumu gerçeği yansıtır; GUV-02 bilinen risk
   olarak SECURITY.md'de yazılıdır.
8. **AC-8 [Medium]** Given boş kuyruk, Then `200` + `{"items":[],"limit":50,"offset":0,"has_more":false}`
   ve ekranda ne yapılacağını söyleyen boş durum metni.
9. **AC-9 [Medium]** Given liste isteği 500/ağ hatası/zaman aşımı, Then ekranda `aria-live` hata mesajı +
   "Tekrar dene"; önceki sayfa verisi başarılıymış gibi gösterilmez.

Güvenlik (threat-model, Faz 4 kapsamı):
- **AC-S1 [Critical] (E)** Given talent, org ADMIN'i, kurum koordinatörü ve askıya alınmış eski admin
  oturumları, When her biri `GET /admin/verification-queue?limit=1&offset=0`, `/admin/skills?limit=1`,
  `/admin/fraud-queue?limit=1` çağırır, Then admin olmayanlar `404 NOT_FOUND`, askıdaki `401` alır;
  yanıt gövdesinde `items`, `has_more`, `limit`, `offset` anahtarlarının hiçbiri bulunmaz (yeni zarf
  alanları kaynağın varlığını sızdırmaz).
- **AC-S2 [High] (D)** Given admin, When `limit=201`, `limit=100000`, `offset=-1`, `offset=abc` gönderir,
  Then `422`; sunucu 200'den fazla satır döndürmez. `has_more` için çekilen ek satır (limit+1) yanıtta
  asla yer almaz: `limit=200` ve 250 kayıtla `len(items) == 200`.
- **AC-S3 [High] (I)** Given `has_more` eklenmiş liste yanıtları, Then öğe şemaları değişmez:
  kuyruk öğesinde yalnız `id,name,legal_id,domain,verification_level,created_at`; fraud öğesinde e-posta,
  kişi adı veya tanıklık metni yoktur (yalnız mevcut `reason`, sayı içeren kural gerekçesi).
- **AC-S4 [High] (E)** Given `/admin` kök sayfası ve `layout.tsx`, When admin olmayan giriş yapmış kullanıcı
  `/admin`'e gider, Then sayfa hiçbir `/admin/*` verisini render etmez ve yönlendirir; aynı kullanıcının
  doğrudan API çağrısı yine `404` alır (frontend guard tek kontrol değildir — test API'yi doğrudan çağırır).
- **AC-S5 [Medium] (T)** Given `/admin` layout, Then admin olup olmadığı yalnız `/me` yanıtındaki
  `is_platform_admin` alanından okunur; URL parametresi, `localStorage` veya cookie'deki bir bayraktan okunmaz.

Güvenlik (yol haritası — U2/O4/O1/U1 uygulanırken zorunlu):
- **AC-S6 [Critical] (E/T)** `POST /admin/users/{id}/suspend`: hedef `id` yalnız path'ten, aktör yalnız
  oturumdan alınır; body'de `actor_id`/`is_platform_admin`/`status` gönderilse yok sayılır. Askıya alınan
  kullanıcının mevcut access ve refresh token'ı bir sonraki istekte `401` alır.
- **AC-S7 [High] (R)** Her askıya alma/geri açma `audit_events`'e `actor_user_id`, `subject_id`, `action`
  ile yazılır; serbest metin gerekçe ve tam e-posta yazılmaz (yalnız uzunluk).
- **AC-S8 [High] (I)** `GET /admin/users` yanıtında `password_hash`, token, `failed_login_count`,
  PRIVATE evidence alanı bulunmaz; arama parametresi `q` loglara yazılmaz (e-posta = PII).

Hackathon sonrası (her biri uygulanırken kendi atdd.md'sini alır; burada yalnız sözleşme sabitlenir):
10. **AC-10 [High] (U2/O4)** Askıya alma: var olmayan id → `404`; zaten `SUSPENDED` → `200` idempotent,
    yeni audit satırı yok; kendi hesabı veya son platform admini → `409 LAST_ADMIN_PROTECTED`.
11. **AC-11 [High]** Askıya alma + audit aynı transaction'da: audit yazımı hata verirse durum değişikliği de
    geri alınır (`get_session` rollback) — kısmi yazım yok.
12. **AC-12 [Medium]** O1/U1/I1/A1 liste uçları AC-2 zarfını ve AC-4 yetki davranışını aynen kullanır.

Şikayet akışı (C1–C8, hackathon sonrası):
13. **AC-13 [Critical]** Given öğrencinin onay bekleyen bir engagement'ı veya sertifika kontrolü en az
    `COMPLAINT_MIN_WAIT_DAYS` (varsayım: 7) gündür yanıtsız, When `POST /complaints`
    `{"subject_type":"ENGAGEMENT","subject_id":"…","description":"…"}` gönderir, Then `201` +
    `{"id":"…","status":"OPEN","subject_type":"ENGAGEMENT","subject_id":"…","created_at":"…"}`; hedef
    kurum/kuruluş ve yetkili sunucuda özneden türetilir (body'den alınmaz).
14. **AC-14 [High]** Given bekleme süresi dolmamış → `409 {"error":{"code":"TOO_EARLY","message":"…"}}`;
    aynı özne için açık şikayet varsa → `409 ALREADY_OPEN` (DB partial UNIQUE); özne zaten onaylanmış/
    reddedilmişse → `409 NOT_PENDING`.
15. **AC-15 [High]** Given öğrenci şikayete belge ekler (PDF/JPG/PNG, ≤10 MB), Then dosya magic-byte ile
    doğrulanır, `{uuid}.{ext}` adıyla saklanır; yalnız şikayet sahibi ve platform admini indirebilir.
16. **AC-16 [Critical]** Given admin `UNDER_REVIEW` şikayette, When `{"action":"REQUEST_EXPLANATION","note":"…"}`
    gönderir, Then durum `EXPLANATION_REQUESTED`, `complaint_events`'e satır, yetkiliye outbox bildirimi;
    `{"action":"DISMISS","reason":"…"}` → `DISMISSED`, öğrenciye bildirim. `reason` zorunlu.
17. **AC-17 [High]** Given yetkili gerekçe yazar (`POST /complaints/{id}/explanation` `{"text":"…"}`), Then
    `EXPLANATION_SUBMITTED`; admin `ACCEPT_EXPLANATION` → `RESOLVED`, `REJECT_EXPLANATION` → `ESCALATED` ve aynı
    kurum/kuruluşun diğer tüm aktif koordinatör/ADMIN üyelerine bildirim (şikayet edilen yetkili hariç).
18. **AC-18 [High]** Given `ESCALATED` şikayet, When admin `UPHOLD` verir, Then `UPHELD`; kurum/kuruluşun
    haklı bulunan şikayet sayacı 1 artar; Keşfet kartında ve profilinde damga + sayı görünür. Sayaç 0 ise
    damga hiç render edilmez (boş/"0 şikayet" rozeti yok).
19. **AC-19 [High]** Given açık (terminal olmayan) şikayet, Then öğrenci `GET /complaints` yanıtında
    `"status_label":"IN_PROGRESS"` görür — iç ara durum adı, admin notu ve yetkilinin gerekçe metni dönmez;
    terminalde `"DISMISSED" | "RESOLVED" | "UPHELD"` + admin'in sonuç gerekçesi döner.
20. **AC-20 [Medium]** Given geçersiz geçiş (ör. `OPEN` → `UPHOLD`, terminal durumdan herhangi biri), Then
    `409 INVALID_TRANSITION`, durum ve sayaç değişmez. Eşzamanlı iki admin kararı: ilki geçer, ikincisi
    `409` (satır `version`/`SELECT … FOR UPDATE`).
21. **AC-21 [Medium]** Given şikayet açıkken yetkili asıl onayı verir, Then şikayet kendiliğinden kapanmaz;
    admin kuyruğunda "özne artık beklemiyor" işaretiyle görünür ve admin `RESOLVED`'a alır (varsayım).

Güvenlik (şikayet):
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
Çağrıldı — AC-S1…AC-S8 yukarıdaki Acceptance Criteria'ya eklendi. Şikayet akışı için AC-S9…AC-S14
eklendi (yeni sınırlar: öğrenci→admin belge paylaşımı, admin→yetkili/kurum bildirimi, public damga).
Varlıklar/sınırlar: kuruluş kimlik verisi (`legal_id`, `domain`), fraud işaretleri, kullanıcı hesap durumu;
sınır tarayıcı→API (`require_platform_admin`, router seviyesi) ve API→DB.
STRIDE: S atlandı (kimlik doğrulama değişmiyor, mevcut `/auth/login`); T → AC-S5, AC-S6; R → AC-S7
(Faz 4 kalemleri salt okuma, yeni iz gerekmez); I → AC-S1, AC-S3, AC-S8; D → AC-S2; E → AC-S1, AC-S4, AC-S6.
Sıra notu: `limit`/`offset` doğrulaması framework seviyesindedir (`Query(ge,le)`) ama router bağımlılığı
`require_platform_admin` ondan önce çözülür mü doğrulanmadı — AC-S1 bu yüzden geçerli parametrelerle yazıldı;
"admin olmayan + geçersiz limit" için 404/422 sırası iddia edilmiyor.
Kabul edilen risk: admin uçlarında hız sınırı yok (tek/az sayıda güvenilir admin, sayfa boyutu 200 ile
sınırlı); A2 `actor_ip=None` Faz 4'te düzeltilmiyor (inkâr edilemezlik `actor_user_id` ile sağlanıyor).
Sonraki adım notu: `plan` aşamasında `authz-test` skill'i AC-S1/AC-S4/AC-S6 için rol × uç matrisini üretmeli.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path: `GET /admin/<liste>?limit=50&offset=50` | `200 {"items":[{"id":"…","name":"…"}],"limit":50,"offset":50,"has_more":true}` | Yok | İkinci sayfa, Önceki/Sonraki | AC-1, AC-2 |
| 2 | `limit=0` / `limit=500` / `offset=-1` | `422 {"error":{"code":"VALIDATION_ERROR","message":"…"}}` | Yok | Hata mesajı (frontend zaten geçerli değer yollar) | AC-3 |
| 3 | Tekil kaynak yok (`POST /admin/users/{id}/suspend`) | `404 {"error":{"code":"NOT_FOUND","message":"Kaynak bulunamadı."}}` | Yok, audit yazılmaz | "Kullanıcı bulunamadı" | AC-10 |
| 4 | Admin olmayan / oturumsuz | Admin olmayan: `404 {"error":{"code":"NOT_FOUND","message":"Kaynak bulunamadı."}}` · oturumsuz: mevcut `401` | Yok | Sayfa yok / `/admin/giris` | AC-4 |
| 5 | DB hatası | `500 {"error":{"code":"INTERNAL_ERROR","message":"…"}}`, iç detay sızmaz | Rollback | "Bir hata oluştu" + Tekrar dene | AC-9 |
| 6 | Frontend zaman aşımı | Sunucu kodu yok (istemci iptali) | Okumada yok; yazmada sunucu tamamlamış olabilir → liste yenilenerek doğrulanır | "Zaman aşımı" + Tekrar dene; yazma körü körüne tekrarlanmaz | AC-9 |
| 7 | Kısmi başarı: askıya alma yazıldı, audit hata verdi | `500 INTERNAL_ERROR`; tek transaction → askıya alma da geri alınır | Hepsi ya da hiçbiri | "İşlem tamamlanamadı", durum değişmemiş | AC-11 |
| 8 | Hiçbir şey yapılmadı ama hata yok | Zaten askıda: `200 {"id":"…","status":"SUSPENDED"}` (yeni audit yok) · boş kuyruk: `200 {"items":[],"limit":50,"offset":0,"has_more":false}` | Yok | "Zaten askıda" / boş durum metni | AC-8, AC-10 |
| 9 | Kombinasyon: admin kendini / son platform adminini askıya alır | `409 {"error":{"code":"LAST_ADMIN_PROTECTED","message":"…"}}` | Yok | Uyarı | AC-10 |
| 10 | Liste tam `limit` kadar kayıt döndü | `200` aynı zarf; `has_more` limit+1 sorgusuyla kesin | Yok | `has_more=false` ise Sonraki pasif | AC-2 |

Kısmi başarı: admin karar uçlarında durum değişikliği ve audit aynı transaction'dadır; biri düşerse ikisi
de geri alınır. Erken/ayrı commit yok; outbox olayı (O2) da aynı transaction'a yazılır, gönderim worker'da.
Hiçbir şey yapılamadı ama hata da yok: idempotent `200` + değişmemiş kaynak gövdesi; başarı iddiası
`status` alanıyla ve audit satırı sayısıyla doğrulanabilir.
Boş sonuç ↔ hata ayrımı: yetkili admin için boş liste her zaman `200 + {"items":[]}`; `404` yalnız yetki
yokluğu veya tekil kaynağın yokluğudur; hata gövdesi `error` anahtarı taşır, `items` taşımaz.
Nullable alanlar (UI kararı): `legal_id`, `domain` → "—"; `verified_at` null → "Doğrulanmadı";
`name_en`, `parent_id`, `merged_into_id` null → hücre boş/"—"; `subject_label`, `signal` null → satır
gizlenmez, "—" gösterilir. Hiçbiri `new Date(null)` veya literal "null" üretmez.

DÜZELTME (2026-10-10, uygulama sırasında doğrulandı): Bu tablodaki `{"error":{"code":…,"message":…}}`
sarmalayıcısı YANLIŞTIR. Gerçek hata gövdesi düz `{"code","message","request_id"}`'dir
(`backend/app/core/errors.py`). Liste zarfı `{"items","limit","offset","has_more"}` doğrudur. Sınıf nedeni:
mevcut hata biçimi kod okunmadan, alt-ajan önerisinden alındı (bkz. Sorular ve Cevaplar #12).

Not (orkestratör düzeltmesi): alt-ajan hata kodlarını küçük harf önerdi; koddaki mevcut sözleşme büyük
harftir (`NOT_FOUND`, `VALIDATION_ERROR` — `admin.py`), tablo ona göre yazıldı. `INTERNAL_ERROR` ve
`LAST_ADMIN_PROTECTED` kodlarının projedeki tam adı doğrulanmadı (bkz. Unknowns).

## Test Strategy
Unit: 60% — servis fonksiyonları (`list_*` sayfalama + `has_more`), frontend API client, sayfalama bileşeni.
Integration: 30% — `/admin/*` uçları gerçek DB ile + `tests/authorization` matrisi (her uç × her rol).
E2E: 10% — admin girişi → `/admin` → kuyrukta ikinci sayfaya geçiş.

## Benchmark / Başarı Ölçütü
Coverage Target: %85 (değişen dosyalarda)
Performance Target: admin liste uçları <300ms (limit=200)
Memory: —
Görsel/UI kriteri: sayfalama düğmeleri klavye ile erişilebilir, görünür focus; boş durum ve hata durumu
görünür (`vision-test` ile).
Diğer: envanterdeki 31 kalemin (23 eksik + 8 şikayet) %100'ü bir AC'ye veya "SONRA" gerekçesine bağlı; değişen/yeni her uç için
≥1 yetkilendirme testi; mevcut 42 admin yetkilendirme testi yeşil; limit+1 kayıtla sessiz kesilme = 0.

## Kapsam Dışı
Break-glass (Faz 5) · platform admin self-servis atama · SQLAdmin gibi hazır panel · AI'nin karar vermesi ·
Faz 4'te: S1, E1, F1, F2, O1–O4, U1, U2, A1, A2, I1 uçları (yol haritasında kalır, şimdi yazılmaz).

## Etkilenen Dosyalar/Modüller (bilinen)
Faz 4: `backend/app/api/admin.py` (yanıt zarfı), `services/organization.py`, `services/skill.py`,
`services/fraud_flag.py` (limit+1), `frontend/lib/api/admin.ts`, `frontend/app/admin/{page,layout}.tsx` (yeni),
üç admin `page.tsx`, `frontend/messages/tr.json`, `docs/API.md`, `docs/AUTHORIZATION.md`, `docs/SECURITY.md`, `PLAN.md`.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Git kökünün proje klasörü olduğu doğrulanmadı. Aramalar `backend/`, `frontend/`, `docs/` ile sınırlanır;
`node_modules` hariç.

## Rollback Beklentisi
Kalem başına ayrı commit. Test kırılırsa o commit `git revert` ile geri alınır (push yok), kalem "ertelendi"
işaretlenir. Faz 4 kalemleri migration gerektirmez → DB geri alma yok. Demo çalışır kalmak önceliktir.

## Risks
- Faz 4 kod dondurma: PLAN 3.16 kutusu açık ama tarih Faz 4 içinde. Liste yanıtına `has_more` eklemek
  mevcut `{"items":[…]}` sözleşmesini genişletir (kırmaz) — yine de sunum sırasında değişiklik riski.
- Yanıt zarfı değişimi 3+ dosyaya dokunur → CLAUDE.md gereği açık onay gerekir.
- I1/GUV-02: sahte kurum açma riski demo sırasında gösterilebilir.

- **Şikayet — mevcut kararlarla çelişki (kullanıcı kararı gerekir, sessizce uygulanmaz):**
  (1) Faz 4 "yeni özellik yok" → SONRA'ya kondu. (2) CLAUDE.md "trust score yasak" (§39): public damga +
  sayaç olumsuz bir itibar sinyalidir; algoritmik değil admin kararına dayansa da bu kuralın bilinçli
  daraltılmasını gerektirir (3.54'teki AI istisnası gibi PLAN'a yazılmalı). (3) "chat yasak": akış serbest
  mesajlaşma değil, aşama başına tek gerekçe + tek karar olarak sınırlandı. (4) Kapsam testi: şikayet
  olmadan beyan→kanıt→tanıklık zinciri çalışır → MVP dışı sayılır.
- Şikayet — kötüye kullanım: asılsız/toplu şikayetle bir kuruluşu damgalatma; damga gerçek bir tüzel kişi
  hakkında public olumsuz beyan (hukuki/itibar riski) → yalnız admin kararı + iki aşamalı yanıt hakkı.
- Şikayet — KVKK: şikayet metni ve ek kişisel veri içerir; saklama süresi ve silme yolu tanımlı değil.

## Assumptions
- (varsayım) "Uzun süre" = 7 gün; yapılandırılabilir sabit.
- (varsayım) Şikayet konusu: `PENDING_APPROVAL`/`PENDING_EVALUATION` engagement veya bekleyen sertifika kontrolü.
- (varsayım) Yetkili şikayet ekini göremez; yalnız admin'in talep notunu görür.
- (varsayım) Damga ayrı kolon değil, `UPHELD` şikayetlerden türetilen sayıdır; kalıcıdır.
- (varsayım) Yetkilinin gerekçe verme süresi 5 gün; dolunca admin elle `ESCALATED`'a alır (arka plan işi yok).
- (varsayım) "Modellere göre" = birincil kırılım veri modeli + kalem başına AI modeli sütunu.
- (varsayım) Faz 4'te yalnız sessiz kesilme/404/doküman kalemleri yapılır; yeni uç yazılmaz.
- (varsayım) Seed'deki skill sayısı 200'ü aşıyor veya aşacak (hedef ~300) — sayı doğrulanmadı.
- (varsayım) Test oranı 60/30/10 — alt-ajan önerisi, kullanıcı onayı bekliyor.

## Unknowns
- Şikayet: "uzun süre" kaç gün? Damga kalıcı mı, süreli mi (ör. 12 ay)? Kurumun itiraz hakkı var mı?
- Şikayet: yetkili şikayet edenin kimliğini görür mü (özne zaten belli ediyor)?
- Şikayet: damga `UPHELD` sayısının kaçıncısından itibaren görünür (1 mi, eşik mi)?
- Şikayet: kuruluşta başka üye/koordinatör yoksa yükseltme adımı atlanıp doğrudan karar mı verilir?
- Mevcut demo verisinde kuyruk/işaret sayısı 50'yi, skill sayısı 200'ü aşıyor mu (F4 kalemlerinin aciliyeti)?
- Reddedilen kuruluş yeniden başvurabiliyor mu (`verification_rejected_at` yalnız seviye yükselince temizleniyor)?
- Admin, işaretlenen tanıklığın (`subject_id`) detayını okuyabileceği bir uca sahip mi?
- E1 dispute akışı MVP kapsamında mı?
- A-15 kararı ("kurum domain'ini yalnız platform admini set eder") uygulandı mı?
- `INTERNAL_ERROR` / `LAST_ADMIN_PROTECTED` hata kodlarının projedeki adı.

## Sorular ve Cevaplar (ham kayıt)
1. Persona → geliştirici ekip + platform admini (Sonnet 5 low alt-ajanı tarafından yanıtlandı: envanteri ekip uygular, admin kullanır).
2. Ana hedef → demoyu kırabilecekler önce, kalanı yol haritası (alt-ajan: Faz 4 "yeni özellik yok").
3. "Modellere göre" → veri modeli + AI modeli sütunu (alt-ajan: ifade iki şekilde okunabilir, ikisini karşılamak maliyetsiz).
4. Faz 4'te yapılabilirler → O5, S3, F3, X1, X2, X3, S4 (alt-ajan: yalnız sessiz veri kaybı/yanıltma; U2/O1 yeni özellik).
5. Çıktı biçimi → tek şemsiye atdd.md, uygulamada kalem başına görev (alt-ajan: model başına dosya şimdi bakım yükü).
6. Edge case → 51+/201+ kayıtta sessiz kesilme; admin olmayanın erişimi 404 (alt-ajan).
7. Başarı ölçütü → kalemlerin %100'ü AC'ye bağlı, uç başına ≥1 authz testi, 42 test yeşil, kesilme = 0 (alt-ajan).
8. Kapsam dışı → break-glass, self-servis admin, SQLAdmin, AI kararı; S1/E1/F1/O1–O4/U1–U2/A1–A2/I1 sonraya; I1 riski belgelenir (alt-ajan).
9. Test oranı → 60/30/10 (alt-ajan: çoğu API sınır davranışı).
10. Rollback → kalem başına commit, kırılırsa revert, migration yok (alt-ajan).
11. Kabul sahibi → kullanıcı onayı + otomatik testler (alt-ajan).
12. Davranış sözleşmesi → yukarıdaki tablo (alt-ajan doldurdu; hata kodu büyük harfe orkestratör düzeltmesi).
- Bağımlılıklar / etkilenen dosyalar → kod okumasından (orkestratör keşfi, sorulmadı).
