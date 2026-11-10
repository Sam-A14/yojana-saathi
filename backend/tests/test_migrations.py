from sqlalchemy import Engine, inspect, text

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
    "login_codes",
    "sessions",
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


def test_email_login_migration_deletes_households_nobody_can_claim(engine: Engine) -> None:
    """0005 removes token-only households (test data) with their members, and keeps owned ones."""
    user, orphan, owned, member = (f"00000000-0000-4000-8000-00000000000{n}" for n in (1, 2, 3, 4))
    reset_schema(engine)
    with engine.begin() as connection:
        config = alembic_config()
        config.attributes["connection"] = connection
        command.upgrade(config, "0004")
        connection.execute(
            text(f"INSERT INTO users (id, email) VALUES ('{user}', 'a@example.com')")
        )
        connection.execute(
            text(
                "INSERT INTO households (id, user_id, access_token_hash) VALUES "
                f"('{orphan}', NULL, 'token-only'), ('{owned}', '{user}', NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO members (id, household_id, nickname, relation) "
                f"VALUES ('{member}', '{orphan}', 'X', 'self')"
            )
        )
        command.upgrade(config, "head")
        households = connection.execute(text("SELECT id FROM households")).scalars().all()
        members = connection.execute(text("SELECT count(*) FROM members")).scalar()

    assert [str(h) for h in households] == [owned]
    assert members == 0
    reset_schema(engine)  # drop the sample rows, then leave the database at head for other tests
    migrate_to_head(engine)
