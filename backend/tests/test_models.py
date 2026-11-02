from datetime import UTC, date, datetime
from typing import Any

import pytest
from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    Alert,
    Document,
    EligibilityResult,
    Household,
    Member,
    MemberDocument,
    Scheme,
    SchemeDocument,
    SchemeVersion,
    User,
)

RULES = {"all": [{"field": "age", "op": "gte", "value": 18}], "fixable": ["has_bank_account"]}


def make_scheme(slug: str = "demo", **overrides: Any) -> Scheme:
    values: dict[str, Any] = {
        "slug": slug,
        "name_en": "Demo scheme",
        "level": "central",
        "category": "farmer",
        "official_url": "https://example.gov.in",
    }
    return Scheme(**{**values, **overrides})


def make_version(scheme: Scheme, version_no: int = 1, **overrides: Any) -> SchemeVersion:
    values: dict[str, Any] = {
        "scheme": scheme,
        "version_no": version_no,
        "rules_json": RULES,
        "source_url": "https://example.gov.in/rules",
    }
    return SchemeVersion(**{**values, **overrides})


def make_family(db: Session, email: str = "a@example.com") -> tuple[User, Household, Member]:
    user = User(email=email)
    db.add(user)
    db.flush()
    household = Household(user_id=user.id, state="UP")
    db.add(household)
    db.flush()
    member = Member(household_id=household.id, nickname="Maa", relation="mother")
    db.add(member)
    db.flush()
    return user, household, member


def assert_rejected(db: Session, constraint: str, *objects: Any) -> None:
    """The database must refuse these rows, and for the named constraint (not some other reason).

    The savepoint keeps the test session usable after the failed statement.
    """
    with pytest.raises(IntegrityError) as error:
        with db.begin_nested():
            db.add_all(objects)
            db.flush()
    assert constraint in str(error.value.orig)


def assert_insert_rejected(db: Session, constraint: str, table: Any, **values: Any) -> None:
    """Same as assert_rejected, but a plain INSERT so the ORM cannot catch duplicates first."""
    with pytest.raises(IntegrityError) as error:
        with db.begin_nested():
            db.execute(insert(table).values(**values))
    assert constraint in str(error.value.orig)


def count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


# --- catalogue ---------------------------------------------------------------------------


def test_scheme_with_versions_and_current_pointer(db: Session) -> None:
    scheme = make_scheme()
    v1 = make_version(scheme, 1)
    v2 = make_version(scheme, 2, deadline_end=date(2027, 3, 31))
    scheme.current_version = v2
    db.add(scheme)
    db.flush()
    db.expire_all()

    saved = db.scalars(select(Scheme).where(Scheme.slug == "demo")).one()
    assert saved.status == "active"  # database default
    assert [v.version_no for v in saved.versions] == [1, 2]
    assert saved.current_version is not None
    assert saved.current_version.id == v2.id
    assert v1.rules_json == RULES
    assert saved.current_version.rules_json["fixable"] == ["has_bank_account"]  # JSONB round trip


def test_scheme_slug_is_unique(db: Session) -> None:
    db.add(make_scheme("same"))
    db.flush()
    assert_rejected(db, "uq_schemes_slug", make_scheme("same"))


def test_scheme_rejects_unknown_level_and_status(db: Session) -> None:
    assert_rejected(db, "ck_schemes_level_valid", make_scheme("a", level="district"))
    assert_rejected(db, "ck_schemes_status_valid", make_scheme("b", status="deleted"))


def test_state_scheme_needs_a_state(db: Session) -> None:
    assert_rejected(
        db, "state_scheme_has_state", make_scheme("no-state", level="state", state=None)
    )
    db.add(make_scheme("with-state", level="state", state="UP"))
    db.flush()


def test_version_number_is_unique_per_scheme(db: Session) -> None:
    scheme = make_scheme()
    make_version(scheme, 1)
    db.add(scheme)
    db.flush()
    assert_insert_rejected(
        db,
        "uq_scheme_versions_scheme_id_version_no",
        SchemeVersion.__table__,
        scheme_id=scheme.id,
        version_no=1,
        rules_json=RULES,
        source_url="https://example.gov.in/rules",
    )


def test_deadline_end_cannot_be_before_start(db: Session) -> None:
    scheme = make_scheme()
    db.add(scheme)
    db.flush()
    assert_insert_rejected(
        db,
        "ck_scheme_versions_deadline_order",
        SchemeVersion.__table__,
        scheme_id=scheme.id,
        version_no=1,
        rules_json=RULES,
        source_url="https://example.gov.in/rules",
        deadline_start=date(2027, 5, 1),
        deadline_end=date(2027, 4, 1),
    )


def test_scheme_document_links_version_to_catalogue(db: Session) -> None:
    db.add(Document(code="aadhaar_card", name_en="Aadhaar card", name_hi="आधार कार्ड"))
    scheme = make_scheme()
    version = make_version(scheme)
    db.add(scheme)
    db.flush()

    link = SchemeDocument(scheme_version_id=version.id, document_code="aadhaar_card")
    db.add(link)
    db.flush()
    db.refresh(link)
    assert link.required is True and link.applies_to == "applicant"  # defaults

    assert_rejected(
        db,
        "fk_scheme_documents_document_code_documents",
        SchemeDocument(scheme_version_id=version.id, document_code="nope"),
    )
    assert_insert_rejected(
        db,
        "ck_scheme_documents_applies_to_valid",
        SchemeDocument.__table__,
        scheme_version_id=version.id,
        document_code="aadhaar_card",
        applies_to="x",
        required=True,
    )


