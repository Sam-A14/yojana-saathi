import pytest
from fastapi.testclient import TestClient


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
def test_bad_household_input_is_422(client: TestClient, body, signed_in) -> None:
    assert client.post("/households", json=body, headers=signed_in).status_code == 422


def test_422_names_the_field_and_has_no_stack_trace(client: TestClient, signed_in) -> None:
    response = client.post("/households", json={"area_type": "suburb"}, headers=signed_in)

    text = response.text
    assert "area_type" in text
    assert "Traceback" not in text


def test_a_person_has_one_household(client: TestClient, make_family) -> None:
    family = make_family(state="UP")

    again = client.post("/households", json={"state": "BR"}, headers=family.headers)

    assert again.status_code == 409
    assert client.get(family.url, headers=family.headers).json()["state"] == "UP"


def test_there_is_no_way_to_delete_just_the_household(client: TestClient, make_family) -> None:
    # "Delete my data" is DELETE /me, which removes the user and their email as well.
    family = make_family()

    assert client.delete(family.url, headers=family.headers).status_code == 405
