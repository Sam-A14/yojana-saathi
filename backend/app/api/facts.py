"""Turn database rows into the plain facts the rules engine and range evaluation expect.

Everything here is a small pure function except `documents_of` (one query). Age is NOT computed
here as a single number: a birth year only gives a range (see ranges.py).
"""

import math
import uuid
from collections.abc import Mapping, Sequence
from datetime import date, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Household, Member, MemberDocument
from app.rules.values import HOUSEHOLD_DOCUMENT_CODES, INCOME_BANDS

# India has no daylight saving, so a fixed offset is exact and needs no timezone database.
INDIA = timezone(timedelta(hours=5, minutes=30))

# Member columns that are engine facts. A test checks this list against rules/fields.py, so a new
# fact added to the engine cannot be forgotten here.
MEMBER_FACT_COLUMNS = (
    "gender",
    "marital_status",
    "occupation",
    "education",
    "is_student",
    "disability",
    "owns_cultivable_land",
    "paid_income_tax_last_year",
    "govt_employee",
    "pension_band",
    "is_registered_professional",
    "holds_constitutional_post",
    "is_remarried",
)
HOUSEHOLD_FACT_COLUMNS = ("state", "district", "area_type", "category")


def age_range(birth_year: int, today: date) -> tuple[int, int]:
    """(youngest, oldest) the person can be today, knowing only the birth year.

    Born in 1966, today in 2026: 59 if the birthday has not come yet, else 60.
    """
    oldest = max(today.year - birth_year, 0)
    return max(oldest - 1, 0), oldest


def income_range(income_band: str) -> tuple[float, float]:
    """(lowest, highest) yearly income in the band, both possible. The top band: highest = math.inf.

    Bands are "more than lower, up to and including upper" (values.py), so the lowest possible
    income is one rupee above the lower edge. A rule cut exactly at an edge therefore has a
    definite answer; only a rule cut inside the band is "unknown".
    """
    band = INCOME_BANDS[income_band]
    return band.lowest, math.inf if band.upper is None else band.upper


def member_facts(member: Member, documents: Mapping[str, bool]) -> dict[str, Any]:
    """Facts about one person, without age. A fact left unanswered stays None (= unknown)."""
    facts: dict[str, Any] = {"nickname": member.nickname}
    for column in MEMBER_FACT_COLUMNS:
        facts[column] = getattr(member, column)
    # "has_<code>" only for documents the family answered; an absent key is "not asked yet".
    for code, has in documents.items():
        facts[f"has_{code}"] = has
    return facts


def shared_documents(answers: Sequence[Mapping[str, bool]]) -> list[dict[str, bool]]:
    """Each member's document answers after sharing family-level documents.

    If ANY member has a household document (ration card, BPL card, ...), every member has it. One
    rule used for both the engine's has_<code> facts and the missing-documents list, so the two
    cannot disagree. Nobody holding it changes nothing: members who said "no" stay "no" and
    members who were not asked stay unanswered (we never invent a "no" or a "yes").
    """
    held = {code for code in HOUSEHOLD_DOCUMENT_CODES if any(a.get(code) is True for a in answers)}
    return [{**a, **dict.fromkeys(held, True)} for a in answers]


def household_facts(household: Household) -> dict[str, Any]:
    """Household facts, without income_band_max (that is a range, see income_range)."""
    return {column: getattr(household, column) for column in HOUSEHOLD_FACT_COLUMNS}


def documents_of(db: Session, member_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, bool]]:
    """Document code -> has / has not, for each member. Members with no answers get {}."""
    held: dict[uuid.UUID, dict[str, bool]] = {member_id: {} for member_id in member_ids}
    rows = db.execute(
        select(MemberDocument).where(MemberDocument.member_id.in_(member_ids))
    ).scalars()
    for row in rows:
        held[row.member_id][row.document_code] = row.has
    return held
