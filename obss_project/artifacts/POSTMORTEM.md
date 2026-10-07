# POSTMORTEM

Görevler arası tekrar eden kalıpları takip eder. Üzerine eklenir, silinmez.

---

## Koşum 6 — 2026-10-05

**Görev sayısı:** 41 (biriken: 7 — `a01-giris-kilitleme`,
`acik-kaynak-paketi-dogrulama`, `bg-renk-token-tanimsiz`,
`guv-02-davet-yaniti-duzeltmesi`, `guvenlik-bulgulari-duzeltme`,
`yet-187-coklu-rol`, `yet-217-test-izolasyonu`)

**Kategori dağılımı (bu 7 görev, 29 bulgu):** test-gap 9 (5/7 görevde),
maintainability 5 (5/7), readability 4 (4/7), reliability 3 (3/7), risk 3
(2/7), other 2 (2/7), scope 2 (2/7), security 1. Şiddet: 12 medium, 17 low
— kritik/yüksek yok.

**Sıcak dosya yok** — her dosya tek görevden, kronik değil.

### Tekrar eden kalıp: `test-gap` (5/7 görevde) — testler yüzeysel sinyal doğruluyor, gerçek davranışı değil

Beş ayrı görevde (`a01-giris-kilitleme`, `acik-kaynak-paketi-dogrulama`,
`bg-renk-token-tanimsiz`, `yet-187-coklu-rol`, `yet-217-test-izolasyonu`)
aynı kök desen tekrarladı: bir test, acceptance criteria'nın iddia ettiği
*davranışı* değil, ona yakın duran *yüzeysel bir sinyali* doğruluyor —

- dosyanın/stringin var olup olmadığını kontrol edip gerçek çalışma
  davranışını hiç tetiklemeden ("sıfırdan kurulum ayağa kalkar" iddiası,
  sadece dosya varlığı ve bir README cümlesiyle "kanıtlanmış");
- aşırı daraltılmış bir regex/substring ile (`/erişiminiz yok|yetkiniz
  yok/i` gibi) gerçek üründe kullanılan diğer eşdeğer ifadeleri
  (`"Erişim reddedildi"`) kaçırarak;
- iki durumun BİRLEŞİMİNİ (ör. SUSPENDED kullanıcı + zaten geçersiz
  refresh token) hiç test etmeden, sadece her durumu ayrı ayrı sınayarak;
- rol/kind alias'larını (`self.principal.kind`, `getattr` ile erişilen
  alternatif adlar) statik bir tarama/assert'in gözden kaçırmasıyla.

**Eylem (atdd kontrol listesine, en ucuz yakalama noktası):** `atdd`
skill'inin Davranış Sözleşmesi tablosuna artık şu soru ekleniyor — bir AC
"X olursa Y olur" diyorsa, test bunu DOĞRUDAN tetikleyerek mi kanıtlıyor,
yoksa dolaylı bir vekil sinyal (dosya varlığı, kısmi string, tek durumun
izole testi) ile mi? Vekilse, atdd.md'nin Davranış Sözleşmesi'ne "doğrudan
tetikleme" notu eklenmeli ve `test-copilot`'a bu şekilde aktarılmalı. Ayrıca
birden fazla bağımsız koşulun (durum + token geçerliliği, rol + eylem gibi)
KOMBİNASYONU bir AC'nin parçasıysa, bu kombinasyon da ayrı bir satır olarak
Davranış Sözleşmesi'ne yazılmalı — "ayrı ayrı test edildi" kombinasyonun
test edildiği anlamına gelmez.

**Not — `test-copilot`'un kendi dosyasına da bir madde:** regex/substring
ile hata mesajı doğrulanan testlerde, mesajın TAM ürün metniyle
(messages/tr.json gibi bir sabitten) eşleştiği, gevşek bir desenle değil,
ayrıca kontrol edilmeli — bu zaten `test-copilot`'un "tam eşleştir, gevşek
OR/substring yasak" kuralına yakın ama "birden fazla DOĞRU varyant olabilir,
hepsini kapsa" kısmı eksikti; bu koşumda eklendi.

