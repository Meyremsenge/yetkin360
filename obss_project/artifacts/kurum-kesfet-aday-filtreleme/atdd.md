---
task_slug: kurum-kesfet-aday-filtreleme
jira_id: null
saga_task_id: null  # Saga araçları bu oturumda yoktu — task açılamadı
priority: medium
threat_model: done
coverage_target: 85
performance_target: "liste ucu p95 < 300ms (seed ölçeği), < 500ms (1000 öğrenci)"
memory_target: null
test_strategy:
  unit: 30
  integration: 60
  e2e: 10
affected_modules:
  # plan adımında doğrulanacak — yollar tahmini
  - backend/app/api/ (yeni discover router)
  - backend/app/services/ (yeni discover servisi + merkezî yetkilendirmeye yeni scope)
  - backend/tests/authorization/
  - docs/AUTHORIZATION.md (§4 karar matrisi)
  - docs/API.md
  - frontend/src/app/ (Keşfet rotası + menü girişi)
  - frontend sabit metin dosyası (UI metinleri)
  - PLAN.md (R.1)
---

# ATDD — kurum-kesfet-aday-filtreleme

> **GEÇERSİZ (10 Ekim 2026):** Kapsam değişti — yalnız `PUBLIC` profiller, oturum açmış herkes, kimlikli detay ucu yok. Güncel tasarım: `docs/kesfet-tasarim.md`.


## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. `PLAN.md` **R.1** ("Basit aday filtreleme ekranı — skill + kurum filtresi, matching motoru değil") maddesine karşılık gelir.

## Persona
Doğrulanmış bir Organization'ın (staj yeri / işveren) üyesi. Henüz engagement'ı olmayan öğrencileri, beyan ve doğrulanmış yetkinliklerine göre arıyor.

## Hedef (Neden)
Organization'lar bugün engagement'ı olmayan öğrenciyi hiç göremiyor. Keşfet, engagement kurmadan önce öğrencileri kanıta dayalı yetkinlikleriyle bulmayı sağlar. Eşleştirmeyi **insan** yapar; sistem yalnız deterministik filtre sunar (skor, öneri, matching motoru yok — final analiz §9.1, CLAUDE.md kapsam kuralı).

## User Story
As a doğrulanmış Organization üyesi
I want görünürlüğünü kurumlara açmış öğrencileri skill ve üniversiteye göre filtrelemek
So that uygun adayı bulup mevcut engagement davet akışına geçebileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)

