"""Wait until the database has every migration the code knows about.

Why this exists: a merge to main starts two things at once, the backend deploy (which runs the
Alembic migrations) and the "Seed database" workflow. If the seed starts first, it writes to
columns that do not exist yet and fails. This waits instead, up to a limit, then fails with a
message that says what happened.

Run it with:  python -m app.db.migration_status [--timeout SECONDS] [--interval SECONDS]
Exit 0: the database is at the newest migration. Exit 1: it is not (or cannot be reached).
"""

import argparse
import sys
import time
from collections.abc import Callable
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory

BACKEND_DIR = Path(__file__).resolve().parents[2]


def code_head() -> str | None:
    """The newest migration in the code (alembic/versions)."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return ScriptDirectory.from_config(config).get_current_head()


def database_revision(engine: Engine) -> str | None:
    """The migration the database is at (None for a database with no migrations applied)."""
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def is_at_head(engine: Engine) -> bool:
    return database_revision(engine) == code_head()


def wait_until_at_head(
    check: Callable[[], bool],
    timeout: float,
    interval: float,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> bool:
    """Call `check` until it is true or `timeout` seconds have passed. A check that raises a
    database error counts as "not yet": the database may be waking up or restarting."""
    deadline = clock() + timeout
    while True:
        try:
            if check():
                return True
        except SQLAlchemyError as error:
            print(f"database not ready: {type(error).__name__}", file=sys.stderr)
        if clock() >= deadline:
            return False
        sleep(interval)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wait for the database migrations.")
    parser.add_argument("--timeout", type=float, default=900, help="seconds to wait in all")
    parser.add_argument("--interval", type=float, default=20, help="seconds between checks")
    args = parser.parse_args(argv)

    from app.db.session import get_engine

    engine = get_engine()
    if wait_until_at_head(lambda: is_at_head(engine), args.timeout, args.interval):
        print(f"The database is at the newest migration ({code_head()}).")
        return 0
    try:
        found = database_revision(engine)
    except SQLAlchemyError as error:
        found = f"unknown ({type(error).__name__})"
    print(
        f"error: the database is at migration {found}, but the code expects {code_head()}. "
        "The backend deploy (which runs the migrations) has not finished or has failed. "
        "Check the deploy, then run this workflow again.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
