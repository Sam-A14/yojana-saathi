"""The three kinds of news, and the code that decides each. No LLM and no guessing: every alert
comes from the same rules engine the results page uses (decision 051).

  new_scheme     a member now fits (status "eligible") a scheme they did not fit before
  age_threshold  a member reaches an age (a "from age N" rule of some scheme) soon
  rule_change    a scheme's rules changed in a new version, and this family had a result for it

"Before" is the stored result (eligibility_results), written by the previous daily run.
"""

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.api.facts import (
    age_range,
    documents_of,
    household_facts,
    income_range,
    member_facts,
    shared_documents,
)
from app.api.ranges import Ranges, evaluate_with_ranges
from app.api.schemes import active_schemes_query
from app.db.models import (
    Alert,
    EligibilityResult,
    Household,
    Member,
    Scheme,
    SchemeVersion,
)
from app.rules.engine import RuleError

# How far ahead an age alert is made. We hold a birth YEAR only, so the earliest the birthday can
# fall is 1 January: the alert is made this many days before that.
AGE_WARNING_DAYS = 60


# --- age thresholds ----------------------------------------------------------------------------


def age_thresholds(rules: Mapping[str, Any]) -> set[int]:
    """The ages at which a scheme STARTS to fit: `age gte N` and `age between [N, M]`.

    Only conditions every applicant must meet are read (inside "all" and "any"); anything under
    "not" or "any_member" says something else (an exclusion, or about other people) and is skipped.
    An upper limit (`lte`, the end of a `between`) is not good news, so it is not an alert.
    """
    found: set[int] = set()
    _collect_thresholds(rules, found)
    return {age for age in found if age > 0}


def _collect_thresholds(node: Any, found: set[int]) -> None:
    if isinstance(node, list):
        for item in node:
            _collect_thresholds(item, found)
        return
    if not isinstance(node, dict):
        return
    if node.get("field") == "age":
        value = node.get("value")
        if node.get("op") == "gte" and isinstance(value, int):
            found.add(value)
        elif node.get("op") == "between" and isinstance(value, list) and value:
            found.add(value[0])
        return
    for key in ("all", "any"):
        _collect_thresholds(node.get(key), found)


def age_alert_due(birth_year: int, threshold: int, today: date) -> bool:
    """True from 60 days before 1 January of the year the member reaches `threshold`, to the end
    of that year. After that year it is old news, and a member already past the age is never told.
    """
    reach_year = birth_year + threshold
    earliest = date(reach_year, 1, 1)
    return earliest - timedelta(days=AGE_WARNING_DAYS) <= today <= date(reach_year, 12, 31)


# --- one family --------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Now:
    """What one member's result for one scheme is today."""

    status: str
    scheme: Scheme
    version: SchemeVersion


def _evaluate_all(
    db: Session, household: Household, members: Sequence[Member], today: date
) -> dict[tuple[uuid.UUID, int], _Now]:
    """The engine's answer for every member and every active scheme (including "not eligible")."""
    own = documents_of(db, [m.id for m in members])
    answers = shared_documents([own[m.id] for m in members])
    people = [member_facts(m, answers[i]) for i, m in enumerate(members)]
    ranges = Ranges(
        ages={i: age_range(m.birth_year, today) for i, m in enumerate(members) if m.birth_year},
        income=income_range(household.income_band) if household.income_band else None,
    )
    attributes = household_facts(household)
    now: dict[tuple[uuid.UUID, int], _Now] = {}
    for scheme, version in db.execute(active_schemes_query()).all():
        for index, member in enumerate(members):
            try:
                evaluation = evaluate_with_ranges(
                    index, people, attributes, version.rules_json, ranges
                )
            except RuleError:
                break  # broken rules of ours: no answer for this scheme, for anyone
            now[(member.id, scheme.id)] = _Now(evaluation.status, scheme, version)
    return now


def _name(scheme: Scheme) -> dict[str, Any]:
    return {"slug": scheme.slug, "name_en": scheme.name_en, "name_hi": scheme.name_hi}


def _add(
    alerts: list[dict[str, Any]], kind: str, key: str, payload: dict[str, Any]
) -> None:
    alerts.append({"type": kind, "dedupe_key": key, "payload_json": payload})


