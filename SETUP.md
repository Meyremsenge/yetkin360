# Setup Notları

Bu dosya, pipeline adımlarının (özellikle `plan.md`) belgelediği yeni
bağımlılık/migration/kurulum adımlarını **birebir aktarır**.

## YET-2.2 — Durum makinesi: POST /engagements/{id}/transitions

**Kaynak:** `obss_project/artifacts/engagement-durum-makinesi-transitions-ucu/plan.md` (+ red-team sonrası ek migration)

- Yeni migration: `h9i0j1k2l3m4_add_engagement_reason_column` — `engagements`
  tablosuna `reason` (nullable Text) kolonu ekler (T3/T6 red/iptal
  gerekçesinin kalıcı saklanması için, red-team bulgusu). Uygulamak için:
  ```bash
  cd backend
  alembic upgrade head
  ```

## YET-2.1 — Engagement modeli + migration + oluşturma ucu

**Kaynak:** `obss_project/artifacts/engagement-model-olusturma-ucu/plan.md`

- Yeni migration: `g8h9i0j1k2l3_add_engagements_table` — `engagements`
  tablosu (talent_id/organization_id/institution_id/supervisor_user_id FK'leri,
  `kind`/`status`/tarih-sırası CHECK kısıtları, 4 index: `(organization_id,
  status)`, `(talent_id,status)`, `(institution_id,status)`, partial
  `(status) WHERE status='PENDING_EVALUATION'`). Uygulamak için:
  ```bash
  cd backend
  alembic upgrade head
  ```

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
