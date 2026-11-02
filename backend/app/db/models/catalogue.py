"""Scheme catalogue: what exists, its versioned rules, and which documents it needs."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_at_column, in_list_check, updated_at_column

SCHEME_LEVELS = ("central", "state")
SCHEME_STATUSES = ("active", "closed", "paused", "merged", "renamed")
DOCUMENT_APPLIES_TO = ("applicant", "household")


class Scheme(Base):
    __tablename__ = "schemes"
    __table_args__ = (
        CheckConstraint(in_list_check("level", SCHEME_LEVELS), name="level_valid"),
        CheckConstraint(in_list_check("status", SCHEME_STATUSES), name="status_valid"),
        # A state scheme without a state could never be matched to a household.
        CheckConstraint("level = 'central' OR state IS NOT NULL", name="state_scheme_has_state"),
        Index("ix_schemes_status_level_state", "status", "level", "state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(unique=True)
    name_en: Mapped[str]
    name_hi: Mapped[str | None]
    level: Mapped[str]
    state: Mapped[str | None]
    category: Mapped[str]
    official_url: Mapped[str]
    status: Mapped[str] = mapped_column(server_default="active")
    # use_alter: schemes and scheme_versions point at each other, so this foreign key is added
    # after both tables exist. Nullable because a scheme is created before its first version.
    current_version_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "scheme_versions.id",
            use_alter=True,
            name="fk_schemes_current_version_id_scheme_versions",
            ondelete="RESTRICT",
        )
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    versions: Mapped[list["SchemeVersion"]] = relationship(
        back_populates="scheme",
        foreign_keys="SchemeVersion.scheme_id",
        order_by="SchemeVersion.version_no",
    )
    # post_update: insert the scheme first, then set this pointer, to break the circular dependency.
    current_version: Mapped["SchemeVersion | None"] = relationship(
        foreign_keys=[current_version_id], post_update=True
    )


class SchemeVersion(Base):
    """One approved snapshot of a scheme's rules. Rows are never edited, only added."""

    __tablename__ = "scheme_versions"
    __table_args__ = (
        UniqueConstraint("scheme_id", "version_no"),
        CheckConstraint("version_no >= 1", name="version_no_positive"),
        CheckConstraint(
            "deadline_end IS NULL OR deadline_start IS NULL OR deadline_end >= deadline_start",
            name="deadline_order",
        ),
        # The alert scheduler looks for deadlines in the next 14 and 3 days.
        Index("ix_scheme_versions_deadline_end", "deadline_end"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scheme_id: Mapped[int] = mapped_column(ForeignKey("schemes.id", ondelete="RESTRICT"))
    version_no: Mapped[int]
    rules_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    benefit_text_en: Mapped[str | None]
    benefit_text_hi: Mapped[str | None]
    deadline_start: Mapped[date | None]
    deadline_end: Mapped[date | None]
    source_url: Mapped[str]
    # Hash of the fetched source page, used by the crawler to skip unchanged pages.
    source_hash: Mapped[str | None]
    # NULL means "never verified by a human"; the UI must show that honestly.
    verified_at: Mapped[datetime | None]
    approved_by: Mapped[str | None]
    created_at: Mapped[datetime] = created_at_column()

    scheme: Mapped[Scheme] = relationship(back_populates="versions", foreign_keys=[scheme_id])
    documents: Mapped[list["SchemeDocument"]] = relationship(
        order_by="SchemeDocument.document_code"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stable machine name (e.g. "aadhaar_card") used by rules, seed files and member_documents.
    code: Mapped[str] = mapped_column(unique=True)
    name_en: Mapped[str]
    name_hi: Mapped[str]
    how_to_get_en: Mapped[str | None]
    how_to_get_hi: Mapped[str | None]
    official_link: Mapped[str | None]


class SchemeDocument(Base):
    __tablename__ = "scheme_documents"
    __table_args__ = (
        CheckConstraint(in_list_check("applies_to", DOCUMENT_APPLIES_TO), name="applies_to_valid"),
        # "Which schemes need this document?" is asked when a user adds or loses a document.
        Index("ix_scheme_documents_document_code", "document_code"),
    )

    # Belongs to a version: deleting a version removes its document list with it.
    scheme_version_id: Mapped[int] = mapped_column(
        ForeignKey("scheme_versions.id", ondelete="CASCADE"), primary_key=True
    )
    document_code: Mapped[str] = mapped_column(
        ForeignKey("documents.code", ondelete="RESTRICT"), primary_key=True
    )
    required: Mapped[bool] = mapped_column(server_default="true")
    applies_to: Mapped[str] = mapped_column(server_default="applicant")
