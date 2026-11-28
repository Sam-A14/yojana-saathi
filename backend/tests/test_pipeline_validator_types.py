"""Validator gaps found in review item 4: value types, and papers written as eligibility rules."""

import json
from typing import Any

import pytest

from app.db.seed import DEFAULT_DATA_DIR, _validator, read_seed_files
from app.llm.prompts import SYSTEM_PROMPT, build_user_prompt
from app.pipeline.allowed_fields import allowed_documents, allowed_fields
from app.pipeline.field_types import (
    BOOLEAN_FIELDS,
    CLOSED_VALUES,
    NUMBER_FIELDS,
    TEXT_FIELDS,
    kind_of,
    value_problem,
)
from app.pipeline.sections import eligibility_text, split_sections
from app.pipeline.validator import ValidationResult, validate_output
from app.rules.fields import ATTRIBUTE_FIELDS
from tests import ignoaps_item4 as item4
from tests.pipeline_samples import SLUG, SOURCE_TEXT, SOURCE_URL, good_answer

ALLOWED = allowed_fields(DEFAULT_DATA_DIR)
SCHEMA_VALIDATOR = _validator(DEFAULT_DATA_DIR / "scheme.schema.json")


def check(
    answer: dict[str, Any], *, source_text: str = item4.SOURCE_TEXT, slug: str = item4.SLUG
) -> ValidationResult:
    return validate_output(
        json.dumps(answer),
        slug=slug,
        source_url=item4.SOURCE_URL if slug == item4.SLUG else SOURCE_URL,
        source_text=source_text,
        allowed=ALLOWED,
        schema_validator=SCHEMA_VALIDATOR,
    )


def codes(result: ValidationResult) -> list[str]:
    return [p.code for p in result.problems]


def paper_codes(result: ValidationResult) -> list[str]:
    """Only the paper-as-rule problems. A paper quoted from Documents Required is also refused for
    its section (a later check, "quote_wrong_section"), so these tests look at the one they are
    about and leave the section check to its own tests."""
    return [p.code for p in result.problems if p.code == "document_as_rule"]


# --- review item 4, the failing fixture (its exact Proposal block) -----------------------------


def test_item_4_is_flagged_by_the_checks_added_after_it_and_by_nothing_else() -> None:
    """The old validator passed item 4. Today three checks reject it: the value type (added for
    it), papers as rules (added for it) and the rule-quote section (added later, because the six
    paper rules quote Documents Required). Schema, fields, engine, documents, identity and benefit
    still accept it."""
    result = check(item4.proposal())

    assert {p.code for p in result.problems} == {
        "invalid_value_type",
        "document_as_rule",
        "quote_wrong_section",
    }


def test_item_4_is_no_longer_valid_and_each_defect_is_named_with_its_position() -> None:
    result = check(item4.proposal())

    assert not result.is_valid
    assert [(p.code, p.where) for p in result.problems] == [
        ("invalid_value_type", "scheme.version.rules.all[0]"),
        # Each paper rule is refused for its quote's section, and again as a paper: two lines,
        # because each names a different fix.
        *[("quote_wrong_section", f"rule_quotes[{i}]") for i in range(2, 8)],
        *[("document_as_rule", f"scheme.version.rules.all[{i}]") for i in range(2, 8)],
    ]
    type_problem = result.problems[0].message
    assert "is_bpl is a yes/no field" in type_problem and '"yes"' in type_problem
    assert "is_true" in type_problem and "would match nobody" in type_problem
    paper_problems = [p for p in result.problems if p.code == "document_as_rule"]
    for problem, paper in zip(paper_problems, item4.PAPER_RULES, strict=True):
        assert paper in problem.message
        assert "only in version.documents" in problem.message
        assert "Eligibility section" in problem.message


def test_the_corrected_item_4_passes_so_nothing_else_is_flagged() -> None:
    result = check(item4.corrected())
    assert result.problems == [], [p.as_dict() for p in result.problems]


def test_the_corrected_item_4_keeps_its_papers_and_notes_the_alternatives() -> None:
    version = item4.corrected()["scheme"]["version"]
    required = {d["code"]: d["required"] for d in version["documents"]}
    assert required["voter_id"] is False and required["aadhaar_card"] is False
    assert required["domicile_certificate"] is True  # not an alternative: still required
    assert item4.corrected()["scheme"]["labeller_notes"]["notes"]  # the note is there


def test_the_quotes_of_item_4_sit_in_the_sections_the_check_relies_on() -> None:
    """Rules 0 and 1 quote the Eligibility section; every paper rule quotes Documents Required."""
    sections = split_sections(item4.SOURCE_TEXT)
    quotes = {q["index"]: q["quote"] for q in item4.proposal()["rule_quotes"]}
    for index in (0, 1):
        assert quotes[index] in sections["eligibility"]
    for index in range(2, 8):
        assert quotes[index] in sections["documents required"]
        assert quotes[index] not in sections["eligibility"]


