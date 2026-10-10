from pathlib import Path
from urllib.parse import urlparse

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root, resolved from this file — not from the current working directory.
# docs/ENV.md puts .env at the repo root, but the backend is usually run from
# backend/, so a relative ".env" would resolve differently per command.
# Real environment variables still win over the file (CI sets them directly).
REPO_ROOT = Path(__file__).resolve().parents[3]

KNOWN_ENVIRONMENTS = ("development", "staging", "production")
_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _all_public_https(origins: list[str]) -> bool:
    for origin in origins:
        parsed = urlparse(origin.strip())
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not host or host in _LOOPBACK_HOSTS:
            return False
    return True


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    database_url: str
    frontend_origin: str = "http://localhost:3000"
    allowed_origins: str = "http://localhost:3000"

    @field_validator("allowed_origins")
    @classmethod
    def _validate_allowed_origins(cls, value: str) -> str:
        """Comma-separated origins: strip blanks, refuse wildcard (CORS uses credentials)."""
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if not origins:
            raise ValueError("ALLOWED_ORIGINS must list at least one origin")
        if "*" in origins:
            raise ValueError("ALLOWED_ORIGINS must not contain '*' (credentials are enabled)")
        return ",".join(origins)

    # Auth — docs/SECURITY.md §6, final analiz §15.3.
    # No default for secret_key: a fallback value would silently ship to production.
    secret_key: str
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    cookie_secure: bool = True  # False only for local HTTP development
    # YET-186: identity-endpoint rate limits (docs/SECURITY.md §3). Off only for
    # local development; the test suite turns it off by default.
    rate_limit_enabled: bool = True

    # Outbox / Email — docs/ENV.md §6, PLAN 1.5 (yet-5-outbox-worker), PLAN 1.6
    outbox_poll_interval_seconds: int = 5
    outbox_max_attempts: int = 5
    outbox_backoff_base_seconds: int = 30
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
    # Self-servis admin-olma ucu yoktur. Parola için bilerek varsayılan yok (YET-229):
    # tahmin edilebilir bir fallback admin hesabına dönüşebilir; seed_admin boş,
    # placeholder veya kısa parolayı reddeder, .env'de SEED_ADMIN_PASSWORD verilmeli.
    seed_admin_email: str = "admin@yetkin360.local"
    seed_admin_password: str = ""

    # Fraud flag (PLAN 3.54) — outbox worker'da attestation.statement metnini
    # OpenRouter'a gönderip şüpheli paternleri işaretler (karar her zaman admin'de).
    # Boş olabilir: ayarlanmamışsa worker handler'ı sessizce no-op yapar (AI opsiyonel).
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-haiku-4.5"

    @model_validator(mode="after")
    def _validate_environment(self) -> "Settings":
        """YET-207: refuse to start with a cookie/CSRF-weakening production config.

        Supported production topology is a single origin behind a reverse proxy
        over HTTPS (host-only cookies, no Domain). Problems are collected so the
        operator sees them all at once; messages name settings, never values.
        """
        if self.environment not in KNOWN_ENVIRONMENTS:
            raise ValueError(f"ENVIRONMENT must be one of {', '.join(KNOWN_ENVIRONMENTS)}")
        if self.environment != "production":
            return self

        problems: list[str] = []
        if not self.cookie_secure:
            problems.append("COOKIE_SECURE must be true")
        if self.debug:
            problems.append("DEBUG must be false")
        if not _all_public_https([self.frontend_origin]):
            problems.append("FRONTEND_ORIGIN must be a public https origin")
        if not _all_public_https(self.allowed_origins.split(",")):
            problems.append("ALLOWED_ORIGINS must contain only public https origins")
        if problems:
            raise ValueError("Unsafe production configuration: " + "; ".join(problems))
        return self


settings = Settings()  # type: ignore[call-arg]  # values come from .env
