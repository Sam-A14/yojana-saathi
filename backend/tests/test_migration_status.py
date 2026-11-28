"""Waiting for the database migrations before the seed writes anything."""

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

from alembic import command
from app.db import migration_status
from tests.conftest import alembic_config


class FakeClock:
    """Time that only moves when the code sleeps, so the tests take no real time."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_it_returns_at_once_when_the_database_is_ready() -> None:
    time = FakeClock()
    assert migration_status.wait_until_at_head(lambda: True, 900, 20, time.sleep, time.clock)
    assert time.sleeps == []


def test_it_waits_until_the_database_catches_up() -> None:
    time = FakeClock()
    answers = iter([False, False, True])

    assert migration_status.wait_until_at_head(
        lambda: next(answers), 900, 20, time.sleep, time.clock
    )
    assert time.sleeps == [20, 20]


def test_it_gives_up_after_the_timeout() -> None:
    time = FakeClock()

    assert not migration_status.wait_until_at_head(lambda: False, 60, 20, time.sleep, time.clock)
    assert time.now == 60  # waited the whole time, not forever


def test_a_database_that_is_down_counts_as_not_yet_and_is_retried() -> None:
    time = FakeClock()
    calls = iter(["down", "down", "up"])

    def check() -> bool:
        if next(calls) == "down":
            raise OperationalError("select 1", {}, Exception("connection refused"))
        return True

    assert migration_status.wait_until_at_head(check, 900, 20, time.sleep, time.clock)
    assert time.sleeps == [20, 20]


def test_the_test_database_is_at_the_newest_migration(engine: Engine) -> None:
    head = migration_status.code_head()
    assert head is not None
    assert migration_status.database_revision(engine) == head
    assert migration_status.is_at_head(engine)


def test_a_database_one_migration_behind_is_not_at_head(engine: Engine) -> None:
    """The case that broke seeding: the code has a column the database does not have yet."""
    head = migration_status.code_head()
    config = alembic_config()
    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.stamp(config, "0001")  # only the version marker moves, not the tables
        assert not migration_status.is_at_head(engine)
    finally:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.stamp(config, head)
    assert migration_status.is_at_head(engine)


def test_main_fails_with_a_clear_message_when_the_database_is_behind(
    engine: Engine, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("app.db.session.get_engine", lambda: engine)
    monkeypatch.setattr(migration_status, "is_at_head", lambda _engine: False)

    assert migration_status.main(["--timeout", "0", "--interval", "0"]) == 1
    message = capsys.readouterr().err
    assert "has not finished or has failed" in message and "run this workflow again" in message


def test_main_succeeds_when_the_database_is_at_head(
    engine: Engine, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("app.db.session.get_engine", lambda: engine)

    assert migration_status.main(["--timeout", "0"]) == 0
    assert "newest migration" in capsys.readouterr().out
