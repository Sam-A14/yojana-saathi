"""GET /households/{id}/eligibility through the real API and a real PostgreSQL."""

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.facts import MEMBER_FACT_COLUMNS
from app.db.seed import DEFAULT_DATA_DIR, read_seed_files
from app.rules.values import INCOME_BANDS
from tests.api.conftest import Family, add_scheme

PROFILES = sorted((DEFAULT_DATA_DIR / "test_profiles").glob("*.json"))
SLUGS = ("pm-kisan", "ignwps")


def add_member(client: TestClient, family: Family, nickname: str, **fields: Any) -> str:
    body = {"nickname": nickname, "relation": "other", **fields}
    response = client.post(f"{family.url}/members", json=body, headers=family.headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def put_documents(
    client: TestClient, family: Family, member_id: str, docs: dict[str, bool]
) -> None:
    response = client.put(
        f"{family.url}/members/{member_id}/documents",
        json={"documents": docs},
        headers=family.headers,
    )
    assert response.status_code == 200, response.text


def eligibility(client: TestClient, family: Family) -> dict[str, Any]:
    response = client.get(f"{family.url}/eligibility", headers=family.headers)
    assert response.status_code == 200, response.text
    return response.json()


def schemes_of(body: dict[str, Any], nickname: str) -> dict[str, dict[str, Any]]:
    member = next(m for m in body["members"] if m["nickname"] == nickname)
    return {s["scheme"]["slug"]: s for s in member["schemes"]}


def band_for(income_band_max: int) -> str:
    return next(name for name, band in INCOME_BANDS.items() if band.upper == income_band_max)


def load_profile(client: TestClient, make_family, today, path: Path) -> tuple[Family, dict]:
    """Enter a data/test_profiles family through the API, the way the setup form would."""
    profile = json.loads(path.read_text(encoding="utf-8"))
    household = profile["household"]
    family = make_family(
        state=household["state"],
        district=household["district"],
        area_type=household["area_type"],
        category=household["category"],
        income_band=band_for(household["income_band_max"]),
        is_bpl=household.get("is_bpl"),  # absent in a profile = never answered = unknown
    )
    for person in profile["members"]:
        facts = {k: person[k] for k in MEMBER_FACT_COLUMNS if k in person}
        member_id = add_member(
            client, family, person["nickname"], birth_year=today.year - person["age"], **facts
        )
        docs = {k.removeprefix("has_"): v for k, v in person.items() if k.startswith("has_")}
        if docs:
            put_documents(client, family, member_id, docs)
    return family, profile


# --- the end-to-end test from a hand-checked profile ---------------------------------------------


def test_widow_in_a_landowning_family_end_to_end(
    client: TestClient, seeded, today, make_family
) -> None:
    family, profile = load_profile(
        client,
        make_family,
        today,
        DEFAULT_DATA_DIR / "test_profiles/13-widow-in-landowning-family.json",
    )

    body = eligibility(client, family)

    assert body["computed_on"] == "2026-11-03"
    assert body["skipped_schemes"] == []
    kamla, raju = schemes_of(body, "Kamla"), schemes_of(body, "Raju")
    assert kamla["pm-kisan"]["status"] == "eligible"
    assert kamla["ignwps"]["status"] == "eligible"
    assert raju["pm-kisan"]["status"] == "eligible"
    assert "ignwps" not in raju  # a man does not qualify for the widow pension: counted, not listed
    raju_member = next(m for m in body["members"] if m["nickname"] == "Raju")
    # Counted, not listed: every seeded scheme that is neither listed for him nor an exclusion
    # (IGNWPS: he is a man; the old-age, pre-matric, post-matric and Vay Vandana schemes: he is 35
    # and not a student). Computed, so that a new scheme in the seed data cannot break this test.
    seeded = len(read_seed_files().schemes)
    assert raju_member["not_eligible_count"] == seeded - len(raju) - len(raju_member["excluded"])
    assert raju_member["not_eligible_count"] >= 3
    assert raju_member["excluded"] == []  # nobody else's facts excluded him
    # The reasons are there for the screen: which rules passed, with the scheme's own wording.
    ignwps = kamla["ignwps"]
    assert {r["rule"]["field"] for r in ignwps["passed_rules"]} == {
        "gender",
        "marital_status",
        "age",
        "is_bpl",
    }
    assert ignwps["failed_rules"] == [] and ignwps["unknown_rules"] == []
    assert ignwps["scheme"]["official_url"] == "https://nsap.nic.in/"
    # Not yet checked by a human: shown, and labelled as such.
    assert ignwps["scheme"]["verified"] is False


@pytest.mark.parametrize("path", PROFILES, ids=lambda p: p.stem)
def test_every_test_profile_through_the_api(
    client: TestClient, seeded, today, make_family, path: Path
) -> None:
    family, profile = load_profile(client, make_family, today, path)
    body = eligibility(client, family)

    for slug, expected in profile["expected"].items():
        for nickname, want in expected.items():
            listed = schemes_of(body, nickname)
            got = listed[slug]["status"] if slug in listed else "not_eligible"
            # The API only knows the birth YEAR. Where the exact age would change the answer it
            # says so, instead of guessing; that is the one allowed difference from the profile.
            if got == "unknown" and want != "unknown":
                assert listed[slug]["reasons"] == ["depends_on_exact_age"], f"{path.name}/{slug}"
                continue
            assert got == want, f"{path.name} / {slug} / {nickname}"

    for slug, names in profile.get("excluded_by", {}).items():
        first = next(
            m for m in body["members"] if m["nickname"] == profile["members"][0]["nickname"]
        )
        scheme = next(e for e in first["excluded"] if e["scheme"]["slug"] == slug)
        assert sorted(scheme["excluded_by"]) == sorted(names), path.name


def test_exclusion_names_the_family_member_who_caused_it(
    client: TestClient, seeded, today, make_family
) -> None:
    family = make_family(state="UP", area_type="rural", income_band="up_to_1_lakh")
    base = {"paid_income_tax_last_year": False, "is_registered_professional": False}
    base |= {"holds_constitutional_post": False, "govt_employee": "none", "pension_band": "none"}
    add_member(client, family, "Ramesh", birth_year=1976, owns_cultivable_land=True, **base)
    add_member(
        client, family, "Suresh", birth_year=1999, **{**base, "paid_income_tax_last_year": True}
    )

    body = eligibility(client, family)

    for member in body["members"]:
        assert "pm-kisan" not in schemes_of(body, member["nickname"])  # not an offer
        (excluded,) = (e for e in member["excluded"] if e["scheme"]["slug"] == "pm-kisan")
        assert excluded["excluded_by"] == ["Suresh"]  # the son paid income tax
        assert [r["rule"]["not"]["any_member"]["field"] for r in excluded["failed_rules"]] == [
            "paid_income_tax_last_year"
        ]


def test_exclusion_that_can_be_fixed_is_a_near_miss_naming_the_member(
    client: TestClient, db: Session, seeded, today, make_family
) -> None:
    rules = {
        "all": [{"not": {"any_member": {"field": "paid_income_tax_last_year", "op": "is_true"}}}],
        "fixable": ["paid_income_tax_last_year"],
    }
    add_scheme(db, "fixable-test", rules)
    family = make_family()
    add_member(client, family, "Ramesh", paid_income_tax_last_year=False)
    add_member(client, family, "Suresh", paid_income_tax_last_year=True)

    result = schemes_of(eligibility(client, family), "Ramesh")["fixable-test"]

    assert result["status"] == "near_miss"
    assert result["excluded_by"] == ["Suresh"]
    assert result["failed_rules"][0]["fixable"] is True


# --- age and income ranges through the API -------------------------------------------------------


@pytest.mark.parametrize(
    ("birth_year", "status", "reasons"),
    [
        (1985, "eligible", []),  # 40 or 41: certainly 40 or over
        (1986, "unknown", ["depends_on_exact_age"]),  # 39 or 40: depends on the birthday
        (1987, None, None),  # 38 or 39: certainly under 40, so not eligible (not listed)
    ],
)
def test_age_limit_uses_the_range_from_birth_year(
    client: TestClient, seeded, today, make_family, birth_year, status, reasons
) -> None:
    family = make_family(state="UP", is_bpl=True)
    member_id = add_member(
        client, family, "Kamla", birth_year=birth_year, gender="female", marital_status="widow"
    )
    put_documents(client, family, member_id, {"bpl_card": True})

    result = schemes_of(eligibility(client, family), "Kamla").get("ignwps")

    if status is None:
        assert result is None
    else:
        assert result is not None
        assert (result["status"], result["reasons"]) == (status, reasons)
        if status == "unknown":
            (age_rule,) = (r for r in result["unknown_rules"] if r["rule"]["field"] == "age")
            assert age_rule["reasons"] == ["depends_on_exact_age"]


@pytest.mark.parametrize(
    ("band", "limit", "status", "reasons"),
    [
        ("1_to_2_lakh", 200_000, "eligible", []),  # the top edge belongs to the band
        ("1_to_2_lakh", 100_000, None, None),  # the bottom edge belongs to the band below: no
        ("1_to_2_lakh", 150_000, "unknown", ["depends_on_exact_income"]),  # limit inside the band
    ],
)
def test_income_limit_uses_the_range_of_the_band(
    client: TestClient, db: Session, seeded, today, make_family, band, limit, status, reasons
) -> None:
    add_scheme(
        db, "income-test", {"all": [{"field": "income_band_max", "op": "lte", "value": limit}]}
    )
    family = make_family(income_band=band)
    add_member(client, family, "Asha")

    result = schemes_of(eligibility(client, family), "Asha").get("income-test")

    if status is None:
        assert result is None
    else:
        assert result is not None
        assert (result["status"], result["reasons"]) == (status, reasons)


def test_no_income_band_answered_is_unknown_without_a_range_reason(
    client: TestClient, db: Session, seeded, today, make_family
) -> None:
    add_scheme(
        db, "income-test", {"all": [{"field": "income_band_max", "op": "lte", "value": 200000}]}
    )
    family = make_family()
    add_member(client, family, "Asha")

    result = schemes_of(eligibility(client, family), "Asha")["income-test"]

    assert (result["status"], result["reasons"]) == ("unknown", [])


# --- the household's BPL status ---


BPL_RULE = {"all": [{"field": "is_bpl", "op": "is_true"}]}


def test_is_bpl_unanswered_is_unknown_not_no(
    client: TestClient, db: Session, seeded, today, make_family
) -> None:
    add_scheme(db, "bpl-test", BPL_RULE)
    family = make_family()  # is_bpl never answered
    add_member(client, family, "Asha")

    result = schemes_of(eligibility(client, family), "Asha")["bpl-test"]

    assert result["status"] == "unknown"
    assert [r["rule"] for r in result["unknown_rules"]] == [BPL_RULE["all"][0]]


@pytest.mark.parametrize(("answer", "listed"), [(True, "eligible"), (False, None)])
def test_is_bpl_answers_decide_the_rule(
    client: TestClient, db: Session, seeded, today, make_family, answer: bool, listed: str | None
) -> None:
    add_scheme(db, "bpl-test", BPL_RULE)
    family = make_family(is_bpl=answer)
    add_member(client, family, "Asha")

    body = eligibility(client, family)
    results = schemes_of(body, "Asha")

    if listed is None:  # a definite "no": counted, not listed
        assert "bpl-test" not in results
    else:
        assert results["bpl-test"]["status"] == listed


def test_is_bpl_is_independent_of_holding_the_bpl_card(
    client: TestClient, db: Session, seeded, today, make_family
) -> None:
    """BPL status and the card are two facts: a BPL family without the card is still BPL."""
    add_scheme(db, "bpl-test", BPL_RULE)
    family = make_family(is_bpl=True)
    asha = add_member(client, family, "Asha")
    put_documents(client, family, asha, {"bpl_card": False})

    result = schemes_of(eligibility(client, family), "Asha")["bpl-test"]

    assert result["status"] == "eligible"


# --- the kind of house the family lives in ---


HOUSE_RULE = {"all": [{"field": "house_type", "op": "in", "value": ["no_house", "kutcha"]}]}


def test_house_type_unanswered_is_unknown_not_no(
    client: TestClient, db: Session, seeded, today, make_family
) -> None:
    add_scheme(db, "house-test", HOUSE_RULE)
    family = make_family()  # house_type never answered
    add_member(client, family, "Asha")

    result = schemes_of(eligibility(client, family), "Asha")["house-test"]

    assert result["status"] == "unknown"
    assert [r["rule"] for r in result["unknown_rules"]] == [HOUSE_RULE["all"][0]]


@pytest.mark.parametrize(
    ("house", "listed"), [("no_house", "eligible"), ("kutcha", "eligible"), ("pucca", None)]
)
def test_house_type_answers_decide_the_rule(
    client: TestClient, db: Session, seeded, today, make_family, house: str, listed: str | None
) -> None:
    add_scheme(db, "house-test", HOUSE_RULE)
    family = make_family(house_type=house)
    add_member(client, family, "Asha")

    results = schemes_of(eligibility(client, family), "Asha")

    if listed is None:  # a definite "no": counted, not listed
        assert "house-test" not in results
    else:
        assert results["house-test"]["status"] == listed


# --- schemes that are about the whole family ---


def test_a_family_scheme_is_flagged_and_gives_every_member_the_same_answer(
    client: TestClient, db: Session, seeded, today, make_family
) -> None:
    """The dashboard shows such a scheme once, taking one member's result, so every member's result
    must be the same: that is what makes it safe."""
    add_scheme(
        db,
        "family-test",
        {
            "all": [
                {"field": "area_type", "op": "eq", "value": "rural"},
                {"not": {"any_member": {"field": "paid_income_tax_last_year", "op": "is_true"}}},
            ]
        },
    )
    family = make_family(area_type="rural")
    add_member(client, family, "Asha", birth_year=1990, paid_income_tax_last_year=False)
    add_member(client, family, "Ravi", birth_year=2012)  # tax question never answered for him

    body = eligibility(client, family)
    asha, ravi = schemes_of(body, "Asha")["family-test"], schemes_of(body, "Ravi")["family-test"]

    assert asha["scheme"]["for_whole_family"] is True
    assert ravi["scheme"]["for_whole_family"] is True
    assert asha["status"] == ravi["status"] == "unknown"  # Ravi's missing answer decides for all
    assert [r["rule"] for r in asha["unknown_rules"]] == [r["rule"] for r in ravi["unknown_rules"]]


def test_a_scheme_with_a_rule_about_a_person_is_not_a_family_scheme(
    client: TestClient, db: Session, seeded, today, make_family
) -> None:
    family = make_family(area_type="rural")
    add_member(client, family, "Asha", birth_year=1950)

    results = schemes_of(eligibility(client, family), "Asha")

    assert results["ignoaps"]["scheme"]["for_whole_family"] is False


# --- what the person is studying now ---


STUDY_RULE = {"all": [{"field": "current_study_level", "op": "eq", "value": "class_9_10"}]}


def test_study_level_unanswered_is_unknown_not_no(
    client: TestClient, db: Session, seeded, today, make_family
) -> None:
    add_scheme(db, "study-test", STUDY_RULE)
    family = make_family()
    add_member(client, family, "Ravi", is_student=True)  # level never answered

    result = schemes_of(eligibility(client, family), "Ravi")["study-test"]

    assert result["status"] == "unknown"
    assert [r["rule"] for r in result["unknown_rules"]] == [STUDY_RULE["all"][0]]


@pytest.mark.parametrize(
    ("level", "listed"), [("class_9_10", "eligible"), ("class_11_12", None), ("class_1_8", None)]
)
def test_study_level_answers_decide_the_rule(
    client: TestClient, db: Session, seeded, today, make_family, level: str, listed: str | None
) -> None:
    add_scheme(db, "study-test", STUDY_RULE)
    family = make_family()
    add_member(client, family, "Ravi", is_student=True, current_study_level=level)

    results = schemes_of(eligibility(client, family), "Ravi")

    if listed is None:  # a definite "no": counted, not listed
        assert "study-test" not in results
    else:
        assert results["study-test"]["status"] == listed


# --- missing documents ---


def test_missing_documents_say_no_or_not_asked_and_household_documents_are_shared(
    client: TestClient, seeded, today, make_family
) -> None:
    family = make_family(state="UP")
    kamla = add_member(
        client, family, "Kamla", birth_year=1964, gender="female", marital_status="widow"
    )
    raju = add_member(client, family, "Raju", birth_year=1991)
    put_documents(client, family, kamla, {"bank_account_aadhaar_linked": False})
    put_documents(client, family, raju, {"bpl_card": True})  # household document, held by Raju

    ignwps = schemes_of(eligibility(client, family), "Kamla")["ignwps"]

    missing = {d["code"]: d["state"] for d in ignwps["missing_documents"]}
    assert missing == {
        "aadhaar_card": "not_answered",
        "spouse_death_certificate": "not_answered",
        "bank_account_aadhaar_linked": "no",
    }  # bpl_card is not listed: someone in the household has it
    sample = ignwps["missing_documents"][0]
    assert {"name_en", "name_hi", "how_to_get_en", "official_link"} <= set(sample)


# --- family-level documents ---------------------------------------------------------------------


def widow_and_husbands_family(client: TestClient, make_family, father_docs, mother_docs):  # noqa: ANN201
    family = make_family(state="UP")
    mother = add_member(
        client, family, "Kamla", birth_year=1964, gender="female", marital_status="widow"
    )
    father = add_member(client, family, "Raju", birth_year=1962, gender="male")
    if mother_docs is not None:
        put_documents(client, family, mother, mother_docs)
    if father_docs is not None:
        put_documents(client, family, father, father_docs)
    return family


# IGNWPS asks for BPL through the household's is_bpl answer, so these tests of how documents are
# shared use a small scheme whose rule needs the card itself.
CARD_RULE = {"all": [{"field": "has_bpl_card", "op": "is_true"}]}


def test_only_the_father_has_the_bpl_card_and_the_mothers_result_is_not_unknown_for_it(
    client: TestClient, db: Session, seeded, today, make_family
) -> None:
    add_scheme(db, "card-test", CARD_RULE)
    family = widow_and_husbands_family(client, make_family, {"bpl_card": True}, None)

    results = schemes_of(eligibility(client, family), "Kamla")

    # The mother was never asked about the card, but the household has one: not unknown.
    card = results["card-test"]
    assert card["status"] == "eligible"
    assert "has_bpl_card" in {r["rule"]["field"] for r in card["passed_rules"]}
    assert card["unknown_rules"] == []
    # The same sharing drives the missing list: the card is not missing for her under IGNWPS either.
    assert "bpl_card" not in {d["code"] for d in results["ignwps"]["missing_documents"]}


def test_one_members_yes_beats_anothers_no_for_a_household_document(
    client: TestClient, db: Session, seeded, today, make_family
) -> None:
    add_scheme(db, "card-test", CARD_RULE)
    family = widow_and_husbands_family(client, make_family, {"bpl_card": True}, {"bpl_card": False})

    assert schemes_of(eligibility(client, family), "Kamla")["card-test"]["status"] == "eligible"


def test_when_nobody_has_the_bpl_card_the_mother_is_still_asked(
    client: TestClient, db: Session, seeded, today, make_family
) -> None:
    add_scheme(db, "card-test", CARD_RULE)
    family = widow_and_husbands_family(client, make_family, None, None)

    results = schemes_of(eligibility(client, family), "Kamla")

    assert results["card-test"]["status"] == "unknown"
    assert [r["rule"]["field"] for r in results["card-test"]["unknown_rules"]] == ["has_bpl_card"]
    missing = {d["code"]: d["state"] for d in results["ignwps"]["missing_documents"]}
    assert missing["bpl_card"] == "not_answered"  # still a required paper for IGNWPS


# --- IGNWPS: BPL status is the household's answer, the card is a paper ---------------------------


def test_a_bpl_family_without_the_card_qualifies_and_is_told_the_card_is_missing(
    client: TestClient, seeded, today, make_family
) -> None:
    family, _ = load_profile(
        client,
        make_family,
        today,
        DEFAULT_DATA_DIR / "test_profiles/16-bpl-widow-without-the-card.json",
    )

    ignwps = schemes_of(eligibility(client, family), "Kamla")["ignwps"]

    assert ignwps["status"] == "eligible"  # BPL is the family's own answer, not the card
    assert "is_bpl" in {r["rule"]["field"] for r in ignwps["passed_rules"]}
    missing = {d["code"]: d["state"] for d in ignwps["missing_documents"]}
    assert missing["bpl_card"] == "no"  # the required paper is shown as missing


def test_a_widow_whose_family_has_not_answered_the_bpl_question_is_asked_not_rejected(
    client: TestClient, seeded, today, make_family
) -> None:
    family = make_family(state="UP")  # is_bpl never answered
    member_id = add_member(
        client, family, "Kamla", birth_year=1964, gender="female", marital_status="widow"
    )
    put_documents(client, family, member_id, {"bpl_card": True})  # a card does not answer it

    ignwps = schemes_of(eligibility(client, family), "Kamla")["ignwps"]

    assert ignwps["status"] == "unknown"
    assert [r["rule"]["field"] for r in ignwps["unknown_rules"]] == ["is_bpl"]


def test_a_family_that_says_it_is_not_bpl_is_not_offered_ignwps(
    client: TestClient, seeded, today, make_family
) -> None:
    family = make_family(state="UP", is_bpl=False)
    member_id = add_member(
        client, family, "Kamla", birth_year=1964, gender="female", marital_status="widow"
    )
    put_documents(client, family, member_id, {"bpl_card": True})  # even with a card on file

    assert "ignwps" not in schemes_of(eligibility(client, family), "Kamla")


def test_personal_documents_are_not_shared_between_members(
    client: TestClient, seeded, today, make_family
) -> None:
    family = widow_and_husbands_family(client, make_family, {"aadhaar_card": True}, None)

    ignwps = schemes_of(eligibility(client, family), "Kamla")["ignwps"]

    assert "aadhaar_card" in {d["code"] for d in ignwps["missing_documents"]}


# --- safety ------------------------------------------------------------------------------------


def test_a_scheme_with_broken_rules_is_skipped_not_answered(
    client: TestClient, db: Session, seeded, today, make_family
) -> None:
    add_scheme(db, "broken", {"all": [{"field": "no_such_fact", "op": "eq", "value": 1}]})
    family = make_family()
    add_member(client, family, "Asha")

    body = eligibility(client, family)

    assert body["skipped_schemes"] == ["broken"]
    assert "broken" not in schemes_of(body, "Asha")
    assert "ignwps" in schemes_of(body, "Asha")  # the rest still works


def test_household_with_no_members_has_no_results(
    client: TestClient, seeded, today, make_family
) -> None:
    assert eligibility(client, make_family())["members"] == []


def test_eligibility_needs_a_session_for_the_households_own_user(
    client: TestClient, seeded, today, make_family
) -> None:
    mine, other = make_family(), make_family()
    url = f"{mine.url}/eligibility"

    assert client.get(url).status_code == 401  # not signed in
    assert client.get(url, headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.get(url, headers=other.headers).status_code == 403  # signed in, not theirs
    assert client.get(url, headers=mine.headers).status_code == 200


def test_the_real_clock_is_used_when_the_date_is_not_overridden(
    client: TestClient, make_family
) -> None:
    from datetime import datetime

    from app.api.facts import INDIA

    family = make_family()

    body = client.get(f"{family.url}/eligibility", headers=family.headers).json()

    # Computed in India's date, not the server's (which is UTC on Render).
    assert body["computed_on"] == datetime.now(INDIA).date().isoformat()


# --- a person added after setup is checked straight away -----------------------------------------


def ignoaps_status(body: dict[str, Any], nickname: str) -> str | None:
    result = schemes_of(body, nickname).get("ignoaps")
    return None if result is None else str(result["status"])


def test_a_person_added_after_setup_is_checked_straight_away(
    client: TestClient, seeded, today, make_family
) -> None:
    """The dashboard's 'Add a family member' uses the same endpoint as the setup. A person born in
    1958 in a UP household that is below the poverty line may qualify for IGNOAPS (60 or over)."""
    family = make_family(state="UP", is_bpl=True)
    add_member(client, family, "Asha", birth_year=1990)  # the owner, set up earlier
    assert ignoaps_status(eligibility(client, family), "Asha") is None  # 36: too young, not listed

    add_member(client, family, "Sita", birth_year=1958, relation="mother")  # added later

    body = eligibility(client, family)
    assert ignoaps_status(body, "Sita") == "eligible"
    assert {r["rule"]["field"] for r in schemes_of(body, "Sita")["ignoaps"]["passed_rules"]} == {
        "is_bpl",
        "age",
    }
    assert ignoaps_status(body, "Asha") is None  # the first person's results did not change


@pytest.mark.parametrize(
    ("is_bpl", "born", "expected"),
    [
        (True, 1958, "eligible"),
        (None, 1958, "unknown"),  # never answered: asked, not rejected
        (False, 1958, None),  # a definite "no": counted, not listed
        (True, 1990, None),  # under 60
    ],
)
def test_ignoaps_for_a_person_added_later_follows_the_family_and_the_age(
    client: TestClient, seeded, today, make_family, is_bpl, born, expected
) -> None:
    family = make_family(state="UP", is_bpl=is_bpl)
    add_member(client, family, "Sita", birth_year=born)

    assert ignoaps_status(eligibility(client, family), "Sita") == expected


def test_removing_a_person_removes_their_results(
    client: TestClient, seeded, today, make_family
) -> None:
    family = make_family(state="UP", is_bpl=True)
    keep = add_member(client, family, "Asha", birth_year=1990)
    gone = add_member(client, family, "Sita", birth_year=1958)
    assert ignoaps_status(eligibility(client, family), "Sita") == "eligible"

    assert client.delete(f"{family.url}/members/{gone}", headers=family.headers).status_code == 204

    body = eligibility(client, family)
    assert [m["nickname"] for m in body["members"]] == ["Asha"]
    assert keep  # the other person is untouched
