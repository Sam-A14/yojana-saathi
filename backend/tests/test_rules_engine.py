"""Unit tests for the rules engine. No database: the engine is a pure function.

Layout: operators, combinators, missing data, household rules, near-miss, malformed rules.
"""

from typing import Any

import pytest

from app.rules.engine import Evaluation, HouseholdFacts, RuleError, evaluate, validate_rules


def person(**facts: Any) -> dict[str, Any]:
    return {"nickname": "Asha", **facts}


def check(
    rules: dict[str, Any],
    member: dict[str, Any] | None = None,
    members: list[dict[str, Any]] | None = None,
    **household: Any,
) -> Evaluation:
    """Evaluate `rules`. By default the household is just the member."""
    member = member if member is not None else person()
    facts = HouseholdFacts(household, members if members is not None else [member])
    return evaluate(member, facts, rules)


def condition(field: str, op: str, value: Any = None) -> dict[str, Any]:
    node: dict[str, Any] = {"field": field, "op": op}
    if op != "is_true":
        node["value"] = value
    return node


def status_of(node: dict[str, Any], member: dict[str, Any] | None = None, **household: Any) -> str:
    return check({"all": [node]}, member, **household).status


# ---------------------------------------------------------------- operators


@pytest.mark.parametrize(
    ("op", "value", "actual", "expected"),
    [
        ("eq", "UP", "UP", "eligible"),
        ("eq", "UP", "BR", "not_eligible"),
        ("neq", "UP", "BR", "eligible"),
        ("neq", "UP", "UP", "not_eligible"),
        ("in", ["SC", "ST"], "ST", "eligible"),
        ("in", ["SC", "ST"], "GEN", "not_eligible"),
        ("not_in", ["SC", "ST"], "GEN", "eligible"),
        ("not_in", ["SC", "ST"], "SC", "not_eligible"),
        ("gte", 18, 18, "eligible"),  # boundary is inclusive
        ("gte", 18, 17, "not_eligible"),
        ("lte", 60, 60, "eligible"),  # boundary is inclusive
        ("lte", 60, 61, "not_eligible"),
        ("between", [18, 60], 18, "eligible"),  # both ends inclusive
        ("between", [18, 60], 60, "eligible"),
        ("between", [18, 60], 17, "not_eligible"),
        ("between", [18, 60], 61, "not_eligible"),
    ],
)
def test_each_operator_on_a_household_or_member_fact(
    op: str, value: Any, actual: Any, expected: str
) -> None:
    field = {"gte": "age", "lte": "age", "between": "age"}.get(op, "category")
    member = person(age=actual) if field == "age" else person()
    household = {"category": actual} if field == "category" else {}

    assert status_of(condition(field, op, value), member, **household) == expected


def test_is_true_operator() -> None:
    rule = condition("is_student", "is_true")

    assert status_of(rule, person(is_student=True)) == "eligible"
    assert status_of(rule, person(is_student=False)) == "not_eligible"


def test_eq_does_not_confuse_true_with_one() -> None:
    assert status_of(condition("age", "eq", True), person(age=1)) == "not_eligible"


def test_household_facts_are_read_from_the_household_not_the_member() -> None:
    rule = condition("state", "eq", "UP")

    assert status_of(rule, person(state="BR"), state="UP") == "eligible"


def test_non_numeric_fact_for_a_numeric_operator_is_an_error() -> None:
    with pytest.raises(RuleError, match="should be a number"):
        status_of(condition("age", "gte", 18), person(age="old"))


def test_non_boolean_fact_for_is_true_is_an_error() -> None:
    with pytest.raises(RuleError, match="true/false"):
        status_of(condition("is_student", "is_true"), person(is_student="yes"))


# ---------------------------------------------------------------- combinators


YES = condition("is_student", "is_true")
NO = condition("disability", "is_true")
ME = person(is_student=True, disability=False)


def test_all_needs_every_child() -> None:
    assert status_of({"all": [YES, YES]}, ME) == "eligible"
    assert status_of({"all": [YES, NO]}, ME) == "not_eligible"


def test_any_needs_one_child() -> None:
    assert status_of({"any": [NO, YES]}, ME) == "eligible"
    assert status_of({"any": [NO, NO]}, ME) == "not_eligible"


