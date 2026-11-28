"""Seed loader against a real PostgreSQL."""

import json
import shutil
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import seed
from app.db.models import Document, Scheme, SchemeDocument, SchemeVersion
from app.db.session import get_engine

REAL_DATA = seed.DEFAULT_DATA_DIR


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """A private copy of the real data files, so a test can edit them freely."""
    shutil.copytree(REAL_DATA, tmp_path / "data")
    return tmp_path / "data"


def edit_scheme(data_dir: Path, slug: str, change: Callable[[dict[str, Any]], None]) -> None:
    path = data_dir / "schemes_seed" / f"{slug}.json"
    content = json.loads(path.read_text(encoding="utf-8"))
    change(content)
    path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")


def load(db: Session, data_dir: Path) -> seed.SeedSummary:
    return seed.apply_seed(db, seed.read_seed_files(data_dir))


def count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def scheme(db: Session, slug: str) -> Scheme:
    return db.scalars(select(Scheme).where(Scheme.slug == slug)).one()


def committed_schemes(data_dir: Path) -> list[dict[str, Any]]:
    """The schemes in the data folder. Counted, not hard-coded: approved schemes are added to
    data/schemes_seed by pull request, so the number grows."""
    return seed.read_seed_files(data_dir).schemes


def test_first_load_creates_everything(db: Session, data_dir: Path) -> None:
    schemes = committed_schemes(data_dir)
    documents = seed.read_seed_files(data_dir).documents
    summary = load(db, data_dir)

    assert count(db, Document) == len(documents)
    assert count(db, Scheme) == len(schemes)
    assert count(db, SchemeVersion) == len(schemes)
    assert count(db, SchemeDocument) == sum(len(s["version"]["documents"]) for s in schemes)
    assert summary.count("document", "created") == len(documents)
    assert summary.count("scheme", "created") == len(schemes)
    kisan = scheme(db, "pm-kisan")
    assert kisan.current_version is not None
    assert kisan.current_version.version_no == 1
    assert kisan.current_version.verified_at is None  # examples must stay unverified
    assert kisan.current_version.approved_by == "seed-example-unverified"
    assert kisan.current_version.rules_json["fixable"] == []  # land ownership is not fixable
    assert kisan.name_hi and kisan.level == "central" and kisan.state is None


def test_running_twice_changes_nothing(db: Session, data_dir: Path) -> None:
    load(db, data_dir)
    before = (count(db, Document), count(db, Scheme), count(db, SchemeVersion))

    summary = load(db, data_dir)

    assert (count(db, Document), count(db, Scheme), count(db, SchemeVersion)) == before
    assert all(action == "unchanged" for _, _, action, _ in summary.changes)
    assert "Nothing changed" in summary.render()


def test_changed_rules_add_a_new_version_and_keep_the_old(db: Session, data_dir: Path) -> None:
    load(db, data_dir)
    old_rules = scheme(db, "ignwps").current_version.rules_json  # type: ignore[union-attr]

    def raise_age(content: dict[str, Any]) -> None:
        content["version"]["rules"]["all"][1]["value"] = [60, 79]  # the age rule (between)

    edit_scheme(data_dir, "ignwps", raise_age)
    summary = load(db, data_dir)
    db.expire_all()

    widow = scheme(db, "ignwps")
    assert [v.version_no for v in widow.versions] == [1, 2]
    assert widow.current_version is widow.versions[1]
    assert widow.versions[0].rules_json == old_rules  # history is never rewritten
    assert widow.current_version.rules_json["all"][1]["value"] == [60, 79]
    assert summary.count("version", "created") == 1
    # every other scheme is untouched
    assert summary.count("version", "unchanged") == len(committed_schemes(data_dir)) - 1


def test_switching_ignwps_from_the_bpl_card_to_is_bpl_adds_version_2_and_keeps_the_paper(
    db: Session, data_dir: Path
) -> None:
    """The committed file reads BPL from the household answer. Production already holds version 1
    (the card as a stand-in): Seed database must add version 2 and keep version 1 unchanged."""

    def as_it_was(content: dict[str, Any]) -> None:
        rules = content["version"]["rules"]["all"]
        rules[2] = {"field": "has_bpl_card", "op": "is_true"}  # the old stand-in

    current = json.loads((data_dir / "schemes_seed" / "ignwps.json").read_text("utf-8"))
    edit_scheme(data_dir, "ignwps", as_it_was)
    load(db, data_dir)  # production as it is today
    (data_dir / "schemes_seed" / "ignwps.json").write_text(
        json.dumps(current, ensure_ascii=False), encoding="utf-8"
    )

    summary = load(db, data_dir)  # the committed file
    db.expire_all()

    widow = scheme(db, "ignwps")
    assert [v.version_no for v in widow.versions] == [1, 2]
    assert widow.versions[0].rules_json["all"][2] == {"field": "has_bpl_card", "op": "is_true"}
    assert widow.current_version.rules_json["all"][2] == {"field": "is_bpl", "op": "is_true"}
    assert summary.count("version", "created") == 1
    # The card is still a required paper, so a BPL family without it is shown it as missing.
    required = {d.document_code: d.required for d in widow.current_version.documents}
    assert required["bpl_card"] is True


