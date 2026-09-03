from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Anchored to this file's directory (backend/), not the process's current
# working directory. pydantic-settings resolves a relative env_file against
# cwd, so `alembic upgrade head` (or anything else) run from anywhere other
# than backend/ would silently fail to find .env and fall back to every
# hardcoded default below — including the SQLite database_url — with no
# error. That exact failure mode is why this is now an absolute path.
_ENV_FILE = Path(__file__).resolve().parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    database_url: str = "sqlite:///./pov_zen.db"

    secret_key: str = "dev-only-insecure-key"
    access_token_expire_minutes: int = 1440
    jwt_algorithm: str = "HS256"

    # "strict" is correct — and requires no CSRF token — as long as the
    # frontend and API are same-site (same registrable domain; subdomains of
    # one shared domain, e.g. app.example.com + api.example.com, count as
    # same-site). Only set this to "none" if frontend and API must live on
    # genuinely unrelated domains; that combination requires secure=True
    # (enforced in auth/security.py regardless of this value) and loses
    # SameSite's CSRF protection entirely, so it is not recommended.
    cookie_samesite: str = "strict"

    # Both local hostnames are allowed by default so CORS doesn't silently
    # under-allow if .env isn't loaded for some reason — a page opened via
    # either http://localhost:5500 or http://127.0.0.1:5500 must work.
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500"

    storage_backend: str = "local"
    upload_dir: str = "uploads"  # relative to the backend/ working directory
    max_upload_size_mb: int = 5

    environment: str = "development"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def is_test(self) -> bool:
        return self.environment.lower() == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()
