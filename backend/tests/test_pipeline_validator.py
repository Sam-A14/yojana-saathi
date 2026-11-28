"""The validator, without a database or an LLM."""

import copy
import json
from typing import Any

import pytest

from app.db.seed import DEFAULT_DATA_DIR, _validator
from app.pipeline.allowed_fields import allowed_fields
from app.pipeline.validator import ValidationResult, validate_output
from tests.pipeline_samples import (
    BENEFIT_QUOTE,
    SLUG,
    SOURCE_TEXT,
    SOURCE_URL,
    answer_with_benefit,
    good_answer,
)

ALLOWED = allowed_fields(DEFAULT_DATA_DIR)
SCHEMA_VALIDATOR = _validator(DEFAULT_DATA_DIR / "scheme.schema.json")


def check(raw: str | dict[str, Any]) -> ValidationResult:
    text = raw if isinstance(raw, str) else json.dumps(raw)
    return validate_output(
        text,
        slug=SLUG,
        source_url=SOURCE_URL,
        source_text=SOURCE_TEXT,
        allowed=ALLOWED,
        schema_validator=SCHEMA_VALIDATOR,
    )


def codes(result: ValidationResult) -> list[str]:
    return [p.code for p in result.problems]


def answer() -> dict[str, Any]:
    return copy.deepcopy(good_answer())


def test_a_correct_answer_passes() -> None:
    result = check(answer())
    assert result.problems == []
    assert result.is_valid
    assert result.scheme is not None and len(result.quotes) == 3


def test_a_markdown_fence_around_good_json_is_tolerated() -> None:
    assert check("```json\n" + json.dumps(answer()) + "\n```").is_valid


@pytest.mark.parametrize("raw", ["not json at all", "", '{"scheme": NaN}', "{'a': 1}"])
def test_text_that_is_not_json_is_flagged_not_dropped(raw: str) -> None:
    result = check(raw)
    assert codes(result) == ["not_json"]
    assert result.scheme is None


def test_wrong_top_level_shape() -> None:
    assert codes(check("[1, 2]")) == ["bad_shape"]
    assert codes(check({"nothing": 1})) == ["bad_shape", "bad_shape"]


def test_schema_violation_is_flagged_but_the_scheme_is_kept() -> None:
    bad = answer()
    bad["scheme"]["version"]["rules"]["all"][0]["op"] = "roughly"
    result = check(bad)
    assert "schema" in codes(result)
    assert result.scheme is not None  # kept for the reviewer


def test_field_outside_the_allowed_list_names_where() -> None:
    bad = answer()
    bad["scheme"]["version"]["rules"]["all"][2] = {
        "not": {"any_member": {"field": "owns_tractor", "op": "is_true"}}
    }
    result = check(bad)
    problem = next(p for p in result.problems if p.code == "unknown_field")
    assert problem.where == "scheme.version.rules.all[2].not.any_member"
    assert "owns_tractor" in problem.message


def test_unknown_field_in_fixable_is_flagged() -> None:
    bad = answer()
    bad["scheme"]["version"]["rules"]["fixable"] = ["has_unicorn_card"]
    problem = next(p for p in check(bad).problems if p.code == "unknown_field")
    assert problem.where == "scheme.version.rules.fixable[0]"


def test_a_rule_without_a_quote_is_flagged() -> None:
    bad = answer()
    del bad["rule_quotes"][1]
    result = check(bad)
    assert codes(result) == ["missing_quote"]
    assert result.problems[0].where == "scheme.version.rules.all[1]"


def test_no_quotes_at_all_flags_every_rule() -> None:
    bad = answer()
    bad["rule_quotes"] = []
    assert codes(check(bad)) == ["missing_quote"] * 3


def test_an_invented_quote_is_flagged() -> None:
    bad = answer()
    bad["rule_quotes"][0]["quote"] = "every citizen above the age of sixty"
    result = check(bad)
    assert codes(result) == ["quote_not_in_source", "missing_quote"]


def test_a_quote_may_span_a_line_break_in_the_source() -> None:
    # SOURCE_TEXT breaks the line between "ST" and "categories"; the quote is on one line.
    assert check(answer()).is_valid


def test_a_too_short_quote_is_flagged() -> None:
    bad = answer()
    bad["rule_quotes"][0]["quote"] = "aged 60"
    assert "quote_too_short" in codes(check(bad))


def test_quote_index_out_of_range_and_malformed_entries() -> None:
    bad = answer()
    bad["rule_quotes"] += [{"index": 9, "quote": "aged 60 years or above"}, "oops", {"index": True}]
    assert codes(check(bad)) == ["bad_quote", "bad_quote", "bad_quote"]


def test_wrong_slug_wrong_url_and_claiming_verified_are_flagged() -> None:
    bad = answer()
    bad["scheme"]["slug"] = "another-scheme"
    bad["scheme"]["version"]["source_url"] = "https://elsewhere.example/"
    bad["scheme"]["version"]["verified_at"] = "2026-11-02"
    bad["scheme"]["version"]["approved_by"] = "gemini"
    assert codes(check(bad)) == [
        "slug_mismatch",
        "source_url_mismatch",
        "claims_verified",
        "claims_verified",
    ]


def test_engine_refusal_is_flagged_when_the_schema_cannot_see_it() -> None:
    bad = answer()
    bad["scheme"]["version"]["rules"]["all"][0] = {
        "field": "age",
        "op": "between",
        "value": [70, 60],
    }
    result = check(bad)
    assert codes(result) == ["engine_rejects"]


