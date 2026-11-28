"""Approving a reviewed proposal: the seed file, the pull request text, and every refusal.

Nothing here needs a database except the last two tests, which run the command end to end.
"""

import contextlib
import copy
import json
import re
import shutil
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ReviewItem, Scheme, SchemeVersion
from app.db.seed import DEFAULT_DATA_DIR, read_seed_files
from app.llm import FakeLLM
from app.pipeline import approve
from app.pipeline.approve import ApproveError, file_text, prepare
from app.pipeline.extractor import extract
from app.pipeline.proposals import save_proposal
from app.pipeline.source import SourceDocument
from tests.pipeline_samples import (
    BENEFIT_QUOTE,
    BENEFIT_TEXT,
    QUOTES,
    SLUG,
    SOURCE_TEXT,
    SOURCE_URL,
    answer_text,
    answer_with_benefit,
    good_answer,
)

TODAY = date(2026, 11, 26)
SOURCE = SourceDocument(slug=SLUG, url=SOURCE_URL, text=SOURCE_TEXT.strip())


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """A private copy of what the command needs from data/, with the sample scheme's source text."""
    for name in ("documents.json", "documents.schema.json", "scheme.schema.json"):
        shutil.copy(DEFAULT_DATA_DIR / name, tmp_path / name)
    (tmp_path / "schemes_seed").mkdir()
    (tmp_path / "scheme_sources").mkdir()
    (tmp_path / "scheme_sources" / f"{SLUG}.txt").write_text(
        f"{SOURCE_URL}\n{SOURCE_TEXT}", "utf-8"
    )
    return tmp_path


def make_item(answer: dict[str, Any] | None = None, **changes: Any) -> ReviewItem:
    """A review item as the extractor would have saved it, without a database."""
    validation = extract(
        SOURCE, FakeLLM(response=answer_text(answer or answer_with_benefit()))
    ).validation
    assert validation.is_valid, validation.problems
    fields: dict[str, Any] = {
        "id": 7,
        "scheme_slug": SLUG,
        "source_url": SOURCE_URL,
        "proposed_rules_json": validation.scheme,
        "source_quotes": validation.stored_quotes(),
        "is_valid": True,
        "validation_errors": [],
        "model": "fake-1",
        "status": "pending",
    }
    return ReviewItem(**{**fields, **changes})


# --- the file ---------------------------------------------------------------------------------


def test_a_valid_item_becomes_a_verified_seed_file_the_loader_accepts(data_dir: Path) -> None:
    approval = prepare(make_item(), "octocat", today=TODAY, data_dir=data_dir)

    version = approval.seed["version"]
    assert approval.slug == SLUG
    assert version["verified_at"] == "2026-11-26" and version["approved_by"] == "octocat"
    assert version["benefit_text_en"] == BENEFIT_TEXT
    assert list(approval.seed)[:2] == ["$schema", "labeller_notes"]
    assert approval.seed["labeller_notes"]["example"] is False

    (data_dir / "schemes_seed" / f"{SLUG}.json").write_text(file_text(approval.seed), "utf-8")
    loaded = read_seed_files(data_dir).schemes  # schema, file name, documents: the real loader
    assert [s["slug"] for s in loaded] == [SLUG]


def test_conditions_the_fields_cannot_express_become_what_we_did_not_check(
    data_dir: Path,
) -> None:
    answer = answer_with_benefit()
    answer["scheme"]["labeller_notes"] = {
        "not_encoded": ["You must be a citizen of India. This app does not ask about it."]
    }
    approval = prepare(make_item(answer), "octocat", today=TODAY, data_dir=data_dir)

    # One list, in the version families read; not a second copy in the labeller's notes.
    assert approval.seed["version"]["not_checked_en"] == [
        "You must be a citizen of India. This app does not ask about it."
    ]
    assert "not_encoded" not in approval.seed["labeller_notes"]
    assert "What we did not check" in approval.body
    assert "citizen of India" in approval.body
    (data_dir / "schemes_seed" / f"{SLUG}.json").write_text(file_text(approval.seed), "utf-8")
    assert read_seed_files(data_dir).schemes[0]["version"]["not_checked_en"]  # the loader accepts