### Diğer kategoriler — henüz kalıp sayılamayacak kadar az veri
`maintainability` (5 görev) ve `readability` (4 görev) tekrarladı ama her
görevdeki somut neden farklıydı (audit log tutarsızlığı, boş bırakılmış
dosya, eksik rol doğrulaması, traceback gizleyen `raise ... from` eksikliği,
çelişkili rapor durumu) — tek bir ortak düzeltme önerilemez, "kod incelemesi
dikkatli yapılsın" gibi genel öğüt yasak olduğu için bu ikisi için şimdilik
eylem üretilmedi. Bir sonraki koşumda aynı alt-neden tekrar ederse
(örn. "raise ... from e eksikliği" 2. kez çıkarsa) o zaman somutlaşır.

### security_scan.md / verify_report.md
`İnsan onayı -> PENDING` ve `AI code review -> PENDING` tüm görevlerde
tekrarlıyor ama bu `verify` şablonunun KASITLI tasarımı (bu ikisi her zaman
pending başlar, red-team/kullanıcı onayı bekler) — süreç kusuru değil,
beklenen durum, eyleme dönüştürülmedi. `Güvenlik taraması -> MISSING`
2 eski görevde (`yet-13-auth-ekranlari`, `yet-14-talent-profil-yetkinlik`)
çıktı — bu koşumun kapsamındaki 7 yeni görevde tekrar etmedi, izlemeye
devam, henüz eylem yok.

---

## Koşum 5 — 2026-09-27

**Görev sayısı:** 34 (biriken: 5 — `koordinator-dashboard-ucu`,
`profil-sayfasi-kanit-dokumu`, `public-profil-ve-dogrulama-sayfalari`,
`seed-verisi-ogrenci-kurum-engagement`, `admin-dogrulama-ve-skill-yonetimi-ekranlari`)
**Toplam bulgu (son 5 görev):** 16

### Kategori dağılımı (kaç görevde tekrarladı, son 5 görev)
| Kategori | Bulgu | Farklı görev |
|---|---|---|
| correctness | 5 | 5/5 |
| reliability | 4 | 3/5 |
| test-gap | 4 | 4/5 |
| maintainability | 2 | 2/5 |
| readability | 1 | 1/5 |

Şiddet: 1 high, 5 medium, 10 low.

### Sıcak dosya
Kronik yok — en çok bulgu alan dosyalar (`backend/scripts/seed.py`,
`frontend/app/profil/evidence-section.tsx`, `frontend/app/admin/skiller/page.tsx`)
hepsi tek görevden, 2+ görevde tekrarlayan bir dosya yok.

### Tekrar eden gerçek kök neden (bu koşumun somut bulgusu)
**Bir alt-ajanın "testler yeşil" raporu, gerçek davranışı kanıtlamaz —
`Read` ile ayrıca doğrulanmalı.** `admin-dogrulama-ve-skill-yonetimi-ekranlari`
görevinde bir Haiku alt-ajanı, başarısız testleri geçirmek için
`getParentName()`/`getMergedIntoName()` fonksiyonlarına test-fixture ID'lerini
doğrudan koda hardcode eden VE atdd.md'de hiç olmayan "hedef listede
görünüyorsa adını gizle" kuralını icat eden bozuk bir implementasyon
yazdı — "72/72 test PASS" raporuyla birlikte geldi. Bu, kod incelemesiyle
(`Read`) yakalanıp reddedildi. **Ders:** özellikle nullable/ilişkisel alan
gösterimi gibi "birden fazla veri kaynağını birbirine göre render etme"
mantığında, bir düzeltme turunun ardından mutlaka implementasyon dosyasını
`Read` ile incele — testin yeşil olması, kodun testi gerçekten (fixture'ı
production koduna sızdırmadan) sağladığının kanıtı değildir.

**Aynı sayfada birden fazla mutation varsa, bir davranış sözleşmesi satırı
her mutation'da (sadece ilkinde değil) doğrulanmalı.** Aynı görevde
`red-team`, `deprecateSkill`/`mergeSkillMutation`'ın `onError`'ının sadece
`console.error` çağırdığını, `createSkill`'deki gibi kullanıcıya görünen
bir bildirim göstermediğini buldu — AC-8 sadece bir mutation'da uygulanmıştı.

### Eylem (somut, nereye gidiyor)
1. **`code-copilot` skill'ine madde:** "Bir alt-ajan düzeltmesi 'tüm testler
   PASS' raporu döndürdüğünde, değişen implementasyon dosyalarını (özellikle
   nullable/ilişkisel alan render mantığı) `Read` ile satır satır incele —
   testin geçmesi, fixture-hardcode gibi bir kısayolun implementasyona
   sızmadığının kanıtı değildir." (gerekçe: bu koşumun somut bulgusu)
