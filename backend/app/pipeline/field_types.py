"""What kind of value each rule field holds, so a proposal that says the wrong kind can be refused.

The rules engine compares exactly (`_same`): the text "yes" is not true, and a category nobody can
have matches nobody. So `is_bpl eq "yes"` is a valid rule that nobody can ever satisfy. The engine
cannot know that; this table can. It is used by the extraction validator, and by the accuracy
normaliser (which only rewrites fields whose values it knows).

Four kinds:
  boolean  yes/no facts, and every has_<document> field   true / false / is_true
  closed   a fixed list of answers (the API and the database refuse anything else)
  number   age and the income limit
  text     state and district
"""

from collections.abc import Mapping
from typing import Any

from app.db.models.family import AREA_TYPES, GENDERS
from app.rules.fields import ALLOWED_VALUES, DOCUMENT_FIELD_PREFIX
from app.rules.values import (
    CATEGORY_VALUES,
    EDUCATION_VALUES,
    MARITAL_STATUS_VALUES,
    OCCUPATION_VALUES,
)

# Fields whose answer is always one of a fixed list. For these, "not group_d" and "none or other"
# are the same condition (the accuracy normaliser relies on that too).
CLOSED_VALUES: dict[str, tuple[str, ...]] = {
    "gender": GENDERS,
    "area_type": AREA_TYPES,
    "marital_status": MARITAL_STATUS_VALUES,
    "category": CATEGORY_VALUES,
    "education": EDUCATION_VALUES,
    "occupation": OCCUPATION_VALUES,
    **ALLOWED_VALUES,  # govt_employee, pension_band
}

# Yes/no facts. A test checks this list against the yes/no columns of the Member and Household
# tables, so a new yes/no column cannot be forgotten here.
BOOLEAN_FIELDS = frozenset(
    {
        "is_bpl",
        "is_student",
        "disability",
        "owns_cultivable_land",
        "paid_income_tax_last_year",
        "is_registered_professional",
        "holds_constitutional_post",
        "is_remarried",
    }
)

NUMBER_FIELDS = frozenset({"age", "income_band_max"})
TEXT_FIELDS = frozenset({"state", "district"})


def is_boolean_field(name: str) -> bool:
    return name in BOOLEAN_FIELDS or name.startswith(DOCUMENT_FIELD_PREFIX)


def kind_of(field: str) -> str | None:
    """'boolean', 'closed', 'number' or 'text'; None for a field we have no type for."""
    if is_boolean_field(field):
        return "boolean"
    if field in CLOSED_VALUES:
        return "closed"
    if field in NUMBER_FIELDS:
        return "number"
    if field in TEXT_FIELDS:
        return "text"
    return None


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)  # True is not 1


def _shown(value: Any) -> str:
    """A value as the person reading the problem would write it: "yes" in quotes, true bare."""
    if isinstance(value, str):
        return f'"{value}"'
    return str(value).lower() if isinstance(value, bool) else str(value)


def value_problem(condition: Mapping[str, Any]) -> str | None:
    """Why this condition's operator or value does not fit its field, or None if it does.

    A condition with no value for an operator that needs one is not judged here: the schema and
    the engine already refuse it, and saying so twice only adds noise.
    """
    field, op = condition.get("field"), condition.get("op")
    kind = kind_of(field) if isinstance(field, str) else None
    if kind is None or op == "is_true" and kind == "boolean":
        return None
    if op == "is_true":
        return f"{field} is not a yes/no field, so is_true cannot be used on it."
    if "value" not in condition:
        return None
    value = condition["value"]
    as_list = value if isinstance(value, list) else None

    if kind == "boolean":
        if op in ("eq", "neq") and isinstance(value, bool):
            return None
        if op in ("eq", "neq"):
            return (
                f"{field} is a yes/no field: use is_true, or {op} with true or false "
                f'(got {_shown(value)}). The text "yes" is not true and would match nobody.'
            )
        return f"{field} is a yes/no field: {op} cannot be used on it; use is_true."

    if kind == "closed":
        allowed = CLOSED_VALUES[field]
        if op in ("eq", "neq"):
            if value in allowed and isinstance(value, str):
                return None
            return f"{field} takes one of: {', '.join(allowed)} (got {_shown(value)})."
        if op in ("in", "not_in"):
            bad = [v for v in as_list or [] if v not in allowed or not isinstance(v, str)]
            if as_list and not bad:
                return None
            shown = ", ".join(_shown(v) for v in bad) if bad else _shown(value)
            return f"{field} takes values from: {', '.join(allowed)} (got {shown})."
        return f"{field} has a fixed list of answers: {op} cannot be used on it."

    if kind == "number":
        if op in ("gte", "lte", "eq", "neq") and _is_number(value):
            return None
        if op == "between" and as_list and len(as_list) == 2 and all(map(_is_number, as_list)):
            return None
        if op in ("in", "not_in") and as_list and all(map(_is_number, as_list)):
            return None
        return f"{field} is a number: {op} needs a number value (got {_shown(value)})."

    # text
    if op in ("eq", "neq") and isinstance(value, str):
        return None
    if op in ("in", "not_in") and as_list and all(isinstance(v, str) for v in as_list):
        return None
    return f"{field} is text: {op} needs text (got {_shown(value)})."
