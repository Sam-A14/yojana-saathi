"""Run one extraction:  python -m app.pipeline.extract_cli <slug>

Reads data/scheme_sources/<slug>.txt, asks the LLM for a proposal, validates it, saves it to
review_items (status pending) and prints a Markdown report on stdout. Needs DATABASE_URL and, for
the real provider, LLM_API_KEY.

Exit code 0 means "the proposal was saved", even if it was flagged invalid: a flagged proposal is
a normal result. Non-zero means something broke before it could be saved.
"""

import argparse
import sys

from sqlalchemy.exc import SQLAlchemyError

from app.db.session import new_session
from app.llm import LLMError, get_llm_client
from app.pipeline.accuracy import AccuracyError, compare_to_seed, render_accuracy, seed_path
from app.pipeline.extractor import Extraction, extract
from app.pipeline.proposals import save_proposal
from app.pipeline.report import render_report
from app.pipeline.source import SourceError, read_source


def _accuracy_text(extraction: Extraction) -> str | None:
    slug = extraction.source.slug
    if not seed_path(slug).is_file():
        return None  # nothing hand-labelled to compare with
    scheme = extraction.validation.scheme
    if scheme is None:
        return "Not computed: the answer had no readable scheme."
    try:
        result = compare_to_seed(slug, scheme)
    except AccuracyError as error:
        return f"Not computed: {error}"
    return None if result is None else render_accuracy([result])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract rules for one scheme into review_items.")
    parser.add_argument("slug")
    args = parser.parse_args(argv)

    try:
        source = read_source(args.slug)
        extraction = extract(source, get_llm_client())
    except (SourceError, LLMError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    # Save before printing so the report can name the review item. If saving fails the report is
    # still printed: the paid-for model answer must not be lost along with the database error.
    exit_code = 0
    try:
        with new_session() as session:
            item_id = save_proposal(session, extraction).id  # read before the session closes
            session.commit()
        saved_note = f"Saved as review item #{item_id} (status: pending)"
    except (SQLAlchemyError, RuntimeError) as error:
        saved_note = f"NOT SAVED: {type(error).__name__}"
        print(f"error: could not save the proposal: {error}", file=sys.stderr)
        exit_code = 1

    print(render_report(extraction, saved_note, _accuracy_text(extraction)))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
