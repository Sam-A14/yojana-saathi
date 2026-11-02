"""Seed loader: validate data/ files, then load documents and schemes into the database.

Run it with:  python -m app.db.seed          (needs DATABASE_URL)

Safe to run twice. Documents and schemes are matched by their stable names (code, slug) and only
changed when the file differs. A scheme's rules are never edited in place: if the rules, benefit
text, deadlines, source or document list change, a NEW version is added and made current, because
eligibility results point at version ids. Changing only verified_at or approved_by updates the
current version in place (nothing about eligibility changed).

Everything is validated before the first database write, so a typo in one file loads nothing.
"""

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError, best_match
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import Document, Scheme, SchemeDocument, SchemeVersion
from app.db.session import new_session

# backend/app/db/seed.py -> repository root is three folders up from this file's folder.
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data"
TEMPLATE_NAME = "TEMPLATE.json"
DEFAULT_APPROVER = "seed"

DOCUMENT_FIELDS = ("name_en", "name_hi", "how_to_get_en", "how_to_get_hi", "official_link")
SCHEME_FIELDS = ("name_en", "name_hi", "level", "state", "category", "official_url", "status")


class SeedError(Exception):
    """The data files are wrong. Carries every problem found, not just the first."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("\n".join(problems))
        self.problems = problems


@dataclass
class SeedData:
    documents: list[dict[str, Any]]
    schemes: list[dict[str, Any]]


@dataclass
class SeedSummary:
    # (kind, key, action, detail): action is "created", "updated" or "unchanged".
    changes: list[tuple[str, str, str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add(self, kind: str, key: str, action: str, detail: str = "") -> None:
        self.changes.append((kind, key, action, detail))

    def count(self, kind: str, action: str) -> int:
        return sum(1 for k, _, a, _ in self.changes if k == kind and a == action)

    def render(self) -> str:
        lines = []
        for kind in ("document", "scheme", "version"):
            counts = Counter(a for k, _, a, _ in self.changes if k == kind)
            lines.append(
                f"{kind.capitalize()}s: {counts['created']} created, "
                f"{counts['updated']} updated, {counts['unchanged']} unchanged"
            )
        lines.append("")
        for kind, key, action, detail in self.changes:
            if action != "unchanged":
                lines.append(f"  {action:<8} {kind} {key}" + (f" ({detail})" if detail else ""))
        if all(a == "unchanged" for _, _, a, _ in self.changes):
            lines.append("  Nothing changed: the database already matches the files.")
        lines.extend(f"  WARNING: {w}" for w in self.warnings)
        return "\n".join(lines)


# --- reading and validating files ----------------------------------------------------------


def _validator(schema_path: Path) -> Draft202012Validator:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def _explain(error: ValidationError) -> str:
    # For "one of" rules the top-level message is unhelpful; the best inner error names the typo.
    if error.context:
        error = best_match(error.context) or error
    where = "/".join(str(p) for p in error.absolute_path) or "(top level)"
    return f"{where}: {error.message}"


def schema_problems(validator: Draft202012Validator, data: Any) -> list[str]:
    return [_explain(e) for e in sorted(validator.iter_errors(data), key=lambda e: list(e.path))]


def _read_json(path: Path, problems: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        problems.append(f"{path.name}: cannot read as JSON ({error})")
        return None


def _read_documents(data_dir: Path, problems: list[str]) -> list[dict[str, Any]]:
    path = data_dir / "documents.json"
    content = _read_json(path, problems)
    if content is None:
        return []
    found = schema_problems(_validator(data_dir / "documents.schema.json"), content)
    if found:
        problems.extend(f"documents.json: {p}" for p in found)
        return []
    codes = [d["code"] for d in content["documents"]]
    for code in sorted({c for c in codes if codes.count(c) > 1}):
        problems.append(f"documents.json: code '{code}' appears more than once")
    return list(content["documents"])


def scheme_file_problems(
    data: dict[str, Any], known_codes: set[str], file_stem: str | None
) -> list[str]:
    """Checks a JSON Schema cannot express: file name, deadlines, document references."""
    problems = []
    if file_stem is not None and data["slug"] != file_stem:
        problems.append(f"slug '{data['slug']}' must equal the file name '{file_stem}'")
    version = data["version"]
    start, end = version.get("deadline_start"), version.get("deadline_end")
    if start and end and date.fromisoformat(end) < date.fromisoformat(start):
        problems.append("deadline_end is before deadline_start")
    codes = [d["code"] for d in version["documents"]]
    for code in sorted(set(codes) - known_codes):
        problems.append(f"document '{code}' is not in documents.json")
    for code in sorted({c for c in codes if codes.count(c) > 1}):
        problems.append(f"document '{code}' is listed twice")
    return problems


def read_seed_files(data_dir: Path = DEFAULT_DATA_DIR) -> SeedData:
    problems: list[str] = []
    documents = _read_documents(data_dir, problems)
    known_codes = {d["code"] for d in documents}
    validator = _validator(data_dir / "scheme.schema.json")

    schemes: list[dict[str, Any]] = []
    seen_slugs: dict[str, str] = {}
    for path in sorted((data_dir / "schemes_seed").glob("*.json")):
        if path.name == TEMPLATE_NAME:
            continue  # a template to copy from, never loaded
        data = _read_json(path, problems)
        if data is None:
            continue
        found = schema_problems(validator, data)
        if not found:
            found = scheme_file_problems(data, known_codes, path.stem)
        problems.extend(f"{path.name}: {p}" for p in found)
        if found:
            continue
        if data["slug"] in seen_slugs:
            problems.append(
                f"{path.name}: slug '{data['slug']}' already used by {seen_slugs[data['slug']]}"
            )
        seen_slugs[data["slug"]] = path.name
        schemes.append(data)

    if problems:
        raise SeedError(problems)
    return SeedData(documents=documents, schemes=schemes)


# --- writing to the database ---------------------------------------------------------------


def _to_datetime(day: str | None) -> datetime | None:
    # The files hold a date; the column holds a moment. Midnight UTC is a fixed, honest choice.
    return datetime.combine(date.fromisoformat(day), time.min, tzinfo=UTC) if day else None


def _to_date(day: str | None) -> date | None:
    return date.fromisoformat(day) if day else None


def _document_links(items: list[dict[str, Any]]) -> list[tuple[str, bool, str]]:
    links = [(d["code"], d.get("required", True), d.get("applies_to", "applicant")) for d in items]
    return sorted(links)


def _material_from_file(version: dict[str, Any]) -> dict[str, Any]:
    """The parts of a version that affect eligibility or what the user is shown."""
    return {
        "rules_json": version["rules"],
        "benefit_text_en": version.get("benefit_text_en"),
        "benefit_text_hi": version.get("benefit_text_hi"),
        "deadline_start": _to_date(version.get("deadline_start")),
        "deadline_end": _to_date(version.get("deadline_end")),
        "source_url": version["source_url"],
        "documents": _document_links(version["documents"]),
    }


def _material_from_row(row: SchemeVersion) -> dict[str, Any]:
    return {
        "rules_json": row.rules_json,
        "benefit_text_en": row.benefit_text_en,
        "benefit_text_hi": row.benefit_text_hi,
        "deadline_start": row.deadline_start,
        "deadline_end": row.deadline_end,
        "source_url": row.source_url,
        "documents": sorted((d.document_code, d.required, d.applies_to) for d in row.documents),
    }


def _upsert_documents(session: Session, items: list[dict[str, Any]], summary: SeedSummary) -> None:
    existing = {d.code: d for d in session.scalars(select(Document))}
    for item in items:
        values = {name: item.get(name) for name in DOCUMENT_FIELDS}
        row = existing.get(item["code"])
        if row is None:
            session.add(Document(code=item["code"], **values))
            summary.add("document", item["code"], "created")
            continue
        changed = [name for name, value in values.items() if getattr(row, name) != value]
        for name in changed:
            setattr(row, name, values[name])
        summary.add(
            "document", item["code"], "updated" if changed else "unchanged", ", ".join(changed)
        )
    missing = sorted(set(existing) - {i["code"] for i in items})
    if missing:
        # Never deleted automatically: members or schemes may still refer to them.
        summary.warnings.append(f"in the database but not in documents.json: {', '.join(missing)}")
    session.flush()


def _upsert_scheme(session: Session, item: dict[str, Any], summary: SeedSummary) -> Scheme:
    values = {name: item.get(name) for name in SCHEME_FIELDS}
    values["status"] = item.get("status", "active")
    scheme = session.scalars(select(Scheme).where(Scheme.slug == item["slug"])).one_or_none()
    if scheme is None:
        scheme = Scheme(slug=item["slug"], **values)
        session.add(scheme)
        summary.add("scheme", item["slug"], "created")
        return scheme
    changed = [name for name, value in values.items() if getattr(scheme, name) != value]
    for name in changed:
        setattr(scheme, name, values[name])
    summary.add("scheme", item["slug"], "updated" if changed else "unchanged", ", ".join(changed))
    return scheme


def _add_version(scheme: Scheme, version: dict[str, Any]) -> SchemeVersion:
    material = _material_from_file(version)
    links = material.pop("documents")
    number = max((v.version_no for v in scheme.versions), default=0) + 1
    row = SchemeVersion(
        scheme=scheme,
        version_no=number,
        verified_at=_to_datetime(version.get("verified_at")),
        approved_by=version.get("approved_by") or DEFAULT_APPROVER,
        **material,
    )
    row.documents = [
        SchemeDocument(document_code=code, required=required, applies_to=applies_to)
        for code, required, applies_to in links
    ]
    scheme.current_version = row
    return row


def _sync_version(
    session: Session, scheme: Scheme, item: dict[str, Any], summary: SeedSummary
) -> None:
    slug, incoming = item["slug"], item["version"]
    current = scheme.current_version
    if current is None:
        row = _add_version(scheme, incoming)
        summary.add("version", slug, "created", f"version {row.version_no}")
    elif _material_from_row(current) != _material_from_file(incoming):
        row = _add_version(scheme, incoming)
        summary.add(
            "version", slug, "created", f"version {row.version_no}, rules or content changed"
        )
    else:
        verified_at = _to_datetime(incoming.get("verified_at"))
        approved_by = incoming.get("approved_by") or DEFAULT_APPROVER
        if (current.verified_at, current.approved_by) != (verified_at, approved_by):
            current.verified_at, current.approved_by = verified_at, approved_by
            summary.add(
                "version", slug, "updated", f"version {current.version_no}, verification only"
            )
        else:
            summary.add("version", slug, "unchanged", f"version {current.version_no}")
    session.flush()


def apply_seed(session: Session, data: SeedData) -> SeedSummary:
    """Write the data into the session. The caller decides when to commit."""
    summary = SeedSummary()
    _upsert_documents(session, data.documents, summary)
    for item in data.schemes:
        scheme = _upsert_scheme(session, item, summary)
        _sync_version(session, scheme, item, summary)
    return summary


# --- command line --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load documents and schemes into the database.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args(argv)

    try:
        data = read_seed_files(args.data_dir)
    except SeedError as error:
        print("The data files have problems; nothing was loaded:", file=sys.stderr)
        print("\n".join(f"  - {p}" for p in error.problems), file=sys.stderr)
        return 1

    try:
        # begin() commits when the block ends, and rolls everything back if anything fails.
        with new_session() as session, session.begin():
            summary = apply_seed(session, data)
    except (RuntimeError, SQLAlchemyError) as error:
        print(f"Database problem; nothing was loaded: {error}", file=sys.stderr)
        return 1

    print(summary.render())
    return 0


if __name__ == "__main__":
    sys.exit(main())
