"""Who may open a household: the token, and only the token."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.security import hash_token
from app.db.models import Household


def test_create_returns_a_long_token_and_says_it_cannot_be_recovered(client: TestClient) -> None:
    response = client.post("/households", json={"state": "UP", "area_type": "rural"})

    assert response.status_code == 201
    body = response.json()
    assert len(body["access_token"]) >= 40  # 256 random bits in URL-safe text
    assert "cannot be recovered" in body["token_notice"]
    assert body["state"] == "UP"


def test_only_the_hash_of_the_token_is_stored(client: TestClient, db: Session, make_family) -> None:
    family = make_family()

    row = db.scalar(select(Household).where(Household.id == family.id))
    assert row is not None
    assert row.access_token_hash == hash_token(family.token)
    assert family.token not in (row.access_token_hash or "")
    assert row.user_id is None  # no account behind a token-only household


def test_two_households_get_different_tokens(make_family) -> None:
    assert make_family().token != make_family().token


def test_the_token_opens_its_own_household(client: TestClient, make_family) -> None:
    family = make_family(state="UP")

    response = client.get(family.url, headers=family.headers)

    assert response.status_code == 200
    assert response.json()["id"] == family.id
    assert "access_token" not in response.json()  # never repeated after creation


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer not-the-token"},
        {"Authorization": "Bearer "},
        {"Authorization": "Basic abc"},
        {"Authorization": "just-a-word"},
    ],
    ids=["missing", "wrong", "empty", "wrong-scheme", "no-scheme"],
)
def test_missing_or_wrong_token_is_403(client: TestClient, make_family, headers) -> None:
    family = make_family()

    assert client.get(family.url, headers=headers).status_code == 403


def test_another_households_token_cannot_read_this_one(client: TestClient, make_family) -> None:
    mine, other = make_family(), make_family()
    member = client.post(
        f"{mine.url}/members", json={"nickname": "Asha", "relation": "self"}, headers=mine.headers
    ).json()

    strangers = other.headers
    assert client.get(mine.url, headers=strangers).status_code == 403
    assert client.patch(mine.url, json={"state": "UP"}, headers=strangers).status_code == 403
    assert client.get(f"{mine.url}/members", headers=strangers).status_code == 403
    assert client.get(f"{mine.url}/members/{member['id']}", headers=strangers).status_code == 403
    assert client.delete(mine.url, headers=strangers).status_code == 403
    # ...and nothing was changed or deleted by those attempts.
    assert client.get(mine.url, headers=mine.headers).json()["state"] is None


def test_unknown_household_id_is_403_not_404(client: TestClient, make_family) -> None:
    family = make_family()
    missing = "/households/00000000-0000-4000-8000-000000000000"

    # Same answer as a wrong token, so a stranger cannot tell which ids exist.
    assert client.get(missing, headers=family.headers).status_code == 403


def test_a_member_id_from_another_household_is_404(client: TestClient, make_family) -> None:
    mine, other = make_family(), make_family()
    theirs = client.post(
        f"{other.url}/members", json={"nickname": "Ravi", "relation": "self"}, headers=other.headers
    ).json()

    # My token is valid for MY household, but that member is not in it.
    response = client.get(f"{mine.url}/members/{theirs['id']}", headers=mine.headers)

    assert response.status_code == 404
