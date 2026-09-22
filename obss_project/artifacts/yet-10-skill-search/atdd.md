---
task_slug: yet-10-skill-search
jira_id: YET-10
saga_task_id: null
threat_model: done
priority: high
coverage_target: 85
performance_target: "p95 <200ms (basit ILIKE araması, ~150 satırlık tablo)"
memory_target: null
test_strategy:
  unit: 70
  integration: 20
  e2e: 10
affected_modules:
  - backend/app/api/skills.py (yeni)
  - backend/app/services/skill.py (yeni)
  - backend/scripts/seed.py (yeni)
  - backend/app/models/skill.py (mevcut, salt okunur, DEĞİŞTİRİLMEZ)
---

# ATDD — yet-10-skill-search

## Jira Kaynağı
[YET-10 — [PLAN 1.10] Skill taksonomisi (~150 skill) seed + arama ucu](https://kuyusuzyusuf123.atlassian.net/browse/YET-10)
User Story (Jira'dan): "As any user declaring or searching skills I want a
consistent ~150-item skill taxonomy with a search endpoint So that
competency claims are comparable across the platform instead of free-text
noise."
Jira bağımlılığı: YET-1 (migration), YET-2 (yetkilendirme) — ikisi de
Tamamlandı, engel yok.

**Bağlam (bu görevin neden şimdi açıldığı):** YET-10, Jira'da "Tamamlandı"
işaretliydi ama kod tabanında hiçbir `GET /skills` ucu/seed script'i
bulunamadı — bu, YET-11 (skill claims) ve YET-14'ün (frontend skill-arama
ekranı, zaten `GET /skills?q=...` çağırıyor) ATDD'lerinde ayrı ayrı not
düşülmüştü. YET-14'ün gerçek entegrasyonu incelenirken bu boşluk somut
olarak doğrulandı: frontend var olmayan bir ucu çağırıyor, testler bunu
mock'ladığı için hiç yakalanmamıştı. Bu görev o boşluğu kapatıyor.

## Persona
Herhangi bir kimliği doğrulanmış kullanıcı (talent, kurum/organizasyon
admini) — skill taksonomisinde arama yapan.

## Hedef (Neden)
Serbest metin yetkinlik beyanı yerine kontrollü bir taksonomiden seçim
yaparak "beyan" adımının karşılaştırılabilir/aranabilir olmasını sağlamak
— DOMAIN.md §3.5: "Serbest metin skill'e MVP'de bile izin verilmez."

## User Story
As kimliği doğrulanmış herhangi bir kullanıcı
I want skill taksonomisinde isim/kategoriye göre arama yapabilmek
So that yetkinlik beyanımı standart bir taksonomiden seçebileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given kimliği doğrulanmış bir kullanıcı, When
   `GET /skills?q=python` çağrılır, Then `200` + `{items: [{id, slug,
   name_tr, name_en, category, parent_id}, ...]}` döner — `q`, `name_tr` +
   `name_en` + `slug` üzerinde arama yapar, yalnız `status='ACTIVE'`
   skill'ler döner.
2. [Critical] Given `q` verilmemiş, When `GET /skills` çağrılır, Then `200`
   + ilk `limit` (varsayılan **50**) ACTIVE skill döner (hata değil).
3. [High] Given `q` ile eşleşen hiçbir skill yok, When çağrılır, Then `200`
   + `{items: []}` döner (bu bir arama sonucu, kaynak yokluğu değil — `404`
   DEĞİL).
4. [High] Given `category` filtresi (`LANGUAGE|FRAMEWORK|TOOL|DOMAIN|SOFT`),
   When `GET /skills?category=LANGUAGE` çağrılır, Then `200` + yalnız o
   kategorideki ACTIVE skill'ler döner.
5. [Critical] Given `category` geçersiz bir enum değeri, When çağrılır,
   Then `422` döner (Pydantic enum validasyonu).
6. [High] Given `limit` sunucu üst sınırını (100) aşan bir değer, When
   çağrılır, Then `422` döner.
7. [Critical] Given bir skill `status='MERGED'` veya `'DEPRECATED'`, When
   herhangi bir arama yapılır, Then bu skill sonuçlarda **asla** görünmez
   (sorgu her zaman `status='ACTIVE'` filtreler).
8. [Critical] Given kimliksiz bir istek, When `GET /skills` çağrılır, Then
   `401` döner.
9. [High] Given seed script'i (`python -m scripts.seed`) çalıştırılır,
   Then veritabanına temsili bir skill seti eklenir (bkz. Assumptions —
   tam "~150" sayısı yerine MVP'de temsili bir alt küme).
10. [High] AC-S1: Given herhangi bir arama sonucu, When yanıt gövdesi
    incelenir, Then `status`/`merged_into_id` gibi Skill modelinin iç/
    yönetimsel alanları **asla** dönmez — yanıt yalnızca ayrı bir Pydantic
    response şemasındaki alanları (`id, slug, name_tr, name_en, category,
    parent_id`) içerir, ORM modeli doğrudan serialize edilmez.
11. [Critical] AC-S2: Given `q` parametresine SQL meta-karakterleri içeren
    bir girdi (`"'; DROP TABLE skills; --"`, `"' OR '1'='1"`), When
    `GET /skills?q=...` çağrılır, Then `200` + normal bir arama sonucu
    (muhtemelen boş liste) döner — DB sorgusu SQLAlchemy ORM üzerinden
    parametreli çalıştığı için hiçbir tablo etkilenmez, hata fırlatılmaz.

## Threat Model
Çağrıldı — STRIDE-lite uygulandı, AC-S1..AC-S2 kriterleri yukarıdaki
Acceptance Criteria listesine eklendi.

**Varlıklar ve sınırlar:** `Skill` platform-geneli, düşük-hassasiyetli bir
kaynak (kullanıcıya/kiracıya özel değil, gizli bilgi taşımıyor). Tarayıcı→API
güven sınırı var, kiracı→kiracı sınırı YOK (bu kaynak zaten herkese açık
bir taksonomi).

**STRIDE-lite:**
- **Spoofing** — mevcut `AUTH` middleware'i kapsıyor → atlandı.
- **Tampering** — Salt-okunur uç, hiçbir mutasyon/sahiplik alanı yok →
  atlandı (değiştirilecek bir şey yok).
- **Repudiation** — Salt-okunur arama, hiçbir kullanıcıyı etkilemeyen
  düşük-hassasiyetli bir işlem — audit logging **kabul edilen kapsam dışı**
  (YET-7/YET-11'deki aynı gerekçe: self-servis/etkisiz okuma işlemi).
- **Info disclosure** — Yanıtın Skill modelinin iç alanlarını (`status`,
  `merged_into_id`) sızdırmaması → AC-S1. MERGED/DEPRECATED skill'lerin
  hiç görünmemesi zaten AC-7 ile karşılanıyor (bu da bir info-disclosure
  kontrolü).
- **DoS** — `limit` üst sınırı (100, AC-6) zaten sınırsız sonuç dönmeyi
  engelliyor. `q`'nun karmaşık bir `ILIKE` deseni olması ~150 satırlık
  tabloda önemsiz bir maliyet — ek bir AC gerektirmiyor, **kabul edilen
  kapsam dışı**.
- **Elevation** — Bu uçta bir yetki yükseltme yüzeyi yok (platform-geneli
  okuma, admin/sahiplik eylemi değil) → atlandı.

**SQL injection notu:** SQLAlchemy ORM (`select(Skill).where(...)`)
kullanıldığı sürece parametreli sorgu garanti — AC-S2 bunun gerçekten
doğru kullanıldığını (ham SQL string birleştirme YOK) doğrulayan bir test
üretir.

**Kabul edilen risk:** Repudiation (audit logging yok) ve karmaşık `q`
deseninin DoS potansiyeli bilinçli olarak kapsam dışı bırakıldı — düşük
hassasiyetli, küçük veri setli (~150 satır) bir okuma ucu.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — `q` ile arama, sonuç bulunur | `200` + `{items:[...]}` | Yok (salt okuma) | Eşleşen ACTIVE skill listesi | AC-1 |
| 2 | `q` verilmemiş | `200` + `{items:[...]}` ilk `limit` (varsayılan 50) ACTIVE skill | Yok | İlk N skill | AC-2 |
| 3 | `q` ile hiç sonuç bulunamaz | `200` + `{items: []}` | Yok | Boş liste (`404` DEĞİL) | AC-3 |
| 4 | `category` filtresi ile arama | `200` + filtrelenmiş liste | Yok | O kategorideki skill'ler | AC-4 |
| 5 | `category` geçersiz enum | `422` + `{code:"VALIDATION_ERROR",...}` | Yok | Doğrulama hatası | AC-5 |
| 6 | `limit` üst sınırı (100) aşılırsa | `422` + `{code:"VALIDATION_ERROR",...}` | Yok | Doğrulama hatası | AC-6 |
| 7 | MERGED/DEPRECATED skill'ler | Asla dönmez | Yok | Listede hiç görünmez | AC-7 |
| 8 | Kimliksiz istek | `401` | Yok | Kimlik doğrulama hatası | AC-8 |
| 9 | Yanıt gövdesi iç alan sızıntısı kontrolü | Yanıt yalnız `id/slug/name_tr/name_en/category/parent_id` içerir | Yok | `status`/`merged_into_id` asla görünmez | AC-S1 |
| 10 | `q`'da SQL meta-karakterleri | `200` + normal/boş sonuç, DB'ye zarar yok | Yok | Aranan skill(ler) veya boş liste | AC-S2 |

Kısmi başarı: Bu uç tek bir `SELECT` sorgusuna karşılık gelen atomic bir
işlem — "kısmi başarı" durumu yapısal olarak oluşmaz (DB'ye hiç yazma yok).

Hiçbir şey yapılamadı ama hata da yok: `{items: []}` (satır 3) — bu bir
hata değil, aramanın gerçek sonucu. Sessiz başarı riski yok çünkü zaten
hiçbir "başarı" iddiası (yazma/mutasyon) yok, yalnız okuma sonucu dönüyor.

Boş sonuç ↔ hata ayrımı: `{items: []}` (arama sonucu yok) ile `401`/`422`
(hata) açıkça farklı durum kodlarıyla ayrışıyor — karışma riski yok.

## Test Strategy
Unit: 70% — arama filtreleme mantığı (q/category/limit kombinasyonları),
ACTIVE-dışı skill'lerin hariç tutulması, limit üst sınırı.
Integration: 20% — endpoint + DB + AUTH dependency akışı.
E2E: 10% — gerçek bir arama senaryosu (seed edilmiş birkaç skill ile).

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: p95 <200ms — ~150 satırlık tabloda `ILIKE`/`CITEXT`
araması trivial, ek index gerekmiyor (not: `name_tr`/`name_en` şu an
index'siz, veri büyürse trigram index düşünülebilir — bu görevin kapsamı
dışı).
Memory: Belirtilmedi.
Görsel/UI kriteri: Yok — frontend zaten var (YET-14), bu görev yalnız
backend, frontend'e DOKUNULMAYACAK.
Diğer ölçülebilir kriterler: `limit` sunucu üst sınırı: 100.

## Kapsam Dışı
- Serbest metin skill önerisi / admin onay akışı (PLAN 3.6, `is_curated`).
- Skill hiyerarşisi/parent-child gezinme ucu (bu görevde yalnız düz liste,
  `parent_id` response'ta dönüyor ama ayrı bir gezinme ucu yok).
- Frontend değişikliği — `frontend/lib/api/client.ts`'deki `listSkills()`
  zaten doğru sözleşmeye göre yazılmış, dokunulmayacak.
- Rollback/atomiklik — salt-okunur uç, DB'ye hiç yazmıyor.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/api/skills.py` (yeni router — `GET /skills`).
- `backend/app/services/skill.py` (yeni — `search_skills(session, q,
  category, limit)`, merkezi filtreli sorgu — `plan` aşamasında "çıplak
  select() yasağı" ile ilişkisi netleştirilecek, bkz. Unknowns).
- `backend/scripts/seed.py` (yeni — `python -m scripts.seed`, temsili
  skill seti, production'da çalıştırılmaz).
- `backend/app/models/skill.py` (mevcut `Skill`, salt okunur).

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulandı (önceki görevlerde) — git reposu kökü proje klasörüyle aynı.
Arama `backend/`/proje klasörüyle sınırlı tutulmalı.

## Rollback Beklentisi
Geçerli değil — bu uç salt-okunur, DB'ye hiçbir yazma yapmıyor. Seed
script'i ayrı bir CLI aracı, testlerin kapsamı dışında (testler kendi
fixture'larını kurar).

## Risks
- **Skill kaynağının "kiracı-özel olmayan" doğası ile CLAUDE.md'nin
  "çıplak select(Model) yasak" kuralı arasındaki ilişki netleşmeli** —
  `Skill` platform-geneli bir kaynak (kullanıcıya/kiracıya özel değil),
  mevcut `scoped_*()` paterni (kiracı izolasyonu için tasarlanmış) burada
  doğrudan uygulanmıyor. Öneri (Sonnet 5 alt-ajanı): yeni bir
  `services/skill.py::search_skills()` fonksiyonu yazılsın, içinde
  `select(Skill).where(Skill.status=='ACTIVE', ...)` kullanılsın — bu,
  "router'da/kontrolsüz çıplak sorgu" değil, servis katmanındaki tek,
  merkezi bir fonksiyon üzerinden geçen filtreli sorgu olduğu için yasağın
  ruhuna aykırı değil. Kullanıcı onayı gerekebilir (bkz. Unknowns).
- Gerçek ~150 skill listesinin kaynağı belirsiz (bkz. Assumptions).

## Assumptions
- **MVP'de tam "~150" skill yerine temsili bir alt küme (~30-50, her
  kategoriden örnek) kabul edilebilir** — hackathon süresi için tam listeyi
  elle yazmak zaman alır, "~150" yaklaşık bir hedef, katı bir sayı
  zorunluluğu değil. **Bu varsayım kullanıcı onayı gerektiriyor** — Hard
  Stop'ta netleştirilecek.
- `q` için minimum karakter uzunluğu KONULMADI — API.md'de böyle bir sınır
  yazmıyor, frontend zaten debounce (≥300ms) ile tetikliyor.
- `limit` varsayılanı 50, üst sınırı 100 — API.md'de sayısal değer
  belirtilmemiş, Sonnet 5 alt-ajanı tarafından makul varsayılan olarak
  önerildi.
- Kimliksiz istek → `401` (404 değil) — bu bir kiracı-izolasyon kaynağı
  değil, genel kimlik doğrulama gereksinimi (CLAUDE.md'nin 404 kuralı
  "kaynağın varlığını gizleme" amaçlı, `/skills` gibi platform-geneli bir
  kaynağın varlığı zaten gizli değil).

## Unknowns
- `search_skills()`'in çıplak `select()` yasağıyla ilişkisi — `plan`
  aşamasında kod keşfiyle netleşecek, gerekirse kullanıcıya sorulacak.
- Gerçek skill listesinin içeriği (hangi ~30-50 skill) — `code-copilot`
  aşamasında, docs/DOMAIN.md §3.5'in kategori örneklerinden (LANGUAGE:
  Python/JavaScript/Java..., FRAMEWORK: FastAPI/React/Django..., vb.)
  türetilecek, kullanıcı Hard Stop'ta itiraz edebilir.

## Sorular ve Cevaplar (ham kayıt)
1. Persona → herhangi bir kimliği doğrulanmış kullanıcı. (Sonnet 5 low
   alt-ajanı tarafından yanıtlandı: API.md §2.3 yetkisi `AUTH`, role özel
   değil.)
2. Ana hedef → free-text noise'u önlemek. (Sonnet 5 low alt-ajanı
   tarafından yanıtlandı: DOMAIN.md §3.5.)
3. Happy path → `GET /skills?q=python`. (Sonnet 5 low alt-ajanı tarafından
   yanıtlandı: API.md §2.3 sözleşmesinden birebir.)
4. Edge case'ler → q kısa/boş, category geçersiz, limit aşımı,
   MERGED/DEPRECATED gizleme. (Sonnet 5 low alt-ajanı tarafından
   yanıtlandı.)
5. Davranış sözleşmesi → yukarıdaki tablo. (Sonnet 5 low alt-ajanı
   tarafından dolduruldu.)
6. Başarı ölçütü → coverage %85, p95 <200ms. (Sonnet 5 low alt-ajanı
   tarafından yanıtlandı.)
7. Kapsam dışı → admin onay akışı, hiyerarşi gezinme, frontend. (Sonnet 5
   low alt-ajanı tarafından yanıtlandı.)
8. Bağımlılıklar → Skill modeli, AUTH dependency. (Sonnet 5 low alt-ajanı
   tarafından yanıtlandı.)
9. Güvenlik kısıtı → ORM parametreli sorgu (injection riski yok), limit
   üst sınırı. (Sonnet 5 low alt-ajanı tarafından yanıtlandı — bu bölüm
   ayrıca `threat-model` skill'i tarafından derinleştirilecek.)
10. Rollback → geçerli değil, salt-okunur. (Sonnet 5 low alt-ajanı
    tarafından yanıtlandı.)
11. Kabul kriteri sahibi → otomatik test. (Sonnet 5 low alt-ajanı
    tarafından yanıtlandı.)
12. Test stratejisi → 70/20/10. (Sonnet 5 low alt-ajanı tarafından
    yanıtlandı.)
13. Riskler/varsayımlar → seed listesi kaynağı, çıplak select() ilişkisi.
    (Sonnet 5 low alt-ajanı tarafından yanıtlandı, kullanıcı onayı
    gerektiği işaretlendi.)
