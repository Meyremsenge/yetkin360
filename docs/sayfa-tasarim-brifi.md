# Yetkin360 — Ekran ekran tasarım brifi (v2)

> **Baz alınan tasarım:** Koddaki **mevcut** görsel dil — `/` (landing, "Resmi Sicil Gazetesi" yönü) ve 5 auth sayfası (`AuthLayout`, "Sicil Gişesi" yönü) + `globals.css` token'ları + `ChainProgress` / `VerifiedSeal` bileşenleri.
> `planfrontend.md` **baz alınmaz**. Çeliştiği yerde bu dosya geçerlidir.
>
> **Kullanım:** Her ekran tasarımına **Bölüm 1–5** (temel, bileşenler, hizalama, animasyon, kabuk) + ilgili **sayfa bölümü** birlikte verilir.
> **Veri kuralı:** Yalnız burada listelenen veri alanları kullanılır. Olmayan veri (istatistik, fotoğraf, puan, yüzde, sayaç) çizilmez.
> **Ölçüler:** px cinsinden. Parantez içinde Tailwind karşılığı (geliştirici için).

---

## İçindekiler

1. Temel: renk, yazı, boşluk, ızgara, köşe, çizgi, ikon
2. Bileşen kataloğu (buton, form, kart, rozet, uyarı, dialog, tablo, zincir, mühür…)
3. Hizalama ve yerleşim kuralları (butonlar nereye konur)
4. Animasyon sistemi
5. Uygulama kabuğu — **sol navbar**, mobil üst bar, uyarı şeritleri
6. Sayfalar (1–21)
7. Navigasyon haritası (hangi buton nereye gider — tek tablo)
8. Açık noktalar (kodda eksik bağlantılar — tasarımcı bilsin)

---

## 1. Temel

### 1.1 Renk paleti (kodda tanımlı, `globals.css`)

| Ad (tasarım) | Token | Hex | Nerede kullanılır |
|---|---|---|---|
| **Kâğıt** | `background` | `#FAF8F5` | Sayfa zemini, içerik alanı |
| **Kart** | `card` | `#FEFEFD` | Kart, tablo gövdesi, dialog, dropdown, aktif menü öğesi |
| **Kum** | `sand` | `#EBE5DA` | **Sol navbar zemini**, auth marka paneli, vurgulu bilgi kutusu |
| **Soluk** | `muted` | `#EFECE7` | Nötr buton, tablo başlık satırı, hover zemini, nötr rozet |
| **Çizgi** | `border` | `#E1DCD6` | Tüm 1px çizgiler, kart/input kenarı, bölüm ayırıcı |
| **Mürekkep** | `foreground` | `#221F1B` | Ana metin, başlıklar |
| **İkincil metin** | `muted-foreground` | `#625C55` | Etiket, açıklama, pasif menü, tarih |
| **Çam yeşili** | `success` / `verified` | `#265445` | **Birincil buton**, doğrulanmış/mühür, odak halkası, link hover |
| **Aşı boyası** | `warning` | `#8F5A14` | Bekleyen, onay bekliyor, uyarı |
| **Tuğla** | `destructive` | `#A13B2B` | Hata, red, iptal, geri çekme, çıkış |

**Türetilmiş zeminler (renk %10 + kâğıt):**

| Ad | Hex (yaklaşık) | Kullanım |
|---|---|---|
| Çam zemini (`success/10`) | `#E5E8E3` | Doğrulandı rozeti, başarı uyarısı, outline buton hover |
| Aşı zemini (`warning/10`) | `#EFE8DE` | Bekliyor rozeti, uyarı şeridi |
| Tuğla zemini (`destructive/10`) | `#F1E5E1` | Hata rozeti, hata uyarısı |
| Uyarı kenarı | renk %30 | Uyarı kutularının 1px kenarı |

**Kontrast (WCAG, hepsi ≥ 4.5:1):** mürekkep/kâğıt 15.5 · ikincil/kâğıt 6.2 · çam/kâğıt 8.1 · kâğıt yazı/çam buton 8.5 · aşı/zemini 5.4 · tuğla/zemini 6.2.

**Renk oranı:** ekranın ~%85'i kâğıt + kart + çizgi + mürekkep, ~%10 kum/soluk, ~%5 renk. Birincil buton da çam yeşili olduğu için **bir ekranda en fazla 1 dolu çam buton** olur; geri kalan aksiyonlar outline/nötr.

**Yasak:** mor, mavi, indigo, pembe, gradyan, blob/glow, cam efekti, emoji, stok görsel/illüstrasyon, karanlık mod, kalın gölge.

### 1.2 Yazı tipleri (kodda yüklü, `layout.tsx`)

| Rol | Font | Ağırlık |
|---|---|---|
| Başlık, logo, zincir adımı, kişi adı, persona başlığı | **Source Serif 4** | 500 / 600 (logo bold) |
| Arayüz, form, buton, tablo, gövde | **IBM Plex Sans** | 400 / 500 / 600 |
| Slogan satırı, zincir numarası, tarih damgası, sicil/doğrulama no, slug, TXT kaydı, destek kodu | **IBM Plex Mono** | 400 |

**Ölçek (mevcut koddan):**

| Stil | Boyut / satır | Font | Örnek kullanım |
|---|---|---|---|
| Display | 48/56 (mobil 36/44) | Serif 600 | Landing hero başlığı |
| H1 | 32/40 | Serif 600 | Sayfa başlığı |
| H2 | 24/32 | Serif 500 | Bölüm başlığı |
| H3 | 20/28 | Serif 500 | Kart başlığı, persona |
| Lead | 18/28 | Sans 400, ikincil | Hero açıklaması, bölüm girişi |
| Gövde | 15/24 | Sans 400 | Paragraf, liste |
| Arayüz | 14/20 | Sans 400–500 | Buton, input, menü, tablo |
| Küçük | 13/18 | Sans 400 | Yardım metni, meta |
| Etiket | 12/16 | Sans 500 | Form etiketi üstü, rozet, menü grup başlığı (BÜYÜK HARF **yok**) |
| Mono | 14/20 ve 12/16 | Mono 400 | Slogan, tarih damgası, kodlar |

- Sayılar `tabular-nums`. Tarih: "12 Eylül 2026"; listelerde göreli ("3 gün önce") + hover'da tam tarih.
- Paragraf genişliği en fazla 65 karakter (~640px).

### 1.3 Boşluk, ızgara, kırılım noktaları

- Boşluk birimi **4px**. Kullanılan adımlar: 4 · 8 · 12 · 16 · 24 · 32 · 40 · 48 · 64.
- Landing/public: içerik genişliği **1152px** (`max-w-6xl`), yan boşluk 32px (mobil 16px). Bölüm dikey boşluğu **64px** (`py-16`), bölümler arası 1px çizgi.
- Uygulama içi: navbar 248px + içerik alanı; içerik genişliği **liste/panel 1040px**, **detay/form 880px**, **dar form 560px**. İçerik yan boşluğu 40px (tablet 24, mobil 16), üst boşluk 32px.
- Kırılım: **mobil < 768**, **tablet 768–1023**, **masaüstü ≥ 1024** (navbar burada görünür), geniş ≥ 1440.
- Kart iç boşluğu **24px** (mobil 16). Kartlar arası 16–24px.

### 1.4 Köşe, çizgi, gölge

| Öğe | Köşe |
|---|---|
| Buton, input, select, menü öğesi, uyarı kutusu | **6px** (`rounded-md`) |
| Kart, dialog, dropdown, tablo çerçevesi | **8px** (`rounded-lg`) |
| Rozet, avatar, zincir dairesi, mühür | tam yuvarlak |

- Ayrım **gölgeyle değil, 1px `#E1DCD6` çizgiyle** yapılır.
- Gölge **yalnız** üst katmanlarda (dropdown, dialog, toast, mobil çekmece): `0 8px 24px -12px rgba(34,31,27,0.25)`.
- Landing'deki sertifika kartı **−1° eğik** durur (mevcut). Bu "belge masaya bırakılmış" hissi, yalnız sertifika/mühür kartlarında kullanılır.

### 1.5 İkonlar

- Set: **lucide** (1.5px çizgi). Boyut: menüde/butonda **16px**, başlık yanında **20px**, boş durumda **32px** (ince). *(Not: `lucide-react` henüz pakette yok; kurulması onay ister.)*
- İkon ile metin arası **8px**. Süs ikonu yok; her ikon bir işlevi anlatır.
- Önerilen eşleşme: Çalışmalarım `briefcase` · Profil `user-round` · Herkese açık profil `globe` · Kuruluş paneli `building-2` · Kurum paneli `landmark` · Kurum doğrulama `shield-check` · Yetkinlik yönetimi `tags` · Çıkış `log-out` · Kanıt yükle `upload` · Kopyala `copy` · Geri `arrow-left` · Dış link `arrow-up-right` · Menü `menu` · Kapat `x` · Uyarı `alert-triangle` · Bilgi `info` · Kilit `lock`.

---

## 2. Bileşen kataloğu

### 2.1 Butonlar

Mevcut landing CTA'ları baz alınmıştır (dolu çam + çam outline).

| Varyant | Zemin | Metin | Kenar | Hover | Basılı (active) | Ne için |
|---|---|---|---|---|---|---|
| **Birincil** | `#265445` çam | `#FAF8F5` kâğıt, 500 | yok | opaklık %90 | 1px aşağı kayma, opaklık %85 | Sayfanın **tek** ana aksiyonu: Kayıt Ol, Giriş Yap, Kaydet, Gönder, Onayla |
| **Outline (ikincil)** | şeffaf | `#265445` çam, 500 | 1px çam | zemin çam %10 (`#E5E8E3`) | 1px aşağı | Ana aksiyonun yanındaki alternatif: "Örnek doğrulamayı incele", "Profili gör" |
| **Nötr** | `#EFECE7` soluk | mürekkep, 500 | 1px çizgi | zemin kum `#EBE5DA` | 1px aşağı | Yardımcı aksiyon: Kriter Ekle, Ekle, Linki kopyala, İptal (formda) |
| **Hayalet** | şeffaf | ikincil metin | yok | zemin soluk, metin mürekkep | — | Dialog'da "Vazgeç", tablo satır menüsü, ikon buton |
| **Tehlikeli** | `#A13B2B` tuğla | kâğıt, 500 | yok | opaklık %90 | 1px aşağı | **Yalnız dialog içindeki son onay**: "Reddet", "İptal Et", "Geri Çek" |
| **Tehlikeli outline** | şeffaf | tuğla, 500 | 1px tuğla %40 | zemin tuğla %10 | 1px aşağı | Listede/aksiyon çubuğunda tetikleyici: Reddet, İptal Et, Geri Çek, Kaldır |
| **Metin link** | — | ikincil → hover mürekkep | — | alt çizgi (offset 4px) | — | Üst bar linkleri, geri linki, "Şifremi unuttum" |

**Boyutlar:**

| Boyut | Yükseklik | Yatay iç boşluk | Yazı | Kullanım |
|---|---|---|---|---|
| sm | 32px | 12px | 13px | Tablo satırı, liste öğesi aksiyonları |
| md | 40px | 16px | 14px | Varsayılan (formlar, başlık aksiyonu, dialog) |
| lg | 48px | 24px | 16px | Landing hero CTA, auth formu gönder butonu |

**Durumlar (her varyant için çizilecek):**
- **Odak (klavye):** 2px çam dış çizgi, 2px boşluk (`outline-offset-2`) — mevcut landing kuralı.
- **Devre dışı:** opaklık %50, imleç yasak, hover yok.
- **Yükleniyor:** buton genişliği **sabit kalır** (zıplamaz); metin "…yor" haline gelir (ör. "Gönderiliyor…") ve solunda 14px dönen halka. Tıklama kilitli.
- **İkonlu:** ikon solda 16px, 8px boşluk. Yalnız ikonlu butonlar kare (32/40px) ve `aria-label` taşır.

### 2.2 Form öğeleri

- **Etiket:** üstte, 12/16 Sans 500 mürekkep, alanla arası 6px. Opsiyonel alanlarda etiketin sağında ikincil renkle "(opsiyonel)".
- **Input / Select / Textarea:** yükseklik 40px (textarea min 96px), zemin kart `#FEFEFD`, 1px çizgi `#E1DCD6`, köşe 6px, iç boşluk 12px, yazı 14px. Placeholder ikincil metin %70.
  - Hover: kenar `#625C55` %40.
  - Odak: kenar çam + 2px çam halka (%25 opak dış halka). 150ms geçiş.
  - Hata: kenar tuğla; altında 13px tuğla mesaj (`aria-live`), solunda 14px `alert-circle`.
  - Devre dışı: zemin soluk, metin ikincil.
