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

Precision = matched / extracted (how much of what the model wrote is right).
Recall    = matched / expected  (how much of the labelled rules the model found).
Overall numbers add up the counts of all schemes first (micro-average), so a big scheme weighs more.

Run on saved proposals:  python -m app.pipeline.accuracy proposal.json [more.json ...]
"""

import argparse
import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.db.seed import DEFAULT_DATA_DIR

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


# --- comparing -----------------------------------------------------------------------------


@dataclass(frozen=True)
class SchemeAccuracy:
    slug: str
    matched: list[Leaf]
    missed: list[Leaf]  # in the seed file, not found in the extraction
    extra: list[Leaf]  # in the extraction, not in the seed file
    fixable_missed: list[str]
    fixable_extra: list[str]

    @property
    def expected_count(self) -> int:
        return len(self.matched) + len(self.missed)

    @property
    def extracted_count(self) -> int:
        return len(self.matched) + len(self.extra)


def compare_rules(slug: str, expected: Any, extracted: Any) -> SchemeAccuracy:
    want, got = leaf_conditions(expected), leaf_conditions(extracted)
    want_fixable, got_fixable = _fixable(expected), _fixable(extracted)
    return SchemeAccuracy(
        slug=slug,
        matched=sorted(want & got),
        missed=sorted(want - got),
        extra=sorted(got - want),
        fixable_missed=sorted(want_fixable - got_fixable),
        fixable_extra=sorted(got_fixable - want_fixable),
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


def render_accuracy(results: list[SchemeAccuracy]) -> str:
    lines: list[str] = []
    for r in results:
        lines.append(
            f"{r.slug}: precision {_ratio(len(r.matched), r.extracted_count)}, "
            f"recall {_ratio(len(r.matched), r.expected_count)}"
        )
        if r.missed:
            lines.append("  Missed (in the seed file, not extracted):")
            lines.extend(f"    - {describe(leaf)}" for leaf in r.missed)
        if r.extra:
            lines.append("  Extra (extracted, not in the seed file):")
            lines.extend(f"    - {describe(leaf)}" for leaf in r.extra)
        if r.fixable_missed or r.fixable_extra:
            lines.append(
                f"  'fixable' differs: missed {r.fixable_missed or 'none'}, "
                f"extra {r.fixable_extra or 'none'}"
            )
        if not (r.missed or r.extra):
            lines.append("  Every condition matches.")
    if len(results) > 1:
        matched = sum(len(r.matched) for r in results)
        extracted = sum(r.extracted_count for r in results)
        expected = sum(r.expected_count for r in results)
        lines.append(
            f"OVERALL ({len(results)} schemes): precision {_ratio(matched, extracted)}, "
            f"recall {_ratio(matched, expected)}"
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
