from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root, resolved from this file — not from the current working directory.
# docs/ENV.md puts .env at the repo root, but the backend is usually run from
# backend/, so a relative ".env" would resolve differently per command.
# Real environment variables still win over the file (CI sets them directly).
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    database_url: str
    frontend_origin: str = "http://localhost:3000"
    allowed_origins: str = "http://localhost:3000"

    # Auth — docs/SECURITY.md §6, final analiz §15.3.
    # No default for secret_key: a fallback value would silently ship to production.
    secret_key: str
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    cookie_secure: bool = True  # False only for local HTTP development

    # Outbox / Email — docs/ENV.md §6, PLAN 1.5 (yet-5-outbox-worker), PLAN 1.6
    outbox_poll_interval_seconds: int = 5
    outbox_max_attempts: int = 5
    email_backend: str = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@yetkin360.local"
    email_from_name: str = "Yetkin360"

    # S3/MinIO — PLAN 2.5 (YET-82, YET-83), PLAN 2.6 (YET-84, YET-85)
    s3_endpoint_url: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str = "yetkin360-evidence"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False
    s3_presigned_url_ttl_seconds: int = 900  # Upload TTL: 15 minutes
    evidence_download_url_ttl_seconds: int = 300  # Download TTL: 5 minutes
    evidence_max_size_bytes: int = 10485760

    # İlk platform admin — yalnız scripts/seed.py tarafından kullanılır (PLAN 3.6).
    # Self-servis admin-olma ucu yoktur; prod'da bu değerler .env üzerinden değiştirilir.
    seed_admin_email: str = "admin@yetkin360.local"
    seed_admin_password: str = "DEGISTIR_admin_parola"


settings = Settings()  # type: ignore[call-arg]  # values come from .env
