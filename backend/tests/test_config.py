import pytest

from app.config import Settings, to_driver_url


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgresql://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("postgres://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        (
            "postgresql://u:p@ep-x.neon.tech/db?sslmode=require",
            "postgresql+psycopg://u:p@ep-x.neon.tech/db?sslmode=require",
        ),
        # Already in driver form: left alone.
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
    ],
)
def test_to_driver_url(given: str, expected: str) -> None:
    assert to_driver_url(given) == expected


def test_database_url_is_optional_but_required_when_used() -> None:
    settings = Settings(database_url=None, _env_file=None)

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        _ = settings.sqlalchemy_database_url
