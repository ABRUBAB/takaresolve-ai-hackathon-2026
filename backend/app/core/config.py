"""Application settings, read from environment variables (see .env.example)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_version: str = "1.0.0"
    allowed_origins: str = "http://localhost:3000"
    model_dir: str = "../artifacts"
    world_dir: str = "../_outputs/world_full"
    world_scale: str = "full"
    db_path: str = "../_outputs/uvera.db"
    llm_mode: str = "cached"
    jwt_secret: str = "change-me"
    demo_mode: bool = True
    rate_limit_per_minute: int = 120
    log_level: str = "info"
    warm_on_start: bool = True

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
