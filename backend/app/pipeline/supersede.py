"""Close old pending review items that a newer proposal or a merged pull request replaced.

    python -m app.pipeline.supersede 2 3 4 --by <github-name>

A review item is a proposal waiting for a person. Once the scheme went in another way (a later
item, or a hand-made seed file), the old item only clutters the list. There is no "superseded"
status (a migration for a label is not worth it), so the item is set to "rejected" and
`reviewed_by` says why: "superseded by <name>". Only items that are still "pending" are touched;
an approved, rejected or missing id is reported and skipped, never changed. Prints one line per id.
"""

import argparse
import re
import sys
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import ReviewItem
from app.db.session import new_session

# Same rule as the approver name in approve.py: it ends up in the database.
NAME_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")


def supersede(db: Session, ids: list[int], by: str, now: datetime) -> list[str]:
    """Rejects each pending item in `ids`. Returns one report line per id, in the order given."""
    lines: list[str] = []
    for item_id in dict.fromkeys(ids):  # a repeated id is done once
        item = db.get(ReviewItem, item_id)
        if item is None:
            lines.append(f"#{item_id}: no such review item, skipped")
        elif item.status != "pending":
            lines.append(f"#{item_id}: already {item.status}, left as it is")
        else:
            item.status = "rejected"
            item.reviewed_by = f"superseded by {by}"
            item.reviewed_at = now
            lines.append(f"#{item_id}: superseded ({item.scheme_slug or 'no slug'})")
    db.flush()
    return lines


def parse_ids(text: list[str]) -> list[int]:
    """Ids as typed in the workflow box: "2, 3 4" or "2,3,4"."""
    words = re.split(r"[\s,]+", " ".join(text).strip())
    if not words or words == [""] or not all(w.isdigit() for w in words):
        raise ValueError("Give review item numbers like: 2 3 4 or 2,3,4")
    return [int(w) for w in words]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mark old pending review items as superseded.")
    parser.add_argument("ids", nargs="+", help="review item numbers, spaces or commas between")
    parser.add_argument("--by", required=True, help="the GitHub name of the person asking")
    args = parser.parse_args(argv)
    if not NAME_PATTERN.fullmatch(args.by):
        print("error: --by must be a GitHub user name.", file=sys.stderr)
        return 1
    try:
        ids = parse_ids(args.ids)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    with new_session() as db:
        for line in supersede(db, ids, args.by, datetime.now(UTC)):
            print(line)
        db.commit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
