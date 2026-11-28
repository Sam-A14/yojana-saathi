"""The family's "What's new" list: GET it, mark one read, mark all read.

The alerts are made by the daily job (app/alerts/daily.py); nothing here makes or changes the news.
An alert belongs to the family's user, so a family can only ever read and mark its own.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update

from app.api.deps import DbSession, Now, OwnHousehold
from app.db.models import Alert

router = APIRouter(prefix="/households", tags=["alerts"])

# The newest news is what matters; a long list is not a better product. Old rows stay in the table.
LIST_LIMIT = 50


class AlertOut(BaseModel):
    id: int
    # "new_scheme", "age_threshold" or "rule_change". The wording is the web app's, built from the
    # payload, so Hindi and English both work.
    type: str
    payload: dict[str, Any]
    created_at: datetime
    read: bool


class AlertsOut(BaseModel):
    unread: int
    alerts: list[AlertOut]


def _out(alert: Alert) -> AlertOut:
    return AlertOut(
        id=alert.id,
        type=alert.type,
        payload=alert.payload_json,
        created_at=alert.created_at,
        read=alert.read_at is not None,
    )


@router.get("/{household_id}/alerts", response_model=AlertsOut)
def list_alerts(household: OwnHousehold, db: DbSession) -> AlertsOut:
    rows = list(
        db.scalars(
            select(Alert)
            .where(Alert.user_id == household.user_id)
            .order_by(Alert.created_at.desc(), Alert.id.desc())
            .limit(LIST_LIMIT)
        )
    )
    unread = sum(1 for a in rows if a.read_at is None)
    return AlertsOut(unread=unread, alerts=[_out(a) for a in rows])


@router.post("/{household_id}/alerts/read-all", response_model=AlertsOut)
def mark_all_read(household: OwnHousehold, db: DbSession, now: Now) -> AlertsOut:
    db.execute(
        update(Alert)
        .where(Alert.user_id == household.user_id, Alert.read_at.is_(None))
        .values(read_at=now)
    )
    db.commit()
    return list_alerts(household, db)


@router.post("/{household_id}/alerts/{alert_id}/read", response_model=AlertOut)
def mark_read(alert_id: int, household: OwnHousehold, db: DbSession, now: Now) -> AlertOut:
    alert = db.scalars(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == household.user_id)
    ).one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="No such alert.")
    if alert.read_at is None:  # marking twice keeps the first time
        alert.read_at = now
        db.commit()
    return _out(alert)
