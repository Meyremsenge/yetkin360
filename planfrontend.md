# planfrontend.md — Frontend'i sunulabilir hale getirme planı

> **Amaç:** 4 gün içinde frontend'i "çalışan iskelet"ten **zanaatle yapılmış, doğal, güven veren** bir ürüne dönüştürmek. Ölçüt "sunulabilir" değil: jüri ekranı görünce "bunu bir tasarımcı mı yaptı?" diye sormalı.
> **Görsel çizgi:** Mor yok, cırtlak renk yok, gradyan yok, "yapay zekâ ürünü" görünümü yok. Kâğıt, mürekkep, mühür: resmî bir belge kadar ciddi, iyi basılmış bir kitap kadar sıcak (§1).
> **Kapsam kuralı:** Yeni **özellik** yok. Var olan ekranların **görünümü, akışı ve anlatımı** yeniden yapılır.
> Backend'e dokunulmaz (Faz 0'daki migration hariç). Her ekran, mevcut API'yi ve mevcut testlerin davranış beklentisini korur.
>
> Durum: `[ ]` yapılmadı · `[~]` sürüyor · `[x]` bitti. Her görev kodu (`FE-xx`) commit gövdesine yazılır.

---

## 0. Teşhis — neden "berbat" görünüyor?

### 0.1 Ekran görüntülerinden

| Ekran | Sorun |
|---|---|
| `/` (landing) | Beyaz sayfa ortasında başlık + bir cümle + bir buton. Ürünün ne yaptığı, kimin için olduğu, neden farklı olduğu anlatılmıyor. Kayıt linki yok. |
| `/giris` | Sayfanın ortasında çıplak form. Marka yok, kayıt / şifremi unuttum bağlantıları görsel olarak zayıf, karşılama hissi yok. |
| `/calismalar` (hata) | Tüm ekranı kaplayan tek bir kırmızı kutu. Kullanıcı nerede olduğunu, ne yapacağını bilmiyor; navigasyon bile yok. |

### 0.2 Koddan

| Bulgu | Kanıt | Etkisi |
|---|---|---|
| **Tasarım sistemi yok** | `globals.css` 9 renk token'ı; kod içinde **652** adet sabit renk sınıfı (`bg-slate-50`, `text-red-700`…). `dark:` kullanımı 0. | Her sayfa kendi kafasına göre renkleniyor; tutarlılık yok. |
| shadcn/ui kararı uygulanmamış | `components/ui/` elle yazılmış 6 ilkel; Radix yok, ikon kütüphanesi yok. | Dialog, menü, sekme, toast yok → ekranlar uzun dikey form yığını. |
| **Navigasyon eksik** | `app-shell.tsx`: yalnız "Çalışmalar", "Profil", admin linkleri. `/kurum/[id]/panel` ve `/kurulus/[id]/panel`'e **hiçbir yerden link yok**. | Kurum ve kuruluş yöneticileri kendi panellerine ulaşamıyor (URL elle yazılmazsa). Girişten sonra herkes `/calismalar`'a düşüyor. |
| Ekranlar "form yığını" | `calismalar/[id]/page.tsx`: başlık + `dl` + 5 form + 3 liste alt alta. | Ürünün kalbi olan zincir (beyan→kanıt→tanıklık→doğrulama) görünmüyor. |
| Public sayfalar ham | `/v/[token]`, `/p/[slug]`: beyaz kart + metin; `trust_level` "T1/T2" diye çıplak basılıyor, `claim_type` enum adı olarak görünüyor. | **Jürinin telefonundan açacağı sayfa** bu — en çok göz önünde olan ekran en zayıfı. |
| Font Türkçe karakter alt kümesini yüklemiyor | `layout.tsx`: `Inter({ subsets: ["latin"] })` → `ş ğ ı İ` için `latin-ext` yok. | Türkçe harfler yedek fonttan geliyor, yazı tipi karışık görünüyor. |
| Yükleme / boş durum | Her yerde `<p>Yükleniyor…</p>` ve "Henüz yok" metni. | Ekran titriyor; boş durumlar ne yapılacağını söylemiyor (`.claude/rules/frontend.md` ihlali). |
| Hata ekranı tüm kabuğu yutuyor | `app-shell.tsx` oturum hatasında yalnız `ErrorBanner` render ediyor. | Kullanıcı çıkış bile yapamıyor; marka/navigasyon kayboluyor. |

### 0.3 Senin gördüğün hatanın asıl sebebi (frontend değil) ⚠️

Test ettim: seed öğrenci hesabıyla giriş **çalışıyor**, `/me` 200 dönüyor, ama `GET /engagements` **500** dönüyor:

```
psycopg.errors.UndefinedColumn: column engagements.completed_at does not exist
```

`alembic current` → `b7d3f19a4e26`, `alembic heads` → `d85a0529f295`. GitHub'dan çekilen kod yeni şemayı bekliyor, yerel veritabanı geride. **Faz 0'da `alembic upgrade head` ile düzelir** (CLAUDE.md gereği önce onayın gerekiyor). Bu düzelmeden hiçbir sayfa doğru görülemez ve yeniden tasarım doğrulanamaz.

---

## 1. Tasarım yönü — "Kâğıt, mürekkep, mühür"

Ürünün tek iddiası **kanıt**. Kanıtın insanlıktaki en eski biçimi de belgedir: iyi kâğıda basılmış, imzalı, mühürlü. Görsel dil buradan gelir:

- **Kâğıt:** sıcak, kırık beyaz zemin; saf beyaz yalnız kartlarda.
- **Mürekkep:** sıcak, neredeyse siyah metin ve ana butonlar. Marka rengi bağırmaz.
- **Mühür:** tek güçlü renk **derin çam yeşili** ve yalnız *doğrulanmış* şeylerde kullanılır. Ekranda yeşil görmek "bu kanıtlandı" demektir; bu yüzden değerlidir, her yere serpiştirilmez.

