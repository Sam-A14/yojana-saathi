"""How close is an extracted rule set to the hand-labelled seed file for the same scheme?

Method: cut each rule tree into LEAF conditions and compare the two sets.
  leaf = (wrappers around it, field, operator, value)
  e.g.  not > any_member > govt_employee eq "other"

Why leaves and not whole trees: "condition by condition" is the target (PROJECT_SPEC section 10),
and comparing sets makes the order of rules, of children inside all/any, and of values inside `in`
irrelevant, so equivalent orderings count as equal.

Wrappers are part of a leaf because "no member owns land" and "some member owns land" are opposite
rules about the same field. A few harmless shapes are flattened so they compare equal: all inside
all, any inside any, a not inside a not, and a group with a single child.

Known limit: a leaf does not remember which sibling it was grouped with. If the model regroups
conditions inside two same-shaped groups (all[a,b] + all[c,d] written as all[a,c] + all[b,d]) the
score still says 100%. A human reviews every proposal; the score is a guide, not a proof.

Two scores are reported. EXACT compares the leaves as written. NORMALISED first rewrites both rule
trees into one canonical form, so two spellings of the same condition stop counting as a miss plus
an extra. Only rewrites that cannot change an answer are made (see `normalise`); the report says
which ones fired. Anything we cannot prove equivalent stays a difference.

Precision = matched / extracted (how much of what the model wrote is right).
Recall    = matched / expected  (how much of the labelled rules the model found).
Overall numbers add up the counts of all schemes first (micro-average), so a big scheme weighs more.

Run on saved proposals:  python -m app.pipeline.accuracy proposal.json [more.json ...]
"""

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.db.seed import DEFAULT_DATA_DIR

# Re-exported under the same names: the tests and callers import them from here.
from app.pipeline.field_types import BOOLEAN_FIELDS as BOOLEAN_FIELDS
from app.pipeline.field_types import CLOSED_VALUES, is_boolean_field

# (wrappers from the top down, field, operator, value as canonical JSON text)
Leaf = tuple[tuple[str, ...], str, str, str]


class AccuracyError(Exception):
    """The rules cannot be compared (missing seed file, or too malformed to read)."""


# --- cutting a rule tree into leaves -------------------------------------------------------


def leaf_conditions(rules: Any) -> set[Leaf]:
    if not isinstance(rules, Mapping) or not isinstance(rules.get("all"), list):
        raise AccuracyError("rules must be an object with a top-level 'all' list")
    leaves: set[Leaf] = set()
    for child in rules["all"]:
        _collect(child, (), leaves)
    return leaves


def _collect(node: Any, wrappers: tuple[str, ...], out: set[Leaf]) -> None:
    if not isinstance(node, Mapping):
        raise AccuracyError(f"a rule must be an object, got {node!r}")
    if "field" in node:
        op = str(node.get("op"))
        out.add((wrappers, str(node["field"]), op, _value_key(op, node.get("value"))))
    elif "all" in node or "any" in node:
        kind = "all" if "all" in node else "any"
        children = node[kind]
        if not isinstance(children, list):
            raise AccuracyError(f"'{kind}' must be a list")
        # The top level is an implicit 'all', so the parent of a first-level rule is 'all'.
        parent = wrappers[-1] if wrappers else "all"
        transparent = len(children) == 1 or parent == kind
        for child in children:
            _collect(child, wrappers if transparent else wrappers + (kind,), out)
    elif "not" in node:
        # not(not(x)) is x.
        double = bool(wrappers) and wrappers[-1] == "not"
        _collect(node["not"], wrappers[:-1] if double else wrappers + ("not",), out)
    elif "any_member" in node:
        among = node.get("among", "household")
        label = "any_member" if among == "household" else f"any_member[{among}]"
        _collect(node["any_member"], wrappers + (label,), out)
    else:
        raise AccuracyError(f"unrecognised rule: {node!r}")


