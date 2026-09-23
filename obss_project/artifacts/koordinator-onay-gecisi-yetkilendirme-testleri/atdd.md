---
task_slug: koordinator-onay-gecisi-yetkilendirme-testleri
jira_id: YET-65
saga_task_id: null
threat_model: done
priority: medium
coverage_target: 100
performance_target: null
memory_target: null
test_strategy:
  unit: 10
  integration: 80
  e2e: 10
affected_modules:
  - backend/tests/authorization/test_matrix.py
  - backend/tests/test_engagement_transitions.py
  - backend/tests/test_engagement_authorization.py
  - backend/app/services/engagement.py
  - backend/app/services/authorization.py
  - backend/app/api/engagements.py
---

# ATDD — koordinator-onay-gecisi-yetkilendirme-testleri

## Jira Kaynağı
[YET-65 — [PLAN 2.3] Koordinatör onayı geçişi + yetkilendirme testleri](https://kuyusuzyusuf123.atlassian.net/browse/YET-65)
Açıklama (Jira'dan birebir): "docs/AUTHORIZATION.md §5.1/§5.5 tam IDOR/tenant-isolation matrisi (COORDINATOR/ORG_ADMIN çapraz-kurum senaryoları) — YET-7 pending skip'lerinin kapatılması."
Alt görevler: YET-77 "authz-test ile Engagement tenant-isolation/IDOR matrisi (COORDINATOR/ORG_ADMIN çapraz-kurum)", YET-78 "docs/AUTHORIZATION.md §5.1/§5.5 A5, E1-E6 senaryolarının tam testi".
PLAN.md madde: 2.3 (Faz 2). 2.1 (Engagement modeli) ve 2.2 (durum makinesi) tamamlanmış.

## Persona
**COORDINATOR** (üniversite/kurum koordinatörü, `institution_id` kapsamlı) ve **ORG_ADMIN**
(kurum/organizasyon yöneticisi, `org_admin_ids` kapsamlı) — engagement onay/red/iptal
geçişlerini yapan iki rol. Test kapsamında ayrıca kıyaslama aktörü olarak ORG_MEMBER
ve TALENT de kullanılır (tenant-isolation'ın simetrik doğrulaması için).

## Hedef (Neden)
`transition_engagement()` (PLAN 2.2'de yazıldı) COORDINATOR/ORG_ADMIN yetkilendirme
mantığını zaten implemente ediyor, ama bu mantık şu ana kadar yalnız query-layer
(`scoped_engagements()`) seviyesinde test edilmiş — gerçek HTTP ucu
(`POST /engagements/{id}/transitions`) üzerinden çapraz-kurum/çapraz-organizasyon
IDOR senaryoları hiç doğrulanmamış. `tests/authorization/test_matrix.py`'deki
`YET-7 pending` placeholder'ların kapatılması ve docs/AUTHORIZATION.md §5.1 A5 +
§5.5 E1-E6 satırlarının gerçek testlere dönüşmesi gerekiyor.

## User Story
As a **proje güvenlik sorumlusu (Yusuf)**
I want **koordinatör/org-admin onay geçişlerinin çapraz-kurum ve çapraz-organizasyon
senaryolarında HTTP uç seviyesinde IDOR'a kapalı olduğunu kanıtlayan bir test paketi**
So that **açık kaynak repoda bu kritik yetkilendirme yüzeyi (BOLA) herkese açık
denetime dayanıklı olsun ve YET-7'nin bıraktığı placeholder'lar gerçek kanıta dönüşsün**

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)

1. [Critical] Given COORDINATOR A (`institution_id=X`) ve `institution_id=X`'e ait,
   `PENDING_APPROVAL` durumundaki bir engagement, When
   `POST /engagements/{id}/transitions` `{"to_status":"ACTIVE","version":1}` ile
   çağrılır, Then **200** döner, body `{"status":"ACTIVE","version":2,...}` içerir
   ve DB'de kayıt güncellenir.
2. [Critical] Given COORDINATOR A (`institution_id=X`) ve `institution_id=Y` (Y≠X)
   kurumuna ait bir engagement, When aynı ucu `PENDING_APPROVAL→ACTIVE` ile çağırır,
   Then **404** `{"code":"NOT_FOUND"}` döner — response body'de engagement'ın
   `status`/`institution_id` gibi hiçbir alanı bulunmaz (§5.5 E2).
3. [Critical] Given aynı çapraz-kurum senaryosu, When `to_status` alanı GEÇERSİZ
   bir değerle (`"FOOBAR"` veya tanımsız bir geçiş) gönderilir, Then yine **404**
   döner — **422 DÖNMEZ** (scope kontrolü, illegal-transition kontrolünden önce
   çalışmalı; aksi halde 404/422 farkı varlığı sızdırır).
4. [High] Given ORG_ADMIN, `org_ids` listesinde olup `org_admin_ids` listesinde
   OLMAYAN bir organizasyona ait `ACTIVE` engagement, When `ACTIVE→CANCELLED`
   (`reason` dolu) ile çağrılır, Then **403** `{"code":"FORBIDDEN"}` döner
   (kaynak org_ids kapsamında GÖRÜNÜR ama eylem yasak — 404 DEĞİL, §5.4 D-serisiyle
   aynı sınıf).
5. [High] Given ORG_A üyesi (ORG_MEMBER), When Org B'ye ait bir engagement'ı
   `GET`/`transitions` ile hedefler, Then **404** döner (§5.1 A5, zaten
   `test_engagement_access_org_member_read_own_org` ile query-layer'da
   doğrulanmış — bu AC onu HTTP uç seviyesine taşır).
6. [High] Given COORDINATOR A kendi kurumunun bir engagement'ını
   `PENDING_APPROVAL→REJECTED` yapmak isterken `reason` boş/eksik gönderirse,
   Then **422** `PRECONDITION_FAILED` döner, durum değişmez.
7. [Medium] Given COORDINATOR A, kendi kurumuna ait engagement için **eski**
   (bayat) bir `version` değeri gönderirse, Then **409** `CONFLICT` döner ve
   DB'de status **değişmez** — version tampering ile durum makinesi atlatılamaz
   (AC-S5 ile aynı senaryo, davranış sözleşmesi tablosunda tekrar).
8. [Medium] Given `TransitionEngagementRequest` şemasında `institution_id`/
   `organization_id`/`talent_id` alanı yok, When istemci body'ye bu alanları
   ekstra olarak eklerse, Then Pydantic bu alanları yok sayar/reddeder — yetki
   kapsamı client body'sinden GENİŞLETİLEMEZ.
9. **AC-S1** [Critical] (threat-model) — madde 2 ile aynı senaryonun güvenlik
   çerçevesi: COORDINATOR A → institution_id=Y engagement → 404, body'de hiçbir
   Y-kurumuna ait alan yok.
10. **AC-S2** [Critical] (threat-model) — madde 3 ile aynı: kontrol sırası
    (scope-check önce, illegal-transition sonra) 404/422 tutarsızlığını önler.
11. **AC-S3** [High] (threat-model) — madde 4 ile aynı: org_ids⊃org_admin_ids
    farkı doğru şekilde 403 (görünür-ama-yasak) üretir, 404 (yok sayılmış) değil.
12. **AC-S4** [Medium] (threat-model) — madde 8 ile aynı: request şemasında
    tenant-belirleyici alan yok, body enjeksiyonuyla scope genişlemez.
13. **AC-S5** [Medium] (threat-model) — madde 7 ile aynı: version tampering
    409'a düşer, durum değişmez (state machine bypass yok).
14. **AC-S6** [High] (threat-model) — `authz-test` skill'i ile §5.1 A5 ve §5.5
    E1-E6'nın TAMAMI parametrik matris olarak üretilir/koşulur; hiçbir
    principal×resource kombinasyonunda 403/404 arasında varlık sızıntısı
    (response şekli/alan seti tutarsızlığı) olmadığı teyit edilir.

## Threat Model
Çağrıldı — AC-S1 ile AC-S6 arası kriterler yukarıdaki Acceptance Criteria'ya
eklendi. STRIDE-lite özeti: en kritik risk **Elevation of Privilege**
(scope filtresi ile eylem-yetkisi kontrolü arasındaki fark — org_ids vs
org_admin_ids) ve **Information Disclosure** (404/422 sırası varlık sızdırabilir).
Tampering: `TransitionEngagementRequest` şemasında tenant alanı olmadığı için
düşük risk, yine de AC-S4 ile kilitlendi. Spoofing/Repudiation/DoS bu görevde
tetiklenmedi (auth zaten `get_current_principal`'dan geliyor, audit event her
geçişte zaten yazılıyor, rate-limit bu ucun kapsamı dışı — bkz. Risks).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path: COORDINATOR kendi kurumu, geçerli geçiş | `200 + {"id":"...","status":"ACTIVE","version":2,"talent_id":"...","organization_id":"...","institution_id":"...","kind":"...","title":"...","reason":null,"created_at":"...","updated_at":"..."}` | DB'de `status`/`version` güncellenir, audit event (`ENGAGEMENT_TRANSITIONED`) yazılır, `PENDING_APPROVAL` hedefse outbox'a `engagement.pending_approval` kuyruklanır | Geçiş başarılı, güncel engagement | AC-1 |
| 2 | Çapraz-kurum/çapraz-org (scope dışı) | `404 + {"code":"NOT_FOUND","message":"Engagement bulunamadı.","request_id":null}` | Yok — DB değişmez, audit yazılmaz | "Bulunamadı" | AC-2, AC-3, AC-5, AC-S1, AC-S2 |
| 3 | Kaynak görünür ama eylem yasak (org_ids⊃org_admin_ids farkı, veya TALENT'ın COORDINATOR işlemi denemesi) | `403 + {"code":"FORBIDDEN","message":"Bu geçişi yapma yetkiniz yok.","request_id":null}` | Yok | "Yetkiniz yok" | AC-4, AC-S3 |
| 4 | Geçersiz/eksik precondition (`reason` boş, `institution_id` NULL) | `422 + {"code":"PRECONDITION_FAILED","message":"..."}` | Yok | Alan-altı hata | AC-6 |
| 5 | Tanımsız geçiş (`to_status` transition tablosunda yok) | `422 + {"code":"ILLEGAL_TRANSITION","message":"..."}` | Yok | "Bu durumdan X'e geçilemez" | (mevcut, bu görevde değişmiyor) |
| 6 | Version tampering / optimistic lock çakışması | `409 + {"code":"CONFLICT","message":"Kayıt başka tarafından değiştirilmiş..."}` | Yok — DB'de status DEĞİŞMEZ | "Yeniden yükleyin" uyarısı | AC-7, AC-S5 |
| 7 | Kimlik doğrulanmamış istek | `401 + {"code":"UNAUTHORIZED"}` | Yok | Login'e yönlendirme | (mevcut, kapsam dışı değişiklik yok) |

Kısmi başarı: Bu görev feature kodunu DEĞİŞTİRMİYOR (sadece test + varsa küçük
authz bug fix), dolayısıyla "bir kısmı yazıldı bir kısmı olmadı" senaryosu
kod tarafında geçerli değil. Kod tarafında incelenen tek kısmi-başarı riski:
`transition_engagement()` içindeki `session.execute(update(...))` **tek bir
UPDATE statement** — ayrı bir `flush()` + sonradan exception fırlatma paterni
YOK, dolayısıyla `get_session`'ın `rollback()` davranışı (bkz. proje kısıtı)
burada veri kaybına yol açmıyor. `rowcount==0` durumunda zaten `VersionConflictError`
fırlatılıyor ve hiçbir alan değişmemiş oluyor — bu senaryo AC-7/AC-S5 ile test
edilir.
Hiçbir şey yapılamadı ama hata da yok: Bu uçta böyle bir durum YOK — her çağrı
ya 2xx ile bir state değişikliği yapar ya da 4xx/409 ile açık bir hata döner.
Sessiz "hiçbir şey olmadı ama 200" durumu mevcut kodda üretilmiyor (rowcount
kontrolü bunu garantiliyor).
Boş sonuç ↔ hata ayrımı: Bu uç liste dönmüyor (tekil kaynak), dolayısıyla
"boş liste" belirsizliği yok. Asıl ayrım 404 (yok/erişilemez) ile 422
(var ama geçiş geçersiz) arasında — AC-3/AC-S2 bu ayrımın kontrol SIRASINA
bağlı olduğunu ve sırası bozulursa varlık sızıntısı oluşacağını kilitler.

## Test Strategy
Unit: 10% — `scoped_engagements()`/`can()` gibi zaten var olan query-layer
birim testleri korunur, yeni unit test eklenmez (mantık zaten `test_matrix.py`'de var).
Integration: 80% — asıl eklenecek olan: `TestClient` ile gerçek HTTP çağrıları
(`POST /engagements/{id}/transitions`), gerçek PostgreSQL fixture'larıyla
(Org A/B, Institution A/B, iki coordinator, iki org_admin) parametrik IDOR matrisi.
`authz-test` skill'i bu matrisi üretir/koşar (YET-77).
E2E: 10% — minimal bir happy-path akışı (DRAFT→PENDING_APPROVAL→ACTIVE) tek
senaryoda uçtan uca doğrulanır; tam kullanıcı akışı bu görevin kapsamında değil.

## Benchmark / Başarı Ölçütü
Coverage Target: 100% — docs/AUTHORIZATION.md §5.1 A5 ve §5.5 E1-E6'nın TÜM
satırları (6 satır: E1-E6, artı A5) gerçek HTTP-uç testiyle karşılanmalı, skip
kalmamalı.
Performance Target: yok (saf yetkilendirme testi, performans kriteri anlamsız).
Memory: yok.
Görsel/UI kriteri: yok (bu görev backend-only, frontend değişikliği kapsam dışı).
Diğer ölçülebilir kriterler: `pytest tests/authorization -q` VE ilgili engagement
testleri (`test_engagement_transitions.py`, `test_engagement_authorization.py`)
tamamı yeşil; `test_matrix.py`'deki engagement'a özgü `pytest.skip()` YOK.

## Kapsam Dışı
- Yeni HTTP endpoint veya yeni transition/durum eklenmez.
- Frontend değişikliği yapılmaz (2.11 ayrı madde).
- Evidence/Evaluation/Attestation yetkilendirme testleri (YET-8/YET-9 kapsamı).
- `test_anonymous_public_profile_access` skip'i (talent profili public-access,
  YET-7'nin engagement-dışı kısmı) — bu görev SADECE engagement/koordinatör
  IDOR matrisini kapatır.
- Yeni migration.
- Rate limiting eklenmesi (bkz. Risks — kabul edilen risk).

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/tests/authorization/test_matrix.py` (mevcut placeholder'lar HTTP-uç
  seviyesine taşınacak/genişletilecek)
- `backend/tests/test_engagement_transitions.py`, `test_engagement_authorization.py`
- `backend/app/services/engagement.py` (`transition_engagement`) — yalnız bug
  bulunursa küçük düzeltme
- `backend/app/services/authorization.py` (`can`, `scoped_engagements`,
  `get_scoped_or_404`) — yalnız bug bulunursa küçük düzeltme
- `backend/app/api/engagements.py` — değişmesi beklenmiyor

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu makinede git kök dizininin proje klasörüyle birebir örtüşüp
örtüşmediği teyit edilmedi. Sonraki adımlarda (plan/code-copilot/test-copilot/
red-team) arama `backend/` ve `docs/` ile sınırlı tutulmalı; kök dizinden
sınırsız `grep -r`/`git log -p --all` kullanılmamalı.

## Rollback Beklentisi
Bu görev test-ağırlıklı: bir authz testi kırmızı çıkıp gerçek bir kod açığı
ortaya çıkarırsa, düzeltme **aynı PR/commit dizisi içinde** `authorization.py`/
`engagement.py`'de yapılır (dosya sayısı azdır, PLAN 2.3'ün amacı zaten bu
açığı kapatmaktır). Düzeltme 3+ dosyayı etkileyen bir refactor'a dönüşürse
CLAUDE.md'nin izin sınırına göre kullanıcıdan onay istenir ve gerekirse ayrı
bir takip görevi (yeni Jira/PLAN maddesi) önerilir — sessizce genişletilmez.

## Risks
- MCP_DOCKER (Saga sunucusu) bu oturumda bağlı değil (`CONNECTION_CLOSED`) —
  `saga_task_id` bu yüzden `null` bırakıldı. Saga senkronizasyonu bağlantı
  düzeldiğinde `jira-sync` skill'i ile manuel yapılmalı.
- Audit event'te `actor_ip=None` sabit geçiliyor (mevcut, bu göreve özgü değil)
  — kabul edilen risk, ayrı bir görev gerektirir, bu ATDD'nin kapsamı dışında.
- `POST /engagements/{id}/transitions` ucuna özel bir rate limit yok — proje
  genelinde rate limit login/register/upload uçlarına uygulanıyor
  (yetkin360-final-analiz.md), bu uç düşük hacimli iç-kullanıcı ucu olduğu
  için şimdilik kabul edilen risk.

## Assumptions
- `authz-test` skill'inin ürettiği parametrik matris, mevcut `test_matrix.py`
  fixture'larıyla (Org A/B, Institution A/B) uyumlu şekilde genişletilebilir
  varsayılıyor — teyit `plan` adımında yapılmalı.
- Yeni test dosyası açılıp açılmayacağı (örn. `test_engagement_idor_matrix.py`)
  yoksa mevcut dosyalara mı ekleneceği `plan` adımında netleştirilecek; bu ATDD
  bunu önceden karara bağlamıyor.

## Unknowns
- ORG_ADMIN'in `org_ids` ile `org_admin_ids` arasındaki fark gerçek seed/fixture
  verisinde (test dışı, gerçek onboarding akışında) nasıl kuruluyor — bu bilgi
  `plan`/`code-copilot` aşamasında `Principal` oluşturma koduna (muhtemelen
  `app/api/deps.py::get_current_principal`) bakılarak teyit edilmeli.

## Sorular ve Cevaplar (ham kayıt)
1. Yeni endpoint mi test mi? → Sadece test yazımı + gerekirse küçük authz
   düzeltmesi (Sonnet 5 low alt-ajanı tarafından yanıtlandı: kod zaten
   `transition_engagement()`'ı implemente etmiş, alt görevlerde yeni endpoint
   tanımlı değil).
2. Happy path somut örnek → COORDINATOR (institution_id=X) + aynı kurumun
   PENDING_APPROVAL engagement'ı → `{"to_status":"ACTIVE","version":1}` →
   200 + `{"status":"ACTIVE","version":2,...}` (Sonnet 5 low alt-ajanı
   tarafından yanıtlandı).
3. Edge case 1 (çapraz-kurum COORDINATOR) → 404 generic body (Sonnet 5 low
   alt-ajanı tarafından yanıtlandı: proje kuralı "403 değil 404",
   `get_scoped_or_404` zaten sağlıyor — kodda doğrulandı: `scoped_engagements`
   institution_id ile filtreliyor).
4. Edge case 2 (ORG_ADMIN çapraz-org) → 404 (Sonnet 5 alt-ajanının ilk cevabı) →
   **DÜZELTİLDİ:** kod incelemesinde (`authorization.py:174-177`,
   `engagement.py:278-284`) `scoped_engagements` ORG_ADMIN için `org_ids`
   (üyelik) ile filtreliyor, ama `can_transition` için `org_admin_ids`
   (adminlik) kontrol ediyor — org_ids⊃org_admin_ids olduğunda kaynak
   GÖRÜNÜR ama eylem YASAK, yani doğru cevap **403**, 404 değil. Bu
   çelişki kod okunarak (alt-ajanın tool kullanmadan verdiği cevap yerine)
   düzeltildi — AC-4/AC-S3'e yansıtıldı.
5. Kısmi başarı / sessiz başarı → kod tek UPDATE statement, flush-sonra-exception
   paterni yok, rowcount==0 → VersionConflictError (Sonnet 5 low alt-ajanı +
   kod okumasıyla teyit edildi).
6. Benchmark → coverage %100 (A5+E1-E6 tam), performans hedefi yok (Sonnet 5
   low alt-ajanı tarafından yanıtlandı).
7. Kapsam dışı → yeni endpoint/transition/frontend/YET-8-9 testleri/yeni
   migration (Sonnet 5 low alt-ajanı tarafından yanıtlandı).
8. Test stratejisi oranı → 10/80/10 unit/integration/e2e (Sonnet 5 low
   alt-ajanı tarafından yanıtlandı: authz testi ağırlıklı integration).
9. Rollback → aynı PR içinde düzeltme, 3+ dosya etkilerse kullanıcı onayı
   (Sonnet 5 low alt-ajanı tarafından yanıtlandı, CLAUDE.md izin sınırıyla
   uyumlu).
10. authz-test skill + Saga durumu → authz-test kullanılacak (YET-77 açıkça
    belirtiyor), Saga MCP bağlı değil → saga_task_id null (Sonnet 5 low
    alt-ajanı tarafından yanıtlandı, kullanıcıya ayrıca soruldu — kullanıcı
    "devam" dedi, bu varsayım onaylanmış sayıldı).