- **Yardım metni:** alanın altında 13px ikincil, 6px boşluk.
- **Alanlar arası:** 16px; form grupları arası 32px + 1px çizgi.
- **Segment seçici (radyo yerine):** yan yana eşit kutular, 40px yükseklik, 1px çizgi; seçili kutu çam kenar + çam %10 zemin + çam metin; klavyede ok tuşlarıyla gezilir. (Değerlendirme puanı, tanıklık türü, çalışma türü için.)
- **Onay kutusu:** 16px kare, 4px köşe, seçili = çam dolgu + kâğıt tik.
- **Şifre alanı:** sağ içte göz ikonu (hayalet ikon buton 32px) — *öneri; kodda yok.*

### 2.3 Kart

- Zemin kart, 1px çizgi, köşe 8px, iç boşluk 24px, gölge yok (mevcut `Card`).
- Kart başlığı H3 serif; başlık–içerik arası 12px. Kart altı aksiyon satırı varsa üstünde 1px çizgi + 16px boşluk, butonlar **sağa** hizalı.
- **Tıklanabilir kart** (liste kartları): hover'da kenar `#625C55` %50'ye koyulaşır + başlık alt çizgisi; gölge/yükselme yok. İmleç el.

### 2.4 Rozetler

Hap şekli, yükseklik 22px, yatay 10px, 12px Sans 500 (mevcut `Badge`). Solunda 6px dolu nokta (durum rengiyle).

| Rozet türü | Zemin | Metin |
|---|---|---|
| Nötr (`default`) | soluk `#EFECE7` | mürekkep |
| Bekliyor (`warning`) | aşı %10 | aşı |
| Doğrulandı (`success`) | çam %10 | çam |
| Hata/Red (`error`) | tuğla %10 | tuğla |

**Çalışma durumu → rozet:**

| Durum | Etiket | Rozet | Zincir adımı |
|---|---|---|---|
| DRAFT | Taslak | Nötr | 1 Beyan (şu an) |
| PENDING_APPROVAL | Onay Bekliyor | Bekliyor | 1 Beyan (bekliyor) |
| ACTIVE | Aktif | Nötr (mürekkep noktalı) | 2 Kanıt (şu an) |
| PENDING_EVALUATION | Değerlendirme Bekliyor | Bekliyor | 3 Tanıklık (bekliyor) |
| EVALUATED | Değerlendirildi | Nötr | 3 Tanıklık (şu an) |
| VERIFIED | Doğrulandı | **Doğrulandı** | 4 tamam |
| RESOLVED | İtiraz Çözüldü | Doğrulandı | 4 tamam |
| REJECTED | Reddedildi | Hata | kırık (1. adımda) |
| CANCELLED | İptal Edildi | Hata | kırık (2. adımda) |
| DISPUTED | İtiraz Edildi | Hata | kırık (4. adımda) |

**Kuruluş güven seviyesi rozeti (`TrustLevelBadge`)** — ham "T1" yerine insan dili + bilgi ikonu (hover/tıkla açıklama):

| Seviye | Etiket | Rozet |
|---|---|---|
| T0 | Kişinin kendi beyanı | Nötr |
| T1 | Doğrulanmamış kuruluş | Bekliyor |
| T2 | Alan adı doğrulanmış | Nötr + küçük tik |
| T3 | Kimliği doğrulanmış kuruluş | Doğrulandı |
| T4 | Kuruluş + üniversite ortak onayı | Doğrulandı |

**Kanıt tarama rozeti:** Taranıyor (Bekliyor + dönen nokta) · Temiz (Nötr + tik — **yeşil değil**, yeşil yalnız doğrulanmış deneyime ait) · Riskli — engellendi (Hata) · Tarama başarısız (Hata).

### 2.5 Uyarı kutusu (Alert) ve şerit

- 1px kenar (renk %30), zemin renk %10, köşe 6px, iç boşluk 12×16px, solunda 16px ikon, metin 14px.
- Türler: **Hata** (tuğla, `alert-circle`) · **Başarı** (çam, `check-circle`) · **Uyarı** (aşı, `alert-triangle`) · **Bilgi** (soluk zemin + çizgi, mürekkep, `info`).
- Hata kutusunda en altta **Destek kodu**: 12px Mono ikincil + 24px kopyala ikonu. Sağda "Tekrar dene" nötr sm buton.
- Sayfa üstü **şerit** (kabuktaki): tam içerik genişliği, sol kenarında 3px renk çizgisi, sağda aksiyon butonu.

### 2.6 Bildirim (toast)