Hedeflenen his: sakin, kendinden emin, sıcak. Bir belediye formu kadar soğuk değil, bir startup landing'i kadar gürültülü de değil. Referans duygusu: iyi bir üniversite yayınevinin kitap kapağı, bir noter belgesi, Linear/Stripe dokümanlarının sadeliği ama sıcak tonlarda.

### 1.0 "Yapay zekâ gibi görünmesin" — yasak listesi

Bunlar bugün "yapay zekâ yaptı" hissini veren kalıplar. Hiçbiri kullanılmaz:

| Yasak | Yerine |
|---|---|
| Mor, menekşe, indigo, neon pembe; mor→mavi **gradyanlar** | Düz, doğal renkler (§1.2). Gradyan hiç yok. |
| Arka planda bulanık renk lekeleri (blob), "glow", cam efekti (glassmorphism) | Düz kâğıt zemin; ayrımı ince çizgiler (1px hairline) ve boşluk yapar |
| ✨ ikonu, emoji başlıklar, "sparkles", robot/beyin görselleri | Az ve anlamlı ikon (lucide, 1.5px çizgi), yalnız işlevi olan yerde |
| Her kartta kalın gölge, `rounded-3xl` balon kartlar | Hafif köşe (`8px`), gölge yalnız açılır katmanlarda (menü, dialog) |
| Hazır illüstrasyon setleri, yapay zekâ üretimi görseller, stok fotoğraf | **Ürünün kendisi görsel olur:** landing'deki ana görsel gerçek bir doğrulama sertifikasının bileşenle çizilmiş hali |
| "Geleceğin…", "devrim niteliğinde", "yapay zekâ destekli", "🚀 Hemen başla!" | Somut, sakin Türkçe: ne olduğunu ve ne işe yaradığını söyleyen cümleler (§1.5) |
| Her şeyi ortalamak; ortada küçük kart, etrafı bomboş | Sola hizalı, editoryal düzen; bilinçli asimetri ve ızgara |
| Inter + `text-slate-*` her yerde (varsayılan "Tailwind şablonu" görünümü) | Karakterli yazı tipi eşleşmesi (§1.3), sıcak gri tonlar |
| Animasyonlu sayaçlar, zıplayan butonlar, parıltı efektleri | 150–200 ms sade geçişler; hareket yalnız durum değişimini anlatır |
| Karanlık mod / renkli temalar arasında kararsızlık | Tek, iyi yapılmış açık tema |

### 1.1 İlkeler

1. **Zincir her yerde görünür.** `Beyan → Kanıt → Tanıklık → Doğrulanmış deneyim` bir bileşen (`ChainProgress`) olarak landing'de, çalışma detayında ve `/v/[token]`'da aynı görünür. Jüri ürünün ne yaptığını tek bakışta görür.
2. **Doğrulama = mühür.** Doğrulanmış her öğe aynı yeşil mühür/rozetle işaretlenir; beyan (doğrulanmamış) her zaman nötr/gri. Kullanıcı ikisini asla karıştırmaz.
3. **Rol bazlı ana sayfa.** Öğrenci, kuruluş, kurum, admin girişte **kendi** ekranına düşer ve menüsü kendi işini gösterir.
4. **Boş durum = yönlendirme.** Her boş liste: ikon + 1 cümle açıklama + bir sonraki adım butonu.
5. **Mobil öncelik yalnız public sayfalarda.** `/v` ve `/p` telefonda kusursuz; panel ekranları masaüstü öncelikli ama mobilde kırılmaz.

### 1.2 Token seti (`globals.css` + `tailwind.config.ts`)

Tüm renkler HSL token; bileşenler **yalnız token** kullanır (yeni kodda sabit `slate-*` / `red-*` / `blue-*` yasak). Palet bilinçli olarak **dar**: 1 nötr aile (sıcak gri) + 1 marka rengi (çam yeşili) + 2 durum rengi (aşı boyası, tuğla). Mavi ve mor paletin içinde **hiç yok**.

| Token | Rol | HSL | Hex |
|---|---|---|---|
| `--paper` (`background`) | Sayfa zemini, sıcak kırık beyaz | `40 30% 97%` | `#FAF8F5` |
| `--card` | Kart / yüzey | `40 33% 99.5%` | `#FEFEFD` |
| `--sand` (`muted`) | İkincil yüzey, tablo başlığı, seçili satır | `38 20% 92%` | `#EFECE7` |
| `--ink` (`foreground`, `primary`) | Metin + ana buton (mürekkep) | `30 12% 12%` | `#221F1B` |
| `--ink-soft` (`muted-foreground`) | İkincil metin, etiket | `30 7% 36%` | `#625C55` |
| `--line` (`border`) | 1px çizgiler, kenarlık | `36 16% 86%` | `#E1DCD6` |
| `--pine` (`verified`, `ring`) | **Mühür**: doğrulanmış, link, focus halkası | `160 38% 24%` | `#265445` |
| `--pine-wash` | Doğrulanmış öğe zemini | `150 25% 93%` | `#E9F2ED` |
| `--ochre` / `--ochre-wash` | Bekleyen, onay bekliyor, beyan uyarısı | `34 75% 32%` / `40 65% 92%` | `#8F5A14` / `#F8EFDD` |
| `--brick` / `--brick-wash` | Hata, red, iptal, geri alındı | `8 58% 40%` / `10 60% 95%` | `#A13B2B` / `#FAEDEB` |
| `--radius` | Köşe | `0.5rem` | |