def _value_key(op: str, value: Any) -> str:
    if op in ("in", "not_in") and isinstance(value, list):
        # A set of allowed values: order and repeats do not matter.
        unique = {_canonical(item) for item in value}
        return "[" + ",".join(sorted(unique)) + "]"
    return _canonical(value)


def _canonical(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)  # 200000.0 and 200000 are the same number
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def describe(leaf: Leaf) -> str:
    wrappers, field, op, value = leaf
    condition = f"{field} {op}" + ("" if value == "null" else f" {value}")
    return " > ".join((*wrappers, condition))


# --- normalising: one canonical spelling for conditions that mean the same ---------------------

# CLOSED_VALUES (fields with a fixed list of answers) and BOOLEAN_FIELDS (yes/no facts) live in
# field_types.py, shared with the extraction validator. For a closed field "not group_d" and
# "none or other" are the same condition; for a yes/no field "eq true" and "is_true" are.

_SET_OPERATORS = ("eq", "neq", "in", "not_in")


def normalise(rules: Any) -> tuple[dict[str, Any], list[str]]:
    """Rewrite equivalent forms into one canonical form. Returns (rules, what was rewritten).

    1. eq true on a yes/no field becomes is_true.
    2. On a field with a closed list, every eq / neq / in / not_in becomes one "in [sorted set]"
       (neq a on [a,b,c] is in [b,c]). Several such conditions on the same field inside one
       all (intersect) or one any (union) merge into one. A missing fact is unknown for every
       operator, and stays unknown after the rewrite, so no answer changes.
    Not rewritten, so still a difference: a field without a closed list, a value that is not in the
    list, eq false, and anything under a "not" (not(eq a) is not turned into neq a).
    The input is not modified. Call leaf_conditions first: this expects readable rules.
    """
    fired: list[str] = []
    children = _normalise_children("all", rules["all"], fired)
    return {**rules, "all": children}, fired


def _normalise_node(node: Any, fired: list[str]) -> Any:
    if "field" in node:
        return _normalise_leaf(node, fired)
    for kind in ("all", "any"):
        if kind in node:
            return {kind: _normalise_children(kind, node[kind], fired)}
    if "not" in node:
        return {"not": _normalise_node(node["not"], fired)}
    if "any_member" in node:
        return {**node, "any_member": _normalise_node(node["any_member"], fired)}
    return node


def _normalise_leaf(leaf: dict[str, Any], fired: list[str]) -> dict[str, Any]:
    field, op, value = leaf["field"], leaf.get("op"), leaf.get("value")
    if op == "eq" and value is True and is_boolean_field(field):
        fired.append(f"{field}: eq true -> is_true")
        return {"field": field, "op": "is_true"}
    allowed = _closed_set(field, op, value)
    if allowed is None:
        return leaf
    canonical = {"field": field, "op": "in", "value": sorted(allowed)}
    if leaf != canonical:
        fired.append(f"{field}: {op} {_value_key(op or '', value)} -> in {sorted(allowed)}")
    return canonical


def _closed_set(field: str, op: Any, value: Any) -> set[str] | None:
    """The values a set-style condition on a closed-list field allows, or None if it is not one
    (other operator, no closed list, or a value outside the list: not safe to reason about)."""
    universe = CLOSED_VALUES.get(field)
    if universe is None or op not in _SET_OPERATORS:
        return None
    listed = value if op in ("in", "not_in") else [value]
    if not isinstance(listed, list) or not all(isinstance(v, str) for v in listed):
        return None
    if not set(listed) <= set(universe):
        return None
    return set(listed) if op in ("eq", "in") else set(universe) - set(listed)


def _is_set_condition(node: dict[str, Any]) -> bool:
    return _closed_set(node["field"], node.get("op"), node.get("value")) is not None


