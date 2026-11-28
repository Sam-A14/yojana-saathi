"""Is a scheme about one person, or about the whole family?

A scheme is for the whole family when every rule in it is about the household (state, area, house,
income, category, BPL) or about the members as a group (`any_member`, with or without `not`: "at
least one member owns farmland", "no member pays income tax"). The answer for such a scheme is the
same whichever member you ask, so the dashboard shows it once, not on every member's card.

A rule about a person (age, gender, studying, a paper that person holds) makes the scheme a
person's. This only reads the rule JSON; it never decides eligibility, which stays in the engine.
"""

from typing import Any

from app.rules.fields import HOUSEHOLD_FIELDS


def is_for_whole_family(rules: dict[str, Any]) -> bool:
    top_level = rules.get("all")
    return isinstance(top_level, list) and all(_about_the_family(node) for node in top_level)


def _about_the_family(node: Any) -> bool:
    if not isinstance(node, dict):
        return False
    if "field" in node:
        return (
            node["field"] in HOUSEHOLD_FIELDS
        )  # a person's fact, or a has_<paper>: not family-wide
    if "any_member" in node:
        return True  # whatever is inside, the question is asked of the household as a group
    if "not" in node:
        return _about_the_family(node["not"])
    for kind in ("all", "any"):
        if kind in node:
            return isinstance(node[kind], list) and all(_about_the_family(n) for n in node[kind])
    return False
