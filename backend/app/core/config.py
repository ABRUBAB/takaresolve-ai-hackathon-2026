"""Application settings, read from environment variables (see .env.example)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_version: str = "0.1.0"
    allowed_origins: str = "http://localhost:3000"
    model_dir: str = "../artifacts"
    llm_mode: str = "cached"
    demo_mode: bool = True
    log_level: str = "info"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
