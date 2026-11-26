"""Turn one LLM proposal that a person has reviewed into a seed file plus a pull request text.

Run it with:  python -m app.pipeline.approve <review_item_id> --approver <github-name>
              --body-file <where to write the pull request description>

This is the "Approve scheme proposal" workflow's engine. It only READS the database. It writes
`data/schemes_seed/<slug>.json` in the working copy; the workflow then opens a pull request, and a
person merges it. Nothing reaches the database from here: the existing "Seed database" workflow
loads the file after the merge (decision 004). Prints the slug on stdout; every refusal goes to
stderr and exits 1, with nothing written.

If data/schemes_seed/<slug>.json already exists it is hand-labelled ground truth, so the command
refuses to touch it unless --bump-version is given (the workflow's bump_version input).
"""

import argparse
import copy
import difflib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app.db.models import ReviewItem
from app.db.seed import DEFAULT_DATA_DIR, _validator, schema_problems, scheme_file_problems
from app.db.session import new_session
from app.pipeline.report import _fence
from app.pipeline.source import SLUG_PATTERN, SourceError, read_source
from app.pipeline.validator import _squash
from app.rules.engine import RuleError, validate_rules

# A GitHub user name: letters, digits and single hyphens, up to 39 characters. Checked here as well
# as in the workflow, because it ends up in the data file and in a commit.
APPROVER_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")

# GitHub refuses a pull request description over 65,536 characters.
MAX_BODY_CHARS = 60_000
MAX_DIFF_CHARS = 15_000

SCHEME_KEYS = ("slug", "name_en", "name_hi", "level", "state", "category", "official_url", "status")
VERSION_KEYS = (
    "rules",
    "benefit_text_en",
    "benefit_text_hi",
    "deadline_start",
    "deadline_end",
    "source_url",
    "verified_at",
    "approved_by",
    "documents",
)


class ApproveError(Exception):
    """This proposal cannot be approved. The message says why, in one line."""


@dataclass(frozen=True)
class Approval:
    slug: str
    seed: dict[str, Any]  # the file to write
    body: str  # the pull request description


# --- reading the review item -----------------------------------------------------------------


def _one_line(text: str, limit: int = 300) -> str:
    """Model text can hold newlines (a log line that starts with '::' is a workflow command) and
    backticks (which would end a Markdown code span early), so neither is let through."""
    return " ".join(text.split())[:limit].replace("`", "'")


def _check_approvable(item: ReviewItem, approver: str) -> dict[str, Any]:
    """Refuse anything that is not a valid, still-pending proposal. Returns the proposed scheme."""
    if not APPROVER_PATTERN.fullmatch(approver):
        raise ApproveError("approver must be a GitHub user name (letters, digits and hyphens).")
    if item.status != "pending":
        raise ApproveError(f"review item {item.id} is '{item.status}', not 'pending'.")
    if not item.is_valid:
        codes = sorted({str(e.get("code")) for e in item.validation_errors if isinstance(e, dict)})
        raise ApproveError(
            f"review item {item.id} did not pass validation ({_one_line(', '.join(codes))}). "
            "Fix the source text and run Extract scheme rules again."
        )
    proposed = item.proposed_rules_json
    if not isinstance(proposed, dict) or not proposed:
        raise ApproveError(f"review item {item.id} has no readable proposal.")
    slug = proposed.get("slug")
    if not isinstance(slug, str) or not SLUG_PATTERN.fullmatch(slug) or slug != item.scheme_slug:
        raise ApproveError("the proposal's slug is missing, malformed or differs from the item's.")
    return proposed


def _quotes(item: ReviewItem) -> tuple[dict[int, str], str | None]:
    """(rule quotes by index, benefit quote). Entries that look like neither are ignored."""
    by_index: dict[int, str] = {}
    benefit: str | None = None
    for entry in item.source_quotes:
        if not isinstance(entry, dict) or not isinstance(entry.get("quote"), str):
            continue
        if isinstance(entry.get("index"), int):
            by_index[entry["index"]] = entry["quote"]
        elif entry.get("field") == "benefit_text_en":
            benefit = entry["quote"]
    return by_index, benefit