- Sağ alt köşe, alttan 24px / sağdan 24px; genişlik 360px (mobil: alttan tam genişlik −32px).
- Kart zemin, 1px çizgi, gölge (bkz. 1.4), solunda 3px durum rengi çizgisi, ikon + 14px metin + kapat ikonu.
- 4 saniye sonra kendiliğinden kapanır; üzerine gelince süre durur. Hata toast'ları kendiliğinden kapanmaz.
- Kullanılacağı yerler: "Durum güncellendi", "Görev eklendi", "Profiliniz kaydedildi", "Davet kuyruğa alındı" vb. *(Kodda bu mesajlar satır içi; toast'a çevrilmesi önerilir.)*

### 2.7 Dialog

- Ortada, genişlik 480px (geniş: 640px), kart zemin, 8px köşe, 24px iç boşluk, gölge. Arka plan mürekkep %40.
- Yerleşim: **Başlık** H3 serif (üst sol) · sağ üstte kapat ikonu (hayalet 32px) · gövde metni 14px ikincil · alanlar · **alt satır butonları sağa hizalı: [Vazgeç — hayalet] [Ana aksiyon — birincil veya tehlikeli]**, aralarında 8px.
- Esc ve arka plana tıklama kapatır (gönderim sürerken kapatmaz). Odak dialog içinde kilitli; açılınca ilk alana gider.
- Mobilde alttan açılan sayfa (bottom sheet): tam genişlik, üst köşeler 12px.

### 2.8 Dropdown menü

- Kart zemin, 1px çizgi, 8px köşe, gölge, iç boşluk 4px, min genişlik 200px.
- Öğe: 36px yükseklik, 12px yatay boşluk, 16px ikon + 14px metin; hover zemin soluk. Tehlikeli öğe (Çıkış) tuğla metin. Gruplar arası 1px çizgi.

### 2.9 Sekmeler

- Yatay, sola hizalı; altında 1px çizgi boydan boya.
- Sekme: 40px yükseklik, 16px yatay boşluk, 14px Sans 500 ikincil; seçili = mürekkep + altta **2px çam çizgi** (çizgi sekmeler arasında kayarak geçer).
- Sayı varsa sekme adının yanında 12px Mono ikincil: "Görevler 3".
- Mobilde yatay kaydırılabilir, kenarda solma yok (düz kesilir).

### 2.10 Tablo

- Çerçeve: 1px çizgi, 8px köşe, taşma gizli.
- Başlık satırı: zemin soluk `#EFECE7`, 40px, 12px Sans 500 ikincil, sola hizalı (sayılar sağa).
- Satır: 52px, alt çizgi 1px, 14px metin, hücre iç boşluğu 16px. Hover zemin kâğıt `#FAF8F5`. Tıklanabilir satırda sağ uçta 16px `chevron-right` ikincil.
- Aksiyon sütunu **en sağda**, butonlar sm, sağa hizalı, 8px aralık.
- Mobilde (< 768) tablo **kart listesine** döner: her satır bir kart, etiket–değer çiftleri alt alta, aksiyonlar kartın altında sağda.

### 2.11 Yükleme iskeleti, boş durum, hata durumu

- **İskelet:** soluk `#EFECE7` bloklar, 6px köşe, gerçek içeriğin şekliyle (başlık çubuğu, 3 satır, kart). Nabız animasyonu (bkz. 4).
- **Boş durum:** kartın/bölümün içinde sola hizalı; 32px ince ikon (ikincil) → 16px boşluk → başlık 16px Sans 600 → açıklama 14px ikincil (en fazla 2 satır) → 16px boşluk → aksiyon butonu (nötr veya birincil). Ortaya hizalanmış devasa boşluk **yok**.
- **Hata durumu:** Alert (hata) + "Tekrar dene" + destek kodu (bkz. 2.5).

### 2.12 Zincir (`ChainProgress`) — mevcut + genişletme

**Mevcut (landing/auth):** 4 adım yatay (mobilde dikey). Her adım: 32px daire (1px çizgi kenar, içinde Mono 14px numara) + altında Serif 18px etiket. Tamamlanan adım: daire çam dolgu, kâğıt numara, etiket çam.

**Uygulama içi için eklenecek durumlar:**

| Adım durumu | Daire | Numara/ikon | Etiket |
|---|---|---|---|
| Tamamlandı | çam dolgu | kâğıt tik (14px) | çam |
| Şu an (aktif) | 1.5px mürekkep kenar, kart zemin | mürekkep numara | mürekkep, 600 |
| Bekliyor (başkasını bekliyor) | 1.5px aşı kenar, aşı %10 zemin | aşı numara | aşı + altında 12px "Kuruluş bekleniyor" |
| Sırada (henüz değil) | 1px çizgi kenar | ikincil numara | ikincil |
| Kırık | 1.5px tuğla kenar, tuğla %10 zemin | tuğla `x` | tuğla + altında 12px durum ("Reddedildi") |

- Adımlar arası **1px yatay bağlantı çizgisi** (dairenin ortasından): tamamlanan bölüm çam, kalan çizgi rengi. *(Öneri: mevcutta çizgi yok.)*
- Boyutlar: **lg** (landing, detay sayfası: 32px daire, 18px serif etiket) · **sm** (liste kartında mini zincir: 4 adet 8px nokta + aralarında 12px çizgi, etiketsiz, `aria-label` ile).

### 2.13 Mühür (`VerifiedSeal`) — mevcut + genişletme

**Mevcut:** 64px çam dolgu daire, ortada 32px kâğıt tik (2px çizgi); altında isteğe bağlı Serif 24px ad, Mono 14px tarih, Mono 14px sicil no. Boş alan render edilmez (sahte isim yok).

**Boyutlar:**
- **lg (sertifika):** 96px daire; dairenin dışında 4px boşluklu ikinci ince (1px) çam halka; −4° eğik. *(Öneri: çift halka + eğim.)*
- **md (landing kartı):** mevcut 64px.
- **sm (rozet):** 20px daire + 12px tik; liste ve zaman çizelgesinde başlığın yanında.

### 2.14 Diğer küçük bileşenler

- **Avatar:** daire; 32px (navbar), 40px (liste), 64px (profil başlığı). Zemin kum, 1px çizgi, içinde baş harfler Serif 500 mürekkep.
- **Geri linki:** sayfanın en üst solunda, 14px ikincil, solunda 16px `arrow-left`; hover mürekkep + alt çizgi. Altındaki başlıkla arası 16px.
- **Sayfa başlığı (PageHeader):** sol: H1 serif + altında 14px ikincil açıklama/meta (8px). Sağ: aksiyonlar (sağa hizalı, başlığın ilk satırıyla dikey ortalı). Altında 32px boşluk. Mobilde aksiyonlar başlığın altına iner, birincil buton tam genişlik.
- **Sayaç kartı (StatCard):** kart; üstte 12px Sans 500 ikincil etiket, altında 32px Serif 600 sayı (`tabular-nums`), sayı rengi durumla eşleşir (bekleyenler aşı). Trend oku/yüzde **yok**.
- **Kopyalanabilir kod kutusu:** soluk zemin, 1px çizgi, 6px köşe, Mono 13px, sağda kopyala ikon butonu; kopyalanınca ikon 1.5 sn tik'e döner + "Kopyalandı" küçük ipucu.

---

## 3. Hizalama ve yerleşim kuralları (butonlar nereye konur)

Tüm ekranlarda aynı kural seti uygulanır:

1. **Sayfa düzeyi ana aksiyon → başlığın sağı.** (ör. "Yeni çalışma", "Değerlendirme Formu"). Mobilde başlığın altında tam genişlik.
2. **Form gönder butonu → formun altında, sola hizalı**, son alanla arası 24px. Formun "İptal/Vazgeç"i varsa birincilin **sağında** hayalet/nötr.
   - **İstisna:** auth formları (giriş, kayıt, şifre) → gönder butonu **tam genişlik** (lg, 48px).
   - Değerlendirme gibi uzun formlar → alt kısımda **yapışkan aksiyon çubuğu** (kâğıt zemin, üstte 1px çizgi, 16px dikey boşluk, butonlar sağa hizalı).
3. **Dialog ve kart altı aksiyonları → sağa hizalı**; birincil/tehlikeli **en sağda**, Vazgeç solunda.
4. **Liste/tablo satır aksiyonları → satırın en sağında**, sm boyut, olumlu (Onayla) solda, olumsuz (Reddet) sağda, aralık 8px.
5. **Yan yana butonlar arası 8px**; buton grupları arası 16px.
6. **Bir görünümde tek birincil (dolu çam) buton.** İkinci önemli aksiyon outline, diğerleri nötr/hayalet.
7. **Yıkıcı aksiyonlar asla doğrudan çalışmaz** → tehlikeli outline tetikleyici → dialog (gerekçe) → tehlikeli dolu onay.
8. **Metin linkleri** cümle içindeyse çam renk + alt çizgi; navigasyon linkiyse ikincil renk, hover'da mürekkep.
9. **Başarı mesajları** butonun hemen altında satır içi değil → toast (bkz. 2.6). **Hata mesajları** ilgili alanın altında veya formun üstünde (formun tamamıyla ilgiliyse).

---

## 4. Animasyon sistemi

Hareket yalnız **durum değişimini** anlatır; süs animasyonu yok. Kullanıcıda `prefers-reduced-motion: reduce` varsa **tüm hareketler kapanır**, yalnız anlık durum değişimi görünür (mevcut `motion-reduce` kuralı).

| Öğe | Tetikleyici | Hareket | Süre | Eğri |
|---|---|---|---|---|
| Buton (tüm varyantlar) | hover | zemin/opaklık/renk geçişi | 150ms | ease-out |
| Buton | basma | 1px aşağı kayma | 75ms | ease-out |
| Buton | yükleniyor | dönen halka (sonsuz) | 800ms/tur | linear |
| Metin link | hover | renk + alt çizgi belirir | 150ms | ease-out |
| Input/Select | odak | kenar rengi + halka belirir | 150ms | ease-out |
| Input | hata | kenar tuğlaya döner; mesaj 4px yukarıdan kayarak + opaklık | 150ms | ease-out |
| Tıklanabilir kart / tablo satırı | hover | kenar/zemin rengi | 150ms | ease-out |
| Navbar öğesi | hover | zemin rengi | 120ms | ease-out |
| Navbar aktif çizgisi | sayfa değişimi | sol 2px çam çizgi yeni öğeye geçer (sönüp belirir) | 150ms | ease-out |
| Sekme alt çizgisi | sekme değişimi | çizgi yeni sekmeye kayar (genişlik + konum) | 200ms | ease-in-out |
| Sekme içeriği | sekme değişimi | opaklık 0→1 | 120ms | ease-out |
| Dropdown | açılış | opaklık 0→1 + 4px kayma + ölçek 0.98→1 | 150ms | ease-out |
| Dropdown | kapanış | opaklık 1→0 | 100ms | ease-in |
| Dialog | açılış | arka plan opaklık 0→%40; panel opaklık + 8px yukarı kayma + ölçek 0.98→1 | 200ms | ease-out |
| Dialog | kapanış | ters yönde | 150ms | ease-in |
| Mobil çekmece (navbar) | açılış | soldan kayma (−100%→0) + arka plan karartma | 250ms | ease-out |
| Mobil çekmece | kapanış | sola kayma | 200ms | ease-in |
| Toast | giriş | alttan 8px kayma + opaklık | 200ms | ease-out |
| Toast | çıkış | opaklık + 8px sağa kayma | 150ms | ease-in |
| Uyarı şeridi | belirme | yükseklik açılır + opaklık | 200ms | ease-out |
| İskelet | yükleniyor | opaklık 1→0.55→1 nabız | 1.6s döngü | ease-in-out |
| Liste öğesi ekleme (görev, çıktı, kriter) | ekleme | yeni öğe opaklık + 4px aşağıdan | 200ms | ease-out |
| Liste öğesi kaldırma | kaldırma | opaklık 1→0, ardından yükseklik kapanır | 150 + 150ms | ease-in |
| Kanıt yükleme ilerleme çubuğu | 1/3 → 2/3 → 3/3 | genişlik dolar | 200ms | linear |
| Sürükle-bırak alanı | dosya üzerine gelince | kesik kenar çama döner + zemin çam %10 | 150ms | ease-out |
| Kopyala butonu | tıklama | ikon `copy`→`check` çapraz geçiş, 1.5 sn sonra geri | 150ms | ease-out |
| Rozet durumu değişimi | durum güncellenince | renk geçişi | 200ms | ease-out |
| **Zincir adımı tamamlanınca** | durum ilerleyince | bağlantı çizgisi soldan sağa çamla dolar, ardından daire dolgusu | 400ms (+100ms) | ease-in-out |
| **Mühür basılması (tek "keyif anı")** | çalışma `VERIFIED` olunca (detay sayfası) | ölçek 1.08→1, dönüş −8°→−4°, opaklık 0→1 | 400ms | cubic-bezier(.2,.8,.2,1) |
| Landing sertifika kartı | — | **hareket yok** (statik −1° eğim) | — | — |
| Sayfa geçişi | — | **animasyon yok** | — | — |

**Yasak:** zıplayan butonlar, parıltı, sayıların sayarak artması, paralaks, kaydırınca beliren bölümler, sürekli dönen/titreşen öğeler (yükleniyor halkası hariç).

---

## 5. Uygulama kabuğu (AppShell) — sol navbar

Giriş yapan kullanıcının gördüğü tüm sayfaları sarar (`/calismalar…`, `/profil`, `/kurulus…`, `/kurum…`, `/admin…`). Landing, auth ve public (`/v`, `/p`) sayfalarında **yok**.

> Kodda bugün yatay üst bar var; tasarlanacak yapı aşağıdaki sol navbar'dır.

### 5.1 Masaüstü (≥ 1024px)

```
┌──────────────┬────────────────────────────────────────────┐
│  NAVBAR      │  [Uyarı şeritleri — varsa]                  │
│  248px       │                                            │
│  kum zemin   │  İçerik alanı (kâğıt zemin)                 │
│  sağda 1px   │  üst 32px, yan 40px boşluk                  │
│  çizgi       │  max 1040 / 880 / 560px (sayfa türüne göre) │
│  tam yükseklik, sabit (kaymaz)                            │
└──────────────┴────────────────────────────────────────────┘
```

**Navbar dikey yapısı (yukarıdan aşağı):**

| # | Blok | Konum / ölçü | İçerik ve stil |
|---|---|---|---|
| 1 | **Logo alanı** | üst, 24px üst / 20px yan boşluk, yükseklik 64px | "Yetkin360" Serif 20px bold mürekkep (landing başlığıyla aynı). Altında 4px boşlukla Mono 11px ikincil slogan: "beyan → kanıt → tanıklık → doğrulanmış deneyim" (2 satıra kırılabilir). Logoya tıklama → `/calismalar`. |
| 2 | Ayırıcı | 1px çizgi, 20px yan boşluk | — |
| 3 | **Grup: Çalışma** | 24px üst boşluk | Grup etiketi 12px Sans 500 ikincil (sol 20px). Öğeler: **Çalışmalarım** → `/calismalar` (herkes) · **Profil** → `/profil` (öğrenci profili varsa) · **Herkese açık profilim** → `/p/{public_slug}` (slug varsa; sağında 14px `arrow-up-right`, yeni sekmede açılır) |
| 4 | **Grup: Kuruluşlarım** | 24px üst boşluk | Kullanıcının üyesi olduğu **her kuruluş için** bir öğe: "{Kuruluş adı}" → `/kurulus/{id}/panel`. İkon `building-2`. Uzun ad tek satırda "…" ile kesilir, hover'da tam ad ipucu. Grup yalnız kuruluş varsa görünür. |
| 5 | **Grup: Kurumlarım** | 24px üst boşluk | Her kurum için "{Kurum adı}" → `/kurum/{id}/panel`. İkon `landmark`. Yalnız kurum üyeliği varsa. |
| 6 | **Grup: Yönetim** | 24px üst boşluk | Yalnız platform admini: **Kurum Doğrulama** → `/admin/dogrulama-kuyrugu` · **Yetkinlik Yönetimi** → `/admin/skiller` |
| 7 | Boşluk | esner (navbarın kalanını doldurur) | — |
| 8 | Ayırıcı | 1px çizgi | — |
| 9 | **Kullanıcı kartı** | en alt, 12px boşluk, yükseklik 56px | Solda 32px avatar (baş harf), yanında ad (14px 500, tek satır) ve altında e-posta (12px ikincil, "…" ile kesilir; tam e-posta **gösterilmez**, ör. `meyr…@gmail.com`). Sağda 16px `chevrons-up-down`. Tüm kart buton; hover zemin kâğıt %60. Tıklanınca **yukarı doğru açılan dropdown**: "Profil" (`user-round`) → `/profil` · çizgi · **"Çıkış"** (`log-out`, tuğla metin) → çıkış → `/giris`. |

**Menü öğesi stili:**

| Durum | Zemin | Metin | İkon | Ek |
|---|---|---|---|---|
| Normal | şeffaf | ikincil `#625C55`, 14px 400 | ikincil 16px | yükseklik 36px, yatay iç boşluk 12px, dış boşluk 8px (navbar kenarından), köşe 6px, ikon–metin 10px |
| Hover | kâğıt `#FAF8F5` | mürekkep | mürekkep | 120ms geçiş |
| **Aktif (bulunulan sayfa)** | kart `#FEFEFD` + 1px çizgi kenar | mürekkep, **500** | **çam** | öğenin solunda (navbar iç kenarına yapışık) **2px × 20px çam dikey çizgi** |
| Odak (klavye) | — | — | — | 2px çam dış çizgi |

- Alt sayfalar üst öğeyi aktif yapar: `/calismalar/{id}` ve `/calismalar/{id}/degerlendirme` → "Çalışmalarım" aktif.
- Öğeler arası dikey boşluk 2px.

### 5.2 Tablet ve mobil (< 1024px)

- **Üst bar:** yükseklik 56px, kâğıt zemin, altta 1px çizgi, yapışkan (sayfa kayarken üstte kalır).
  - Sol: 40px hayalet ikon buton `menu` (aria-label "Menüyü aç") → 12px boşluk → "Yetkin360" Serif 18px bold.
  - Sağ: 32px avatar → tıklanınca aşağı açılan aynı kullanıcı dropdown'u.
- **Çekmece:** soldan açılır, genişlik 280px (en fazla ekranın %85'i), kum zemin, içerik masaüstü navbarla aynı (logo alanının sağ üstünde `x` kapat butonu). Arka plan mürekkep %40; arka plana tıklama, Esc veya bir menü öğesine tıklama çekmeceyi kapatır. Odak çekmece içinde kilitli.

### 5.3 İçerik alanının üstündeki uyarı şeritleri

İçerik alanının en üstünde, sayfa başlığından önce, aralarında 8px, altında 24px boşlukla yığılır. Tam içerik genişliği; kapatılamaz (durum düzelince kaybolur).

| Şerit | Ne zaman | Renk | Metin | Buton (sağda) |
|---|---|---|---|---|
| E-posta doğrulanmadı | `email_verified = false` | Uyarı (aşı) | "E-posta adresiniz doğrulanmadı. Doğrulanana kadar kayıt oluşturamaz veya değişiklik yapamazsınız." | **"Doğrulama bağlantısını yeniden gönder"** — nötr sm. Tıklayınca "Gönderiliyor…" → başarıda şerit metni "İstek alındı. E-postanızı kontrol edin…" olur, buton gizlenir; hata: "Bağlantı gönderilemedi…" + buton tekrar aktif |
| Kuruluş yok | kullanıcının kuruluşu yoksa | Bilgi (soluk) | "Henüz bir kuruluşunuz yok. Lütfen yöneticinize başvurun." | — *(Not: bu şerit öğrencilere de çıkıyor; yalnız kuruluş rolü beklenen kullanıcılara gösterilmesi önerilir.)* |
| Oturum verisi kısmen yüklenemedi | önbellek var + hata | Hata | "Bağlantı hatası…" / genel hata + destek kodu | **"Tekrar dene"** nötr sm |
| Çıkış başarısız | çıkış hatası | Hata | "Çıkış tamamlanamadı, lütfen tekrar deneyin." | — |

### 5.4 Kabuk durumları

- **Yükleniyor:** navbar iskeleti (logo bloğu + 4 menü çubuğu + alt avatar dairesi) + içerikte başlık çubuğu ve 3 blok. "Yükleniyor…" yazısı **yok**.
- **Oturum süresi doldu:** navbar yerine yalnız logo; içerik ortasında değil **sol üstte** hata kartı: "Oturumunuz sona erdi. Lütfen tekrar giriş yapınız." + birincil **"Giriş yap"** → `/giris`.
- **Bilgiler yüklenemedi / ağ hatası:** aynı yerleşim, hata kartı + "Tekrar dene" + destek kodu.

---

## 6. Sayfalar

Her sayfada şu başlıklar var: **Yol · Kim · Genişlik · Düzen (yukarıdan aşağı) · Butonlar tablosu · Durumlar · Mobil · Animasyon notu.**

### Sayfa listesi

| # | Sayfa | Yol | Kabuk | Öncelik |
|---|---|---|---|---|
| 1 | Landing | `/` | yok (kendi üst barı) | P0 — **mevcut tasarım** |
| 2 | Doğrulama sertifikası | `/v/[token]` | yok (public) | **P0 — en kritik** |
| 3 | Herkese açık profil | `/p/[slug]` | yok (public) | P0 |
| 4 | Giriş | `/giris` | AuthLayout | P0 — **mevcut tasarım** |
| 5 | Kayıt | `/kayit` | AuthLayout | P0 — **mevcut tasarım** |
| 6 | Şifremi unuttum | `/sifre-unuttum` | AuthLayout | P1 |
| 7 | Şifre sıfırla | `/sifre-sifirla?token=…` | AuthLayout | P1 |
| 8 | E-posta doğrula | `/e-posta-dogrula?token=…` | AuthLayout | P1 |
| 9 | Çalışmalarım | `/calismalar` | AppShell | P0 |
| 10 | Çalışma detayı | `/calismalar/[id]` | AppShell | **P0 — demonun kalbi** |
| 11 | Değerlendirme formu | `/calismalar/[id]/degerlendirme` | AppShell | P0 |
| 12 | Yeni çalışma | `/calismalar/olustur?organization_id=…` | AppShell | P1 |
| 13 | Profil | `/profil` | AppShell | P0 |
| 14 | Kuruluş paneli | `/kurulus/[id]/panel` | AppShell | P1 |
| 15 | Yeni kuruluş | `/kurulus/olustur` | AppShell | P1 |
| 16 | Kurum paneli | `/kurum/[id]/panel` | AppShell | P1 |
| 17 | Yeni kurum | `/kurum/olustur` | AppShell | P1 |
| 18 | Kuruma bağlan | `/kurum/[id]/baglan` | AppShell | P1 |
| 19 | Admin — kurum doğrulama | `/admin/dogrulama-kuyrugu` | AppShell | P1 |
| 20 | Admin — yetkinlikler | `/admin/skiller` | AppShell | P2 |
| 21 | 404 ve hata | `not-found`, `error` | yok | P1 |

---

### 1. Landing — `/` (mevcut tasarım, ince işçilik)

**Kim:** ziyaretçi + jüri. **Genişlik:** 1152px, yan 32px (mobil 16px). **Zemin:** kâğıt.

**Düzen (koddaki sırayla):**

| # | Bölüm | Konum ve ölçü | İçerik |
|---|---|---|---|
| 1 | **Üst bar** | yükseklik ~68px (20px dikey boşluk), altında 1px çizgi; içerik genişliğinde | **Sol:** "Yetkin360" Serif 20px bold. **Sağ:** linkler, aralarında 24px: "Giriş Yap" (14px ikincil metin link) · "Kayıt Ol" (14px 500 mürekkep, hover çam). Üst bar yapışkan **değil**. |
| 2 | **Hero** | 2 kolon **7fr / 5fr**, kolon arası 48px, dikey 64px, dikey ortalı | **Sol kolon:** H1 Display Serif 48px (mobil 36) "Yetkinliğiniz iddia değil, kanıt olsun." → 24px → Lead 18px ikincil açıklama → 16px → **Mono 14px ikincil slogan** "beyan → kanıt → tanıklık → doğrulanmış deneyim" → 32px → **CTA satırı** (sola hizalı, 16px aralık). **Sağ kolon:** sertifika kartı (Kart, 32px iç boşluk, **−1° eğik**) içinde ortada `VerifiedSeal` md → kartın altında 16px boşlukla 14px ikincil açıklama "Doğrulama sertifikası örneği. İsim ve tarih, doğrulama tamamlandığında görünür." |
| 3 | **Zincir nasıl işler** | üstte 1px çizgi, dikey 64px | H2 Serif 24px "Zincir nasıl işler" → 32px → `ChainProgress` lg, 4 eşit kolon (yalnız son adım "Doğrulanmış Deneyim" çam dolu). *İnce işçilik önerisi:* her adımın altına 13px ikincil tek cümle (kim yapar) + adımlar arası bağlantı çizgisi. |
| 4 | **Beyan mı, doğrulanmış kayıt mı?** | üstte 1px çizgi, dikey 64px, metin genişliği **768px** | H2 → 24px → 18px **ikincil** "Kendi beyanınız: yalnızca sizin sözünüzden ibaret." → 16px → 18px **mürekkep** "Doğrulanmış kayıt: kanıt ve tanıklıkla teyit edilmiş." *İnce işçilik önerisi:* iki cümleyi yan yana iki sütun yap — sol sütun gri, mühürsüz bir CV satırı örneği; sağ sütun aynı satır + `VerifiedSeal` sm. |
| 5 | **Kimler için?** | üstte 1px çizgi, dikey 64px | H2 → 32px → 3 eşit kolon, 24px aralık, her biri **Kart**: H3 Serif 20px (Öğrenci / Kuruluş / Kurum) → 12px → 15px ikincil açıklama. |
| 6 | **Footer** | üstte 1px çizgi, dikey 32px, tam genişlik | 14px ikincil "Yetkin360 açık kaynak bir projedir." *Öneri:* sağa GitHub ve Lisans metin linkleri. |

**Butonlar:**

| Buton | Konum | Stil | Tıklayınca |
|---|---|---|---|
| Giriş Yap | üst bar sağ, 1. | metin link (ikincil → mürekkep) | `/giris` |
| Kayıt Ol | üst bar sağ, 2. | metin link 500 (→ hover çam) | `/kayit` |
| **Kayıt Ol** | hero sol, CTA satırı 1. | **Birincil lg** (48px, 24px yatay) | `/kayit` |
| Örnek Bir Doğrulamayı İncele | hero sol, CTA satırı 2. | **Outline lg** | **bugün `/giris`** (test sabitliyor) → hedef: örnek bir `/v/{demo-token}` (bkz. Açık noktalar) |

**Durumlar:** statik sayfa — yükleme/hata yok. Rakam/istatistik şeridi **yok** (gerçek veri yok).
**Mobil:** üst bar aynı (linkler küçülmez); hero tek kolon — önce başlık + açıklama + slogan + CTA'lar (CTA'lar alt alta, tam genişlik), sonra sertifika kartı; zincir dikey (daire solda, etiket sağda, 24px aralık); persona kartları alt alta.
**Animasyon:** yalnız hover/odak geçişleri. Kart eğimi statik.

---

### 2. Doğrulama sertifikası — `/v/[token]` (en kritik ekran)

**Kim:** herkes, giriş gerekmez; çoğunlukla **telefonda, QR'dan** açılır. **Genişlik:** sertifika kartı max **720px**, ortalı (bu sayfada ortalama bilinçli: belge masada). **Zemin:** kâğıt.

**Veri (yalnız bunlar):** `title` (rol/çalışma adı) · `talent_name` · `organization_name` · `organization_trust_level` · `organization_domain` (ops.) · `institution_name` + `institution_trust_level` (ops.) · `started_on`, `ended_on` (ops.) · `verified_at` · `attested_skills[]` → `name_tr`, `attestor_organization`.

**Düzen:**

| # | Bölüm | Konum ve ölçü | İçerik |
|---|---|---|---|
| 1 | İnce üst bar | 56px, altında 1px çizgi | Sol: "Yetkin360" Serif 18px bold (→ `/`). Sağ: 13px ikincil "Doğrulama kaydı". |
| 2 | **Sertifika kartı** | üstten 40px (mobil 16px); kart zemin, **çift çerçeve** (dışta 1px çizgi, 6px içeride ikinci 1px çizgi), 8px köşe, iç boşluk 48px (mobil 24px) | aşağıdaki iç düzen |
| 2a | Kart üst satırı | | **Sol:** 12px Mono ikincil "DOĞRULANMIŞ DENEYİM KAYDI" (tek yerde büyük harf istisnası — belge başlığı). **Sağ üst köşe:** `VerifiedSeal` **lg** (96px, −4°), kart kenarından 32px içeride. |
| 2b | Kişi | 24px altında | Serif **32px** 600 kişi adı (`talent_name`) → 8px → Serif 20px 500 ikincil rol/başlık (`title`). |
| 2c | Ayırıcı | 32px | 1px çizgi |
| 2d | **Bilgi ızgarası** | 2 kolon (mobil 1), satır arası 24px | Her hücre: üstte 12px Sans 500 ikincil etiket, altında 16px değer. **Kurum:** kuruluş adı + yanında `TrustLevelBadge` + (varsa) altında 13px "Doğrulanmış alan adı: ornek.com" Mono. **Eğitim Kurumu:** (varsa) ad + güven rozeti. **Dönem:** "12 Eylül 2026 – 20 Aralık 2026". **Doğrulama Tarihi:** "9 Ekim 2026". |
| 2e | **T1 uyarısı** | bilgi ızgarasının hemen altında, 16px | Yalnız kuruluş T1 ise: Uyarı kutusu (aşı) "Bu kurum henüz doğrulanmamıştır. Kurum adı kurumun kendi beyanıdır; kimliğini bağımsız olarak teyit edin." |
| 2f | **Zincir** | 32px, üstünde 1px çizgi + 24px | 12px ikincil "Bu deneyim dört adımdan geçti" → 16px → `ChainProgress` lg, **4 adım da tamamlandı** (çam). |
| 2g | **Tanıklık yapılan yetkinlikler** | 32px, üstünde 1px çizgi + 24px | H3 Serif 20px → 12px → yetkinlik çipleri (sarılan satırlar, 8px aralık). Çip: 32px yükseklik, kart zemin, 1px çizgi, 6px köşe, 14px 500 yetkinlik adı + 13px ikincil "· {tanıklık eden kuruluş}". Liste boşsa bölüm hiç gösterilmez. |
| 2h | **Kart altı damga satırı** | 40px, üstünde kesik 1px çizgi | Mono 12px ikincil: sol "Kayıt no: {token'ın ilk 8 karakteri}…", sağ "Yetkin360 · {verified_at, tam tarih-saat}". Altında 13px ikincil: "Bu sayfa Yetkin360 tarafından {tarih} tarihinde doğrulanmıştır." |
| 3 | Kart altı | 24px | Ortada 13px ikincil link "Yetkin360 nedir?" → `/`. |

**Butonlar / linkler:**

| Öğe | Konum | Stil | Tıklayınca |
|---|---|---|---|
| Yetkin360 logo | üst bar sol | metin | `/` |
| Yetkin360 nedir? | kart altı orta | metin link | `/` |
| Güven rozeti bilgi ikonu | rozet yanında | hayalet ikon 24px | küçük açıklama balonu (T seviyesi ne demek) |
| *(Öneri)* Linki kopyala | kart üst satırı, mührün solunda | hayalet ikon `link` + "Linki kopyala" | panoya kopyalar → "Kopyalandı" |

**Durumlar:**
- **Yükleniyor:** sertifika kartı iskeleti (aynı çerçeve; ad çubuğu, 4 hücre, çip sırası) — mühür yerinde soluk daire.
- **Bulunamadı (404):** aynı çift çerçeveli kart; mühür yerine **kesik çizgili boş daire** (ikincil); Serif 24px "Kayıt bulunamadı" → 14px ikincil "Bağlantı hatalı olabilir ya da kayıt kaldırılmış olabilir." → nötr buton "Ana sayfaya dön" → `/`.
- **Ağ/genel hata:** Hata uyarısı + "Tekrar dene".

**Mobil (375px, öncelikli):** mühür kartın üstünde **ortalı** (−4°), altında ad/rol sola hizalı; bilgi ızgarası tek kolon; zincir dikey; damga satırı iki satıra kırılır.
**Baskı (P2):** üst bar ve kart altı linki gizlenir, kart tek sayfaya sığar, zemin beyaz.
**Animasyon:** sayfa açılışında mühür **hareketsiz** (keyif anı yalnız detay sayfasında).

---

### 3. Herkese açık profil — `/p/[slug]`

**Kim:** herkes. **Genişlik:** 720px ortalı. **Zemin:** kâğıt.

**Veri:** `display_name` · `verified_experiences[]` → `role_snapshot`, `organization_name_snapshot`, `started_on_snapshot`, `ended_on_snapshot`, `claim_type`.

**Düzen:**

| # | Bölüm | Konum | İçerik |
|---|---|---|---|
| 1 | İnce üst bar | 56px | `/v` ile aynı ("Herkese açık profil"). |
| 2 | **Profil başlığı** | üstten 40px; sola hizalı | 64px avatar (baş harf) → 16px sağında Serif 32px ad → altında 14px ikincil "{n} doğrulanmış deneyim". |
| 3 | Ayırıcı | 32px | 1px çizgi |
| 4 | **Zaman çizelgesi** | 32px | H2 Serif 24px "Doğrulanmış deneyimler" → 24px → dikey liste. Solda 1px dikey çizgi; her öğenin hizasında çizginin üstünde `VerifiedSeal` sm (20px). Öğe (çizgiden 24px sağda): Serif 20px rol → 4px → 15px kuruluş adı → 4px → 13px ikincil dönem + " · " + tanıklık türü etiketi (Katılım / Katkı / Yetkinlik / Davranış — ham enum **değil**). Öğeler arası 32px. |
| 5 | Alt | 40px | "Yetkin360 nedir?" → `/` |

**Butonlar:** logo → `/`; "Yetkin360 nedir?" → `/`. *(API, deneyimin `/v` token'ını vermediği için öğeler tıklanabilir değil — bkz. Açık noktalar.)*
**Durumlar:** iskelet (avatar dairesi + 3 öğe) · **boş:** zaman çizelgesi yerine boş durum "Bu profilde henüz doğrulanmış deneyim yok." · **bulunamadı:** `/v`'deki gibi kesik daire + "Kayıt bulunamadı".
**Mobil:** avatar adın üstünde; zaman çizelgesi aynı (çizgi solda).

---

### 4–8. Kimlik doğrulama sayfaları — ortak `AuthLayout` (mevcut tasarım)

**Masaüstü (≥ 768px) düzen — 2 kolon, oran 2fr / 3fr, tam ekran yüksekliği:**

| Kolon | Zemin | İç boşluk | İçerik (yukarıdan aşağı, aralarında 32px) |
|---|---|---|---|
| **Sol — marka paneli** (%40) | **kum `#EBE5DA`** | 40px | 1) "Yetkin360" Serif 24px · 2) marka cümlesi Serif 20px "Sicil kaydınız, kanıtlarınızla birlikte güvenle saklanır." · 3) `ChainProgress` (son adım çam) — yalnız masaüstünde · 4) sayfa geçiş linkleri: 14px, alt çizgili (offset 4px), aralarında 16px |
| **Sağ — form alanı** (%60) | kâğıt | 48px | Form **dikey ve yatay ortalı**, genişlik max **448px**. **Kart çerçevesi yok** — form sayfaya oturur. |

