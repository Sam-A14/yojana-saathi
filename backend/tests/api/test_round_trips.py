"""Fewer database round trips per request (decision 038): one lookup for who is calling, and no
read-back of updated_at after a save. The access rules themselves must not change."""

import re
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event, update
from sqlalchemy.orm import Session

from app.db.models import UserSession


@pytest.fixture
def statements(db: Session) -> Iterator[list[str]]:
    """The SQL the app sends while a test runs, in order (the test session's own savepoint
    bookkeeping left out)."""
    # The app's sessions are made with expire_on_commit=False (db/session.py); the shared test
    # session expires everything on commit, which would add refresh reads the app never makes.
    db.expire_on_commit = False
    bind = db.get_bind()
    engine = bind if isinstance(bind, Engine) else bind.engine
    seen: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        if not statement.startswith(("SAVEPOINT", "RELEASE SAVEPOINT", "ROLLBACK TO")):
            seen.append(" ".join(statement.split()))

    event.listen(engine, "before_cursor_execute", record)
    yield seen
    event.remove(engine, "before_cursor_execute", record)


def selects(seen: list[str]) -> list[str]:
    return [s for s in seen if s.startswith("SELECT")]


# --- one lookup for who is calling ------------------------------------------------------------


def test_a_household_request_looks_up_session_user_and_household_in_one_query(
    client: TestClient, make_family, statements: list[str]
) -> None:
    family = make_family(state="UP")
    statements.clear()

    response = client.get(family.url, headers=family.headers)

    assert response.status_code == 200
    (only,) = selects(statements)  # one SELECT in total for the whole request
    assert "FROM sessions" in only and "JOIN households" in only


def test_a_household_edit_is_one_lookup_one_update_and_nothing_read_back(
    client: TestClient, make_family, statements: list[str]
) -> None:
    family = make_family(state="UP")
    statements.clear()

    response = client.patch(family.url, json={"district": "Agra"}, headers=family.headers)

    assert response.status_code == 200
    assert len(selects(statements)) == 1  # the lookup; no SELECT of updated_at afterwards
    (update_sql,) = [s for s in statements if s.startswith("UPDATE households")]
    assert re.search(r"RETURNING .*updated_at", update_sql)  # the UPDATE hands the new value back
    assert response.json()["updated_at"]  # and the answer still has it


def test_a_person_edit_returns_updated_at_without_reading_it_back(
    client: TestClient, make_family, statements: list[str]
) -> None:
    family = make_family(state="UP")
    member = client.post(
        f"{family.url}/members",
        json={"nickname": "Asha", "relation": "self"},
        headers=family.headers,
    ).json()
    statements.clear()

    client.patch(
        f"{family.url}/members/{member['id']}", json={"gender": "female"}, headers=family.headers
    )

    (update_sql,) = [s for s in statements if s.startswith("UPDATE members")]
    assert re.search(r"RETURNING .*updated_at", update_sql)
    assert not [s for s in selects(statements) if re.fullmatch(r"SELECT members\.updated_at.*", s)]


def test_creating_a_household_looks_up_the_user_with_one_query(
    client: TestClient, db: Session, statements: list[str]
) -> None:
    from tests.api.conftest import sign_in_user

    _, token = sign_in_user(db, "newcomer@example.com")
    statements.clear()

    response = client.post("/households", json={}, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 201
    lookups = [s for s in selects(statements) if "FROM users" in s]
    assert len(lookups) == 1 and "JOIN sessions" in lookups[0]  # session and user joined


# --- who may see what has not changed ---------------------------------------------------------


def test_someone_elses_household_and_a_missing_one_get_the_same_403(
    client: TestClient, make_family
) -> None:
    mine, other = make_family(), make_family()
    stranger = client.get(mine.url, headers=other.headers)
    missing = client.get(f"/households/{uuid.uuid4()}", headers=other.headers)

    assert stranger.status_code == missing.status_code == 403
    assert stranger.json() == missing.json() == {"detail": "No such household for your account."}


def test_an_unknown_token_is_401_not_403_even_for_a_real_household(
    client: TestClient, make_family
) -> None:
    family = make_family()
    response = client.get(family.url, headers={"Authorization": "Bearer nobody"})
    assert response.status_code == 401 and response.json() == {"detail": "Please sign in."}


def test_an_expired_session_is_401_on_every_kind_of_route(
    client: TestClient, db: Session, make_family
) -> None:
    family = make_family()
    db.execute(update(UserSession).values(expires_at=datetime.now(UTC) - timedelta(minutes=1)))

    assert client.get(family.url, headers=family.headers).status_code == 401  # household route
    assert client.get("/me", headers=family.headers).status_code == 401  # user route
    assert client.post("/auth/sign-out", headers=family.headers).status_code == 401  # session route


def test_no_token_is_401_before_the_household_id_is_even_checked(client: TestClient) -> None:
    assert client.get("/households/not-a-uuid").status_code == 401


def test_the_owner_still_reaches_every_household_route(client: TestClient, make_family) -> None:
    family = make_family(state="UP")
    member = client.post(
        f"{family.url}/members",
        json={"nickname": "Asha", "relation": "self"},
        headers=family.headers,
    ).json()

    for path in ("", "/members", f"/members/{member['id']}", "/eligibility"):
        assert client.get(family.url + path, headers=family.headers).status_code == 200, path
