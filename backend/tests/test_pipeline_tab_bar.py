"""A pasted web page starts with its tab bar: the tab names in a row, with no text between them.

Without special care the six names read as six headings, every one of them empty, and the whole
page text lands under the last one ("Frequently Asked Questions"), so no rule could be quoted from
Details or Eligibility. A run of three or more headings in a row is ignored.
"""

import json

import pytest

from app.db.seed import DEFAULT_DATA_DIR, _validator
from app.pipeline.allowed_fields import allowed_fields
from app.pipeline.sections import (
    eligibility_text,
    rule_quote_text,
    sections_containing,
    split_sections,
)
from app.pipeline.source import read_source
from app.pipeline.validator import ValidationResult, validate_output
from tests.pipeline_samples import SLUG, SOURCE_URL, good_answer

TAB_BAR = """\
Cooking Fuel
Household
Check Eligibility
Details
Benefits
Eligibility
Application Process
Documents Required
Frequently Asked Questions
"""


def test_a_tab_bar_is_not_six_headings() -> None:
    page = TAB_BAR + "Women get a free LPG connection.\n"

    assert split_sections(page) == {}  # no headings at all, so no sections


def test_the_text_after_a_tab_bar_is_not_put_under_its_last_name() -> None:
    page = TAB_BAR + "Women get a free LPG connection.\n"

    assert "frequently asked questions" not in split_sections(page)
    assert rule_quote_text(page) is None  # no sections: the whole page is the only thing to check


def test_a_page_with_a_tab_bar_and_real_sections_reads_the_real_ones() -> None:
    page = (
        TAB_BAR
        + "Details\nA scheme for women.\n\nEligibility\nThe applicant must be a woman.\n\n"
        + "Documents Required\nRation card\n"
    )

    sections = split_sections(page)

    assert sections == {
        "details": "A scheme for women.\n",
        "eligibility": "The applicant must be a woman.\n",
        "documents required": "Ration card",
    }
    assert eligibility_text(page) == "The applicant must be a woman.\n"
    assert sections_containing(page, "The applicant must be a woman.") == ["eligibility"]
    assert sections_containing(page, "Ration card") == ["documents required"]


def test_blank_lines_between_the_tab_names_do_not_break_the_bar() -> None:
    bar = "Details\n\nBenefits\n\n\nEligibility\n\nApplication Process\n"
    page = bar + "Some text.\n"

    assert split_sections(page) == {}


def test_two_headings_in_a_row_are_still_headings() -> None:
    """A real page may have an empty section: only three or more in a row is a tab bar."""
    page = "Details\nText.\n\nExclusions\nEligibility\nThe applicant is a woman.\n"

    assert split_sections(page) == {
        "details": "Text.\n",
        "exclusions": "",
        "eligibility": "The applicant is a woman.",
    }


def test_three_headings_with_text_between_them_are_headings() -> None:
    page = "Details\nOne.\nBenefits\nTwo.\nEligibility\nThree.\n"

    assert list(split_sections(page)) == ["details", "benefits", "eligibility"]


def test_a_faq_line_with_text_is_never_part_of_a_tab_bar() -> None:
    page = "Details\nBenefits\nFAQ: Who can apply?\nWomen can.\n"

    assert "faq" in split_sections(page)  # the question line is a heading with text


def test_a_tab_bar_in_the_middle_of_a_page_does_not_change_the_section_it_sits_in() -> None:
    page = "Eligibility\nA woman.\nDetails\nBenefits\nExclusions\nAn adult.\n"

    assert split_sections(page) == {"eligibility": "A woman.\nAn adult."}


@pytest.mark.parametrize("slug", ["ignoaps", "up-sc-st-pre-matric", "up-obc-post-matric"])
def test_pages_already_in_the_repository_are_read_as_before(slug: str) -> None:
    """None of them has a tab bar: their sections must not change."""
    text = read_source(slug).text
    expected = {
        "ignoaps": ["details", "benefits", "eligibility", "documents required", "faq"],
        "up-sc-st-pre-matric": ["details", "benefits", "eligibility", "documents required"],
        "up-obc-post-matric": ["details", "benefits", "eligibility", "documents required"],
    }
    assert list(split_sections(text)) == expected[slug]


# --- through the validator: what the fix is for -------------------------------------------------

ALLOWED = allowed_fields(DEFAULT_DATA_DIR)
SCHEMA_VALIDATOR = _validator(DEFAULT_DATA_DIR / "scheme.schema.json")

PAGE_SOURCE = (
    TAB_BAR
    + """\
Details
The scheme gives a pension to every person aged 60 years or above.

Eligibility
Only persons belonging to SC or ST categories can apply.
A family where any member paid income tax last year is not eligible.

Documents Required
Ration card
"""
)


def check(answer: dict, source: str) -> ValidationResult:
    return validate_output(
        json.dumps(answer),
        slug=SLUG,
        source_url=SOURCE_URL,
        source_text=source,
        allowed=ALLOWED,
        schema_validator=SCHEMA_VALIDATOR,
    )


def test_rules_can_be_quoted_from_details_and_eligibility_on_a_page_with_a_tab_bar() -> None:
    answer = good_answer()
    answer["rule_quotes"] = [
        {"index": 0, "quote": "aged 60 years or above"},
        {"index": 1, "quote": "belonging to SC or ST categories"},
        {"index": 2, "quote": "any member paid income tax last year"},
    ]

    assert check(answer, PAGE_SOURCE).problems == []


def test_a_quote_from_documents_required_is_still_refused_on_such_a_page() -> None:
    answer = good_answer()
    answer["rule_quotes"][0]["quote"] = "Ration card"

    result = check(answer, PAGE_SOURCE)

    assert [p.code for p in result.problems] == ["quote_wrong_section"]
    assert "documents required" in result.problems[0].message


def test_a_page_pasted_with_only_its_first_tab_can_be_quoted_from_its_whole_text() -> None:
    """What was pasted for Ujjwala: the tab bar, then the first tab's text with no heading. There
    are no sections to tell apart, so (as for a press release) the whole text is checked."""
    page = TAB_BAR + "The scheme gives a pension to every person aged 60 years or above.\n"
    answer = good_answer()
    answer["rule_quotes"] = [
        {"index": 0, "quote": "aged 60 years or above"},
        {"index": 1, "quote": "aged 60 years or above"},
        {"index": 2, "quote": "aged 60 years or above"},
    ]

    codes = [p.code for p in check(answer, page).problems]

    assert "quote_wrong_section" not in codes  # before the fix this was refused for every rule
