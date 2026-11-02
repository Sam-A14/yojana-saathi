"""Whole-family checks: data/test_profiles/*.json run through the real rules in data/schemes_seed/.

Each profile file holds a household, its members, and the answer we expect for every member and
scheme. The expected answers were worked out by hand from the scheme's published conditions, not
copied from the engine's output, so a wrong rule OR a wrong engine shows up as a failure here.

Optional key "excluded_by": {scheme: [nicknames]} also checks WHO caused a failure.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from app.db.seed import DEFAULT_DATA_DIR, read_seed_files
from app.rules.engine import HouseholdFacts, evaluate

PROFILE_FILES = sorted((DEFAULT_DATA_DIR / "test_profiles").glob("*.json"))
RULES = {s["slug"]: s["version"]["rules"] for s in read_seed_files().schemes}


def test_there_are_at_least_fifteen_profiles() -> None:
    assert len(PROFILE_FILES) >= 15


@pytest.mark.parametrize("path", PROFILE_FILES, ids=lambda p: p.stem)
def test_profile(path: Path) -> None:
    profile: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    household = HouseholdFacts(profile["household"], profile["members"])
    names = {m["nickname"] for m in profile["members"]}
    assert set(profile["expected"]) == {"pm-kisan", "ignwps"}, "every profile covers both schemes"

    for slug, expected in profile["expected"].items():
        # Every member needs an expectation, so adding a person forces a decision about them.
        assert set(expected) == names, f"{path.name}: expected answers must cover {sorted(names)}"
        actual = {
            m["nickname"]: evaluate(m, household, RULES[slug]).status for m in profile["members"]
        }
        assert actual == expected, f"{path.name} / {slug}"

    for slug, who in profile.get("excluded_by", {}).items():
        first = profile["members"][0]
        failed = evaluate(first, household, RULES[slug]).failed
        assert sorted({n for r in failed for n in r.matched_members}) == sorted(who)