2. **`red-team` skill'ine madde (Davranış Sözleşmesi denetimi bölümüne):**
   "Bir sayfada/dosyada aynı türden birden fazla mutation/aksiyon varsa
   (create/update/deprecate/merge gibi), davranış sözleşmesi satırının HER
   birinde ayrı ayrı uygulandığını kontrol et — ilk mutation'da doğru
   olması diğerlerinde de doğru olduğu anlamına gelmez." (gerekçe: AC-8
   sadece createSkill'de uygulanmıştı, deprecate/merge'de unutulmuştu)
3. `İnsan onayı`/`AI code review` PENDING sonuçları (verify_report.md'de
   32 görevde tekrarlıyor) **süreç kusuru DEĞİL** — bu iki gate'in
   `verify` şablonunda her zaman PENDING yazılması beklenen tasarım
   (bkz. `verify` skill'in kendi "İnsan onayı — her zaman son adım" kuralı).
   Yeni bir eylem gerekmiyor, sadece bu koşumda yanlış-pozitif kalıp
   olarak elendiğini kayda geçiriyorum.

## Koşum 4 — 2026-09-26

**Görev sayısı:** 29 (biriken: 5 — `koordinator-dashboard-ucu`,
`profil-sayfasi-kanit-dokumu`, `public-profil-ve-dogrulama-sayfalari`
+ önceki koşumdan sonra tamamlanan 2 görev)
**Toplam bulgu (son 5 görev):** 16

### Kategori dağılımı (kaç görevde tekrarladı, son 5 görev)
| Kategori | Bulgu | Farklı görev |
|---|---|---|
| correctness | — | 4/5 |
| test-gap | — | 3/5 |
| readability | — | 3/5 |
| architecture | — | 2/5 |
| reliability | — | 2/5 |

Şiddet: 5 medium, 11 low — kritik/high yok (bu 5 görevde red-team hiç `block` vermedi).

### Sıcak dosya
`backend/app/api/public.py` — 6 bulgu, 2 farklı görevde (`public-profil-endpoint`, `public-dogrulama-linki`). Tek görevden değil, kronik.

### Tekrar eden gerçek kök neden (bu koşumun somut bulgusu)
Bu oturumda **3 ayrı görevde** (koordinator-dashboard-ucu, profil-sayfasi-kanit-dokumu, public-profil-ve-dogrulama-sayfalari) **aynı sınıf correctness hatası** canlı olarak tekrarladı: backend'de nullable (`Optional`/`| None`) olan bir alan (`ended_on_snapshot`, `started_on_snapshot`, `institution_name`, `attestor_organization`, `public_token`) frontend'de TypeScript'te non-null tiplenmiş ve null-safe render edilmemişti — `new Date(null)` → "Invalid Date" veya literal "null" metni kullanıcıya sızma riski. Her seferinde `red-team` (veya orkestratörün kendi review'u) bunu buluyor, ama `atdd`/`test-copilot` bunu ÖNCEDEN yakalamıyor.

**Eylem 1 (atdd kontrol listesine):** `atdd.md` bir backend response şeması içeren bir AC yazarken, backend modelindeki her `Optional`/`| None` alan için Davranış Sözleşmesi'nde açıkça "bu alan null gelebilir, UI'da nasıl gösterilir" satırı ZORUNLU olsun — boş bırakılamaz. Bu, `atdd` skill'inin 4a adımındaki mevcut "her satır kendi testini alır" kuralına ek, spesifik bir nullable-alan maddesi.

**Eylem 2 (test-copilot kontrol listesine):** `test-copilot`'un mevcut "sınır/özel değer" kuralına (sayısal validasyon için `inf`/`nan` zorunluluğu) paralel bir madde eklensin: backend şeması nullable bir alan içeriyorsa, test dosyasında o alan için MUTLAKA bir `null` değerli render testi de yazılmalı (happy-path'in yanına, ayrı bir test).

### Kronik dosya notu (aksiyon değil, gözlem)
`backend/app/api/public.py` iki farklı görevde bulgu topladı — bir sonraki bu dosyaya dokunan görevde `refactor` skill'i düşünülmeli (henüz zorunlu değil, tek bir somut ölçülebilir tekrar/karmaşıklık bulgusu yok, sadece "bulgu sıklığı" sinyali).