**Kontrast (WCAG, hesaplandı):** mürekkep/kâğıt **15.5:1** · ikincil metin/kâğıt **6.2:1** · ikincil metin/kum **5.6:1** · çam/kâğıt **8.1:1** · beyaz yazı/çam buton **8.57:1** · aşı boyası/zemini **5.46:1** · tuğla/zemini **6.25:1**. Hepsi ≥ 4.5:1. FE-04 bunu kodda tekrar doğruladı — _(düzeltme: son 3 değer (beyaz/çam, aşı/zemin, tuğla/zemin) ilk hesaplamada hatalıydı; standart WCAG formülüyle `frontend/lib/ui/contrast-ratio.ts`'te doğrulanan gerçek değerler kullanılıyor, bkz. `obss_project/artifacts/fe04-kontrast-testi/`)_.

Kullanım oranı (göz kararı): **%90 kâğıt + mürekkep + çizgi**, %8 kum, %2 renk. Bir ekranda yeşil çoksa, yanlış bir şeyler doğrulanmış gibi görünüyordur. Koyu tema **yapılmaz** (`color-scheme: light` kalır).

### 1.3 Tipografi — Inter'den çık, karakter kazan

Varsayılan Inter + Tailwind, ürünü "şablon" gibi gösteren en büyük tek etken. Yeni eşleşme (hepsi `next/font/google`, npm bağımlılığı değil, hepsi `latin-ext`, yani Türkçe tam):

| Rol | Yazı tipi | Neden |
|---|---|---|
| Başlık / display | **Source Serif 4** (opsz, 500–600) | Belge, sertifika, yayın hissi. Ürünün "kanıt" iddiasını tipografi taşır. |
| Gövde / arayüz | **IBM Plex Sans** (400, 500, 600) | Kurumsal ama insani; Türkçe'de çok iyi okunur; Inter'den belirgin farklı. |
| Kod / doğrulama kodu / destek kodu / tarih damgası | **IBM Plex Mono** (400) | Sertifika numarası, `request_id` gibi alanlara "resmî kayıt" görünümü verir. |

- Ölçek: `display 56/60 serif` (yalnız landing hero) · `h1 32/40 serif` · `h2 22/30 serif` · `h3 16/24 sans 600` · gövde `15/24` · küçük `13/20` · etiket `12/16 sans 500, harf aralığı +0.02em, BÜYÜK HARF yok`.
- Serif yalnız başlıklarda ve sertifika adında; form, tablo, buton hep sans.
- Satır uzunluğu metin bloklarında `max-w-[65ch]`.
- Sayılar `tabular-nums`; tarihler Türkçe ve tam: "12 Eylül 2026". Göreli tarih ("3 gün önce") yalnız listelerde, üstüne gelince tam tarih görünür.

### 1.4 Görsel ayrıntılar (şaheser farkı burada)

- **Logo:** El işi, tipografik bir wordmark: serif "Yetkin" + ince çizgiyle ayrılmış "360", yanında küçük, yuvarlak, mühür izi gibi bir işaret (SVG, tek renk mürekkep). Hazır ikon değil. Favicon aynı işaretten.
- **Mühür bileşeni (`VerifiedSeal`):** Dairesel, ince çift çizgili kenar, ortada onay işareti, çevresinde Plex Mono ile küçük "DOĞRULANDI · 2026". Damga gibi hafif (−4°) eğik durur. Yalnız `/v` ve `/p`'de büyük boyda, diğer yerlerde küçük rozet.
- **Çizgiler, gölge değil:** Bölümler 1px `--line` ile ayrılır. Gölge yalnız dropdown, dialog, toast'ta (`0 8px 24px -12px rgb(34 31 27 / 0.25)`).
- **Kâğıt dokusu:** Yalnız `/v` sertifika kartında, çok hafif bir kâğıt grenı (inline SVG `feTurbulence`, opaklık ≤ %4). Başka hiçbir yerde doku yok.
- **Izgara:** 12 kolon, içerik `max-w-6xl`; landing'de editoryal asimetri (metin 7 kolon, görsel 5 kolon). Panellerde sol hizalı başlık, sağda aksiyon.
- **Boşluk:** 4'ün katları; bölümler arası cömert (landing'de `py-24`, panellerde `space-y-10`). Sıkışıklık ucuz görünür.
- **Hareket:** Sayfa geçişinde yok. Dialog/menü 150 ms opaklık + 4px kayma. Zincir adımı tamamlanınca çizgi 400 ms'de dolar (tek "keyif anı"). `prefers-reduced-motion` ile hepsi kapanır.
- **İkonlar:** lucide, 1.5px çizgi, 16/20px. Her ikon bir işlevi anlatır; süs ikonu yok. Boş durumlarda büyük ikon yerine ince çizimli tek bir sembol + metin.
- **Odak (focus):** 2px çam yeşili halka + 2px kâğıt boşluk. Klavye kullanıcısı için de güzel görünür.

### 1.5 Ses ve dil (mikro metinler)

Tasarımın yarısı metindir. `tr.json` baştan bu tona göre elden geçirilir (FE-34):

- Sakin, net, "siz" dili. Ünlem yok, emoji yok, abartı yok.
- Buton = fiil: "Kanıt yükle", "Tanıklık ver", "Doğrulamayı görüntüle". "Gönder", "Tamam" gibi belirsiz etiketlerden kaçın.
- Hata mesajı ne olduğunu ve ne yapılacağını söyler: "Dosya 10 MB'tan büyük. Daha küçük bir dosya seçin." Teknik kod (`request_id`) küçük ve ikincil: "Destek kodu".
- Boş durum davet eder: "Henüz bir çalışmanız yok. Kurumunuz bir staj tanımladığında burada görünecek." gibi.
- Landing'deki slogan örnek tonu: **"Söylediğin değil, kanıtladığın."** Alt metin: "Yetkin360'ta her yetkinlik bir çalışmaya, bir çıktıya ve onu gören bir tanığa dayanır."