*İnce işçilik önerileri (mevcut yapıyı bozmaz):* sol panelde logo üstte, linkler **en altta** (paneli dikeyde yay); logo `/`'a link olsun; form üstündeki eski gri kutu (`bg-slate-50` çerçeve) kaldırılsın.

**Form alanı ortak yapısı:**
- H1 Serif 32px (başlık) → 8px → 15px ikincil tek cümle açıklama → 32px → alanlar (16px aralık) → 24px → **gönder butonu: birincil lg, tam genişlik** → 16px → alternatif link satırı (14px, ortalanmış değil, sola hizalı).
- Form düzeyindeki hata (yanlış şifre vb.) **başlığın altında**, alanların üstünde Hata kutusu.

**Mobil (< 768px):** tek kolon. Üstte **ince marka şeridi** (kum zemin, 16px boşluk): "Yetkin360" Serif 20px + altında marka cümlesi 15px; zincir gizli; linkler formun altına iner. Form 16px yan boşluk.

#### 4. Giriş — `/giris`

| Öğe | Konum | Stil | Davranış |
|---|---|---|---|
| Başlık "Giriş" | form üstü | H1 | — |
| Oturum bitti uyarısı | başlık altı | Uyarı (aşı) | `?neden=oturum-bitti` ile gelinirse: "Oturumunuz sona erdi. Lütfen tekrar giriş yapınız." |
| E-posta | 1. alan | input, placeholder "E-posta adresiniz" | — |
| Şifre | 2. alan | input (şifre) | *Öneri:* etiket satırının **sağında** "Şifremi Unuttum" küçük metin link |
| **Giriş Yap** | alanların altı | **Birincil lg tam genişlik** | Başarı → `?next=` varsa oraya, yoksa **`/calismalar`**. Yükleniyor: "Giriş yapılıyor…" |
| Hata kutusu | başlık altı | Hata | "E-posta veya şifre hatalı." · "Hesabınız geçici olarak kilitlendi." · "Çok fazla deneme yaptınız…" |
| Kayıt Ol | sol panel linkleri (mobil: form altı) | metin link | `/kayit` |
| Şifremi Unuttum | sol panel linkleri | metin link | `/sifre-unuttum` |