def test_not_checked_lines_are_stored_and_a_change_adds_a_version(
    db: Session, data_dir: Path
) -> None:
    load(db, data_dir)
    first = scheme(db, "ignoaps").current_version
    assert first is not None and len(first.not_checked_en) == 2
    for slug, lines in (("pm-kisan", 3), ("ignwps", 3)):
        version = scheme(db, slug).current_version
        assert version is not None and len(version.not_checked_en) == lines
        assert version.not_checked_hi is not None and len(version.not_checked_hi) == lines

    def reword(content: dict[str, Any]) -> None:
        content["version"]["not_checked_en"][0] = "You must be a citizen of India."
        content["version"]["not_checked_hi"] = None

    edit_scheme(data_dir, "ignoaps", reword)
    summary = load(db, data_dir)
    db.expire_all()

    versions = scheme(db, "ignoaps").versions
    assert [v.version_no for v in versions] == [1, 2]
    assert versions[0].not_checked_en[0].endswith("does not ask about it.")  # history kept
    assert versions[1].not_checked_en[0] == "You must be a citizen of India."
    assert versions[1].not_checked_hi is None
    assert summary.count("version", "created") == 1


def test_changed_document_list_adds_a_new_version(db: Session, data_dir: Path) -> None:
    load(db, data_dir)

    def add_document(content: dict[str, Any]) -> None:
        content["version"]["documents"].append({"code": "ration_card", "required": False})

    edit_scheme(data_dir, "pm-kisan", add_document)
    load(db, data_dir)
    db.expire_all()

    kisan = scheme(db, "pm-kisan")
    assert kisan.current_version.version_no == 2  # type: ignore[union-attr]
    assert len(kisan.current_version.documents) == 4  # type: ignore[union-attr]
    assert len(kisan.versions[0].documents) == 3


def test_only_verification_changes_update_in_place(db: Session, data_dir: Path) -> None:
    load(db, data_dir)

    def verify(content: dict[str, Any]) -> None:
        content["version"]["verified_at"] = "2026-11-02"
        content["version"]["approved_by"] = "owner"

    edit_scheme(data_dir, "pm-kisan", verify)
    summary = load(db, data_dir)
    db.expire_all()

    kisan = scheme(db, "pm-kisan")
    assert len(kisan.versions) == 1  # same rules, so no new version
    assert kisan.current_version.verified_at is not None  # type: ignore[union-attr]
    assert kisan.current_version.verified_at.date().isoformat() == "2026-11-02"  # type: ignore[union-attr]
    assert kisan.current_version.approved_by == "owner"  # type: ignore[union-attr]
    assert ("version", "pm-kisan", "updated", "version 1, verification only") in summary.changes


def test_scheme_and_document_text_updates_in_place(db: Session, data_dir: Path) -> None:
    load(db, data_dir)
    edit_scheme(data_dir, "pm-kisan", lambda c: c.update(name_en="PM-KISAN renamed"))
    documents_path = data_dir / "documents.json"
    content = json.loads(documents_path.read_text(encoding="utf-8"))
    content["documents"][0]["how_to_get_en"] = "Visit an Aadhaar centre."
    documents_path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")

    summary = load(db, data_dir)

    assert scheme(db, "pm-kisan").name_en == "PM-KISAN renamed"
    assert count(db, SchemeVersion) == len(committed_schemes(data_dir))  # one version per scheme
    assert db.scalars(select(Document).where(Document.code == "aadhaar_card")).one().how_to_get_en
    assert summary.count("scheme", "updated") == 1
    assert summary.count("document", "updated") == 1


def test_document_missing_from_file_is_kept_and_warned(db: Session, data_dir: Path) -> None:
    load(db, data_dir)
    in_file = len(seed.read_seed_files(data_dir).documents)
    db.add(Document(code="extra_doc", name_en="Extra", name_hi="अतिरिक्त"))
    db.flush()

    summary = load(db, data_dir)

    assert count(db, Document) == in_file + 1  # the extra one is kept
    assert any("extra_doc" in w for w in summary.warnings)


def test_main_reports_data_problems_without_touching_the_database(
    data_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    edit_scheme(data_dir, "pm-kisan", lambda c: c["version"]["documents"].append({"code": "nope"}))

    code = seed.main(["--data-dir", str(data_dir)])

    assert code == 1
    assert "'nope' is not in documents.json" in capsys.readouterr().err


def test_main_without_database_url_fails_clearly(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    get_engine.cache_clear()
    monkeypatch.chdir(REAL_DATA)  # a folder with no .env file

    code = seed.main([])

    get_settings.cache_clear()
    get_engine.cache_clear()
    assert code == 1
    assert "DATABASE_URL is not set" in capsys.readouterr().err


@pytest.fixture
def committed_database(
    engine: Engine, monkeypatch: pytest.MonkeyPatch, test_database_url: str
) -> Iterator[None]:
    """Point the app at the test database for a command that really commits, then empty it."""
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    get_settings.cache_clear()
    get_engine.cache_clear()
    yield
    get_engine.cache_clear()
    get_settings.cache_clear()
    with engine.begin() as connection:
        connection.execute(
            text("TRUNCATE scheme_documents, schemes, scheme_versions, documents CASCADE")
        )


def test_command_commits_and_is_repeatable(
    committed_database: None, engine: Engine, capsys: pytest.CaptureFixture[str]
) -> None:
    assert seed.main([]) == 0
    first = capsys.readouterr().out
    schemes = len(seed.read_seed_files().schemes)
    documents = seed.read_seed_files().documents
    assert (
        f"Documents: {len(documents)} created" in first and f"Schemes: {schemes} created" in first
    )

    assert seed.main([]) == 0
    second = capsys.readouterr().out
    assert f"Documents: 0 created, 0 updated, {len(documents)} unchanged" in second
    assert "Nothing changed" in second
    with engine.connect() as connection:  # a fresh connection sees only committed rows
        assert connection.scalar(text("SELECT count(*) FROM scheme_versions")) == schemes
