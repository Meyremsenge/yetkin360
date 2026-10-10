# ENV.md — Ortam Değişkenleri

Projenin okuduğu tüm ortam değişkenleri, varsayılanları ve anlamları.

> **Bu dosya `.env.example`'ın kaynağıdır.** Kurulum sırasında aşağıdaki
> §8'deki şablonu kopyalayıp repo köküne `.env.example` olarak kaydedin,
> sonra `cp .env.example .env` ile çalışma kopyanızı oluşturun.
>
> **`.env` asla commit edilmez** — `.gitignore` içindedir.
> `.env.example` yalnız **placeholder** içerir, gerçek sır içermez.

**Tek `.env`, repo kökünde.** `backend/app/core/config.py` dosyayı kendi
konumundan hesaplar (`REPO_ROOT / ".env"`), çalışma dizininden değil — yani
`backend/` içinden de repo kökünden de aynı dosya okunur. `backend/.env`
diye ikinci bir dosyaya **gerek yoktur**; varsa silin, yoksa ikisi ayrışır.

**Öncelik:** gerçek ortam değişkeni > `.env` dosyası. CI `.env` kullanmaz,
değişkenleri doğrudan tanımlar ([.github/workflows/ci.yml](../.github/workflows/ci.yml)).

**İlgili dosyalar:**
- Sır yönetimi kuralları → [SECURITY.md](SECURITY.md) §6
- Hız sınırı gerekçeleri → [SECURITY.md](SECURITY.md) §3
- İş kuralı sabitleri → [DOMAIN.md](DOMAIN.md) §3.11
- Kurulum adımları → [README.md](../README.md)

---

## 1. Genel

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `ENVIRONMENT` | `development` | `development` \| `staging` \| `production` |
| `DEBUG` | `true` | **Production'da mutlaka `false`** — hata detayı sızdırır |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |
| `TZ` | `UTC` | Tüm zaman damgaları UTC ([DATABASE.md](DATABASE.md) §1) |

## 2. Veritabanı

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `POSTGRES_USER` | `yetkin360` | |
| `POSTGRES_PASSWORD` | *(placeholder)* | Docker Compose ve uygulama ortak kullanır |
| `POSTGRES_DB` | `yetkin360` | |
| `POSTGRES_HOST` | `localhost` | Compose içinden: `postgres` |
| `POSTGRES_PORT` | `5432` | |
| `DATABASE_URL` | *(türetilmiş)* | SQLAlchemy bağlantı dizesi. Diğer `POSTGRES_*` değerleriyle **tutarlı olmalı** |

## 3. Güvenlik ve oturum

Kararların gerekçesi → [SECURITY.md](SECURITY.md) §5.

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `SECRET_KEY` | *(placeholder)* | Token imzalama. `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `ACCESS_TOKEN_TTL_MINUTES` | `15` | Kısa ömürlü JWT |
| `REFRESH_TOKEN_TTL_DAYS` | `30` | DB'de saklanır, rotating |
| `COOKIE_SECURE` | `true` | Yalnız yerel HTTP geliştirmede `false`. **Production'da `false` ise uygulama açılmaz** (YET-207). Cookie'ler her zaman `SameSite=Lax`, `Domain`'siz (host-only) yazılır; SameSite/Domain ayarı yoktur |
| `CSRF_ENABLED` | `true` | Double-submit token |
| `MAX_FAILED_LOGINS` | `5` | Aşılınca hesap kilitlenir |
| `ACCOUNT_LOCK_MINUTES` | `15` | Kilit süresi |
| `RATE_LIMIT_ENABLED` | `true` | Kimlik uçlarında DB tabanlı hız sınırı (YET-186, [SECURITY.md](SECURITY.md) §3). Yalnız yerel geliştirmede `false` yapılabilir; production'da açık kalır. IP anahtarı `request.client.host`'tur: Caddy arkasında uvicorn `--proxy-headers --forwarded-allow-ips=<caddy-ip>` ile çalıştırılmazsa tüm istekler tek IP sayılır |

## 4. CORS

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `FRONTEND_ORIGIN` | `http://localhost:3000` | E-posta linklerinin (doğrulama, şifre sıfırlama) kökü. Cookie ayarlarıyla ilgisi yoktur |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | Virgülle ayrılmış CORS listesi, `*` yasak |

**Desteklenen production topolojisi (YET-207, K6 = a): tek origin.** Frontend ve API aynı alan adından, HTTPS reverse proxy (Caddy) arkasında sunulur (ör. `/` → Next.js, API yolları → uvicorn). Cookie'ler `Domain`'siz yazıldığı için tarayıcı onları yalnız yazan host'a bağlar; `csrf_token` cookie'sini frontend'in `document.cookie` ile okuyabilmesi ve Next middleware'in `access_token`'ı görebilmesi bu varsayıma dayanır. **`app.x` / `api.x` gibi ayrı alt alan adları desteklenmez** (`Domain=.x` seçeneği bilinçli olarak yoktur: kardeş alt alan adları cookie'yi okuyabilir/ezebilir).

