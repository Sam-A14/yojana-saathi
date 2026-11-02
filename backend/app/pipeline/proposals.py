"""Saving a proposal for human review. This is the pipeline's only database write."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ReviewItem, Scheme
from app.pipeline.extractor import Extraction


def save_proposal(session: Session, extraction: Extraction) -> ReviewItem:
    """Insert a review_items row with status 'pending'. Nothing here publishes anything.

    Valid and invalid proposals are both saved; is_valid and validation_errors tell them apart.
    Running the same slug twice adds a second row: each run is its own piece of evidence.
    The caller commits.
    """
    validation = extraction.validation
    scheme_id = session.scalar(select(Scheme.id).where(Scheme.slug == extraction.source.slug))
    item = ReviewItem(
        scheme_id=scheme_id,  # None when we do not have this scheme yet
        scheme_slug=extraction.source.slug,
        source_url=extraction.source.url,
        proposed_rules_json=validation.scheme or {},
        source_quotes=validation.quotes,
        is_valid=validation.is_valid,
        validation_errors=[p.as_dict() for p in validation.problems],
        raw_output=extraction.raw_output,
        model=extraction.model,
        status="pending",
    )
    session.add(item)
    session.flush()  # fills in item.id
    return item
