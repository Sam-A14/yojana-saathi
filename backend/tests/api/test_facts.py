from datetime import date

import pytest

from app.api.facts import (
    HOUSEHOLD_FACT_COLUMNS,
    MEMBER_FACT_COLUMNS,
    age_range,
    income_range,
    shared_documents,
)
from app.db.seed import read_seed_files
from app.rules.fields import HOUSEHOLD_FIELDS, MEMBER_FIELDS
from app.rules.values import HOUSEHOLD_DOCUMENT_CODES, INCOME_BANDS

TODAY = date(2026, 11, 3)


def test_birth_year_gives_two_possible_ages() -> None:
    assert age_range(1966, TODAY) == (59, 60)


def test_baby_born_this_year_is_zero_not_negative() -> None:
    assert age_range(2026, TODAY) == (0, 0)


def test_income_range_is_more_than_the_lower_edge_up_to_the_upper_edge() -> None:
    assert income_range("1_to_2_lakh") == (100_001, 200_000)
    assert income_range("up_to_1_lakh") == (0, 100_000)  # the first band includes 0


def test_top_band_starts_just_above_eight_lakh() -> None:
    assert income_range("above_8_lakh")[0] == 800_001


def test_top_income_band_has_no_upper_edge() -> None:
    assert income_range("above_8_lakh")[1] == float("inf")


def test_income_bands_leave_no_gaps_and_no_overlaps() -> None:
    bands = list(INCOME_BANDS.values())
    assert bands[0].lower == 0
    assert bands[-1].upper is None
    for below, above in zip(bands, bands[1:], strict=False):
        assert below.upper == above.lower  # shared edge...
        assert below.upper + 1 == above.lowest  # ...belongs to the lower band: every rupee in one


@pytest.mark.parametrize("band", list(INCOME_BANDS))
def test_every_band_converts(band: str) -> None:
    low, high = income_range(band)
    assert low < high


def test_every_engine_fact_is_wired_to_a_column() -> None:
    """Add a fact to rules/fields.py and forget facts.py: this fails instead of giving 'unknown'."""
    assert set(MEMBER_FACT_COLUMNS) | {"age"} == set(MEMBER_FIELDS)
    assert set(HOUSEHOLD_FACT_COLUMNS) | {"income_band_max"} == set(HOUSEHOLD_FIELDS)


# --- family-level documents -------------------------------------------------------------------


def test_one_member_holding_a_household_document_gives_it_to_everyone() -> None:
    mother, father = {}, {"bpl_card": True}

    assert shared_documents([mother, father]) == [{"bpl_card": True}, {"bpl_card": True}]


def test_a_yes_overrides_another_members_no() -> None:
    assert shared_documents([{"ration_card": False}, {"ration_card": True}])[0] == {
        "ration_card": True
    }


def test_when_nobody_has_it_answers_stay_as_given() -> None:
    answers = [{"bpl_card": False}, {}]

    # No invented "no" for the member who was not asked, and no invented "yes".
    assert shared_documents(answers) == answers


def test_personal_documents_are_not_shared() -> None:
    assert shared_documents([{"aadhaar_card": True}, {}]) == [{"aadhaar_card": True}, {}]


def test_sharing_does_not_change_the_callers_data() -> None:
    answers = [{}, {"bpl_card": True}]

    shared_documents(answers)

    assert answers == [{}, {"bpl_card": True}]


def test_household_document_codes_exist_and_match_the_seed_files() -> None:
    data = read_seed_files()
    known = {d["code"] for d in data.documents}
    assert HOUSEHOLD_DOCUMENT_CODES <= known
    # A scheme that marks a document "applies_to: household" must be one we actually share.
    marked = {
        d["code"]
        for scheme in data.schemes
        for d in scheme["version"]["documents"]
        if d["applies_to"] == "household"
    }
    assert marked <= HOUSEHOLD_DOCUMENT_CODES