def alerts_for_household(
    db: Session, household: Household, today: date
) -> tuple[list[dict[str, Any]], int]:
    """Works out the news for one family, saves today's results as the new "before", and returns
    (alerts to store, number of members seen for the first time).

    A member with no stored results has never been looked at: their results are saved quietly
    (nothing is "new" about a family that has just signed up). From the next run on, changes count.
    """
    members = list(
        db.scalars(
            select(Member).where(Member.household_id == household.id).order_by(Member.created_at)
        )
    )
    if not members:
        return [], 0
    now = _evaluate_all(db, household, members, today)
    member_ids = [m.id for m in members]
    # (member, scheme) -> (status, version id, version no) as of the last run.
    before: dict[tuple[uuid.UUID, int], tuple[str, int, int]] = {}
    for result, scheme_id, version_no in db.execute(
        select(EligibilityResult, SchemeVersion.scheme_id, SchemeVersion.version_no)
        .join(SchemeVersion, EligibilityResult.scheme_version_id == SchemeVersion.id)
        .where(EligibilityResult.member_id.in_(member_ids))
    ).all():
        before[(result.member_id, scheme_id)] = (
            result.status,
            result.scheme_version_id,
            version_no,
        )
    seen_before = {member_id for member_id, _ in before}
    first_time = [m for m in members if m.id not in seen_before]

    alerts: list[dict[str, Any]] = []
    changed_schemes: dict[int, tuple[Scheme, SchemeVersion]] = {}
    for member in members:
        if member.id not in seen_before:
            continue
        for (member_id, scheme_id), current in now.items():
            if member_id != member.id:
                continue
            old = before.get((member.id, scheme_id))
            if old is not None and old[1] != current.version.id:
                changed_schemes[scheme_id] = (current.scheme, current.version)
            if current.status == "eligible" and (old is None or old[0] != "eligible"):
                _add(
                    alerts,
                    "new_scheme",
                    f"new_scheme:{member.id}:{current.scheme.slug}:{current.version.id}",
                    {"member": member.nickname, "scheme": _name(current.scheme)},
                )
    for scheme, version in changed_schemes.values():
        _add(
            alerts,
            "rule_change",
            f"rule_change:{scheme.slug}:{version.id}",
            {"scheme": _name(scheme), "version_no": version.version_no},
        )
    alerts.extend(_age_alerts(members, [(s, v) for s, v in _schemes(now)], today))

    _save_results(db, member_ids, now)
    return alerts, len(first_time)


def _schemes(now: Mapping[tuple[uuid.UUID, int], _Now]) -> list[tuple[Scheme, SchemeVersion]]:
    unique = {current.scheme.id: (current.scheme, current.version) for current in now.values()}
    return list(unique.values())


def _age_alerts(
    members: Sequence[Member],
    schemes: Sequence[tuple[Scheme, SchemeVersion]],
    today: date,
) -> list[dict[str, Any]]:
    starts: dict[int, list[Scheme]] = {}
    for scheme, version in schemes:
        for age in age_thresholds(version.rules_json):
            starts.setdefault(age, []).append(scheme)
    alerts: list[dict[str, Any]] = []
    for member in members:
        if not member.birth_year:
            continue
        for age, schemes_at_age in sorted(starts.items()):
            if age_alert_due(member.birth_year, age, today):
                _add(
                    alerts,
                    "age_threshold",
                    f"age_threshold:{member.id}:{age}",
                    {
                        "member": member.nickname,
                        "age": age,
                        "year": member.birth_year + age,
                        "schemes": [_name(s) for s in sorted(schemes_at_age, key=lambda s: s.slug)],
                    },
                )
    return alerts


def _save_results(
    db: Session, member_ids: Sequence[uuid.UUID], now: Mapping[tuple[uuid.UUID, int], _Now]
) -> None:
    """Replaces the family's stored results with today's (one row per member and scheme)."""
    db.execute(delete(EligibilityResult).where(EligibilityResult.member_id.in_(member_ids)))
    db.add_all(
        EligibilityResult(
            member_id=member_id, scheme_version_id=current.version.id, status=current.status
        )
        for (member_id, _), current in now.items()
    )
    db.flush()


def store_alerts(db: Session, user_id: uuid.UUID, alerts: Sequence[dict[str, Any]], at: Any) -> int:
    """Saves new alerts; an alert whose key already exists for this family is skipped. Returns how
    many were new. In-app alerts are "sent" the moment they exist (nothing else delivers them)."""
    created = 0
    for alert in alerts:
        statement = (
            pg_insert(Alert)
            .values(
                user_id=user_id,
                type=alert["type"],
                status="sent",
                payload_json=alert["payload_json"],
                scheduled_for=at,
                sent_at=at,
                dedupe_key=alert["dedupe_key"],
            )
            .on_conflict_do_nothing(index_elements=["user_id", "dedupe_key"])
        )
        created += db.execute(statement).rowcount
    return created