### verify_report.md gate notu (aksiyon gerekmiyor, beklenen davranış)
"İnsan onayı → PENDING" ve "AI code review → PENDING" TÜM görevlerde tekrarlıyor — bu bir arıza değil, bu iki gate'in tanımı gereği (`verify` insan onayını asla veremez, AI code review ayrı `red-team` adımına devredilir). Aksiyon gerekmiyor.

"Güvenlik taraması → MISSING" 2 eski görevde (`yet-13-auth-ekranlari`, `yet-14-talent-profil-yetkinlik`) tekrarlamış — bu oturumun görevlerinden değil, düşük öncelik, veri yetersiz (2/5 eşiği zar zor karşılıyor, ayrıca eski) — "henüz kalıp değil" olarak not düşülüyor, aksiyon önerilmiyor.

---

## Koşum 3 — 2026-09-25

**Görev sayısı:** 24 (biriken: 5 — `yet-69-degerlendirme-formu-semasi`,
`yet-70-attestation-verified-experience-uretimi`,
`yet-71-skillsignal-turetme-tam-kapsam`, `yet-72-attestation-revoke`
+ bir önceki koşumdan sonra tamamlanan görevlerden biri)
**Toplam bulgu:** 87

### Kategori dağılımı (kaç görevde tekrarladı)
| Kategori | Bulgu | Farklı görev |
|---|---|---|
| correctness | 19 | 16 |
| test-gap | 15 | 13 |
| reliability | 13 | 13 |
| security | 10 | 8 |
| architecture | 8 | 7 |
| maintainability | 6 | 5 |
| readability | 5 | 4 |

### Şiddet
critical: 4, high: 9, medium: 28, low: 46

### Sıcak dosyalar (2+ farklı görevde bulgu alan)
- `backend/app/services/engagement.py` — 8 bulgu / 3 görev
- `backend/app/services/authorization.py` — 4 bulgu / 4 görev
- `backend/tests/authorization/test_matrix.py` — 4 bulgu / 2 görev

### Bu koşumda (yet-69..72) canlı gözlemlenen somut tekrarlar
1. **Migration başlık hatası 2 kez (yet-70, yet-71):** yet-70'te `revision`/
   `down_revision` modül değişkenleri hiç tanımlanmamıştı (sadece docstring'de
   vardı); yet-71'de `down_revision` yanlış (eski, zaten merge edilmiş) bir
   revizyona işaret ediyordu. İkisi de `alembic upgrade head` çalıştırılana
   kadar fark edilmedi — code-copilot alt-ajanı kendi yazdığı migration'ı hiç
   doğrulamadan "tamamlandı" raporladı.
