"""Evaluate a scheme's rules when some facts are only known as a range.

Why this exists: a family tells us a birth YEAR and an income BAND, not an exact age or income.
A person born in 1966 is 59 or 60 in 2026; a household in "1 to 2 lakh" earns somewhere between
the two edges. If a rule's answer changes inside that range, saying "eligible" or "not eligible"
would be a guess. So we run the unchanged rules engine at the corners of each range (youngest and
oldest age, lowest and highest income). If every corner agrees, the answer does not depend on the
missing detail and we use it. If they disagree, the answer is "unknown" and we say which detail it
depends on. The engine itself is never changed and still makes every decision (CLAUDE.md rule 1).

This file is pure: no database, no clock. `today` is turned into ranges by the caller (facts.py).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import product
from typing import Any, Literal

from app.rules.engine import HouseholdFacts, Outcome, Status, evaluate, validate_rules

ReasonCode = Literal["depends_on_exact_age", "depends_on_exact_income"]
AGE_REASON: ReasonCode = "depends_on_exact_age"
INCOME_REASON: ReasonCode = "depends_on_exact_income"

# Every uncertain age doubles the number of corners (2 ages = 4, 6 ages = 64). This only matters
# when a rule reads other members' ages (inside any_member). Above the cap we stop enumerating and
# let the engine treat those ages as unanswered, which gives "unknown" instead of a wrong answer.
MAX_UNCERTAIN_AGES = 6


@dataclass(frozen=True)
class Ranges:
    """What is only known as a range.

    ages: member index -> (youngest possible age, oldest possible age).
    income: (lowest, highest) yearly household income; highest may be math.inf for the top band.
    A member with no birth year, or a household with no income band, simply has no entry: that
    fact is then missing and the engine says "unknown" by itself, with no reason code.
    """

    ages: Mapping[int, tuple[int, int]]
    income: tuple[float, float] | None


@dataclass(frozen=True)
class RangedRule:
    """One top-level rule's verdict across all corners (same shape as the engine's RuleResult)."""

    rule: Mapping[str, Any]
    outcome: Outcome
    fields: tuple[str, ...]
    matched_members: tuple[str, ...]
    fixable: bool
    # Why the outcome is "unknown", when it is because the corners disagreed.
    reasons: tuple[ReasonCode, ...]


@dataclass(frozen=True)
class RangedEvaluation:
    status: Status
    reasons: tuple[ReasonCode, ...]
    rule_results: tuple[RangedRule, ...]

    def with_outcome(self, outcome: Outcome) -> tuple[RangedRule, ...]:
        return tuple(r for r in self.rule_results if r.outcome == outcome)


@dataclass(frozen=True)
class _Dimension:
    kind: Literal["age", "income"]
    member_index: int | None
    values: tuple[float, ...]  # one value, or the two corners

    @property
    def reason(self) -> ReasonCode:
        return AGE_REASON if self.kind == "age" else INCOME_REASON


# --- which uncertain facts do these rules actually read? ------------------------------------


def _facts_read(node: Mapping[str, Any], inside_any_member: bool = False) -> set[str]:
    """Tags: 'age_self' (age of the applicant), 'age_any' (age inside any_member), 'income'."""
    if "field" in node:
        if node["field"] == "age":
            return {"age_any" if inside_any_member else "age_self"}
        return {"income"} if node["field"] == "income_band_max" else set()
    if "any_member" in node:
        return _facts_read(node["any_member"], inside_any_member=True)
    children = node.get("all") or node.get("any") or [node["not"]]
    return set().union(*(_facts_read(child, inside_any_member) for child in children))


def _dimensions(tags: set[str], applicant: int, ranges: Ranges) -> tuple[list[_Dimension], bool]:
    """The ranges that matter for these rules, and whether there are too many ages to enumerate."""
    if "age_any" in tags:
        members = sorted(ranges.ages)
    elif "age_self" in tags and applicant in ranges.ages:
        members = [applicant]
    else:
        members = []
    too_many = len(members) > MAX_UNCERTAIN_AGES
    dims = [] if too_many else [_age_dimension(i, ranges.ages[i]) for i in members]
    if "income" in tags and ranges.income is not None:
        low, high = ranges.income
        dims.append(_Dimension("income", None, (low,) if low == high else (low, high)))
    return dims, too_many


def _age_dimension(index: int, age_range: tuple[int, int]) -> _Dimension:
    low, high = age_range
    return _Dimension("age", index, (low,) if low == high else (low, high))


# --- the entry point ------------------------------------------------------------------------


def evaluate_with_ranges(
    applicant: int,
    members: Sequence[Mapping[str, Any]],
    household: Mapping[str, Any],
    rules: Mapping[str, Any],
    ranges: Ranges,
) -> RangedEvaluation:
    """Run the engine for members[applicant] at every corner and combine the answers.

    members: one mapping of facts per person, WITHOUT "age" and including the applicant.
    household: household facts, WITHOUT "income_band_max".
    Raises RuleError (from the engine) if the rules are malformed.
    """
    validate_rules(rules)
    tags = _facts_read({"all": rules["all"]})
    dims, too_many_ages = _dimensions(tags, applicant, ranges)

    runs: dict[tuple[int, ...], Any] = {}
    for key in product(*(range(len(d.values)) for d in dims)):
        people = [dict(m) for m in members]
        attributes = dict(household)
        for dim, choice in zip(dims, key, strict=True):
            if dim.kind == "age":
                assert dim.member_index is not None
                people[dim.member_index]["age"] = dim.values[choice]
            else:
                attributes["income_band_max"] = dim.values[choice]
        runs[key] = evaluate(people[applicant], HouseholdFacts(attributes, people), rules)

    evaluation = _combine(runs, dims)
    if too_many_ages and evaluation.status == "unknown":
        return RangedEvaluation("unknown", (AGE_REASON,), evaluation.rule_results)
    return evaluation


# --- combining the corners ------------------------------------------------------------------


def _disagreement_reasons(
    outcomes: Mapping[tuple[int, ...], str], dims: Sequence[_Dimension]
) -> tuple[ReasonCode, ...]:
    """Which ranges made the corners differ?

    A range matters if moving ONLY that one between its two corners can change the answer. If the
    answers are not all equal, some such single move changes it (the corners form a grid), so the
    result is never empty when there is a disagreement.
    """
    found: list[ReasonCode] = []
    for position, dim in enumerate(dims):
        if len(dim.values) < 2 or dim.reason in found:
            continue
        for key, outcome in outcomes.items():
            if key[position] == 0:
                moved = key[:position] + (1,) + key[position + 1 :]
                if outcomes[moved] != outcome:
                    found.append(dim.reason)
                    break
    return tuple(r for r in (AGE_REASON, INCOME_REASON) if r in found)


def _combine(runs: Mapping[tuple[int, ...], Any], dims: Sequence[_Dimension]) -> RangedEvaluation:
    statuses = {key: run.status for key, run in runs.items()}
    if len(set(statuses.values())) == 1:
        status: Status = next(iter(statuses.values()))
        status_reasons: tuple[ReasonCode, ...] = ()
    else:
        status, status_reasons = "unknown", _disagreement_reasons(statuses, dims)

    first = next(iter(runs.values()))
    rules: list[RangedRule] = []
    for index, template in enumerate(first.rule_results):
        per_corner = [run.rule_results[index] for run in runs.values()]
        outcomes = {key: run.rule_results[index].outcome for key, run in runs.items()}
        if len(set(outcomes.values())) == 1:
            outcome: Outcome = template.outcome
            reasons: tuple[ReasonCode, ...] = ()
        else:
            outcome, reasons = "unknown", _disagreement_reasons(outcomes, dims)
        matched = tuple(dict.fromkeys(name for r in per_corner for name in r.matched_members))
        rules.append(
            RangedRule(
                rule=template.rule,
                outcome=outcome,
                fields=template.fields,
                matched_members=matched,
                fixable=all(r.fixable for r in per_corner),
                reasons=reasons,
            )
        )
    return RangedEvaluation(status, status_reasons, tuple(rules))