### 1.6 Durum → zincir eşlemesi (görsel dilin omurgası)

| Engagement durumu | Zincir adımı | Renk |
|---|---|---|
| `DRAFT`, `PENDING_APPROVAL` | 1 · Beyan | mürekkep (taslak) / aşı boyası (onay bekliyor) |
| `ACTIVE` | 2 · Kanıt | mürekkep |
| `PENDING_EVALUATION`, `EVALUATED` | 3 · Tanıklık | aşı boyası (bekleyen) / mürekkep |
| `VERIFIED`, `RESOLVED` | 4 · Doğrulanmış deneyim | **çam yeşili (mühür)**, yalnız burada |
| `REJECTED`, `CANCELLED`, `DISPUTED` | zincir kırık (ilgili adımda tuğla işaret) | tuğla |

Bu tablo tek bir yerde (`lib/ui/status.ts`) tutulur; liste rozeti, detay stepper'ı ve panellerdeki sayaçlar buradan beslenir. Bugünkü `STATUS_BADGE_CLASS` (`app/calismalar/page.tsx`) buraya taşınır.

---

## 2. Onay gereken kararlar (başlamadan önce)

CLAUDE.md gereği bunlar senin onayın olmadan yapılmaz:

| # | Karar | Öneri | Gerekçe |
|---|---|---|---|
| K-1 | `alembic upgrade head` (yerel DB) | **Evet, hemen** | 0.3'teki 500 hatası; yoksa hiçbir ekran test edilemez. |
| K-2 | `lucide-react` bağımlılığı | **Evet** | İkonsuz arayüz "bitmemiş" görünür. Tek paket, tree-shake edilir, MIT. |
| K-3 | Radix ilkelleri: `@radix-ui/react-dialog`, `@radix-ui/react-dropdown-menu`, `@radix-ui/react-tabs`, `@radix-ui/react-slot` | **Evet (yalnız bu 4)** | Final analiz §14.2 zaten shadcn/ui (Radix) kararı vermiş; erişilebilir menü/sekme/dialog'u elle yazmak 4 günde riskli. shadcn kopyala-yapıştır yaklaşımı: bileşen kodu repoya girer, CLI gerekmez. |
| K-4 | Toast için `sonner` | Opsiyonel | Form başarı/hata geri bildirimi. Alternatif: mevcut `Alert` ile satır içi mesaj (bağımlılıksız). |
| K-5 | Primitive testlerinin güncellenmesi | **Evet** | `components/ui/*.test.tsx` sınıf adlarını birebir doğruluyor (button 70, alert 47 eşleşme). Görünüm değişince bunlar **bilerek** güncellenir; davranış testleri (sayfa testleri) dokunulmadan geçmeli. |
| K-6 | Girişten sonra rol bazlı yönlendirme | **Evet** | `DEFAULT_AFTER_LOGIN = "/calismalar"` sabiti → `/me` yanıtına göre hedef seçimi (yalnız UX, yetki sunucuda). |

---

## 3. Fazlar ve görevler

Öncelik etiketi: **P0** = demo zincirinde görünür, kesin yapılır · **P1** = demoda gösterilir · **P2** = vakit kalırsa.

### Faz 0 — Demo engelleri (Gün 1, ilk 1 saat)

- [x] **FE-00** `alembic upgrade head` (K-1 onayıyla) → `GET /engagements` 200 doğrula. **P0** _(zaten güncel bulundu: `alembic current` = `d85a0529f295` = heads; 177 engagement testi PASS ile doğrulandı, migration çalıştırmaya gerek kalmadı)_
- [ ] **FE-01** Seed hesaplarının her rolle giriş yapabildiğini doğrula (öğrenci, kuruluş admini, kurum admini/koordinatör, platform admini) ve hangi hesabın hangi ekranı göstereceğini `§5` tablosuna yaz. **P0**
- [ ] **FE-02** Seed verisinde en az bir `VERIFIED` çalışma + paylaşılabilir `/v/[token]` ve `public_slug`'lı bir profil olduğunu doğrula (yoksa PLAN 3.28 ile birlikte ele al — backend işi, ayrı onay). **P0**

### Faz 1 — Tasarım sistemi temeli (Gün 1)

Hedef: sayfalara dokunmadan önce her sayfanın kullanacağı yapı taşları hazır.

- [x] **FE-03** Token'lar + font: `globals.css`, `tailwind.config.ts` (`§1.2`, `§1.3`); `layout.tsx`'te Inter kaldırılır, Source Serif 4 + IBM Plex Sans + IBM Plex Mono (`latin-ext`) eklenir. Tailwind'in varsayılan renkleri config'den **çıkarılmaz** (dönüştürülmemiş ekranlar renksiz kalır); onun yerine FE-30'daki `grep` sayacı her gün izlenir ve yeni kodda sıfır olmalıdır. **P0** _(commit `81eb150`, `obss_project/artifacts/fe03-token-font-degisimi/`)_
- [x] **FE-04** Kontrast kontrolü: §1.2'deki hesaplanmış değerleri token'lar koda girdikten sonra küçük bir unit testle sabitle (renk değişirse test kırılır). **P0** _(commit sırasında işaretlenecek, `obss_project/artifacts/fe04-kontrast-testi/`)_
- [ ] **FE-05** İlkellerin yeniden yazımı (`components/ui/`): `Button` (variant: primary/secondary/outline/ghost/destructive, `loading` durumu, ikon desteği, görünür focus ring), `Input`, `Textarea`, `Select`, `Label`, `Card` (+`CardHeader/CardTitle/CardContent/CardFooter`), `Badge`, `Alert`. Testler K-5'e göre güncellenir. **P0**
- [ ] **FE-06** Yeni ilkeller: `Skeleton`, `Spinner`, `Avatar` (baş harf), `Separator`, `Tabs`, `DropdownMenu`, `Dialog` (K-3). **P0**
- [ ] **FE-07** Ürün bileşenleri (`components/`): **P0**
  - `ChainProgress` — 4 adımlı zincir; `status` alır, aktif/tamam/kırık adımı gösterir. Landing'de statik, detayda canlı.
  - `StatusBadge` — `lib/ui/status.ts` eşlemesinden.
  - `VerifiedSeal` — §1.4'teki dairesel mühür (SVG, çift çizgi, Plex Mono yazı, −4° eğim); `size: sm | lg`.
  - `TrustLevelBadge` — `T1/T2/T3` yerine insan dili ("Doğrulanmamış kuruluş", "Alan adı doğrulanmış"…) + açıklama tooltip'i. Metinler `tr.json`'a.
  - `PageHeader` — başlık, açıklama, sağda aksiyon(lar), opsiyonel breadcrumb.
  - `EmptyState` — ikon, başlık, açıklama, aksiyon.
  - `StatCard` — panel sayaçları (değer, etiket, ikon, opsiyonel trend yok).
  - `ErrorState` — `ErrorBanner`'ın yerine geçen, kabuk içinde kalan hata kartı (mesaj, destek kodu küçük ve kopyalanabilir, "Tekrar dene").
