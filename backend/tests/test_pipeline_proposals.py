"""Saving proposals and the extraction command, against a real PostgreSQL (the `db` fixture)."""

import copy
import json
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ReviewItem, Scheme, SchemeVersion
from app.db.seed import DEFAULT_DATA_DIR
from app.llm import FakeLLM
from app.pipeline import extract_cli
from app.pipeline.extractor import extract
from app.pipeline.proposals import save_proposal
from app.pipeline.source import SourceDocument
from tests.pipeline_samples import SLUG, SOURCE_TEXT, SOURCE_URL, answer_text, good_answer

SOURCE = SourceDocument(slug=SLUG, url=SOURCE_URL, text=SOURCE_TEXT.strip())


def test_a_valid_proposal_is_saved_as_pending(db: Session) -> None:
    extraction = extract(SOURCE, FakeLLM(response=answer_text(good_answer()), model="fake-1"))
    item = save_proposal(db, extraction)

    row = db.get(ReviewItem, item.id)
    assert row is not None
    assert row.status == "pending" and row.is_valid is True
    assert row.validation_errors == []
    assert row.scheme_slug == SLUG and row.source_url == SOURCE_URL and row.model == "fake-1"
    assert row.proposed_rules_json["version"]["rules"]["all"][0]["field"] == "age"
    assert len(row.source_quotes) == 3
    assert row.scheme_id is None  # we do not have this scheme yet
    assert row.reviewed_by is None and row.reviewed_at is None


def test_an_invalid_proposal_is_kept_and_flagged(db: Session) -> None:
    bad = copy.deepcopy(good_answer())
    bad["rule_quotes"] = []
    item = save_proposal(db, extract(SOURCE, FakeLLM(response=json.dumps(bad))))

    row = db.get(ReviewItem, item.id)
    assert row is not None
    assert row.status == "pending" and row.is_valid is False
    assert [e["code"] for e in row.validation_errors] == ["missing_quote"] * 3
    assert row.proposed_rules_json["slug"] == SLUG  # the proposal itself is not thrown away


def test_unreadable_output_is_kept_as_raw_text(db: Session) -> None:
    item = save_proposal(db, extract(SOURCE, FakeLLM(response="I am sorry, no JSON today")))

    row = db.get(ReviewItem, item.id)
    assert row is not None
    assert row.is_valid is False and row.proposed_rules_json == {}
    assert row.raw_output == "I am sorry, no JSON today"
    assert row.validation_errors[0]["code"] == "not_json"


def test_the_proposal_is_linked_to_an_existing_scheme_and_publishes_nothing(db: Session) -> None:
    scheme = Scheme(
        slug=SLUG, name_en="T", level="central", category="pension", official_url="https://x.org"
    )
    db.add(scheme)
    db.flush()

    item = save_proposal(db, extract(SOURCE, FakeLLM(response=answer_text(good_answer()))))

    assert item.scheme_id == scheme.id
    assert db.scalar(select(SchemeVersion.id).where(SchemeVersion.scheme_id == scheme.id)) is None
    assert scheme.current_version_id is None


def test_running_twice_adds_a_second_pending_row(db: Session) -> None:
    for _ in range(2):
        save_proposal(db, extract(SOURCE, FakeLLM(response=answer_text(good_answer()))))
    assert len(db.scalars(select(ReviewItem).where(ReviewItem.scheme_slug == SLUG)).all()) == 2


# --- the command that the GitHub workflow runs -------------------------------------------------


def seed_scheme(slug: str) -> dict[str, Any]:
    return json.loads((DEFAULT_DATA_DIR / "schemes_seed" / f"{slug}.json").read_text("utf-8"))


def run_cli(
    monkeypatch: pytest.MonkeyPatch, db: Session, source: SourceDocument, response: str
) -> int:
    monkeypatch.setattr(extract_cli, "read_source", lambda slug: source)
    monkeypatch.setattr(extract_cli, "get_llm_client", lambda: FakeLLM(response=response))
    monkeypatch.setattr(extract_cli, "new_session", lambda: db)
    return extract_cli.main([source.slug])


def test_cli_saves_and_reports_without_a_seed_file(
    monkeypatch: pytest.MonkeyPatch, db: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    code = run_cli(monkeypatch, db, SOURCE, answer_text(good_answer()))

    out = capsys.readouterr().out
    assert code == 0
    assert "Saved as review item #" in out and "(status: pending)" in out
    assert "### Validation: passed" in out
    assert "No seed file `data/schemes_seed/test-scheme.json`" in out
    assert '"slug": "test-scheme"' in out  # the proposal is printed
    assert db.scalars(select(ReviewItem).where(ReviewItem.scheme_slug == SLUG)).one().is_valid


def test_cli_reports_accuracy_with_missed_and_extra_conditions(
    monkeypatch: pytest.MonkeyPatch, db: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    # Take the real pm-kisan labels, make the model "miss" the last rule and "invent" one more.
    scheme = seed_scheme("pm-kisan")
    scheme["version"]["verified_at"] = None
    scheme["version"]["approved_by"] = None
    rules = scheme["version"]["rules"]["all"]
    rules.pop()
    rules.append({"field": "age", "op": "gte", "value": 18})

    lines = [
        f"Condition number {i} of the scheme applies to every family." for i in range(len(rules))
    ]
    source = SourceDocument(
        slug="pm-kisan", url=scheme["version"]["source_url"], text="\n".join(lines)
    )
    answer = {
        "scheme": scheme,
        "rule_quotes": [{"index": i, "quote": line} for i, line in enumerate(lines)],
    }

    code = run_cli(monkeypatch, db, source, json.dumps(answer))

    out = capsys.readouterr().out
    assert code == 0
    assert "### Validation: passed" in out
    assert "pm-kisan: precision" in out
    assert "Missed (in the seed file, not extracted):" in out
    assert "Extra (extracted, not in the seed file):\n    - age gte 18" in out


def test_cli_keeps_and_flags_a_bad_answer_and_still_exits_zero(
    monkeypatch: pytest.MonkeyPatch, db: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    code = run_cli(monkeypatch, db, SOURCE, "not json")

    out = capsys.readouterr().out
    assert code == 0  # saved and flagged is a normal outcome
    assert "### Validation: FAILED (1 problems)" in out
    assert "Raw text:" in out and "not json" in out
    assert db.scalars(select(ReviewItem)).one().is_valid is False


def test_cli_fails_loudly_when_the_source_file_is_bad(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    code = extract_cli.main(["definitely-not-a-real-scheme"])
    assert code == 1
    assert "Cannot read" in capsys.readouterr().err


def test_cli_prints_the_proposal_even_when_the_database_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(extract_cli, "read_source", lambda slug: SOURCE)
    monkeypatch.setattr(
        extract_cli, "get_llm_client", lambda: FakeLLM(response=answer_text(good_answer()))
    )
    monkeypatch.delenv("DATABASE_URL", raising=False)

    code = extract_cli.main([SLUG])

    captured = capsys.readouterr()
    assert code == 1
    assert "NOT SAVED" in captured.out and '"slug": "test-scheme"' in captured.out
    assert "could not save" in captured.err
