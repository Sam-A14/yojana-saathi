"""The rules engine: decides eligibility from a scheme's rules and a family's facts.

Pure functions only: no database, no network, no clock, no LLM. The same inputs always give the
same answer, which is why the answer can be tested and trusted (CLAUDE.md rule 1).

How to read this file, top to bottom:
  1. Result types (what evaluate() returns).
  2. validate_rules(): rejects a malformed rule before anything is decided.
  3. Condition operators (eq, gte, ...): one small function per operator.
  4. Combinators (all / any / not / any_member): how true / false / unknown combine.
  5. evaluate(): the only public entry point; builds the status from the pieces.

Three-valued logic. Every rule node is True, False or None, where None means "unknown": a fact the
rule needs has not been given. We never guess: a missing fact is not "no", it is "ask the family".
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from app.rules.fields import ALLOWED_VALUES, is_household_field, is_known_field

Truth = bool | None  # True = passes, False = fails, None = unknown
Status = Literal["eligible", "near_miss", "not_eligible", "unknown"]
Outcome = Literal["passed", "failed", "unknown"]

OPERATORS = ("eq", "neq", "in", "not_in", "gte", "lte", "between", "is_true")
COMBINATORS = ("all", "any", "not", "any_member")


class RuleError(Exception):
    """The rule itself is malformed (typo in a field, bad operator, wrong value type).

    Deliberately different from "unknown": unknown means the FAMILY's data is incomplete, this
    means OUR rule is broken and a human must fix it. Never turned into an eligibility answer.
    """


@dataclass(frozen=True)
class HouseholdFacts:
    """What the engine knows about the household.

    attributes: household-level facts, e.g. {"state": "UP", "area_type": "rural"}.
    members: one mapping per person, INCLUDING the person being evaluated. Each holds that
        person's facts (age, owns_cultivable_land, has_land_record, ...) and a "nickname" used
        when the result has to say who triggered a rule. A fact that is absent or None is unknown.
    """

    attributes: Mapping[str, Any]
    members: Sequence[Mapping[str, Any]]


@dataclass(frozen=True)
class RuleResult:
    """The verdict on one top-level rule, shaped for the "ticked-off reasons" list on screen."""

    rule: Mapping[str, Any]  # the rule exactly as written in the scheme
    outcome: Outcome
    fields: tuple[str, ...]  # every fact the rule looked at
    # Nicknames of members whose facts satisfied an "any_member" part of this rule. For an
    # exclusion such as not(any_member(paid tax)), a failed rule lists who caused the exclusion.
    matched_members: tuple[str, ...]
    # True when the rule failed but would pass if the family fixed its "fixable" items.
    fixable: bool


@dataclass(frozen=True)
class Evaluation:
    status: Status
    rule_results: tuple[RuleResult, ...]

    @property
    def passed(self) -> tuple[RuleResult, ...]:
        return tuple(r for r in self.rule_results if r.outcome == "passed")

    @property
    def failed(self) -> tuple[RuleResult, ...]:
        return tuple(r for r in self.rule_results if r.outcome == "failed")

    @property
    def unknown(self) -> tuple[RuleResult, ...]:
        return tuple(r for r in self.rule_results if r.outcome == "unknown")


# ---------------------------------------------------------------------------------------------
# 2. Validation
# ---------------------------------------------------------------------------------------------


def validate_rules(rules: Mapping[str, Any]) -> None:
    """Raise RuleError if the rules are malformed. Runs before every evaluation.

    Why up front: the evaluator never short-circuits, but an any_member over an empty household
    would never look inside its rule. Checking the whole tree first means a broken rule fails the
    same way for every family, not only for some.
    """
    if "all" not in rules:
        raise RuleError("rules must have a top-level 'all' list")
    unexpected = set(rules) - {"all", "fixable"}
    if unexpected:
        raise RuleError(f"unexpected top-level keys: {sorted(unexpected)}")
    _validate_node({"all": rules["all"]})
    for name in rules.get("fixable", []):
        if not isinstance(name, str) or not is_known_field(name):
            raise RuleError(f"fixable lists an unknown field: {name!r}")


def _validate_node(node: Any) -> None:
    if not isinstance(node, Mapping):
        raise RuleError(f"a rule must be an object, got {node!r}")
    kinds = [k for k in ("field", *COMBINATORS) if k in node]
    if len(kinds) != 1:
        raise RuleError(f"a rule must have exactly one of field/all/any/not/any_member: {node!r}")
    kind = kinds[0]
    if kind == "field":
        _validate_condition(node)
    elif kind in ("all", "any"):
        _check_keys(node, {kind})
        children = node[kind]
        if not isinstance(children, list) or not children:
            raise RuleError(f"'{kind}' needs a non-empty list of rules")
        for child in children:
            _validate_node(child)
    elif kind == "not":
        _check_keys(node, {"not"})
        _validate_node(node["not"])
    else:  # any_member
        # "among" is reserved for later ("applicant_family"); only "household" exists today.
        _check_keys(node, {"any_member", "among"})
        if node.get("among", "household") != "household":
            raise RuleError(f"among={node['among']!r} is not supported yet; use 'household'")
        _validate_node(node["any_member"])


def _check_keys(node: Mapping[str, Any], allowed: set[str]) -> None:
    extra = set(node) - allowed
    if extra:
        raise RuleError(f"unexpected keys {sorted(extra)} in {dict(node)!r}")


def _validate_condition(node: Mapping[str, Any]) -> None:
    field, op = node["field"], node.get("op")
    if not isinstance(field, str) or not is_known_field(field):
        raise RuleError(f"unknown field {field!r}")
    if op not in OPERATORS:
        raise RuleError(f"unknown operator {op!r} for field {field!r}")
    _check_keys(node, {"field", "op", "value"})
    if op == "is_true":
        if "value" in node:
            raise RuleError(f"is_true on {field!r} takes no value")
        return
    if "value" not in node:
        raise RuleError(f"operator {op!r} on {field!r} needs a value")
    value = node["value"]
    if op in ("eq", "neq"):
        _check_scalar(field, value)
        values = [value]
    elif op in ("in", "not_in"):
        if not isinstance(value, list) or not value:
            raise RuleError(f"{op} on {field!r} needs a non-empty list")
        for item in value:
            _check_scalar(field, item)
        values = value
    elif op == "between":
        if not (isinstance(value, list) and len(value) == 2 and all(map(_is_number, value))):
            raise RuleError(f"between on {field!r} needs [low, high] numbers")
        if value[0] > value[1]:
            raise RuleError(f"between on {field!r}: low is greater than high")
        return
    else:  # gte, lte
        if not _is_number(value):
            raise RuleError(f"{op} on {field!r} needs a number, got {value!r}")
        return
    allowed = ALLOWED_VALUES.get(field)
    if allowed is not None:
        for item in values:
            if item not in allowed:
                raise RuleError(f"{item!r} is not a valid answer for {field!r}: use {allowed}")


def _check_scalar(field: str, value: Any) -> None:
    if not isinstance(value, str | int | float | bool):
        raise RuleError(f"value for {field!r} must be text, number or true/false, got {value!r}")


def _is_number(value: Any) -> bool:
    # bool is a subclass of int in Python; True is not an age or an income.
    return isinstance(value, int | float) and not isinstance(value, bool)


# ---------------------------------------------------------------------------------------------
# 3. Condition operators
# ---------------------------------------------------------------------------------------------


def _same(a: Any, b: Any) -> bool:
    """Equality that refuses to treat True as 1 (plain == would: True == 1 in Python)."""
    return isinstance(a, bool) == isinstance(b, bool) and a == b


def _need_number(field: str, actual: Any) -> float:
    if not _is_number(actual):
        raise RuleError(f"fact {field!r} should be a number but is {actual!r}")
    return actual  # type: ignore[no-any-return]


def _apply_operator(node: Mapping[str, Any], actual: Any) -> Truth:
    """Compare one fact with the rule's value. A missing fact is unknown for EVERY operator."""
    if actual is None:
        return None
    op, field, value = node["op"], node["field"], node.get("value")
    if op == "eq":
        return _same(actual, value)
    if op == "neq":
        return not _same(actual, value)
    if op == "in":
        return any(_same(actual, v) for v in value)
    if op == "not_in":
        return not any(_same(actual, v) for v in value)
    if op == "gte":
        return _need_number(field, actual) >= value
    if op == "lte":
        return _need_number(field, actual) <= value
    if op == "between":
        return value[0] <= _need_number(field, actual) <= value[1]
    # is_true. A text answer here means the data is wrong, so say so loudly.
    if not isinstance(actual, bool):
        raise RuleError(f"fact {field!r} should be true/false but is {actual!r}")
    return actual


