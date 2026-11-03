import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Household, Member, MemberDocument


def test_update_changes_only_the_fields_sent(client: TestClient, make_family) -> None:
    family = make_family(state="UP", area_type="rural", income_band="1_to_2_lakh")

    response = client.patch(family.url, json={"category": "OBC"}, headers=family.headers)

    assert response.status_code == 200
    body = response.json()
    assert (body["state"], body["area_type"], body["category"]) == ("UP", "rural", "OBC")


def test_update_with_null_clears_an_answer(client: TestClient, make_family) -> None:
    family = make_family(category="SC")

    response = client.patch(family.url, json={"category": None}, headers=family.headers)

    assert response.json()["category"] is None


@pytest.mark.parametrize(
    "body",
    [
        {"area_type": "suburb"},
        {"income_band": "rich"},
        {"category": "obc"},  # exact spelling only
        {"state": "Uttar Pradesh"},
        {"district": ""},
        {"aadhaar_number": "123412341234"},  # unknown field: identity numbers are never accepted
    ],
)
def test_bad_household_input_is_422(client: TestClient, body) -> None:
    assert client.post("/households", json=body).status_code == 422


def test_422_names_the_field_and_has_no_stack_trace(client: TestClient) -> None:
    response = client.post("/households", json={"area_type": "suburb"})

    text = response.text
    assert "area_type" in text
    assert "Traceback" not in text


def test_delete_removes_everything_of_this_household_only(
    client: TestClient, db: Session, seeded, make_family
) -> None:
    mine, other = make_family(), make_family()
    for family in (mine, other):
        member = client.post(
            f"{family.url}/members",
            json={"nickname": "Asha", "relation": "self"},
            headers=family.headers,
        ).json()
        client.put(
            f"{family.url}/members/{member['id']}/documents",
            json={"documents": {"bpl_card": True}},
            headers=family.headers,
        )

    response = client.delete(mine.url, headers=mine.headers)

    assert response.status_code == 204
    assert db.scalar(select(func.count()).select_from(Household)) == 1
    # The database cascade removed the members and their document answers too.
    assert db.scalar(select(func.count()).select_from(Member)) == 1
    assert db.scalar(select(func.count()).select_from(MemberDocument)) == 1
    # The old token no longer opens anything, and the other household is untouched.
    assert client.get(mine.url, headers=mine.headers).status_code == 403
    assert client.get(other.url, headers=other.headers).status_code == 200
