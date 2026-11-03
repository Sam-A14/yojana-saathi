from fastapi.testclient import TestClient


def setup_member(client: TestClient, family) -> str:  # noqa: ANN001
    response = client.post(
        f"{family.url}/members",
        json={"nickname": "Kamla", "relation": "mother"},
        headers=family.headers,
    )
    return f"{family.url}/members/{response.json()['id']}"


def test_put_sets_has_and_has_not(client: TestClient, seeded, make_family) -> None:
    family = make_family()
    url = setup_member(client, family)

    response = client.put(
        f"{url}/documents",
        json={"documents": {"bpl_card": True, "ration_card": False}},
        headers=family.headers,
    )

    assert response.status_code == 200
    assert response.json() == {"documents": {"bpl_card": True, "ration_card": False}}
    assert client.get(url, headers=family.headers).json()["documents"] == {
        "bpl_card": True,
        "ration_card": False,
    }


def test_put_replaces_the_whole_set_and_is_safe_to_repeat(
    client: TestClient, seeded, make_family
) -> None:
    family = make_family()
    url = setup_member(client, family)
    client.put(
        f"{url}/documents",
        json={"documents": {"bpl_card": True, "ration_card": True}},
        headers=family.headers,
    )

    body = {"documents": {"bpl_card": False}}
    for _ in range(2):
        client.put(f"{url}/documents", json=body, headers=family.headers)

    # ration_card was left out, so it is "not answered" again, not "has".
    assert client.get(url, headers=family.headers).json()["documents"] == {"bpl_card": False}


def test_unknown_document_code_is_422_and_changes_nothing(
    client: TestClient, seeded, make_family
) -> None:
    family = make_family()
    url = setup_member(client, family)
    client.put(f"{url}/documents", json={"documents": {"bpl_card": True}}, headers=family.headers)

    response = client.put(
        f"{url}/documents",
        json={"documents": {"ration_card": True, "passport_xyz": True}},
        headers=family.headers,
    )

    assert response.status_code == 422
    assert "passport_xyz" in response.json()["detail"]
    assert client.get(url, headers=family.headers).json()["documents"] == {"bpl_card": True}


def test_document_answers_must_be_true_or_false(client: TestClient, seeded, make_family) -> None:
    family = make_family()
    url = setup_member(client, family)

    response = client.put(
        f"{url}/documents", json={"documents": {"bpl_card": "AB123456"}}, headers=family.headers
    )

    # Only has / doesn't have. A document number is rejected (CLAUDE.md rule 3).
    assert response.status_code == 422
