"""GET /households/{id}/eligibility: every member against every active scheme.

The decisions all come from the rules engine (via ranges.py). This file only gathers the data,
asks the engine, and shapes the answer, plus works out which required documents are missing.
"""

import logging
import uuid
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DbSession, OwnHousehold, Today
from app.api.facts import (
    age_range,
    documents_of,
    household_facts,
    income_range,
    member_facts,
    shared_documents,
)
from app.api.ranges import RangedEvaluation, RangedRule, Ranges, ReasonCode, evaluate_with_ranges
from app.api.schemas import SchemeSummary
from app.api.schemes import active_schemes_query, scheme_summary
from app.db.models import Document, Household, Member, Scheme, SchemeDocument, SchemeVersion
from app.rules.engine import RuleError

logger = logging.getLogger("yojana")
router = APIRouter(prefix="/households", tags=["eligibility"])

# Best news first. not_eligible is not listed per scheme (see MemberEligibility).
STATUS_ORDER = {"eligible": 0, "near_miss": 1, "unknown": 2}


# --- response shapes -----------------------------------------------------------------------


class RuleOut(BaseModel):
    rule: dict[str, Any]  # exactly as written in the scheme
    fields: list[str]  # every fact this rule looked at
    matched_members: list[str]  # nicknames whose facts satisfied an any_member part
    fixable: bool  # failed, but would pass if the family fixed its fixable items
    # Set when the rule is "unknown" only because the exact age or income is not known.
    reasons: list[ReasonCode]


class MissingDocument(BaseModel):
    code: str
    name_en: str
    name_hi: str
    how_to_get_en: str | None
    how_to_get_hi: str | None
    official_link: str | None
    # "no": the family said they do not have it. "not_answered": we have not asked yet.
    state: Literal["no", "not_answered"]


class SchemeResult(BaseModel):
    scheme: SchemeSummary  # includes verified: false for schemes no human has checked yet
    status: Literal["eligible", "near_miss", "unknown"]
    # Why the status is "unknown" when it is because exact age or income would change the answer.
    reasons: list[ReasonCode]
    passed_rules: list[RuleOut]
    failed_rules: list[RuleOut]
    unknown_rules: list[RuleOut]
    # Nicknames of the household members whose facts made a rule fail (e.g. paid income tax).
    excluded_by: list[str]
    missing_documents: list[MissingDocument]


class ExcludedScheme(BaseModel):
    """A scheme this member would fit, except that ANOTHER person's facts exclude the household.

    Listed (unlike other not-eligible schemes) because the family can act on it: "PM-KISAN: not
    available because Suresh paid income tax" is worth showing, "you are not a widow" is not.
    """

    scheme: SchemeSummary
    excluded_by: list[str]
    failed_rules: list[RuleOut]


class MemberEligibility(BaseModel):
    member_id: uuid.UUID
    nickname: str
    schemes: list[SchemeResult]
    excluded: list[ExcludedScheme]
    # All other schemes that definitely do not fit. Counted, not listed, so the dashboard stays
    # readable ("12 other schemes do not fit").
    not_eligible_count: int


class EligibilityOut(BaseModel):
    household_id: uuid.UUID
    computed_on: date
    members: list[MemberEligibility]
    # Schemes left out because their stored rules are broken. Never turned into an answer.
    skipped_schemes: list[str]


# --- building the answer -------------------------------------------------------------------


def _rule_out(result: RangedRule) -> RuleOut:
    return RuleOut(
        rule=dict(result.rule),
        fields=list(result.fields),
        matched_members=list(result.matched_members),
        fixable=result.fixable,
        reasons=list(result.reasons),
    )


def _excluded_by(evaluation: RangedEvaluation) -> list[str]:
    names = (name for rule in evaluation.with_outcome("failed") for name in rule.matched_members)
    return list(dict.fromkeys(names))


def _missing_documents(
    links: Sequence[tuple[SchemeDocument, Document]], answers: Mapping[str, bool]
) -> list[MissingDocument]:
    """Required documents this member does not (or may not) have.

    `answers` are the member's answers after family-level documents were shared (facts.py), the
    same ones the engine saw. Documents that are not required are never listed.
    """
    missing: list[MissingDocument] = []
    for link, doc in links:
        has = answers.get(doc.code)
        if not link.required or has is True:
            continue
        missing.append(
            MissingDocument(
                code=doc.code,
                name_en=doc.name_en,
                name_hi=doc.name_hi,
                how_to_get_en=doc.how_to_get_en,
                how_to_get_hi=doc.how_to_get_hi,
                official_link=doc.official_link,
                state="no" if has is False else "not_answered",
            )
        )
    return missing


