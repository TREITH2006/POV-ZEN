from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./pov_zen.db"

    secret_key: str = "dev-only-insecure-key"
    access_token_expire_minutes: int = 1440
    jwt_algorithm: str = "HS256"

    cors_origins: str = "http://localhost:5500"

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
