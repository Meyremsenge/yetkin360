from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    database_url: str
    frontend_origin: str = "http://localhost:3000"
    allowed_origins: str = "http://localhost:3000"


settings = Settings()  # type: ignore[call-arg]  # values come from .env