`ENVIRONMENT=production` iken şunlardan biri varsa uygulama **açılmaz** (tüm sorunlar tek hatada listelenir): `COOKIE_SECURE=false`, `DEBUG=true`, `FRONTEND_ORIGIN` veya `ALLOWED_ORIGINS` içinde `http://` ya da localhost/127.0.0.1/[::1]. `ENVIRONMENT` yalnız `development`, `staging`, `production` olabilir (yazım hatası, ör. `prod`, açılışı reddeder). `ENVIRONMENT` varsayılanı `development` olduğundan production'da **açıkça** `production` yazılmalıdır.

## 5. Object storage

Dosya güvenliği kuralları → [SECURITY.md](SECURITY.md) §2.

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `S3_ENDPOINT_URL` | `http://localhost:9000` | MinIO (geliştirme) |
| `S3_ACCESS_KEY` | *(placeholder)* | |
| `S3_SECRET_KEY` | *(placeholder)* | |
| `S3_BUCKET` | `yetkin360-evidence` | **Private bucket** — public erişim kapalı |
| `S3_REGION` | `us-east-1` | MinIO için önemsiz |
| `S3_USE_SSL` | `false` | Production'da `true` |
| `UPLOAD_URL_TTL_SECONDS` | `900` | 15 dk — imzalı yükleme URL'i |
| `DOWNLOAD_URL_TTL_SECONDS` | `300` | **5 dk** — imzalı indirme URL'i |
| `MAX_FILE_SIZE_MB` | `10` | Dosya başına |
| `MAX_USER_QUOTA_MB` | `100` | Kullanıcı başına toplam |
| `ALLOWED_FILE_TYPES` | `pdf,png,jpg,jpeg,docx,zip` | **Allowlist** — blacklist kullanılmaz |
| `USER_CONTENT_BASE_URL` | *(boş)* | Kullanıcı içeriğinin ayrı domain'i. **MVP'de boş**, production'da zorunlu |

## 6. E-posta

Gönderim `outbox` worker üzerinden, **asla transaction içinde değil**
([DATABASE.md](DATABASE.md) §5).

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `EMAIL_BACKEND` | `console` | `console` \| `smtp`. MVP'de konsola yazılır |
| `OUTBOX_POLL_INTERVAL_SECONDS` | `5` | Worker polling aralığı (saniye) |
| `OUTBOX_MAX_ATTEMPTS` | `5` | Maksimum yeniden deneme sayısı; aşılan satır dead-letter olur (seçilmez, tabloda kalır) |
| `OUTBOX_BACKOFF_BASE_SECONDS` | `30` | Başarısız denemeden sonra bekleme: 30, 60, 120, 240 sn (üstel) |
| `SMTP_HOST` | *(boş)* | |
| `SMTP_PORT` | `587` | |
| `SMTP_USER` | *(boş)* | |
| `SMTP_PASSWORD` | *(placeholder)* | |
| `EMAIL_FROM` | `noreply@yetkin360.local` | |
| `EMAIL_FROM_NAME` | `Yetkin360` | |

## 7. Hız sınırları ve iş kuralları

Tam tablo ve gerekçeler → [SECURITY.md](SECURITY.md) §3.

| Değişken | Varsayılan |
|---|---|
| `RATE_LIMIT_ENABLED` | `true` |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | `5` |
| `RATE_LIMIT_REGISTER_PER_HOUR` | `3` |
| `RATE_LIMIT_UPLOAD_PER_HOUR` | `20` |
| `RATE_LIMIT_SEARCH_PER_MINUTE` | `60` |
| `RATE_LIMIT_GENERAL_PER_MINUTE` | `300` |

İş kuralı sabitleri ([DOMAIN.md](DOMAIN.md) §3.11):

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `NEW_ORG_COOLING_PERIOD_DAYS` | `30` | Yeni kurum `COMPETENCE` tanıklığı yapamaz |
| `COMPETENCE_MIN_WEEKS` | `4` | Minimum engagement süresi |
| `ATTESTATION_QUOTA_PER_MEMBER_MONTHLY` | `5` | Doğrulanmış üye başına aylık kota |

AI fraud-check (PLAN 3.54, faz 1 — [API.md](API.md) §2.10):

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `OPENROUTER_API_KEY` | `""` | Boşsa handler sessizce no-op (AI opsiyonel, zorunlu bağımlılık değil) |
| `OPENROUTER_MODEL` | `anthropic/claude-haiku-4.5` | Küçük/hızlı model — çıkarım görevi, akıl yürütme değil |

## Frontend

> **`NEXT_PUBLIC_*` değişkenleri tarayıcıya gider — asla sır yazmayın.**

| Değişken | Varsayılan |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1` |
| `NEXT_PUBLIC_SITE_URL` | `http://localhost:3000` |

---

