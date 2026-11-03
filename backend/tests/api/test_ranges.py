"""Range evaluation without a database: the engine is run at the corners of each range."""

import json
from typing import Any

import pytest

from app.api.facts import income_range
from app.api.ranges import MAX_UNCERTAIN_AGES, Ranges, evaluate_with_ranges
from app.db.seed import DEFAULT_DATA_DIR
from app.rules.engine import RuleError

AGE_40 = {"field": "age", "op": "gte", "value": 40}
INCOME_UP_TO_2_LAKH = {"field": "income_band_max", "op": "lte", "value": 200000}


def rules(*conditions: dict[str, Any]) -> dict[str, Any]:
    return {"all": list(conditions), "fixable": []}


def run(
    rule: dict[str, Any],
    age: tuple[int, int] | None = None,
    income: tuple[float, float] | None = None,
    **facts: Any,
):  # noqa: ANN201
    person = {"nickname": "Asha", **facts}
    ages = {0: age} if age else {}
    return evaluate_with_ranges(0, [person], {}, rule, Ranges(ages, income))


# --- age ------------------------------------------------------------------------------------


def test_age_range_entirely_above_the_limit_is_eligible() -> None:
    result = run(rules(AGE_40), age=(65, 66))

    assert (result.status, result.reasons) == ("eligible", ())


def test_age_range_entirely_below_the_limit_is_not_eligible() -> None:
    assert run(rules(AGE_40), age=(38, 39)).status == "not_eligible"


def test_birthday_could_put_the_person_just_under_the_limit() -> None:
    # Aged 39 or 40: whether they qualify depends on a birthday we do not know.
    result = run(rules(AGE_40), age=(39, 40))

    assert result.status == "unknown"
    assert result.reasons == ("depends_on_exact_age",)
    (rule,) = result.rule_results
    assert (rule.outcome, rule.reasons) == ("unknown", ("depends_on_exact_age",))


def test_range_starting_exactly_at_the_limit_is_eligible() -> None:
    # Aged 40 or 41: both are 40 or over, so there is nothing to guess.
    assert run(rules(AGE_40), age=(40, 41)).status == "eligible"


def test_a_definite_failure_beats_an_age_that_is_unclear() -> None:
    result = run(
        rules({"field": "gender", "op": "eq", "value": "female"}, AGE_40), (39, 40), gender="male"
    )

    # Whatever the exact age, a man fails the gender rule, so asking for the birthday is pointless.
    assert result.status == "not_eligible"
    assert result.reasons == ()


def test_no_birth_year_is_plain_unknown_without_a_range_reason() -> None:
    result = run(rules(AGE_40), age=None)

    assert (result.status, result.reasons) == ("unknown", ())


def test_rules_that_ignore_age_are_not_made_unknown_by_a_wide_age_range() -> None:
    rule = rules({"field": "gender", "op": "eq", "value": "female"})

    assert run(rule, age=(0, 99), gender="female").status == "eligible"


# --- income ---------------------------------------------------------------------------------
# Bands are "more than lower, up to and including upper", so a limit exactly at a band edge has a
# definite answer. Only a limit inside the band is unknown.


def at_most(limit: int) -> dict[str, Any]:
    return rules({"field": "income_band_max", "op": "lte", "value": limit})


@pytest.mark.parametrize(
    ("band", "limit", "status", "reasons"),
    [
        ("1_to_2_lakh", 200_000, "eligible", ()),  # the top edge belongs to this band
        ("1_to_2_lakh", 100_000, "not_eligible", ()),  # the bottom edge belongs to the band below
        ("1_to_2_lakh", 150_000, "unknown", ("depends_on_exact_income",)),  # limit inside the band
        ("up_to_1_lakh", 100_000, "eligible", ()),
        ("2_to_2_5_lakh", 200_000, "not_eligible", ()),  # the whole band is above the limit
        ("3_to_5_lakh", 200_000, "not_eligible", ()),
    ],
)
def test_income_band_against_a_limit(band, limit, status, reasons) -> None:
    result = run(at_most(limit), income=income_range(band))

    assert (result.status, result.reasons) == (status, reasons)


def test_first_band_includes_zero_so_a_limit_of_zero_is_unclear() -> None:
    assert run(at_most(0), income=income_range("up_to_1_lakh")).reasons == (
        "depends_on_exact_income",
    )


def test_a_minimum_exactly_at_the_lower_edge_is_met_by_every_income_in_the_band() -> None:
    # More than 100000 means at least 100001, so "at least 100000" always holds in 1_to_2_lakh.
    rule = rules({"field": "income_band_max", "op": "gte", "value": 100_000})

    assert run(rule, income=income_range("1_to_2_lakh")).status == "eligible"