def test_not_flips_the_child() -> None:
    assert status_of({"not": NO}, ME) == "eligible"
    assert status_of({"not": YES}, ME) == "not_eligible"


def test_groups_nest() -> None:
    rule = {"all": [YES, {"any": [NO, {"not": NO}]}]}

    assert status_of(rule, ME) == "eligible"


# ---------------------------------------------------------------- missing data


@pytest.mark.parametrize(
    "node",
    [
        condition("category", "eq", "SC"),
        condition("category", "neq", "SC"),
        condition("category", "in", ["SC"]),
        condition("category", "not_in", ["SC"]),
        condition("age", "gte", 18),
        condition("age", "lte", 18),
        condition("age", "between", [1, 2]),
        condition("is_student", "is_true"),
    ],
)
def test_missing_fact_is_unknown_for_every_operator(node: dict[str, Any]) -> None:
    assert status_of(node, person()) == "unknown"
    assert status_of(node, person(age=None, is_student=None)) == "unknown"


def test_not_of_unknown_stays_unknown() -> None:
    assert status_of({"not": condition("is_student", "is_true")}, person()) == "unknown"


def test_a_definite_failure_beats_unknown() -> None:
    rules = {"all": [condition("is_student", "is_true"), condition("age", "gte", 18)]}

    result = check(rules, person(is_student=False))  # age missing

    assert result.status == "not_eligible"
    assert [r.outcome for r in result.rule_results] == ["failed", "unknown"]


def test_a_definite_pass_beats_unknown_inside_any() -> None:
    rule = {"any": [condition("age", "gte", 18), YES]}

    assert status_of(rule, person(is_student=True)) == "eligible"


def test_missing_document_answer_is_unknown_not_no() -> None:
    rule = condition("has_land_record", "is_true")

    assert status_of(rule, person()) == "unknown"
    assert status_of(rule, person(has_land_record=False)) == "not_eligible"


# ---------------------------------------------------------------- household rules


TAX = condition("paid_income_tax_last_year", "is_true")
EXCLUDED_IF_TAX = {"not": {"any_member": TAX}}


