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


def test_bump_version_replaces_an_existing_scheme_on_purpose(data_dir: Path) -> None:
    (data_dir / "scheme_sources" / "have-seed.txt").write_text("old page\n")
    (data_dir / "schemes_seed" / "have-seed.json").write_text("{}")

    path = add_scheme.write_source("have-seed", PAGE, data_dir, bump_version=True)

    assert path.read_text().startswith("https://example.org/")  # the source is now the new page
    assert (data_dir / "schemes_seed" / "have-seed.json").read_text() == "{}"  # seed untouched here


def test_an_existing_seed_without_bump_version_says_how_to_replace_it(data_dir: Path) -> None:
    (data_dir / "schemes_seed" / "have-seed.json").write_text("{}")

    with pytest.raises(add_scheme.AddSchemeError, match="bump_version"):
        add_scheme.write_source("have-seed", PAGE, data_dir)


def test_bump_version_for_a_slug_that_is_not_a_scheme_is_refused(data_dir: Path) -> None:
    with pytest.raises(add_scheme.AddSchemeError, match="nothing to replace"):
        add_scheme.write_source("typo-slug", PAGE, data_dir, bump_version=True)
    assert not (data_dir / "scheme_sources" / "typo-slug.txt").exists()


def test_the_pull_request_says_when_it_replaces_a_scheme() -> None:
    plain = add_scheme.pr_notice("Sam-A14", "pmay-g", None)
    bumped = add_scheme.pr_notice("Sam-A14", "pmay-g", None, replaces=True)

    assert "REPLACES" not in plain
    assert "REPLACES the existing `data/schemes_seed/pmay-g.json`" in bumped
    assert "labeller_notes" in bumped and "new version" in bumped


def test_the_command_passes_bump_version_only_when_asked(
    monkeypatch: pytest.MonkeyPatch, data_dir: Path
) -> None:
    calls: list[dict] = []
    monkeypatch.setattr(
        add_scheme, "write_source", lambda slug, text, **kw: calls.append(kw) or data_dir
    )
    monkeypatch.setenv("SOURCE_TEXT", PAGE)

    add_scheme.main(["write-source", "have-seed"])
    add_scheme.main(["write-source", "have-seed", "--bump-version"])

    assert calls == [{}, {"bump_version": True}]


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


# --- a page fetched by the workflow --------------------------------------------------------------


def test_the_page_text_can_come_from_a_file_the_fetcher_wrote(
    data_dir: Path, tmp_path: Path
) -> None:
    fetched = tmp_path / "fetched.txt"
    fetched.write_text(f"{SOURCE_URL}\n\nA title\n\nDetails\nText.\n", encoding="utf-8")

    real = add_scheme.write_source
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(add_scheme, "write_source", lambda slug, text: real(slug, text, data_dir))
        patch.delenv("SOURCE_TEXT", raising=False)
        assert add_scheme.main(["write-source", "new-scheme", "--from-file", str(fetched)]) == 0

    document = read_source("new-scheme", data_dir)
    assert document.url == SOURCE_URL and "Text." in document.text


def test_a_fetched_page_is_shown_in_the_pull_request_to_compare_with_the_page() -> None:
    text = f"{SOURCE_URL}\n\nTitle\n\nEligibility\nAdult women only.\n"

    notice = add_scheme.pr_notice("octocat", "new-scheme", None, SOURCE_URL, text)

    assert notice.index("## Added by the Add scheme workflow") < notice.index(
        "## The fetched source text"
    )
    assert f"read from {SOURCE_URL} by a program" in notice
    assert "compare it with the page before merging" in notice
    assert (
        "<details>" in notice and "</details>" in notice
    )  # collapsible: it does not push the review down
    assert "Adult women only." in notice


def test_a_pasted_page_has_no_fetched_section() -> None:
    notice = add_scheme.pr_notice("octocat", "new-scheme", None)

    assert "fetched source text" not in notice and "<details>" not in notice


def test_page_text_cannot_break_out_of_its_code_block() -> None:
    notice = add_scheme.pr_notice("o", "s", None, SOURCE_URL, "line\n```\n# A fake heading\n```\n")

    assert (
        "````\nline\n```\n# A fake heading\n```\n````" in notice
    )  # a longer fence than any inside