def test_top_band_has_no_upper_edge() -> None:
    top = income_range("above_8_lakh")
    limit_10_lakh = at_most(1_000_000)
    at_least_5_lakh = rules({"field": "income_band_max", "op": "gte", "value": 500_000})

    assert run(limit_10_lakh, income=top).reasons == ("depends_on_exact_income",)
    assert run(at_most(500_000), income=top).status == "not_eligible"
    assert run(at_most(800_000), income=top).status == "not_eligible"  # "above 8 lakh" is over it
    assert run(at_least_5_lakh, income=top).status == "eligible"


def test_no_income_band_is_plain_unknown() -> None:
    result = run(rules(INCOME_UP_TO_2_LAKH), income=None)

    assert (result.status, result.reasons) == ("unknown", ())


# --- both at once -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("age", "limit", "reasons"),
    [
        ((39, 40), 200_000, ("depends_on_exact_age",)),  # income is clear (band is under 2 lakh)
        ((65, 66), 150_000, ("depends_on_exact_income",)),  # age is clear (always over 40)
        ((39, 40), 150_000, ("depends_on_exact_age", "depends_on_exact_income")),
    ],
)
def test_reason_names_only_the_detail_that_matters(age, limit, reasons) -> None:
    result = run(
        rules(AGE_40, at_most(limit)["all"][0]), age=age, income=income_range("1_to_2_lakh")
    )

    assert result.status == "unknown"
    assert result.reasons == reasons


# --- other members' ages (any_member) -----------------------------------------------------------


NO_ADULT_TAXPAYER = rules(
    {
        "not": {
            "any_member": {
                "all": [
                    AGE_18 := {"field": "age", "op": "gte", "value": 18},
                    {"field": "paid_income_tax_last_year", "op": "is_true"},
                ]
            }
        }
    }
)


def family(son_age: tuple[int, int]):  # noqa: ANN201
    people = [
        {"nickname": "Ramesh", "paid_income_tax_last_year": False},
        {"nickname": "Suresh", "paid_income_tax_last_year": True},
    ]
    ranges = Ranges({0: (48, 49), 1: son_age}, None)
    return evaluate_with_ranges(0, people, {}, NO_ADULT_TAXPAYER, ranges)


def test_another_members_age_can_make_the_answer_unclear() -> None:
    result = family((17, 18))  # the son may or may not be an adult taxpayer

    assert result.status == "unknown"
    assert result.reasons == ("depends_on_exact_age",)


def test_an_adult_son_who_paid_tax_excludes_the_family_and_is_named() -> None:
    result = family((27, 28))

    assert result.status == "not_eligible"
    assert result.rule_results[0].matched_members == ("Suresh",)


def test_a_minor_son_does_not_exclude_the_family() -> None:
    assert family((10, 11)).status == "eligible"


def test_too_many_uncertain_ages_gives_unknown_not_a_wrong_answer() -> None:
    count = MAX_UNCERTAIN_AGES + 1
    people = [{"nickname": f"P{i}"} for i in range(count)]
    rule = rules({"any_member": AGE_18})

    result = evaluate_with_ranges(
        0, people, {}, rule, Ranges({i: (17, 18) for i in range(count)}, None)
    )

    assert (result.status, result.reasons) == ("unknown", ("depends_on_exact_age",))


# --- the rest -----------------------------------------------------------------------------------


def test_malformed_rules_still_raise() -> None:
    with pytest.raises(RuleError):
        run(rules({"field": "no_such_fact", "op": "eq", "value": 1}))


PROFILES = sorted((DEFAULT_DATA_DIR / "test_profiles").glob("*.json"))
SCHEME_RULES = {
    path.stem: json.loads(path.read_text(encoding="utf-8"))["version"]["rules"]
    for path in (DEFAULT_DATA_DIR / "schemes_seed").glob("*.json")
    if path.stem != "TEMPLATE"
}


@pytest.mark.parametrize("path", PROFILES, ids=lambda p: p.stem)
def test_exact_values_give_exactly_the_hand_checked_profile_answers(path) -> None:
    """With ranges of width zero this layer must change nothing about the engine's answers."""
    profile = json.loads(path.read_text(encoding="utf-8"))
    people = [{k: v for k, v in m.items() if k != "age"} for m in profile["members"]]
    exact_ages = {i: (m["age"], m["age"]) for i, m in enumerate(profile["members"])}
    household = {k: v for k, v in profile["household"].items() if k != "income_band_max"}
    income = profile["household"]["income_band_max"]
    ranges = Ranges(exact_ages, (income, income))

    for slug, expected in profile["expected"].items():
        for i, member in enumerate(profile["members"]):
            got = evaluate_with_ranges(i, people, household, SCHEME_RULES[slug], ranges)
            assert (
                got.status == expected[member["nickname"]]
            ), f"{path.name} / {slug} / {member['nickname']}"
