from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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


settings = Settings()  # type: ignore[call-arg]  # values come from .env
