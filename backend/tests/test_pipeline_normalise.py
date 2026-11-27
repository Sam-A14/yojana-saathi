"""Accuracy normalisation: equivalent spellings score as equal, and only those."""

import itertools
from typing import Any

import pytest

from app.db.models.family import Household, Member
from app.pipeline.accuracy import (
    BOOLEAN_FIELDS,
    CLOSED_VALUES,
    compare_rules,
    normalise,
    render_accuracy,
)
from app.rules.engine import HouseholdFacts, evaluate
from app.rules.fields import ATTRIBUTE_FIELDS


def rules(*nodes: dict[str, Any]) -> dict[str, Any]:
    return {"all": list(nodes), "fixable": []}


def cond(field: str, op: str, value: Any = None) -> dict[str, Any]:
    node: dict[str, Any] = {"field": field, "op": op}
    if op != "is_true":
        node["value"] = value
    return node


def no_member(node: dict[str, Any]) -> dict[str, Any]:
    return {"not": {"any_member": node}}


# --- the run that started this: "neq none AND neq group_d" versus "eq other" ----------------------


def test_two_neq_on_a_closed_list_equal_the_one_value_left() -> None:
    seed = rules(no_member(cond("govt_employee", "eq", "other")))
    proposed = rules(
        no_member(
            {"all": [cond("govt_employee", "neq", "none"), cond("govt_employee", "neq", "group_d")]}
        )
    )

    result = compare_rules("pm-kisan", seed, proposed)

    assert len(result.missed) == 1 and len(result.extra) == 2  # exact: 1 seed leaf, 2 proposed
    assert result.normalised.missed == [] and result.normalised.extra == []
    text = render_accuracy([result])
    assert "exact:      precision 0% (0/2), recall 0% (0/1)" in text
    assert "normalised: precision 100% (1/1), recall 100% (1/1)" in text
    assert "Every condition matches after normalising." in text
    assert "    extraction: govt_employee: 2 conditions under one all -> in ['other']" in text
    assert "    seed file: govt_employee: eq \"other\" -> in ['other']" in text


def test_the_rewrites_that_fired_are_listed_per_side() -> None:
    result = compare_rules(
        "x",
        rules(no_member(cond("govt_employee", "eq", "other"))),
        rules(no_member(cond("govt_employee", "neq", "none"))),
    )
    text = render_accuracy([result])

    assert "Rewrites that fired" in text
    assert "    seed file: govt_employee: eq \"other\" -> in ['other']" in text
    assert "    extraction: govt_employee: neq \"none\" -> in ['group_d', 'other']" in text
    assert "Still different after normalising:" in text  # group_d is allowed in one, not the other


# --- set rewrites ---------------------------------------------------------------------------------


def test_all_intersects_and_any_unions() -> None:
    out, _ = normalise(
        rules(
            {
                "all": [
                    cond("pension_band", "in", ["none", "below_10k"]),
                    cond("pension_band", "neq", "none"),
                ]
            },
            {"any": [cond("gender", "eq", "female"), cond("gender", "eq", "other")]},
        )
    )
    # A merged `any` keeps its wrapper with one child; leaf comparison treats that as the child.
    assert out["all"] == [
        cond("pension_band", "in", ["below_10k"]),  # spliced into the top-level all
        {"any": [cond("gender", "in", ["female", "other"])]},
    ]


def test_nested_all_inside_all_is_spliced_before_merging() -> None:
    out, _ = normalise(
        rules(
            cond("govt_employee", "neq", "none"),
            {"all": [cond("govt_employee", "neq", "group_d")]},
        )
    )
    assert out["all"] == [cond("govt_employee", "in", ["other"])]


def test_not_in_and_in_are_the_same_set() -> None:
    a, _ = normalise(rules(cond("category", "not_in", ["General"])))
    b, _ = normalise(rules(cond("category", "in", ["OBC", "SC", "ST"])))
    assert a["all"] == b["all"]


def test_conditions_stay_apart_across_any_member_and_not_boundaries() -> None:
    # "some member is not group_d AND some (maybe other) member is not none" is a different rule
    # from one member satisfying both, so these must not merge into one condition.
    out, _ = normalise(
        rules(
            {"any_member": cond("govt_employee", "neq", "group_d")},
            {"any_member": cond("govt_employee", "neq", "none")},
        )
    )
    assert out["all"] == [
        {"any_member": cond("govt_employee", "in", ["none", "other"])},
        {"any_member": cond("govt_employee", "in", ["group_d", "other"])},
    ]


def test_a_never_true_combination_is_left_as_a_difference() -> None:
    original = rules({"all": [cond("gender", "eq", "male"), cond("gender", "eq", "female")]})
    out, _ = normalise(original)
    # Not merged (an empty "in" cannot be written): each condition is only canonicalised alone.
    assert out["all"] == [cond("gender", "in", ["male"]), cond("gender", "in", ["female"])]


