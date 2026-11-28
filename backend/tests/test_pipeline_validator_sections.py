"""A rule's quote must come from Details or Eligibility, never a paper list or how-to-apply text.

Why: the quote is the proof that the source states the condition. Words under Documents Required
("Aadhar card number", "Income certificate of your family") only say what to bring, and the model
once turned them into eligibility rules (review item 4).
"""

import copy
import json
from typing import Any

import pytest

from app.db.seed import DEFAULT_DATA_DIR, _validator
from app.pipeline.allowed_fields import allowed_fields
from app.pipeline.sections import rule_quote_text, sections_containing
from app.pipeline.source import read_source
from app.pipeline.validator import ValidationResult, validate_output
from tests.pipeline_samples import BENEFIT_QUOTE, SLUG, SOURCE_URL, answer_with_benefit, good_answer

ALLOWED = allowed_fields(DEFAULT_DATA_DIR)
SCHEMA_VALIDATOR = _validator(DEFAULT_DATA_DIR / "scheme.schema.json")

AGE = "The scheme gives a pension to every person aged 60 years or above."
CATEGORY = "Only persons belonging to SC or ST categories can apply."
TAX = "A family where any member paid income tax last year is not eligible."
QUOTES = ["aged 60 years or above", "belonging to SC or ST categories", "paid income tax last year"]


def check(text: str, answer: dict[str, Any] | None = None) -> ValidationResult:
    return validate_output(
        json.dumps(answer if answer is not None else good_answer()),
        slug=SLUG,
        source_url=SOURCE_URL,
        source_text=text,
        allowed=ALLOWED,
        schema_validator=SCHEMA_VALIDATOR,
    )


def page(details: str = "", eligibility: str = "", documents: str = "", other: str = "") -> str:
    """A myScheme-style page with the given text under each heading."""
    return (
        f"Test Scheme\n\nDetails\n{details}\n\nBenefits\nA pension.\n\n"
        f"Eligibility\n{eligibility}\n\n"
        f"Documents Required\n{documents}\n\n{other}"
    )


def codes(result: ValidationResult) -> list[str]:
    return [p.code for p in result.problems]


def test_quotes_under_details_and_eligibility_are_accepted() -> None:
    assert check(page(details=f"{AGE}\n{CATEGORY}", eligibility=TAX)).problems == []


def test_a_quote_can_run_over_a_line_break() -> None:
    wrapped = "Only persons belonging to SC or ST\ncategories can apply."
    assert check(page(details=AGE, eligibility=f"{wrapped}\n{TAX}")).problems == []


@pytest.mark.parametrize(
    "heading", ["Documents Required", "Application Process", "Benefits", "FAQ"]
)
def test_a_quote_under_any_other_heading_is_refused_and_the_heading_is_named(heading: str) -> None:
    other = f"{heading}\n{TAX}"
    text = (
        f"Test Scheme\n\nDetails\n{AGE}\n\nEligibility\n{CATEGORY}\n\n{other}\n"
        if heading != "Documents Required"
        else page(details=AGE, eligibility=CATEGORY, documents=TAX)
    )
    result = check(text)

    assert codes(result) == ["quote_wrong_section"]
    problem = result.problems[0]
    assert problem.where == "rule_quotes[2]"
    assert heading.lower() in problem.message
    assert "Details or Eligibility" in problem.message


def test_a_wrong_section_quote_is_told_once_not_twice() -> None:
    result = check(page(details=AGE, eligibility=CATEGORY, documents=TAX))
    assert "missing_quote" not in codes(result)


def test_a_quote_found_nowhere_is_still_quote_not_in_source() -> None:
    result = check(page(details=AGE, eligibility=CATEGORY))  # the tax sentence is not on the page
    assert "quote_not_in_source" in codes(result)
    assert "quote_wrong_section" not in codes(result)


def test_a_source_with_headings_but_no_details_or_eligibility_accepts_no_rule_quote() -> None:
    text = f"Documents Required\n{AGE}\n{CATEGORY}\n{TAX}\n"
    assert codes(check(text)).count("quote_wrong_section") == 3


def test_a_source_with_no_headings_at_all_is_checked_against_its_whole_text() -> None:
    """A press release or PDF has no sections to tell apart: the whole text is checked."""
    assert check(f"{AGE}\n{CATEGORY}\n{TAX}\n").problems == []


def test_the_benefit_quote_may_still_come_from_the_benefits_section() -> None:
    text = page(details=f"{AGE}\n{CATEGORY}", eligibility=TAX).replace(
        "A pension.", f"{BENEFIT_QUOTE} every month."
    )
    answer = copy.deepcopy(answer_with_benefit())
    assert check(text, answer).problems == []


def test_the_real_pre_matric_page_has_class_9_10_under_details_only() -> None:
    """The reason for the change: Class 9 or 10 is stated in Details, not Eligibility."""
    text = read_source("up-sc-st-pre-matric").text
    quote = "pursuing secondary education in Class 9 or 10"
    assert sections_containing(text, quote) == ["details"]
    assert quote in rule_quote_text(text)  # type: ignore[operator]


def test_the_real_pre_matric_documents_are_not_a_place_to_quote_rules_from() -> None:
    text = read_source("up-sc-st-pre-matric").text
    for paper in ("Income certificate of your family.", "Caste certificate."):
        assert paper not in rule_quote_text(text)  # type: ignore[operator]
        assert sections_containing(text, paper) == ["documents required"]


def test_rule_quote_text_is_none_without_headings_and_empty_with_only_other_headings() -> None:
    assert rule_quote_text("Just a sentence with no headings.") is None
    assert rule_quote_text("Documents Required\nRation Card") == ""
