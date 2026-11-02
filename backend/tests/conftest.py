import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config

BACKEND_DIR = Path(__file__).resolve().parents[1]


def alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return config


def migrate_to_head(engine: Engine) -> None:
    with engine.begin() as connection:
        config = alembic_config()
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def reset_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """A real PostgreSQL database, migrated with Alembic exactly as production is."""
    from app.config import to_driver_url

    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        # Silent skipping in CI would hide a broken setup, so CI must fail instead.
        if os.environ.get("CI"):
            pytest.fail("TEST_DATABASE_URL must be set in CI")
        pytest.skip("TEST_DATABASE_URL not set; see backend/.env.example")
    driver_url = to_driver_url(url)
    database_name = driver_url.rsplit("/", 1)[-1].split("?")[0]
    # The fixture wipes the schema, so refuse anything not clearly meant for tests.
    if not database_name.endswith("_test"):
        pytest.fail(f"Refusing to wipe database '{database_name}': its name must end in '_test'")

    test_engine = create_engine(driver_url)
    reset_schema(test_engine)
    migrate_to_head(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """A session rolled back after each test, so tests do not affect each other."""
    connection = engine.connect()
    outer = connection.begin()
    # create_savepoint lets a test trigger a failing statement and carry on afterwards.
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    outer.rollback()
    connection.close()
