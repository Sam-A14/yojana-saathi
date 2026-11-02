from sqlalchemy import Engine, inspect

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app.db.base import Base
from tests.conftest import alembic_config, migrate_to_head, reset_schema

EXPECTED_TABLES = {
    "schemes",
    "scheme_versions",
    "documents",
    "scheme_documents",
    "users",
    "households",
    "members",
    "member_documents",
    "eligibility_results",
    "review_items",
    "alerts",
}


def test_migration_creates_every_table(engine: Engine) -> None:
    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())


def test_migration_matches_models(engine: Engine) -> None:
    """If a model is changed without a new migration, production would silently differ."""
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        assert compare_metadata(context, Base.metadata) == []


def test_downgrade_and_upgrade_again(engine: Engine) -> None:
    reset_schema(engine)
    migrate_to_head(engine)
    with engine.begin() as connection:
        config = alembic_config()
        config.attributes["connection"] = connection
        command.downgrade(config, "base")
    assert EXPECTED_TABLES.isdisjoint(inspect(engine).get_table_names())

    migrate_to_head(engine)  # leave the database at head for the other tests
    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())