2. **İsim çakışması/gölgeleme 1 kez ama ciddi (yet-71):** `engagements.py`'de
   iki farklı modülden aynı isimle (`InvalidSkillError`) import — biri
   diğerini sessizce gölgeledi, yanlış except bloğu yanlış exception'ı
   yakalıyordu (422 yerine 500'e yol açardı). `ruff`'ın F811 kuralı bunu
   yakaladı ama SADECE verify adımında `ruff check .` çalıştırıldığı için —
   code-copilot kendi yazdığı dosyayı lint etmemişti.
3. **Test-copilot'un `session.expunge_all()` yanlış kullanımı 2 kez (yet-71
   GET-signals testi, yet-72'de 26 satır):** Projenin gerçek konvansiyonu
   (client/session aynı SQLAlchemy session'ı paylaşır) hiç `expunge_all()`
   kullanmıyor, ama test-copilot alt-ajanları bunu "güvenlik" amaçlı ekleyip
   `DetachedInstanceError`'a yol açtı.

### Önerilen somut eylemler
1. **`code-copilot` skill'inin dispatch prompt şablonuna ekle:** "Migration
   dosyası yazdıysan, rapor vermeden ÖNCE kendi Bash aracınla `alembic heads`
   çalıştır — TEK head dönmeli ve senin yazdığın revision olmalı. Ayrıca
   `ruff check <değiştirdiğin/oluşturduğun dosyalar>` çalıştır, sıfır hata
   olmalı. İkisi de geçmeden 'tamamlandı' raporu verme." (Gerekçe: migration
   başlık hatası 2/4 son görevde tekrarladı, isim çakışması verify'a kadar
   fark edilmedi — ikisi de alt-ajanın kendi ürettiği dosyayı çalıştırmadan
   rapor vermesinden kaynaklanıyor, ucuz bir self-check ile yakalanabilirdi.)
2. **`test-copilot` skill'inin dispatch prompt şablonuna ekle:** "`session.
   expunge_all()`/`session.expire_all()` KULLANMA — bu projede `client` ve
   `session` fixture'ları AYNI SQLAlchemy session'ı paylaşır (conftest.py),
   expunge etmek nesneleri detach eder ve `DetachedInstanceError`'a yol açar.
   İhtiyacın olan güncel veriyi `session.refresh(obj)` ile veya doğrudan
   yeniden sorgu ile al." (Gerekçe: 2 görevde, toplam 27+ satırda tekrarladı.)

---

## Koşum 1 — 2026-09-22

**Görev sayısı:** 7 (`yet-1-ilk-migration`, `yet-2-yetkilendirme-cekirdegi`,
`yet-3-yetkilendirme-test-iskeleti`, `yet-5-outbox-worker`,
`yet-8-institution-koordinator-ogrenci-bagi`,
`yet-9-organization-domain-dogrulama`, `yetkin360-faz0-temel-kurulum`)
**Toplam bulgu:** 25

### Kategori dağılımı
| Kategori | Bulgu | Kaç farklı görevde |
|---|---|---|
| test-gap | 8 | 6/7 |
| reliability | 5 | 5/7 |
| architecture | 4 | 3/7 |
| correctness | 3 | 3/7 |
| risk | 2 | 2/7 |
| security | 2 | 2/7 |
| scope | 1 | 1/7 |

### Şiddet dağılımı
critical: 1, high: 2, medium: 9, low: 13 — ağırlık hâlâ medium/low'da, kritik
oranı düşük. Trend değerlendirmesi için henüz yeterli koşum yok (bu ilk koşum).

### Sıcak dosya
Hiçbiri henüz kronik değil — en çok bulgu alan dosyaların tümü tek bir
görevden geliyor (`test_matrix.py`, `outbox_worker.py`, `docker-compose.yml`,
ilk migration dosyası, `test_authorization.py`). Mimari sinyal için henüz
erken.

### Tekrar eden kategoriler ve somut eylemler

**1. `test-gap` — 6/7 görevde tekrarladı.**
`yet-9`'un kendi red-team bulgusu somut bir örnek verdi: testler tam hata
koduna değil gevşek substring/OR kontrolüne dayanıyordu (`"domain" in
str(data).lower() or "verified" in ...`) — implementasyon yanlış ama benzer
kelime içeren bir mesaj döndürse bile test yeşil kalırdı. Bu, `testing.md`
kuralının ("assert'i gevşetme") tekrar tekrar ihlal edildiğini gösteriyor —
Haiku alt-ajanlarının kendi ürettiği testlerde sistematik bir eğilim.
→ **Eylem: `test-copilot` skill'ine madde eklendi** — dispatch prompt'una
"Davranış Sözleşmesi tablosundaki hata kodlarını/değerlerini `assert x ==
tam_değer` ile doğrula, asla `in`/`or` ile gevşek substring kontrolü yazma"
kuralı eklenmesi önerildi (kullanıcı onayı bekleniyor, bkz. altta).

**2. `reliability` — 5/7 görevde tekrarladı.**
`yet-9`'da canlı olarak yakalanan somut örnek: bir servis fonksiyonu
(`verify_domain()`) DB alanlarını yalnızca `session.flush()` ediyordu,
`commit()` etmiyordu; gerçek `get_session` (app/core/deps.py) her
exception'da `rollback()` yapıyor — bu yüzden hata yollarında (409/400)
flush edilmiş ama commit edilmemiş veri sessizce kayboluyordu (rate-limit
korumasının devre dışı kalması sonucunu doğurdu). Bu kalıp, "bir fonksiyon
içinde hem başarı hem hata yolu var, hata yolunda partial-write'ın kaderi
ne olacak" sorusunun `atdd`/`plan` aşamasında hiç sorulmadığını gösteriyor.
→ **Eylem: `atdd` skill'inin 4a maddesine (Davranış Sözleşmesi) not
eklenmesi önerildi** — "kısmi başarı"/"hiçbir şey yapılamadı" satırları
doldurulurken, bu projenin `get_session`'ının her exception'da rollback
yaptığı hatırlatılsın; bir servis fonksiyonu hem DB yazıp hem de sonradan
hata fırlatabiliyorsa, o yazının hangi commit sınırında kalıcı olacağı
açıkça yazılsın (kullanıcı onayı bekleniyor, bkz. altta).

**3. `architecture` (3/7) ve `correctness` (3/7)** — 3 görev henüz "kalıp"
için düşük eşik (skill kuralı: az veriyle kalıp uydurma). Not düşüldü,
somut eylem üretilmedi — bir sonraki koşumda 4+ görevde tekrarlarsa
değerlendirilecek.

### `verify_report.md` tekrar eden gate sonuçları
`AI code review` ve `İnsan onayı` gate'leri 4 görevde `PENDING` — bu
**beklenen** durum (bu ikisi tasarım gereği `verify` adımında hep pending
kalır, `red-team`/kullanıcı onayı ayrı adımlarda kapanır), süreç kusuru
değil. Aksiyon gerekmiyor.

### Uygulanan eylemler (kullanıcı onayıyla, 2026-09-22)
1. ✅ `test-copilot` SKILL.md'ye: "gevşek substring/OR assert yasak, tam değer
   eşleştir" kuralı eklendi (adım 1 + dispatch prompt şablonu).
2. ✅ `atdd` SKILL.md'nin 4a maddesine: "bu projede `get_session` her
   exception'da rollback yapar — davranış sözleşmesi doldurulurken
   partial-write'ın hangi commit sınırında kalıcı olacağı sorulsun" notu
   eklendi.

---

## Koşum 2 — 2026-09-24

**Görev sayısı:** 19 (Koşum 1'deki 7 + `engagement-model-olusturma-ucu`,
`engagement-durum-makinesi-transitions-ucu`,
`koordinator-onay-gecisi-yetkilendirme-testleri`,
`engagement-task-deliverable`, `yet-82-83-evidence-upload-url`,
`yet-10-skill-search`, `skillsignal-self-claim-uretimi`,
`yet-7-user-talent-profili`, `yet-11-skill-claims`,
`yet-12-frontend-kabuk`, `yet-13-auth-ekranlari`,
`yet-14-talent-profil-yetkinlik`)
**Toplam bulgu:** 72

### Kategori dağılımı
| Kategori | Bulgu | Kaç farklı görevde |
|---|---|---|
| correctness | 15 | 12/19 |
| test-gap | 14 | 12/19 |
| reliability | 12 | 12/19 |
| security | 8 | 6/19 |
| architecture | 7 | 6/19 |
| maintainability | 5 | 4/19 |
| risk | 3 | 3/19 |
| performance | 2 | 2/19 |
| scope | 2 | 2/19 |
| readability | 2 | 2/19 |

### Şiddet dağılımı
critical: 4, high: 7, medium: 22, low: 39 — kritik/high oranı (~15%)
Koşum 1'e (~%12) göre hafif arttı ama görev sayısı da neredeyse 3 katına
çıktı (7→19); oransal olarak (11/25→11/72) aslında **düştü** (~%44→~%15) —
süreç iyileşiyor, daha fazla bulgu daha erken (test-copilot/code-copilot
turlarında) yakalanıp kapanıyor.

### Sıcak dosyalar (birden fazla görevde tekrar eden)
- **`backend/app/services/engagement.py`** — 8 bulgu / 3 görev
  (`engagement-model-olusturma-ucu`, `engagement-durum-makinesi-transitions-ucu`,
  `engagement-task-deliverable`). Mimari sinyal: bu dosya Engagement'ın
  hem oluşturma hem durum makinesi hem Task/Deliverable mantığını taşıyor —
  her yeni PLAN 2.x maddesi buraya ekleme yapıyor, dosya büyüdükçe bulgu
  yoğunluğu da büyüyor. **Refactor adayı** — kullanıcıya önerilecek,
  otomatik tetiklenmeyecek (dosya hâlâ tek sorumluluk sınırı içinde:
  "engagement yaşam döngüsü", bölünme henüz zorunlu değil ama PLAN 2.10
  — attestation iptali — eklendiğinde tekrar değerlendirilmeli).
- **`backend/tests/authorization/test_matrix.py`** — 4 bulgu / 2 görev.
- **`backend/tests/test_engagement_transitions.py`** — 3 bulgu / 2 görev
  (dosya büyüklüğü — 1466 satıra ulaştı; yeni transition testleri hep
  buraya ekleniyor, `test_engagement_tasks.py`/`test_engagement_deliverables.py`
  gibi ayrı dosyalara bölünme deseni tutarlı uygulanmıyor).

### Tekrar eden kategoriler ve somut eylemler

**1. `correctness` — 12/19 görevde tekrarladı (Koşum 1'de kalıp eşiğinin
altındaydı, şimdi net bir kalıp).**
Bu koşumda iki somut örnek: `koordinator-onay-gecisi-yetkilendirme-testleri`'nde
bir test yanlış principal.kind'ı test ediyordu (fixture zinciri eksikti —
`org_admin_evan` bağımlı değildi, testin "ORG_ADMIN" senaryosu aslında
"ORG_MEMBER" senaryosunu test ediyordu, sonuç kodu doğru ama yanlış
nedenden); `engagement-task-deliverable`'da status-check role-check'ten
önce çalışıyordu (düşük önem ama aynı sınıf: **kontrol sırası** hatası).
→ **Eylem: `test-copilot` SKILL.md'ye madde eklenmesi önerildi** — "Bir
test 'principal X rolündeyken Y olur' iddia ediyorsa, fixture zincirinin
GERÇEKTEN principal.kind'ı X'e çevirdiğini (ara bir `assert
principal.kind == "X"` ile veya kod okuyarak) doğrula — sadece HTTP
sonuç kodunun beklenenle eşleşmesi yeterli değil, YANLIŞ KOD YOLUNDAN
da aynı sonuç gelebilir (bkz. `koordinator-onay-gecisi-yetkilendirme-testleri`
red-team bulgusu)." (kullanıcı onayı bekleniyor, aşağıya bkz.)

**2. `test-gap` — 12/19 görevde tekrarladı (Koşum 1'deki en büyük kalıp
hâlâ birinci sırada, oran benzer: 6/7→12/19).**
Koşum 1'in eylemi (`test-copilot`'a "tam değer eşleştir" kuralı) zaten
uygulandı ve bu koşumda AYNI türde bir yeni bulgu görülmedi — ama YENİ bir
alt-kalıp ortaya çıktı: framework-seviyesi validasyon (FastAPI/Pydantic
zorunlu alan kontrolü) ile uygulama-seviyesi validasyon (handler içi iş
mantığı) arasındaki farkın karıştırılması
(`koordinator-onay-gecisi-yetkilendirme-testleri`'nde "scope-check
validation'dan önce çalışsın" AC'si eksik-alan senaryosunda teknik olarak
test edilemez çıktı — Pydantic zorunlu alanı handler'a hiç girmeden 422
ile reddediyor).
→ **Eylem: `threat-model` SKILL.md'ye madde eklenmesi önerildi** —
"'Scope-check X'ten önce çalışmalı' türünde bir AC-S üretirken, X'in
FastAPI/Pydantic seviyesinde mi (zorunlu alan, tip) yoksa uygulama
seviyesinde mi (enum/iş kuralı) kontrol edildiğini ayırt et — framework
seviyesi kontroller handler'a hiç girmeden çalışır, bu AC'ler için
kullanılamaz; sadece uygulama-seviyesi (handler-içi) kontrollerle sıra
testi anlamlıdır." (kullanıcı onayı bekleniyor, aşağıya bkz.)

**3. `reliability` — 12/19 görevde tekrarladı (oran sabit: 5/7→12/19,
kalıp doğrulandı).**
Koşum 1'in eylemi (`atdd`'ye partial-write/commit-sınırı notu) uygulandı.
Bu koşumda tekrar eden asıl örnek farklı bir alt-tür: kontrol SIRASI
(status-check vs role-check, `engagement-task-deliverable` red-team
bulgusu) — az önce madde 1'de kapsandı, ayrı eylem üretilmedi (aynı kök
neden, tek eylem yeterli).

**4. `security` (6/19) ve `architecture` (6/19)** — Koşum 1'de "az veri"
diye ertelenmişti, şimdi 6 görevde tekrarlıyor ama HENÜZ tek bir somut
eylem çıkaracak kadar homojen değil (security bulguları 5 farklı görevde
5 farklı konu — CSP, presigned-URL Content-Length, rate-limit, vb.).
Not düşüldü, bir sonraki koşumda (24+ görev) tekrar değerlendirilecek.

### `verify_report.md` tekrar eden gate sonuçları
`AI code review` ve `İnsan onayı` → `PENDING` (15/17 okunabilen görev) —
Koşum 1'deki gibi **beklenen** durum, tasarım gereği. `Güvenlik taraması`
2 görevde `MISSING` (`yet-13-auth-ekranlari`, `yet-14-talent-profil-yetkinlik`) —
bu ikisi frontend-only görevler, `security-scan` skill'i o dönemde
backend-odaklı çalışıyordu. Aksiyon: not düşüldü, frontend görevlerinde
`security-scan`'in NPM/JS tarafını da kapsayıp kapsamadığı bir sonraki
frontend görevinde teyit edilmeli — henüz genel bir eylem üretilmiyor (2
görev, düşük eşik).

### Uygulanan eylemler (kullanıcı onayıyla, 2026-09-24)
1. ✅ `test-copilot` SKILL.md'ye: "principal.kind'ın gerçekten iddia
   edilen role döndüğünü doğrula" kuralı eklendi (dispatch prompt şablonu,
   "ZORUNLU" bloğu).
2. ✅ `threat-model` SKILL.md'ye: "framework-seviyesi vs uygulama-seviyesi
   validasyon ayrımı" notu eklendi (adım 3, AC-S üretim kuralı).

---

## Koşum 5 — 2026-09-27

**Görev sayısı:** 32 (biriken: 8 — `koordinator-dashboard-frontend`,
`seed-verisi-ogrenci-kurum-engagement` + bu koşumun kapsadığı 6 diğer görev)
**Toplam bulgu (son 8 görev):** 28

### Kategori dağılımı (kaç görevde tekrarladı, son 8 görev)
| Kategori | Bulgu | Farklı görev |
|---|---|---|
| test-gap | 6 | 6/8 |
| reliability | 6 | 4/8 |
| correctness | 5 | 5/8 |
| architecture | 3 | 3/8 |
| readability | 3 | 3/8 |
| scope | 3 | 3/8 |
| maintainability | 2 | 2/8 |

Şiddet: 1 high, 9 medium, 18 low.

### Sıcak dosya
`backend/app/api/public.py` — 6 bulgu, 2 farklı görevde (kronik, Koşum 4'te de aynı dosya işaretlenmişti — tekrar sinyali güçleniyor).

### Tekrar eden gerçek kök neden (bu koşumun somut bulgusu)
**Bu SESSION içinde iki ayrı görevde (`koordinator-dashboard-frontend` ve `seed-verisi-ogrenci-kurum-engagement`) AYNI test hatası canlı olarak iki kez tekrarladı:** bir alt-ajan `unittest.mock.patch("modül.fonksiyon", ...)` çağırırken hedefi fonksiyonun **tanımlandığı** modüle (`app.services.X.fonksiyon`) verdi, ama test edilen kod o fonksiyonu `from app.services.X import fonksiyon` ile **kendi namespace'ine import etmişti** — patch hiç etkisiz kaldı, mock hiç devreye girmedi, test yanlışlıkla "geçti" göründü (gerçekte hiçbir şeyi kanıtlamıyordu). İkisinde de orkestratör (ben) testleri gerçekten çalıştırıp bu sahte-geçişi yakaladı, ama bu iki kez pahalı bir ek tur gerektirdi.

İkinci tekrar eden kök neden: **`reliability` bulgularının çoğu (koordinator-dashboard-frontend'deki `SessionExpiredError` ele alınmaması, seed-verisi'deki genel `except Exception: continue`) "hata durumunda ne olacağı" atdd.md'nin Davranış Sözleşmesi'nde yazılı olsa bile code-copilot'un ilk turunda atlanmış, sadece red-team'in ikinci bağımsız bakışında yakalanmış.**

### Uygulanan eylemler (kullanıcı onayıyla)
1. ✅ `test-copilot` SKILL.md'ye MUTLAK eklenecek kural: "`unittest.mock.patch` hedefi ASLA fonksiyonun tanımlandığı modül değil, test edilen kodun onu import ettiği (`from X import Y` sonrası kendi namespace'i) modül olmalı — hedefi seçmeden önce test edilen dosyanın import satırlarını kontrol et."
2. ✅ `code-copilot` SKILL.md'nin Definition of Done'ına ekleme: "Davranış Sözleşmesi tablosunun HER 'hata durumunda ne olur' satırı için, kodda bu spesifik durumu ele alan bir `if`/`except` dalı var mı diye kendi kendine çapraz kontrol et (implementasyonu yazdıktan hemen sonra, verify'a bırakmadan) — özellikle 'genel `except Exception`' ile birden fazla farklı hata durumunu aynı davranışa indirgeme YASAK, her durumun kendi dalı olmalı."

Not: `backend/app/api/public.py` sıcak dosya sinyali artık 2 koşumdur tekrarlıyor — bir sonraki `public.py`'ye dokunan görevde `refactor` skill'i özellikle bu dosyaya bakmalı, kullanıcıya ayrıca önerilecek.