def _normalise_children(kind: str, children: list[Any], fired: list[str]) -> list[Any]:
    flat: list[Any] = []
    for child in children:
        done = _normalise_node(child, fired)
        # all inside all, any inside any: the same condition set, so splice them in.
        flat.extend(done[kind] if isinstance(done, dict) and kind in done else [done])

    by_field: dict[str, list[int]] = {}
    for position, node in enumerate(flat):
        field = node.get("field") if isinstance(node, dict) else None
        if field in CLOSED_VALUES and _is_set_condition(node):
            by_field.setdefault(field, []).append(position)

    drop: set[int] = set()
    for field, positions in by_field.items():
        if len(positions) < 2:
            continue
        sets = [set(flat[i]["value"]) for i in positions]
        merged = set.intersection(*sets) if kind == "all" else set.union(*sets)
        if not merged:
            continue  # "never true" cannot be written as an "in" list: leave it, as a difference
        flat[positions[0]] = {"field": field, "op": "in", "value": sorted(merged)}
        drop.update(positions[1:])
        count = len(positions)
        fired.append(f"{field}: {count} conditions under one {kind} -> in {sorted(merged)}")
    return [node for position, node in enumerate(flat) if position not in drop]


# --- comparing -----------------------------------------------------------------------------


@dataclass(frozen=True)
class LeafSets:
    matched: list[Leaf]
    missed: list[Leaf]  # in the seed file, not found in the extraction
    extra: list[Leaf]  # in the extraction, not in the seed file

    @property
    def expected_count(self) -> int:
        return len(self.matched) + len(self.missed)

    @property
    def extracted_count(self) -> int:
        return len(self.matched) + len(self.extra)


@dataclass(frozen=True)
class SchemeAccuracy:
    slug: str
    # The exact comparison (leaves as written).
    matched: list[Leaf]
    missed: list[Leaf]
    extra: list[Leaf]
    fixable_missed: list[str]
    fixable_extra: list[str]
    # The same comparison after normalise(), and which rewrites fired on each side.
    normalised: LeafSets
    rewrites_expected: list[str]
    rewrites_extracted: list[str]

    @property
    def expected_count(self) -> int:
        return len(self.matched) + len(self.missed)

    @property
    def extracted_count(self) -> int:
        return len(self.matched) + len(self.extra)


def _compare_leaves(want: set[Leaf], got: set[Leaf]) -> LeafSets:
    return LeafSets(sorted(want & got), sorted(want - got), sorted(got - want))


def compare_rules(slug: str, expected: Any, extracted: Any) -> SchemeAccuracy:
    want, got = leaf_conditions(expected), leaf_conditions(extracted)
    want_fixable, got_fixable = _fixable(expected), _fixable(extracted)
    exact = _compare_leaves(want, got)
    norm_expected, fired_expected = normalise(expected)
    norm_extracted, fired_extracted = normalise(extracted)
    return SchemeAccuracy(
        slug=slug,
        matched=exact.matched,
        missed=exact.missed,
        extra=exact.extra,
        fixable_missed=sorted(want_fixable - got_fixable),
        fixable_extra=sorted(got_fixable - want_fixable),
        normalised=_compare_leaves(leaf_conditions(norm_expected), leaf_conditions(norm_extracted)),
        rewrites_expected=fired_expected,
        rewrites_extracted=fired_extracted,
    )


def _fixable(rules: Any) -> set[str]:
    names = rules.get("fixable", []) if isinstance(rules, Mapping) else []
    return {str(n) for n in names} if isinstance(names, list) else set()