# ---------------------------------------------------------------------------------------------
# 4. Combinators
# ---------------------------------------------------------------------------------------------


def _all(truths: Sequence[Truth]) -> Truth:
    """One definite 'no' beats any 'unknown': a family that clearly fails is not asked more."""
    if any(t is False for t in truths):
        return False
    if any(t is None for t in truths):
        return None
    return True


def _any(truths: Sequence[Truth]) -> Truth:
    """One definite 'yes' beats any 'unknown'."""
    if any(t is True for t in truths):
        return True
    if any(t is None for t in truths):
        return None
    return False


def _not(truth: Truth) -> Truth:
    return None if truth is None else not truth


@dataclass
class _Run:
    """Everything one pass over the rules needs. Private: callers only see evaluate().

    relax: fields whose conditions are pretended fixed (empty on the normal pass). Used only to
        ask "would this family be eligible if it fixed its fixable items?".
    matched: collector for nicknames of members that satisfied an any_member rule. A list passed
        down is the simplest way to get this "evidence" out without changing every return type.
    """

    household: HouseholdFacts
    relax: frozenset[str]
    matched: list[str]


def _eval(node: Mapping[str, Any], person: Mapping[str, Any], run: _Run, helps: bool) -> Truth:
    """Evaluate one rule node for one person.

    person: whose personal facts a plain condition reads (the applicant, or the member that an
        any_member is currently looking at).
    helps: True when this node is NOT inside an odd number of 'not's. It only matters when
        relaxing: a fixed condition is forced to the value that HELPS eligibility, which is True
        normally but False under a 'not'. Example: not(has_x) with has_x fixable becomes eligible
        once has_x is fixed to false, so forcing it to True would be backwards.
    """
    if "field" in node:
        field = node["field"]
        if field in run.relax:
            return helps
        return _apply_operator(node, _read_fact(field, person, run.household))
    if "all" in node:
        return _all([_eval(child, person, run, helps) for child in node["all"]])
    if "any" in node:
        return _any([_eval(child, person, run, helps) for child in node["any"]])
    if "not" in node:
        return _not(_eval(node["not"], person, run, not helps))
    return _eval_any_member(node["any_member"], run, helps)


