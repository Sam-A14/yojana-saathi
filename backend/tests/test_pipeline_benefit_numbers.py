"""Every number in benefit_text_en must be written in the benefit quote.

Why: the quote is the proof of the text. In review item 10 the quote was a sentence with no figures
and the rates in the text were right only because a person compared them with the table; in item 4
the text said "from 80 years" but the quote had no 80. Nothing flagged either.
"""

import copy
import json
from typing import Any

import pytest

from app.db.seed import DEFAULT_DATA_DIR, _validator, read_seed_files
from app.pipeline.allowed_fields import allowed_fields
from app.pipeline.source import read_source
from app.pipeline.validator import ValidationResult, numbers_in, validate_output
from tests.pipeline_samples import SLUG, SOURCE_TEXT, SOURCE_URL, answer_with_benefit

ALLOWED = allowed_fields(DEFAULT_DATA_DIR)
SCHEMA_VALIDATOR = _validator(DEFAULT_DATA_DIR / "scheme.schema.json")

# A page with a table like the OBC post-matric one: tab-separated columns, amounts as "1,200/-".
TABLE_SOURCE = SOURCE_TEXT + (
    "Group\tCourse\tHostel Rates (Rs/month)\tDay scholar Rates (Rs/month)\n"
    "1\tGroup -1\tDegree and Master Degree Courses etc.\t1,200/-\t550/-\n"
    "2\tGroup -2\tDiploma courses\t820/-\t530/-\n"
    "4\tGroup -4\tAll non-degree level courses\t380/-\t230/-\n"
)
GROUP_1_ROW = "1 Group -1 Degree and Master Degree Courses etc. 1,200/- 550/-"
GROUP_4_ROW = "4 Group -4 All non-degree level courses 380/- 230/-"


def check(text: str, quote: str | None, source: str = TABLE_SOURCE) -> ValidationResult:
    answer: dict[str, Any] = copy.deepcopy(answer_with_benefit())
    answer["scheme"]["version"]["benefit_text_en"] = text
    answer["benefit_quote"] = quote
    return validate_output(
        json.dumps(answer),
        slug=SLUG,
        source_url=SOURCE_URL,
        source_text=source,
        allowed=ALLOWED,
        schema_validator=SCHEMA_VALIDATOR,
    )


def codes(result: ValidationResult) -> list[str]:
    return [p.code for p in result.problems]


# --- reading numbers ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("₹3,500/- per annum", {"3500"}),
        ("Rs. 2,50,000/-", {"250000"}),  # Indian grouping
        ("Rs.10,000 or more", {"10000"}),
        ("₹2.5 lakh a year.", {"2.5"}),
        ("₹1,200, then ₹550.", {"1200", "550"}),  # a comma after a figure belongs to the sentence
        ("1,200/- 550/-", {"1200", "550"}),
        ("up to 79 years and from 80 years", {"79", "80"}),
        ("Group 1 courses", {"1"}),
        ("a monthly pension, with no figure", set()),
    ],
)
def test_numbers_are_read_the_same_whatever_their_commas_and_signs(
    text: str, expected: set[str]
) -> None:
    assert numbers_in(text) == expected


# --- the check ---------------------------------------------------------------------------------


def test_a_text_whose_every_number_is_in_the_quote_passes() -> None:
    result = check(
        "Group 1 courses get Rs.1,200 a month in a hostel or ₹550 for day scholars.", GROUP_1_ROW
    )
    assert result.problems == []


def test_a_number_the_quote_does_not_contain_is_flagged_and_named() -> None:
    result = check("Group 1 courses get ₹1,200 a month, and group 2 courses get ₹820.", GROUP_1_ROW)

    assert codes(result) == ["benefit_number_not_in_quote"]
    problem = result.problems[0]
    assert problem.where == "scheme.version.benefit_text_en"
    assert "820" in problem.message and "2" in problem.message
    assert "1200" not in problem.message  # only the missing ones are listed


def test_a_quote_with_no_figures_cannot_support_a_text_with_figures() -> None:
    """Review item 10: a real sentence from the page, but nothing in it shows a rate."""
    quote = "The pension is paid every month"
    source = TABLE_SOURCE + quote + ".\n"
    result = check("The family gets ₹500 a month.", quote, source)
    assert codes(result) == ["benefit_number_not_in_quote"]


def test_two_table_rows_that_are_not_next_to_each_other_cannot_be_one_quote() -> None:
    """The quote must be one stretch of the page. Rows 1 and 4 are separate, so a text about both
    needs a quote that includes everything between them (or a text that mentions only one)."""
    both = f"{GROUP_1_ROW} {GROUP_4_ROW}"
    result = check("Rates run from ₹1,200 down to ₹230 a month.", both)
    assert codes(result) == ["benefit_quote_not_in_source"]  # not on the page as one piece


def test_a_quote_that_spans_the_rows_between_passes() -> None:
    middle = "2 Group -2 Diploma courses 820/- 530/-"
    quote = f"{GROUP_1_ROW} {middle} {GROUP_4_ROW}"
    assert check("Rates run from ₹1,200 down to ₹230 a month.", quote).problems == []


def test_a_text_with_no_numbers_needs_nothing_from_the_quote() -> None:
    assert check("The family gets a monthly pension.", GROUP_1_ROW).problems == []


def test_an_unreal_quote_is_one_problem_not_two() -> None:
    result = check("The family gets ₹99 a month.", "a line that is not on the page at all")
    assert codes(result) == ["benefit_quote_not_in_source"]


def test_a_missing_quote_is_one_problem_not_two() -> None:
    result = check("The family gets ₹99 a month.", None)
    assert codes(result) == ["benefit_unquoted"]


def test_the_check_is_in_the_words_the_model_is_told() -> None:
    from app.llm.prompts import SYSTEM_PROMPT

    flat = " ".join(SYSTEM_PROMPT.split())
    assert "Every number in benefit_text_en" in flat and "must be written in benefit_quote" in flat


# --- the real seed files -----------------------------------------------------------------------


def test_every_noted_benefit_quote_in_the_seed_files_shows_every_number_of_its_text() -> None:
    """Schemes whose labeller_notes record 'Source quote (benefit_text_en): ...' (ignoaps and the
    two UP scholarships) must show every figure of benefit_text_en in those quotes together."""
    prefix = "Source quote (benefit_text_en): "
    checked = 0
    for scheme in read_seed_files().schemes:
        notes = scheme.get("labeller_notes", {}).get("notes", [])
        quotes = [n.removeprefix(prefix) for n in notes if n.startswith(prefix)]
        text = scheme["version"].get("benefit_text_en")
        if not quotes or text is None:
            continue
        shown = set().union(*(numbers_in(q) for q in quotes))
        assert numbers_in(text) <= shown, (scheme["slug"], numbers_in(text) - shown)
        assert read_source(scheme["slug"]).text  # the quotes are checked against it elsewhere
        checked += 1
    assert checked >= 3