#### 5. Kayıt — `/kayit`

| Öğe | Konum | Stil | Davranış |
|---|---|---|---|
| Başlık "Kayıt Ol" | form üstü | H1 | — |
| Ad Soyad · E-posta · Şifre | alanlar (bu sırayla) | input | Şifre altında 13px ikincil kural ipucu |
| **Kayıt Ol** | alanların altı | Birincil lg tam genişlik | Başarı → form yerine **başarı görünümü** (Başarı kutusu "Kaydınız alındı. E-postanızı doğrulayın.") → **0.8 sn sonra otomatik `/giris`** |
| Giriş Yap | sol panel linkleri | metin link | `/giris` |

#### 6. Şifremi unuttum — `/sifre-unuttum`

- Alan: **E-posta**. Buton: **"Şifre Sıfırlama Bağlantısı Gönder"** (birincil lg tam genişlik).
- Başarı: form yerine Başarı kutusu "Şifre sıfırlama bağlantısı gönderildi. E-postanızı kontrol edin." + altında metin link "Giriş sayfasına dön" → `/giris`.
- Sol panel linkleri: "Giriş Yap" → `/giris`.

#### 7. Şifre sıfırla — `/sifre-sifirla?token=…`

- Alanlar: **Yeni Şifre**, **Yeni Şifre Tekrar**. Buton: **"Şifre Sıfırla"** (birincil lg tam genişlik).
- Başarı: Başarı kutusu "Şifreniz değiştirildi." + birincil lg "Giriş Yap" → `/giris`.
- Token yok/geçersiz: form yerine Hata kutusu + nötr buton "Yeni bağlantı iste" → `/sifre-unuttum`.

#### 8. E-posta doğrula — `/e-posta-dogrula?token=…`

Form yok; tek alan, 3 durum (aynı konumda değişir):

| Durum | Görünüm | Buton |
|---|---|---|
| Doğrulanıyor | 16px dönen halka + 15px "E-posta doğrulanıyor..." | — |
| Başarılı | `VerifiedSeal` sm + H1 "E-postanız doğrulandı." | Birincil lg "Giriş Yap" → `/giris` |
| Geçersiz/süresi dolmuş | Hata kutusu "Bağlantı geçersiz veya süresi dolmuş." | Nötr "Kayıt Ol" → `/kayit` · metin link "Giriş Yap" → `/giris` |

---

### 9. Çalışmalarım — `/calismalar`

**Kim:** giriş yapan herkes (öğrenci, kuruluş, kurum). **Genişlik:** 1040px.

**Veri (liste öğesi):** `id`, `title`, `kind`, `organization_name`, `status`, `updated_at`.

**Düzen:**

| # | Bölüm | Konum | İçerik |
|---|---|---|---|
| 1 | **Başlık** | sol | H1 "Çalışmalarım" → 8px → 14px ikincil "{n} çalışma". *(Sağ: bkz. Açık noktalar — "Yeni çalışma" butonu yalnız kuruluş linkiyle mümkün.)* |
| 2 | **Filtre sekmeleri** | başlığın 32px altı | Sekmeler (2.9): **Tümü · Devam eden** (DRAFT, PENDING_APPROVAL, ACTIVE) **· Değerlendirmede** (PENDING_EVALUATION, EVALUATED) **· Doğrulanmış** (VERIFIED, RESOLVED) **· Kapanmış** (REJECTED, CANCELLED, DISPUTED). Her sekmede sayı. İstemci tarafı filtre. |
| 3 | **Kart ızgarası** | sekmelerin 24px altı | 2 kolon (≥1280: 3 kolon), 16px aralık. |

**Liste kartı (tıklanabilir, tamamı link → `/calismalar/{id}`):**

```
┌─────────────────────────────────────────┐
│ [Staj]                       [● Aktif]  │  ← sol: 12px ikincil tür · sağ: durum rozeti
│                                         │
│ Veri Analizi Stajı                      │  ← Serif 20px, en fazla 2 satır
│ Acme Yazılım A.Ş.                       │  ← 14px ikincil
│                                         │
│ ●───●───○───○          3 gün önce       │  ← sol: mini zincir · sağ: 12px Mono ikincil göreli tarih
└─────────────────────────────────────────┘
```
- Kart iç boşluğu 20px, yükseklik içerikle; doğrulanmış kartlarda başlığın sağında `VerifiedSeal` sm.

**Butonlar:** kartın tamamı → `/calismalar/{id}`. Sekmeler → filtre.
**Durumlar:** **yükleniyor:** 4 iskelet kart · **boş (hiç çalışma yok):** boş durum — ikon `briefcase`, başlık "Henüz bir çalışmanız yok", açıklama "Bir kuruluş sizi bir staja veya projeye eklediğinde ya da size bir başlatma bağlantısı gönderdiğinde çalışmanız burada görünür." · **sekme boş:** küçük boş durum "Bu durumda çalışma yok." · **hata:** Hata kutusu "Çalışmalar yüklenemedi." + "Tekrar dene".
**Mobil:** tek kolon kart; sekmeler yatay kaydırılır.
**Animasyon:** kart hover kenarı; sekme çizgisi kayar.

---

### 10. Çalışma detayı — `/calismalar/[id]` (demonun kalbi)

**Kim:** çalışmanın tarafları (öğrenci, kuruluş, kurum). **Genişlik:** 880px.

**Veri:** `title`, `kind`, `organization_name`, `status`, `updated_at`, `reason` (ops.), `version`, `tasks[]` (`title`, `status`), `deliverables[]` (`id`, `title`) + her çıktının kanıt dosyaları (tarama durumu), `attestations[]` (`claim_type`, geri çekilme durumu).

**Düzen:**

