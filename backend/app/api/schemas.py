"""Request and response shapes. Everything a client sends is checked here before it reaches the
database, so a wrong value is a clear 422 and never a database error.

Rules of thumb used below:
  * extra="forbid": an unknown field (a typo, or someone sending "aadhaar_number") is rejected,
    not silently ignored. This is also how we keep identity numbers out (CLAUDE.md rule 3).
  * StrictBool: only real true/false. Pydantic would otherwise accept "yes", 1 or "on".
  * Optional facts may be null. Null means "not answered", which the rules engine treats as unknown.
"""

import uuid
from datetime import date, datetime
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.db.models.family import AREA_TYPES, GENDERS
from app.rules.fields import GOVT_EMPLOYEE_VALUES, PENSION_BAND_VALUES
from app.rules.values import (
    CATEGORY_VALUES,
    EDUCATION_VALUES,
    INCOME_BAND_VALUES,
    MARITAL_STATUS_VALUES,
    OCCUPATION_VALUES,
)

MAX_MEMBERS_PER_HOUSEHOLD = 20
MAX_DOCUMENTS_PER_REQUEST = 100

Text = StringConstraints(strip_whitespace=True)
Nickname = Annotated[str, Text, Field(min_length=1, max_length=50)]
Relation = Annotated[str, Text, Field(min_length=1, max_length=30)]
# Two capital letters, the same form the rules use ("UP").
StateCode = Annotated[str, Field(pattern=r"^[A-Z]{2}$")]
District = Annotated[str, Text, Field(min_length=1, max_length=60)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- households ----------------------------------------------------------------------------


class HouseholdFields(Strict):
    state: StateCode | None = None
    district: District | None = None
    area_type: Literal[*AREA_TYPES] | None = None  # type: ignore[valid-type]
    income_band: Literal[*INCOME_BAND_VALUES] | None = None  # type: ignore[valid-type]
    category: Literal[*CATEGORY_VALUES] | None = None  # type: ignore[valid-type]


class HouseholdCreate(HouseholdFields):
    pass


class HouseholdUpdate(HouseholdFields):
    """Only the fields that are sent change. Sending null clears an answer."""


class HouseholdOut(HouseholdFields):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class HouseholdCreated(HouseholdOut):
    access_token: str = Field(description="Shown once. Send as 'Authorization: Bearer <token>'.")
    token_notice: str


TOKEN_NOTICE = (
    "Save this access token now. It is shown only once and cannot be recovered or reset: we store "
    "only a scrambled copy. If it is lost, this household can no longer be opened or deleted."
)


# --- members -------------------------------------------------------------------------------


def _this_year() -> int:
    return date.today().year


class MemberFields(Strict):
    """Every answer about a person. All optional here; MemberCreate adds the two required ones."""

    birth_year: Annotated[int, Field(ge=1900)] | None = None
    gender: Literal[*GENDERS] | None = None  # type: ignore[valid-type]
    marital_status: Literal[*MARITAL_STATUS_VALUES] | None = None  # type: ignore[valid-type]
    occupation: Literal[*OCCUPATION_VALUES] | None = None  # type: ignore[valid-type]
    education: Literal[*EDUCATION_VALUES] | None = None  # type: ignore[valid-type]
    is_student: StrictBool | None = None
    disability: StrictBool | None = None
    owns_cultivable_land: StrictBool | None = None
    paid_income_tax_last_year: StrictBool | None = None
    govt_employee: Literal[*GOVT_EMPLOYEE_VALUES] | None = None  # type: ignore[valid-type]
    pension_band: Literal[*PENSION_BAND_VALUES] | None = None  # type: ignore[valid-type]
    is_registered_professional: StrictBool | None = None
    holds_constitutional_post: StrictBool | None = None
    is_remarried: StrictBool | None = None

    @field_validator("birth_year")
    @classmethod
    def not_in_the_future(cls, value: int | None) -> int | None:
        if value is not None and value > _this_year():
            raise ValueError("birth_year cannot be in the future")
        return value


class MemberCreate(MemberFields):
    nickname: Nickname  # a nickname, never a legal name
    relation: Relation


class MemberUpdate(MemberFields):
    nickname: Nickname | None = None
    relation: Relation | None = None

    @model_validator(mode="after")
    def required_fields_cannot_be_cleared(self) -> Self:
        # "nickname": null would otherwise slip through as "not sent" and then hit the database.
        for name in ("nickname", "relation"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be cleared")
        return self


class MemberOut(MemberFields):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    nickname: str
    relation: str
    # Document code -> has it (true) or not (false). A code that is absent was never answered.
    documents: dict[str, bool] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class DocumentsIn(Strict):
    documents: Annotated[dict[str, StrictBool], Field(max_length=MAX_DOCUMENTS_PER_REQUEST)]


class DocumentsOut(BaseModel):
    documents: dict[str, bool]


# --- schemes (public) ----------------------------------------------------------------------


class SchemeSummary(BaseModel):
    slug: str
    name_en: str
    name_hi: str | None
    level: str
    state: str | None
    category: str
    official_url: str
    benefit_text_en: str | None
    benefit_text_hi: str | None
    deadline_start: date | None
    deadline_end: date | None
    # False when no human has checked this scheme yet. The UI shows "Not yet verified"; we never
    # hide such schemes (CLAUDE.md: honest labels, not an empty product).
    verified: bool
    verified_at: datetime | None


class DocumentSummary(BaseModel):
    code: str
    name_en: str
    name_hi: str
    # One answer for the whole family (ration card, BPL card, family register): ask only once.
    household_level: bool


class SchemeDocumentOut(BaseModel):
    code: str
    name_en: str
    name_hi: str
    how_to_get_en: str | None
    how_to_get_hi: str | None
    official_link: str | None
    required: bool
    applies_to: str


class SchemeDetail(SchemeSummary):
    source_url: str
    version_no: int
    documents: list[SchemeDocumentOut]


def sent_fields(data: BaseModel) -> dict[str, Any]:
    """Only the fields the client actually sent (used by PATCH)."""
    return data.model_dump(exclude_unset=True)