def family(*people: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return people[0], list(people)


def test_any_member_matches_when_one_member_matches() -> None:
    asha, members = family(person(), {"nickname": "Dada", "paid_income_tax_last_year": True})

    assert check({"all": [{"any_member": TAX}]}, asha, members).status == "eligible"


def test_any_member_fails_when_nobody_matches() -> None:
    asha, members = family(
        person(paid_income_tax_last_year=False),
        {"nickname": "Dada", "paid_income_tax_last_year": False},
    )

    assert check({"all": [{"any_member": TAX}]}, asha, members).status == "not_eligible"


def test_any_member_is_unknown_if_nobody_matches_but_someone_is_unanswered() -> None:
    asha, members = family(person(paid_income_tax_last_year=False), {"nickname": "Dada"})

    assert check({"all": [{"any_member": TAX}]}, asha, members).status == "unknown"


def test_a_definite_match_beats_an_unanswered_member() -> None:
    asha, members = family(person(), {"nickname": "Dada", "paid_income_tax_last_year": True})

    assert check({"all": [{"any_member": TAX}]}, asha, members).status == "eligible"


def test_inner_rule_applies_to_one_member_at_a_time() -> None:
    """'Pensioner AND not Group D' must describe ONE person, not two people with one fact each."""
    rule = {
        "any_member": {
            "all": [
                condition("pension_band", "eq", "10k_plus"),
                condition("govt_employee", "neq", "group_d"),
            ]
        }
    }
    pensioner = {"nickname": "Dada", "pension_band": "10k_plus", "govt_employee": "group_d"}
    other = {"nickname": "Chacha", "pension_band": "none", "govt_employee": "other"}

    result = check({"all": [rule]}, pensioner, [pensioner, other])

    assert result.status == "not_eligible"  # nobody has both facts


def test_exclusion_names_the_member_who_triggered_it() -> None:
    asha, members = family(
        person(paid_income_tax_last_year=False),
        {"nickname": "Ramesh", "paid_income_tax_last_year": True},
        {"nickname": "Sunita", "paid_income_tax_last_year": False},
    )

    result = check({"all": [EXCLUDED_IF_TAX]}, asha, members)

    assert result.status == "not_eligible"
    (failed,) = result.failed
    assert failed.matched_members == ("Ramesh",)
    assert failed.fields == ("paid_income_tax_last_year",)


def test_exclusion_names_every_member_who_triggered_it() -> None:
    asha, members = family(
        person(paid_income_tax_last_year=True),
        {"nickname": "Ramesh", "paid_income_tax_last_year": True},
    )

    (failed,) = check({"all": [EXCLUDED_IF_TAX]}, asha, members).failed

    assert failed.matched_members == ("Asha", "Ramesh")


def test_passing_exclusion_names_nobody() -> None:
    asha, members = family(person(paid_income_tax_last_year=False))

    (passed,) = check({"all": [EXCLUDED_IF_TAX]}, asha, members).passed

    assert passed.matched_members == ()


def test_members_are_named_separately_for_each_rule() -> None:
    post = condition("holds_constitutional_post", "is_true")
    rules = {"all": [EXCLUDED_IF_TAX, {"not": {"any_member": post}}]}
    asha, members = family(
        person(),
        {"nickname": "Ramesh", "paid_income_tax_last_year": True},
        {"nickname": "Sunita", "holds_constitutional_post": True},
    )

    first, second = check(rules, asha, members).rule_results

    assert first.matched_members == ("Ramesh",)
    assert second.matched_members == ("Sunita",)


def test_household_condition_inside_any_member_reads_the_household() -> None:
    rule = {"any_member": {"all": [condition("state", "eq", "UP"), condition("age", "gte", 60)]}}
    asha, members = family(person(age=30), {"nickname": "Dada", "age": 70})

    assert check({"all": [rule]}, asha, members, state="UP").status == "eligible"
    assert check({"all": [rule]}, asha, members, state="BR").status == "not_eligible"


def test_empty_household_list_makes_any_member_false() -> None:
    assert check({"all": [{"any_member": TAX}]}, person(), members=[]).status == "not_eligible"


def test_among_household_is_accepted_and_other_values_are_not() -> None:
    validate_rules({"all": [{"any_member": TAX, "among": "household"}]})
    with pytest.raises(RuleError, match="not supported yet"):
        validate_rules({"all": [{"any_member": TAX, "among": "applicant_family"}]})


# ---------------------------------------------------------------- near miss


def test_failing_only_a_fixable_rule_is_a_near_miss() -> None:
    rules = {
        "all": [condition("age", "gte", 18), condition("has_ration_card", "is_true")],
        "fixable": ["has_ration_card"],
    }

    result = check(rules, person(age=30, has_ration_card=False))

    assert result.status == "near_miss"
    assert [r.fixable for r in result.rule_results] == [False, True]


def test_failing_a_fixable_and_a_non_fixable_rule_is_not_eligible() -> None:
    rules = {
        "all": [condition("age", "gte", 18), condition("has_ration_card", "is_true")],
        "fixable": ["has_ration_card"],
    }

    assert check(rules, person(age=10, has_ration_card=False)).status == "not_eligible"


def test_nothing_fixable_means_no_near_miss() -> None:
    rules = {"all": [condition("has_ration_card", "is_true")], "fixable": []}

    assert check(rules, person(has_ration_card=False)).status == "not_eligible"


def test_fixable_branch_of_an_any_is_enough_for_a_near_miss() -> None:
    rules = {
        "all": [{"any": [condition("has_bpl_card", "is_true"), condition("age", "gte", 80)]}],
        "fixable": ["has_bpl_card"],
    }

    assert check(rules, person(age=30, has_bpl_card=False)).status == "near_miss"


def test_fixable_inside_not_is_relaxed_the_helpful_way() -> None:
    """not(has_x) with has_x fixable: the family is fixed by making has_x FALSE, not true.

    Forcing the condition to true (the naive relaxation) would make not(...) fail and report a
    wrong not_eligible.
    """
    rules = {
        "all": [{"not": condition("has_ration_card", "is_true")}],
        "fixable": ["has_ration_card"],
    }

    result = check(rules, person(has_ration_card=True))

    assert result.status == "near_miss"
    assert result.rule_results[0].fixable is True


def test_fixable_inside_double_not_is_relaxed_back_to_true() -> None:
    rule = {"not": {"not": condition("has_ration_card", "is_true")}}

    result = check({"all": [rule], "fixable": ["has_ration_card"]}, person(has_ration_card=False))

    assert result.status == "near_miss"


def test_fixable_inside_not_any_member_is_relaxed_the_helpful_way() -> None:
    rules = {
        "all": [{"not": {"any_member": condition("has_ration_card", "is_true")}}],
        "fixable": ["has_ration_card"],
    }

    assert check(rules, person(has_ration_card=True)).status == "near_miss"


def test_relaxing_never_creates_eligibility_from_a_different_failure() -> None:
    rules = {
        "all": [{"not": condition("has_ration_card", "is_true")}, condition("age", "gte", 18)],
        "fixable": ["has_ration_card"],
    }

    assert check(rules, person(has_ration_card=True, age=5)).status == "not_eligible"


def test_unknown_stays_unknown_when_fixable_items_would_still_leave_questions() -> None:
    rules = {
        "all": [condition("has_ration_card", "is_true"), condition("age", "gte", 18)],
        "fixable": ["has_ration_card"],
    }

    assert check(rules, person(has_ration_card=False)).status == "unknown"


def test_eligible_family_with_fixable_list_is_just_eligible() -> None:
    rules = {"all": [condition("has_ration_card", "is_true")], "fixable": ["has_ration_card"]}

    assert check(rules, person(has_ration_card=True)).status == "eligible"


# ---------------------------------------------------------------- results


def test_result_lists_passed_failed_and_unknown_rules() -> None:
    rules = {
        "all": [
            condition("age", "gte", 18),
            condition("is_student", "is_true"),
            condition("state", "eq", "UP"),
        ]
    }

    result = check(rules, person(age=30, is_student=False))

    assert [r.fields for r in result.passed] == [("age",)]
    assert [r.fields for r in result.failed] == [("is_student",)]
    assert [r.fields for r in result.unknown] == [("state",)]
    assert result.failed[0].rule == condition("is_student", "is_true")


# ---------------------------------------------------------------- malformed rules


@pytest.mark.parametrize(
    ("rules", "message"),
    [
        ({}, "top-level 'all'"),
        ({"all": [condition("agee", "gte", 1)]}, "unknown field"),
        ({"all": [{"field": "age", "op": "above", "value": 1}]}, "unknown operator"),
        ({"all": [{"field": "age", "op": "gte"}]}, "needs a value"),
        ({"all": [{"field": "age", "op": "gte", "value": "18"}]}, "needs a number"),
        ({"all": [{"field": "age", "op": "between", "value": [9, 1]}]}, "low is greater"),
        ({"all": [{"field": "age", "op": "between", "value": [1]}]}, "[low, high]"),
        ({"all": [{"field": "category", "op": "in", "value": []}]}, "non-empty list"),
        ({"all": [{"field": "is_student", "op": "is_true", "value": True}]}, "takes no value"),
        ({"all": [{"all": []}]}, "non-empty list"),
        ({"all": [{"field": "age", "all": []}]}, "exactly one"),
        ({"all": [{"nope": 1}]}, "exactly one"),
        ({"all": [condition("govt_employee", "eq", "grup_d")]}, "not a valid answer"),
        ({"all": [condition("pension_band", "in", ["none", "huge"])]}, "not a valid answer"),
        ({"all": [YES], "fixable": ["agee"]}, "unknown field"),
        ({"all": [YES], "extra": 1}, "unexpected top-level"),
    ],
)
def test_malformed_rules_raise_a_clear_error(rules: dict[str, Any], message: str) -> None:
    with pytest.raises(RuleError, match=message.replace("[", r"\[").replace("]", r"\]")):
        check(rules, ME)


def test_malformed_rule_is_reported_even_if_no_member_would_reach_it() -> None:
    bad = {"all": [{"any_member": condition("agee", "gte", 1)}]}

    with pytest.raises(RuleError):
        check(bad, person(), members=[])
