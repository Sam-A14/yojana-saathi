"""The small steps of the "Add scheme" workflow that are easier to test as Python than as shell.

    python -m app.pipeline.add_scheme write-source <slug>        (text comes from $SOURCE_TEXT)
    python -m app.pipeline.add_scheme issue-body <result.json>   (Markdown for the problems issue)
    python -m app.pipeline.add_scheme pr-notice --actor <name> --slug <slug>  (top of the PR)

The workflow itself (.github/workflows/add-scheme.yml) is the glue: write the source file, extract,
and either open an issue with the problems or approve and open one pull request. All three commands
print to stdout or write a file; every refusal goes to stderr with exit code 1 and nothing written.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from app.db.seed import DEFAULT_DATA_DIR
from app.pipeline.report import _fence
from app.pipeline.source import MAX_SOURCE_CHARS, SLUG_PATTERN, SourceError, read_source

# GitHub accepts at most about 65,000 characters in all the inputs of one workflow run.
MAX_INPUT_CHARS = min(MAX_SOURCE_CHARS, 60_000)


class AddSchemeError(Exception):
    """This request cannot be started. The message says why, in one line."""


def write_source(
    slug: str, text: str, data_dir: Path = DEFAULT_DATA_DIR, bump_version: bool = False
) -> Path:
    """Save the pasted page as data/scheme_sources/<slug>.txt, exactly as given (line breaks made
    uniform, one newline at the end).

    Refuses a slug that is already a scheme: data/schemes_seed/<slug>.json is hand-labelled ground
    truth and this flow adds, it does not overwrite. The one way to replace it is `bump_version`
    (the workflow's tick box), the same guard as the Approve workflow: the old files stay in git
    history and Seed database adds a new version of the scheme. `bump_version` for a slug that does
    not exist is refused too, so a typo cannot start a "replacement" of nothing."""
    if not SLUG_PATTERN.fullmatch(slug):
        raise AddSchemeError(f"'{slug}' is not a valid slug (lowercase words joined by '-').")
    if len(text) > MAX_INPUT_CHARS:
        raise AddSchemeError(f"The text is longer than {MAX_INPUT_CHARS} characters.")
    source = data_dir / "scheme_sources" / f"{slug}.txt"
    seed = data_dir / "schemes_seed" / f"{slug}.json"
    if bump_version and not seed.exists():
        raise AddSchemeError(
            f"bump_version is set but '{slug}' is not a scheme yet, so there is nothing to "
            "replace. Run again with bump_version off."
        )
    if seed.exists() and not bump_version:
        raise AddSchemeError(
            f"'{slug}' already exists in data/ (data/schemes_seed/{slug}.json is hand-labelled "
            "ground truth). Use a new slug, or tick bump_version to propose replacing it."
        )
    if source.exists() and not seed.exists():
        raise AddSchemeError(
            f"'{slug}' already exists in data/ (a source file is there). Use a new slug, or change "
            "it by hand in a pull request."
        )
    clean = text.replace("\r\n", "\n").replace("\r", "\n").strip("\n") + "\n"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(clean, encoding="utf-8")
    try:
        read_source(slug, data_dir)  # line 1 must be the URL, and there must be text after it
    except SourceError as error:
        source.unlink()
        raise AddSchemeError(str(error)) from error
    return source


def issue_body(result: dict[str, Any], run_url: str | None) -> str:
    """The text of the GitHub issue for a proposal that failed validation. The problems contain
    model text, so they sit in a code fence that the text cannot close."""
    slug = str(result.get("slug"))
    problems = result.get("problems") or []
    lines = [
        f"The extraction for `{slug}` was saved (review item {result.get('review_item_id')}) but "
        f"it **failed validation** with {len(problems)} problem(s). No pull request was opened "
        "and nothing was published.",
        "",
    ]
    if run_url:
        lines += [f"Run: {run_url}", ""]
    lines += ["### Problems", ""]
    for problem in problems:
        entry = f"{problem.get('code')} at {problem.get('where')}: {problem.get('message')}"
        lines.append(_fence(" ".join(entry.split())))
    lines += [
        "",
        "### What to do",
        "- A problem about a **quote** or **section** usually means the source page text does not "
        "say the condition in Details, Eligibility or Exclusions: add that rule by hand later, "
        "or accept that it is not encoded.",
        "- A problem about a **value** (for example `obc`) means the model did not follow the "
        "prompt. Do not loosen the validator; run **Add scheme** again only if the cause is "
        "chance, not a pattern. There is no automatic retry.",
        "- Fix the source text or the prompt, then start **Add scheme** again with a new slug "
        "(the source file was not committed, so the same slug is free).",
    ]
    return "\n".join(lines) + "\n"


# GitHub refuses a pull request description over 65,536 characters; the fetched text is cut well
# below that so the rest of the description always fits.
MAX_SHOWN_SOURCE_CHARS = 40_000


def fetched_section(page_url: str, source_text: str) -> str:
    """The page text a robot fetched, shown in the pull request so a person can compare it with the
    page before merging. Inside a code fence the text cannot close, and a collapsible block so it
    does not push the review down."""
    shown = source_text.strip("\n")
    cut = len(shown) > MAX_SHOWN_SOURCE_CHARS
    if cut:
        shown = shown[:MAX_SHOWN_SOURCE_CHARS]
    return "\n".join(
        [
            "## The fetched source text: compare it with the page before merging",
            "",
            f"This text was **read from {page_url} by a program**, not pasted by a person. The "
            "quotes behind every rule and the benefit text come from it word for word. Open the "
            "page and check that it says the same, tab by tab, and that nothing is missing.",
            "",
            "<details><summary>Show the fetched text</summary>",
            "",
            _fence(shown),
            *(
                [
                    "",
                    f"*(Cut after {MAX_SHOWN_SOURCE_CHARS:,} characters; the whole file is in the "
                    "pull request's changes.)*",
                ]
                if cut
                else []
            ),
            "",
            "</details>",
            "",
            "---",
            "",
        ]
    )


def pr_notice(
    actor: str,
    slug: str,
    run_url: str | None,
    fetched_from: str | None = None,
    source_text: str | None = None,
    replaces: bool = False,
) -> str:
    """The paragraph that starts a pull request opened by the "Add scheme" workflow. When the page
    was fetched by the workflow (not pasted), it also shows the fetched text."""
    where = f" ([run]({run_url}))" if run_url else ""
    fetched = fetched_section(fetched_from, source_text or "") if fetched_from is not None else ""
    notice = "\n".join(
        [
            f"## Added by the Add scheme workflow{where}",
            "",
            f"- The run was started by `{actor}`, so `approved_by` in the file is `{actor}`. "
            'It was set **before anyone read this pull request**: it means "this person asked for '
            'it", not "this person checked it".',
            "- **Nothing here has been compared with the official page by a person. Merging is the "
            "verification.** Read the diff and every Hindi line against "
            "`docs/scheme-review-checklist.md` first.",
            f"- This pull request contains the source file `data/scheme_sources/{slug}.txt` as "
            "well as the seed file, so it is the only merge needed.",
            "- When you merge, **Seed database** runs by itself and families see the scheme.",
            *(
                [
                    f"- **bump_version was set: this REPLACES the existing "
                    f"`data/schemes_seed/{slug}.json` and `data/scheme_sources/{slug}.txt`.** The "
                    "old files stay in git history, their hand-written `labeller_notes` are "
                    "replaced too, and Seed database adds a new version of the scheme. Read the "
                    "diff for what changed."
                ]
                if replaces
                else []
            ),
            "",
            "---",
            "",
        ]
    )
    return notice + fetched


def _run_url() -> str | None:
    server, repo, run = (
        os.environ.get(k) for k in ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID")
    )
    return f"{server}/{repo}/actions/runs/{run}" if server and repo and run else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Steps of the Add scheme workflow.")
    commands = parser.add_subparsers(dest="command", required=True)
    write = commands.add_parser("write-source")
    write.add_argument("slug")
    write.add_argument("--from-file", type=Path, help="read the page text from this file")
    write.add_argument(
        "--bump-version", action="store_true", help="replace an existing scheme on purpose"
    )
    issue = commands.add_parser("issue-body")
    issue.add_argument("result_file", type=Path)
    notice = commands.add_parser("pr-notice")
    notice.add_argument("--actor", required=True)
    notice.add_argument("--slug", required=True)
    notice.add_argument("--fetched-from", help="the page address, when the workflow fetched it")
    notice.add_argument("--bump-version", action="store_true", help="the run replaces a scheme")
    args = parser.parse_args(argv)

    try:
        if args.command == "write-source":
            text = (
                args.from_file.read_text(encoding="utf-8")
                if args.from_file
                else os.environ.get("SOURCE_TEXT", "")
            )
            # Only passed when set, so the common call stays exactly write_source(slug, text).
            write_source(args.slug, text, **({"bump_version": True} if args.bump_version else {}))
        elif args.command == "issue-body":
            result = json.loads(args.result_file.read_text(encoding="utf-8"))
            sys.stdout.write(issue_body(result, _run_url()))
        else:
            source = None
            if args.fetched_from:  # show exactly what was saved for this scheme
                path = DEFAULT_DATA_DIR / "scheme_sources" / f"{args.slug}.txt"
                source = path.read_text(encoding="utf-8")
            sys.stdout.write(
                pr_notice(
                    args.actor,
                    args.slug,
                    _run_url(),
                    args.fetched_from,
                    source,
                    replaces=args.bump_version,
                )
            )
    except (AddSchemeError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
