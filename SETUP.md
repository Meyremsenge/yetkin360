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
