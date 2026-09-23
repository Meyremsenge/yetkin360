---
task_slug: skillsignal-self-claim-uretimi
jira_id: YET-104
saga_task_id: null
threat_model: done
priority: medium
coverage_target: 80
performance_target: null
memory_target: null
test_strategy:
  unit: 10
  integration: 80
  e2e: 10
affected_modules:
  - backend/app/models/skill_signal.py (yeni)
  - backend/app/models/__init__.py
  - backend/app/services/skill_claim.py (add_skill_claim() içine SkillSignal INSERT'i)
  - backend/app/services/authorization.py (yeni scoped_skill_signals())
  - backend/app/api/talent_skills.py (yeni GET /talents/me/signals route'u) veya yeni backend/app/api/signals.py
  - backend/alembic/versions/ (yeni migration — kullanıcı onayı gerekli)
---

# ATDD — skillsignal-self-claim-uretimi

## Jira Kaynağı
[YET-104 — SkillSignal: SELF_CLAIM türetme + GET /talents/me/signals (kısmi)](https://kuyusuzyusuf123.atlassian.net/browse/YET-104)
Açıklama (Jira'dan birebir): "YET-71'in ([PLAN 2.9] SkillSignal türetme) bağımsız/hazır
dilimi: source_type=SELF_CLAIM kaynağından sinyal türetme + GET /talents/me/signals ucu.
YET-71 (Meyrem'e atanmış) sadece source_type=ATTESTATION'ı kapsıyor ve 2.6/2.7/2.8'e
(Meyrem'in işi) bağımlı. Bu görev ondan bağımsız."
PLAN.md madde: 2.9'un bir alt-kümesi (Faz 2). Bağımlılık: yok (2.1-2.5 zaten mainde).

## Persona
**TALENT** — kendi beyan ettiği (SkillClaim) yetkinliklerin "kanıt dökümünü"
(`GET /talents/me/signals`) görüntüleyen öğrenci/çalışan. Bu görevde sadece
kendi verisi, başka hiçbir rol bu uca erişemez (API.md: yetki=`TALENT`).

## Hedef (Neden)
`docs/DOMAIN.md` §3.14'ün öngördüğü `SkillSignal` append-only tablosu henüz
hiç yok — "Neden STRONG?" sorusunun cevabı olan `GET /talents/me/signals`
ucu da yok. Bu görev, zaten var olan `SkillClaim` (Faz 1) akışına dokunmadan,
her beyan bir `source_type=SELF_CLAIM, strength=NONE` sinyaline dönüşecek
şekilde zinciri başlatır — DOMAIN.md'nin açık sorusunu (SELF_CLAIM her zaman
NONE mı?) kapatır ve DELIVERABLE/TASK/EVALUATION/ATTESTATION kaynakları
(Meyrem'in işi bitince) aynı tabloya eklenebilecek bir temel kurar.

## User Story
As a **TALENT**
I want **skill beyanımı yaptığımda bunun bir "sinyal" olarak kaydedilmesini
ve kendi sinyal dökümümü görebilmeyi**
So that **yetkinliklerimin nereden geldiğini (henüz sadece beyan olsa da)
takip edebileyim, ileride gerçek kanıtlarla güçlendiğini görebileyim**

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)

1. [Critical] Given kimlik doğrulanmış bir TALENT, When
   `POST /talents/me/skills` `{"skill_id":"..."}` çağırırsa (mevcut AC-1,
   değişmiyor), Then SkillClaim oluşturulmasıyla AYNI transaction'da bir
   `SkillSignal` satırı da oluşturulur: `{talent_id, skill_id,
   source_type:"SELF_CLAIM", source_id:<claim.id>, strength:"NONE",
   attested_by_org_id:null, occurred_at:<claim.created_at>}`.
2. [Critical] Given TALENT'ın en az bir skill claim'i (dolayısıyla en az bir
   SELF_CLAIM sinyali) var, When `GET /talents/me/signals` çağırırsa, Then
   **200** döner, body `docs/API.md` şemasıyla birebir:
   `{"items":[{"skill":{"id":"...","name_tr":"...","slug":"..."},"signals":
   [{"source_type":"SELF_CLAIM","strength":"NONE","occurred_at":"...",
   "attested_by":null,"superseded":false}]}]}`.
3. [Critical] Given aynı TALENT, When `GET /talents/me/signals?skill_id=<X>`
   çağırırsa (X kendi claim'lerinden biri), Then **200** döner, body sadece
   o skill'in grubunu içerir (`items` tek elemanlı).
4. [High] Given TALENT'ın HİÇ skill claim'i yok, When
   `GET /talents/me/signals` çağırırsa, Then **200** döner,
   `{"items":[]}` — 404 DEĞİL, boş liste geçerli bir durum.
5. [High] Given TALENT bir skill claim'i siler (`DELETE
   /talents/me/skills/{id}`, mevcut davranış değişmiyor), When aynı TALENT
   daha sonra `GET /talents/me/signals` çağırırsa, Then o skill'e ait
   SELF_CLAIM sinyali **HÂLÂ görünür** — SkillSignal append-only, claim
   silinse bile sinyal silinmez (DOMAIN.md §3.14).
6. [Medium] Given `skill_id` filtresi, TALENT'ın hiç claim'i olmayan (veya
   var olmayan) bir skill_id ile, When `GET /talents/me/signals?skill_id=<Y>`
   çağırırsa, Then **200** döner, `{"items":[]}` — 404 DEĞİL (aynı desende
   boş sonuç).
7. **AC-S1** [Critical] (threat-model) — Given TALENT A, When
   `GET /talents/me/signals?skill_id=<sadece TALENT B'nin claim ettiği bir
   skill>` çağırırsa, Then **200** döner, `{"items":[]}` — TALENT B'nin
   sinyali asla dönmez, ne var olduğu bilgisi bile sızmaz.
8. **AC-S2** [Critical] (threat-model) — `scoped_skill_signals()` sorgusu
   HER ZAMAN `principal.talent_id` ile filtrelenir; request'te (query param
   veya body) bir `talent_id` alanı YOKTUR, olsa bile yok sayılır (kaynak
   sahipliği oturumdan çıkar, URL'den/body'den değil).

## Threat Model
Çağrıldı — AC-S1/AC-S2 yukarıdaki Acceptance Criteria'ya eklendi. STRIDE-lite
özeti: **Info Disclosure/Elevation** en kritik kategori (`skill_id` filtresi
üzerinden başka bir talent'ın sinyaline erişim denemesi) — `scoped_skill_signals()`
ile kapatıldı. Tampering düşük risk (`talent_id` request şemasında hiç yok).
Spoofing (mevcut cookie-auth, değişmiyor), Repudiation (bu uç salt-okunur,
audit gerektirmiyor — SkillSignal'ın kendisi zaten append-only kanıt),
DoS (rate-limit yok, kabul edilen risk — düşük hacimli GET ucu, diğer
uçlarla tutarlı) bu görevde yeni bir tetikleyici oluşturmadı.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path: skill claim ekleme | `201 + {"skill":{...},"claimed_level":...}` (mevcut şema, DEĞİŞMİYOR) | SkillClaim + SkillSignal AYNI transaction'da INSERT edilir | Beyan eklendi | AC-1 |
| 2 | Happy path: sinyal listesi | `200 + {"items":[{"skill":{...},"signals":[{"source_type":"SELF_CLAIM","strength":"NONE",...}]}]}` | Yok (salt okuma) | Kanıt dökümü | AC-2, AC-3 |
| 3 | Hiç claim/sinyal yok | `200 + {"items":[]}` | Yok | Boş döküm | AC-4 |
| 4 | Claim silinmiş ama sinyal kalıcı | `200 + {"items":[{"skill":{...},"signals":[{"source_type":"SELF_CLAIM",...}]}]}` (claim yok, sinyal var) | Yok | Geçmiş sinyal hâlâ görünür | AC-5 |
| 5 | skill_id filtresi eşleşmiyor / başka talent'a ait | `200 + {"items":[]}` | Yok | Boş döküm (varlık sızmaz) | AC-6, AC-S1 |

Kısmi başarı: SkillClaim yazılıp SkillSignal yazılamazsa (ör. FK ihlali) —
İKİSİ DE aynı `session.flush()` içinde, aynı transaction'da olduğu için
SQLAlchemy hata fırlatır, `get_session` zaten `except`'te `rollback()`
yapıyor — SkillClaim de commit edilmez, DB'de HİÇBİR satır kalmaz. "SkillClaim
var ama SkillSignal yok" durumu bu tasarımda üretilemez.
Hiçbir şey yapılamadı ama hata da yok: Bu uçlarda böyle bir durum yok —
`POST /talents/me/skills` ya ikisini de yazar (201) ya da açık bir hata
(404/409/422) döner; `GET /talents/me/signals` her zaman ya dolu ya boş bir
liste döner, asla "sessizce hiçbir şey".
Boş sonuç ↔ hata ayrımı: "TALENT'ın hiç sinyali yok" ile "skill_id başka
talent'a ait" AYNI değeri (`{"items":[]}`) döner — bu BİLİNÇLİ bir tasarım
kararı (AC-S1), çünkü ikisini ayırmak varlık sızıntısına yol açar (başka
talent'ın o skill'i claim edip etmediği bilgisi sızar).

## Test Strategy
Unit: 10% — `scoped_skill_signals()` query-layer testi.
Integration: 80% — `add_skill_claim()`'in SkillSignal'i gerçekten yazdığının
DB'ye karşı doğrulanması, `GET /talents/me/signals` HTTP-uç testleri (happy
path + boş + filtre + çapraz-talent izolasyonu + claim-silinince-sinyal-kalır).
E2E: 10% — claim ekle → sinyal listesinde gör → claim'i sil → sinyal hâlâ
listede tek senaryoda uçtan uca.

## Benchmark / Başarı Ölçütü
Coverage Target: 80%.
Performance Target: yok (MVP/hackathon, tek VPS, düşük hacim).
Memory: yok.
Görsel/UI kriteri: yok (backend-only).
Diğer ölçülebilir kriterler: `pytest tests/authorization -q` + yeni testler
tamamı yeşil; append-only kural ihlali (SkillSignal'e UPDATE/DELETE) test
edilip reddedildiği doğrulanır.

## Kapsam Dışı
- `DELIVERABLE`/`TASK`/`EVALUATION`/`ATTESTATION` source_type'ları — YET-71
  ve bağımlı görevler (Meyrem'in işi), bu görevde SADECE `SELF_CLAIM`.
- Gerçek `superseded_by_id` mantığı — bu görevde hep `NULL`, supersede
  edilecek bir şey yok (tek kaynak SELF_CLAIM, hiçbir zaman "daha güçlü bir
  sinyal onu geçersiz kılıyor" senaryosu bu turda gerçekleşmiyor).
- `attested_by_org_id` — SELF_CLAIM için her zaman `NULL` (beyanı doğrulayan
  bir organizasyon yok).
- Frontend (ayrı görev, kapsam dışı).
- `POST /talents/me/skills`/`DELETE /talents/me/skills/{id}` uçlarının
  mevcut davranışı DEĞİŞMİYOR — sadece `add_skill_claim()` içine bir INSERT
  ekleniyor, response şeması aynı kalıyor.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/models/skill_signal.py` — yeni `SkillSignal` modeli
- `backend/app/models/__init__.py` — export
- `backend/app/services/skill_claim.py::add_skill_claim()` — SkillSignal
  INSERT'i eklenecek
- `backend/app/services/skill_signal.py` (yeni) — `list_skill_signals()`
  servis fonksiyonu (GET /talents/me/signals mantığı)
- `backend/app/services/authorization.py` — yeni `scoped_skill_signals()`
- `backend/app/api/talent_skills.py` (veya yeni `signals.py`) — yeni
  `GET /talents/me/signals` route'u
- `backend/alembic/versions/` — yeni migration (`skill_signals` tablosu) —
  **kullanıcı onayı gerekli, `plan` adımından sonra ayrıca sorulacak**

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı (önceki görevlerdeki notla aynı) — arama `backend/` ve `docs/`
ile sınırlı tutulmalı.

## Rollback Beklentisi
Migration geri alınabilir olmalı (`alembic downgrade -1` temiz düşmeli).
Servis kodunda bir authz testi kırmızı çıkarsa aynı PR içinde düzeltilir.

## Risks
- Migration onayı zorunlu — `plan` adımından hemen sonra ayrıca sorulacak.
- `scoped_skill_signals()` yeni yazılacak, `scoped_skill_claims()` deseniyle
  bilinçli kod tekrarı (merkezi yetkilendirme deseni korunuyor) — kabul
  edilen risk (Sonnet 5 alt-ajanı tarafından önerildi).
- MCP_DOCKER (Saga) bağlantı durumu bu oturumda değişken — `saga_task_id`
  `null` bırakıldı.

## Assumptions
- `GET /talents/me/signals` response'unda `attested_by` alanı SELF_CLAIM
  için `null` döner (API.md örneğinde sadece ATTESTATION için dolu
  gösterilmiş, SELF_CLAIM örneğinde bu alan hiç yok — `null` en güvenli
  varsayım, alan var ama boş).
- Yeni route mevcut `backend/app/api/talent_skills.py` dosyasına eklenecek
  (aynı `/talents/me/...` prefix'i) — `plan` aşamasında kod keşfiyle
  teyit edilecek, ayrı bir `signals.py` gerekirse orada karar verilir.

## Unknowns
- Yok — Sonnet 5 alt-ajanı ve threat-model tüm açık soruları kapattı.

## Sorular ve Cevaplar (ham kayıt)
1. Persona → TALENT, sadece kendi verisi (Sonnet 5 low alt-ajanı).
2. Happy path (claim→sinyal) → aynı transaction, occurred_at=claim.created_at
   (Sonnet 5 low alt-ajanı).
3. Happy path (GET) → filtre yoksa tüm skill'ler, varsa tek skill grubu
   (Sonnet 5 low alt-ajanı).
4. Hiç claim yok → 200 + boş liste (Sonnet 5 low alt-ajanı).
5. Claim silinince sinyal → hâlâ görünür, DOMAIN.md kuralı (Sonnet 5 low
   alt-ajanı).
6. Kısmi başarı → aynı flush'ta iki INSERT, atomic (Sonnet 5 low alt-ajanı).
7. Sessiz başarı senaryosu → yok, transaction atomicliği garanti ediyor
   (Sonnet 5 low alt-ajanı).
8. Benchmark → %80 coverage, performans hedefi yok (Sonnet 5 low alt-ajanı).
9. Kapsam dışı → DELIVERABLE/TASK/EVALUATION/ATTESTATION, superseded_by_id,
   attested_by_org_id hep NULL (Sonnet 5 low alt-ajanı).
10. Test stratejisi → 10/80/10 (Sonnet 5 low alt-ajanı).
11. Rollback → aynı transaction, FK ihlali → tam rollback (Sonnet 5 low
    alt-ajanı, doğrulandı).
12. scoped_skill_signals() + superseded_by_id → yeni yazılacak, hep NULL
    kalacak (Sonnet 5 low alt-ajanı).
13. (threat-model) Çapraz-talent skill_id filtresi → 200 + boş liste, varlık
    sızıntısı yok (AC-S1/AC-S2).