def test_the_fixture_is_the_run_summary_block_unedited() -> None:
    """Guards the swap: eight rules, six of them papers, all six also under fixable."""
    scheme = item4.proposal()["scheme"]["version"]
    assert len(scheme["rules"]["all"]) == 8
    assert scheme["rules"]["all"][0] == {"field": "is_bpl", "op": "eq", "value": "yes"}
    assert len(scheme["rules"]["fixable"]) == 6
    assert all(d["required"] for d in scheme["documents"])


# --- 1. a value must fit its field ------------------------------------------------------------


def cond(field: str, op: str, *value: Any) -> dict[str, Any]:
    node: dict[str, Any] = {"field": field, "op": op}
    if value:
        node["value"] = value[0]
    return node


@pytest.mark.parametrize(
    "node",
    [
        cond("is_bpl", "is_true"),
        cond("is_bpl", "eq", True),
        cond("is_bpl", "eq", False),
        cond("disability", "neq", True),
        cond("has_ration_card", "is_true"),
        cond("category", "eq", "SC"),
        cond("category", "in", ["SC", "ST", "OBC"]),
        cond("category", "not_in", ["General"]),
        cond("govt_employee", "neq", "group_d"),
        cond("age", "gte", 60),
        cond("age", "between", [60, 79]),
        cond("age", "eq", 61.5),
        cond("income_band_max", "lte", 200000),
        cond("state", "eq", "UP"),
        cond("district", "in", ["Agra", "Lucknow"]),
    ],
)
def test_a_value_that_fits_its_field_is_accepted(node: dict[str, Any]) -> None:
    assert value_problem(node) is None


@pytest.mark.parametrize(
    ("node", "fragment"),
    [
        (
            cond("is_bpl", "eq", "yes"),
            'yes/no field: use is_true, or eq with true or false (got "yes")',
        ),
        (cond("is_bpl", "eq", "true"), 'got "true"'),
        (cond("is_bpl", "eq", 1), "got 1"),  # 1 is not true
        (cond("is_student", "neq", "no"), 'got "no"'),
        (cond("is_bpl", "in", [True]), "in cannot be used"),
        (cond("is_bpl", "gte", 1), "gte cannot be used"),
        (cond("has_ration_card", "eq", "yes"), 'got "yes"'),
        (cond("category", "eq", "Dalit"), "category takes one of: General, SC, ST, OBC"),
        (cond("category", "in", ["SC", "XX"]), 'got "XX"'),
        (cond("category", "in", []), "category takes values from"),
        (cond("category", "gte", 3), "fixed list of answers"),
        (cond("gender", "eq", True), "gender takes one of"),
        (cond("govt_employee", "eq", 5), "govt_employee takes one of"),
        (cond("age", "gte", "sixty"), 'age is a number: gte needs a number value (got "sixty")'),
        (cond("age", "gte", True), "got true"),  # True is not 1
        (cond("age", "between", [60]), "between needs a number"),
        (cond("age", "is_true"), "age is not a yes/no field"),
        (cond("income_band_max", "lte", "2 lakh"), "needs a number value"),
        (cond("state", "eq", 5), "state is text"),
        (cond("district", "gte", "A"), "district is text"),
        (cond("category", "is_true"), "category is not a yes/no field"),
    ],
)
def test_a_value_that_does_not_fit_its_field_is_described(
    node: dict[str, Any], fragment: str
) -> None:
    problem = value_problem(node)
    assert problem is not None and fragment in problem, problem


def test_a_condition_with_no_value_is_left_to_the_schema_and_the_engine() -> None:
    assert value_problem({"field": "age", "op": "gte"}) is None
    assert value_problem({"field": "no_such_field", "op": "eq", "value": 1}) is None


def test_the_position_of_a_bad_value_is_found_inside_nested_rules() -> None:
    answer = good_answer()
    answer["scheme"]["version"]["rules"]["all"][2] = {
        "not": {"any_member": {"all": [cond("age", "gte", 60), cond("is_student", "eq", "yes")]}}
    }
    result = check(answer, source_text=SOURCE_TEXT, slug=SLUG)

    problem = next(p for p in result.problems if p.code == "invalid_value_type")
    assert problem.where == "scheme.version.rules.all[2].not.any_member.all[1]"


def test_every_value_in_the_real_seed_files_fits_its_field() -> None:
    """No false alarm on the hand-labelled rules: the check must not reject what is known good."""

    def walk(node: Any) -> list[dict[str, Any]]:
        if isinstance(node, list):
            return [c for child in node for c in walk(child)]
        if isinstance(node, dict):
            if "field" in node:
                return [node]
            return [c for child in node.values() for c in walk(child)]
        return []

    conditions = [
        c for scheme in read_seed_files().schemes for c in walk(scheme["version"]["rules"]["all"])
    ]
    assert len(conditions) > 10
    assert [value_problem(c) for c in conditions if value_problem(c)] == []


def test_every_rule_field_has_a_type_so_a_new_field_forces_a_decision() -> None:
    assert [f for f in sorted(ATTRIBUTE_FIELDS) if kind_of(f) is None] == []
    assert kind_of("has_ration_card") == "boolean" and kind_of("no_such_field") is None
    kinds = [BOOLEAN_FIELDS, set(CLOSED_VALUES), NUMBER_FIELDS, TEXT_FIELDS]
    assert sum(len(k) for k in kinds) == len(set().union(*kinds))  # no field has two kinds


