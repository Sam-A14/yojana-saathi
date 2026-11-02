from pathlib import Path

import pytest

from app.db.seed import DEFAULT_DATA_DIR
from app.llm import FakeLLM
from app.pipeline.extractor import EXTRACTION_TEMPERATURE, extract
from app.pipeline.source import MAX_SOURCE_CHARS, SourceDocument, SourceError, read_source
from tests.pipeline_samples import SLUG, SOURCE_TEXT, SOURCE_URL, answer_text, good_answer

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
    assert "govt_employee (one of none, group_d, other)" in prompt
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