def _scheme_documents(
    db: Session, version_ids: list[int]
) -> dict[int, list[tuple[SchemeDocument, Document]]]:
    by_version: dict[int, list[tuple[SchemeDocument, Document]]] = {v: [] for v in version_ids}
    rows = db.execute(
        select(SchemeDocument, Document)
        .join(Document, SchemeDocument.document_code == Document.code)
        .where(SchemeDocument.scheme_version_id.in_(version_ids))
        .order_by(SchemeDocument.document_code)
    ).all()
    for link, doc in rows:
        by_version[link.scheme_version_id].append((link, doc))
    return by_version


def compute_eligibility(db: Session, household: Household, today: date) -> EligibilityOut:
    members = list(
        db.scalars(
            select(Member).where(Member.household_id == household.id).order_by(Member.created_at)
        )
    )
    own_answers = documents_of(db, [m.id for m in members])
    answers = shared_documents([own_answers[m.id] for m in members])
    people = [member_facts(m, answers[i]) for i, m in enumerate(members)]
    ranges = Ranges(
        ages={i: age_range(m.birth_year, today) for i, m in enumerate(members) if m.birth_year},
        income=income_range(household.income_band) if household.income_band else None,
    )
    attributes = household_facts(household)

    schemes: list[tuple[Scheme, SchemeVersion]] = [
        (s, v) for s, v in db.execute(active_schemes_query().order_by(Scheme.name_en)).all()
    ]
    documents = _scheme_documents(db, [v.id for _, v in schemes])
    skipped: list[str] = []

    result_members: list[MemberEligibility] = []
    for index, member in enumerate(members):
        listed: list[SchemeResult] = []
        excluded: list[ExcludedScheme] = []
        not_eligible = 0
        for scheme, version in schemes:
            if scheme.slug in skipped:
                continue
            try:
                evaluation = evaluate_with_ranges(
                    index, people, attributes, version.rules_json, ranges
                )
            except RuleError:
                # Our rule is broken, not the family's data: leave the scheme out, say so, and
                # keep serving the rest. Never turn this into an eligibility answer.
                logger.exception("Scheme %s has malformed rules; skipped", scheme.slug)
                skipped.append(scheme.slug)
                continue
            if evaluation.status == "not_eligible":
                names = _excluded_by(evaluation)
                if names:
                    excluded.append(
                        ExcludedScheme(
                            scheme=scheme_summary(scheme, version),
                            excluded_by=names,
                            failed_rules=[_rule_out(r) for r in evaluation.with_outcome("failed")],
                        )
                    )
                else:
                    not_eligible += 1
                continue
            listed.append(
                SchemeResult(
                    scheme=scheme_summary(scheme, version),
                    status=evaluation.status,
                    reasons=list(evaluation.reasons),
                    passed_rules=[_rule_out(r) for r in evaluation.with_outcome("passed")],
                    failed_rules=[_rule_out(r) for r in evaluation.with_outcome("failed")],
                    unknown_rules=[_rule_out(r) for r in evaluation.with_outcome("unknown")],
                    excluded_by=_excluded_by(evaluation),
                    missing_documents=_missing_documents(documents[version.id], answers[index]),
                )
            )
        listed.sort(key=lambda r: (STATUS_ORDER[r.status], r.scheme.name_en))
        result_members.append(
            MemberEligibility(
                member_id=member.id,
                nickname=member.nickname,
                schemes=listed,
                excluded=excluded,
                not_eligible_count=not_eligible,
            )
        )
    return EligibilityOut(
        household_id=household.id,
        computed_on=today,
        members=result_members,
        skipped_schemes=skipped,
    )


@router.get("/{household_id}/eligibility", response_model=EligibilityOut)
def read_eligibility(household: OwnHousehold, db: DbSession, today: Today) -> EligibilityOut:
    """Which schemes each member may qualify for, why, and which documents are missing.

    Guidance only, not an official decision. Ages come from birth YEAR, so an answer that would
    change with the exact age or income is "unknown" with a reason, never a guess.
    """
    return compute_eligibility(db, household, today)