def _check_quotes_stored(
    proposed: dict[str, Any], rule_quotes: dict[int, str], benefit: str | None
) -> None:
    """Every published sentence must have its evidence next to it in the pull request."""
    version = proposed["version"]
    for index in range(len(version["rules"]["all"])):
        if index not in rule_quotes:
            raise ApproveError(f"rule {index} has no stored source quote.")
    if version.get("benefit_text_en") is not None and not benefit:
        raise ApproveError(
            "benefit_text_en has no stored source quote (the proposal predates the benefit-quote "
            "check). Run Extract scheme rules again."
        )


# --- building the file -------------------------------------------------------------------------


_KEY_ORDER = ("all", "any", "not", "any_member", "among", "fixable", "field", "op", "value")


def _tidy(node: Any) -> Any:
    """Put keys in the order a person writes them (field, op, value). The database stores JSONB,
    which returns keys shortest first ("op" before "field"); the same rule must read the same in
    every seed file. Only the order changes, never a value."""
    if isinstance(node, list):
        return [_tidy(child) for child in node]
    if isinstance(node, dict):
        rank = {key: i for i, key in enumerate(_KEY_ORDER)}
        return {k: _tidy(node[k]) for k in sorted(node, key=lambda k: rank.get(k, len(rank)))}
    return node


def build_seed_file(
    proposed: dict[str, Any], item: ReviewItem, approver: str, today: date
) -> dict[str, Any]:
    """The proposal in seed-file format, verified today by `approver`.

    verified_at and approved_by are set here and nowhere else: the extractor and its validator
    insist they are null, so a model can never verify its own work.
    """
    version = copy.deepcopy(proposed["version"])
    version["rules"] = _tidy(version["rules"])
    version["verified_at"] = today.isoformat()
    version["approved_by"] = approver
    notes: dict[str, Any] = {
        "example": False,
        "notes": [
            f"Proposed by the LLM extractor (review item {item.id}, model {item.model}), checked "
            f"by {approver} in the pull request that added this file on {today.isoformat()}. "
            "Every rule has a word-for-word source quote, shown in that pull request.",
        ],
    }
    proposed_notes = proposed.get("labeller_notes")
    if isinstance(proposed_notes, dict) and proposed_notes.get("not_encoded"):
        notes["not_encoded"] = list(proposed_notes["not_encoded"])

    seed: dict[str, Any] = {"$schema": "../scheme.schema.json", "labeller_notes": notes}
    seed.update({key: proposed[key] for key in SCHEME_KEYS if key in proposed})
    seed["version"] = {key: version[key] for key in VERSION_KEYS if key in version}
    return seed


def _problems_with(seed: dict[str, Any], data_dir: Path) -> list[str]:
    """The same checks the seed loader and CI make, run before anything is written."""
    try:
        documents = json.loads((data_dir / "documents.json").read_text(encoding="utf-8"))
        known = {d["code"] for d in documents["documents"]}
    except (OSError, ValueError, KeyError, TypeError) as error:
        return [f"cannot read documents.json: {error!r}"]
    found = schema_problems(_validator(data_dir / "scheme.schema.json"), seed)
    if not found:
        found = scheme_file_problems(seed, known, seed["slug"])
    if not found:
        try:
            validate_rules(seed["version"]["rules"])
        except RuleError as error:
            found = [f"the rules engine refuses the rules: {error}"]
    return found


# --- the pull request description ----------------------------------------------------------------


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


def _diff(old: str | None, new: str, slug: str) -> str:
    before = [] if old is None else old.splitlines()
    text = "\n".join(
        difflib.unified_diff(
            before,
            new.splitlines(),
            fromfile="/dev/null" if old is None else f"a/data/schemes_seed/{slug}.json",
            tofile=f"b/data/schemes_seed/{slug}.json",
            lineterm="",
        )
    )
    if len(text) > MAX_DIFF_CHARS:
        return text[:MAX_DIFF_CHARS] + "\n... (cut here; see the Files changed tab)"
    return text