## 8. `.env.example` şablonu

Aşağıdaki bloğu repo kökünde `.env.example` olarak kaydedin.

```bash
# Yetkin360 — ortam değişkenleri örneği
#
# Kullanım:  cp .env.example .env
#
# UYARI: Bu dosya repoda tutulur ve HERKESE AÇIKTIR.
#        Buraya asla gerçek sır yazılmaz — yalnız placeholder.
#        .env dosyası .gitignore içindedir ve asla commit edilmez.
#
# Tam açıklamalar: docs/ENV.md

# --- Genel ---
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
TZ=UTC

# --- Veritabanı ---
POSTGRES_USER=yetkin360
POSTGRES_PASSWORD=DEGISTIR_guclu_parola
POSTGRES_DB=yetkin360
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL=postgresql+psycopg://yetkin360:DEGISTIR_guclu_parola@localhost:5432/yetkin360

# --- Güvenlik ---
# Üretmek için: python -c "import secrets; print(secrets.token_urlsafe(64))"
SECRET_KEY=DEGISTIR_en_az_64_karakter_rastgele
ACCESS_TOKEN_TTL_MINUTES=15
REFRESH_TOKEN_TTL_DAYS=30
COOKIE_SECURE=false
CSRF_ENABLED=true
MAX_FAILED_LOGINS=5
ACCOUNT_LOCK_MINUTES=15

# --- CORS ---
FRONTEND_ORIGIN=http://localhost:3000
ALLOWED_ORIGINS=http://localhost:3000

# --- Object storage (MinIO / S3) ---
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=DEGISTIR_minio_erisim_anahtari
S3_SECRET_KEY=DEGISTIR_minio_gizli_anahtar
S3_BUCKET=yetkin360-evidence
S3_REGION=us-east-1
S3_USE_SSL=false
UPLOAD_URL_TTL_SECONDS=900
DOWNLOAD_URL_TTL_SECONDS=300
MAX_FILE_SIZE_MB=10
MAX_USER_QUOTA_MB=100
ALLOWED_FILE_TYPES=pdf,png,jpg,jpeg,docx,zip
USER_CONTENT_BASE_URL=

# --- E-posta (outbox worker) ---
EMAIL_BACKEND=console
OUTBOX_POLL_INTERVAL_SECONDS=5
OUTBOX_MAX_ATTEMPTS=5
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=noreply@yetkin360.local
EMAIL_FROM_NAME=Yetkin360

# --- Hız sınırları ---
RATE_LIMIT_ENABLED=true
RATE_LIMIT_LOGIN_PER_MINUTE=5
RATE_LIMIT_REGISTER_PER_HOUR=3
RATE_LIMIT_UPLOAD_PER_HOUR=20
RATE_LIMIT_SEARCH_PER_MINUTE=60
RATE_LIMIT_GENERAL_PER_MINUTE=300

# --- İş kuralları ---
NEW_ORG_COOLING_PERIOD_DAYS=30
COMPETENCE_MIN_WEEKS=4
ATTESTATION_QUOTA_PER_MEMBER_MONTHLY=5

# --- AI fraud-check (PLAN 3.54, faz 1 — opsiyonel, boşsa handler no-op) ---
# OpenRouter: tanıklık metnini (attestation.statement) şüpheli patern için
# tarar, flag üretir — karar her zaman admin'de (bkz. docs/API.md §2.10).
OPENROUTER_API_KEY=
OPENROUTER_MODEL=anthropic/claude-haiku-4.5

# --- Frontend (tarayıcıya gider — sır yazmayın) ---
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

---

## 9. Production kontrol listesi

Deploy öncesi ([PLAN.md](../PLAN.md) 3.14) doğrulanır:

- [ ] `ENVIRONMENT=production` (açıkça; varsayılan `development` doğrulamayı devreye sokmaz)
- [ ] `DEBUG=false`
- [ ] `COOKIE_SECURE=true`
- [ ] Frontend ve API **tek origin** (aynı alan adı, HTTPS reverse proxy); `FRONTEND_ORIGIN` ve `ALLOWED_ORIGINS` https ve localhost dışı
- [ ] `RATE_LIMIT_ENABLED=true` ve uvicorn `--proxy-headers --forwarded-allow-ips` ayarlı (gerçek istemci IP'si görünüyor)
- [ ] `S3_USE_SSL=true`
- [ ] `SECRET_KEY` yeniden üretilmiş (geliştirme değeri **kullanılmaz**)
- [ ] `POSTGRES_PASSWORD` ve `S3_*` anahtarları güçlü ve benzersiz
- [ ] `ALLOWED_ORIGINS` yalnız gerçek domain'i içeriyor
- [ ] `EMAIL_BACKEND=smtp` ve gönderim test edilmiş
- [ ] `.env` dosya izinleri kısıtlı (`chmod 600`)
- [ ] Hiçbir sır git geçmişinde yok (`gitleaks` taraması temiz)