def test_a_field_without_a_closed_list_is_never_rewritten() -> None:
    for node in (
        cond("state", "neq", "UP"),
        cond("age", "gte", 18),
        cond("district", "eq", "Agra"),
    ):
        out, fired = normalise(rules(node))
        assert out["all"] == [node] and fired == []
    # and so "neq UP" against "in [every other state]" stays a difference
    result = compare_rules(
        "x", rules(cond("state", "neq", "UP")), rules(cond("state", "in", ["BR"]))
    )
    assert result.normalised.missed and result.normalised.extra


def test_a_value_outside_the_list_is_not_touched() -> None:
    node = cond("govt_employee", "eq", "contractor")
    out, fired = normalise(rules(node))
    assert out["all"] == [node] and fired == []


def test_not_around_a_condition_is_not_turned_into_neq() -> None:
    result = compare_rules(
        "x",
        rules({"not": cond("govt_employee", "eq", "none")}),
        rules(cond("govt_employee", "neq", "none")),
    )
    assert result.normalised.missed and result.normalised.extra  # stays a difference, on purpose


def test_the_input_rules_are_not_modified() -> None:
    original = rules(
        {"all": [cond("govt_employee", "neq", "none"), cond("govt_employee", "neq", "group_d")]}
    )
    snapshot = repr(original)
    normalise(original)
    assert repr(original) == snapshot


# --- booleans -------------------------------------------------------------------------------------


@pytest.mark.parametrize("field", ["is_student", "owns_cultivable_land", "has_land_record"])
def test_eq_true_on_a_yes_no_field_becomes_is_true(field: str) -> None:
    out, fired = normalise(rules(cond(field, "eq", True)))
    assert out["all"] == [cond(field, "is_true")]
    assert fired == [f"{field}: eq true -> is_true"]
    result = compare_rules("x", rules(cond(field, "is_true")), rules(cond(field, "eq", True)))
    assert result.normalised.missed == [] and result.normalised.extra == []
    assert result.missed and result.extra  # still a difference in the exact score


@pytest.mark.parametrize(
    "node",
    [cond("is_student", "eq", False), cond("age", "eq", True), cond("gender", "eq", True)],
)
def test_eq_false_and_eq_true_on_other_fields_are_left_alone(node: dict[str, Any]) -> None:
    out, fired = normalise(rules(node))
    assert out["all"] == [node] and not any("is_true" in f for f in fired)


def test_the_boolean_list_matches_the_yes_no_columns_of_the_member_and_household_tables() -> None:
    columns = {
        c.name
        for table in (Member.__table__, Household.__table__)
        for c in table.columns
        if c.type.python_type is bool  # type: ignore[attr-defined]
    }
    assert BOOLEAN_FIELDS == columns & ATTRIBUTE_FIELDS


def test_every_closed_list_field_is_a_known_rule_field() -> None:
    assert set(CLOSED_VALUES) <= ATTRIBUTE_FIELDS


# --- the rewrites never change what the engine says ---------------------------------

GOVT = list(CLOSED_VALUES["govt_employee"])


def _status(rule: dict[str, Any], govt: str | None, pension: str | None) -> str:
    member = {"nickname": "A", "govt_employee": govt, "pension_band": pension}
    return evaluate(member, HouseholdFacts({}, [member]), rule).status


@pytest.mark.parametrize(
    "tree",
    [
        no_member(
            {"all": [cond("govt_employee", "neq", "none"), cond("govt_employee", "neq", "group_d")]}
        ),
        no_member(
            {"any": [cond("govt_employee", "eq", "none"), cond("govt_employee", "eq", "group_d")]}
        ),
        {
            "any_member": {
                "all": [
                    cond("govt_employee", "not_in", ["none"]),
                    cond("pension_band", "neq", "none"),
                ]
            }
        },
        {
            "any_member": {
                "any": [cond("pension_band", "neq", "none"), cond("govt_employee", "in", ["other"])]
            }
        },
        {
            "any_member": {
                "all": [
                    cond("pension_band", "eq", "10k_plus"),
                    cond("govt_employee", "neq", "group_d"),
                ]
            }
        },
    ],
)
def test_normalised_rules_give_the_same_engine_answer_for_every_fact(tree: dict[str, Any]) -> None:
    original = rules(tree)
    rewritten, _ = normalise(original)
    values = [None, *GOVT]
    pensions = [None, *CLOSED_VALUES["pension_band"]]
    for govt, pension in itertools.product(values, pensions):
        assert _status(rewritten, govt, pension) == _status(original, govt, pension), (
            govt,
            pension,
        )


def test_rewrites_both_sides_share_are_counted_but_not_listed() -> None:
    node = no_member(cond("govt_employee", "eq", "other"))
    text = render_accuracy([compare_rules("x", rules(node), rules(node))])

    assert "none that differ between the two sides" in text
    assert "1 identical rewrites on both sides not listed" in text
    assert "seed file:" not in text
