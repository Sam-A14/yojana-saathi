"""Households, their members, and the documents each member holds.

Every endpoint needs a signed-in user, and the household must be theirs (see deps.py).
"""

import uuid

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbSession, OwnHousehold
from app.api.facts import documents_of
from app.api.schemas import (
    MAX_MEMBERS_PER_HOUSEHOLD,
    DocumentsIn,
    DocumentsOut,
    HouseholdCreate,
    HouseholdOut,
    HouseholdUpdate,
    MemberCreate,
    MemberOut,
    MemberUpdate,
    sent_fields,
)
from app.db.models import Document, Household, Member, MemberDocument

router = APIRouter(prefix="/households", tags=["households"])


# --- households ----------------------------------------------------------------------------


@router.post("", status_code=201, response_model=HouseholdOut)
def create_household(data: HouseholdCreate, user: CurrentUser, db: DbSession) -> Household:
    """Start the signed-in person's household. Each person has one."""
    if db.scalar(select(Household.id).where(Household.user_id == user.id)) is not None:
        raise HTTPException(status_code=409, detail="You already have a household.")
    household = Household(**data.model_dump(), user_id=user.id)
    db.add(household)
    try:
        db.commit()
    except IntegrityError:  # two requests at once: the unique constraint on user_id decides
        db.rollback()
        raise HTTPException(status_code=409, detail="You already have a household.") from None
    return household


@router.get("/{household_id}", response_model=HouseholdOut)
def read_household(household: OwnHousehold) -> Household:
    return household


@router.patch("/{household_id}", response_model=HouseholdOut)
def update_household(data: HouseholdUpdate, household: OwnHousehold, db: DbSession) -> Household:
    for name, value in sent_fields(data).items():
        setattr(household, name, value)
    db.commit()
    return household


# --- members -------------------------------------------------------------------------------


def _member_out(member: Member, documents: dict[str, bool]) -> MemberOut:
    out = MemberOut.model_validate(member)
    out.documents = documents
    return out


def _own_member(db: Session, household: Household, member_id: uuid.UUID) -> Member:
    """A member of THIS household. Another household's member id is simply "not found"."""
    member = db.get(Member, member_id)
    if member is None or member.household_id != household.id:
        raise HTTPException(status_code=404, detail="No such member in this household.")
    return member


@router.post("/{household_id}/members", status_code=201, response_model=MemberOut)
def add_member(data: MemberCreate, household: OwnHousehold, db: DbSession) -> MemberOut:
    # Lock the household row so two simultaneous requests cannot both pass the count check.
    db.execute(select(Household.id).where(Household.id == household.id).with_for_update())
    count = db.scalar(select(func.count()).where(Member.household_id == household.id)) or 0
    if count >= MAX_MEMBERS_PER_HOUSEHOLD:
        raise HTTPException(
            status_code=409,
            detail=f"A household can have at most {MAX_MEMBERS_PER_HOUSEHOLD} members.",
        )
    member = Member(household_id=household.id, **data.model_dump())
    db.add(member)
    db.commit()
    return _member_out(member, {})


@router.get("/{household_id}/members", response_model=list[MemberOut])
def list_members(household: OwnHousehold, db: DbSession) -> list[MemberOut]:
    members = list(
        db.scalars(
            select(Member).where(Member.household_id == household.id).order_by(Member.created_at)
        )
    )
    held = documents_of(db, [m.id for m in members])
    return [_member_out(m, held[m.id]) for m in members]


@router.get("/{household_id}/members/{member_id}", response_model=MemberOut)
def read_member(member_id: uuid.UUID, household: OwnHousehold, db: DbSession) -> MemberOut:
    member = _own_member(db, household, member_id)
    return _member_out(member, documents_of(db, [member.id])[member.id])


@router.patch("/{household_id}/members/{member_id}", response_model=MemberOut)
def update_member(
    member_id: uuid.UUID, data: MemberUpdate, household: OwnHousehold, db: DbSession
) -> MemberOut:
    member = _own_member(db, household, member_id)
    for name, value in sent_fields(data).items():
        setattr(member, name, value)
    db.commit()
    return _member_out(member, documents_of(db, [member.id])[member.id])


@router.delete("/{household_id}/members/{member_id}", status_code=204)
def delete_member(member_id: uuid.UUID, household: OwnHousehold, db: DbSession) -> Response:
    member = _own_member(db, household, member_id)
    db.execute(delete(Member).where(Member.id == member.id))
    db.commit()
    return Response(status_code=204)


# --- documents -----------------------------------------------------------------------------


@router.put("/{household_id}/members/{member_id}/documents", response_model=DocumentsOut)
def set_member_documents(
    member_id: uuid.UUID, data: DocumentsIn, household: OwnHousehold, db: DbSession
) -> DocumentsOut:
    """Replace everything we know about which documents this member holds.

    PUT means "this is the full picture": a code left out becomes "not answered" again. Sending the
    same body twice gives the same result, so a retry after a network error is safe.
    """
    member = _own_member(db, household, member_id)
    known = set(db.scalars(select(Document.code).where(Document.code.in_(data.documents))))
    unknown = sorted(set(data.documents) - known)
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown document codes: {unknown}")
    db.execute(delete(MemberDocument).where(MemberDocument.member_id == member.id))
    db.add_all(
        MemberDocument(member_id=member.id, document_code=code, has=has)
        for code, has in data.documents.items()
    )
    db.commit()
    return DocumentsOut(documents=dict(data.documents))