def _quote_recheck(slug: str, quotes: list[str], data_dir: Path) -> str:
    """Are the quotes still in data/scheme_sources/<slug>.txt as it is now? The file may have been
    edited since the extraction ran, which is worth a reviewer's attention."""
    try:
        source = _squash(read_source(slug, data_dir).text)
    except SourceError:
        return (
            "data/scheme_sources/ has no file for this slug now, so the quotes were not re-checked."
        )
    missing = [q for q in quotes if _squash(q) not in source]
    if missing:
        return (
            f"WARNING: {len(missing)} of {len(quotes)} quotes are no longer found word for word in "
            "data/scheme_sources/ as it is now. The source text changed after the extraction."
        )
    return (
        f"All {len(quotes)} quotes are still found word for word in data/scheme_sources/{slug}.txt."
    )


def render_body(
    *,
    item: ReviewItem,
    seed: dict[str, Any],
    approver: str,
    diff: str,
    recheck: str,
    rule_quotes: dict[int, str],
    benefit_quote: str | None,
    actor: str | None,
    run_url: str | None,
    replaces: bool,
) -> str:
    version = seed["version"]
    lines = [
        f"## Approve scheme: {seed['slug']}",
        "",
        f"- Review item: {item.id} (model: `{_one_line(str(item.model))}`)",
        f"- Source: `{_one_line(str(item.source_url))}`",
        f"- Approver named in the workflow: `{approver}`"
        + (f" (workflow run by `{actor}`)" if actor else ""),
        f"- `verified_at` set to {version['verified_at']}; `approved_by` set to `{approver}`.",
    ]
    if run_url:
        lines.append(f"- Workflow run: {run_url}")
    if replaces:
        lines += [
            "",
            f"> **This replaces the existing `data/schemes_seed/{seed['slug']}.json`** "
            "(bump_version was set). The old file stays in git history. Its hand-written "
            "`labeller_notes` are replaced too: read the diff below. When **Seed database** runs, "
            "the loader adds a new version of the scheme if the rules, benefit text, deadlines, "
            "source or documents differ, and keeps the old version for past results "
            "(decision 004). The file has no version number of its own.",
        ]
    lines += [
        "",
        "**Merging this does not publish anything.** After the merge, run the **Seed database** "
        "workflow to load the file. Nothing here has touched the database.",
        "",
        "Pull requests opened by a workflow do not start the normal CI checks. Close and reopen "
        "this pull request to run them. The job already ran the seed-file and rule tests.",
        "",
        "### Checks made before this was opened",
        "- The review item was valid and still pending.",
        "- The file passes `scheme.schema.json`, the document list check and the rules engine.",
        f"- {recheck}",
        "",
        "### Source quotes: read each rule next to its quote",
    ]
    for index, rule in enumerate(version["rules"]["all"]):
        lines += [
            "",
            f"**Rule {index}**",
            _fence(_json(rule), "json"),
            "Quote from the source:",
            _fence(rule_quotes[index]),
        ]
    lines += ["", "### Benefit text"]
    if version.get("benefit_text_en") is None:
        lines.append("None: the source text did not state what the family receives.")
    else:
        lines += [
            _fence(str(version["benefit_text_en"])),
            "Quote from the source:",
            _fence(str(benefit_quote)),
        ]
    if version.get("benefit_text_hi"):
        lines += [
            "",
            "Hindi text (a translation; have a native speaker check it):",
            _fence(str(version["benefit_text_hi"])),
        ]
    not_encoded = seed["labeller_notes"].get("not_encoded")
    if not_encoded:
        lines += [
            "",
            "### Conditions the rule fields could not express",
            *[f"- `{_one_line(n)}`" for n in not_encoded],
        ]
    lines += ["", "### The file", _fence(diff, "diff"), ""]
    lines += [
        "### Review checklist",
        "- [ ] Each rule says what its quote says, including exceptions.",
        "- [ ] The benefit text says no more than its quote.",
        "- [ ] Documents and `fixable` fields make sense.",
        "- [ ] No test profile covers this scheme yet (`data/test_profiles/`).",
    ]
    body = "\n".join(lines)
    if len(body) > MAX_BODY_CHARS:
        body = body[:MAX_BODY_CHARS] + "\n\n... (cut: the description was too long for GitHub)"
    return body