1. **AC-1 [Critical]** Given doğrulanmış bir Organization üyesi ve `visibility IN ('ORGANIZATIONS','PUBLIC')` olan öğrenciler, When `GET /discover/talents` çağrılır, Then `200 + {items:[...], next_cursor}` döner; her kartta görünen ad, üniversite/bölüm, skill'ler (doğrulanmış / self-claim ayrımıyla), doğrulanmış deneyim sayısı ve public talent id bulunur.
2. **AC-2 [Critical]** Given `visibility` değeri `PRIVATE` veya `INSTITUTION` olan bir öğrenci, When herhangi bir filtreyle liste çağrılır, Then o öğrenci `items` içinde **hiç** yer almaz.
3. **AC-S1 [Critical]** Given talent rolündeki kullanıcı, hiçbir Organization üyesi olmayan kullanıcı veya doğrulanmamış Organization üyesi, When `GET /discover/talents` ya da `GET /discover/talents/{public_id}` çağrılır, Then `404` döner (403 değil) ve gövdede hiçbir öğrenci alanı bulunmaz. Anonim çağrı `401` döner.
4. **AC-S2 [Critical]** Given yetkili bir çağrı, When liste veya detay yanıtı incelenir, Then gövdede `email`, `phone`, CV, evidence/dosya URL'si, `private_note`, `user_id` ve `PRIVATE` görünürlüklü doğrulanmış deneyimler **yer almaz** (yanıt şeması allowlist; ORM modeli dönülmez).
5. **AC-S3 [Critical]** Given listede görünen bir öğrenci sonradan `visibility`'yi `PRIVATE`/`INSTITUTION` yapar, When `GET /discover/talents/{public_id}` çağrılır, Then `404` döner ve bu yanıt, var olmayan bir id için dönen yanıtla **bayt düzeyinde aynıdır** (varlık sızmaz).
6. **AC-S4 [Critical]** Given yetkili üye, When isteğe `organization_id`, `visibility=PRIVATE`, `role` gibi istemci kaynaklı yetki/kapsam parametresi eklenir, Then `422` döner (`extra=forbid`); kapsam yalnız oturumdaki üyelikten türetilir, istemci girdisinden değil.
7. **AC-3 [High]** Given `skill_id` (çoklu), `institution_id`, `verified_only` filtreleri, When birden fazla `skill_id` verilir, Then yalnız **tümüne** sahip öğrenciler döner; `verified_only=true` ise yalnız doğrulanmış sinyali olan skill'ler eşleşir.
8. **AC-4 [High]** Given aynı filtre, When istek tekrarlanır, Then sıra deterministiktir: `created_at DESC, id` — skor/puan alanı yanıtta yoktur.
9. **AC-5 [High]** Given filtreye uyan öğrenci yok ya da var olmayan (geçerli biçimli) `skill_id`/`institution_id`, When liste çağrılır, Then `200 + {items:[], next_cursor:null}` döner (kaydın varlığı sızmasın diye 404 değil) ve arayüz boş durum metnini gösterir.
10. **AC-6 [High]** Given bozuk UUID, `limit > 50` veya bilinmeyen sorgu parametresi, When liste çağrılır, Then `422` döner ve arayüz "Filtre geçersiz" hatasını gösterir.
11. **AC-S5 [High]** Given `skill_id=' OR 1=1--` veya `institution_id=../..` gibi girdi, When liste çağrılır, Then `422` döner, sorgu parametreli çalışır, yanıtta hiçbir öğrenci kaydı bulunmaz.
12. **AC-S6 [High]** Given yetkili üye, When sayfalama ile derine gidilir, Then sayfa en fazla 50 kayıt döner, toplam erişilebilir derinlik 200 kayıtla sınırlıdır ve sınır sonrası `next_cursor: null` olur (toplu kazıma sınırı).
13. **AC-S7 [High]** Given Organization doğrulaması geri alınır ya da kullanıcının üyeliği kaldırılır, When aynı oturumla liste çağrılır, Then `404` döner (yetki her istekte sunucuda yeniden değerlendirilir; yalnız menüyü gizlemek yeterli değildir).
14. **AC-7 [High]** Given bir kart, When tıklanır, Then keşfet-görünümlü profil detayı (`GET /discover/talents/{id}`, `id` = `talent_profiles.id`) açılır. Davet / çalışma başlatma düğmesi **yoktur** — kurum tarafı davet arayüzü mevcut değil, kapsam dışı (plan.md Karar 1).
15. **AC-S8 [Medium]** Given profil detayı görüntüleme, When istek başarıyla tamamlanır, Then `audit_events`'e kim / hangi organization / hangi profil yazılır; PII yazılmaz. Liste araması audit'e yazılmaz (plan.md Karar 4).
16. **AC-8 [Medium]** Given hiçbir kuruluş üyesi olmayan kullanıcı, When uygulama kabuğu yüklenir, Then menüde Keşfet girişi görünmez; rota doğrudan açılırsa "Sayfa bulunamadı" gösterilir. Given doğrulanmamış kuruluşun üyesi, Then giriş görünür ama sayfa "kuruluşun doğrulanınca açılır" bilgi durumunu gösterir; API yine `404` döner (plan.md Karar 3).
17. **AC-9 [Medium]** Given DB hatası ya da zaman aşımı, When liste çağrılır, Then `500`/`504` genel hata gövdesi döner (stack trace, sorgu, PII yok) ve arayüz "Bir hata oluştu" + yeniden dene düğmesi gösterir — boş liste gösterilmez.
18. **AC-10 [Medium]** Given öğrenci ayarları, When görünürlük `ORGANIZATIONS` seçilir, Then "Profilin kurumlara Keşfet'te görünür olur" açık bilgilendirmesi gösterilir; değişiklik anında etkilidir.

## Davranış Sözleşmesi (hangi durumda ne döner)

`GET /discover/talents`

| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path | `200 + {items:[...], next_cursor}` | yok | Kart listesi | AC-1 |
| 2 | Girdi geçersiz (bozuk UUID, `limit>50`, bilinmeyen parametre) | `422` | yok | "Filtre geçersiz" | AC-6, AC-S4, AC-S5 |
| 3 | Filtre geçerli ama skill/institution kaydı yok | `200 + {items:[], next_cursor:null}` | yok | "Eşleşen öğrenci bulunamadı" | AC-5 |
| 4a | Anonim | `401` | yok | Giriş sayfasına yönlendirme | AC-S1 |
| 4b | Talent / üyeliksiz / doğrulanmamış org | `404` | yok | "Sayfa bulunamadı" | AC-S1, AC-S7 |
| 5 | DB hatası | `500` genel gövde | PII'siz hata logu | "Bir hata oluştu, tekrar deneyin" | AC-9 |
| 6 | Zaman aşımı | `504` veya istemci timeout | yok | Yeniden dene düğmesi | AC-9 |
| 8 | Görünür öğrenci hiç yok | `200 + {items:[], next_cursor:null}` | yok | "Henüz keşfedilebilir öğrenci yok" | AC-5 |

`GET /discover/talents/{public_id}`

| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Görünür öğrenci | `200 + izinli alanlar` | audit kaydı (AC-S8) | Profil detayı | AC-7 |
| 3 | Id yok **veya** görünürlük kapalı | `404` (ikisi aynı gövde) | yok | "Sayfa bulunamadı" | AC-S3 |
| 4 | Yetkisiz | `401` / `404` | yok | yukarıdaki ile aynı | AC-S1 |

Kısmi başarı: **Satır 7 silindi** — uçlar salt okunur, tek sorgu kümesi; ya tam yanıt ya tam hata. Toplu yüklemelerden (skill, deneyim sayısı) biri hata verirse eksik kartlı `200` dönülmez, istek `500` olur.
Hiçbir şey yapılamadı ama hata da yok: `200 + []` yalnız yetkili çağrıda ve sorgu başarıyla çalıştığında döner. Sorgu çalışmadıysa `500`; boş listeyle maskelenmez.
Boş sonuç ↔ hata ayrımı: yetkili çağrı her zaman `200` (boş olsa da), yetkisiz çağrı `401`/`404`, altyapı hatası `5xx`. Üçü farklı durum koduna sahiptir; arayüz boş durumu yalnız `200` için gösterir.

## Test Strategy
Unit: 30% — filtre/sayfalama parametre doğrulaması, yanıt şeması allowlist'i, frontend filtre bileşeni ve boş/hata durumları.
Integration: 60% — rol × görünürlük yetkilendirme matrisi (`tests/authorization`), filtre kombinasyonları, görünürlük değişimi sonrası 404, sorgu sayısı sınırı.
E2E: 10% — Keşfet'e gir → filtrele → kart → profil → mevcut davet akışına geçiş.

## Benchmark / Başarı Ölçütü
Coverage Target: yeni kodda ≥ %85; rol × görünürlük yetkilendirme matrisi %100.
Performance Target: liste ucu p95 < 300 ms (seed ölçeği), < 500 ms (1000 öğrenci).
Memory: —
Sorgu sınırı: istek başına en fazla 3 sorgu (liste, skill toplu yükleme, deneyim sayısı toplu) — N+1 yok.
Sayfalama: varsayılan 20, en fazla 50, derinlik 200.
Görsel/UI kriteri: kart ızgarası mobil genişlikte bozulmamalı; boş durum ve hata durumu metinleri görünür olmalı; doğrulanmış / self-claim rozet ayrımı ayırt edilebilir olmalı (`verify` adımında `vision-test`).

## Kapsam Dışı
- Skor / eşleşme puanı, öneri, "sana uygun adaylar", AI (yasaklı — matching motoru).
- Serbest metin ad araması (enumeration + PII riski).
- Kaydetme / favori, kayıtlı arama, mesajlaşma / chat, CSV / PDF export.
- Yeni davet akışı (mevcut `ORG_TO_TALENT` akışına link verilir).
- Institution koordinatörü için keşif (zaten kendi kurumunun öğrencilerini görüyor; PLAN 7.5).
- Mevcut öğrencilerin `visibility` varsayılanını toplu değiştirme.
- Redis / Elasticsearch / pgvector.

