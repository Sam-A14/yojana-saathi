"""Editing a person reads their documents before the commit, not after (decision 039)."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event
from sqlalchemy.orm import Session

# The test session commits by releasing a savepoint; the app's own sessions send COMMIT.
COMMIT_MARKERS = ("COMMIT", "RELEASE SAVEPOINT")


@pytest.fixture
def statements(db: Session) -> Iterator[list[str]]:
    """The SQL the app sends while a test runs, in order, commits included."""
    # The app's sessions use expire_on_commit=False (db/session.py); the shared test session expires
    # everything on commit, which would add refresh reads the app never makes.
    db.expire_on_commit = False
    bind = db.get_bind()
    engine = bind if isinstance(bind, Engine) else bind.engine
    seen: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        seen.append(" ".join(statement.split()))

    event.listen(engine, "before_cursor_execute", record)
    yield seen
    event.remove(engine, "before_cursor_execute", record)


def commit_position(seen: list[str]) -> int:
    return next(i for i, s in enumerate(seen) if s.startswith(COMMIT_MARKERS))


def reads_documents(statement: str) -> bool:
    return statement.startswith("SELECT member_documents.")


def a_person(client: TestClient, family) -> str:  # type: ignore[no-untyped-def]
    """A person with two document answers (needs the `seeded` fixture: the document codes)."""
    member = client.post(
        f"{family.url}/members",
        json={"nickname": "Asha", "relation": "self", "birth_year": 1962},
        headers=family.headers,
    ).json()
    client.put(
        f"{family.url}/members/{member['id']}/documents",
        json={"documents": {"aadhaar_card": True, "ration_card": False}},
        headers=family.headers,
    )
    return str(member["id"])


def test_the_documents_are_read_before_the_commit_not_after(
    client: TestClient, seeded, make_family, statements: list[str]
) -> None:
    family = make_family(state="UP")
    member_id = a_person(client, family)
    statements.clear()

    response = client.patch(
        f"{family.url}/members/{member_id}", json={"gender": "female"}, headers=family.headers
    )

    assert response.status_code == 200
    committed = commit_position(statements)
    reads = [i for i, s in enumerate(statements) if reads_documents(s)]
    assert len(reads) == 1  # read once
    assert reads[0] < committed  # and before the commit: no second trip to the pool afterwards


def test_the_answer_is_unchanged_documents_and_new_value(
    client: TestClient, seeded, make_family
) -> None:
    family = make_family(state="UP")
    member_id = a_person(client, family)

    response = client.patch(
        f"{family.url}/members/{member_id}",
        json={"gender": "female", "paid_income_tax_last_year": False},
        headers=family.headers,
    )

    body = response.json()
    assert body["gender"] == "female" and body["paid_income_tax_last_year"] is False
    assert body["documents"] == {
        "aadhaar_card": True,
        "ration_card": False,
    }  # untouched by the edit
    assert body["updated_at"]
    again = client.get(f"{family.url}/members/{member_id}", headers=family.headers).json()
    assert again["gender"] == "female" and again["documents"] == body["documents"]


def test_an_edit_that_is_refused_saves_nothing_and_reads_no_documents(
    client: TestClient, seeded, make_family, statements: list[str]
) -> None:
    family = make_family(state="UP")
    member_id = a_person(client, family)
    statements.clear()

    response = client.patch(
        f"{family.url}/members/{member_id}", json={"gender": "robot"}, headers=family.headers
    )

    assert response.status_code == 422
    assert not any(s.startswith("UPDATE members") for s in statements)
    assert (
        client.get(f"{family.url}/members/{member_id}", headers=family.headers).json()["gender"]
        is None
    )


def test_someone_elses_person_is_still_not_found(client: TestClient, seeded, make_family) -> None:
    mine, other = make_family(), make_family()
    member_id = a_person(client, mine)

    response = client.patch(
        f"{other.url}/members/{member_id}", json={"gender": "male"}, headers=other.headers
    )

    assert response.status_code == 404