def test_every_problem_is_reported_not_just_the_first() -> None:
    bad = answer()
    bad["scheme"]["slug"] = "x"
    bad["rule_quotes"] = []
    assert len(check(bad).problems) == 4  # slug + three missing quotes


def test_garbage_inside_a_valid_envelope_does_not_crash() -> None:
    result = check({"scheme": {"version": "oops"}, "rule_quotes": [None, 3]})
    assert not result.is_valid


# --- the benefit text needs a quote like a rule does ---------------------------------------


def test_benefit_text_with_a_real_quote_passes_and_the_quote_is_kept() -> None:
    result = check(answer_with_benefit())
    assert result.problems == []
    assert result.benefit_quote == BENEFIT_QUOTE
    assert result.stored_quotes()[-1] == {"field": "benefit_text_en", "quote": BENEFIT_QUOTE}
    assert len(result.stored_quotes()) == 4  # three rule quotes, then the benefit quote


def test_no_benefit_text_and_no_quote_is_fine() -> None:
    result = check(answer())  # benefit_text_en is absent: nothing to prove
    assert result.is_valid
    assert result.stored_quotes() == result.quotes


def test_benefit_text_set_to_null_is_fine() -> None:
    ok = answer()
    ok["scheme"]["version"]["benefit_text_en"] = None
    ok["scheme"]["version"]["benefit_text_hi"] = None
    ok["benefit_quote"] = None
    assert check(ok).is_valid


def test_benefit_text_without_a_quote_is_flagged() -> None:
    bad = answer_with_benefit()
    del bad["benefit_quote"]
    result = check(bad)
    assert codes(result) == ["benefit_unquoted"]
    assert result.problems[0].where == "scheme.version.benefit_text_en"


@pytest.mark.parametrize("quote", [None, "", "   "])
def test_an_empty_benefit_quote_counts_as_none(quote: str | None) -> None:
    bad = answer_with_benefit()
    bad["benefit_quote"] = quote
    assert codes(check(bad)) == ["benefit_unquoted"]


def test_an_invented_benefit_quote_is_flagged() -> None:
    bad = answer_with_benefit()
    bad["benefit_quote"] = "gives Rs.1,000 every month to widows"
    assert codes(check(bad)) == ["benefit_quote_not_in_source"]


def test_a_too_short_benefit_quote_is_flagged() -> None:
    bad = answer_with_benefit()
    bad["benefit_quote"] = "a pension"
    assert codes(check(bad)) == ["benefit_quote_too_short"]


def test_a_benefit_quote_may_span_a_line_break_in_the_source() -> None:
    ok = answer_with_benefit()
    ok["scheme"]["version"]["benefit_text_en"] = "A pension for persons belonging to SC or ST."
    ok["benefit_quote"] = "persons belonging to SC or ST categories"  # the source breaks after "ST"
    assert check(ok).is_valid


def test_hindi_benefit_text_needs_english_benefit_text() -> None:
    bad = answer()
    bad["scheme"]["version"]["benefit_text_hi"] = "परिवार को पेंशन मिलती है।"
    result = check(bad)
    assert codes(result) == ["benefit_hi_without_en"]
    assert result.problems[0].where == "scheme.version.benefit_text_hi"


def test_hindi_benefit_text_beside_a_quoted_english_one_is_allowed() -> None:
    ok = answer_with_benefit()
    ok["scheme"]["version"]["benefit_text_hi"] = "परिवार को पेंशन मिलती है।"
    assert check(ok).is_valid


def test_benefit_quote_of_the_wrong_type_is_a_shape_problem() -> None:
    bad = answer_with_benefit()
    bad["benefit_quote"] = ["gives a pension"]
    assert "bad_shape" in codes(check(bad))


# --- document codes must exist: the approval step would refuse them -------------------------------


def with_documents(*codes: str) -> dict[str, Any]:
    bad = answer()
    bad["scheme"]["version"]["documents"] = [
        {"code": code, "required": True, "applies_to": "applicant"} for code in codes
    ]
    return bad


def test_a_real_document_code_passes() -> None:
    assert check(with_documents("aadhaar_card", "bpl_card")).is_valid


def test_a_made_up_document_code_is_flagged_with_where_and_a_hint() -> None:
    """The proposal that failed approval: the model wrote "aadhaar" for aadhaar_card."""
    result = check(with_documents("aadhaar_card", "aadhaar"))

    assert codes(result) == ["unknown_document"]
    assert result.problems[0].where == "scheme.version.documents[1].code"
    assert "'aadhaar' is not in documents.json" in result.problems[0].message
    assert result.scheme is not None  # kept and flagged, never dropped


def test_a_document_listed_twice_is_flagged() -> None:
    result = check(with_documents("ration_card", "ration_card"))
    assert codes(result) == ["duplicate_document"]
    assert result.problems[0].where == "scheme.version.documents[1].code"


def test_every_unknown_document_is_reported_not_just_the_first() -> None:
    assert codes(check(with_documents("aadhaar", "pan", "bpl_card"))) == ["unknown_document"] * 2


def test_a_scheme_with_no_documents_is_fine() -> None:
    assert check(with_documents()).is_valid


def test_malformed_document_entries_do_not_crash_this_check() -> None:
    bad = answer()
    bad["scheme"]["version"]["documents"] = ["oops", {"required": True}, {"code": 7}]
    result = check(bad)
    assert "unknown_document" not in codes(result)  # the schema check reports the real problems
    assert "schema" in codes(result)
