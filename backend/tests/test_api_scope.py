"""Which schemes are about the whole family (and are shown once), and which about a person."""

import pytest

from app.api.scope import is_for_whole_family
from app.db.seed import read_seed_files

YES = {"field": "paid_income_tax_last_year", "op": "is_true"}
RURAL = {"field": "area_type", "op": "eq", "value": "rural"}
HOUSE = {"field": "house_type", "op": "in", "value": ["no_house", "kutcha"]}
AGE = {"field": "age", "op": "gte", "value": 60}


def rules(*nodes: dict) -> dict:
    return {"all": list(nodes), "fixable": []}


@pytest.mark.parametrize(
    ("name", "scheme_rules", "expected"),
    [
        ("household facts only", rules(RURAL, HOUSE), True),
        ("a household yes/no (BPL)", rules({"field": "is_bpl", "op": "is_true"}), True),
        ("at least one member (PM-KISAN requirement)", rules({"any_member": YES}), True),
        ("no member (PMAY-G exclusion)", rules({"not": {"any_member": YES}}), True),
        (
            "household facts and a no-member exclusion (PMAY-G)",
            rules(RURAL, HOUSE, {"not": {"any_member": YES}}),
            True,
        ),
        (
            "an exclusion with a condition inside",
            rules({"not": {"any_member": {"all": [YES, AGE]}}}),
            True,
        ),
        ("a person's age", rules(AGE), False),
        ("a person's age beside household facts", rules(RURAL, AGE), False),
        ("a person's fact next to an exclusion", rules({"not": {"any_member": YES}}, AGE), False),
        ("a paper a person holds", rules({"field": "has_ration_card", "op": "is_true"}), False),
        ("any of: a household fact or a person's", rules({"any": [RURAL, AGE]}), False),
        ("any of: two household facts", rules({"any": [RURAL, HOUSE]}), True),
        ("not a person's fact", rules({"not": AGE}), False),
        ("nothing at all", {"all": []}, True),
        ("no rule list", {}, False),
        ("a node that is not a rule", rules({"mystery": 1}), False),
    ],
)
def test_pattern(name: str, scheme_rules: dict, expected: bool) -> None:
    assert is_for_whole_family(scheme_rules) is expected, name


def test_the_real_seed_schemes() -> None:
    by_slug = {s["slug"]: s["version"]["rules"] for s in read_seed_files().schemes}

    assert is_for_whole_family(by_slug["pm-kisan"])  # land and exclusions are all any_member rules
    assert not is_for_whole_family(by_slug["ignwps"])  # a woman of 40 or more: a person's rules
    assert not is_for_whole_family(by_slug["ignoaps"])
    assert not is_for_whole_family(by_slug["up-obc-post-matric"])
