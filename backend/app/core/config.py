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


settings = Settings()  # type: ignore[call-arg]  # values come from .env