- [ ] **FE-08** `lib/ui/status.ts`: durum→etiket/renk/zincir adımı eşlemesi + unit testi. **P0**

### Faz 2 — Kabuk ve navigasyon (Gün 1 sonu / Gün 2 başı)

- [x] **FE-09** `AppShell` yeniden düzeni: **P0**
  - Masaüstü: sol **sidebar** (logo, rol bazlı menü, altta kullanıcı kartı + çıkış dropdown'u). Mobil: üst bar + açılır menü (Dialog/Sheet).
  - Menü `/me` yanıtından türetilir:
    - Her kullanıcı: Çalışmalarım
    - `talent_profile` varsa: Profilim, Herkese açık profilim (`public_slug` varsa)
    - `organizations[]` her biri için: "{ad} paneli" → `/kurulus/{id}/panel`
    - `institutions[]` her biri için: "{ad} paneli" → `/kurum/{id}/panel`
    - `is_platform_admin`: Doğrulama kuyruğu, Yetkinlik kataloğu
  - Aktif sayfa vurgusu (`usePathname`).
  - Banner'lar (e-posta doğrulama, kuruluş yok, çıkış hatası) içerik alanının üstünde tek bir `Alert` yığını olarak.
  - Yükleme: tam ekran "Yükleniyor…" yerine kabuk iskeleti (`Skeleton`).
  - Oturum hatası: kabuk ve marka yerinde kalır, içerikte `ErrorState`; `SessionExpiredError` → girişe yönlendiren net mesaj.
  - Mevcut `app-shell.test.tsx` davranışları (AC-1, AC-5, AC-7, AC-8, AC-12, AC-S1) korunur; admin linki testleri yeni menü yapısına göre güncellenir.
- [ ] **FE-10** Rol bazlı giriş yönlendirmesi (K-6): `?next=` yoksa → kurum varsa kurum paneli, kuruluş varsa kuruluş paneli, admin ise doğrulama kuyruğu, aksi halde `/calismalar`. Saf fonksiyon + unit test (`lib/auth/landing-path.ts`). **P0**
- [ ] **FE-11** `not-found.tsx`, `error.tsx`, `global-error.tsx` yeni `ErrorState`/`EmptyState` ile; ana sayfaya ve geri dönüş linki. **P1**

### Faz 3 — Ekranlar (Gün 2-3)

Sıra demo akışına göredir (`§4`). Her ekran için "bitti" tanımı `§6`.

#### 3a. Public yüz (jürinin ilk ve son gördüğü)

- [ ] **FE-12** **Landing `/`** — **P0**
  - Üst bar: logo, "Giriş yap", "Kayıt ol".
  - Hero (editoryal, sola hizalı, 7/5 kolon): solda serif başlık **"Söylediğin değil, kanıtladığın."** + alt metin + 2 CTA (Kayıt ol / Örnek bir doğrulamayı incele). Sağda **görsel olarak ürünün kendisi**: gerçek bileşenlerle çizilmiş, hafif eğik duran bir doğrulama sertifikası kartı (`VerifiedSeal` + ad + yetkinlik çipleri). İllüstrasyon, stok görsel, gradyan yok.
  - **Zincir bölümü:** `ChainProgress` büyük boy, her adımın altında 1 cümle (kim yapar, ne üretir).
  - "Kimin için" 3 kart: Öğrenci · Kuruluş (işveren) · Kurum (üniversite). Her biri ne kazandığını söyler.
  - "Neden farklı" — beyan ile doğrulanmış deneyimin yan yana karşılaştırması: solda gri, mühürsüz bir CV satırı ("Python biliyorum"), sağda aynı yetkinliğin çalışma + çıktı + tanık + mühürle gösterimi.
  - Rakamlar şeridi (opsiyonel): seed'deki gerçek sayılar yoksa **konmaz**; uydurma istatistik yok.
  - Footer: açık kaynak notu + GitHub linki + lisans.
  - Tüm metin `tr.json` → `home.*`.
- [x] **FE-13** **`/v/[token]` doğrulama sayfası** — **P0, en kritik ekran**
  - "Sertifika" düzeni: kâğıt dokulu kart, ince çift çerçeve, sağ üstte büyük `VerifiedSeal`; serif ile kişi adı, rol/başlık, kuruluş, dönem. Altta Plex Mono ile doğrulama kodu ve tarih damgası. Telefonda açıldığında "gerçek bir belge" hissi vermeli.
  - `ChainProgress` tamamlanmış halde ("bu deneyim 4 adımdan geçti").
  - Tanıklık eden yetkinlikler: skill çipleri + tanıklık eden kuruluş.
  - Güven bilgisi: `TrustLevelBadge` + alan adı; T1 uyarısı nazik ama görünür.
  - "Bu sayfa Yetkin360 tarafından {tarih} tarihinde doğrulanmıştır" + doğrulama kodu.
  - Mobilde (375px) tek sütun, büyük dokunma alanları; `generateMetadata` ile sayfa başlığı ve OG başlık/açıklaması (link paylaşılınca düzgün önizleme). 404 için markalı boş durum.
- [x] **FE-14** **`/p/[slug]` public profil** — **P0**
  - Profil başlığı (Avatar baş harf, ad, başlık/bölüm, kurum).
  - Doğrulanmış deneyimler zaman çizelgesi; her biri `VerifiedSeal` ve `/v/...` linki (API veriyorsa).
  - `claim_type` enum yerine `tr.json` etiketi.
  - Boş durum: "Bu profilde henüz doğrulanmış deneyim yok."

#### 3b. Kimlik doğrulama

- [ ] **FE-15** **Auth düzeni** (`/giris`, `/kayit`, `/sifre-unuttum`, `/sifre-sifirla`, `/e-posta-dogrula`) — **P0**
  - Ortak `AuthLayout`: masaüstünde iki kolon — solda kum (`--sand`) zeminli marka paneli (wordmark, serif tek cümle, altta dört adımlı zincir ince çizgiyle), sağda kâğıt zeminde sade form (kart çerçevesi yok, form sayfaya oturur). Mobilde tek kolon, marka paneli üstte ince bir şerit.
  - Form: etiketler, satır içi hata (`aria-live`), şifre göster/gizle, gönderirken buton `loading`.
  - Giriş ↔ kayıt ↔ şifremi unuttum bağlantıları belirgin.
  - Mevcut form testleri (alan etiketleri, hata mesajları, yönlendirme) değişmeden geçmeli.

#### 3c. Öğrenci akışı

- [ ] **FE-16** **`/calismalar` liste** — **P0**
  - `PageHeader` + "Yeni çalışma" aksiyonu (yetkisi olan role).
  - Durum filtre sekmeleri (Tümü / Devam eden / Değerlendirmede / Doğrulanmış) — **yalnız istemci tarafı filtre**, yeni API yok.
  - Kart ızgarası: başlık, kuruluş, tür, `StatusBadge`, mini zincir (4 nokta), güncellenme tarihi (göreli: "3 gün önce").
  - Yükleme: 3 iskelet kart. Boş durum: role göre aksiyonlu `EmptyState`.
- [ ] **FE-17** **`/calismalar/[id]` detay** — **P0, demonun kalbi**
  - Üst: breadcrumb, başlık, kuruluş · tür, `StatusBadge`, sağda durum geçiş aksiyonları (`TransitionActions` → buton grubu / onay `Dialog`'u).
  - Hemen altında **canlı `ChainProgress`** + "Sıradaki adım" kartı (kimin ne yapması gerektiğini söyler; ör. "Kuruluşun değerlendirmesi bekleniyor").
  - `reason` varsa `Alert`.
  - **Sekmeler:** Görevler · Çıktılar & kanıtlar · Tanıklıklar · Değerlendirme.
    - Formlar (`TaskForm`, `DeliverableForm`, `EvidenceUploadForm`, `AttestationForm`) sekme içinde, "Ekle" butonuyla açılan kart/dialog olarak; listeler kart görünümü.
    - Kanıt yükleme: sürükle-bırak alanı görünümü, ilerleme çubuğu, dosya türü/boyut ipucu (davranış aynı).
    - Tanıklıklar: her biri skill + tanıklık eden + tarih; geri alınmışsa üstü çizili + "Geri alındı" rozeti.
  - Görev durumları ham enum (`task.status`) yerine `tr.json` etiketi.
- [x] **FE-18** **`/profil`** — **P0**
  - Üstte profil özeti kartı (avatar, ad, başlık, kurum, görünürlük rozeti, "Herkese açık profili gör / linki kopyala").
  - Sekmeler: Profil bilgileri · Yetkinlikler · Kanıt dökümü · Kurum bağlantısı.
  - Yetkinlikler: **beyan** (gri, "Beyan") ile **sinyal/doğrulanmış** (yeşil, kanıt sayısı) görsel olarak ayrışır — ürün iddiasının profildeki karşılığı.
  - `SkillPicker` arama + çip görünümü.
- [x] **FE-19** **`/calismalar/olustur`** — **P1** — tek kart form, adım açıklaması, kuruluş/kurum seçimi açık etiketli.

#### 3d. Kuruluş (işveren) ve kurum (üniversite)

- [ ] **FE-20** **`/kurulus/[id]/panel`** — **P1**
  - `PageHeader` (kuruluş adı + `TrustLevelBadge`).
  - `StatCard` satırı: aktif çalışma, değerlendirme bekleyen, doğrulanmış (mevcut yanıt verisinden sayılır).
  - "Sizden aksiyon bekleyenler" listesi (onay bekleyen, değerlendirme bekleyen) en üstte.
  - Mevcut bölümler kart/tablo olarak.
- [ ] **FE-21** **`/kurum/[id]/panel`** (447 satır, en büyük ekran) — **P1**
  - Aynı panel kalıbı: stat kartları, bekleyen bağlantı istekleri, öğrenci/çalışma tablosu.
  - Tablo: başlık satırı sabit, durum rozeti, satır tıklanınca detay.
  - Bileşen dosyalarına bölünür (sayfa dosyası < 200 satır hedefi) — **davranış değişmez**.
- [ ] **FE-22** **`/calismalar/[id]/degerlendirme`** — **P0** (zincirin "tanıklık" adımı canlı gösterilir)
  - Değerlendirilen çalışma özeti kartı üstte.
  - Puanlama alanları büyük, seçilebilir kartlar/segmentler; skill tanıklıkları çip seçimi.
  - Gönder → onay `Dialog`'u ("Bu tanıklık geri alınamaz şekilde kaydedilir").
- [ ] **FE-23** `/kurulus/olustur`, `/kurum/olustur`, `/kurum/[id]/baglan` — **P1** — `AuthLayout` benzeri ortalanmış kart form.

#### 3e. Admin

- [ ] **FE-24** `/admin/dogrulama-kuyrugu` — **P1** — tablo + satırda onay/red, red için `Dialog` ile gerekçe.
- [ ] **FE-25** `/admin/skiller` — **P2** — arama + tablo; 502 satırlık dosya bileşenlere bölünür.

### Faz 4 — Cila ve doğrulama (Gün 3 sonu / Gün 4)

- [ ] **FE-26** Tüm sayfalarda yükleme → `Skeleton`, boş durum → `EmptyState`, form başarı → toast/`Alert` (K-4). **P0**
- [ ] **FE-27** Responsive tur: 375 / 768 / 1280 / 1920 genişlikte her P0 ekranı. **P0**
- [ ] **FE-28** Erişilebilirlik turu: klavye ile tüm P0 akışı, görünür focus, form `label`'ları, `aria-live` hatalar, ikon butonlarda `aria-label`. **P0**
- [ ] **FE-29** Favicon + uygulama ikonu + `metadata` (başlık şablonu `%s · Yetkin360`, açıklama, OG). **P1**
- [ ] **FE-30** Sabit renk temizliği: dokunulan dosyalarda `slate-*`/`red-*` vb. → token. Hedef: `grep` sayısı 652 → P0 ekranlarda 0. **P1**
- [ ] **FE-31** Tam doğrulama: `npm run lint && npm run typecheck && npm test` + `npm run build`. **P0**
- [ ] **FE-32** Demo provası (PLAN 4.1): `§4` senaryosu baştan sona, ekran kaydı yedeği. **P0**

### Faz 5 — Zanaat (dört güne yayılır; "sunulabilir"i "şaheser"e çeviren kısım)

Bu görevler bir fazın sonunda değil, **her gün** işlenir. Fark ayrıntıdadır.

- [ ] **FE-33** Marka: el işi wordmark (serif "Yetkin" + "360") + yuvarlak mühür işareti, SVG, tek renk; favicon ve `apple-touch-icon` aynı işaretten. FE-29'u kapsar. **P0** (Gün 1)
- [ ] **FE-34** Mikro metin elden geçirme: `tr.json`'daki ~460 satır §1.5 tonuna göre okunur; buton etiketleri fiil, hata mesajları "ne oldu + ne yapmalı", boş durumlar davetkâr. Anahtar adları değişmez (testler anahtara bağlı). **P0** (Gün 2)
- [ ] **FE-35** **Günlük tasarım eleştirisi:** her gün sonunda P0 ekranların 375px ve 1440px ekran görüntüleri alınır, yan yana konur ve §1.0 yasak listesi + §6 ile tek tek karşılaştırılır. Bulgular ertesi günün ilk işidir. **P0** (her gün)
- [ ] **FE-36** Tek "keyif anı": çalışma `VERIFIED` olduğunda zincirin son çizgisi dolar ve mühür hafifçe "basılır" (scale 1.04 → 1, 400 ms). `prefers-reduced-motion`'da yalnız statik hali görünür. **P1**
- [ ] **FE-37** `/v` sertifikası için baskı stili (`@media print`): tarayıcının "Yazdır / PDF olarak kaydet" çıktısı tek sayfa, menüsüz, düzgün. Buton ya da yeni özellik değil, yalnız CSS. **P2**
- [ ] **FE-38** Piksel turu: tüm ekranlar yan yana; boşluk ölçeği, başlık hizaları, buton yükseklikleri, tablo satır yükseklikleri, ikon boyutları tek tek eşitlenir. **P0** (Gün 4 sabahı)
- [ ] **FE-39** Etkileşim durumları ve kenar vakaları: her etkileşimli öğede hover/active/disabled/focus; uzun kurum adı, uzun başlık, 0 ve 100+ öğeli listeler, ad soyadı olmayan profil gibi taşma durumları; her sayfada anlamlı `<title>`. **P1**

---

## 4. Demo akışı (ekranların sırası bu akışa göre önceliklendirildi)

Final analiz §35.2 senaryosunun ekran karşılığı:

| # | Rol | Ekran | Jürinin görmesi gereken |
|---|---|---|---|
| 1 | — | `/` | Ürün ne yapıyor, zincir, kimin için |
| 2 | Öğrenci | `/kayit` → `/giris` | Temiz, güven veren giriş |
| 3 | Öğrenci | `/profil` → Yetkinlikler | Beyan ekleme; beyanın **gri** olduğu |
| 4 | Öğrenci | `/calismalar/[id]` | Zincir 2. adımda; çıktı + kanıt yükleme |
| 5 | Kuruluş | `/kurulus/[id]/panel` | "Değerlendirme bekleyen" listesi |
| 6 | Kuruluş | `/calismalar/[id]/degerlendirme` | Tanıklık verme anı |
| 7 | Öğrenci | `/calismalar/[id]` | Zincir **tamamlandı**, yeşil mühür |
| 8 | Öğrenci | `/profil` | Aynı yetkinlik artık **doğrulanmış** (yeşil, kanıtlı) |
| 9 | Herkes | `/v/[token]` (jüri telefonu, QR) | Sertifika görünümü, giriş gerektirmez |
| 10 | Kurum | `/kurum/[id]/panel` | Üniversitenin tüm öğrencilerinin doğrulanmış deneyim tablosu |

> Öneri: sunumda `/v/[token]` linki için slayta QR kod konur (sunum işi, kod değil).

---

## 5. Seed hesapları (FE-01 sırasında doldurulacak)

Şifreler bu dosyaya **yazılmaz**; seed hesaplarının şifresi `backend/scripts/seed.py`'de, admin şifresi `.env`'de.

| Rol | E-posta | Gösterdiği ekran |
|---|---|---|
| Öğrenci | `ogrenci1@seed.local` | `/calismalar`, `/profil` |
| Kuruluş admini | `org1-admin@seed.local` | `/kurulus/{id}/panel` |
| Kurum admini | `kurum1-admin@seed.local` | `/kurum/{id}/panel` |
| Koordinatör | `kurum1-koordinator@seed.local` | `/kurum/{id}/panel` |
| Platform admini | `.env` → `SEED_ADMIN_EMAIL` | `/admin/*` |

---

## 6. "Bitti" tanımı (her ekran için)

Bir ekran şu maddelerin **hepsi** sağlanınca `[x]` olur:

1. Yalnız token renkleri ve `components/ui` ilkelleri kullanır; yeni sabit renk sınıfı yok.
2. Yükleme (`Skeleton`), boş (`EmptyState` + aksiyon), hata (`ErrorState`) durumlarının üçü de tasarlanmış.
3. Tüm metin `messages/tr.json`'da; ham enum (`ACTIVE`, `T1`, `claim_type`) ekranda görünmüyor.
4. 375px'de yatay kaydırma yok; klavyeyle kullanılabilir; focus görünür.
5. O ekranın mevcut testleri geçiyor (davranış testi değiştirilmedi; yalnız sınıf/yapı testleri K-5 kapsamında güncellendi).
6. `npm run lint` + `npm run typecheck` temiz.
7. §1.0 yasak listesinden hiçbiri yok: mor/indigo yok, gradyan yok, süs ikonu/emoji yok, kalın gölge yok, ortalanmış boş düzen yok.
8. Diğer ekranların yanına konduğunda aynı aileden görünüyor (FE-35 eleştirisinden geçti).

---

## 7. Kurallar ve sınırlar (bu iş boyunca)

- **Yeni özellik yok.** İstemci tarafı filtre, sayaç, sekme gibi *sunum* iyileştirmeleri serbest; yeni endpoint, yeni alan, yeni iş kuralı yok. Bir ekranda veri eksikse → not düş, backend'e dokunma.
- Backend'den gelen veri neyse o gösterilir; frontend'de gizleyerek "düzeltme" yapılmaz (`.claude/rules/frontend.md`).
- `dangerouslySetInnerHTML` yasak. `localStorage` yasak (auth için zaten yasak; filtre tercihi bile tutulmaz).
- Rol bazlı menü/yönlendirme **yalnız UX**'tir; yetki sunucuda.
- UI metni `tr.json`'a; kod, yorum, tanımlayıcı İngilizce.
- Her FE görevi ayrı commit, mesaj Türkçe, gövdede `FE-xx`. Dosyalar adıyla eklenir.
- Büyük sayfa dosyaları bölünürken (FE-21, FE-25) davranış değişmez; bu refactor 3+ dosyaya dokunduğu için görev başında haber verilir.

---

## 8. Takvim

| Gün | Tarih | Hedef | Görevler |
|---|---|---|---|
| 1 | 7 Ekim | Engeller kalkar; marka, tasarım sistemi ve kabuk hazır | FE-00 → FE-10, FE-33 · akşam FE-35 |
| 2 | 8 Ekim | Public yüz + auth + öğrenci akışı; metinler | FE-12 → FE-18, FE-22, FE-34 · akşam FE-35 |
| 3 | 9 Ekim | Paneller, durumlar, keyif anı | FE-11, FE-19 → FE-21, FE-23, FE-24, FE-26 → FE-28, FE-30, FE-36, FE-39 · akşam FE-35 |
| 4 | 10 Ekim | Sabah: piksel turu ve son dokunuşlar. Öğleden sonra: **kod dondurma**, doğrulama, prova | Sabah FE-38, FE-37, FE-25 · öğleden sonra FE-31, FE-32; sonrasında yalnız kırık olan düzeltilir |

Dört gün iyi bir şey çıkarmak için yeterli; ama süre **yeni ekrana değil, var olan ekranların ayrıntısına** harcanır. Gün sonunda P0'ın gerisinde kalınırsa **P1/P2 kesilir, P0 asla**. Kesme sırası: FE-37 → FE-25 → FE-24 → FE-23 → FE-19 → FE-36 → FE-30 → FE-11.

---

## 9. Riskler

| Risk | Olasılık | Önlem |
|---|---|---|
| Yerel DB tekrar geride kalır (ekip üyesi yeni migration ekler) | Orta | `baslat.bat` / kurulum adımında `alembic upgrade head`; demo öncesi `alembic current == heads` kontrolü |
| Görsel değişiklik testleri toplu kırar | Yüksek | Önce ilkeller (FE-05) + testleri; sayfalar ilkelleri kullandığı için sonrası daha az kırılır. Davranış testleri asla "geçsin diye" değiştirilmez. |
| Kapsam kayması ("şu da olsa güzel olur") | Yüksek | `§7` ilk madde; her yeni fikir → "Vakit kalırsa" listesine, bu plana değil |
| Demo günü ağ / canlı URL sorunu | Orta | Ekran kaydı yedeği (FE-32); PLAN'daki canlı deploy maddesiyle eşgüdüm |
| Seed verisinde `VERIFIED` örnek yok → `/v` gösterilemez | Orta | FE-02'de erken tespit; gerekirse demo sırasında akış canlı tamamlanır |