## Etkilenen Dosyalar/Modüller (bilinen)
- `docs/AUTHORIZATION.md` §4: "TalentProfile (public alanlar) — Org üyesi (ilgisiz) = ✗" satırı değişir → **yetkilendirme değişikliği, uygulamadan önce açık onay gerekir** (CLAUDE.md).
- `backend/app/models/identity.py:84-106` — `talent_profiles.visibility` (mevcut; şema değişikliği beklenmiyor).
- Yeni router + servis, `tests/authorization` içine yeni matris, `docs/API.md`.
- Frontend: Keşfet rotası, menü girişi, öğrenci görünürlük ayarı bilgilendirmesi, sabit metin dosyası.
- Kesin yollar `plan` adımında doğrulanacak.

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı. Sonraki adımlarda arama `backend/`, `frontend/src/`, `docs/` ile sınırlı tutulmalı.

## Rollback Beklentisi
Tek bayrak (öneri: `DISCOVER_ENABLED`) hem backend rotasını hem frontend menü girişini kapatır; kapalıyken uçlar `404` döner. Şema değişmediği için migration geri alma gerekmez. `docs/AUTHORIZATION.md` değişikliği ayrı commit'te tutulur ki tek başına geri alınabilsin.

## Risks
- **Yetki genişlemesi:** Açık kaynak repoda bir filtre hatası, görünürlüğü kapalı öğrencileri tüm kurumlara açar. Azaltma: AC-2, AC-S1–S4, kapsamın merkezî `scoped_*()` içinde tek yerde tanımlanması.
- **Toplu kazıma:** Doğrulanmış bir kurum hesabı tüm görünür öğrencileri dökebilir. Azaltma: AC-S6 (sayfa 50, derinlik 200). Kullanıcı başına hız sınırı **kabul edilen risk olarak açık** — Redis yasak, mevcut bir hız sınırlayıcı olup olmadığı doğrulanmadı (Unknowns #2).
- **Boş vitrin:** `visibility` varsayılanı `INSTITUTION` olduğu için demo verisinde Keşfet boş çıkabilir. Azaltma: seed'de birkaç öğrenci `ORGANIZATIONS` yapılır (seed değişikliği ayrı iş).
- **Takvim:** Bugün 10 Ekim 2026, teslim 9–11 Ekim. R.1 "vakit kalırsa" maddesi; yetkilendirme değişikliği + tam `tests/authorization` koşusu gerektiriyor.
- **Kapsam kayması:** "Keşfet" adı öneri/sıralama beklentisi doğurur; skor eklenirse yasaklı matching motoruna dönüşür.

## Assumptions
(Hepsi Sonnet alt-ajanı varsayımıdır, kullanıcı onaylamadı.)
- "Kurum" = Organization üyeleri (tüm üyeler, yalnız `ORG:ADMIN` değil).
- Yalnız doğrulanmış Organization'lar erişir.
- Görünürlük opt-in: yalnız `ORGANIZATIONS` ve `PUBLIC`.
- Uç adları `GET /discover/talents` ve `GET /discover/talents/{public_id}`.
- Görev @fe + @be2 paylaşımlı; @fe backend yarısını yazmaz, uçlar hazır olana kadar mock katmanıyla ilerler (rastgele sonuç yok, versiyonlu localStorage).
- Test oranı 30/60/10.

## Unknowns
`plan` adımında kod keşfiyle çözülenler: doğrulanmış = `verification_level` T2+ (#1); hız sınırlayıcı var, `services/rate_limit.py` (#2 — AC-S6'ya kullanıcı başına 30/dk kuralı eklenir); görünürlük arayüzü var (#4); bayrak `core/config.py` ayarı olarak eklenir (#5). Audit kapsamı plan.md Karar 4 ile daraltıldı (#3).

Hâlâ açık:
1. Backend yarısını @be2 hackathon süresi içinde üstlenebiliyor mu?
2. `/me` yanıtı kuruluşun doğrulama seviyesini taşıyor mu? (AC-8'deki bilgi durumu, taşımıyorsa API'nin `404`'üne göre gösterilir.)
3. Sonnet alt-ajanının verdiği kararlar (atdd Assumptions + plan.md Kararlar) kullanıcı tarafından onaylanmadı.

## Sorular ve Cevaplar (ham kayıt)
Tüm cevaplar: *Sonnet alt-ajanı (low) tarafından yanıtlandı* — kullanıcı cevabı değildir.

1. Kurum kim? → Organization üyeleri (ORG:ADMIN dahil tüm üyeler), yalnız doğrulanmış organization; Institution koordinatörleri kapsam dışı. *Gerekçe: hedef "işveren öğrenci keşfeder", yetki riski en dar.*
2. Ana hedef? → Engagement öncesi kanıta dayalı keşif; eşleştirmeyi insan yapar, sistem yalnız deterministik filtre sunar. *Gerekçe: §9.1 matching'i yasaklıyor, R.1 basit filtreye izin veriyor.*
3. Kim görünür? → Yalnız `ORGANIZATIONS`/`PUBLIC`; varsayılan `INSTITUTION` görünmez, opt-in gerekir. *Gerekçe: KVKK, varsayılanlar sessizce genişletilmez.*
4. Alanlar? → Görünür: ad, üniversite/bölüm, skill'ler (rozet ayrımıyla), doğrulanmış deneyim sayısı, public talent id. Asla: e-posta, telefon, CV, kanıt dosyaları, `private_note`, PRIVATE deneyimler. *Gerekçe: mevcut yetki matrisi.*
5. Filtre/sıralama? → `skill_id` (çoklu, hepsi), `institution_id`, `verified_only`; serbest metin yok; sıra `created_at DESC, id`; sayfa 20 / maks 50. *Gerekçe: puansız, öngörülebilir, kazımayı sınırlar.*
6. Happy path? → Keşfet → filtre → kart → keşfet-görünümlü profil → "Davet gönder" mevcut akışa link. *Gerekçe: minimum eklemeyle zinciri bağlar.*
7. Edge case'ler? → boş sonuç 200+[]; sonradan PRIVATE → detay 404; bozuk UUID 422; doğrulanmamış org/üyeliksiz 404; üyelik askıya alındı 404; `limit>50` 422. *Gerekçe: 403 sızıntısı yasak.*
8. Davranış sözleşmesi → yukarıdaki tablo; satır 7 silindi (tek sorgu, kısmi sonuç yok).
9. Benchmark? → p95 < 300 ms / < 500 ms, ≤ 3 sorgu, authz matrisi %100, yeni kod ≥ %85. *Gerekçe: küçük veri, tek VPS.*
10. Kapsam dışı? → skor, öneri, AI, serbest metin, favori, kayıtlı arama, chat, export, yeni davet akışı, koordinatör keşfi. *Gerekçe: CLAUDE.md MVP dışı listesi.*
11. Güvenlik? → hız sınırı ~30/dk, sayfa 50, derinlik 200; yanıtta PII yok; audit yalnız filtre meta verisiyle; öğrenciye açık bilgilendirme; AUTHORIZATION.md §4 güncellenir, `pytest tests/authorization -q` tamamı, uygulama öncesi açık onay. *Gerekçe: CLAUDE.md onay sınırı.*
12. Test oranı / iş bölümü / rollback? → 30/60/10; paylaşımlı, @fe mock ile ilerler; `DISCOVER_ENABLED` bayrağı. *Gerekçe: teslim yakın, kapatılabilir yayın.*

## Threat Model (STRIDE-lite özeti)
Varlık: öğrenci profil verisi (KVKK). Sınır: tarayıcı → API; kiracı → kiracı (Organization ↔ engagement'ı olmayan öğrenci).

| Kategori | Karar | AC |
|---|---|---|
| Spoofing | Atlandı — mevcut oturum/kimlik doğrulama kullanılıyor, değişmiyor | — |
| Tampering | İstemciden gelen kapsam/rol parametresine güvenilmez | AC-S4, AC-S5 |
| Repudiation | Arama ve profil görüntüleme izi | AC-S8 |
| Info disclosure | Alan allowlist'i, görünürlük kapalıyken varlık sızmaması | AC-2, AC-S2, AC-S3 |
| DoS / kazıma | Sayfa ve derinlik sınırı; hız sınırı açık risk | AC-S6 |
| Elevation | Yetki her istekte sunucuda, 404 ile | AC-S1, AC-S7 |

Sonraki adım notu: yetkilendirme AC'leri üretildiği için `authz-test` çalıştırılmalı; uygulama henüz olmadığından canlı sondaj `plan` sonrasına kalır.
