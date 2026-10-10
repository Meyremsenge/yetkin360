# Yetkin360

**Kanıta dayalı yetkinlik platformu.** Öğrencinin ne bildiğini iddia etmez —
kimin, neyi, hangi dayanakla söylediğini değişmez biçimde kaydeder ve gösterir.

Zincir: **beyan → kanıt → tanıklık → doğrulanmış deneyim**

> Zemin360 Hackathon projesi (GİRVAK × İSTKA × İstanbul Bilgi Üniversitesi).
> Teslim: 9-11 Ekim 2026, İstanbul.

---

## Problem

Bir öğrenci staj yapar, gerçekten bir şey öğrenir, gerçekten bir şey üretir.
Sonra bunu nasıl gösterir? CV'sine "Python" yazar.

Bu satırın karşılığı yoktur:

- **İşveren** doğrulayamaz. Yüzlerce CV'de aynı kelime yazar; hangisinin arkasında
  gerçek iş var, hangisinin yok — ayırt etmenin yolu yoktur.
- **Öğrenci** kanıtlayamaz. Yaptığı iş kurumun içinde kalır; elinde kalan tek şey
  kendi beyanıdır.
- **Üniversite** raporlayamaz. Stajın gerçekten olup olmadığını, ne öğretildiğini,
  hangi yetkinliği geliştirdiğini kurumsal olarak bilemez; akreditasyon
  belgelerini elle toplanan formlarla üretir.

Mevcut platformlar bu boşluğu kapatmıyor. LinkedIn'de yetkinlik onayı
arkadaşlıktan gelir, işten değil. Sertifika siteleri kursu tamamladığınızı
doğrular, işi yaptığınızı değil.

### Çözüm

Yetkin360 üç kavramı **birbirinden ayırır** — ürünün tüm iddiası budur:

| Kavram | Kim söylüyor | Güven değeri |
|---|---|---|
| **Claim** (beyan) | Kişinin kendisi: "Python biliyorum" | **Sıfır** |
| **Evidence** (kanıt) | Bir yapıt: depo, doküman, çıktı | Tek başına doğrulama **değil** |
| **Attestation** (tanıklık) | Kimliği doğrulanmış kurum, **adıyla**, belirli tarihte | **Güvenin tek kaynağı** |

Platform asla "bu kişi Python biliyor" demez. Şunu der:

> **Acme Yazılım A.Ş.** (MERSİS doğrulamalı, T3) bu kişinin Python'ı yeterli
> düzeyde kullandığını **Ağustos 2026'da beyan etti**. Dayanak: 3 çıktı,
> 12 görev kaydı. Üniversite koordinatörü onayladı (T4).

Bu ifade herkese açık bir linkle doğrulanabilir — kurum platformdan ayrılsa bile
çalışmaya devam eder.

---

## Nasıl çalışır

```
1. Öğrenci kaydolur, yetkinliklerini beyan eder              (güven: sıfır)
2. Kurum kaydolur, domain doğrulamasından geçer              (T2)
3. Staj/proje açılır, koordinatör gerçekliğini onaylar       (T4 yolu açılır)
4. Öğrenci çalışır: görevler, çıktılar, yüklenen kanıtlar
5. Kurum yapılandırılmış değerlendirme formunu doldurur
6. Koordinatör onaylar → tek transaction'da:
      ├─ VerifiedExperience üretilir  (snapshot — değişmez)
      ├─ Attestation kaydedilir       (append-only)
      └─ SkillSignal'ler türer        (append-only)
7. Public doğrulama linki açılır — herkes doğrulayabilir
```

**Bir yetkinliğin "seviyesi" bir kolon değildir** — sinyallerin bir
fonksiyonudur. "Neden güçlü?" sorusunun cevabı her zaman listelenebilir.

**Silinemez, geri çekilebilir.** Kurum tanıklığını geri çekerse kayıt kalır,
"geri çekildi" notu eklenir. Silinebilir doğrulama, doğrulama değildir.

