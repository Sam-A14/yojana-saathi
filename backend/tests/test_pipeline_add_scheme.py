"""The pieces of the Add scheme workflow that are code, not shell."""

import json
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.db.models import ReviewItem
from app.llm import FakeLLM
from app.pipeline import add_scheme, extract_cli
from app.pipeline.source import SourceDocument, read_source
from tests.pipeline_samples import SLUG, SOURCE_TEXT, SOURCE_URL, answer_text, good_answer

PAGE = f"{SOURCE_URL}\n\n{SOURCE_TEXT}"


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    (tmp_path / "scheme_sources").mkdir()
    (tmp_path / "schemes_seed").mkdir()
    return tmp_path


# --- write-source ------------------------------------------------------------------------------


def test_the_pasted_page_is_saved_so_the_extractor_can_read_it(data_dir: Path) -> None:
    path = add_scheme.write_source("new-scheme", PAGE, data_dir)

    assert path == data_dir / "scheme_sources" / "new-scheme.txt"
    document = read_source("new-scheme", data_dir)
    assert document.url == SOURCE_URL and "aged 60 years or above" in document.text


def test_windows_line_breaks_become_plain_ones_and_nothing_else_changes(data_dir: Path) -> None:
    page = "https://example.org/x\r\n\r\nLine one.  Two spaces stay.\r\nLine two.\r\n\r\n"
    path = add_scheme.write_source("new-scheme", page, data_dir)

    assert path.read_text(encoding="utf-8") == (
        "https://example.org/x\n\nLine one.  Two spaces stay.\nLine two.\n"
    )


@pytest.mark.parametrize("slug", ["", "Bad Slug", "../etc/passwd", "a/b", "-x", "x-", "x--y", "X"])
def test_a_bad_slug_is_refused_and_nothing_is_written(data_dir: Path, slug: str) -> None:
    with pytest.raises(add_scheme.AddSchemeError, match="not a valid slug"):
        add_scheme.write_source(slug, PAGE, data_dir)
    assert list((data_dir / "scheme_sources").iterdir()) == []


def test_an_existing_source_or_seed_file_is_never_overwritten(data_dir: Path) -> None:
    (data_dir / "scheme_sources" / "have-source.txt").write_text("keep me\n")
    (data_dir / "schemes_seed" / "have-seed.json").write_text("{}")

    for slug in ("have-source", "have-seed"):
        with pytest.raises(add_scheme.AddSchemeError, match="already exists"):
            add_scheme.write_source(slug, PAGE, data_dir)
    assert (data_dir / "scheme_sources" / "have-source.txt").read_text() == "keep me\n"
    assert not (data_dir / "scheme_sources" / "have-seed.txt").exists()


@pytest.mark.parametrize(
    "page", ["", "no url on the first line\nsome text", "https://example.org/x\n\n   \n"]
)
def test_a_page_without_a_url_or_text_is_refused_and_leaves_no_file(
    data_dir: Path, page: str
) -> None:
    with pytest.raises(add_scheme.AddSchemeError):
        add_scheme.write_source("new-scheme", page, data_dir)
    assert not (data_dir / "scheme_sources" / "new-scheme.txt").exists()


def test_a_page_that_is_too_long_is_refused(data_dir: Path) -> None:
    with pytest.raises(add_scheme.AddSchemeError, match="longer than"):
        add_scheme.write_source("new-scheme", "https://example.org/x\n" + "a" * 70_000, data_dir)


