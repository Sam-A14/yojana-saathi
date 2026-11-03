from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient

FULL_MEMBER: dict[str, Any] = {
    "nickname": "Kamla",
    "relation": "mother",
    "birth_year": 1964,
    "gender": "female",
    "marital_status": "widow",
    "occupation": "farmer",
    "education": "primary",
    "is_student": False,
    "disability": False,
    "owns_cultivable_land": False,
    "paid_income_tax_last_year": False,
    "govt_employee": "none",
    "pension_band": "none",
    "is_registered_professional": False,
    "holds_constitutional_post": False,
    "is_remarried": False,
}


def add(client: TestClient, family, **fields: Any):  # noqa: ANN201
    body = {"nickname": "Asha", "relation": "self", **fields}
    return client.post(f"{family.url}/members", json=body, headers=family.headers)


def test_create_stores_every_field(client: TestClient, make_family) -> None:
    family = make_family()

    response = client.post(f"{family.url}/members", json=FULL_MEMBER, headers=family.headers)

    assert response.status_code == 201
    body = response.json()
    assert {k: body[k] for k in FULL_MEMBER} == FULL_MEMBER
    assert body["household_id"] == family.id
    assert body["documents"] == {}


def test_unanswered_facts_stay_null_not_false(client: TestClient, make_family) -> None:
    # The engine must see "not answered" as unknown; a default of false would hide the question.
    body = add(client, make_family()).json()

    assert body["owns_cultivable_land"] is None
    assert body["birth_year"] is None


def test_list_get_update_delete(client: TestClient, make_family) -> None:
    family = make_family()
    first = add(client, family, nickname="Asha").json()
    add(client, family, nickname="Ravi", relation="husband")

    listed = client.get(f"{family.url}/members", headers=family.headers).json()
    assert [m["nickname"] for m in listed] == ["Asha", "Ravi"]

    member_url = f"{family.url}/members/{first['id']}"
    assert client.get(member_url, headers=family.headers).json()["nickname"] == "Asha"

    patched = client.patch(
        member_url, json={"birth_year": 1990, "is_student": True}, headers=family.headers
    ).json()
    assert patched["nickname"] == "Asha"
    assert (patched["birth_year"], patched["is_student"]) == (1990, True)

    assert client.delete(member_url, headers=family.headers).status_code == 204
    assert client.get(member_url, headers=family.headers).status_code == 404
    assert len(client.get(f"{family.url}/members", headers=family.headers).json()) == 1


def test_at_most_twenty_members(client: TestClient, make_family) -> None:
    family = make_family()
    for i in range(20):
        assert add(client, family, nickname=f"P{i}").status_code == 201

    response = add(client, family, nickname="One too many")

    assert response.status_code == 409
    assert "at most 20" in response.json()["detail"]


@pytest.mark.parametrize(
    "fields",
    [
        {"nickname": ""},
        {"nickname": "   "},
        {"nickname": "x" * 51},
        {"relation": ""},
        {"birth_year": 1899},
        {"birth_year": date.today().year + 1},
        {"birth_year": "1990-05-01"},  # a full date is not accepted: birth year only
        {"gender": "unknown"},
        {"marital_status": "single"},  # the word used here is "unmarried"
        {"is_student": "yes"},  # real true/false only
        {"govt_employee": "clerk"},
        {"pension_band": "5k"},
        {"aadhaar_number": "123412341234"},
        {"pan": "ABCDE1234F"},
    ],
)
def test_bad_member_input_is_422(client: TestClient, make_family, fields) -> None:
    assert add(client, make_family(), **fields).status_code == 422


def test_missing_required_fields_is_422(client: TestClient, make_family) -> None:
    family = make_family()

    response = client.post(
        f"{family.url}/members", json={"relation": "self"}, headers=family.headers
    )

    assert response.status_code == 422


def test_required_member_fields_cannot_be_cleared(client: TestClient, make_family) -> None:
    family = make_family()
    member = add(client, family).json()

    response = client.patch(
        f"{family.url}/members/{member['id']}", json={"nickname": None}, headers=family.headers
    )

    assert response.status_code == 422


def test_unknown_member_is_404(client: TestClient, make_family) -> None:
    family = make_family()
    url = f"{family.url}/members/00000000-0000-4000-8000-000000000000"

    assert client.get(url, headers=family.headers).status_code == 404
    assert client.delete(url, headers=family.headers).status_code == 404
