"""Closing old pending review items: only pending ones change, and nothing else is touched."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.db.models import ReviewItem
from app.pipeline.supersede import main, parse_ids, supersede

NOW = datetime(2026, 11, 28, 12, 0, tzinfo=UTC)


def item(db: Session, status: str = "pending", slug: str | None = "pm-kisan") -> ReviewItem:
    row = ReviewItem(proposed_rules_json={}, status=status, scheme_slug=slug)
    db.add(row)
    db.flush()
    return row


def test_a_pending_item_is_closed_with_the_reason_and_the_time(db: Session) -> None:
    row = item(db)

    lines = supersede(db, [row.id], "Sam-A14", NOW)

    assert lines == [f"#{row.id}: superseded (pm-kisan)"]
    assert (row.status, row.reviewed_by, row.reviewed_at) == (
        "rejected",
        "superseded by Sam-A14",
        NOW,
    )


def test_approved_and_rejected_items_are_left_exactly_as_they_were(db: Session) -> None:
    approved, rejected = item(db, "approved"), item(db, "rejected")

    lines = supersede(db, [approved.id, rejected.id], "Sam-A14", NOW)

    assert lines == [
        f"#{approved.id}: already approved, left as it is",
        f"#{rejected.id}: already rejected, left as it is",
    ]
    assert approved.reviewed_by is None and rejected.reviewed_by is None


def test_a_missing_id_is_reported_and_a_repeated_id_is_done_once(db: Session) -> None:
    row = item(db)

    lines = supersede(db, [row.id, 999999, row.id], "Sam-A14", NOW)

    assert lines == [f"#{row.id}: superseded (pm-kisan)", "#999999: no such review item, skipped"]


@pytest.mark.parametrize(
    ("typed", "ids"),
    [(["2", "3", "4"], [2, 3, 4]), (["2,3,", "4"], [2, 3, 4]), (["2, 3 4"], [2, 3, 4])],
)
def test_ids_can_be_typed_with_spaces_or_commas(typed: list[str], ids: list[int]) -> None:
    assert parse_ids(typed) == ids


@pytest.mark.parametrize("typed", [[""], ["two"], ["2;3"], ["-1"]])
def test_anything_that_is_not_a_number_is_refused(typed: list[str]) -> None:
    with pytest.raises(ValueError):
        parse_ids(typed)


def test_a_bad_name_is_refused_before_the_database_is_used(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["2", "--by", "bad name; drop"]) == 1
    assert "GitHub user name" in capsys.readouterr().err
