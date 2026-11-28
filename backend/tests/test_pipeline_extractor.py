import json
from pathlib import Path

import pytest

from app.db.seed import DEFAULT_DATA_DIR
from app.llm import FakeLLM
from app.llm.prompts import EXCEPTION_EXAMPLE_QUOTE, EXCEPTION_EXAMPLE_RULE
from app.pipeline.extractor import EXTRACTION_TEMPERATURE, extract
from app.pipeline.report import render_report
from app.pipeline.source import MAX_SOURCE_CHARS, SourceDocument, SourceError, read_source
from app.rules.engine import validate_rules
from tests.pipeline_samples import (
    BENEFIT_QUOTE,
    SLUG,
    SOURCE_TEXT,
    SOURCE_URL,
    answer_text,
    answer_with_benefit,
    good_answer,
)

SOURCE = SourceDocument(slug=SLUG, url=SOURCE_URL, text=SOURCE_TEXT.strip())


def test_extract_sends_text_fields_and_schema_at_low_temperature() -> None:
    fake = FakeLLM(response=answer_text(good_answer()))
    extract(SOURCE, fake)

    (call,) = fake.calls
    prompt = str(call["prompt"])
    assert 0 < float(call["temperature"]) <= 0.2  # type: ignore[arg-type]
    assert call["temperature"] == EXTRACTION_TEMPERATURE
    assert SOURCE_URL in prompt and "aged 60 years or above" in prompt
    assert "- owns_cultivable_land" in prompt  # from rules/fields.py
    assert "- has_land_record" in prompt  # from documents.json
    assert 'govt_employee (one of "none", "group_d", "other")' in prompt
    assert '"$id":"https://github.com/Sam-A14/yojana-saathi/data/scheme.schema.json"' in prompt
    assert "only a human sets them" in str(call["system"])


def test_a_good_answer_is_valid_and_carries_the_model_name() -> None:
    result = extract(SOURCE, FakeLLM(response=answer_text(good_answer()), model="fake-1"))
    assert result.validation.is_valid
    assert result.model == "fake-1"


def test_a_bad_answer_is_returned_flagged_with_the_raw_text_kept() -> None:
    result = extract(SOURCE, FakeLLM(response="Sorry, I cannot help."))
    assert not result.validation.is_valid
    assert result.raw_output == "Sorry, I cannot help."


# --- reading the pasted source file ---------------------------------------------------------


def write_source(tmp_path: Path, content: str, slug: str = "demo") -> Path:
    (tmp_path / "scheme_sources").mkdir(exist_ok=True)
    (tmp_path / "scheme_sources" / f"{slug}.txt").write_text(content, encoding="utf-8")
    return tmp_path


def test_read_source_takes_the_url_from_line_one(tmp_path: Path) -> None:
    data_dir = write_source(tmp_path, "https://example.org/demo\n\nThe text.\nMore text.\n")
    source = read_source("demo", data_dir)
    assert source.url == "https://example.org/demo"
    assert source.text == "The text.\nMore text."


@pytest.mark.parametrize(
    "content",
    ["no url here\ntext", "https://example.org/demo\n   \n", "https://a.org x\ntext", ""],
)
def test_read_source_rejects_a_bad_file(tmp_path: Path, content: str) -> None:
    with pytest.raises(SourceError):
        read_source("demo", write_source(tmp_path, content))


def test_read_source_rejects_huge_text(tmp_path: Path) -> None:
    data_dir = write_source(tmp_path, "https://example.org/\n" + "x" * (MAX_SOURCE_CHARS + 1))
    with pytest.raises(SourceError, match="longer"):
        read_source("demo", data_dir)


@pytest.mark.parametrize("slug", ["../secrets", "Demo", "demo/x", "", "a b"])
def test_read_source_rejects_slugs_that_could_escape_the_folder(slug: str) -> None:
    with pytest.raises(SourceError, match="not a valid slug"):
        read_source(slug, DEFAULT_DATA_DIR)


def test_read_source_missing_file(tmp_path: Path) -> None:
    with pytest.raises(SourceError, match="Cannot read"):
        read_source("nothing-here", tmp_path)


# --- the exception rule in the prompt -------------------------------------------------------


def test_prompt_tells_the_model_to_keep_exceptions_on_the_same_member() -> None:
    fake = FakeLLM(response=answer_text(good_answer()))
    extract(SOURCE, fake)

    (call,) = fake.calls
    system, prompt = str(call["system"]), str(call["prompt"])
    for word in ('"excluding"', '"except"', '"other than"'):
        assert word in system
    assert "all[...] inside any_member" in system
    # The worked example: pension condition and Group D exception together under one any_member.
    assert EXCEPTION_EXAMPLE_QUOTE in prompt
    assert json.dumps(EXCEPTION_EXAMPLE_RULE) in prompt


def test_the_prompt_example_is_a_valid_rule_with_the_exception_on_the_same_member() -> None:
    validate_rules({"all": [EXCEPTION_EXAMPLE_RULE]})

    member_rule = EXCEPTION_EXAMPLE_RULE["not"]["any_member"]
    fields = {condition["field"] for condition in member_rule["all"]}
    assert fields == {"pension_band", "govt_employee"}


# --- the benefit quote ----------------------------------------------------------------------


def test_prompt_asks_for_a_benefit_quote_and_nulls_without_one() -> None:
    fake = FakeLLM(response=answer_text(good_answer()))
    extract(SOURCE, fake)

    (call,) = fake.calls
    system, prompt = str(call["system"]), str(call["prompt"])
    assert "benefit_quote" in system and "must all be null" in system
    assert '"benefit_quote": null or "words copied' in prompt


def test_the_report_shows_the_benefit_quote_beside_the_rule_quotes() -> None:
    extraction = extract(SOURCE, FakeLLM(response=answer_text(answer_with_benefit())))

    report = render_report(extraction, "Saved as review item #1 (status: pending)", None)

    assert extraction.validation.is_valid
    assert f'"benefit_quote": "{BENEFIT_QUOTE}"' in report


# --- the allowed document codes ---------------------------------------------------------------


def test_prompt_lists_every_document_code_with_its_name_and_says_to_spell_it_exactly() -> None:
    documents = json.loads((DEFAULT_DATA_DIR / "documents.json").read_text("utf-8"))["documents"]
    fake = FakeLLM(response=answer_text(good_answer()))
    extract(SOURCE, fake)

    (call,) = fake.calls
    prompt = str(call["prompt"])
    section = prompt.split("ALLOWED DOCUMENT CODES\n", 1)[1].split("RULE FORMAT", 1)[0]
    for document in documents:
        assert f"- {document['code']} ({document['name_en']})" in section
    assert "aadhaar_card, not aadhaar" in section
    assert "do not make up a code" in section and "not_encoded" in section


def test_the_codes_in_the_prompt_and_the_allowed_rule_fields_come_from_one_file() -> None:
    from app.pipeline.allowed_fields import allowed_documents, allowed_fields

    prompt_codes = {code for code, _ in allowed_documents(DEFAULT_DATA_DIR)}
    field_codes = {
        f.removeprefix("has_") for f in allowed_fields(DEFAULT_DATA_DIR) if f.startswith("has_")
    }
    assert prompt_codes == field_codes