# --- the whole step ------------------------------------------------------------------------------


def prepare(
    item: ReviewItem,
    approver: str,
    *,
    today: date | None = None,
    data_dir: Path = DEFAULT_DATA_DIR,
    actor: str | None = None,
    run_url: str | None = None,
    bump_version: bool = False,
) -> Approval:
    """Check the item and build the file and the description. Writes nothing."""
    proposed = _check_approvable(item, approver)
    slug = proposed["slug"]
    path = data_dir / "schemes_seed" / f"{slug}.json"
    replaces = path.exists()
    if replaces and not bump_version:
        raise ApproveError(
            f"seed exists; this would overwrite hand-labelled ground truth "
            f"(data/schemes_seed/{slug}.json). To propose a new version of it, run again with "
            "bump_version set to true; the old file stays in git history."
        )
    rule_quotes, benefit_quote = _quotes(item)
    seed = build_seed_file(proposed, item, approver, today or datetime.now(UTC).date())
    problems = _problems_with(seed, data_dir)
    if problems:
        raise ApproveError("the file would not load: " + _one_line("; ".join(problems)))
    _check_quotes_stored(seed, rule_quotes, benefit_quote)

    old = path.read_text(encoding="utf-8") if path.is_file() else None
    new_text = file_text(seed)
    all_quotes = [*rule_quotes.values(), *([benefit_quote] if benefit_quote else [])]
    body = render_body(
        item=item,
        seed=seed,
        approver=approver,
        diff=_diff(old, new_text, slug),
        recheck=_quote_recheck(slug, all_quotes, data_dir),
        rule_quotes=rule_quotes,
        benefit_quote=benefit_quote,
        actor=actor,
        run_url=run_url,
        replaces=replaces,
    )
    return Approval(slug=slug, seed=seed, body=body)


def file_text(seed: dict[str, Any]) -> str:
    """The file as written: two-space indent, Hindi left readable, one newline at the end."""
    return json.dumps(seed, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a seed file from a reviewed proposal.")
    parser.add_argument("review_item_id", type=int)
    parser.add_argument("--approver", required=True)
    parser.add_argument("--body-file", type=Path, required=True)
    parser.add_argument(
        "--bump-version",
        action="store_true",
        help="allow replacing an existing seed file (the loader then adds a new scheme version)",
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    server, repo, run = (
        os.environ.get(k) for k in ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID")
    )
    run_url = f"{server}/{repo}/actions/runs/{run}" if server and repo and run else None
    try:
        with new_session() as session:  # read only: nothing here writes or commits
            item = session.get(ReviewItem, args.review_item_id)
            if item is None:
                raise ApproveError(f"there is no review item {args.review_item_id}.")
            approval = prepare(
                item,
                args.approver,
                data_dir=args.data_dir,
                actor=os.environ.get("GITHUB_ACTOR"),
                run_url=run_url,
                bump_version=args.bump_version,
            )
    except ApproveError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except SQLAlchemyError as error:
        print(f"error: database problem: {type(error).__name__}", file=sys.stderr)
        return 1

    target = args.data_dir / "schemes_seed" / f"{approval.slug}.json"
    target.write_text(file_text(approval.seed), encoding="utf-8")
    args.body_file.write_text(approval.body, encoding="utf-8")
    print(approval.slug)
    return 0


if __name__ == "__main__":
    sys.exit(main())
