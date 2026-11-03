from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.db.models import Scheme, SchemeVersion


def test_list_is_public_and_includes_unverified_schemes(client: TestClient, seeded) -> None:
    response = client.get("/schemes")  # no token

    assert response.status_code == 200
    by_slug = {s["slug"]: s for s in response.json()}
    assert {"pm-kisan", "ignwps"} <= set(by_slug)
    # The seed files are not yet verified by a human: they are shown, labelled, never hidden.
    assert by_slug["ignwps"]["verified"] is False
    assert by_slug["ignwps"]["verified_at"] is None


def test_verified_scheme_says_so(client: TestClient, db: Session, seeded) -> None:
    db.execute(update(SchemeVersion).values(verified_at="2026-11-01T00:00:00+00:00"))

    by_slug = {s["slug"]: s for s in client.get("/schemes").json()}

    assert by_slug["pm-kisan"]["verified"] is True


def test_detail_has_documents_and_source(client: TestClient, seeded) -> None:
    response = client.get("/schemes/ignwps")

    assert response.status_code == 200
    body = response.json()
    assert body["official_url"] == "https://nsap.nic.in/"
    assert body["version_no"] == 1
    codes = {d["code"] for d in body["documents"]}
    assert {"aadhaar_card", "bpl_card"} <= codes
    bpl = next(d for d in body["documents"] if d["code"] == "bpl_card")
    assert (bpl["required"], bpl["applies_to"]) == (True, "household")


def test_unknown_scheme_is_404(client: TestClient, seeded) -> None:
    assert client.get("/schemes/no-such-scheme").status_code == 404


def test_closed_schemes_are_hidden(client: TestClient, db: Session, seeded) -> None:
    db.execute(update(Scheme).where(Scheme.slug == "ignwps").values(status="closed"))

    assert "ignwps" not in {s["slug"] for s in client.get("/schemes").json()}
    assert client.get("/schemes/ignwps").status_code == 404