| # | Bölüm | Konum | İçerik |
|---|---|---|---|
| 1 | Geri linki | en üst sol | "← Çalışmalara dön" → `/calismalar` |
| 2 | **Başlık satırı** | 16px altı; sol başlık, sağ aksiyonlar | **Sol:** H1 Serif 32px başlık → 8px → 14px ikincil meta "Staj · Acme Yazılım A.Ş. · Güncellendi 9 Ekim 2026, 14:30" → 8px → durum rozeti. **Sağ:** **Aksiyon grubu** (aşağıdaki tablo), sağa hizalı, başlığın ilk satırıyla aynı hizada. |
| 3 | **Zincir kartı** | 32px altı, tam genişlik | Kart. Üstte `ChainProgress` lg (durum → adım eşlemesi 2.4'teki tablodan; bekleyen/kırık durumları dahil). 24px altında üstü 1px çizgili **"Sıradaki adım"** satırı: solda 12px ikincil etiket "Sıradaki adım", yanında 15px açıklama (aşağıdaki tablo). |
| 4 | **Gerekçe kutusu** | zincir kartının 16px altı | `reason` varsa: Uyarı (red/iptalde Hata) kutusu "Gerekçe: …". |
| 5 | **Tanıklık kartı** | 24px altı | Yalnız durum **EVALUATED** iken (bkz. alt bölüm 10b). |
| 6 | **Sekmeler** | 32px altı | **Görevler {n}** · **Çıktılar ve kanıtlar {n}** · **Tanıklıklar {n}**. Varsayılan sekme: ACTIVE ise "Çıktılar ve kanıtlar", EVALUATED/VERIFIED ise "Tanıklıklar", diğerlerinde "Görevler". |

**"Sıradaki adım" metinleri (durum → metin):**

| Durum | Metin |
|---|---|
| DRAFT | "Çalışmayı kuruluşun onayına gönderin." |
| PENDING_APPROVAL | "Kuruluşun onayı bekleniyor." |
| ACTIVE | "Görevleri tamamlayın, çıktı ekleyin ve kanıt yükleyin. Bitince değerlendirmeye gönderin." |
| PENDING_EVALUATION | "Kuruluşun değerlendirmesi bekleniyor." |
| EVALUATED | "Kuruluşun tanıklığı bekleniyor." |
| VERIFIED / RESOLVED | "Bu deneyim doğrulandı." (çam metin, yanında `VerifiedSeal` sm) |
| REJECTED / CANCELLED | "Bu çalışma kapandı." |
| DISPUTED | "İtiraz inceleniyor." |

**Başlık sağındaki aksiyon grubu (koddaki durum geçişleri):**

| Durum | Butonlar (soldan sağa) | Stil | Tıklayınca |
|---|---|---|---|
| DRAFT | **Onaya Gönder** | Birincil md | Hemen gönderir → rozet "Onay Bekliyor"a döner, toast "Durum güncellendi." |
| PENDING_APPROVAL | **Reddet** · **Onayla ve Aktifleştir** | Tehlikeli outline · Birincil | Reddet → **dialog** (aşağıda). Onayla → hemen gönderir → "Aktif". |
| ACTIVE | **İptal Et** · **Değerlendirmeye Gönder** | Tehlikeli outline · Birincil | İptal → **dialog**. Değerlendirmeye Gönder → hemen → "Değerlendirme Bekliyor". |
| PENDING_EVALUATION | **Değerlendirme Formu** | Birincil md (ikon `clipboard-check`) | **`/calismalar/{id}/degerlendirme`** sayfasına gider |
| EVALUATED · VERIFIED · REJECTED · CANCELLED · DISPUTED · RESOLVED | — (grup boş) | — | — |

- Butonlar bugün **rol fark etmeksizin** herkese görünüyor; yetkisi olmayan basarsa sunucu reddeder → başlığın altında Hata kutusu "Bu işlemi yapma yetkiniz yok." Tasarımcı bu hata durumunu da çizmeli.
- Diğer hatalar (aynı yerde): "Kayıt başka bir işlemle değişti, güncel durum yeniden yüklendi." (Uyarı) · "Bu durumda bu işlem yapılamaz…" (Uyarı).

**Reddet / İptal Et dialog'u:**
- Başlık: "Çalışmayı reddet" / "Çalışmayı iptal et". Gövde: 14px ikincil "Bu işlem geri alınamaz. Gerekçe çalışmanın taraflarına gösterilir."
- Alan: **Gerekçe** (textarea, zorunlu; boşsa "Bu işlem için gerekçe girilmesi zorunludur.").
- Alt satır sağa hizalı: **[Vazgeç — hayalet] [Reddet / İptal Et — Tehlikeli dolu]** (yükleniyor: "Uygulanıyor…").
- *(Kodda gerekçe alanı bugün satır içi açılıyor; dialog'a çevrilecek.)*

#### 10a. Sekme içerikleri

**Görevler sekmesi**
- Üst satır: sol 14px ikincil "{n} görev" · sağ **"Görev ekle"** (nötr md, ikon `plus`) — yalnız durum ACTIVE iken görünür.
- "Görev ekle" → listenin üstünde **satır içi açılan form kartı** (yükseklik açılarak, 200ms): Başlık · Açıklama (ops., textarea) · Son Tarih (ops., tarih) · İlişkili Yetkinlik (ops., yetkinlik arama alanı + seçili çip, "Temizle"). Kart altı sağa hizalı: [Vazgeç — hayalet] [**Görev Ekle** — Birincil]. Başarıda kart kapanır, yeni görev listeye eklenir, toast "Görev eklendi."
- Liste: her görev bir satır (52px, 1px alt çizgi): sol başlık 15px · sağ görev durum rozeti (Türkçe etiket; ham enum **değil**).
- Boş: "Henüz görev eklenmemiş." (+ ACTIVE ise "Görev ekle" butonu boş durumun içinde).
- Hata: "Görev yalnızca aktif çalışmalara eklenebilir." · "Seçilen yetkinlik geçersiz."

**Çıktılar ve kanıtlar sekmesi**
- Üst satır: sol "{n} çıktı" · sağ **"Çıktı ekle"** (nötr md) — yalnız ACTIVE.
- "Çıktı ekle" formu (satır içi kart): Başlık · Açıklama (ops.) · İlişkili Yetkinlik (ops.) → [Vazgeç] [**Çıktı Ekle**].
- Her çıktı bir **kart**:
  - Üst: Serif 18px çıktı başlığı.
  - Altında **kanıt dosyaları listesi**: her satır → solda dosya türü ikonu (16px) + dosya türü/boyut 13px ikincil · sağda tarama rozeti (2.4).
  - En altta **kanıt yükleme alanı**: 1px **kesik** çizgili kutu, 96px yükseklik, ortasında `upload` ikonu + 14px "Dosyayı buraya bırakın veya **seçin**" (seçin = çam link) + 12px ikincil "PDF, JPEG, PNG, DOCX — en fazla 10 MB".
  - Yükleme sırasında kutu **3 adımlı ilerleme**ye döner: 4px yükseklik ilerleme çubuğu (çam) + altında 13px adım metni "1/3 — Yükleme adresi alınıyor…" → "2/3 — Dosya yükleniyor…" → "3/3 — Kanıt kaydediliyor…". Bitince yeni dosya listeye "Taranıyor" rozetiyle eklenir; tarama sürerken rozet otomatik güncellenir.
- Boş: "Henüz çıktı yüklenmemiş."
- Hata: "Çıktı yalnızca aktif çalışmalara eklenebilir." · dosya boyutu/türü hataları (kutunun altında tuğla).

**Tanıklıklar sekmesi**
- Liste; her tanıklık bir satır/kart: sol — tanıklık türü (Katılım/Katkı/Yetkinlik/Davranış) 15px 500 · altında 13px ikincil ilgili yetkinlik ve tarih (varsa) · sağ — durum.
- **Geri çekilmiş tanıklık:** metin üstü çizili + ikincil renk, sağda Hata rozeti "Geri çekildi".
- **Geri Çek:** her aktif tanıklığın sağında **Tehlikeli outline sm "Geri Çek"** → **dialog**: başlık "Tanıklığı geri çek", alan **Geri çekme gerekçesi** (zorunlu), [Vazgeç] [**Geri Çek** — Tehlikeli dolu]. Hatalar: "Sadece kendi verdiğiniz tanıklığı geri çekebilirsiniz." · "Bu tanıklık zaten geri çekilmiş." *(Buton bugün herkese görünüyor; sunucu yetkisizi reddeder.)*
- Boş: "Henüz tanıklık yok."

#### 10b. Tanıklık kartı (yalnız EVALUATED)

Zincir kartının altında, tam genişlik kart; sol kenarında 3px aşı çizgisi (bekleyen adım):
- H3 Serif "Tanıklık Ver" → 8px → 14px ikincil "Değerlendirmesi tamamlanan bu çalışmaya kuruluş adına tanıklık edin. Tanıklık kaydı silinemez; yalnız gerekçeyle geri çekilebilir."
- **Tanıklık Türü:** 4'lü **segment** (Katılım · Katkı · Yetkinlik · Davranış).
- **İlişkili Yetkinlik** (ops.): yetkinlik arama alanı.
- Kart altı sağa hizalı: **[Tanıklığı Gönder — Birincil]** (yükleniyor "Gönderiliyor…").
- **Başarı:** kart kaybolur → durum VERIFIED olur → **zincirin son çizgisi dolar + mühür basılma animasyonu** (Bölüm 4) → toast "Tanıklık gönderildi, deneyim doğrulandı."
- **Düşürülmüş başarı:** Uyarı kutusu "Tanıklığınız **Yetkinlik** yerine **Katılım** olarak kaydedildi." + altında sebep (ör. "Çalışma süresi yeterli değil (en az 4 hafta gerekli)", "Hiç çıktı gönderilmemiş", "Kurumunuz yeterince doğrulanmış değil", "Koordinatör onayı eksik").
- Hatalar: "Kendi deneyiminize tanıklık yapamazsınız." · "Bu çalışma için zaten tanıklık gönderilmiş." · "Tanıklık yalnızca değerlendirme tamamlanmış çalışmalar için verilebilir."

**Durumlar (sayfa):** iskelet (başlık + zincir kartı + sekme + 3 satır) · **bulunamadı:** "Çalışma bulunamadı." + nötr "Çalışmalara dön" · **hata:** "Çalışma yüklenemedi." + "Tekrar dene".
**Mobil:** başlık satırında aksiyonlar başlığın **altına** iner (birincil tam genişlik, tehlikeli outline altında tam genişlik); zincir dikey; sekmeler kaydırılır; formlar tam genişlik.

---

### 11. Değerlendirme formu — `/calismalar/[id]/degerlendirme`

**Kim:** kuruluş (değerlendiren). **Genişlik:** 880px. Yalnız çalışma **PENDING_EVALUATION** iken form görünür.

**Düzen:**

| # | Bölüm | Konum | İçerik |
|---|---|---|---|
| 1 | Geri linki | üst sol | "← Çalışmaya dön" → `/calismalar/{id}` |
| 2 | Başlık | 16px altı | H1 "Değerlendirme Formu" → 8px → 14px ikincil "Her kriter için gözleminizi işaretleyin. Gönderilen değerlendirme değiştirilemez." |
| 3 | **Çalışma özet kartı** | 24px altı | Kum zeminli kart (çerçeve 1px çizgi): Serif 20px çalışma başlığı · 14px ikincil "Tür · Kuruluş" · sağda durum rozeti. |
| 4 | **Kriter blokları** | 32px altı, aralarında 16px | Her biri bir kart, sol üstte 12px Mono ikincil "Kriter 1". Alanlar: **Kriter** (input, placeholder "Örn. Python kullanımı, Zamanında teslim") → **Değerlendirme**: 4'lü **segment**, tam genişlik: Beklentinin Altında · Beklentiyi Karşılıyor · Beklentiyi Aşıyor · Gözlemlenmedi (seçili segment çam kenar/zemin; "Beklentinin Altında" seçiliyse de çam — renkle not verme yok) → **Yorum** (ops., textarea 2 satır). Kartın sağ üst köşesinde **"Kaldır"** (hayalet sm, ikon `trash-2`) — 1'den fazla kriter varsa. |
| 5 | Kriter ekle | son kriterin 16px altı, sola hizalı | **"Kriter Ekle"** — Nötr md, ikon `plus`. Tıklayınca yeni boş kriter kartı eklenir (animasyonlu) ve ilk alanına odaklanır. |
| 6 | **Kurum içi not** | 32px altı | Kum zeminli kutu, 1px çizgi, 16px iç boşluk: başlıkta 16px `lock` ikonu + "Kurum içi not (opsiyonel)" → textarea → 13px ikincil "Bu not sadece kurumunuz içinde görünür, öğrenciye asla gösterilmez." |
| 7 | **Yapışkan aksiyon çubuğu** | sayfanın altında sabit | Kâğıt zemin, üstte 1px çizgi, 16px dikey boşluk, içerik genişliğinde. Sol: 13px ikincil "{n} kriter". Sağ: **[Değerlendirmeyi Gönder — Birincil md]**. |

**Gönder akışı:** butona basınca **onay dialog'u**: başlık "Değerlendirmeyi gönder", gövde "Gönderilen değerlendirme değiştirilemez. Çalışma 'Değerlendirildi' durumuna geçer." → [Vazgeç] [**Gönder** — Birincil]. Başarı → Başarı kutusu "Değerlendirme gönderildi." + nötr buton "Çalışmaya dön" → `/calismalar/{id}` *(kodda bugün yönlendirme yok, yalnız mesaj)*.

**Durumlar:**
- **Uygun değil** (durum PENDING_EVALUATION değil): form yerine Bilgi kutusu "Bu çalışma değerlendirme aşamasında değil, form gösterilemiyor." + nötr "Çalışmaya dön".
- **Çakışma:** Uyarı "Bu çalışma şu anda değerlendirilemiyor (zaten değerlendirilmiş veya durumu değişmiş olabilir). Güncel durum yeniden yüklendi."
- Alan hataları ilgili alanın altında; ilk hatalı alana kaydırılır.

**Mobil:** segment 2×2 ızgaraya döner; aksiyon çubuğunda buton tam genişlik.

---

### 12. Yeni çalışma — `/calismalar/olustur?organization_id=…`

**Kim:** öğrenci; kuruluşun gönderdiği bağlantıyla gelir. **Genişlik:** 560px.

| # | Bölüm | İçerik |
|---|---|---|
| 1 | Geri linki | "← Çalışmalara dön" → `/calismalar` |
| 2 | Başlık | H1 "Yeni Çalışma Oluştur" → 14px ikincil "Oluşturduğunuz çalışma taslak olarak kaydedilir; ardından kuruluşun onayına gönderirsiniz." |
| 3 | Form (kartsız) | **Tür:** 4 seçenekli **seçim kartları** (2×2 ızgara, her biri 64px: 15px 500 ad + 12px ikincil kısa açıklama): Staj · Bitirme Projesi · Kısa Proje · Yarı Zamanlı → **Başlık** (input) |
| 4 | Buton | sola hizalı **[Oluştur — Birincil md]** (yükleniyor "Oluşturuluyor…") → başarı → **`/calismalar/{yeni id}`** |

**Durumlar (form yerine Bilgi/Hata kartı + "Çalışmalara dön"):** bağlantı eksik/geçersiz → "Bu link eksik veya geçersiz. Organizasyonunuzdan doğru linki isteyin." · öğrenci değil → "Bu özellik yalnızca öğrenci hesapları için kullanılabilir." · kuruluş bulunamadı → "Bu organizasyon bulunamadı…".

---

### 13. Profil — `/profil`

**Kim:** öğrenci. **Genişlik:** 880px.

**Düzen:**

| # | Bölüm | Konum | İçerik |
|---|---|---|---|
| 1 | **Profil özet kartı** | en üst | Kart, yatay: sol 64px avatar → 16px → Serif 28px ad + altında 14px ikincil "Başlık · Bölüm · Şehir" (dolu olanlar) + 8px altında görünürlük rozeti (Özel / Kurum / Kuruluşlar / Herkese Açık — Herkese Açık nötr+`globe`). **Sağ (sağa hizalı):** **"Herkese açık profili gör"** (Outline sm, `arrow-up-right`) → `/p/{slug}` yeni sekme · **"Linki kopyala"** (hayalet sm, `copy`). İkisi yalnız slug varsa ve görünürlük "Herkese Açık" ise. |
| 2 | **Sekmeler** | 32px altı | **Profil bilgileri · Yetkinlikler {n} · Kanıt dökümü · Kurum bağlantısı** |

**Profil bilgileri sekmesi** — form, 2 kolon ızgara (mobil 1), 16px aralık:
- Başlık (tam genişlik) · Bölüm · Öğrenim Yılı (sayı) · Şehir · Görünürlük (select: Özel (Sadece Ben) / Kurum (Kurumum) / Kuruluşlar / Herkese Açık) · **Profil Linki** (tam genişlik; input'un solunda soluk zeminli sabit önek kutusu Mono "yetkin360…/p/", input Mono).
- Altında sola hizalı **[Kaydet — Birincil md]** (yükleniyor "Kaydediliyor…"). Başarı → toast "Profiliniz başarıyla kaydedildi." Hata: profil linki alanının altında "Bu slug zaten alındı, lütfen farklı bir profil linki seçin."

**Yetkinlikler sekmesi** — ürünün iddiasının profildeki karşılığı:
- **Ekleme satırı** (üstte, kum zeminli kutu): yetkinlik **arama alanı** ("Yetkinlik ara…", sonuçlar altta açılan listede) → **Seviye** select (Başlangıç / Orta / İleri) → **[Ekle — Nötr md]**. Yan yana, mobilde alt alta.
- **Liste** — her yetkinlik bir satır (56px): sol yetkinlik adı 15px 500 + altında 12px ikincil seviye · orta **beyan/kanıt göstergesi** · sağ **"Kaldır"** (hayalet sm).
  - **Yalnız beyan:** nötr rozet "Kendi beyanı", mühür yok, ad ikincil renkte.
  - **Kanıt sinyali olan:** *(veri `Kanıt dökümü`'nden eşleştirilebilirse)* rozet + "{n} kanıt" — doğrulanmışsa `VerifiedSeal` sm ve çam metin. *(Bkz. Açık noktalar: yetkinlik listesi API'si kanıt sayısı döndürmüyor.)*
- Toast: "Yetkinlik eklendi." / "Yetkinlik kaldırıldı." Hatalar: "Bu yetkinliği zaten eklediniz." · "Bu yetkinlik artık mevcut değil, listeyi yeniledik."
- Boş: "Henüz bir yetkinlik eklemediniz." + "Yukarıdan arayarak ilk yetkinliğinizi ekleyin."

**Kanıt dökümü sekmesi** — iki bölüm alt alta:
1. **Kanıt Sinyalleri** (H2): tablo — Kaynak (Kendi Beyanı / Teslim Edilen Çıktı / Görev / Değerlendirme / Tanıklık / Harici Kaynak) · Güç (Yok / Zayıf / Orta / Güçlü → 4 küçük çubuk göstergesi, dolu çubuklar mürekkep) · Tanıklık eden (varsa) · Tarih. **Geçersiz kılınmış** satırlar soluk + rozet "Geçersiz kılındı". Boş: "Henüz kanıt sinyali yok." Hata: "Kanıt dökümü yüklenemedi." + "Tekrar dene".
2. **Doğrulanmış Deneyimler** (H2): `/p` sayfasındaki zaman çizelgesiyle **aynı** bileşen (rol, kuruluş, dönem; "Devam ediyor" / "Başlangıç bilinmiyor"). Boş: "Henüz doğrulanmış deneyim yok."

**Kurum bağlantısı sekmesi:**
- Bağlı değilse: boş durum — ikon `landmark`, "Henüz bir kuruma bağlı değilsiniz.", "Kurumunuzdan aldığınız bağlantıyı kullanarak bağlanma talebi gönderebilirsiniz."
- **Bağlanma Taleplerim** (H3): liste — kurum adı 15px + tarih 13px ikincil · sağda rozet: Onay Bekliyor (aşı) / Onaylandı (çam) / Reddedildi (tuğla). Boş: "Henüz bir bağlanma talebiniz yok." Hata: "Bağlanma talepleriniz yüklenemedi."

**Durumlar:** özet kartı + sekme iskeleti; profil yüklenemezse Hata "Profiliniz yüklenemedi, lütfen destek ile iletişime geçin."
**Mobil:** özet kartında aksiyonlar adın altına iner; form tek kolon.

---

### 14. Kuruluş paneli — `/kurulus/[id]/panel`

**Kim:** kuruluş (işveren) üyesi. **Genişlik:** 880px.

**Veri:** kuruluş `name`, `legal_id`, `domain`, alan adı doğrulama durumu, TXT kaydı, güven seviyesi.

**Düzen:**

| # | Bölüm | Konum | İçerik |
|---|---|---|---|
| 1 | Başlık | üst | 12px ikincil üst etiket "Organizasyon Paneli" → H1 Serif kuruluş adı → 8px → satır: `TrustLevelBadge` + 13px Mono ikincil "Ticari Sicil No: {legal_id}" (varsa) |
| 2 | **Alan Adı Doğrulama kartı** | 32px altı | H3 "Alan Adı Doğrulama" + sağda durum rozeti. İçerik duruma göre (aşağıda). |
| 3 | **Üye Davet Et kartı** | 24px altı | H3 → satır: **E-posta** (input, esnek genişlik) · **Rol** (select 160px: Yönetici / Üye) · **[Davet Gönder — Nötr md]** — yan yana, alt hizalı. Başarı toast "Davet kuyruğa alındı." Hata satır içi "Davet gönderilemedi." |

**Alan adı kartı durumları:**

| Durum | İçerik | Buton |
|---|---|---|
| Alan adı yok | Bilgi metni "Bu organizasyon için alan adı belirlenmemiş, doğrulama yapılamaz." | — |
| Doğrulanmadı | 14px "Alan Adı: **ornek.com**" → 12px → "Bu TXT kaydını alan adınızın DNS ayarlarına ekleyin, sonra tekrar deneyin:" → **kopyalanabilir kod kutusu** (TXT değeri, Mono) | **[Doğrulamayı Kontrol Et — Birincil md]**, kutunun altında sola hizalı. Yükleniyor "Kontrol ediliyor…" |
| Kayıt henüz yok | Yukarıdakine ek Uyarı "Kayıt henüz bulunamadı. DNS değişiklikleri yayılması biraz zaman alabilir…" | Buton metni **"Tekrar Dene"** |
| Doğrulandı | Başarı satırı: `VerifiedSeal` sm + "Alan adı doğrulandı." + rozet "Doğrulanmış alan adı" | — |
| Hata | "Ücretsiz e-posta sağlayıcıları (gmail.com, hotmail.com vb.) doğrulanamaz." · "Çok sık deniyorsunuz…" · "Bu alan adı başka bir organizasyonda zaten doğrulanmış." | Tekrar Dene |

*Opsiyonel bloklar (veri backend'den gelmedikçe çizilmez/uygulanmaz):* sayaç kartları ve "Sizden aksiyon bekleyenler" listesi; öğrenciye gönderilecek "Çalışma başlatma bağlantısı" kopyalama kutusu (bkz. Açık noktalar).

**Durumlar:** iskelet · bulunamadı · hata + "Tekrar dene".

---

### 15. Yeni kuruluş — `/kurulus/olustur`

**Genişlik:** 560px. Geri linki yok (navbar var).
- H1 "Yeni Organizasyon Oluştur" → 14px ikincil açıklama "Kuruluşunuzu oluşturun; alan adınızı daha sonra doğrulayarak güven seviyenizi yükseltebilirsiniz."
- Alanlar: **Ad** · **Alan Adı** (ops., placeholder "ornek.com", yardım "Daha sonra bu alan adını doğrulayabilirsiniz. Boş bırakırsanız doğrulama bölümü gösterilmez.") · **Ticari Sicil No** (ops., Mono input).
- **[Oluştur — Birincil md]** sola hizalı → başarı → **`/kurulus/{yeni id}/panel`**.
- Hatalar: "Bu ticari sicil numarası zaten kayıtlı." (alan altı) · "Ad veya alan adı geçersiz. Lütfen kontrol edin." (form üstü).

---

### 16. Kurum paneli — `/kurum/[id]/panel` (en büyük ekran)

**Kim:** üniversite yöneticisi/koordinatörü. **Genişlik:** 1040px.

**Veri:** `summary.pending_approval`, `summary.pending_evaluation` · `pending_approval[]` (`id`, `title`, `started_on`) · `pending_evaluation[]` (`id`, `title`, `ended_on`) · `members[]` (`user_id`, `email`, `role`) · bağlanma talepleri (`id`, `talent_full_name`).

**Düzen:**

| # | Bölüm | Konum | İçerik |
|---|---|---|---|
| 1 | Başlık | üst | 12px ikincil "Kurum Paneli" → H1 Serif kurum adı |
| 2 | **Sayaç satırı** | 32px altı | 2 sayaç kartı yan yana (her biri 240px): **Onay Bekleyen** (sayı aşı) · **Değerlendirme Bekleyen** (sayı aşı). Kart tıklanınca ilgili bölüme kaydırır. |
| 3 | **Bekleyen Bağlanma Talepleri** | 40px altı | H2 + yanında sayı rozeti. Liste kartı: her satır 56px — sol avatar 32px + ad 15px 500 + 13px ikincil tarih (varsa) · sağ **[Onayla — Birincil sm] [Reddet — Tehlikeli outline sm]**. Onaylanan/reddedilen satır kaybolur (animasyonlu) + toast "Talep onaylandı." / "Talep reddedildi." Boş: "Bekleyen bağlanma talebi yok." |
| 4 | **Onay Bekleyen Stajlar** | 40px altı | H2 → tablo: Başlık · Başlangıç (tarih) · durum rozeti "Onay Bekliyor". Boş: "Onay bekleyen staj yok." |
| 5 | **Değerlendirme Bekleyen Stajlar** | 40px altı | H2 + sağda (başlıkla aynı hizada) **[Seçilenlere Hatırlatma Gönder — Outline md, ikon `bell`]** (seçim yoksa devre dışı; seçim varsa metin "Seçilenlere hatırlatma gönder (3)"). Tablo: ilk sütun onay kutusu (başlıkta **"Tümünü seç"** kutusu) · Başlık · Bitiş (tarih) · rozet "Değerlendirme Bekliyor". Seçili satır zemini çam %10. Başarı toast "Hatırlatma kuyruğa alındı." Hata "Hatırlatma gönderilemedi." · "Önce en az bir staj seçin." Boş: "Değerlendirme bekleyen staj yok." |
| 6 | **Üyeler** | 40px altı | H2 → tablo: E-posta · Rol rozeti (Yönetici / Koordinatör). Altında 24px boşlukla **Üye Davet Et** satırı (kum zeminli kutu): E-posta · Rol (Yönetici / Koordinatör) · **[Davet Gönder — Nötr md]**. Boş: "Henüz üye yok." |

*Öneri:* tablolardaki staj satırları `/calismalar/{id}`'ye tıklanabilir olsun (bugün tıklanmıyor).

**Durumlar:** sayaç + tablo iskeletleri; hata kartı + "Tekrar dene"; bağlanma talepleri ayrı yüklenir — kendi iskeleti ve hatası ("İşlem sırasında bir hata oluştu.").
**Mobil:** sayaç kartları yan yana küçülür (2 kolon); tablolar karta döner; hatırlatma butonu bölüm başlığının altına tam genişlik.

---

### 17. Yeni kurum — `/kurum/olustur`

**Genişlik:** 560px.
- H1 "Yeni Kurum Oluştur" → 14px ikincil açıklama "Üniversitenizi veya bölümünüzü oluşturun; öğrencileriniz bağlantınızla kurumunuza bağlanabilir."
- Alan: **Ad**. **[Oluştur — Birincil md]** sola hizalı → başarı → **`/kurum/{yeni id}/panel`**.

---

### 18. Kuruma bağlan — `/kurum/[id]/baglan`

**Kim:** öğrenci, kurumun bağlantısıyla gelir. **Genişlik:** 560px.
- H1 "Kuruma Bağlanma Talebi" → kurum adı (Serif 20px, varsa) → 16px → 15px metin "Bu kuruma bağlanma talebi göndermek istediğinize emin misiniz? Talebiniz kurum koordinatörünün onayına sunulacak."
- Butonlar sola hizalı: **[Talep Gönder — Birincil md]** · [Vazgeç — hayalet] → `/profil`.
- **Başarı:** butonlar yerine Başarı kutusu "Bağlanma talebiniz gönderildi. Koordinatörünüzün onayını bekleyin." + metin link **"Profiline dön"** → `/profil`.
- Hatalar: "Bu kuruma zaten bekleyen bir talebiniz var." (Uyarı + "Profiline dön") · "Kurum bulunamadı." · "Talep gönderilirken bir hata oluştu."

---

### 19. Admin — Kurum doğrulama kuyruğu — `/admin/dogrulama-kuyrugu`

**Kim:** platform admini. **Genişlik:** 1040px.
- H1 "Kurum Doğrulama Kuyruğu" → 14px ikincil "{n} bekleyen istek".
- **Tablo:** Kurum Adı · Ticari Kayıt (Mono) · Domain (Mono) · Doğrulama Seviyesi (mevcut, `TrustLevelBadge`) · Tarih · **Aksiyon** (en sağ).
- **Aksiyon hücresi** (sağa hizalı, 8px aralık): seviye select (sm, 140px; seçenekler T0–T3, yanında insan dili etiket) · **[Onayla — Birincil sm]** · **[Reddet — Tehlikeli outline sm]** → dialog (başlık "Başvuruyu reddet", gerekçe alanı, [Vazgeç] [Reddet — Tehlikeli]).
- İşlenen satır kaybolur + toast "Doğrulama seviyesi güncellendi" / "Başvuru reddedildi". Uyarı: "Kurum artık doğrulama kuyruğunda değil."
- Boş: ikon `shield-check` + "Bekleyen doğrulama isteği yok".
- **Mobil:** satırlar karta döner; aksiyonlar kart altında.

---

### 20. Admin — Yetkinlik yönetimi — `/admin/skiller`

**Kim:** platform admini. **Genişlik:** 1040px.

| # | Bölüm | İçerik |
|---|---|---|
| 1 | Başlık satırı | Sol H1 "Yetkinlik Yönetimi". Sağ **[Yeni yetkinlik — Birincil md, `plus`]** → **dialog** "Yeni Yetkinlik Oluştur": Slug (Mono) · Adı (Türkçe) · Kategori (Dil / Alan / Araç / Framework) → [Vazgeç] [**Oluştur**]. Hata "Bu slug zaten kullanımda." Başarı toast "Yetkinlik oluşturuldu". *(Kodda form sayfa içinde; dialog önerilir.)* |
| 2 | Arama + filtre | 24px altı: arama input (320px, `search` ikonu) + kategori select + durum select (Aktif / Devre Dışı / Birleştirilmiş) |
| 3 | Tablo | Slug (Mono) · Adı · Kategori · Durum rozeti (Aktif nötr / Devre Dışı uyarı / Birleştirilmiş nötr+ok) · Üst Yetkinlik ("Kök seviye" ikincil) · Hedef (birleştirildiyse) · en sağda **satır menüsü** (hayalet ikon `more-horizontal` → dropdown: Düzenle · Birleştir · çizgi · **Devre Dışı Bırak** (tuğla)) |

- **Birleştir dialog'u:** "Yetkinliği Birleştir" · Hedef Yetkinlik (arama alanı) · [İptal] [**Onayla**].
- **Devre Dışı Bırak:** onay dialog'u → [Vazgeç] [Devre Dışı Bırak — Tehlikeli].
- Boş: "Henüz bir yetkinlik yok".

---

### 21. 404 ve hata sayfaları

**Kabuk yok; landing üst barı var.** İçerik sola hizalı, 560px, üstten 96px.
- **404:** kesik çizgili boş mühür dairesi (64px, ikincil) → 24px → H1 Serif "Sayfa bulunamadı" → 8px → 15px ikincil "Aradığınız sayfa bulunamadı." → 24px → butonlar sola hizalı: **[Ana Sayfaya Dön — Birincil md]** → `/` · **[Giriş Sayfasına Dön — Outline md]** → `/giris`.
- **Genel hata:** aynı düzen; H1 "Bir şeyler ters gitti" + "İşlem sırasında bir hata oluştu. Lütfen tekrar deneyin." + destek kodu kutusu → **[Tekrar dene — Birincil]** · [Ana sayfaya dön — Outline].

---

## 7. Navigasyon haritası

| Nereden | Buton / link | Nereye |
|---|---|---|
| `/` | Giriş Yap (üst bar) | `/giris` |
| `/` | Kayıt Ol (üst bar + hero) | `/kayit` |
| `/` | Örnek Bir Doğrulamayı İncele | bugün `/giris` → hedef `/v/{demo-token}` |
| `/giris` | Giriş Yap (başarı) | `?next=` veya `/calismalar` |
| `/giris` | Kayıt Ol / Şifremi Unuttum | `/kayit` / `/sifre-unuttum` |
| `/kayit` | Kayıt Ol (başarı) | 0.8 sn sonra `/giris` |
| `/kayit` | Giriş Yap | `/giris` |
| `/sifre-unuttum` | Giriş sayfasına dön | `/giris` |
| `/sifre-sifirla` | Giriş Yap (başarı) / Yeni bağlantı iste | `/giris` / `/sifre-unuttum` |
| `/e-posta-dogrula` | Giriş Yap / Kayıt Ol | `/giris` / `/kayit` |
| Navbar | Çalışmalarım / Profil / Herkese açık profilim | `/calismalar` / `/profil` / `/p/{slug}` (yeni sekme) |
| Navbar | {Kuruluş} / {Kurum} | `/kurulus/{id}/panel` / `/kurum/{id}/panel` |
| Navbar | Kurum Doğrulama / Yetkinlik Yönetimi | `/admin/dogrulama-kuyrugu` / `/admin/skiller` |
| Navbar kullanıcı menüsü | Çıkış | `/giris` |
| `/calismalar` | Çalışma kartı | `/calismalar/{id}` |
| `/calismalar/{id}` | ← Çalışmalara dön | `/calismalar` |
| `/calismalar/{id}` | Değerlendirme Formu (PENDING_EVALUATION) | `/calismalar/{id}/degerlendirme` |
| `/calismalar/{id}/degerlendirme` | ← Çalışmaya dön / (başarı) Çalışmaya dön | `/calismalar/{id}` |
| `/calismalar/olustur` | Oluştur (başarı) | `/calismalar/{yeni id}` |
| `/profil` | Herkese açık profili gör | `/p/{slug}` (yeni sekme) |
| `/kurulus/olustur` | Oluştur (başarı) | `/kurulus/{yeni id}/panel` |
| `/kurum/olustur` | Oluştur (başarı) | `/kurum/{yeni id}/panel` |
| `/kurum/{id}/baglan` | Profiline dön / Vazgeç | `/profil` |
| `/v`, `/p` | Logo / Yetkin360 nedir? | `/` |
| 404 | Ana Sayfaya Dön / Giriş Sayfasına Dön | `/` / `/giris` |
| Oturum süresi doldu (kabuk) | Giriş yap | `/giris` |

---

## 8. Açık noktalar (tasarımcı bilsin; kod/backend kararı gerekir)

1. **"Örnek Bir Doğrulamayı İncele"** bugün `/giris`'e gidiyor (test sabitlemiş). Doğrusu seed'deki bir `/v/{token}`. Değişiklik kod + test işi.
2. **Öğrenci çalışmaya nasıl başlıyor?** `/calismalar/olustur?organization_id=…` bağlantısını kuruluşun paylaşacağı bir yer arayüzde yok. Kuruluş panelinde "Çalışma başlatma bağlantısı — kopyala" kutusu önerilir.
3. **Kuruma bağlanma bağlantısı** (`/kurum/{id}/baglan`) da kurum panelinde gösterilmiyor; aynı kopyala kutusu önerilir.
4. **Durum geçiş butonları role göre filtrelenmiyor** (`/me` rol bilgisi döndürmüyor); yetkisiz kullanıcı butonu görür, sunucu reddeder. Tasarım hata durumunu içermeli.
5. **Profil → Yetkinlikler** listesi kanıt sayısı/doğrulanmışlık döndürmüyor. "Beyan vs. doğrulanmış" görsel ayrımı için ya kanıt dökümünden eşleme ya da API alanı gerekir.
6. **`/p/[slug]`** deneyimleri `/v/{token}`'a bağlanamıyor (API token vermiyor).
7. **Kurum paneli** staj satırlarında öğrenci adı yok (yalnız başlık + tarih); satırlar tıklanabilir değil.
8. **Navbar'daki kuruluş/kurum adları:** `/me` yanıtında `organizations[]` / `institutions[]` alanları tipsiz; adların gelip gelmediği doğrulanmalı.
9. **"Kuruluş yok" şeridi** öğrencilere de çıkıyor; yalnız ilgili kullanıcılara gösterilmesi önerilir.
10. **Toast, Dialog, Sekme, Dropdown** bileşenleri ve **lucide** ikonları kodda henüz yok; uygulama aşamasında bağımlılık onayı gerekir.
11. Kodda çoğu sayfa hâlâ eski `slate-*` / `red-*` / `blue-*` renklerinde; bu brif uygulandığında hepsi token'lara çevrilecek.
