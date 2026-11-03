"""Family data. Deleting a user removes everything below them (privacy: full account deletion).

Deletion is done by the database (ON DELETE CASCADE), so these tables have no ORM relationships.
Value lists for fields such as marital_status, category and income_band are not enforced here;
they are defined once in the rules field list (added with the rules engine) and checked by the API.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_column, in_list_check, updated_at_column
from app.rules.fields import GOVT_EMPLOYEE_VALUES, PENSION_BAND_VALUES

LANGUAGES = ("en", "hi")
ALERT_CHANNELS = ("email",)
AREA_TYPES = ("rural", "urban")
GENDERS = ("male", "female", "other")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(in_list_check("language", LANGUAGES), name="language_valid"),
        CheckConstraint(in_list_check("alert_channel", ALERT_CHANNELS), name="alert_channel_valid"),
        # Two spellings of one address must not become two accounts.
        CheckConstraint("email = lower(email)", name="email_lowercase"),
    )

    # UUIDs, not counters, so ids in URLs cannot be guessed one after another.
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(unique=True)
    language: Mapped[str] = mapped_column(server_default="en")
    alert_channel: Mapped[str] = mapped_column(server_default="email")
    created_at: Mapped[datetime] = created_at_column()


class Household(Base):
    __tablename__ = "households"
    __table_args__ = (
        CheckConstraint(in_list_check("area_type", AREA_TYPES), name="area_type_valid"),
        # A household nobody can open (no login, no token) could never be reached or deleted.
        CheckConstraint("user_id IS NOT NULL OR access_token_hash IS NOT NULL", name="has_owner"),
        Index("ix_households_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # NULL until the family logs in: before login, the access token below is the only key.
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # SHA-256 of the access token. The token itself is never stored, so a database leak does not
    # give anyone access to a household. Unique, so lookup by hash is also an index lookup.
    access_token_hash: Mapped[str | None] = mapped_column(unique=True)
    # Attributes are nullable: "not answered yet" must stay different from any real answer,
    # because the rules engine turns a missing attribute into "unknown", not "not eligible".
    state: Mapped[str | None]
    district: Mapped[str | None]
    area_type: Mapped[str | None]
    income_band: Mapped[str | None]
    category: Mapped[str | None]
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class Member(Base):
    __tablename__ = "members"
    __table_args__ = (
        CheckConstraint(in_list_check("gender", GENDERS), name="gender_valid"),
        CheckConstraint("birth_year BETWEEN 1900 AND 2100", name="birth_year_range"),
        CheckConstraint(
            in_list_check("govt_employee", GOVT_EMPLOYEE_VALUES), name="govt_employee_valid"
        ),
        CheckConstraint(
            in_list_check("pension_band", PENSION_BAND_VALUES), name="pension_band_valid"
        ),
        Index("ix_members_household_id", "household_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    # A nickname, never a legal name: we do not need to know who the person is.
    nickname: Mapped[str]
    relation: Mapped[str]
    # Birth year, not birth date: enough for age rules, and less personal data to hold.
    birth_year: Mapped[int | None]
    gender: Mapped[str | None]
    marital_status: Mapped[str | None]
    occupation: Mapped[str | None]
    education: Mapped[str | None]
    is_student: Mapped[bool | None]
    disability: Mapped[bool | None]
    # Facts used by exclusion rules (for example PM-KISAN). All nullable for the same reason as
    # above: "not answered" must stay different from "no". Yes/no answers only, never a number
    # such as a PAN or a pension amount.
    owns_cultivable_land: Mapped[bool | None]
    paid_income_tax_last_year: Mapped[bool | None]
    govt_employee: Mapped[str | None]  # none / group_d / other
    pension_band: Mapped[str | None]  # none / below_10k / 10k_plus
    is_registered_professional: Mapped[bool | None]
    holds_constitutional_post: Mapped[bool | None]
    is_remarried: Mapped[bool | None]
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class MemberDocument(Base):
    """Whether a member holds a document. Only yes/no; never a document number."""

    __tablename__ = "member_documents"

    member_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE"), primary_key=True
    )
    document_code: Mapped[str] = mapped_column(
        ForeignKey("documents.code", ondelete="RESTRICT"), primary_key=True
    )
    has: Mapped[bool]
