"""The daily job: python -m app.alerts.daily

For every family: works out what is new (detect.py), stores the alerts and today's results. Run by
the "Daily alerts" workflow. Safe to run twice in a day: each alert has a key, so none is repeated.
One family's failure is logged and skipped; it never stops the others.
"""

import logging
import sys
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alerts.detect import alerts_for_household, store_alerts
from app.api.facts import INDIA
from app.db.models import Household
from app.db.session import new_session

logger = logging.getLogger("yojana.alerts")


def run(db: Session, today: date, now: datetime) -> dict[str, int]:
    summary = {"households": 0, "new_alerts": 0, "first_time_members": 0, "failed": 0}
    for household in db.scalars(select(Household).order_by(Household.created_at)).all():
        try:
            with db.begin_nested():  # a failure rolls back this family only
                found, first_time = alerts_for_household(db, household, today)
                summary["new_alerts"] += store_alerts(db, household.user_id, found, now)
                summary["first_time_members"] += first_time
        except Exception:  # noqa: BLE001 - one family must not stop the rest
            logger.exception("Alerts failed for household %s", household.id)
            summary["failed"] += 1
        summary["households"] += 1
    return summary


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    now = datetime.now(UTC)
    today = now.astimezone(INDIA).date()  # families live in India: "today" is the Indian date
    with new_session() as db:
        summary = run(db, today, now)
        db.commit()
    for name, value in summary.items():
        print(f"{name}: {value}")
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
