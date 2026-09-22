---
task_slug: yet-11-skill-claims
jira_id: YET-11
saga_task_id: null
threat_model: done
priority: high
coverage_target: 85
performance_target: "p95 <200ms (basit CRUD, dış ağ çağrısı yok)"
memory_target: null
test_strategy:
  unit: 70
  integration: 20
  e2e: 10
affected_modules:
  - backend/app/api/talent_skills.py (yeni, veya me.py'ye eklenir — plan aşamasında karar verilecek)
  - backend/app/services/skill_claim.py (yeni)
  - backend/app/services/authorization.py (mevcut — yeni scoped_skill_claims() eklenir)
  - backend/app/models/skill_claim.py (yeni — SkillClaim modeli)
  - backend/alembic/versions/ (yeni migration — skill_claims tablosu)
---

# ATDD — yet-11-skill-claims

## Jira Kaynağı
[YET-11 — [PLAN 1.11] Talent yetkinlik beyanı: skill ekle/listele/çıkar](https://kuyusuzyusuf123.atlassian.net/browse/YET-11)
User Story (Jira'dan): "As a talent I want to declare, list, and remove
skills on my profile So that I can start building my competency record
before any institution attests to it."
Jira bağımlılığı: YET-2 (yetkilendirme) ve YET-10 (skill taksonomisi) —
ikisi de Tamamlandı, engel yok.

## Persona
Talent — kimlik doğrulanmış birey kullanıcı.

## Hedef (Neden)
"Beyan → kanıt → tanıklık → doğrulanmış deneyim" zincirinin ilk halkasını
kurmak — talent, kurumsal onay beklemeden kendi yetkinlik iddialarını
profiline ekleyebilmeli.

## User Story
As a talent
I want kendi profilime skill ekleyip listeleyip çıkarabilmek
So that bir kurum onaylamadan önce yetkinlik kaydımı oluşturmaya başlayabileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given kimliği doğrulanmış bir talent, When `POST /talents/me/skills`
   ile `{skill_id, claimed_level?}` (var olan ACTIVE bir skill) gönderilir,
   Then `201` + `{skill_id, claimed_level, source:"MANUAL"}` döner, `skill_claims`
   tablosuna bir satır eklenir.
2. [Critical] Given kayıtlı claim'leri olan bir talent, When `GET /talents/me/skills`
   çağrılır, Then `200` + `{items: [{skill: {...}, claimed_level}, ...]}` döner
   (her item'da skill'in temel alanları — id, slug, name_tr, name_en, category
   — join edilerek).
3. [Critical] Given kendi claim'i olan bir talent, When
   `DELETE /talents/me/skills/{skill_id}` çağrılır, Then `204` döner, satır
   **hard-delete** edilir (DATABASE.md §2.2'de `deleted_at` kolonu yok).
4. [Critical] Given var olmayan bir `skill_id`, When `POST /talents/me/skills`
   çağrılır, Then `404 SKILL_NOT_FOUND` döner, hiçbir satır eklenmez.
5. [Critical] Given talent'ın zaten claim ettiği bir `skill_id`, When aynı
   `skill_id` ile tekrar `POST` çağrılır, Then `409 ALREADY_CLAIMED` döner,
   hiçbir değişiklik yapılmaz.
6. [High] Given `status` alanı `ACTIVE` olmayan (`MERGED` veya `DEPRECATED`)
   bir skill, When bu skill'in `id`'siyle `POST /talents/me/skills` çağrılır,
   Then `404 SKILL_NOT_FOUND` döner (aynı kod — status ayrımı istemciye
   sızdırılmaz; skill var olsa da taksonomide artık "seçilebilir" değildir).
   `merged_into_id`'ye otomatik yönlendirme YAPILMAZ (kullanıcı iradesi
   dışında farklı bir skill'e claim atmak MVP kapsamını genişletir).
7. [High] Given talent'ın hiç claim etmediği veya var olmayan bir `skill_id`,
   When `DELETE /talents/me/skills/{skill_id}` çağrılır, Then `404` döner.
8. [Medium] Given hiç skill claim'i olmayan bir talent, When
   `GET /talents/me/skills` çağrılır, Then `200` + `{items: []}` döner (boş
   liste bir hata değildir).
9. [Critical] AC-S1: Given `talent_id`'si olmayan (register invaryantı
   bozulmuş) veya kimliği doğrulanmamış bir istek, When bu üç uçtan biri
   çağrılır, Then `404`/`401` döner (403 değil).
10. [Critical] AC-S2: Given bir talent'ın body/URL'de **başka bir talent'ın**
    `skill_claim` kaydına ait bir tanımlayıcı göndermesi (ör. DELETE için
    kullanılan `skill_id` başka bir talent'a ait bir claim'e karşılık
    geliyor ama kendi claim'i değil), When işlem yapılır, Then `404` döner
    (kaynak her zaman `principal.talent_id`'ye göre scoped sorgulanır,
    başka talent'ın claim'i "yok" gibi görünür).
11. [High] AC-S2: Given `POST /talents/me/skills` body'sinde `talent_id`
    veya başka bir sahiplik alanı (ör. `user_id`) gönderilir, When istek
    işlenir, Then bu alanlar tamamen yok sayılır — hedef `talent_id` her
    zaman sunucuda `principal.talent_id`'den çözülür (Pydantic şemasında
    `talent_id` alanı hiç YOK).
12. [Critical] AC-S3: Given `GET /talents/me/skills`, When çağrılır, Then
    yanıt yalnızca çağıranın **kendi** claim'lerini içerir — sorgu her
    zaman `scoped_skill_claims(session, principal)` üzerinden yapılır,
    hiçbir çıplak `select(SkillClaim)` veya client-supplied `talent_id`
    filtresiyle çalışmaz.
13. [High] AC-S4: Given `DELETE /talents/me/skills/{skill_id}` çağrısındaki
    `skill_id`, başka bir talent'ın claim'ine ait (kendi claim'i değil),
    When istek yapılır, Then `404` döner ve yanıt o claim'in var olup
    olmadığına dair hiçbir bilgi sızdırmaz (aynı `404`, kendi hiç claim
    etmediği bir skill_id ile aynı davranış — ayırt edilemez).

## Threat Model
Çağrıldı — STRIDE-lite uygulandı, AC-S1..AC-S4 kriterleri yukarıdaki
Acceptance Criteria listesine eklendi.

**Varlıklar ve sınırlar:** `SkillClaim` (talent'ın kendi verisi, kişisel
yetkinlik beyanı), tarayıcı→API güven sınırı. Kiracı sınırı klasik anlamda
yok (kendi verisi) ama "başka bir talent'ın claim'i" sınırı var (AC-S4).

**STRIDE-lite:**
- **Spoofing** — mevcut `AUTH` middleware'i kapsıyor → atlandı.
- **Tampering** — İstemciden gelen `talent_id`/sahiplik alanlarına
  güvenilmemesi gerekiyor → AC-S2.
- **Repudiation** — Kullanıcının kendi profiline skill ekleyip çıkarması,
  üçüncü bir tarafı etkilemeyen düşük-hassasiyetli bir self-servis işlem;
  YET-7'de aynı gerekçeyle audit logging zorunlu tutulmamıştı, aynı karar
  burada da geçerli — **kabul edilen kapsam dışı**.
- **Info disclosure** — `GET`'in yalnız kendi verisini dönmesi → AC-S3.
  `DELETE`'in başka talent'ın claim'i hakkında bilgi sızdırmaması → AC-S4.
- **DoS** — Basit CRUD, dış ağ çağrısı yok, rate-limit gerektirmiyor —
  **kabul edilen kapsam dışı** (YET-7'deki gerekçeyle aynı).
- **Elevation** — Yetkinin sunucuda (`principal.talent_id`, URL'de talent
  id parametresi olmadan) kontrol edilmesi → AC-S2, AC-S3.

**Kabul edilen risk:** Repudiation (audit logging yok) ve DoS (rate-limit
yok) bilinçli olarak kapsam dışı bırakıldı — gerekçe yukarıda, düşük
hassasiyetli self-servis CRUD işlemi (YET-7 ile tutarlı).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — POST skill ekleme | `201` + `{skill_id, claimed_level, source:"MANUAL"}` | `skill_claims` INSERT (tek transaction) | Eklenen skill + seviyesi | AC-1 |
| 2 | Happy path — GET listeleme | `200` + `{items:[{skill,claimed_level}]}` | Yok (salt okuma) | Tüm claim'ler | AC-2 |
| 3 | Happy path — DELETE çıkarma | `204`, boş gövde | `skill_claims`'ten hard-DELETE | Boş yanıt | AC-3 |
| 4 | Var olmayan `skill_id` ile POST | `404` + `{code:"SKILL_NOT_FOUND",...}` | Yok | Genel hata mesajı | AC-4 |
| 5 | Zaten eklenmiş skill ile POST | `409` + `{code:"ALREADY_CLAIMED",...}` | Yok | "Bu skill zaten eklenmiş" | AC-5 |
| 6 | `MERGED`/`DEPRECATED` skill ile POST | `404` + `{code:"SKILL_NOT_FOUND",...}` | Yok | Genel hata mesajı (status ayrımı sızdırılmaz) | AC-6 |
| 7 | Var olmayan/claim edilmemiş `skill_id` ile DELETE | `404` + `{code:"SKILL_CLAIM_NOT_FOUND",...}` | Yok | Genel hata mesajı | AC-7 |
| 8 | Boş liste — GET | `200` + `{items: []}` | Yok | Boş dizi | AC-8 |
| 9 | Yetkisiz erişim | `404`/`401` (403 değil) | Yok | Genel hata mesajı | AC-S1 |
| 10 | POST body'sinde `talent_id`/`user_id` gönderilirse | `201` (yok sayılır, hedef `principal.talent_id`) | Yalnızca kendi claim'i eklenir | Kendi claim'i oluşur | AC-S2 |
| 11 | Başka talent'ın claim'i olan `skill_id` ile DELETE | `404` (kendi hiç claim etmediği skill ile aynı) | Yok | Genel hata mesajı, ayırt edilemez | AC-S4 |

Kısmi başarı: Bu üç uç tek-satırlık atomic işlemler (tek INSERT veya tek
DELETE) — "kısmi başarı" durumu yapısal olarak oluşmaz (birden fazla alan
güncelleyen bir PATCH yok). Silinmiş satır: yok, gerekçe: her işlem zaten
tek bir DB mutasyonuna karşılık geliyor.

Hiçbir şey yapılamadı ama hata da yok: Oluşmaz — POST/DELETE her zaman ya
açık bir mutasyon yapar ya da açık bir hata koduyla reddeder, "sessiz
başarı" riski yok (mutasyon öncesi tüm kontroller — skill var mı, ACTIVE mi,
zaten claim edilmiş mi — DB'ye dokunmadan önce yapılır).

Boş sonuç ↔ hata ayrımı: `GET /talents/me/skills` boş liste (`{items:[]}`)
her zaman `200` döner — "hiç skill eklenmemiş" ile "yetkisiz erişim" asla
karışmaz çünkü ikincisi zaten endpoint'e hiç ulaşmadan `404`/`401` ile
kesiliyor (AC-S1).

## Test Strategy
Unit: 70% — skill-var-mı/ACTIVE-mi kontrolü, duplicate-claim kontrolü,
MERGED/DEPRECATED reddi mantığı.
Integration: 20% — endpoint + DB + `scoped_skill_claims()` akışı.
E2E: 10% — POST → GET → DELETE → tekrar GET tam akışı.

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: p95 <200ms (basit CRUD, dış ağ çağrısı yok).
Memory: Belirtilmedi.
Görsel/UI kriteri: Yok — backend-only, frontend kapsamı ayrı (PLAN 1.14).
Diğer ölçülebilir kriterler: —

## Kapsam Dışı
- Skill arama/öneri ucu — YET-10 Jira'da "Tamamlandı" görünüyor ama kod
  tabanında hiçbir skill API/arama ucu/seed script'i bulunamadı (yalnız
  `Skill` tablosu migration'da var). Bu YET-11'in kapsamı dışında bir
  tutarsızlık, bu görevde düzeltilmeyecek — ayrı not (bkz. Risks).
- `GET /talents/me/signals` (Faz 2, Attestation/SkillSignal henüz yok).
- `skill_claim_history` tablosu (DOMAIN.md §6'da bahsi geçen, DATABASE.md'de
  "açık soru" olarak işaretli — bu görevde YOK).
- `claimed_level` güncelleme — API.md'de `PATCH /talents/me/skills/{id}`
  diye bir uç tanımlı değil; seviye değiştirmek isteyen kullanıcı silip
  yeniden eklemeli.
- Admin skill yönetimi, `is_curated` onay akışı (PLAN 3.6).

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/api/talent_skills.py` (yeni router — `plan` adımında kesin
  dosya adı netleşecek, `me.py`'ye eklenmesi de değerlendirilecek).
- `backend/app/services/skill_claim.py` (yeni — `add_skill_claim`,
  `list_skill_claims`, `remove_skill_claim`).
- `backend/app/models/skill_claim.py` (yeni — `SkillClaim` ORM modeli,
  DATABASE.md §2.2 şemasına birebir).
- `backend/app/services/authorization.py` (mevcut — yeni
  `scoped_skill_claims(session, principal)` fonksiyonu eklenir, mevcut
  fonksiyonlara dokunulmaz).
- `backend/alembic/versions/` (yeni migration — `skill_claims` tablosu,
  onay gerektirir).
- `backend/app/models/skill.py` (mevcut `Skill` — salt okunur kullanılır,
  DEĞİŞTİRİLMEZ).

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulandı (YET-9'da) — git reposu kökü proje klasörüyle aynı. Arama
`backend/`/proje klasörüyle sınırlı tutulmalı.

## Rollback Beklentisi
POST/DELETE başarısız olursa (404/409 dönen durumlar) hiçbir satır
INSERT/DELETE edilmemiş olmalı — tüm kontroller (skill var mı, ACTIVE mi,
zaten claim edilmiş mi, silinecek claim var mı) DB mutasyonundan önce
tamamlanmalı (postmortem koşum 1'in "flush sonra rollback" tuzağına
düşülmemeli — bu üç uçta zaten tek mutasyonluk basit işlemler olduğu için
risk düşük, ama kontrol sırası yine de netleştirilmeli).

## Risks
- **DOMAIN.md §3.6 ile DATABASE.md §2.2 arasında şema tutarsızlığı**
  bulundu: DOMAIN.md `self_level`/`note`/`deleted_at` alanlarından
  bahsediyor (soft-delete + not alanı), DATABASE.md ise `claimed_level`/
  `source`/`confirmed_by_user_at` (hard-delete, not alanı yok) tanımlıyor.
  CLAUDE.md kuralı gereği ("şema esastır") **DATABASE.md esas alındı** —
  DOMAIN.md güncel değil, ayrı bir dokümantasyon senkronizasyon görevi
  gerektirir (bu görevin kapsamı dışı).
- **YET-10'un iddia ettiği kapsam kod tabanında bulunamadı** — Jira'da
  "Tamamlandı" işaretli ama skill arama ucu/seed script'i yok, yalnız
  `Skill` tablosu var. Bu YET-11'i bloke etmiyor (skill'lere `skill_id`
  ile doğrudan erişilecek, arama gerekmiyor) ama Jira durumu şüpheli —
  `postmortem`'e not düşülecek.
- MERGED/DEPRECATED skill için `404` (ayrı bir kod değil) dönme kararı bir
  varsayım — kullanıcı onayı gerekebilir (bkz. Assumptions).

## Assumptions
- MERGED/DEPRECATED skill'e `POST` denemesi `404 SKILL_NOT_FOUND` ile
  reddedilir (ayrı bir `410`/`400` kodu icat edilmez) — Sonnet 5 alt-ajanı
  tarafından önerildi, kullanıcı onayı Hard Stop'ta alınacak.
  `merged_into_id`'ye otomatik yönlendirme YAPILMAZ.
- Test stratejisi 70/20/10 — proje varsayılanı.
- DATABASE.md şeması esas alındı (yukarıya bkz.).

## Unknowns
- `skill_claim_history` tablosunun ne zaman ekleneceği (DOMAIN.md §6,
  DATABASE.md'de açık soru olarak işaretli) — bu görevde ele alınmıyor.
- YET-10'un gerçek durumu (Jira "Tamamlandı" ama kod yok) — ayrı bir görev
  gerektirebilir, bu ATDD'nin kapsamı dışı.

## Sorular ve Cevaplar (ham kayıt)
1. Persona → Talent. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
2. Ana hedef → beyan zincirinin ilk halkası. (Sonnet 5 low alt-ajanı
   tarafından yanıtlandı.)
3. Happy path → POST → GET → DELETE. (Sonnet 5 low alt-ajanı tarafından
   yanıtlandı: API.md §2.2 sözleşmesinden birebir.)
4. Edge case'ler → 404 SKILL_NOT_FOUND, 409 ALREADY_CLAIMED,
   MERGED/DEPRECATED reddi, claim edilmemiş skill'e DELETE, başka talent'ın
   claim'i. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
5. Davranış sözleşmesi → yukarıdaki tablo. (Sonnet 5 low alt-ajanı
   tarafından dolduruldu.)
6. Başarı ölçütü → coverage %85, p95 <200ms. (Sonnet 5 low alt-ajanı
   tarafından yanıtlandı.)
7. Kapsam dışı → skill arama, signals, skill_claim_history, level
   güncelleme. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
8. Bağımlılıklar → authorization.py, TalentProfile, Skill modeli. (Sonnet 5
   low alt-ajanı tarafından yanıtlandı.)
9. Güvenlik kısıtı → skill_id doğrulama, MERGED/DEPRECATED reddi. (Sonnet 5
   low alt-ajanı tarafından yanıtlandı — bu bölüm ayrıca `threat-model`
   skill'i tarafından derinleştirilecek.)
10. Rollback → mutasyon öncesi tüm kontroller tamamlanmalı. (Sonnet 5 low
    alt-ajanı tarafından yanıtlandı.)
11. Kabul kriteri sahibi → otomatik test. (Sonnet 5 low alt-ajanı
    tarafından yanıtlandı.)
12. Test stratejisi → 70/20/10. (Sonnet 5 low alt-ajanı tarafından
    yanıtlandı.)
13. Riskler/varsayımlar → DOMAIN.md/DATABASE.md tutarsızlığı, YET-10
    kapsam şüphesi, MERGED/DEPRECATED kararı. (Sonnet 5 low alt-ajanı
    tarafından yanıtlandı.)
