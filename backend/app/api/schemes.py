"""The public scheme catalogue. No token: it holds nothing about any family."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import Select, select

from app.api.deps import DbSession
from app.api.schemas import SchemeDetail, SchemeDocumentOut, SchemeSummary
from app.db.models import Document, Scheme, SchemeDocument, SchemeVersion

router = APIRouter(prefix="/schemes", tags=["schemes"])


def scheme_summary(scheme: Scheme, version: SchemeVersion) -> SchemeSummary:
    return SchemeSummary(
        slug=scheme.slug,
        name_en=scheme.name_en,
        name_hi=scheme.name_hi,
        level=scheme.level,
        state=scheme.state,
        category=scheme.category,
        official_url=scheme.official_url,
        benefit_text_en=version.benefit_text_en,
        benefit_text_hi=version.benefit_text_hi,
        deadline_start=version.deadline_start,
        deadline_end=version.deadline_end,
        verified=version.verified_at is not None,
        verified_at=version.verified_at,
    )


# Only active schemes with a published version: closed ones are hidden (kept in the database), and
# a scheme with no version has no rules or benefit text to show yet.
def active_schemes_query() -> Select[tuple[Scheme, SchemeVersion]]:
    return (
        select(Scheme, SchemeVersion)
        .join(SchemeVersion, Scheme.current_version_id == SchemeVersion.id)
        .where(Scheme.status == "active")
    )


@router.get("", response_model=list[SchemeSummary])
def list_schemes(db: DbSession) -> list[SchemeSummary]:
    rows = db.execute(active_schemes_query().order_by(Scheme.name_en)).all()
    return [scheme_summary(scheme, version) for scheme, version in rows]


@router.get("/{slug}", response_model=SchemeDetail)
def read_scheme(slug: str, db: DbSession) -> SchemeDetail:
    row = db.execute(active_schemes_query().where(Scheme.slug == slug)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="No such scheme.")
    scheme, version = row
    documents = db.execute(
        select(SchemeDocument, Document)
        .join(Document, SchemeDocument.document_code == Document.code)
        .where(SchemeDocument.scheme_version_id == version.id)
        .order_by(SchemeDocument.document_code)
    ).all()
    return SchemeDetail(
        **scheme_summary(scheme, version).model_dump(),
        source_url=version.source_url,
        version_no=version.version_no,
        documents=[
            SchemeDocumentOut(
                code=doc.code,
                name_en=doc.name_en,
                name_hi=doc.name_hi,
                how_to_get_en=doc.how_to_get_en,
                how_to_get_hi=doc.how_to_get_hi,
                official_link=doc.official_link,
                required=link.required,
                applies_to=link.applies_to,
            )
            for link, doc in documents
        ],
    )
