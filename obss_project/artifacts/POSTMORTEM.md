# POSTMORTEM

Görevler arası tekrar eden kalıpları takip eder. Üzerine eklenir, silinmez.

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
