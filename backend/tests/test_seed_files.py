"""Checks on the committed data files. No database needed."""

import copy
import json
from typing import Any

import pytest

from app.db.seed import (
    DEFAULT_DATA_DIR,
    TEMPLATE_NAME,
    SeedError,
    _validator,
    read_seed_files,
    schema_problems,
    scheme_file_problems,
)

SCHEMA_PATH = DEFAULT_DATA_DIR / "scheme.schema.json"
# Member and household attributes a rule may use. Changing this list is a deliberate act: update
# data/scheme.schema.json (and backend/app/rules/fields.py once it exists) in the same change.
ATTRIBUTE_FIELDS = {
    "age",
    "gender",
    "marital_status",
    "occupation",
    "education",
    "is_student",
    "disability",
    "state",
    "district",
    "area_type",
    "income_band_max",
    "category",
    "owns_cultivable_land",
    "paid_income_tax_last_year",
    "govt_employee",
    "pension_band",
    "is_registered_professional",
    "holds_constitutional_post",
    "is_remarried",
}


def load(name: str) -> dict[str, Any]:
    return json.loads((DEFAULT_DATA_DIR / name).read_text(encoding="utf-8"))


def rule_problems(*nodes: dict[str, Any], fixable: list[str] | None = None) -> list[str]:
    scheme = copy.deepcopy(load("schemes_seed/pm-kisan.json"))
    scheme["version"]["rules"] = {"all": list(nodes)}
    if fixable is not None:
        scheme["version"]["rules"]["fixable"] = fixable
    return schema_problems(_validator(SCHEMA_PATH), scheme)


def test_committed_files_are_valid() -> None:
    data = read_seed_files()

    assert len(data.documents) >= 15
    assert {s["slug"] for s in data.schemes} == {"pm-kisan", "ignwps"}


def test_template_is_valid_and_never_loaded() -> None:
    template = load(f"schemes_seed/{TEMPLATE_NAME}")
    known = {d["code"] for d in load("documents.json")["documents"]}

    assert schema_problems(_validator(SCHEMA_PATH), template) == []
    # file_stem=None: the template's slug is a placeholder, not a file name.
    assert scheme_file_problems(template, known, None) == []
    assert "replace-with-scheme-slug" not in {s["slug"] for s in read_seed_files().schemes}


def test_examples_are_marked_unverified() -> None:
    for slug in ("pm-kisan", "ignwps"):
        scheme = load(f"schemes_seed/{slug}.json")
        assert scheme["labeller_notes"]["example"] is True
        assert scheme["labeller_notes"]["source_reached"] is False
        assert scheme["version"]["verified_at"] is None


def test_field_list_matches_attributes_and_document_catalogue() -> None:
    """A document added to documents.json needs its has_<code> field in the schema, and back."""
    allowed = set(json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))["$defs"]["field"]["enum"])
    document_fields = {f"has_{d['code']}" for d in load("documents.json")["documents"]}

    assert allowed == ATTRIBUTE_FIELDS | document_fields


def test_valid_rules_are_accepted() -> None:
    assert (
        rule_problems(
            {"field": "age", "op": "between", "value": [18, 60]},
            {"field": "category", "op": "in", "value": ["SC", "ST"]},
            {"not": {"field": "is_student", "op": "is_true"}},
            {
                "any": [
                    {"field": "state", "op": "eq", "value": "UP"},
                    {"field": "area_type", "op": "neq", "value": "urban"},
                ]
            },
            fixable=["has_land_record"],
        )
        == []
    )


@pytest.mark.parametrize(
    ("node", "fragment"),
    [
        ({"field": "incme_band_max", "op": "lte", "value": 1}, "not one of"),
        ({"field": "age", "op": "greater", "value": 1}, "not one of"),
        ({"field": "age", "op": "between", "value": [1, 2, 3]}, "too long"),
        ({"field": "age", "op": "between", "value": [1]}, "too short"),
        ({"field": "age", "op": "gte", "value": "18"}, "not of type 'number'"),
        ({"field": "age", "op": "gte"}, "'value' is a required property"),
        ({"field": "category", "op": "in", "value": "SC"}, "is not of type 'array'"),
        ({"field": "is_student", "op": "is_true", "value": True}, "does not allow"),
        ({"any": [{"field": "age", "op": "gte"}]}, "'value' is a required property"),
        ({"all": []}, "should be non-empty"),
        ({"field": "age", "op": "gte", "value": 1, "all": []}, "Additional properties"),
    ],
)
def test_bad_rules_are_rejected_with_a_useful_message(node: dict[str, Any], fragment: str) -> None:
    problems = rule_problems(node)

    assert problems, "expected the schema to reject this rule"
    assert any(fragment in p for p in problems), problems


