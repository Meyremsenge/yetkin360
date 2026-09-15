# Güvenlik Açığı Bildirimi

Yetkin360'ın güvenliğini ciddiye alıyoruz. Bu platform öğrencilerin kişisel
verilerini, kurumların değerlendirmelerini ve doğrulanmış deneyim kayıtlarını
tutar — bir açığın sonucu yalnız teknik değil, **kişiseldir**.

> Bu dosya **açık bildirimi** içindir. Güvenlik mimarisi (OWASP analizi, dosya
> güvenliği, saldırı senaryoları) için → [docs/SECURITY.md](docs/SECURITY.md)

---

## Açık bulduysanız

**Lütfen herkese açık bir GitHub issue AÇMAYIN.**

Bunun yerine:

1. GitHub üzerinden **Security → Report a vulnerability** (private advisory), veya
2. E-posta ile bildirin.

> ❓ AÇIK SORU: Güvenlik bildirimi için iletişim adresi henüz belirlenmedi.
> Ekip bir adres (`guvenlik@...` veya kişisel) kararlaştırdığında buraya yazılacak.
> O zamana kadar GitHub private advisory kullanın.

### Bildiriminizde şunlar olsun

- Açığın türü ve etkilenen bileşen (uç, dosya, ekran)
- Yeniden üretme adımları — mümkünse minimal
- Etkisi: hangi veriye kim erişebiliyor
- Varsa ekran görüntüsü veya kısa kayıt
- Size nasıl ulaşabileceğimiz

Türkçe veya İngilizce bildirim kabul edilir.

---

## Bizden bekleyebilecekleriniz

| Aşama | Süre |
|---|---|
| İlk yanıt (aldık) | 72 saat |
| İlk değerlendirme (ciddiyet, doğrulama) | 7 gün |
| Düzeltme veya yol haritası | 30 gün |
| Açıklama (sizinle birlikte) | Düzeltme sonrası |

> **Not:** Bu proje şu anda bir hackathon takvimiyle yürüyor (Eylül–Ekim 2026).
> Yoğun dönemde yanıt süreleri uzayabilir — ama her bildirime yanıt verilir.

**Söz veriyoruz:**
- İyi niyetli bildirim için yasal işlem başlatmayız.
- Katkınızı, istemezseniz aksini belirtmediğiniz sürece, düzeltme notlarında
  adınızla anarız.
- Sizi süreç boyunca bilgilendiririz.

---

## Kapsam

### Kapsam içi

- Yetkilendirme atlatma (**BOLA** — başka kiracının verisine erişim)
- Kimlik doğrulama ve oturum yönetimi açıkları
- Alan seviyesi veri sızıntısı (ör. `private_note`'un öğrenciye görünmesi)
- Injection (SQL, komut, şablon)
- XSS, CSRF, SSRF
- Dosya yükleme açıkları (tip atlatma, path traversal, depolama erişimi)
- Public doğrulama linkinin (`/v/{token}`) kötüye kullanımı
- **Sahte tanıklık üretme** — platformun güven modelini atlatan her yol
- Sır sızıntısı (repoda veya çalışan sistemde)

> **Özellikle ilgilendiğimiz:** Güven modelini atlatan senaryolar. Birinin kendi
> kendini doğrulayabildiği, tanıklığı olmayan bir deneyimi doğrulanmış
> gösterebildiği, veya `COMPETENCE` ön koşullarını atlatabildiği bir yol
> bulursanız — bu bizim için en kritik bulgu türüdür.

### Kapsam dışı

- Otomatik tarayıcı çıktısı (elle doğrulanmamış)
- Kullanıcı etkileşimi gerektiren, gerçekçi olmayan senaryolar
- Güvenlik başlığı eksikliği (somut bir istismar gösterilmeden)
- Rate limit'in yalnız "daha sıkı olabilirdi" eleştirisi
- Sosyal mühendislik, fiziksel erişim
- Kendi yerel kurulumunuzdaki `.env.example` varsayılanları
- **Bilinçli olarak ertelendiği belgelenmiş eksikler** —
  [docs/SECURITY.md](docs/SECURITY.md) §9

Son madde önemlidir: MVP'de virüs taraması, ayrı içerik domain'i, RLS ve MFA
**bilinçli olarak yoktur** ve gerekçeleriyle belgelenmiştir. Bunları bildirmeniz
gerekmez — ama listede olmayan bir eksik bulursanız, bildirin.

---

## Demo ortamı uyarısı

Bu bir **hackathon MVP'sidir**. Canlı demo ortamı yalnız seed verisi ve ekip
hesapları içerir. Gerçek kişisel veri girmeyin.

Test yaparken:
- Yalnız kendi oluşturduğunuz hesaplarla çalışın.
- Servis dışı bırakma (DoS) denemesi **yapmayın**.
- Başkasının verisine eriştiğinizi fark ederseniz **durun**, veriyi kaydetmeyin,
  hemen bildirin.

---

## Teşekkür

Bildirimde bulunanlar burada anılır.

*(Henüz bildirim yok.)*
