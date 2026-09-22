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