---

## Mimari

```
┌─────────────────────────────────────────────────────┐
│  Next.js (public profil/doğrulama + uygulama)       │
└───────────────────────┬─────────────────────────────┘
                        │ httpOnly cookie + CSRF
┌───────────────────────▼─────────────────────────────┐
│  Caddy (TLS, güvenlik başlıkları, rate limit)       │
└───────────────────────┬─────────────────────────────┘
┌───────────────────────▼─────────────────────────────┐
│  FastAPI — Modüler Monolit                          │
│  api/ → services/ → models/                         │
│  ┌───────────────────────────────────────────────┐  │
│  │ Merkezî yetkilendirme: can() + scoped_*()     │  │
│  │ (TÜM veri erişimi buradan geçer)              │  │
│  └───────────────────────────────────────────────┘  │
│  auth │ talent │ org │ institution │ engagement     │
│  evidence │ attestation │ evaluation │ admin        │
└────┬──────────────────┬─────────────────┬───────────┘
     │                  │                 │
┌────▼──────┐   ┌───────▼───────┐   ┌─────▼─────────┐
│PostgreSQL │   │ Object Storage│   │ Worker        │
│ + audit   │   │ (private)     │   │ outbox, scan  │
│ + outbox  │   └───────────────┘   └───────────────┘
└───────────┘
```

> Mimarinin tek "akıllı" kısmı, **tüm veri erişiminin merkezî yetkilendirmeden
> geçmesidir.** Geri kalanı kasıtlı olarak sıkıcıdır.

| Katman | Teknoloji |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 |
| Veritabanı | PostgreSQL 16 |
| Dosya | MinIO (geliştirme) / S3 uyumlu (production) |
| Frontend | Next.js (App Router), TypeScript, shadcn/ui |
| Sunucu | Caddy (TLS), tek VPS |
| Test | pytest, testcontainers, Playwright |

**Bilinçli olarak kullanılmayanlar:** Redis, Elasticsearch, Celery, Kubernetes,
pgvector, blockchain, LLM. Gerekçeler `yetkin360-final-analiz.md` §39'da.

---

## Kurulum

### Gereksinimler

- Docker + Docker Compose
- Python 3.12+ ve Node.js 20+ (yalnız yerel geliştirme için)

### Hızlı başlangıç

```bash
git clone <repo-url>
cd yetkin360
cp .env.example .env          # varsayılanlar geliştirme için çalışır

docker compose up -d          # PostgreSQL + MinIO
```

**Backend:**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

alembic upgrade head          # şema
python -m scripts.seed        # yetkinlik taksonomisi + demo verisi

uvicorn app.main:app --reload # http://localhost:8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev                   # http://localhost:3000
```

API dokümantasyonu: `http://localhost:8000/docs`

### Demo hesapları

`python -m scripts.seed` sonrası oluşan hesaplar:

| Rol | E-posta | Şifre |
|---|---|---|
| Bireysel kullanıcı | `ayse.yilmaz@posta.test` | `demo1234` |
| Kuruluş yöneticisi | `murat.demirci@yelkovanyazilim.test` | `demo1234` |
| Koordinatör | `kerem.taskin@cinaralti.edu.test` | `demo1234` |
| Platform admin | `admin@yetkin360.test` | `demo1234` |

> Bu hesaplar **yalnız geliştirme içindir.** Seed script'i production ortamında
> çalıştırılmaz.

### Testler

```bash
cd backend
pytest -q                        # tümü
pytest tests/authorization -q    # yetkilendirme (en kritik paket)

ruff check . && mypy app         # lint + tip

cd ../frontend
npm run lint && npm run typecheck
```

---

## Ekran akışı

