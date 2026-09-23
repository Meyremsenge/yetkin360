# Setup Notları

Bu dosya, pipeline adımlarının (özellikle `plan.md`) belgelediği yeni
bağımlılık/migration/kurulum adımlarını **birebir aktarır**.

## YET-9 — Organization + domain doğrulama

**Kaynak:** `obss_project/artifacts/yet-9-organization-domain-dogrulama/plan.md`

- Yeni bağımlılık: `dnspython==2.7.0` (`backend/requirements.txt`) — domain
  doğrulama için gerçek DNS TXT sorgusu yapar.
- Yeni migration: `d1e2f3g4h5i6_add_organization_domain_verification` —
  `organizations` tablosuna `domain_verification_token` (nullable),
  `last_verify_attempt_at` (nullable) kolonları + T2 domain'ler için partial
  unique index (`ix_organizations_domain_verified`) ekler. Uygulamak için:
  ```bash
  cd backend
  alembic upgrade head
  ```

## YET-82/YET-83 — Evidence upload-url

**Kaynak:** `obss_project/artifacts/yet-82-83-evidence-upload-url/plan.md`

- Yeni bağımlılık: `boto3==1.35.0` (`backend/requirements.txt`) — MinIO ile
  S3-uyumlu presigned URL/POST üretimi için.
- Yeni env değişkenleri (`.env`'e eklenmeli, `.env.example`'da placeholder
  zaten mevcut): `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`,
  `S3_BUCKET` (opsiyonel, default `yetkin360-evidence`), `S3_REGION`
  (opsiyonel, default `us-east-1`), `S3_USE_SSL` (opsiyonel, default
  `false`). Yerel geliştirmede `docker-compose.yml`'deki MinIO servisiyle
  eşleşmeli (`S3_ENDPOINT_URL=http://localhost:9010`).
- Migration yok — bu görev evidence DB kaydı yapmıyor (PLAN 2.6'ya bırakıldı).
- Yeni endpoint: `POST /evidence/upload-url` — kimlik doğrulanmış talent
  kullanıcılar için MinIO presigned POST üretir (content-type allowlist:
  pdf/jpeg/png/docx, boyut sınırı 10MB, rate limit 10 istek/dakika).

## YET-10 — Skill taksonomisi seed + arama

**Kaynak:** `obss_project/artifacts/skill-taksonomisi-seed-arama/plan.md`

- Yeni migration: `0410b8ecfed7_merge_organization_domain_verification_` —
  boş bir merge migration, iki bağımsız alembic head'i (`d1e2f3g4h5i6` ve
  `3f9b7c1a5d2e`) birleştirir (şema değişikliği yok, sadece zincir
  tamamlanıyor — bkz. `AI_DEVLOG.md` YET-10 bölümü). Uygulamak için:
  ```bash
  cd backend
  alembic upgrade head
  ```
- Yeni CLI komutu: `python -m scripts.seed` — ~150 kayıtlık skill taksonomisini
  idempotent olarak (`ON CONFLICT (slug) DO NOTHING`) veritabanına ekler.
  **Production'da çalıştırılmaz** — sadece dev/test ortamı ve ilk kurulum
  (bootstrap) için. Tekrar çalıştırmak güvenlidir (idempotent).
  ```bash
  cd backend
  python -m scripts.seed
  ```
- Yeni endpoint: `GET /skills/search?q=&limit=&offset=` — authenticated
  kullanıcılar için skill taksonomisinde arama (global referans veri, kiracı
  filtresi yok).
