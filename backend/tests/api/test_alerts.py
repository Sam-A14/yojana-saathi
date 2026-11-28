"""In-app alerts: what counts as news (detect.py), the daily job (daily.py) and the API."""

from datetime import UTC, date, datetime
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.alerts.daily import run
from app.alerts.detect import AGE_WARNING_DAYS, age_alert_due, age_thresholds
from app.db.models import Alert, EligibilityResult, Scheme, SchemeVersion
from tests.api.conftest import Family, add_scheme

NOW = datetime(2026, 11, 3, 3, 0, tzinfo=UTC)
TODAY = date(2026, 11, 3)

# A scheme that fits anyone aged 60 or more, and one that fits anyone aged 18 to 50.
OLD_AGE = {"all": [{"field": "age", "op": "gte", "value": 60}], "fixable": []}
YOUNG = {"all": [{"field": "age", "op": "between", "value": [18, 50]}], "fixable": []}


def add_member(client: TestClient, family: Family, nickname: str, birth_year: int) -> str:
    body = {"nickname": nickname, "relation": "other", "birth_year": birth_year}
    response = client.post(f"{family.url}/members", json=body, headers=family.headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def alerts_of(db: Session, family: Family, kind: str | None = None) -> list[Alert]:
    query = select(Alert).where(Alert.user_id == family.user.id).order_by(Alert.id)
    if kind:
        query = query.where(Alert.type == kind)
    return list(db.scalars(query))


# --- which ages are alerts -----------------------------------------------------------------------


def test_only_ages_where_a_scheme_starts_to_fit_are_thresholds() -> None:
    rules = {
        "all": [
            {"field": "age", "op": "gte", "value": 60},
            {"any": [{"field": "age", "op": "between", "value": [18, 50]}]},
            {"field": "age", "op": "lte", "value": 40},  # an upper limit is not good news
            {"not": {"field": "age", "op": "gte", "value": 99}},  # an exclusion
            {"any_member": {"field": "age", "op": "gte", "value": 70}},  # about other people
            {"field": "category", "op": "eq", "value": "OBC"},
        ]
    }
    assert age_thresholds(rules) == {60, 18}


def test_an_age_alert_starts_60_days_before_the_year_and_ends_with_it() -> None:
    # Born 1967, so 60 is reached during 2027. Earliest possible birthday: 1 January 2027.
    assert AGE_WARNING_DAYS == 60
    assert not age_alert_due(1967, 60, date(2026, 11, 1))  # 61 days before
    assert age_alert_due(1967, 60, date(2026, 11, 2))  # 60 days before
    assert age_alert_due(1967, 60, date(2027, 12, 31))
    assert not age_alert_due(1967, 60, date(2028, 1, 1))  # that year is over: old news


# A family is "seen" once results are stored for it, so the tests that need a first look use the
# real seeded schemes (an empty catalogue stores nothing, and the next run would look first again).

# --- the daily job -------------------------------------------------------------------------------


def test_a_family_seen_for_the_first_time_gets_no_flood_of_new_schemes(
    client: TestClient, db: Session, make_family, today: date
) -> None:
    add_scheme(db, "old-age", OLD_AGE)
    family = make_family()
    add_member(client, family, "Dadi", 1960)  # 66: fits old-age today

    summary = run(db, TODAY, NOW)

    assert summary["first_time_members"] == 1 and summary["failed"] == 0
    assert alerts_of(db, family, "new_scheme") == []
    saved = db.scalars(select(EligibilityResult)).all()
    assert saved and all(row.status == "eligible" for row in saved)  # saved quietly


def test_a_scheme_that_now_fits_a_member_is_news_once(
    client: TestClient, db: Session, make_family, today: date, seeded: None
) -> None:
    family = make_family()
    add_member(client, family, "Dadi", 1960)
    run(db, TODAY, NOW)  # the first look: nothing is news
    add_scheme(db, "old-age", OLD_AGE)  # a new scheme appears that fits Dadi

    run(db, TODAY, NOW)
    run(db, TODAY, NOW)  # a second run the same day must not repeat it

    news = alerts_of(db, family, "new_scheme")
    assert len(news) == 1
    assert news[0].payload_json["member"] == "Dadi"
    assert news[0].payload_json["scheme"]["slug"] == "old-age"
    assert news[0].status == "sent" and news[0].read_at is None


def test_a_scheme_that_does_not_fit_is_not_news(
    client: TestClient, db: Session, make_family, today: date, seeded: None
) -> None:
    family = make_family()
    add_member(client, family, "Dadi", 1960)
    run(db, TODAY, NOW)
    add_scheme(db, "young", YOUNG)  # Dadi is 66: does not fit

    run(db, TODAY, NOW)

    assert alerts_of(db, family, "new_scheme") == []


def test_a_member_added_later_is_not_a_flood_either(
    client: TestClient, db: Session, make_family, today: date, seeded: None
) -> None:
    add_scheme(db, "old-age", OLD_AGE)
    family = make_family()
    add_member(client, family, "Dadi", 1960)
    run(db, TODAY, NOW)
    add_member(client, family, "Nana", 1955)  # also fits, but is new to the app

    run(db, TODAY, NOW)

    assert alerts_of(db, family, "new_scheme") == []


def test_a_new_rule_version_is_news_for_a_family_that_had_a_result(
    client: TestClient, db: Session, make_family, today: date, seeded: None
) -> None:
    add_scheme(db, "old-age", OLD_AGE)
    family = make_family()
    add_member(client, family, "Dadi", 1960)
    run(db, TODAY, NOW)
    first = db.scalars(
        select(SchemeVersion)
        .join(Scheme, SchemeVersion.scheme_id == Scheme.id)
        .where(Scheme.slug == "old-age")
    ).one()
    second = SchemeVersion(
        scheme_id=first.scheme_id,
        version_no=2,
        rules_json={"all": [{"field": "age", "op": "gte", "value": 65}], "fixable": []},
        source_url="https://example.gov.in",
    )
    db.add(second)
    db.flush()
    db.execute(
        update(Scheme).where(Scheme.id == first.scheme_id).values(current_version_id=second.id)
    )

    run(db, TODAY, NOW)
    run(db, TODAY, NOW)

    changed = alerts_of(db, family, "rule_change")
    assert len(changed) == 1
    assert changed[0].payload_json["version_no"] == 2
    assert changed[0].payload_json["scheme"]["slug"] == "old-age"
    # Dadi is 66, so still fits: a changed rule is not "a new scheme fits".
    assert alerts_of(db, family, "new_scheme") == []


def test_a_member_nearing_a_scheme_age_is_told_once_with_the_scheme(
    client: TestClient, db: Session, make_family, today: date
) -> None:
    add_scheme(db, "old-age", OLD_AGE)
    family = make_family()
    add_member(client, family, "Bua", 1967)  # reaches 60 during 2027; today is 3 Nov 2026
    add_member(client, family, "Chhotu", 1990)  # 60 is far off: no alert

    run(db, TODAY, NOW)
    run(db, TODAY, NOW)

    ages = alerts_of(db, family, "age_threshold")
    assert len(ages) == 1
    payload: dict[str, Any] = ages[0].payload_json
    assert payload["member"] == "Bua" and payload["age"] == 60 and payload["year"] == 2027
    assert [s["slug"] for s in payload["schemes"]] == ["old-age"]


def test_a_member_already_past_the_age_is_not_told(
    client: TestClient, db: Session, make_family, today: date
) -> None:
    add_scheme(db, "old-age", OLD_AGE)
    family = make_family()
    add_member(client, family, "Dadi", 1960)  # turned 60 in 2020

    run(db, TODAY, NOW)

    assert alerts_of(db, family, "age_threshold") == []


def test_one_family_cannot_see_another_familys_news(
    client: TestClient, db: Session, make_family, today: date
) -> None:
    add_scheme(db, "old-age", OLD_AGE)
    first, second = make_family(), make_family()
    add_member(client, first, "Bua", 1967)
    add_member(client, second, "Chhotu", 1990)
    run(db, TODAY, NOW)

    assert len(alerts_of(db, first)) == 1
    assert alerts_of(db, second) == []


# --- the API -------------------------------------------------------------------------------------


def _make_news(client: TestClient, db: Session, make_family) -> Family:  # noqa: ANN001
    add_scheme(db, "old-age", OLD_AGE)
    add_scheme(db, "young", YOUNG)
    family = make_family()
    add_member(client, family, "Bua", 1967)  # age alert for old-age (60)
    add_member(client, family, "Teen", 2010)  # no alert yet: turns 18 in 2028
    run(db, TODAY, NOW)
    return family


def test_the_list_shows_unread_news_newest_first(
    client: TestClient, db: Session, make_family, today: date
) -> None:
    family = _make_news(client, db, make_family)

    body = client.get(f"{family.url}/alerts", headers=family.headers).json()

    assert body["unread"] == len(body["alerts"]) >= 1
    assert all(a["read"] is False for a in body["alerts"])
    assert body["alerts"][0]["type"] == "age_threshold"
    assert body["alerts"][0]["payload"]["member"] == "Bua"


def test_mark_one_read_then_mark_all(
    client: TestClient, db: Session, make_family, today: date
) -> None:
    family = _make_news(client, db, make_family)
    first = client.get(f"{family.url}/alerts", headers=family.headers).json()["alerts"][0]

    marked = client.post(f"{family.url}/alerts/{first['id']}/read", headers=family.headers)
    assert marked.status_code == 200 and marked.json()["read"] is True
    again = client.post(f"{family.url}/alerts/{first['id']}/read", headers=family.headers)
    assert again.status_code == 200  # twice is fine

    after = client.get(f"{family.url}/alerts", headers=family.headers).json()
    assert after["unread"] == len(after["alerts"]) - 1

    everything = client.post(f"{family.url}/alerts/read-all", headers=family.headers).json()
    assert everything["unread"] == 0 and all(a["read"] for a in everything["alerts"])


def test_an_alert_of_another_family_cannot_be_read_or_marked(
    client: TestClient, db: Session, make_family, today: date
) -> None:
    mine = _make_news(client, db, make_family)
    other = make_family()
    alert_id = client.get(f"{mine.url}/alerts", headers=mine.headers).json()["alerts"][0]["id"]

    assert client.get(f"{mine.url}/alerts", headers=other.headers).status_code == 403
    assert client.get(f"{other.url}/alerts", headers=other.headers).json()["alerts"] == []
    stolen = client.post(f"{other.url}/alerts/{alert_id}/read", headers=other.headers)
    assert stolen.status_code == 404
    still = client.get(f"{mine.url}/alerts", headers=mine.headers).json()
    assert still["unread"] == len(still["alerts"])


def test_the_alerts_need_a_sign_in(client: TestClient, make_family, today: date) -> None:
    family = make_family()
    assert client.get(f"{family.url}/alerts").status_code == 401
    assert client.post(f"{family.url}/alerts/read-all").status_code == 401
    assert client.post(f"{family.url}/alerts/1/read").status_code == 401