def test_fixable_must_name_a_known_field() -> None:
    assert rule_problems({"field": "age", "op": "gte", "value": 1}, fixable=["has_bank"])


def test_scheme_level_and_state_must_agree() -> None:
    validator = _validator(SCHEMA_PATH)
    scheme = load("schemes_seed/pm-kisan.json")

    central_with_state = {**scheme, "state": "UP"}
    state_without_state = {**scheme, "level": "state", "state": None}
    state_ok = {**scheme, "level": "state", "state": "UP"}

    assert schema_problems(validator, central_with_state)
    assert schema_problems(validator, state_without_state)
    assert schema_problems(validator, state_ok) == []


def test_typo_in_a_scheme_key_is_rejected() -> None:
    scheme = {**load("schemes_seed/pm-kisan.json"), "catgory": "farmer"}

    assert any("catgory" in p for p in schema_problems(_validator(SCHEMA_PATH), scheme))


def test_cross_file_checks() -> None:
    scheme = copy.deepcopy(load("schemes_seed/pm-kisan.json"))
    known = {d["code"] for d in load("documents.json")["documents"]}
    scheme["version"]["documents"].append({"code": "made_up_document"})
    scheme["version"]["documents"].append({"code": "aadhaar_card"})  # already listed
    scheme["version"]["deadline_start"] = "2027-05-01"
    scheme["version"]["deadline_end"] = "2027-04-01"

    problems = scheme_file_problems(scheme, known, "other-name")

    assert any("must equal the file name" in p for p in problems)
    assert any("'made_up_document' is not in documents.json" in p for p in problems)
    assert any("'aadhaar_card' is listed twice" in p for p in problems)
    assert any("deadline_end is before deadline_start" in p for p in problems)


def test_loader_reports_every_problem_at_once(tmp_path: Any) -> None:
    for name in ("documents.json", "documents.schema.json", "scheme.schema.json"):
        (tmp_path / name).write_text((DEFAULT_DATA_DIR / name).read_text(encoding="utf-8"))
    seeds = tmp_path / "schemes_seed"
    seeds.mkdir()
    (seeds / "broken-json.json").write_text("{ not json")
    good = load("schemes_seed/pm-kisan.json")
    (seeds / "wrong-name.json").write_text(json.dumps(good))  # slug pm-kisan != file name
    unknown_doc = copy.deepcopy(good) | {"slug": "unknown-doc"}
    unknown_doc["version"]["documents"] = [{"code": "nope"}]
    (seeds / "unknown-doc.json").write_text(json.dumps(unknown_doc))

    with pytest.raises(SeedError) as error:
        read_seed_files(tmp_path)

    assert len(error.value.problems) == 3, error.value.problems


def test_engine_field_list_matches_the_test_pin() -> None:
    from app.rules.fields import ATTRIBUTE_FIELDS as ENGINE_FIELDS

    assert ENGINE_FIELDS == ATTRIBUTE_FIELDS


def test_any_member_is_accepted_by_the_schema() -> None:
    rule = {"not": {"any_member": {"field": "paid_income_tax_last_year", "op": "is_true"}}}

    assert rule_problems(rule) == []
    assert rule_problems({"any_member": rule["not"]["any_member"], "among": "household"}) == []


@pytest.mark.parametrize(
    "node",
    [
        {"any_member": {"field": "age", "op": "gte", "value": 1}, "among": "everyone"},
        {"any_member": {"field": "age", "op": "gte", "value": 1}, "extra": 1},
        {"any_member": {"field": "agee", "op": "gte", "value": 1}},
        {"any_member": []},
    ],
)
def test_bad_any_member_is_rejected(node: dict[str, Any]) -> None:
    assert rule_problems(node)


def test_engine_accepts_every_committed_scheme() -> None:
    """The schema cannot check value lists (grup_d) or the combination rules; the engine can."""
    from app.rules.engine import validate_rules

    for scheme in read_seed_files().schemes:
        validate_rules(scheme["version"]["rules"])


def test_seed_folder_holds_only_json_files() -> None:
    """Source text belongs in data/scheme_sources/; a stray .txt here was once committed."""
    stray = sorted(
        path.name
        for path in (DEFAULT_DATA_DIR / "schemes_seed").iterdir()
        if path.suffix != ".json"
    )

    assert stray == [], f"move these to data/scheme_sources/ or delete them: {stray}"