def test_the_command_reads_the_text_from_the_environment_not_the_command_line(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = add_scheme.write_source
    monkeypatch.setattr(add_scheme, "write_source", lambda slug, text: real(slug, text, data_dir))
    monkeypatch.setenv("SOURCE_TEXT", PAGE)

    assert add_scheme.main(["write-source", "new-scheme"]) == 0
    assert read_source("new-scheme", data_dir).url == SOURCE_URL


def test_the_command_exits_1_with_the_reason_on_a_bad_slug(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SOURCE_TEXT", PAGE)
    assert add_scheme.main(["write-source", "Bad Slug"]) == 1
    assert "not a valid slug" in capsys.readouterr().err


# --- issue-body and pr-notice ------------------------------------------------------------------

RESULT = {
    "slug": "new-scheme",
    "review_item_id": 12,
    "is_valid": False,
    "problems": [
        {
            "code": "invalid_value_type",
            "where": "scheme.version.rules.all[2]",
            "message": 'category takes one of: General, SC, ST, OBC (got "obc").',
        },
        {"code": "quote_wrong_section", "where": "rule_quotes[3]", "message": "x ``` y"},
    ],
}


def test_the_issue_lists_every_problem_and_says_nothing_was_published() -> None:
    body = add_scheme.issue_body(RESULT, "https://github.com/o/r/actions/runs/1")

    assert "`new-scheme`" in body and "review item 12" in body
    assert "failed validation" in body and "2 problem(s)" in body
    assert "nothing was published" in body
    assert "invalid_value_type at scheme.version.rules.all[2]: category takes one of" in body
    assert "quote_wrong_section at rule_quotes[3]" in body
    assert "Run: https://github.com/o/r/actions/runs/1" in body
    assert "no automatic retry" in body.lower()


def test_model_text_in_a_problem_cannot_break_out_of_its_code_block() -> None:
    body = add_scheme.issue_body(RESULT, None)

    # the problem that contains three backticks is wrapped in a longer fence
    assert "````\nquote_wrong_section at rule_quotes[3]: x ``` y\n````" in body


def test_the_pull_request_starts_with_who_asked_and_that_merging_is_the_verification() -> None:
    notice = add_scheme.pr_notice("octocat", "new-scheme", "https://github.com/o/r/actions/runs/1")

    assert "started by `octocat`" in notice and "`approved_by` in the file is `octocat`" in notice
    assert "before anyone read this pull request" in notice
    assert "Merging is the verification" in notice
    assert "docs/scheme-review-checklist.md" in notice
    assert "data/scheme_sources/new-scheme.txt" in notice and "only merge needed" in notice
    assert "Seed database" in notice and "@" not in notice  # no one is pinged


# --- the result file the extract command writes for the workflow --------------------------------


def run_cli(monkeypatch: pytest.MonkeyPatch, db: Session, response: str, result_file: Path) -> int:
    source = SourceDocument(slug=SLUG, url=SOURCE_URL, text=SOURCE_TEXT)
    monkeypatch.setattr(extract_cli, "read_source", lambda slug: source)
    monkeypatch.setattr(extract_cli, "get_llm_client", lambda: FakeLLM(response=response))
    monkeypatch.setattr(extract_cli, "new_session", lambda: db)
    return extract_cli.main([SLUG, "--result-file", str(result_file)])


def test_a_valid_proposal_writes_its_review_item_number_and_valid_true(
    monkeypatch: pytest.MonkeyPatch, db: Session, tmp_path: Path
) -> None:
    out = tmp_path / "result.json"
    assert run_cli(monkeypatch, db, answer_text(good_answer()), out) == 0

    result = json.loads(out.read_text(encoding="utf-8"))
    item = db.query(ReviewItem).filter_by(scheme_slug=SLUG).one()
    assert result == {"slug": SLUG, "review_item_id": item.id, "is_valid": True, "problems": []}


def test_an_invalid_proposal_still_exits_0_and_lists_its_problems(
    monkeypatch: pytest.MonkeyPatch, db: Session, tmp_path: Path
) -> None:
    answer = good_answer()
    answer["scheme"]["version"]["rules"]["all"][1]["value"] = ["sc", "st"]  # wrong case
    out = tmp_path / "result.json"

    assert run_cli(monkeypatch, db, answer_text(answer), out) == 0  # a flagged proposal is normal

    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["is_valid"] is False and result["review_item_id"] is not None
    assert [p["code"] for p in result["problems"]] == ["invalid_value_type"]
    assert set(result["problems"][0]) == {"code", "where", "message"}