def test_no_such_conditions_means_no_section_and_no_list(data_dir: Path) -> None:
    approval = prepare(make_item(), "octocat", today=TODAY, data_dir=data_dir)

    assert "not_checked_en" not in approval.seed["version"]
    assert "What we did not check" not in approval.body


def test_rule_keys_are_written_in_the_order_a_person_writes_them(data_dir: Path) -> None:
    item = make_item()
    # What PostgreSQL's JSONB hands back: shortest key first.
    item.proposed_rules_json["version"]["rules"] = {
        "fixable": [],
        "all": [{"op": "gte", "value": 60, "field": "age"}],
    }
    rules = prepare(item, "octocat", today=TODAY, data_dir=data_dir).seed["version"]["rules"]

    assert list(rules) == ["all", "fixable"]
    assert list(rules["all"][0]) == ["field", "op", "value"]
    assert rules["all"][0] == {"field": "age", "op": "gte", "value": 60}


def test_the_models_own_verified_claims_cannot_survive(data_dir: Path) -> None:
    item = make_item()
    item.proposed_rules_json["version"]["verified_at"] = "2020-01-01"
    item.proposed_rules_json["version"]["approved_by"] = "the-model"

    version = prepare(item, "octocat", today=TODAY, data_dir=data_dir).seed["version"]

    assert (version["verified_at"], version["approved_by"]) == ("2026-11-26", "octocat")


def test_the_item_is_not_modified(data_dir: Path) -> None:
    item = make_item()
    before = copy.deepcopy(item.proposed_rules_json)
    prepare(item, "octocat", today=TODAY, data_dir=data_dir)
    assert item.proposed_rules_json == before and item.status == "pending"


# --- refusals ---------------------------------------------------------------------------------


def test_an_invalid_item_is_refused_with_the_reasons(data_dir: Path) -> None:
    item = make_item(is_valid=False, validation_errors=[{"code": "quote_not_in_source"}])
    with pytest.raises(ApproveError, match=r"did not pass validation \(quote_not_in_source\)"):
        prepare(item, "octocat", data_dir=data_dir)


@pytest.mark.parametrize("status", ["approved", "rejected"])
def test_an_item_that_is_not_pending_is_refused(status: str, data_dir: Path) -> None:
    with pytest.raises(ApproveError, match="not 'pending'"):
        prepare(make_item(status=status), "octocat", data_dir=data_dir)


@pytest.mark.parametrize(
    "approver",
    ["", "two words", "a;rm -rf", "$(id)", "-leading", "double--hyphen", "x" * 40, "ü", "a\nb"],
)
def test_an_approver_that_is_not_a_github_name_is_refused(approver: str, data_dir: Path) -> None:
    with pytest.raises(ApproveError, match="GitHub user name"):
        prepare(make_item(), approver, data_dir=data_dir)


@pytest.mark.parametrize("approver", ["octocat", "a", "Sam-A14", "x" * 39])
def test_real_github_names_are_accepted(approver: str, data_dir: Path) -> None:
    assert prepare(make_item(), approver, today=TODAY, data_dir=data_dir).slug == SLUG


def test_an_empty_proposal_is_refused(data_dir: Path) -> None:
    with pytest.raises(ApproveError, match="no readable proposal"):
        prepare(make_item(proposed_rules_json={}), "octocat", data_dir=data_dir)


def test_a_slug_that_differs_from_the_items_is_refused(data_dir: Path) -> None:
    with pytest.raises(ApproveError, match="slug"):
        prepare(make_item(scheme_slug="other-scheme"), "octocat", data_dir=data_dir)