def seed_path(slug: str, data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    return data_dir / "schemes_seed" / f"{slug}.json"


def compare_to_seed(
    slug: str, extracted_scheme: Mapping[str, Any], data_dir: Path = DEFAULT_DATA_DIR
) -> SchemeAccuracy | None:
    """None when there is no seed file for this slug (nothing to compare against)."""
    path = seed_path(slug, data_dir)
    if not path.is_file():
        return None
    try:
        expected = json.loads(path.read_text(encoding="utf-8"))["version"]["rules"]
        extracted = extracted_scheme["version"]["rules"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise AccuracyError(f"cannot read rules for '{slug}': {error!r}") from error
    return compare_rules(slug, expected, extracted)


# --- showing the result --------------------------------------------------------------------


def _ratio(matched: int, total: int) -> str:
    return "n/a" if total == 0 else f"{matched / total:.0%} ({matched}/{total})"


def _scores(label: str, matched: int, extracted: int, expected: int) -> str:
    return f"  {label} precision {_ratio(matched, extracted)}, recall {_ratio(matched, expected)}"


def _lists(missed: list[Leaf], extra: list[Leaf], indent: str) -> list[str]:
    lines: list[str] = []
    if missed:
        lines.append(f"{indent}Missed (in the seed file, not extracted):")
        lines.extend(f"{indent}  - {describe(leaf)}" for leaf in missed)
    if extra:
        lines.append(f"{indent}Extra (extracted, not in the seed file):")
        lines.extend(f"{indent}  - {describe(leaf)}" for leaf in extra)
    return lines


def _rewrite_lines(who: str, fired: Counter[str]) -> list[str]:
    return [f"    {who}: {text}" + (f" (x{n})" if n > 1 else "") for text, n in fired.items()]


def _rewrites_section(expected: list[str], extracted: list[str]) -> list[str]:
    """Rewrites that fired, minus those that fired identically on both sides.

    A rewrite both sides share (the seed file and the model both wrote `eq other`) cannot change
    the score, so listing it only buries the ones that did. How many were left out is said.
    """
    seed, model = Counter(expected), Counter(extracted)
    shared = seed & model
    lines = _rewrite_lines("seed file", seed - shared) + _rewrite_lines(
        "extraction", model - shared
    )
    if not lines and not shared:
        return []
    heading = "  Rewrites that fired (those that differ between the two sides):"
    if not lines:
        heading = "  Rewrites that fired: none that differ between the two sides."
    lines = [heading, *lines]
    if shared:
        lines.append(f"    ({shared.total()} identical rewrites on both sides not listed)")
    return lines


def render_accuracy(results: list[SchemeAccuracy]) -> str:
    lines: list[str] = []
    for r in results:
        n = r.normalised
        lines.append(f"{r.slug}:")
        lines.append(_scores("exact:     ", len(r.matched), r.extracted_count, r.expected_count))
        lines.append(_scores("normalised:", len(n.matched), n.extracted_count, n.expected_count))
        lines.extend(_lists(r.missed, r.extra, "  "))
        lines.extend(_rewrites_section(r.rewrites_expected, r.rewrites_extracted))
        if (n.missed, n.extra) != (r.missed, r.extra):
            if n.missed or n.extra:
                lines.append("  Still different after normalising:")
                lines.extend(_lists(n.missed, n.extra, "    "))
            else:
                lines.append("  Every condition matches after normalising.")
        if r.fixable_missed or r.fixable_extra:
            lines.append(
                f"  'fixable' differs: missed {r.fixable_missed or 'none'}, "
                f"extra {r.fixable_extra or 'none'}"
            )
        if not (r.missed or r.extra):
            lines.append("  Every condition matches.")
    if len(results) > 1:
        lines.append(f"OVERALL ({len(results)} schemes):")
        lines.append(
            _scores(
                "exact:     ",
                sum(len(r.matched) for r in results),
                sum(r.extracted_count for r in results),
                sum(r.expected_count for r in results),
            )
        )
        lines.append(
            _scores(
                "normalised:",
                sum(len(r.normalised.matched) for r in results),
                sum(r.normalised.extracted_count for r in results),
                sum(r.normalised.expected_count for r in results),
            )
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare saved proposals with the seed files.")
    parser.add_argument("files", nargs="+", type=Path, help="proposal JSON ({'scheme': ...})")
    args = parser.parse_args(argv)

    results: list[SchemeAccuracy] = []
    try:
        for path in args.files:
            data = json.loads(path.read_text(encoding="utf-8"))
            scheme = data.get("scheme", data)  # accept the full answer or just the scheme
            result = compare_to_seed(str(scheme.get("slug")), scheme)
            if result is None:
                raise AccuracyError(f"{path.name}: no seed file for slug '{scheme.get('slug')}'")
            results.append(result)
    except (OSError, ValueError, AttributeError, AccuracyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(render_accuracy(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
