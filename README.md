# Yetkin360

**Kanıta dayalı yetkinlik platformu.** Bir kişinin ne bildiğini iddia etmez —
kimin, neyi, hangi dayanakla söylediğini değişmez biçimde kaydeder ve herkese
doğrulatır.

Zincir: **beyan → kanıt → tanıklık → doğrulanmış deneyim**

> Zemin360 Hackathon projesi (GİRVAK × İSTKA × İstanbul Bilgi Üniversitesi), Ekim 2026.

---

## İçindekiler

1. [Hızlı başlangıç — tek tıkla çalıştırın](#1-hızlı-başlangıç--tek-tıkla-çalıştırın)
2. [Giriş bilgileri](#2-giriş-bilgileri)
3. [5 dakikalık demo turu](#3-5-dakikalık-demo-turu)
4. [Sorun giderme](#4-sorun-giderme)
5. [Ürün: problem ve çözüm](#5-ürün-problem-ve-çözüm)
6. [Mimari](#6-mimari)
7. [Elle kurulum ve testler (geliştiriciler için)](#7-elle-kurulum-ve-testler-geliştiriciler-için)
8. [Dokümantasyon](#8-dokümantasyon)

---

## 1. Hızlı başlangıç — tek tıkla çalıştırın

### Gerekenler

| Araç | Sürüm | İndirme |
|---|---|---|
| **Docker Desktop** | güncel | <https://www.docker.com/products/docker-desktop> |
| **Node.js** | 20 veya üstü | <https://nodejs.org> |
| **Python** | 3.12 veya üstü | <https://www.python.org/downloads> (macOS: `brew install python@3.12`) |
| **Git** | herhangi | <https://git-scm.com> |

Kullanılan portlar: `3000` (uygulama), `8000` (API), `5432` (PostgreSQL),
`9000`/`9001` (MinIO). Bunların boş olması gerekir.

### Çalıştırma

```bash
git clone https://github.com/Meyremsenge/yetkin360.git
cd yetkin360
```

| İşletim sistemi | Ne yapılır |
|---|---|
| **Windows** | Klasördeki **`baslat.bat`** dosyasına çift tıklayın. |
| **macOS** | **`baslat.command`** dosyasına çift tıklayın. macOS ilk seferde "geliştirici doğrulanamadı" derse: dosyaya **sağ tık → Aç → Aç**. Ya da Terminal'de: `./baslat.command` |
| **Linux** | Terminal'de: `./baslat.command` |

Başlatıcı **her şeyi kendisi yapar**, sizden hiçbir ayar istemez:

1. Araçları kontrol eder; **`.env` dosyasını rastgele parolalarla kendisi
   oluşturur** (elle düzenleme gerekmez).
2. Docker kapalıysa açar; PostgreSQL ve MinIO'yu başlatır.
3. Python ve npm paketlerini kurar, veritabanı şemasını oluşturur.
4. **Demo verisini yükler** (kişiler, kuruluşlar, kurumlar, doğrulanmış kayıtlar).
5. API'yi, arka plan işçisini ve arayüzü tek pencerede başlatır, tarayıcıyı açar.

İlk çalıştırma paket indirmeleri nedeniyle **3-6 dakika** sürer; sonrakiler
yaklaşık 30 saniye. Hazır olunca terminalde **giriş bilgilerini de içeren bir
özet** görünür ve tarayıcıda <http://localhost:3000> açılır.

Terminal penceresindeki kısayollar: **`B`** tarayıcıyı aç · **`H`** özeti
tekrar göster · **`Q`** veya **`Ctrl+C`** durdur.

> **Claude Code veya başka bir yapay zekâ asistanıyla açıyorsanız:**
> asistandan başlatıcıyı çalıştırmasını isteyin — Windows'ta `baslat.bat`,
> macOS/Linux'ta `./baslat.command --no-browser`. `.env`'i elle oluşturması ya da
> okuması gerekmez (proje kuralı gereği asistan `.env` okumaz); başlatıcı onu
> oluşturur ve giriş bilgilerini kendi çıktısına yazar. Uygulama hazır olunca
> <http://localhost:3000> adresini tarayıcıda açın.

---

## 2. Giriş bilgileri

**Yeni hesap açmanız gerekmez.** Aşağıdaki hazır hesaplar dolu verilerle
gelir. Giriş sayfasında (<http://localhost:3000/giris>) bu hesaplar
**tıklanabilir bir liste** olarak da görünür: hesaba tıklayın, bilgiler forma
dolar, **Giriş Yap**'a basın.

**Ortak şifre: `SeedTest123!`**

| Rol | E-posta | Girişte açılan ekran |
|---|---|---|
| Bireysel kullanıcı (Ayşe Yılmaz) | `ayse.yilmaz@posta.test` | Çalışmalarım, profil, doğrulanmış kayıtlar |
| Kuruluş yöneticisi (Yelkovan Yazılım) | `murat.demirci@yelkovanyazilim.test` | Kuruluş paneli: ekip, birimler, vitrin |
| Kuruluş onaylayıcısı (Yelkovan, Yazılım birimi) | `mehmet.karaca@yelkovanyazilim.test` | Kuruluş paneli → "Bana atananlar" |
| Aday doğrulayan kuruluş (Gündoğusu Enerji, İK) | `seda.gurbuz@gundogusuenerji.test` | Kuruluş paneli → **Aday doğrula** |
| Kurum yöneticisi (Çınaraltı Teknik Üniversitesi) | `nermin.basaran@cinaralti.edu.test` | Kurum paneli |
| Kurum koordinatörü (Çınaraltı) | `kerem.taskin@cinaralti.edu.test` | Kurum paneli: onay ve mühür kuyruğu |

**Platform yöneticisi:** `admin@yetkin360.test` — giriş adresi
<http://localhost:3000/admin/giris>. Şifresi her kurulumda rastgele üretilir ve
**başlatıcının terminal özetinde yazar** (ayrıca `.env` → `SEED_ADMIN_PASSWORD`).

> **Yine de yeni hesap açarsanız:** yerel kurulum gerçek e-posta göndermez.
> E-posta doğrulama bağlantısı başlatıcı terminalinde **`[EMAIL]`** ile başlayan
> renkli satırda görünür — bağlantıyı tarayıcıya yapıştırın. Yeni hesaplar boş
> başlar ve yeni bir kuruluş düşük doğrulama seviyesinden başlar; ürünü görmek
> için hazır hesaplar çok daha hızlıdır.

---

## 3. 5 dakikalık demo turu

Her adımda sağ üstteki **Çıkış** ile çıkıp tablodaki hesapla girin.

| # | Hesap | Nerede | Ne görülür |
|---|---|---|---|
| 1 | **Ayşe** (bireysel) | Çalışmalar → Yeni çalışma | Yelkovan Yazılım'ı seçer, onaylayıcı olarak **Mehmet Karaca · Yazılım**'ı atar |
| 2 | **Kerem** (koordinatör) | Kurum paneli | Onay kutusunda satır içi **Onayla** |
| 3 | **Mehmet** (onaylayıcı) | Kuruluş paneli → Bana atananlar | Yapılandırılmış değerlendirme formunu doldurur |
| 4 | **Kerem** | Kurum paneli → Mühür bekleyen | Mühürler → **çift imzalı kayıt** (kuruluş değerlendirdi + üniversite mühürledi) |
| 5 | **Seda** (Gündoğusu İK) | Kuruluş paneli → **Aday doğrula** | Ayşe'nin doğrulama bağlantısını yapıştırır, imzalı kaydı görür (bağlantı: Ayşe'nin profilindeki doğrulanmış kayıt) |
| 6 | Girişsiz herkes | **Keşfet** → Yelkovan Yazılım → Vitrin | "Bu şirkette yapılmış, imzalı işler" |

Girişsiz açılabilen vitrin sayfaları: Ayşe'nin herkese açık profili
<http://localhost:3000/p/ayse-yilmaz>, Keşfet <http://localhost:3000/kesfet>,
doğrulama sayfaları `/v/<bağlantı>`.

---

## 4. Sorun giderme

| Belirti | Çözüm |
|---|---|
| "Eksik araç var" | Listelenen aracı kurun, terminali kapatıp başlatıcıyı yeniden çalıştırın. |
| "Docker çalışmıyor" / 2 dakikada açılmadı | Docker Desktop'ı elle açın; "Engine running" görününce başlatıcıyı tekrar çalıştırın. |
| "Port 5432 / 9000 başka bir süreçte" | Bilgisayardaki yerel PostgreSQL veya MinIO'yu durdurun (macOS: `brew services stop postgresql`). |
| "3000 / 8000 dolu" | Başlatıcı önceki çalıştırmadan kalan süreci kapatmayı önerir: `E` + Enter. |
| macOS: `baslat.command` açılmıyor | Sağ tık → Aç. Depoyu ZIP olarak indirdiyseniz çalıştırma izni düşer: Terminal'de `bash baslat.command`. |
| "Python 3.12 veya üstü değil" | Python 3.12+ kurun, `backend/.venv` klasörünü silin, yeniden başlatın. |
| Giriş yapamıyorum | Şifre `SeedTest123!` (büyük S, sonda ünlem). Art arda 5 hatalı denemede hesap 15 dakika kilitlenir; bu sürede başka bir demo hesabı kullanın. |
| Demo verisini sıfırlamak | `cd backend` → `.venv/bin/python -m scripts.reset_demo --yes --reseed` (Windows: `.venv\Scripts\python`) |
| Durdurmak | Terminalde `Q`. Veritabanı açık kalır; kapatmak için `docker compose stop`. |

Her servisin ayrıntılı logu: `.logs/api.log`, `.logs/worker.log`, `.logs/web.log`.
API dokümantasyonu: <http://localhost:8000/docs>.

---

## 5. Ürün: problem ve çözüm

### Problem

Bir kişi staj yapar, bir projede çalışır, gerçekten bir şey üretir. Sonra bunu
nasıl gösterir? CV'sine "Python" yazar. Bu satırın karşılığı yoktur:

- **Kuruluş (işveren)** doğrulayamaz: yüzlerce CV'de aynı kelime yazar; hangisinin
  arkasında gerçek iş olduğunu ayırt edemez.
- **Kişi** kanıtlayamaz: yaptığı iş kuruluşun içinde kalır; elinde yalnız kendi
  beyanı vardır.
- **Kurum (üniversite)** raporlayamaz: stajın gerçekten olup olmadığını, hangi
  yetkinliği geliştirdiğini elle toplanan formlarla izler.

### Çözüm

Yetkin360 üç kavramı **birbirinden ayırır** — ürünün tüm iddiası budur:

| Kavram | Kim söylüyor | Güven değeri |
|---|---|---|
| **Beyan** | Kişinin kendisi: "Python biliyorum" | **Sıfır** |
| **Kanıt** | Bir yapıt: depo, doküman, çıktı | Tek başına doğrulama **değil** |
| **Tanıklık** | Kimliği doğrulanmış kuruluş/kurum, **adıyla**, belirli tarihte | **Güvenin tek kaynağı** |

Platform asla "bu kişi Python biliyor" demez. Şunu der:

> **Yelkovan Yazılım A.Ş.** bu kişinin Python'ı yeterli düzeyde kullandığını
> **Ağustos 2026'da beyan etti**; Çınaraltı Teknik Üniversitesi koordinatörü
> mühürledi. Dayanak: 3 çıktı, 12 görev kaydı.

Bu ifade herkese açık bir bağlantıyla doğrulanabilir — kuruluş platformdan
ayrılsa bile çalışmaya devam eder.

### Kim neden kullanır

- **Kuruluş (önce):** Hesap açma sebebi **başvuranı doğrulamak** (Aday doğrula).
  Kalma sebebi **kendi stajyerine mühür vermek** ve herkese açık **vitrin**:
  "bu şirkette yapılmış, imzalı işler". Ekip içinde onay doğru kişiye (birim,
  onaylayıcı) gider; yönetici her şeyi görür.
- **Bireysel kullanıcı:** öğrenci, mezun veya çalışan — iddiasını imzalı kayda
  çevirir, CV'sine doğrulama bağlantısı koyar.
- **Kurum (üniversite):** öğrencisinin çalışmalarını onaylar ve mühürler; kaydı
  **çift imzalı** yapar; iş birliklerini ve raporu tek yerden alır.

### Akış

```
1. Kişi çalışma açar, kuruluşu ve onaylayıcıyı seçer         (beyan: güven sıfır)
2. Kurum koordinatörü çalışmanın gerçekliğini onaylar
3. Kişi çalışır: görevler, çıktılar, yüklenen kanıtlar         (kanıt)
4. Kuruluştaki onaylayıcı yapılandırılmış formu doldurur       (değerlendirme)
5. Koordinatör mühürler → tek transaction'da:                  (tanıklık)
      ├─ Doğrulanmış deneyim üretilir   (anlık görüntü — değişmez)
      ├─ Tanıklık kaydedilir            (yalnız eklenir, silinmez)
      └─ Yetkinlik sinyalleri türer      (yalnız eklenir)
6. Herkese açık doğrulama bağlantısı açılır — herkes doğrulayabilir
```

**Bir yetkinliğin "seviyesi" bir kolon değildir**, sinyallerin bir
fonksiyonudur: "Neden güçlü?" sorusunun cevabı her zaman listelenebilir.
**Silinemez, geri çekilebilir:** tanıklık geri çekilirse kayıt kalır, "geri
çekildi" notu eklenir. **Tek puan yoktur:** "güven skoru" gibi tek bir sayıya
indirgeme manipülasyona davetiyedir ve açıklanabilirliği yok eder.

---

## 6. Mimari

```
┌─────────────────────────────────────────────────────┐
│  Next.js — uygulama + herkese açık profil/doğrulama │
└───────────────────────┬─────────────────────────────┘
                        │ httpOnly cookie + CSRF
┌───────────────────────▼─────────────────────────────┐
│  FastAPI — modüler monolit                          │
│  api/ → services/ → models/                         │
│  ┌───────────────────────────────────────────────┐  │
│  │ Merkezî yetkilendirme: can() + scoped_*()     │  │
│  │ (TÜM veri erişimi buradan geçer)              │  │
│  └───────────────────────────────────────────────┘  │
└────┬──────────────────┬─────────────────┬───────────┘
┌────▼──────┐   ┌───────▼───────┐   ┌─────▼─────────┐
│PostgreSQL │   │ Nesne deposu  │   │ Worker        │
│ + denetim │   │ (MinIO / S3)  │   │ (outbox)      │
│ + outbox  │   └───────────────┘   └───────────────┘
└───────────┘
```

| Katman | Teknoloji |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 |
| Veritabanı | PostgreSQL 16 |
| Dosya | MinIO (yerel) / S3 uyumlu (production) |
| Frontend | Next.js (App Router), TypeScript, Tailwind |
| Test | pytest, Vitest |

Tasarım ilkeleri:

1. **Güven, kanıttan değil tanıklıktan gelir.** Kullanıcının yüklediği PDF ile
   kuruluşun imzası asla aynı statüde gösterilmez.
2. **Doğrulanmış veri değişmezdir.** `attestations`, `skill_signals`,
   `evaluations`, `verified_experiences`, `audit_events` yalnız eklenir.
3. **Tüm veri erişimi merkezî yetkilendirmeden geçer.** Yetkisiz erişimde
   `403` değil **`404`** dönülür; `403` kaynağın varlığını sızdırır.

**Bilinçli olarak kullanılmayanlar:** Redis, Elasticsearch, Celery, Kubernetes,
pgvector, blockchain. Gerekçeler
[docs/yetkin360-final-analiz.md](docs/yetkin360-final-analiz.md) §39'da.

---

## 7. Elle kurulum ve testler (geliştiriciler için)

Başlatıcı kullanmadan, adım adım:

```bash
python scripts/init_env.py    # .env'i rastgele parolalarla üretir
# ya da: cp .env.example .env  ve DEGISTIR_ ile başlayan değerleri doldurun

docker compose up -d          # PostgreSQL + MinIO

cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head          # şema
python -m scripts.seed        # demo verisi
python -m scripts.ensure_bucket
uvicorn app.main:app --reload # http://localhost:8000
# ayrı bir terminalde (e-posta/bildirim işçisi):
python -m app.workers.outbox_worker

cd ../frontend
npm install
npm run dev                   # http://localhost:3000
```

Testler:

```bash
cd backend
pytest -q                        # tümü
pytest tests/authorization -q    # yetkilendirme (en kritik paket)
ruff check . && mypy app         # lint + tip

cd ../frontend
npm run lint && npm run typecheck && npm run test
```

Ortam değişkenlerinin açıklaması: [docs/ENV.md](docs/ENV.md).

---

## 8. Dokümantasyon

| Dosya | İçerik |
|---|---|
| [docs/yetkin360-final-analiz.md](docs/yetkin360-final-analiz.md) | 39 bölümlük mühendislik ve ürün analizi — **tüm kararların gerekçesi** |
| [docs/DOMAIN.md](docs/DOMAIN.md) | Varlıklar, alanlar, ilişkiler, iş kuralları |
| [docs/DATABASE.md](docs/DATABASE.md) | Şema, index, append-only, silme politikası |
| [docs/API.md](docs/API.md) | Uç listesi, yetki, şema, hata kodları |
| [docs/AUTHORIZATION.md](docs/AUTHORIZATION.md) | Yetki matrisi ve test matrisi |
| [docs/SECURITY.md](docs/SECURITY.md) | OWASP analizi, dosya güvenliği, saldırı senaryoları |
| [docs/STATE_MACHINE.md](docs/STATE_MACHINE.md) | Çalışma (engagement) durum makinesi |
| [docs/ENV.md](docs/ENV.md) | Ortam değişkenleri |
| [docs/PLAN.md](docs/PLAN.md) · [docs/SPRINT.md](docs/SPRINT.md) | İş sırası, ilerleme, son sprint |
| [docs/AI_DEVLOG.md](docs/AI_DEVLOG.md) | Yapay zekâ destekli geliştirme günlüğü |
| [docs/arsiv/](docs/arsiv/) | Eski planlar, denetim raporları, tasarım taslakları |

Bilinen eksikler ([docs/SECURITY.md](docs/SECURITY.md) §9): virüs taraması,
ayrı içerik alan adı, RLS, MFA — hepsi gerekçesiyle belgelenmiş bilinçli
ertelemelerdir.

---

## Lisans ve katkı

Lisans: [LICENSE](LICENSE). Katkı akışı: [CONTRIBUTING.md](CONTRIBUTING.md).
Güvenlik açığı bildirimi için [SECURITY.md](SECURITY.md) — lütfen açık issue
açmayın.
