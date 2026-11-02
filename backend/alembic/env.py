from sqlalchemy import create_engine

import app.db.models  # noqa: F401  (registers every table on Base.metadata)
from alembic import context
from app.config import get_settings
from app.db.base import Base

target_metadata = Base.metadata


def run_migrations() -> None:
    # Tests hand in an open connection so they control which database is migrated.
    connection = context.config.attributes.get("connection")
    if connection is None:
        engine = create_engine(get_settings().sqlalchemy_database_url)
        with engine.connect() as connection:
            _migrate(connection)
        engine.dispose()
    else:
        _migrate(connection)


def _migrate(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


# Offline mode (emitting SQL without a database) is not used in this project.
run_migrations()