def test_document_code_is_unique(db: Session) -> None:
    db.add(Document(code="ration_card", name_en="Ration card", name_hi="राशन कार्ड"))
    db.flush()
    assert_rejected(
        db, "uq_documents_code", Document(code="ration_card", name_en="Other", name_hi="अन्य")
    )


# --- family ------------------------------------------------------------------------------


def test_user_email_must_be_lowercase_and_unique(db: Session) -> None:
    assert_rejected(db, "ck_users_email_lowercase", User(email="Mixed@Example.com"))
    db.add(User(email="ok@example.com"))
    db.flush()
    assert_rejected(db, "uq_users_email", User(email="ok@example.com"))


def test_member_value_checks(db: Session) -> None:
    _, household, _ = make_family(db)
    base = {"household_id": household.id, "nickname": "X", "relation": "son"}
    assert_rejected(db, "ck_members_gender_valid", Member(**base, gender="robot"))
    assert_rejected(db, "ck_members_birth_year_range", Member(**base, birth_year=1800))
    db.add(Member(**base))  # every optional attribute may stay unanswered
    db.flush()


def test_household_area_type_check(db: Session) -> None:
    user, _, _ = make_family(db)
    assert_rejected(
        db, "ck_households_area_type_valid", Household(user_id=user.id, area_type="suburb")
    )


def test_member_document_needs_known_document(db: Session) -> None:
    _, _, member = make_family(db)
    assert_rejected(
        db,
        "fk_member_documents_document_code_documents",
        MemberDocument(member_id=member.id, document_code="unknown", has=True),
    )

    db.add(Document(code="domicile", name_en="Domicile certificate", name_hi="निवास प्रमाण पत्र"))
    db.add(MemberDocument(member_id=member.id, document_code="domicile", has=False))
    db.flush()


def test_deleting_user_removes_all_family_data(db: Session) -> None:
    db.add(Document(code="domicile", name_en="Domicile", name_hi="निवास"))
    user, _, member = make_family(db)
    scheme = make_scheme()
    version = make_version(scheme)
    db.add(scheme)
    db.flush()
    db.add_all(
        [
            MemberDocument(member_id=member.id, document_code="domicile", has=True),
            EligibilityResult(member_id=member.id, scheme_version_id=version.id, status="eligible"),
            Alert(
                user_id=user.id,
                type="deadline",
                scheduled_for=datetime(2027, 1, 1, tzinfo=UTC),
            ),
        ]
    )
    db.flush()

    db.delete(user)
    db.flush()

    for model in (Household, Member, MemberDocument, EligibilityResult, Alert):
        assert count(db, model) == 0, model.__name__
    # The shared catalogue must survive a user deleting their account.
    assert count(db, Scheme) == 1 and count(db, Document) == 1


# --- results and alerts ------------------------------------------------------------------


def test_eligibility_result_rules(db: Session) -> None:
    _, _, member = make_family(db)
    scheme = make_scheme()
    version = make_version(scheme)
    db.add(scheme)
    db.flush()

    result = EligibilityResult(
        member_id=member.id, scheme_version_id=version.id, status="near_miss"
    )
    db.add(result)
    db.flush()
    db.refresh(result)
    assert result.failed_rules_json == []  # default

    # One answer per member and scheme version.
    assert_insert_rejected(
        db,
        "pk_eligibility_results",
        EligibilityResult.__table__,
        member_id=member.id,
        scheme_version_id=version.id,
        status="eligible",
        failed_rules_json=[],
    )
    assert_insert_rejected(
        db,
        "ck_eligibility_results_status_valid",
        EligibilityResult.__table__,
        member_id=member.id,
        scheme_version_id=version.id + 1000,
        status="maybe",
        failed_rules_json=[],
    )


def test_scheme_version_in_use_cannot_be_deleted(db: Session) -> None:
    _, _, member = make_family(db)
    scheme = make_scheme()
    version = make_version(scheme)
    db.add(scheme)
    db.flush()
    db.add(EligibilityResult(member_id=member.id, scheme_version_id=version.id, status="eligible"))
    db.flush()

    with pytest.raises(IntegrityError) as error:
        with db.begin_nested():
            db.delete(version)
            db.flush()
    assert "fk_eligibility_results_scheme_version_id_scheme_versions" in str(error.value.orig)


def test_alert_defaults_and_checks(db: Session) -> None:
    user, _, _ = make_family(db)
    when = datetime(2027, 1, 1, tzinfo=UTC)
    alert = Alert(user_id=user.id, type="new_scheme", scheduled_for=when)
    db.add(alert)
    db.flush()
    db.refresh(alert)
    assert alert.status == "pending" and alert.payload_json == {}

    assert_rejected(
        db, "ck_alerts_type_valid", Alert(user_id=user.id, type="spam", scheduled_for=when)
    )
