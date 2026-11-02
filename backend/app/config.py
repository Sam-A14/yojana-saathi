from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


def to_driver_url(url: str) -> str:
    """Turn a plain Postgres URL into the form SQLAlchemy needs for the psycopg 3 driver.

    Neon and Render hand out "postgresql://..." (older tools say "postgres://..."), which would make
    SQLAlchemy look for a different driver (psycopg2) that we do not install.
    """
    for plain in ("postgresql://", "postgres://"):
        if url.startswith(plain):
            return "postgresql+psycopg://" + url[len(plain) :]
    return url


class Settings(BaseSettings):
    # Read from environment variables (or a local .env file); never hard-code secrets here.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    frontend_url: str = "http://localhost:3000"
    app_version: str = "0.1.0"
    # Optional on purpose: /health and its tests must work with no database configured.
    database_url: str | None = None
    # LLM wrapper (app/llm/). The provider is a setting so it can be switched without code changes.
    llm_provider: str = "gemini"  # "gemini" or "fake" (tests only)
    llm_model: str = "gemini-2.5-flash"
    # Optional on purpose: only the extraction job needs it. Never log it.
    llm_api_key: str | None = None

    @property
    def sqlalchemy_database_url(self) -> str:
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is not set. See backend/.env.example.")
        return to_driver_url(self.database_url)


@lru_cache
def get_settings() -> Settings:
    # Cached so the environment is read once per process.
    return Settings()
