"""Application settings, read from environment variables or a .env file (see .env.example)."""
import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND = Path(__file__).resolve().parents[2]  # .../backend
ROOT = BACKEND.parent


class Settings(BaseSettings):
    # .env in the repository root (as the README says), or in backend/; real environment variables win
    model_config = SettingsConfigDict(env_file=(ROOT / ".env", BACKEND / ".env"), extra="ignore")

    app_version: str = "1.0.0"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    model_dir: str = "../artifacts"
    world_dir: str = "../_outputs/world_full"
    world_scale: str = "full"
    db_path: str = "../_outputs/uvera.db"
    llm_mode: str = "cached"
    jwt_secret: str = ""  # empty: a random secret per start (demo tokens are simply issued again)
    demo_mode: bool = True
    rate_limit_per_minute: int = 120
    log_level: str = "info"
    warm_on_start: bool = True

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
# relative paths are relative to backend/, so the API finds its files whatever folder it is started from
for _name in ("model_dir", "world_dir", "db_path"):
    _value = getattr(settings, _name)
    if _value and not Path(_value).is_absolute():
        setattr(settings, _name, str((BACKEND / _value).resolve()))
if not settings.jwt_secret or settings.jwt_secret.startswith("change-me"):
    settings.jwt_secret = secrets.token_urlsafe(48)
