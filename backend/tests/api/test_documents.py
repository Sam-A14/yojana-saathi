from fastapi.testclient import TestClient

from app.rules.values import HOUSEHOLD_DOCUMENT_CODES


def test_documents_are_public_and_bilingual(client: TestClient, seeded: None) -> None:
    response = client.get("/documents")  # no token on purpose

    assert response.status_code == 200
    by_code = {d["code"]: d for d in response.json()}
    assert by_code["aadhaar_card"]["name_en"] == "Aadhaar card"
    assert by_code["aadhaar_card"]["name_hi"]  # a Hindi name exists for every document
    assert set(by_code["ration_card"]) == {"code", "name_en", "name_hi", "household_level"}


def test_household_level_matches_the_list_the_eligibility_step_shares(
    client: TestClient, seeded: None
) -> None:
    documents = client.get("/documents").json()

    flagged = {d["code"] for d in documents if d["household_level"]}
    assert flagged == set(HOUSEHOLD_DOCUMENT_CODES)


def test_documents_never_hold_anything_about_a_family(client: TestClient, seeded: None) -> None:
    document = client.get("/documents").json()[0]

    assert "how_to_get_en" not in document  # guides come later; this is only the question list
