---
task_slug: yet-7-user-talent-profili
jira_id: YET-7
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
  - backend/app/api/me.py (yeni, veya mevcut bir router dosyasına eklenir — plan aşamasında karar verilecek)
  - backend/app/services/talent.py (yeni)
  - backend/app/services/authorization.py (mevcut — scoped_talent_profiles() olası düzeltme, bkz. Unknowns)
  - backend/app/models/identity.py (mevcut — TalentProfile zaten var, DEĞİŞTİRİLMEZ)
---

# ATDD — yet-7-user-talent-profili

## Jira Kaynağı
[YET-7 — [PLAN 1.7] User + Talent profili: GET /me, PATCH /talents/me](https://kuyusuzyusuf123.atlassian.net/browse/YET-7)
User Story (Jira'dan): "As a talent I want to view and update my own profile
So that my information stays accurate without needing anyone else's help"
Jira bağımlılığı: YET-2 (can()/scoped_*()) tamamlanmadan bu uçlar yazılamaz
— YET-2 zaten Tamamlandı, engel yok.

## Persona
Talent/öğrenci kullanıcı — kendi profilini görüntüleyen ve düzenleyen.

## Hedef (Neden)
Kayıt sırasında (register akışı, YET-4) otomatik açılan boş `TalentProfile`
satırını kullanıcının kendi kontrolünde doldurup görünürlüğünü ayarlayabilmesi
— "beyan → kanıt → tanıklık → doğrulanmış deneyim" zincirinin ilk halkası
(beyan) için veri girişini mümkün kılmak.

## User Story
As a talent
I want kendi profilimi görüntüleyip güncelleyebilmek
So that bilgilerim doğru kalsın, başka birinin yardımına ihtiyaç duymadan

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given kimliği doğrulanmış bir kullanıcı, When `GET /me` çağrılır,
   Then `200` + `{user, talent_profile, organizations[], institutions[]}`
   döner (`organizations[]`/`institutions[]` `Principal.org_ids`/
   `institution_ids`'e karşılık gelen gerçek kayıtlardan türetilir).
2. [Critical] Given kimliği doğrulanmamış istek, When `GET /me` çağrılır,
   Then `401` döner.
3. [Critical] Given kendi talent profiline sahip bir kullanıcı, When
   `PATCH /talents/me` ile `{headline, city}` gibi bir/birkaç geçerli alan
   gönderilir, Then `200` + güncel `talent_profile` döner, yalnız gönderilen
   alanlar değişir.
4. [Critical] Given `public_slug` başka bir profilde zaten kullanılıyor,
   When `PATCH /talents/me` bu slug ile çağrılır, Then `409 SLUG_TAKEN`
   döner ve **hiçbir alan güncellenmez** (atomiklik).
5. [Critical] Given `study_year` 1-8 aralığı dışında bir değer (ör. `0`, `9`)
   veya `visibility` geçerli enum dışı bir değer, When `PATCH /talents/me`
   çağrılır, Then `422` döner ve **hiçbir alan güncellenmez**.
6. [High] Given body'de `institution_id` gönderilir (API sözleşmesinde
   parametre olarak yok), When `PATCH /talents/me` çağrılır, Then bu alan
   sessizce yok sayılır, diğer geçerli alanlar (varsa) güncellenir,
   `institution_id` değişmez.
7. [Medium] Given boş body `{}`, When `PATCH /talents/me` çağrılır, Then
   `200` döner, hiçbir alan değişmez (mevcut profil aynen döner) — bu bir
   hata değildir.
8. [High] Given bir kullanıcının `Principal.kind`'ı `"TALENT"` değil ama
   `talent_id`'si dolu (ör. aynı zamanda kurum koordinatörü/admin'i), When
   `PATCH /talents/me` çağrılır, Then yine de `200` ile kendi profilini
   güncelleyebilmelidir — `kind` yalnızca gösterim amaçlı en-yüksek-rol
   etiketidir, yetkilendirme kararı `talent_id`'nin varlığına dayanmalıdır
   (bkz. Unknowns — mevcut `scoped_talent_profiles()` bunu şu an
   **sağlamıyor**, bu AC bilinçli olarak mevcut bir gerçek boşluğu
   kapatmayı hedefliyor).
9. [Critical] AC-S1: `GET /me` çağrısı, query/body/header'da başka bir
   `user_id`/`talent_id` gönderilse bile (istemciden gelen kimliğe
   güvenilmez), yalnızca çağıranın (JWT/session'dan çözülen) kendi verisini
   döner — dönen `organizations[]`/`institutions[]` her zaman
   `Principal.org_ids`/`institution_ids`'den türetilir, hiçbir zaman
   istemciden gelen bir filtre parametresinden değil.
10. [Critical] AC-S2: `PATCH /talents/me` body'sinde `user_id`, `id`,
    `talent_profile_id` veya `institution_id` gibi hedef-belirleyici alanlar
    gönderilse bile, güncellenecek satır **her zaman** sunucuda
    `principal.talent_id`'den çözülür — client'ın gönderdiği herhangi bir
    ID asla sorguya girmez (IDOR yüzeyi yapısal olarak yok, çünkü URL'de de
    id parametresi yok — bu AC bunun bilinçli olarak korunduğunu doğrular).
11. [High] AC-S3: `409 SLUG_TAKEN` yanıtı, çakışan slug'ın **hangi
    kullanıcıya/profile ait olduğuna dair hiçbir bilgi içermez** (yanıt
    gövdesinde yalnızca `{"detail": "SLUG_TAKEN"}`, başka bir kullanıcının
    `id`/`full_name`/`email`'i asla dönmez) — aksi halde saldırgan slug
    deneyerek başka kullanıcıların varlığını/kimliğini keşfedebilir.

## Threat Model
Çağrıldı — STRIDE-lite uygulandı, AC-S1..AC-S3 kriterleri yukarıdaki
Acceptance Criteria listesine eklendi.

**Varlıklar ve sınırlar:** `User`/`TalentProfile` kişisel verisi (KVKK
kapsamında), tarayıcı→API güven sınırı. Kiracı sınırı bu görevde yok (kendi
verisi, çok kiracılı bir kaynak değil) — AC-8/scoped_talent_profiles konusu
kiracı değil rol-etiketleme sorunu.

**STRIDE-lite:**
- **Spoofing** — mevcut `AUTH` middleware'i (JWT/cookie) kapsıyor, bu
  görevde yeni bir kimlik doğrulama mekanizması yok → atlandı.
- **Tampering** — İstemciden gelen `user_id`/`talent_id`/`institution_id`
  gibi hedef-belirleyici veya sahiplik alanlarına güvenilmemesi gerekiyor
  → AC-S1, AC-S2 (AC-6 ile de örtüşüyor — `institution_id` zaten yok
  sayılıyordu, AC-S2 bunu genel bir "hiçbir hedef-ID alanına güvenme"
  kuralına genişletiyor).
- **Repudiation** — Kullanıcının **kendi** profilini düzenlemesi, başka bir
  kullanıcıyı etkilemeyen düşük-hassasiyetli bir self-servis işlemi;
  `institutions.py`/`organizations.py`'deki admin eylemlerinin aksine
  (başkasını davet etme, kurum oluşturma) burada audit_events'e loglama
  **zorunlu tutulmadı** — kabul edilen kapsam dışı, gerekçe: kullanıcı
  kendi verisini değiştiriyor, üçüncü bir tarafı etkilemiyor.
- **Info disclosure** — `409` yanıtının başka kullanıcı bilgisi
  sızdırmaması → AC-S3. `GET /me`'nin yalnızca kendi verisini dönmesi
  → AC-S1.
- **DoS** — Bu uçlar (basit CRUD, dış ağ çağrısı yok) rate-limit
  gerektirmiyor — `verify-domain` (YET-9) gibi DNS/dış sorgu tetiklemiyor,
  amplifikasyon riski yok. Kabul edilen kapsam dışı.
- **Elevation** — Yetkinin sunucuda (`principal.talent_id`, URL'de id
  parametresi olmadan) kontrol edilmesi → AC-S2. AC-8 (kind≠TALENT
  durumunda da kendi profiline erişebilme) bu kategoriyle ilişkili ama
  ayrı bir gerçek kod boşluğu (`scoped_talent_profiles`) — `authz-test`
  skill'i bu düzeltmeyi doğrulamalı.

**Kabul edilen risk:** Repudiation (audit logging yok) ve DoS (rate-limit
yok) bilinçli olarak kapsam dışı bırakıldı — gerekçe yukarıda, düşük
hassasiyetli self-servis CRUD işlemi.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — `GET /me` | `200` + `{user, talent_profile, organizations[], institutions[]}` | Yok (salt okuma) | Profil özeti | AC-1 |
| 2 | Kimliği doğrulanmamış `GET /me` | `401` | Yok | "Kimlik doğrulaması gerekli" | AC-2 |
| 3 | Happy path — `PATCH /talents/me` (tek/birkaç geçerli alan) | `200` + güncel `talent_profile` | `talent_profiles` UPDATE (yalnız gönderilen alanlar, `updated_at` ilerler) — **tek transaction, `session.commit()` fonksiyon sonunda, hata yolunda hiçbir yazı flush edilmeden önce reddedilmeli** (bkz. postmortem koşum 1 — bu proje `get_session`'ı her exception'da rollback yapıyor, ama validasyon hatası zaten DB'ye dokunmadan önce (Pydantic/servis girişinde) yakalanmalı, "flush sonra rollback" deseni bu uçta hiç kurulmamalı) | Güncel profil | AC-3 |
| 4 | `public_slug` çakışması | `409 SLUG_TAKEN` | Yok — DB'ye hiçbir yazma yapılmadan önce (unique constraint'e güvenmeden, önce `SELECT` ile) kontrol edilir | `{"detail": "SLUG_TAKEN"}` | AC-4 |
| 5 | Girdi geçersiz (`study_year` aralık dışı, `visibility` geçersiz enum) | `422` (Pydantic validation) | Yok | Alan bazlı hata mesajı | AC-5 |
| 6 | `institution_id` body'de gönderilirse | `200` (yok sayılır) | Diğer geçerli alanlar güncellenir, `institution_id` değişmez | Güncel profil, `institution_id` eskisiyle aynı | AC-6 |
| 7 | Boş body `{}` | `200` | Yok, hiçbir alan değişmez | Mevcut profil aynen döner | AC-7 |
| 8 | `talent_id` dolu ama `kind != "TALENT"` | `200` (kendi profilini yine güncelleyebilir) | Aynı — yalnız gönderilen alanlar | Güncel profil | AC-8 |
| 9 | `GET /me`'ye query/body'de başka bir `user_id` gönderilir | `200` (parametre yok sayılır) | Yok | Yine çağıranın KENDİ verisi (gönderilen `user_id` hiç etkilemez) | AC-S1 |
| 10 | `PATCH /talents/me` body'sinde `user_id`/`id`/`talent_profile_id` gönderilir | `200` (yok sayılır, hedef yine `principal.talent_id`) | Yok — başka bir kullanıcının satırı asla etkilenmez | Kendi profili güncellenir | AC-S2 |
| 11 | `public_slug` çakışması — yanıt içeriği | `409 SLUG_TAKEN` | Yok | Yalnız `{"detail":"SLUG_TAKEN"}` — çakışan profilin sahibi/id'si asla dönmez | AC-S3 |

Kısmi başarı: Birden fazla alan gönderilip biri geçersizse (ör. `study_year`
geçersiz, `city` geçerli) **tamamı reddedilir** — `422`, hiçbir alan
(geçerli olan dahil) yazılmaz. Kısmi kayıt YASAK (atomiklik).

Hiçbir şey yapılamadı ama hata da yok: Boş body `{}` — bu bir hata değil,
`200` + değişmemiş profil döner (satır 7). Sessiz başarı riski burada YOK
çünkü hiçbir yazma iddiası da yok — dönen veri zaten "değişmedi"yi doğru
yansıtıyor.

Boş sonuç ↔ hata ayrımı: `GET /me` her zaman `200` döner (kimlik doğrulanmış
her kullanıcının bir `talent_profile`'ı vardır, register akışı garanti eder)
— "profil yok" durumu bu ATDD kapsamında **tanımsız/oluşmaz** (register
invariant'ı). Eğer bir gün bu invariant bozulursa (ör. eski veri), bu durum
kapsam dışıdır ve ayrı bir veri-migrasyonu sorunu olarak ele alınmalı.

## Test Strategy
Unit: 70% — validasyon kuralları (study_year aralığı, visibility enum,
slug çakışma kontrolü, institution_id yok sayma mantığı), servis katmanı.
Integration: 20% — endpoint + DB + yetkilendirme (`scoped_talent_profiles`)
akışı.
E2E: 10% — `GET /me` → `PATCH /talents/me` → tekrar `GET /me` tam akışı.

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: p95 <200ms (basit CRUD, dış ağ/AI/S3 çağrısı yok).
Memory: Belirtilmedi.
Görsel/UI kriteri: Yok — bu görev yalnız backend API, frontend kapsamı
PLAN 1.14'te ayrı.
Diğer ölçülebilir kriterler: —

## Kapsam Dışı
- `GET /talents/{id}` (başkasının profilini görüntüleme, visibility budaması)
  — ayrı PLAN maddesi değil ama API.md §2.2'de listeli, bu görevde YOK.
- `GET/POST/DELETE /talents/me/skills` — PLAN 1.11.
- `GET /talents/me/signals` — Faz 2 (Attestation/SkillSignal üretimi henüz yok).
- Frontend ekranları (PLAN 1.14).
- `institution_id`'nin değiştirilmesi — yalnız YET-8'in `InstitutionLinkRequest`
  onay akışıyla değişir, bu uçta salt-okunur.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/api/me.py` veya benzeri (yeni router — `plan` adımında kesin
  dosya adı/yeri netleşecek, muhtemelen `/me` ve `/talents/me` farklı
  prefix'ler gerektirdiği için tek router'da iki farklı prefix veya iki
  router).
- `backend/app/services/talent.py` (yeni — `get_me`, `update_talent_profile`).
- `backend/app/services/authorization.py` (mevcut `scoped_talent_profiles()`
  — AC-8 gereği koşulunun `principal.kind == "TALENT"` yerine
  `principal.talent_id is not None` olarak değişmesi gerekebilir — bu
  **yetkilendirme mantığı değişikliği**, CLAUDE.md gereği ayrı açık onay
  gerektirir, `plan`/`code-copilot` aşamasında kullanıcıya sorulacak).
- `backend/app/models/identity.py` (mevcut `TalentProfile`, `User` —
  DEĞİŞTİRİLMEZ).

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulandı (YET-9'da) — git reposu kökü proje klasörüyle (`yetkin360`)
aynı, devasa/ilgisiz bir geçmiş taşımıyor. Yine de arama `backend/`/proje
klasörüyle sınırlı tutulmalı.

## Rollback Beklentisi
`409`/`422` durumlarında hiçbir alan güncellenmemeli (atomiklik) — servis
fonksiyonu validasyonu **DB'ye herhangi bir `flush`/`add` yapmadan önce**
tamamlamalı, postmortem koşum 1'in "flush sonra rollback" tuzağına
düşülmemeli.

## Risks
- `scoped_talent_profiles()`'ın mevcut `kind == "TALENT"` koşulu, aynı
  zamanda kurum/organizasyon admin'i olan kullanıcıların kendi talent
  profillerine PATCH atamasını engelliyor olabilir — bu AC-8 ile bilinçli
  olarak ele alınıyor, ama düzeltme yetkilendirme dosyasında olacağı için
  ayrı onay gerektirir (bkz. Etkilenen Dosyalar). AC-8/AC-S2'nin doğru
  implemente edildiği `plan`/`test-copilot` aşamasında `authz-test`
  skill'i çağrılarak ayrıca doğrulanmalı (yetkilendirme mantığı değişikliği).
- `public_slug` unique constraint'e güvenip DB `IntegrityError`'ını
  yakalamak yerine önce `SELECT` ile kontrol etmek race condition'a açık
  olabilir (iki eşzamanlı istek aynı slug'ı seçerse) — DB'deki unique
  constraint zaten son çare koruması, kabul edilebilir risk (MVP kapsamı).

## Assumptions
- DOMAIN.md'nin "is_public = true ise public_slug zorunlu" ifadesi eski/
  yanlış — gerçek şemada `is_public` alanı yok, `visibility` enum'u var.
  **Varsayım:** gerçek kural "visibility=PUBLIC ise public_slug zorunlu"
  olmalı — bu, `code-copilot` aşamasında implemente edilecek ama şema/
  DOMAIN.md güncellemesi bu görevin kapsamı dışı (ayrı dokümantasyon görevi).
- Test stratejisi 70/20/10 — Sonnet 5 alt-ajanı tarafından proje varsayılanı
  olarak önerildi (YET-9'da da kullanıldı).

## Unknowns
- `scoped_talent_profiles()`'ın `kind == "TALENT"` koşulunun
  `talent_id is not None` olarak değiştirilip değiştirilmeyeceği — AC-8 bu
  ihtiyacı işaretliyor ama gerçek kod değişikliği kullanıcı onayı bekliyor
  (yetkilendirme mantığı değişikliği).
- `visibility=PUBLIC` ile `public_slug` zorunluluğu arasındaki ilişkinin
  kesin iş kuralı (yukarıdaki Assumptions'a bkz.) — DOMAIN.md güncel değil.

## Sorular ve Cevaplar (ham kayıt)
1. Persona → Talent/öğrenci kullanıcı, kendi profili. (Sonnet 5 low
   alt-ajanı tarafından yanıtlandı: `scoped_talent_profiles` zaten
   "sadece kendi profilin" için tasarlanmış.)
2. Ana hedef → beyan zincirinin ilk halkasının veri girişi. (Sonnet 5 low
   alt-ajanı tarafından yanıtlandı.)
3. Happy path → GET /me sonra PATCH /talents/me. (Sonnet 5 low alt-ajanı
   tarafından yanıtlandı: API.md §2.2 sözleşmesinden birebir.)
4. Edge case'ler → slug çakışması, geçersiz study_year, institution_id yok
   sayma, kind≠TALENT durumu. (Sonnet 5 low alt-ajanı tarafından
   yanıtlandı; kind≠TALENT durumu ayrıca orkestratör tarafından gerçek
   kodda (`app/api/deps.py`) doğrulanarak netleştirildi — `talent_id`
   `kind`'dan bağımsız hesaplanıyor.)
5. Davranış sözleşmesi → yukarıdaki tablo. (Sonnet 5 low alt-ajanı
   tarafından dolduruldu, kısmi başarı/rollback notu postmortem koşum
   1'e göre orkestratör tarafından netleştirildi.)
6. Başarı ölçütü → coverage %85, p95 <200ms. (Sonnet 5 low alt-ajanı
   tarafından yanıtlandı.)
7. Kapsam dışı → GET /talents/{id}, skills, signals, frontend. (Sonnet 5
   low alt-ajanı tarafından yanıtlandı: PLAN.md madde numaralarına göre.)
8. Bağımlılıklar → auth/register, authorization.py, institutions/
   InstitutionLinkRequest. (Sonnet 5 low alt-ajanı tarafından yanıtlandı.)
9. Güvenlik kısıtı → public_slug enumeration riski düşük (tasarım gereği
   public). (Sonnet 5 low alt-ajanı tarafından yanıtlandı — bu bölüm
   ayrıca `threat-model` skill'i tarafından derinleştirilecek.)
10. Rollback → 409/422'de atomiklik zorunlu. (Sonnet 5 low alt-ajanı
    tarafından yanıtlandı.)
11. Kabul kriteri sahibi → otomatik test. (Sonnet 5 low alt-ajanı
    tarafından yanıtlandı.)
12. Test stratejisi → 70/20/10. (Sonnet 5 low alt-ajanı tarafından
    yanıtlandı.)
13. Riskler/varsayımlar → DOMAIN.md is_public tutarsızlığı, kind≠TALENT
    sorunu. (Sonnet 5 low alt-ajanı tarafından yanıtlandı, ikincisi
    orkestratör tarafından gerçek kodla doğrulandı.)
