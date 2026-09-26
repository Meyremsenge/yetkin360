---
task_slug: yet-108-toplu-hatirlatma-ucu
jira_id: YET-108
saga_task_id: null
threat_model: done
priority: medium
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 70
  integration: 20
  e2e: 10
affected_modules:
  - backend/app/api/institutions.py (var olan dosya, mevcut router'a yeni route eklenecek: POST /{institution_id}/reminders — bkz. mevcut POST /{institution_id}/members, /link-requests pattern'i)
  - backend/app/services/reminder.py (yeni: institution/rol doğrulama + engagement filtreleme + outbox insert; throttle/dedup YOK — bkz. "429/dedup/cap doğrulama sonucu")
  - backend/app/services/authorization.py (COORD/ORG_ADMIN kontrolü — can()/scoped_*)
  - backend/tests/test_reminders.py (yeni)
  - backend/tests/authorization/test_reminders_authorization.py (yeni)
---

# ATDD — yet-108-toplu-hatirlatma-ucu

## Jira Kaynağı
[YET-108 — [PLAN 3.4] Toplu hatırlatma ucu (POST /institutions/{id}/reminders)](https://kuyusuzyusuf123.atlassian.net/browse/YET-108)
Alt görevler: YET-130 (servis: hatırlatma outbox kaydı oluşturma), YET-131 (endpoint), YET-132 (yetkilendirme testi: yalnız kurum admin/coordinator tetikleyebilir).
Açıklama (Jira'dan birebir): "PLAN.md Faz 3 — madde 3.4. Sahip: @be2"
Not: CONTRIBUTING.md'de `@be2` = Meyrem Şenge olarak eşleniyor ama Jira'da bu görev Elif Sara'ya atanmış — gerçek iş dağılımı doküman etiketinden farklı ilerlemiş, kullanıcıya ayrıca bildirildi.

Jira'ya bağlı API sözleşmesi (jira-sync skill'i bu oturumda kullanılamadı — proje kurulumunda tanımlı değil; bilgi doğrudan `docs/API.md` satır 320/333'ten ve önceki bir Atlassian MCP sorgusundan alındı, birebir aktarılıyor):
`POST /institutions/{id}/reminders` | yetki: `INST:COORD` | girdi: `engagement_ids[]`, `template` | çıktı: `202` + `queued_count` | hata: `404`, `429`. Not: "`/reminders` `202` döner, `200` değil — e-postalar `outbox` üzerinden gidiyor."

### 429/dedup/cap doğrulama sonucu (kullanıcı talebiyle, plan'dan önce yapıldı)
Kullanıcı şu üç sayısal değeri (institution throttle penceresi, engagement dedup penceresi,
`engagement_ids[]` üst sınırı) kabul etmeden önce Jira/PLAN.md/docs'ta tanımlı olup olmadığının
kontrol edilmesini istedi. Kontrol edildi, sonuç:

- **`docs/SECURITY.md` §3** bir "Genel API: 300/dk/kullanıcı" limiti TANIMLIYOR (`Uygulama:
  Nginx rate limit + PostgreSQL sayaç`), ve `docs/API.md`'de `429` birçok uçta (register,
  login, forgot-password, reminders) aynı şekilde listeleniyor — yani `429` muhtemelen
  bu genel, uç-bağımsız altyapının işi, reminders'a özel bir sayı DEĞİL.
- Ama bu genel altyapı **henüz kod tabanında yok** — `backend/app/main.py`'de yalnız
  CORS middleware var, `/auth/login` ve `/auth/register` gibi 429'u zaten sözleşmesinde
  taşıyan uçlarda bile hiçbir rate-limit kodu yok (grep doğrulandı). PLAN.md 1.6 notu bunu
  doğruluyor: "genel rate-limit altyapısı kararı gerektiriyor... Faz 5.2/5.6 kapsamına
  alınabilir."
- Var olan tek somut precedent `backend/app/services/organization.py`'deki
  `verify-domain` ucu: institution-scope, per-resource, 60 saniyelik cooldown
  (`last_verify_attempt_at` kolonu). Ama bu BAŞKA bir uca özgü, farklı bir sayı — reminders
  için doğrudan kullanılamaz, yalnız "böyle bir mekanizma nasıl kodlanır" örneği.
- **Engagement-seviyeli dedup penceresi (24 saat)** ve **`engagement_ids[]` üst sınırı
  (500)**: Jira'da (YET-108/130/131/132 açıklamaları boş), `PLAN.md`'de, `docs/API.md`/
  `docs/DATABASE.md`/`docs/SECURITY.md`'de, final analiz'de veya kodda (schema'larda
  `max_length`/`max_items` konvansiyonu taranmadı, hiçbir yerde array-size sınırı yok)
  **hiçbir tanım yok.** Bunlar önceki turda alt-ajanın (benim onaylamadan aktardığım)
  makul ama dayanaksız varsayımlarıydı.

**Karar (bu ATDD'de, kullanıcı onayına sunuluyor):** Bu görev kapsamında institution-throttle
VE engagement-dedup **uygulanmayacak** — ikisi de tanımsız bir sayıya dayanıyordu, keyfi
hardcode edilmeyecek. `429`, genel altyapı kurulana kadar bu uçta fiilen tetiklenmeyecek
(login/register ile aynı durumda — proje çapında bilinen bir boşluk, bu görevin icat etmesi
gereken bir şey değil). `engagement_ids[]` için de sabit bir üst sınır kodlanmayacak; bu
DoS riski "Kabul edilen risk" olarak Faz 5.2/5.6'ya not düşülüyor. Aşağıdaki AC listesi ve
davranış sözleşmesi bu karara göre güncellendi (AC-6/7/8/9 kaldırıldı veya yeniden yazıldı).

## Persona
Kendi kurumuna ait (`institution_id` eşleşen) ve `INST:COORD` yetkisine sahip kurum admin/koordinatörü; bekleyen değerlendirmesi olan engagement'lar için toplu hatırlatma tetikler.

## Hedef (Neden)
Koordinatörün her bekleyen değerlendirme için tek tek manuel hatırlatma e-postası atma işini otomatikleştirip değerlendirme tamamlanma oranını artırmak (final analiz: "en değerli — koordinatörün elle yaptığı işi otomatikleştirir").

## User Story
As a kurum koordinatörü
I want bekleyen değerlendirmesi olan engagement'lar için tek istekte toplu hatırlatma tetiklemek
So that değerlendirenlere tek tek manuel e-posta atmak zorunda kalmayayım

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given kendi kurumuna ait koordinatör, When `POST /institutions/{id}/reminders` çağrılır (`engagement_ids: [id1, id2, id3]`, `template: "evaluation_pending"`), Then `202` + `{"queued_count": 3}` döner; tek transaction içinde 3 outbox kaydı + 1 audit_event yazılır, hiçbir senkron e-posta gönderimi yapılmaz.
2. [Critical] Given `engagement_ids[]` boş dizi, When istek gönderilir, Then `422` döner (Pydantic şema doğrulaması — `main.py`'deki global `RequestValidationError` handler'ı, `test_talent.py`/`test_organization.py`'deki mevcut precedent'le tutarlı; `400` bu projede yalnız elle fırlatılan iş-kuralı hataları için kullanılıyor), hiçbir DB yazımı olmaz. **Düzeltme notu:** bu AC ilk yazıldığında yanlışlıkla `400` denmişti, `code-copilot` aşamasında gerçek kod (`main.py:56-72`) okunarak düzeltildi.
3. [Critical] Given başka kuruma ait/var olmayan bir `engagement_id`, kendi kurumuna ait geçerli id'lerle karışık gönderilir, When istek gönderilir, Then yalnız kendi kurumuna ait id'ler işlenir, `queued_count` yalnız işlenenleri sayar, response hangi id'nin filtrelendiğini belirtmez.
4. [Critical] Given path'teki `{id}` isteği yapan kullanıcının kurumu değil (B kurumunun koordinatörü, A kurumunun path id'siyle çağırıyor), When istek gönderilir, Then `404` döner (403 değil), hiçbir kayıt oluşmaz, response A kurumunun var olup olmadığına dair ipucu vermez.
5. [Critical] Given `COORDINATOR`/`ORG_ADMIN` olmayan bir rol (örn. TALENT), When kendi kurumu path'iyle istek gönderilir, Then `404` döner, hiçbir kayıt oluşmaz.
6. [High] Given tüm gönderilen `engagement_ids` başka kuruma ait/var olmayan id'lerden oluşuyor (hiçbiri geçerli değil), When istek gönderilir, Then `202` + `{"queued_count": 0}` döner (hata değil — "geçerli hedef kalmadı" ile "institution bulunamadı" farklı kod, bkz. AC-4).
7. [Medium] Given `template` alanı boş/tanınmayan bir değer, When istek gönderilir, Then `422` döner (aynı Pydantic şema doğrulaması, bkz. AC-2 düzeltme notu).

**AC-6 (eski) / AC-7 (eski) / AC-9 (eski) kaldırıldı — açık soru:** institution-level throttle
(`429`), engagement-level dedup ve `engagement_ids[]` üst sınırı hiçbir kaynakta (Jira/PLAN.md/
docs/kod) tanımlı değil (bkz. yukarıdaki "429/dedup/cap doğrulama sonucu"). Bu görev bunları
UYGULAMAYACAK — bkz. Kapsam Dışı ve Unknowns. `test-copilot`/`code-copilot` bu üç konuda test/
kod üretmeyecek; ileride bir sayı kararlaştırılırsa ayrı bir PLAN maddesi (öneri: 3.12 güvenlik
geçişi veya Faz 5.2/5.6 kapsamında) açılabilir.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path | `202` + `{"queued_count": N}` | Tek transaction'da N outbox kaydı + 1 audit_event | "N kişiye hatırlatma kuyruğa alındı" | AC-1 |
| 2 | Girdi geçersiz/eksik (`template` boş/tanınmayan, `engagement_ids` eksik/boş) | `422` (Pydantic şema hatası) | Yok | Hangi alanın geçersiz olduğu | AC-2, AC-7 |
| 3 | Kaynak yok (institution id yok) | `404` | Yok | Genel "bulunamadı" | AC-4 |
| 4 | Yetkisiz erişim (rol yetersiz veya başka kuruma ait kullanıcı) | `404` (403 değil) | Yok | Aynı "bulunamadı" mesajı — varlık sızdırılmaz | AC-4, AC-5 |
| 5 | Dış bağımlılık hatası (outbox insert sırasında DB hatası) | `500` | Transaction rollback, hiçbir kayıt commit edilmez | Genel sunucu hatası (PII içermez) | — |
| 6 | Zaman aşımı | `500` ile aynı (bu görevde tek ağ-dışı işlem DB insert; email gönderimi worker'ın kapsamında) | Rollback | Genel sunucu hatası | — |
| 7 | **Kısmi başarı** (bazı id'ler işlenir, bazıları başka kuruma ait/geçersiz olduğu için filtrelenir) | `202` + `{"queued_count": başarılı_sayı}` | Yalnız başarılı olanlar için kayıt | Sadece toplam sayı, hangi id'lerin elendiği belirtilmez | AC-3 |
| 8 | **Hiçbir şey yapılamadı ama hata yok** (tüm id'ler filtrelendi) | `202` + `{"queued_count": 0}` | Yok | "0 kişiye gönderildi" | AC-6 |

Kısmi başarı ile hata ayrımı: filtrelenen id'ler asla `400`/`404` üretmez — yalnız sayıma dahil edilmez (AC-3, AC-6).
Boş sonuç ↔ hata ayrımı: `queued_count: 0` (tümü filtrelendi, `202`) ile "institution bulunamadı" (`404`) ve "boş girdi dizisi" (`400`, AC-2) birbirinden HTTP koduyla kesin ayrılır — üçü de farklı kod döner.

## Güvenlik Kabul Kriterleri (threat-model, STRIDE-lite)

Varlıklar/sınırlar: institution-scoped engagement verisi, kurum üyelerinin e-posta adresleri (dolaylı, outbox üzerinden); sınır: tarayıcı→API (auth), API→DB (multi-tenant izolasyon).

STRIDE-lite değerlendirmesi:
- **Spoofing:** Atlandı — mevcut auth altyapısına (token doğrulama) güveniliyor, bu görevde yeni bir kimlik kanıtlama mekanizması yok.
- **Tampering:** Path'teki `{id}` ve gövdedeki `engagement_ids[]` istemciden geliyor, doğrudan güvenilemez → **AC-S1, AC-S3** (aşağıda).
- **Repudiation:** Audit_event zorunlu → **AC-S6**.
- **Info disclosure:** 403 yerine 404, filtrelenen id'ler response'ta belirtilmiyor → **AC-S1, AC-S3**.
- **DoS:** Institution-level throttle ve `engagement_ids[]` üst sınırı hiçbir kaynakta tanımlı
  değil (bkz. "429/dedup/cap doğrulama sonucu") → bu görevde UYGULANMIYOR, kabul edilen risk
  olarak aşağıda not düşüldü, ayrıca Faz 5.2/5.6'ya bırakıldı.
- **Elevation:** Rol + kurum eşleşmesi sunucuda kontrol edilmeli, sadece rol yetmez → **AC-S2**.

| # | Güvenlik AC | Saldırgan girdisi | Beklenen gözlenebilir sonuç |
|---|---|---|---|
| AC-S1 [Critical] | Cross-tenant path erişimi | B kurumu koordinatörünün token'ı, path'te A kurumunun id'si | `404`, hiçbir kayıt oluşmaz, A'nın var olup olmadığı response'tan anlaşılamaz (aynı 404 gövdesi hem var-ama-yabancı hem hiç-yok durumunda) |
| AC-S2 [Critical] | Rol yükseltme denemesi | TALENT rolündeki kullanıcının token'ı, kendi kurumunun path'i | `404`, hiçbir kayıt oluşmaz — AC-5 ile aynı, burada ayrıca vurgulanıyor: kontrol sunucuda `can()`/`scoped_*` ile yapılmalı, yalnız endpoint dekoratöründe rol adı karşılaştırması yeterli değil |
| AC-S3 [High] | Id enumeration denemesi | Kendi kurumuna ait N geçerli id + 1 yabancı-kurum id karışık gönderilir | `queued_count` yalnız kendi kurumundakileri sayar; response'ta yabancı id'nin filtrelenme nedeni (yok/yabancı kuruma ait) ayırt edilemez — hepsi aynı şekilde "sayıma dahil değil" |
| AC-S6 [Medium] | — (pozitif kontrol, saldırgan girdisi yok) | Başarılı bir tetikleme sonrası audit_event içeriği | `audit_event` append-only kaydında: tetikleyen `user_id`, `institution_id`, işlenen `engagement_id` listesi, zaman damgası bulunur; e-posta tam adresi veya `private_note` gibi PII **yazılmaz** |

**Kabul edilen risk (bilinçli, kapsam dışı):**
1. Tekil `engagement_id` enumeration'ı — saldırgan (zaten geçerli bir COORD hesabına sahip
   olmalı) tek tek id deneyip `queued_count` farkından "bu id var ama bana ait değil"
   bilgisini teorik olarak çıkarabilir. Bu risk, institution-level throttle OLMADIĞI için
   önceki turdakinden daha az azaltılmış durumda — saldırgan istediği hızda deneyebilir.
   Yine de kapsam dışı bırakılıyor çünkü: saldırgan zaten kimliği doğrulanmış bir COORD
   olmalı (iç tehdit senaryosu, dış saldırgan değil). Faz 5.2 (BOLA test matrisi
   tamamlama) kapsamına daha derin inceleme için not düşülüyor.
2. `engagement_ids[]` üst sınırı olmadan çok büyük bir dizi gönderilmesi (DoS/N+1 riski) —
   hiçbir yerde tanımlı bir sayı olmadığı için bu görevde sınırlanmıyor. Faz 5.6 ("yük
   testi ve N+1 sorgu temizliği") kapsamına bırakılıyor.
3. `429` (rate limit) bu uçta fiilen çalışmayacak — genel altyapı yok (login/register ile
   aynı, proje çapında bilinen bir boşluk, PLAN 1.6). Faz 5.2/5.6'ya bırakıldı.

**authz-test skill'i ne zaman çalışacak:** Bu ATDD aşamasında `authz-test` çağrılmadı — kendi tanımına göre "gerçek çalışan sisteme karşı" doğrulama yapıyor, henüz endpoint yok. `code-copilot` implementasyonu bitirip `verify` aşamasına gelindiğinde, yukarıdaki AC-S1/S2/S3 için `authz-test` ile canlı IDOR/cross-tenant probe'ları çalıştırılacak. Bu bir varsayım/karar — Assumptions'ta da tekrarlandı.

## Test Strategy
Unit: 70% — filtreleme (institution eşleşmesi), servis mantığının kendisi (`services/reminder.py`) — dedup/throttle hesabı YOK (kapsam dışı)
Integration: 20% — endpoint + DB + outbox + yetkilendirme uçtan uca (gerçek transaction, gerçek outbox satırı doğrulanır)
E2E: 10% — yetkilendirme matrisi (`pytest tests/authorization`) üzerinden AC-4/5/S1/S2 senaryoları

Yetkilendirme kritik olduğundan `pytest tests/authorization -q` tamamı ayrıca CLAUDE.md kuralı gereği zorunlu.

## Benchmark / Başarı Ölçütü
Coverage Target: 90%
Performance Target: yok (bu uçta ölçülebilir bir performans hedefi belirtilmedi)
Memory: yok
Görsel/UI kriteri: yok (bu görev saf backend, frontend bileşeni yok)
Diğer ölçülebilir kriterler: `pytest tests/authorization -q` tamamı yeşil olmalı; yeni endpoint aynı commit'te yetkilendirme testi içermeli (CLAUDE.md kuralı).

## Kapsam Dışı
- Outbox worker'ın kendisi (asıl e-posta gönderimi, retry mantığı) — bu görev yalnız outbox SATIRI oluşturur.
- Gerçek e-posta şablon içerikleri/render — `template` bu görevde yalnız string/enum olarak kabul edilir, içerik üretimi kapsam dışı.
- Template CRUD ucu.
- **Institution-level throttle (429) — uygulanmıyor.** Tanımlı bir sayı yok, genel rate-limit
  altyapısı da yok (Faz 5.2/5.6'ya bırakıldı, PLAN.md 1.6 notuyla tutarlı, login/register ile
  aynı durum).
- **Engagement-level dedup (tekrar hatırlatma engelleme) — uygulanmıyor.** Tanımlı bir pencere
  yok. Bu, MVP'de aynı engagement için art arda hatırlatma gönderilebileceği anlamına gelir —
  bilinen bir sınırlama, kullanıcıya bildiriliyor (bkz. Risks).
- **`engagement_ids[]` üst sınırı — uygulanmıyor.** Tanımlı bir sayı yok, sabit değer icat
  edilmiyor.
- Engagement/evaluation domain mantığının kendisi (durum geçişleri vb.) — bu görev yalnız var olan engagement'ları referans alır, değiştirmez.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/app/api/institutions.py` (var olan dosya — `plan` aşamasında doğrulandı: 305 satır,
  mevcut router'a `POST /{institution_id}/members`, `/link-requests` gibi route'lar zaten var,
  aynı pattern'e yeni bir `POST /{institution_id}/reminders` route eklenecek)
- `backend/app/services/reminder.py` (yeni)
- `backend/app/services/authorization.py` (mevcut `can()`/`scoped_*`'a COORD/ORG_ADMIN + institution-scope kontrolü eklenmesi/kullanılması gerekebilir — `plan` aşamasında mevcut fonksiyonlar incelenip netleşecek)
- `backend/tests/test_reminders.py` (yeni)
- `backend/tests/authorization/test_reminders_authorization.py` (yeni)
- Migration gerekmiyor (dedup/throttle kapsam dışı bırakıldığı için yeni kolon/tablo yok;
  `plan` aşamasında bu varsayım Read/Glob ile bir kez daha teyit edilecek).

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulanmadı — bu oturumda repo kökünün proje klasörüyle (`/Users/elifsarahan/Desktop/yetkin360`) aynı olup olmadığı, daha geniş bir dizin/devasa git geçmişi taşıyıp taşımadığı ayrıca kontrol edilmedi. `plan`/`test-copilot`/`code-copilot` aşamalarında arama bu proje klasörüyle sınırlı tutulacak.

## Rollback Beklentisi
Servis fonksiyonu tek bir DB transaction'ı içinde çalışır (outbox insert + audit_event). Herhangi bir adımda hata olursa transaction rollback edilir, kısmi outbox/audit kaydı kalmaz (Davranış Sözleşmesi satır 5/6).

## Risks
- Dedup olmadan aynı engagement için tekrar tekrar hatırlatma tetiklenebilir (spam riski,
  kullanıcı deneyimi sorunu) — kabul edilen bir MVP sınırlaması, sayı tanımlanınca ayrı bir
  PLAN maddesiyle eklenecek.
- `engagement_ids[]` üst sınırı olmadan çok büyük istek gönderilebilir (DoS/N+1) — Faz 5.6'ya
  bırakılan kabul edilen risk.
- `429` bu uçta hiçbir zaman fiilen dönmeyecek (genel altyapı yokken) — sözleşmede duruyor ama
  test edilemez; `test-copilot` bu kod yolunu test etmeyecek, bu bilinçli bir kapsam kararı.
- Kabul edilen risk: tekil id enumeration (yukarıda "Kabul edilen risk" bölümünde detaylı).

## Assumptions
- `authz-test` skill'inin canlı probe'ları `verify` aşamasına ertelendi (bu oturumda alınan bir karar, kullanıcıya bu atdd.md ile birlikte bildiriliyor).

## Unknowns (kullanıcı onayı/kararı gerektiren açık sorular)
- **Institution-level throttle penceresi:** tanımsız. Genel rate-limit altyapısı kurulana
  kadar (Faz 5.2/5.6) bu uçta uygulanmayacak — bir sayı istenirse ayrı görev.
- **Engagement-level dedup penceresi:** tanımsız. Bu görevde uygulanmayacak.
- **`engagement_ids[]` üst sınırı:** tanımsız. Bu görevde sınırlanmayacak.
- Gerçek `template` enum değerleri (yalnız `"evaluation_pending"` mi, başka şablonlar da olacak mı?) — `plan` aşamasında `docs/API.md`'nin geri kalanı taranarak netleşebilir.

## Sorular ve Cevaplar (ham kayıt)
1-12: Sonnet 5 low alt-ajanı tarafından yanıtlandı (gerekçe: ATDD skill kuralı gereği kullanıcı bu netleştirme sorularıyla durdurulmuyor). Tam cevap metni bu oturumun agent-message kaydında; özet madde 3/4/5/6/7/8/9/10/11/12 doğrudan yukarıdaki AC/sözleşme/kapsam bölümlerine birebir işlendi.