def test_a_traversing_slug_is_refused(data_dir: Path) -> None:
    item = make_item(scheme_slug="../evil")
    item.proposed_rules_json["slug"] = "../evil"
    with pytest.raises(ApproveError, match="slug"):
        prepare(item, "octocat", data_dir=data_dir)
    assert list(data_dir.rglob("evil*")) == []


def test_benefit_text_without_a_stored_quote_is_refused(data_dir: Path) -> None:
    """An item saved before the benefit-quote check: valid then, not publishable now."""
    item = make_item(source_quotes=[q for q in make_item().source_quotes if "index" in q])
    with pytest.raises(ApproveError, match="benefit_text_en has no stored source quote"):
        prepare(item, "octocat", data_dir=data_dir)


def test_a_rule_without_a_stored_quote_is_refused(data_dir: Path) -> None:
    item = make_item()
    item.source_quotes = item.source_quotes[1:]
    with pytest.raises(ApproveError, match="rule 0 has no stored source quote"):
        prepare(item, "octocat", data_dir=data_dir)


def test_a_file_the_loader_would_refuse_is_refused_before_it_is_written(data_dir: Path) -> None:
    item = make_item()
    item.proposed_rules_json["version"]["documents"] = [
        {"code": "not_a_document", "required": True, "applies_to": "applicant"}
    ]
    with pytest.raises(ApproveError, match="would not load.*not_a_document"):
        prepare(item, "octocat", data_dir=data_dir)
    assert list((data_dir / "schemes_seed").iterdir()) == []


def test_a_category_outside_the_list_is_refused(data_dir: Path) -> None:
    item = make_item()
    item.proposed_rules_json["category"] = "helth"
    with pytest.raises(ApproveError, match="would not load"):
        prepare(item, "octocat", data_dir=data_dir)


def test_log_lines_from_model_text_cannot_start_a_workflow_command(data_dir: Path) -> None:
    item = make_item(is_valid=False, validation_errors=[{"code": "x\n::error::pwned"}])
    with pytest.raises(ApproveError) as caught:
        prepare(item, "octocat", data_dir=data_dir)
    assert "\n" not in str(caught.value)


# --- the pull request description ---------------------------------------------------------------


def test_the_description_shows_every_rule_next_to_its_quote_and_the_benefit_quote(
    data_dir: Path,
) -> None:
    body = prepare(
        make_item(),
        "octocat",
        today=TODAY,
        data_dir=data_dir,
        actor="reviewer-1",
        run_url="https://x/run/1",
    ).body

    for index, quote in enumerate(QUOTES):
        assert f"**Rule {index}**" in body and quote in body
    assert BENEFIT_QUOTE in body and BENEFIT_TEXT in body
    assert "`octocat`" in body and "`reviewer-1`" in body  # who was named, and who ran it
    assert "does not publish anything" in body and "Seed database" in body
    assert "Close and reopen" in body  # how to get the normal CI checks
    assert "+++ b/data/schemes_seed/test-scheme.json" in body  # the diff
    assert "All 4 quotes are still found word for word" in body


def test_model_text_in_the_description_cannot_break_out_of_its_code_block(data_dir: Path) -> None:
    item = make_item(model="fake\n## injected `x`")
    item.proposed_rules_json["version"]["benefit_text_en"] = BENEFIT_TEXT + " ``` @octocat"
    body = prepare(item, "octocat", today=TODAY, data_dir=data_dir).body

    assert "\n## injected" not in body
    assert "````\nThe family gets a monthly pension of Rs.1,000. ``` @octocat\n````" in body


def test_a_changed_source_file_is_called_out(data_dir: Path) -> None:
    (data_dir / "scheme_sources" / f"{SLUG}.txt").write_text(
        f"{SOURCE_URL}\nCompletely new text.", "utf-8"
    )
    body = prepare(make_item(), "octocat", today=TODAY, data_dir=data_dir).body
    assert "WARNING: 4 of 4 quotes are no longer found" in body


