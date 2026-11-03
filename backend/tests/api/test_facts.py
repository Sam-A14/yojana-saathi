from datetime import date

import pytest

from app.api.facts import (
    HOUSEHOLD_FACT_COLUMNS,
    MEMBER_FACT_COLUMNS,
    age_range,
    income_range,
)
from app.rules.fields import HOUSEHOLD_FIELDS, MEMBER_FIELDS
from app.rules.values import INCOME_BANDS

TODAY = date(2026, 11, 3)


def test_birth_year_gives_two_possible_ages() -> None:
    assert age_range(1966, TODAY) == (59, 60)


def test_baby_born_this_year_is_zero_not_negative() -> None:
    assert age_range(2026, TODAY) == (0, 0)


def test_income_range_is_the_bands_edges() -> None:
    assert income_range("1_to_2_lakh") == (100_000, 200_000)


def test_top_income_band_has_no_upper_edge() -> None:
    assert income_range("above_8_lakh")[1] == float("inf")


def test_income_bands_leave_no_gaps_and_no_overlaps() -> None:
    bands = list(INCOME_BANDS.values())
    assert bands[0].lower == 0
    assert bands[-1].upper is None
    for below, above in zip(bands, bands[1:], strict=False):
        assert below.upper == above.lower


@pytest.mark.parametrize("band", list(INCOME_BANDS))
def test_every_band_converts(band: str) -> None:
    low, high = income_range(band)
    assert low < high


def test_every_engine_fact_is_wired_to_a_column() -> None:
    """Add a fact to rules/fields.py and forget facts.py: this fails instead of giving 'unknown'."""
    assert set(MEMBER_FACT_COLUMNS) | {"age"} == set(MEMBER_FIELDS)
    assert set(HOUSEHOLD_FACT_COLUMNS) | {"income_band_max"} == set(HOUSEHOLD_FIELDS)
