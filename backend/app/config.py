import re
from functools import lru_cache
from typing import Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# One place for the default so the validator below and the field cannot disagree.
DEFAULT_LLM_MODEL = "gemini-3.6-flash"


def to_driver_url(url: str) -> str:
    """Turn a plain Postgres URL into the form SQLAlchemy needs for the psycopg 3 driver.

    Neon and Render hand out "postgresql://..." (older tools say "postgres://..."), which would make
    SQLAlchemy look for a different driver (psycopg2) that we do not install.
    """
    for plain in ("postgresql://", "postgres://"):
        if url.startswith(plain):
            return "postgresql+psycopg://" + url[len(plain) :]
    return url


def vercel_preview_regex(project: str, team: str) -> str:
    """The origins of one Vercel project's preview deployments, as an anchored regex.

    Vercel gives every deployment of a project a URL in one of two shapes:
      https://<project>-<hash>-<team>.vercel.app          (one per deployment)
      https://<project>-git-<branch>-<team>.vercel.app    (one per branch)
    Both slugs go through re.escape, so a dot or other symbol in a slug cannot widen the match.
    """
    p, t = re.escape(project), re.escape(team)
    return rf"^https://{p}(-[a-z0-9]+|-git-[a-z0-9-]+)-{t}\.vercel\.app$"


class Settings(BaseSettings):
    # Read from environment variables (or a local .env file); never hard-code secrets here.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    frontend_url: str = "http://localhost:3000"
    # Optional: also allow this Vercel project's preview deployments (set both, or neither).
    # Previews have a new URL per deployment, so FRONTEND_URL alone cannot list them.
    vercel_project: str | None = None
    vercel_team: str | None = None
    app_version: str = "0.1.0"
    # Optional on purpose: /health and its tests must work with no database configured.
    database_url: str | None = None
    # LLM wrapper (app/llm/). The provider is a setting so it can be switched without code changes.
    llm_provider: str = "gemini"  # "gemini" or "fake" (tests only)
    llm_model: str = DEFAULT_LLM_MODEL
    # Optional on purpose: only the extraction job needs it. Never log it.
    llm_api_key: str | None = None

    @field_validator("llm_model", mode="before")
    @classmethod
    def blank_model_means_default(cls, value: object) -> object:
        # An unset GitHub repository variable reaches the job as LLM_MODEL="" (not as "missing"),
        # and an empty model name would build a broken URL. Treat blank as "use the default".
        if value is None or (isinstance(value, str) and not value.strip()):
            return DEFAULT_LLM_MODEL
        return value.strip() if isinstance(value, str) else value

    @field_validator("vercel_project", "vercel_team", mode="before")
    @classmethod
    def blank_slug_means_unset(cls, value: object) -> object:
        # Same reason as the model setting above: an unset variable can arrive as "".
        if isinstance(value, str) and not value.strip():
            return None
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def both_vercel_slugs_or_neither(self) -> Self:
        # Half a setting would silently allow no previews (or the wrong ones); fail at startup.
        if (self.vercel_project is None) != (self.vercel_team is None):
            raise ValueError("Set both VERCEL_PROJECT and VERCEL_TEAM, or neither.")
        return self

    @property
    def frontend_preview_regex(self) -> str | None:
        if self.vercel_project and self.vercel_team:
            return vercel_preview_regex(self.vercel_project, self.vercel_team)
        return None

    @property
    def sqlalchemy_database_url(self) -> str:
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is not set. See backend/.env.example.")
        return to_driver_url(self.database_url)


@lru_cache
def get_settings() -> Settings:
    # Cached so the environment is read once per process.
    return Settings()