def test_a_missing_source_file_is_said_not_hidden(data_dir: Path) -> None:
    (data_dir / "scheme_sources" / f"{SLUG}.txt").unlink()
    body = prepare(make_item(), "octocat", today=TODAY, data_dir=data_dir).body
    assert "were not re-checked" in body


def test_no_benefit_text_is_said_plainly(data_dir: Path) -> None:
    body = prepare(make_item(good_answer()), "octocat", today=TODAY, data_dir=data_dir).body
    assert "did not state what the family receives" in body


def test_an_existing_seed_file_gives_a_real_diff(data_dir: Path) -> None:
    first = prepare(make_item(), "octocat", today=TODAY, data_dir=data_dir)
    (data_dir / "schemes_seed" / f"{SLUG}.json").write_text(file_text(first.seed), "utf-8")

    changed = make_item()
    changed.proposed_rules_json["version"]["rules"]["all"][0]["value"] = 65
    body = prepare(changed, "octocat", today=TODAY, data_dir=data_dir).body

    assert f"--- a/data/schemes_seed/{SLUG}.json" in body
    assert re.search(r'^-\s+"value": 60$', body, re.M)
    assert re.search(r'^\+\s+"value": 65$', body, re.M)


def test_a_huge_description_is_cut_below_githubs_limit(data_dir: Path) -> None:
    item = make_item()
    item.proposed_rules_json["labeller_notes"] = {"not_encoded": ["x" * 290] * 400}
    body = prepare(item, "octocat", today=TODAY, data_dir=data_dir).body
    assert len(body) < 65_000


# --- end to end, against PostgreSQL --------------------------------------------------------------


def run(
    monkeypatch: pytest.MonkeyPatch,
    db: Session,
    data_dir: Path,
    item_id: int,
    approver: str = "octocat",
) -> int:
    monkeypatch.setattr(approve, "new_session", lambda: contextlib.nullcontext(db))
    argv = [
        str(item_id),
        "--approver",
        approver,
        "--body-file",
        str(data_dir / "body.md"),
        "--data-dir",
        str(data_dir),
    ]
    return approve.main(argv)


def test_the_command_writes_the_file_and_changes_nothing_in_the_database(
    monkeypatch: pytest.MonkeyPatch, db: Session, data_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    item = save_proposal(db, extract(SOURCE, FakeLLM(response=answer_text(answer_with_benefit()))))

    code = run(monkeypatch, db, data_dir, item.id)

    assert code == 0
    assert capsys.readouterr().out == f"{SLUG}\n"  # the workflow reads the slug from stdout
    written = json.loads((data_dir / "schemes_seed" / f"{SLUG}.json").read_text("utf-8"))
    assert written["version"]["approved_by"] == "octocat"
    assert "Rule 0" in (data_dir / "body.md").read_text("utf-8")
    db.refresh(item)
    assert item.status == "pending" and item.reviewed_by is None  # a person approves in the PR
    assert db.scalar(select(func.count()).select_from(Scheme)) == 0
    assert db.scalar(select(func.count()).select_from(SchemeVersion)) == 0


def test_the_command_refuses_a_flagged_or_missing_item_and_writes_nothing(
    monkeypatch: pytest.MonkeyPatch, db: Session, data_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = copy.deepcopy(answer_with_benefit())
    del bad["benefit_quote"]  # flagged: benefit_unquoted
    flagged = save_proposal(db, extract(SOURCE, FakeLLM(response=json.dumps(bad))))

    assert run(monkeypatch, db, data_dir, flagged.id) == 1
    assert "did not pass validation (benefit_unquoted)" in capsys.readouterr().err
    assert run(monkeypatch, db, data_dir, 999_999) == 1
    assert "there is no review item 999999" in capsys.readouterr().err
    assert list((data_dir / "schemes_seed").iterdir()) == []
    assert not (data_dir / "body.md").exists()