# --- 2. papers are not eligibility ------------------------------------------------------------


def one_rule(field: str, quote: str) -> dict[str, Any]:
    return item4.build([(cond(field, "is_true"), quote)], benefit=False)


def test_a_paper_rule_quoted_from_documents_required_is_refused() -> None:
    result = check(one_rule("has_ration_card", "Ration Card"))
    assert paper_codes(result) == ["document_as_rule"]


def test_a_paper_rule_quoted_from_the_eligibility_section_is_allowed() -> None:
    text = (
        "Eligibility\nThe applicant must hold a valid ration card to apply.\n"
        "Documents Required\nRation Card\n"
    )
    answer = one_rule("has_ration_card", "must hold a valid ration card")
    assert check(answer, source_text=text).problems == []


def test_a_quote_that_is_in_both_sections_counts_as_eligibility() -> None:
    text = "Eligibility\nA ration card is needed.\nDocuments Required\nA ration card is needed.\n"
    assert check(one_rule("has_ration_card", "A ration card is needed."), source_text=text).is_valid


def test_with_no_eligibility_heading_a_paper_rule_cannot_be_shown_to_come_from_it() -> None:
    text = "Documents Required\nRation Card\nBank Passbook\n"
    assert paper_codes(check(one_rule("has_ration_card", "Ration Card"), source_text=text)) == [
        "document_as_rule"
    ]
    plain = "Every family with a ration card may apply for this scheme."
    assert paper_codes(
        check(one_rule("has_ration_card", "with a ration card may apply"), source_text=plain)
    ) == ["document_as_rule"]


def test_a_paper_inside_a_bigger_rule_is_found_too() -> None:
    answer = item4.build(
        [
            (
                {"any": [cond("age", "gte", 60), cond("has_ration_card", "is_true")]},
                "Ration Card",
            )
        ]
    )
    result = check(answer)
    assert paper_codes(result) == ["document_as_rule"]
    paper = next(p for p in result.problems if p.code == "document_as_rule")
    assert paper.where == "scheme.version.rules.all[0]"


def test_rules_that_are_not_about_papers_never_trigger_the_check() -> None:
    """The existing sample has no sections at all, and no has_ rules: it stays valid."""
    assert check(good_answer(), source_text=SOURCE_TEXT, slug=SLUG).is_valid


# --- section reading --------------------------------------------------------------------------


def test_headings_are_found_whatever_the_case_and_a_colon_is_fine() -> None:
    text = "Title\nELIGIBILITY:\nfirst\nDocuments required\nsecond\nFAQ: Why?\nthird\n"
    sections = split_sections(text)
    assert sections["eligibility"] == "first"
    assert sections["documents required"] == "second"
    assert "third" in sections["faq"] and "FAQ: Why?" in sections["faq"]
    assert "Title" not in "".join(sections.values())  # before the first heading: no section


def test_eligibility_text_is_only_what_is_under_that_heading() -> None:
    text = (
        "Benefits\nA pension.\nEligibility\nAged 60.\nBe poor.\nDocuments Required\nRation Card\n"
    )
    assert eligibility_text(text) == "Aged 60.\nBe poor."
    assert eligibility_text("no headings here") == ""
    assert "Ration Card" not in eligibility_text(text)


def test_a_line_that_merely_contains_a_heading_word_is_not_a_heading() -> None:
    text = (
        "Eligibility\nThe eligibility of the family is checked.\nDocuments required by the office\n"
    )
    assert split_sections(text) == {
        "eligibility": "The eligibility of the family is checked.\nDocuments required by the office"
    }


# --- 3. the prompt ----------------------------------------------------------------------------


def prompt() -> tuple[str, str]:
    schema = json.loads((DEFAULT_DATA_DIR / "scheme.schema.json").read_text("utf-8"))
    user = build_user_prompt(
        slug=SLUG,
        source_url=SOURCE_URL,
        source_text=SOURCE_TEXT,
        fields=ALLOWED,
        documents=allowed_documents(DEFAULT_DATA_DIR),
        schema=schema,
    )
    return SYSTEM_PROMPT, user


def test_the_prompt_keeps_papers_out_of_rules() -> None:
    system, user = prompt()
    sentence = "Papers listed under documents go ONLY in version.documents, never in rules"
    assert sentence in system
    assert sentence in " ".join(user.split())  # the user prompt wraps its lines
    assert "Eligibility" in user and "section itself says" in user


def test_the_prompt_says_to_use_true_false_or_is_true_for_yes_no_fields() -> None:
    _, user = prompt()
    assert '{"op": "is_true"}' in user and 'never the text "yes"' in user
    assert "a field with a list of\nallowed answers takes only those answers" in user


def test_the_prompt_says_alternatives_are_not_required_and_must_be_noted() -> None:
    _, user = prompt()
    assert '"X/ Y/ Z" or "X or Y"' in user
    assert "mark none of them required" in user and '"required": false' in user
    assert "scheme.labeller_notes.notes" in user
