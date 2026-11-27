"""Per-request timing (app/timing.py): the Server-Timing header, the log line, /health/db."""

import logging
import re
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app import timing
from app.timing import install_query_timing

_instrumented: set[int] = set()


@pytest.fixture(autouse=True)
def timed_engine(db: Session) -> None:
    """The app puts its listeners on its own engine; these tests use the test database's engine, so
    put them on that one (once)."""
    engine = db.get_bind()
    assert isinstance(engine, Engine) or hasattr(engine, "engine")
    real = engine if isinstance(engine, Engine) else engine.engine
    if id(real) not in _instrumented:
        install_query_timing(real)
        _instrumented.add(id(real))


class Lines(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    @property
    def messages(self) -> list[str]:
        return [r.getMessage() for r in self.records]


@pytest.fixture
def lines() -> Iterator[Lines]:
    handler = Lines()
    timing.logger.addHandler(handler)
    yield handler
    timing.logger.removeHandler(handler)


def server_timing(response) -> dict[str, float | str]:  # type: ignore[no-untyped-def]
    """'app;dur=12, db;dur=5;desc="9 queries, 0 new connections"' as numbers."""
    header = response.headers["server-timing"]
    match = re.fullmatch(
        r'app;dur=(\d+), db;dur=(\d+);desc="(\d+) queries, (\d+) new connections"', header
    )
    assert match, header
    app_ms, db_ms, queries, connects = map(int, match.groups())
    return {"app": app_ms, "db": db_ms, "queries": queries, "connects": connects}


def test_a_request_reports_its_statements_and_time(client: TestClient, make_family) -> None:
    family = make_family(state="UP")

    response = client.patch(family.url, json={"district": "Agra"}, headers=family.headers)

    stats = server_timing(response)
    # session, user, household, UPDATE (and the refresh of updated_at): at least four statements
    assert stats["queries"] >= 4
    assert stats["app"] >= stats["db"] >= 0


def test_statements_are_counted_per_request_not_added_up(client: TestClient, make_family) -> None:
    family = make_family(state="UP")
    busy = server_timing(client.patch(family.url, json={"district": "A"}, headers=family.headers))
    assert busy["queries"] >= 4

    idle = server_timing(client.get("/health"))  # right after a busy one: starts from zero

    assert idle["queries"] == 0 and idle["db"] == 0


def test_a_request_that_never_touches_the_database_says_so(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert server_timing(response) == {
        "app": server_timing(response)["app"],
        "db": 0,
        "queries": 0,
        "connects": 0,
    }


def test_errors_are_timed_too(client: TestClient) -> None:
    assert "server-timing" in client.get("/households/not-a-uuid").headers  # 401 or 422
    assert "server-timing" in client.get("/no-such-route").headers  # 404


def test_the_log_line_has_the_route_pattern_and_no_ids_or_tokens(
    client: TestClient, make_family, lines: Lines
) -> None:
    family = make_family(state="UP")
    lines.records.clear()

    client.patch(family.url, json={"district": "Agra"}, headers=family.headers)

    (message,) = lines.messages
    assert message.startswith("timing PATCH /households/{household_id} 200 total=")
    assert re.search(r"db=\d+ms queries=\d+ connects=\d+$", message)
    assert family.id not in message and family.token not in message  # nothing identifying
    assert "Agra" not in message


def test_an_unknown_path_is_logged_without_the_path(client: TestClient, lines: Lines) -> None:
    client.get("/secret-looking/abc123")

    (message,) = lines.messages
    assert "(no route)" in message and "abc123" not in message


def test_a_slow_request_is_a_warning(
    client: TestClient, lines: Lines, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(timing, "SLOW_SECONDS", 0.0)

    client.get("/health")

    assert [r.levelno for r in lines.records] == [logging.WARNING]


def test_a_normal_request_is_info(client: TestClient, lines: Lines) -> None:
    client.get("/health")
    assert [r.levelno for r in lines.records] == [logging.INFO]


def test_health_db_measures_a_round_trip(client: TestClient) -> None:
    response = client.get("/health/db")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert isinstance(body["first_ms"], int) and isinstance(body["round_trip_ms"], int)
    assert body["first_ms"] >= 0 and body["round_trip_ms"] >= 0
    # one first and three timed (the test session adds its own savepoint statements)
    assert server_timing(response)["queries"] >= 4


def test_health_does_not_touch_the_database(client: TestClient) -> None:
    """The uptime ping must keep answering while the database is asleep (and never wake it)."""
    assert server_timing(client.get("/health"))["queries"] == 0
