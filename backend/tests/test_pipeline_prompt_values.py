"""The prompt must tell the model the exact answers the validator accepts for a closed-list field.

Why: extraction of up-obc-post-matric failed twice because the model wrote category "obc". The
validator compares exactly (so does the rules engine: "obc" would match nobody), and it stays that
way. The fix is in the prompt, which now lists every allowed value with its capitals, taken from
the same table (CLOSED_VALUES) the validator uses.
"""

import re

import pytest

from app.db.seed import DEFAULT_DATA_DIR
from app.llm.prompts import build_user_prompt
from app.pipeline.allowed_fields import allowed_documents, allowed_fields
from app.pipeline.field_types import CLOSED_VALUES, value_problem
from app.rules.values import INCOME_BANDS


@pytest.fixture(scope="module")
def prompt() -> str:
    return build_user_prompt(
        slug="test-scheme",
        source_url="https://example.org/x",
        source_text="Some scheme text.",
        fields=sorted(allowed_fields(DEFAULT_DATA_DIR)),
        documents=allowed_documents(DEFAULT_DATA_DIR),
        schema={},
    )


def field_line(prompt: str, field: str) -> str:
    (line,) = [ln for ln in prompt.splitlines() if ln.startswith(f"- {field} (")]
    return line


def listed_values(line: str) -> list[str]:
    """The quoted words after 'one of' on a field's line, as the model would read them."""
    after = line.split("one of ", 1)[1]
    return re.findall(r'"([^"]*)"', after.split(")", 1)[0].split(";", 1)[0])


def test_there_are_closed_list_fields_to_check() -> None:
    assert {"category", "gender", "marital_status", "area_type", "current_study_level"} <= set(
        CLOSED_VALUES
    )
    assert {"govt_employee", "pension_band", "education", "occupation"} <= set(CLOSED_VALUES)


@pytest.mark.parametrize("field", sorted(CLOSED_VALUES))
def test_the_prompt_lists_every_allowed_value_exactly_as_the_validator_accepts_it(
    prompt: str, field: str
) -> None:
    shown = listed_values(field_line(prompt, field))

    assert shown == list(CLOSED_VALUES[field])  # same words, same capitals, same order
    for value in shown:
        condition = {"field": field, "op": "eq", "value": value}
        assert value_problem(condition) is None, (field, value)


def test_category_is_shown_with_capitals() -> None:
    line = field_line(
        build_user_prompt(
            slug="s",
            source_url="https://example.org/x",
            source_text="t",
            fields=["category"],
            documents=[],
            schema={},
        ),
        "category",
    )
    assert line == '- category (one of "General", "SC", "ST", "OBC")'


def test_the_prompt_says_to_spell_values_exactly_and_names_the_obc_mistake(prompt: str) -> None:
    flat = " ".join(prompt.split())  # the sentence wraps over two lines
    assert 'capital letters included (category is "OBC", never "obc")' in flat


@pytest.mark.parametrize(
    ("field", "wrong"),
    [
        ("category", "obc"),
        ("category", "Obc"),
        ("category", "sc"),
        ("gender", "Female"),
        ("area_type", "Rural"),
        ("marital_status", "Widow"),
        ("current_study_level", "Class_9_10"),
        ("govt_employee", "Group_D"),
    ],
)
def test_the_validator_stays_exact_a_wrong_case_is_still_refused(field: str, wrong: str) -> None:
    """The prompt got better; the validator did not get looser. "obc" would match nobody."""
    problem = value_problem({"field": field, "op": "eq", "value": wrong})
    assert problem is not None and wrong in problem
    assert value_problem({"field": field, "op": "in", "value": [wrong]}) is not None


def test_income_edges_in_the_prompt_are_the_band_edges(prompt: str) -> None:
    line = field_line(prompt, "income_band_max")
    edges = [int(n) for n in re.search(r"band edges: ([\d, ]+);", line).group(1).split(", ")]  # type: ignore[union-attr]

    assert edges == [b.upper for b in INCOME_BANDS.values() if b.upper is not None]
    assert 200000 in edges and 250000 in edges
