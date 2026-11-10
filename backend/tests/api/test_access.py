"""Who may open a household: only the signed-in user it belongs to."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Household


def test_create_ties_the_household_to_the_signed_in_user(
    client: TestClient, db: Session, make_family
) -> None:
    family = make_family(state="UP", area_type="rural")

    row = db.scalar(select(Household).where(Household.id == family.id))
    assert row is not None
    assert row.user_id == family.user.id
    assert family.body["state"] == "UP"
    assert "access_token" not in family.body  # households no longer have their own token


def test_creating_a_household_needs_sign_in(client: TestClient) -> None:
    assert client.post("/households", json={}).status_code == 401


def test_the_owner_opens_their_household(client: TestClient, make_family) -> None:
    family = make_family(state="UP")

    response = client.get(family.url, headers=family.headers)

    assert response.status_code == 200
    assert response.json()["id"] == family.id


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer not-a-session"},
        {"Authorization": "Bearer "},
        {"Authorization": "Basic abc"},
        {"Authorization": "just-a-word"},
    ],
    ids=["missing", "wrong", "empty", "wrong-scheme", "no-scheme"],
)
def test_missing_or_wrong_session_is_401(client: TestClient, make_family, headers) -> None:
    family = make_family()

    assert client.get(family.url, headers=headers).status_code == 401


def test_another_users_session_cannot_read_this_household(client: TestClient, make_family) -> None:
    mine, other = make_family(), make_family()
    member = client.post(
        f"{mine.url}/members", json={"nickname": "Asha", "relation": "self"}, headers=mine.headers
    ).json()

    strangers = other.headers
    assert client.get(mine.url, headers=strangers).status_code == 403
    assert client.patch(mine.url, json={"state": "UP"}, headers=strangers).status_code == 403
    assert client.get(f"{mine.url}/members", headers=strangers).status_code == 403
    assert client.get(f"{mine.url}/members/{member['id']}", headers=strangers).status_code == 403
    # ...and nothing was changed by those attempts.
    assert client.get(mine.url, headers=mine.headers).json()["state"] is None


def test_unknown_household_id_is_403_not_404(client: TestClient, make_family) -> None:
    family = make_family()
    missing = "/households/00000000-0000-4000-8000-000000000000"

    # Same answer as someone else's household, so a stranger cannot tell which ids exist.
    assert client.get(missing, headers=family.headers).status_code == 403


def test_a_member_id_from_another_household_is_404(client: TestClient, make_family) -> None:
    mine, other = make_family(), make_family()
    theirs = client.post(
        f"{other.url}/members", json={"nickname": "Ravi", "relation": "self"}, headers=other.headers
    ).json()

    # My session is valid for MY household, but that member is not in it.
    response = client.get(f"{mine.url}/members/{theirs['id']}", headers=mine.headers)

    assert response.status_code == 404