| Ekran | Yol | Kim görür |
|---|---|---|
| Kayıt / giriş | `/giris`, `/kayit` | Herkes |
| Öğrenci profili + yetkinlik beyanı | `/profil` | Öğrenci |
| Kanıt dökümü (sinyaller) | `/profil/yetkinlikler` | Öğrenci |
| Çalışma listesi ve detayı | `/calismalar`, `/calismalar/[id]` | Taraflar |
| Çıktı yükleme | `/calismalar/[id]/cikti` | Öğrenci |
| Değerlendirme formu | `/calismalar/[id]/degerlendirme` | Kurum |
| Koordinatör dashboard | `/koordinator` | Koordinatör |
| Kurum dashboard | `/kurum` | Kurum üyesi |
| Admin doğrulama kuyruğu | `/admin` | Platform admin |
| **Public profil** | `/p/[slug]` | **Herkes (girişsiz)** |
| **Public doğrulama** | `/v/[token]` | **Herkes (girişsiz)** |

Son iki satır ürünün vitrinidir: giriş yapmadan, telefondan açılabilir.

---

## Dokümantasyon

| Dosya | İçerik |
|---|---|
| [docs/DOMAIN.md](docs/DOMAIN.md) | Entity'ler, alanlar, ilişkiler, iş kuralları |
| [docs/DATABASE.md](docs/DATABASE.md) | Şema, DDL, index, append-only, silme politikası |
| [docs/API.md](docs/API.md) | Uç listesi, yetki, şema, hata kodları |
| [docs/AUTHORIZATION.md](docs/AUTHORIZATION.md) | Yetki matrisi ve test matrisi |
| [docs/SECURITY.md](docs/SECURITY.md) | OWASP analizi, dosya güvenliği, saldırı senaryoları |
| [docs/STATE_MACHINE.md](docs/STATE_MACHINE.md) | Engagement durum makinesi |
| [docs/ENV.md](docs/ENV.md) | Ortam değişkenleri + `.env.example` şablonu |
| [PLAN.md](PLAN.md) | İş sırası ve ilerleme |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Katkı akışı, dal ve commit kuralları |
| [SECURITY.md](SECURITY.md) | Güvenlik açığı bildirimi |
| `yetkin360-final-analiz.md` | 39 bölümlük mühendislik ve ürün analizi — **tüm kararların gerekçesi** |

---

## Tasarım ilkeleri

Bu üç kural ihlal edilirse ürün ürün olmaktan çıkar:

1. **Güven, kanıttan değil tanıklıktan gelir.** Kullanıcının yüklediği PDF ile
   kurumun imzası asla aynı statüde gösterilmez.
2. **Doğrulanmış veri değişmezdir.** `attestations`, `skill_signals`,
   `evaluations`, `verified_experiences`, `audit_events` append-only'dir.
   Silinmez — geri çekilir.
3. **Tüm veri erişimi merkezî yetkilendirmeden geçer.** Yetkisiz erişimde
   `403` değil **`404`** dönülür; `403` kaynağın varlığını sızdırır.

**Tek puan yoktur.** "Trust score" gibi tek bir sayıya indirgeme bilinçli olarak
reddedilmiştir: manipülasyona davetiyedir ve açıklanabilirliği yok eder.

---

## Durum

Hackathon MVP'si. Kapsamın dışında bırakılanlar ve gerekçeleri
[PLAN.md](PLAN.md) ve `yetkin360-final-analiz.md` §39'dadır.

Bilinen eksikler ([docs/SECURITY.md](docs/SECURITY.md) §9): virüs taraması,
ayrı içerik domain'i, RLS, MFA — hepsi bilinçli erteleme, gerekçeleriyle
belgelenmiştir.

---

## Lisans

Bkz. [LICENSE](LICENSE).

## Katkı

Bkz. [CONTRIBUTING.md](CONTRIBUTING.md). Güvenlik açığı bildirimi için
[SECURITY.md](SECURITY.md) — lütfen açık issue açmayın.