def test_a_very_long_page_is_cut_with_a_note_so_the_description_still_fits() -> None:
    text = "x" * (add_scheme.MAX_SHOWN_SOURCE_CHARS + 5_000)

    notice = add_scheme.pr_notice("o", "s", None, SOURCE_URL, text)

    assert "Cut after 40,000 characters" in notice
    assert len(notice) < 50_000  # far below GitHub's 65,536 limit


def test_the_command_shows_exactly_the_file_that_was_saved(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    add_scheme.write_source("new-scheme", PAGE, data_dir)
    monkeypatch.setattr(add_scheme, "DEFAULT_DATA_DIR", data_dir)

    code = add_scheme.main(
        ["pr-notice", "--actor", "octocat", "--slug", "new-scheme", "--fetched-from", SOURCE_URL]
    )

    out = capsys.readouterr().out
    assert (
        code == 0 and "aged 60 years or above" in out and "Added by the Add scheme workflow" in out
    )


# --- the workflow file ---------------------------------------------------------------------------

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "add-scheme.yml"


def workflow() -> dict:
    import yaml

    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_the_workflow_takes_text_or_an_address_and_only_the_slug_is_required() -> None:
    inputs = workflow()[True]["workflow_dispatch"]["inputs"]

    assert inputs["slug"]["required"] is True
    assert inputs["source_text"]["required"] is False and inputs["source_url"]["required"] is False
    assert inputs["source_text"]["default"] == "" and inputs["source_url"]["default"] == ""


def test_the_browser_is_installed_and_the_page_fetched_only_when_an_address_was_given() -> None:
    steps = {s.get("name"): s for s in workflow()["jobs"]["add"]["steps"]}

    for name in ("Install the browser", "Fetch the page (robots.txt first)"):
        assert steps[name]["if"] == "steps.mode.outputs.fetch == 'true'", name
    # the plain install (used for pasted text too) never pulls in the browser package
    plain = next(
        s
        for s in workflow()["jobs"]["add"]["steps"]
        if s.get("run") == "pip install -r backend/requirements.txt"
    )
    assert "fetch" not in plain["run"]
    assert "requirements-fetch.txt" in steps["Install the browser"]["run"]


def test_the_fetch_comes_before_the_source_is_written_and_the_model_is_called() -> None:
    names = [s.get("name") for s in workflow()["jobs"]["add"]["steps"]]

    assert names.index("Check there is exactly one source") < names.index(
        "Fetch the page (robots.txt first)"
    )
    assert names.index("Fetch the page (robots.txt first)") < names.index("Write the source file")
    assert names.index("Write the source file") < names.index("Extract and validate the rules")


def test_the_address_reaches_the_script_only_through_the_environment() -> None:
    step = next(
        s
        for s in workflow()["jobs"]["add"]["steps"]
        if s.get("name") == "Fetch the page (robots.txt first)"
    )

    assert step["env"]["SOURCE_URL"] == "${{ inputs.source_url }}"
    assert "${{" not in step["run"]  # nothing typed by a person is pasted into the shell text


def test_bump_version_is_an_optional_box_that_reaches_every_step_through_the_environment() -> None:
    inputs = workflow()[True]["workflow_dispatch"]["inputs"]
    assert inputs["bump_version"]["type"] == "boolean"
    assert inputs["bump_version"]["required"] is False
    assert inputs["bump_version"]["default"] is False

    steps = {s.get("name"): s for s in workflow()["jobs"]["add"]["steps"]}
    for name in ("Write the source file", "Write the seed file from the review item"):
        step = steps[name]
        assert step["env"]["BUMP_VERSION"] == "${{ inputs.bump_version }}", name
        assert "--bump-version" in step["run"], name
        assert "${{" not in step["run"], name
    # an existing scheme is refused when the source is written, before the model is called
    names = [s.get("name") for s in workflow()["jobs"]["add"]["steps"]]
    assert names.index("Write the source file") < names.index("Extract and validate the rules")
