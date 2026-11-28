from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.db.models import Scheme, SchemeVersion
from tests.api.conftest import add_scheme


def test_list_is_public_and_includes_unverified_schemes(
    client: TestClient, db: Session, seeded
) -> None:
    # Whatever is committed, a scheme with no verified_at must be shown, labelled, never hidden.
    db.execute(update(SchemeVersion).values(verified_at=None))
    response = client.get("/schemes")  # no token

    assert response.status_code == 200
    by_slug = {s["slug"]: s for s in response.json()}
    assert {"pm-kisan", "ignwps"} <= set(by_slug)
    # The seed files are not yet verified by a human: they are shown, labelled, never hidden.
    assert by_slug["ignwps"]["verified"] is False
    assert by_slug["ignwps"]["verified_at"] is None


def test_list_holds_only_real_schemes_never_the_template(client: TestClient, seeded) -> None:
    """The landing page counts per category from this list, so the template must not be in it."""
    schemes = client.get("/schemes").json()

    slugs = {s["slug"] for s in schemes}
    assert {"pm-kisan", "ignwps"} <= slugs  # at least: approved schemes are added by pull request
    assert "replace-with-scheme-slug" not in slugs
    assert "replace_with_category" not in {s["category"] for s in schemes}


def test_verified_scheme_says_so(client: TestClient, db: Session, seeded) -> None:
    db.execute(update(SchemeVersion).values(verified_at="2026-11-01T00:00:00+00:00"))

    by_slug = {s["slug"]: s for s in client.get("/schemes").json()}

    assert by_slug["pm-kisan"]["verified"] is True


def test_list_carries_the_source_page_for_the_credit_line(client: TestClient, seeded) -> None:
    for scheme in client.get("/schemes").json():
        assert scheme["source_url"].startswith("http"), scheme["slug"]


def test_detail_has_documents_and_source(client: TestClient, seeded) -> None:
    response = client.get("/schemes/ignwps")

    assert response.status_code == 200
    body = response.json()
    assert body["official_url"] == "https://www.myscheme.gov.in/schemes/ignwps"
    assert body["source_url"].startswith("http")
    assert body["version_no"] == 1
    codes = {d["code"] for d in body["documents"]}
    assert {"spouse_death_certificate", "bpl_card"} <= codes
    bpl = next(d for d in body["documents"] if d["code"] == "bpl_card")
    assert (bpl["required"], bpl["applies_to"]) == (True, "household")


def test_detail_and_list_carry_what_we_did_not_check(client: TestClient, seeded) -> None:
    detail = client.get("/schemes/ignoaps").json()
    assert len(detail["not_checked_en"]) == 2 and len(detail["not_checked_hi"]) == 2
    assert "citizen of India" in detail["not_checked_en"][0]

    listed = {s["slug"]: s for s in client.get("/schemes").json()}
    assert listed["ignoaps"]["not_checked_en"] == detail["not_checked_en"]
    assert len(listed["pm-kisan"]["not_checked_en"]) == 3
    assert len(listed["ignwps"]["not_checked_en"]) == 2


def test_a_scheme_with_nothing_to_say_has_an_empty_list_and_no_hindi_yet(
    client: TestClient, db: Session, seeded
) -> None:
    add_scheme(db, "plain-test", {"all": [{"field": "age", "op": "gte", "value": 60}]})

    body = client.get("/schemes/plain-test").json()

    assert body["not_checked_en"] == []  # never null: the page can always count the lines
    assert body["not_checked_hi"] is None  # not written yet, which is not the same as nothing


def test_each_scheme_says_if_it_is_for_the_whole_family(client: TestClient, seeded) -> None:
    listed = {s["slug"]: s for s in client.get("/schemes").json()}

    assert listed["pm-kisan"]["for_whole_family"] is True
    assert listed["ignwps"]["for_whole_family"] is False
    assert client.get("/schemes/pm-kisan").json()["for_whole_family"] is True


def test_unknown_scheme_is_404(client: TestClient, seeded) -> None:
    assert client.get("/schemes/no-such-scheme").status_code == 404


def test_closed_schemes_are_hidden(client: TestClient, db: Session, seeded) -> None:
    db.execute(update(Scheme).where(Scheme.slug == "ignwps").values(status="closed"))

    assert "ignwps" not in {s["slug"] for s in client.get("/schemes").json()}
    assert client.get("/schemes/ignwps").status_code == 404
