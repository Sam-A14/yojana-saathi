"""The public document list: what the setup form asks a family about. No token: it holds nothing
about any family."""

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DbSession
from app.api.schemas import DocumentSummary
from app.db.models import Document
from app.rules.values import HOUSEHOLD_DOCUMENT_CODES

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentSummary])
def list_documents(db: DbSession) -> list[DocumentSummary]:
    rows = db.scalars(select(Document).order_by(Document.id))
    return [
        DocumentSummary(
            code=d.code,
            name_en=d.name_en,
            name_hi=d.name_hi,
            # From the same list the eligibility step uses to share these answers (decision 009),
            # so the form asks once per family exactly when the engine shares once per family.
            household_level=d.code in HOUSEHOLD_DOCUMENT_CODES,
        )
        for d in rows
    ]