def _read_fact(field: str, person: Mapping[str, Any], household: HouseholdFacts) -> Any:
    """Household facts come from the household, everything else from the person. None if absent."""
    source = household.attributes if is_household_field(field) else person
    return source.get(field)


def _eval_any_member(inner: Mapping[str, Any], run: _Run, helps: bool) -> Truth:
    """True if the inner rule holds for at least one member of the household.

    The inner rule is evaluated for ONE member at a time, so "paid tax AND is a professional"
    means one person with both, not two people with one each. The result is combined with the
    same any-logic as above, so an unanswered member can make the answer unknown but never hide a
    definite match found in another member.
    """
    truths = [_eval(inner, member, run, helps) for member in run.household.members]
    for index, (member, truth) in enumerate(zip(run.household.members, truths, strict=True)):
        if truth is True:
            name = member.get("nickname") or f"member {index + 1}"
            if name not in run.matched:
                run.matched.append(name)
    return _any(truths)


def _fields_in(node: Mapping[str, Any]) -> tuple[str, ...]:
    """Every fact name a rule looks at, in order, without repeats (for the explanation)."""
    if "field" in node:
        return (node["field"],)
    if "all" in node:
        children: list[Mapping[str, Any]] = node["all"]
    elif "any" in node:
        children = node["any"]
    elif "not" in node:
        children = [node["not"]]
    else:
        children = [node["any_member"]]
    return tuple(dict.fromkeys(name for child in children for name in _fields_in(child)))


# ---------------------------------------------------------------------------------------------
# 5. The entry point
# ---------------------------------------------------------------------------------------------


def evaluate(
    member: Mapping[str, Any], household: HouseholdFacts, rules: Mapping[str, Any]
) -> Evaluation:
    """Decide whether `member` qualifies for a scheme, and say which rules passed and failed.

    Status:
      eligible      every rule passes.
      not_eligible  at least one rule definitely fails and fixing the "fixable" items would not
                    save it.
      near_miss     at least one rule definitely fails, but the family WOULD be eligible if it
                    fixed the items listed in rules["fixable"] (for example by getting a document).
      unknown       a fact needed for the answer is missing. We never turn missing data into 'no'.

    Order of checks matters: a definite failure outranks missing data, because asking more
    questions cannot rescue a family that already fails a rule it cannot fix.
    """
    validate_rules(rules)
    fixable = frozenset(rules.get("fixable", []))
    top_rules = rules["all"]

    results = []
    truths: list[Truth] = []
    for rule in top_rules:
        matched: list[str] = []
        truth = _eval(rule, member, _Run(household, frozenset(), matched), helps=True)
        truths.append(truth)
        results.append(_rule_result(rule, truth, matched, member, household, fixable))

    overall = _all(truths)
    return Evaluation(_status(overall, member, household, top_rules, fixable), tuple(results))


def _rule_result(
    rule: Mapping[str, Any],
    truth: Truth,
    matched: list[str],
    member: Mapping[str, Any],
    household: HouseholdFacts,
    fixable: frozenset[str],
) -> RuleResult:
    outcome: Outcome = {True: "passed", False: "failed", None: "unknown"}[truth]
    can_fix = False
    if truth is False and fixable:
        relaxed = _eval(rule, member, _Run(household, fixable, []), helps=True)
        can_fix = relaxed is True
    return RuleResult(rule, outcome, _fields_in(rule), tuple(matched), can_fix)


def _status(
    overall: Truth,
    member: Mapping[str, Any],
    household: HouseholdFacts,
    top_rules: Sequence[Mapping[str, Any]],
    fixable: frozenset[str],
) -> Status:
    if overall is True:
        return "eligible"
    if overall is None:
        return "unknown"
    # overall is False. Is it a near miss? Pretend every fixable item is fixed and look again.
    if fixable:
        run = _Run(household, fixable, [])
        relaxed = _all([_eval(rule, member, run, helps=True) for rule in top_rules])
        if relaxed is True:
            return "near_miss"
        if relaxed is None:
            # Fixing the fixable items would still leave open questions: ask before deciding.
            return "unknown"
    return "not_eligible"
