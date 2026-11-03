"""Range evaluation without a database: the engine is run at the corners of each range."""

import json
import math
from typing import Any

import pytest

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


@pytest.mark.parametrize(
    ("income", "status", "reasons"),
    [
        ((100_000, 200_000), "eligible", ()),  # whole band is within the limit
        ((200_000, 250_000), "unknown", ("depends_on_exact_income",)),  # could be over by a rupee
        ((300_000, 500_000), "not_eligible", ()),  # whole band is over the limit
    ],
)
def test_income_band_against_a_two_lakh_limit(income, status, reasons) -> None:
    result = run(rules(INCOME_UP_TO_2_LAKH), income=income)

    assert (result.status, result.reasons) == (status, reasons)


def test_a_limit_inside_the_band_is_unknown() -> None:
    rule = rules({"field": "income_band_max", "op": "lte", "value": 150000})

    assert run(rule, income=(100_000, 200_000)).reasons == ("depends_on_exact_income",)


def test_top_band_has_no_upper_edge() -> None:
    top = (800_000, math.inf)
    limit_10_lakh = rules({"field": "income_band_max", "op": "lte", "value": 1_000_000})
    limit_5_lakh = rules({"field": "income_band_max", "op": "lte", "value": 500_000})
    at_least_5_lakh = rules({"field": "income_band_max", "op": "gte", "value": 500_000})

    assert run(limit_10_lakh, income=top).reasons == ("depends_on_exact_income",)
    assert run(limit_5_lakh, income=top).status == "not_eligible"
    assert run(at_least_5_lakh, income=top).status == "eligible"


def test_no_income_band_is_plain_unknown() -> None:
    result = run(rules(INCOME_UP_TO_2_LAKH), income=None)

    assert (result.status, result.reasons) == ("unknown", ())


# --- both at once -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("age", "income", "reasons"),
    [
        ((39, 40), (100_000, 200_000), ("depends_on_exact_age",)),
        ((65, 66), (200_000, 250_000), ("depends_on_exact_income",)),
        ((39, 40), (200_000, 250_000), ("depends_on_exact_age", "depends_on_exact_income")),
    ],
)
def test_reason_names_only_the_detail_that_matters(age, income, reasons) -> None:
    result = run(rules(AGE_40, INCOME_UP_TO_2_LAKH), age=age, income=income)

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
