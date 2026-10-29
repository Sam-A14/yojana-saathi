from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Read from environment variables (or a local .env file); never hard-code secrets here.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    frontend_url: str = "http://localhost:3000"
    app_version: str = "0.1.0"


@lru_cache
def get_settings() -> Settings:
    # Cached so the environment is read once per process.
    return Settings()
