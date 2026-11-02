"""Checks a model's answer before a human sees it.

The rule here: invalid output is KEPT but FLAGGED, never dropped. A reviewer learns from seeing
what the model got wrong, and a silent drop would hide a bad extraction behind "nothing came back".

Checks, in order:  parseable JSON -> expected shape -> scheme.schema.json -> only allowed fields ->
engine accepts the rules -> slug/URL/verified fields -> a real quote for every top-level rule.
"""

import json
from dataclasses import dataclass, field
from typing import Any

from jsonschema import Draft202012Validator

from app.db.seed import schema_problems
from app.rules.engine import RuleError, validate_rules

# A quote shorter than this proves nothing ("age", "farmer" appear everywhere in the source).
MIN_QUOTE_CHARS = 10


@dataclass(frozen=True)
class Problem:
    code: str  # short machine name, e.g. "unknown_field"
    where: str  # where in the output, e.g. "scheme.version.rules.all[2]"
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "where": self.where, "message": self.message}


@dataclass
class ValidationResult:
    problems: list[Problem] = field(default_factory=list)
    # What the model proposed, when it could be read. None if the text was not a JSON object.
    scheme: dict[str, Any] | None = None
    quotes: list[Any] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.problems


def validate_output(
    raw: str,
    *,
    slug: str,
    source_url: str,
    source_text: str,
    allowed: list[str],
    schema_validator: Draft202012Validator,
) -> ValidationResult:
    result = ValidationResult()
    parsed = _parse_json(raw, result)
    if parsed is None:
        return result
    if not isinstance(parsed, dict):
        result.problems.append(Problem("bad_shape", "(top level)", "Expected a JSON object."))
        return result

    scheme, quotes = parsed.get("scheme"), parsed.get("rule_quotes")
    if isinstance(scheme, dict):
        result.scheme = scheme
    else:
        result.problems.append(Problem("bad_shape", "scheme", "Missing or not an object."))
    if isinstance(quotes, list):
        result.quotes = quotes
    else:
        result.problems.append(Problem("bad_shape", "rule_quotes", "Missing or not a list."))
    if result.scheme is None:
        return result

    _check_schema(result, schema_validator)
    _check_fields(result, set(allowed))
    _check_engine(result)
    _check_identity(result, slug, source_url)
    if isinstance(quotes, list):
        _check_quotes(result, source_text)
    return result


# --- steps ---------------------------------------------------------------------------------


def _parse_json(raw: str, result: ValidationResult) -> Any:
    text = raw.strip()
    if text.startswith("```"):  # tolerate a markdown fence around otherwise good JSON
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.removesuffix("```").strip()

    def reject_constant(name: str) -> None:
        # NaN / Infinity are not JSON and PostgreSQL's JSONB would refuse to store them.
        raise ValueError(f"{name} is not valid JSON")

    try:
        return json.loads(text, parse_constant=reject_constant)
    except ValueError as error:
        result.problems.append(Problem("not_json", "(top level)", f"Not valid JSON: {error}"))
        return None


def _check_schema(result: ValidationResult, validator: Draft202012Validator) -> None:
    for message in schema_problems(validator, result.scheme):
        result.problems.append(Problem("schema", "scheme", message))


def _check_fields(result: ValidationResult, allowed: set[str]) -> None:
    """Every field name used anywhere in the rules, or in 'fixable', must be on the list."""
    version = _dict(_dict(result.scheme).get("version"))
    rules = _dict(version.get("rules"))
    for name, where in _field_names(rules.get("all"), "scheme.version.rules.all"):
        if name not in allowed:
            result.problems.append(Problem("unknown_field", where, f"'{name}' is not allowed."))
    fixable = rules.get("fixable")
    for index, name in enumerate(fixable if isinstance(fixable, list) else []):
        if name not in allowed:
            where = f"scheme.version.rules.fixable[{index}]"
            result.problems.append(Problem("unknown_field", where, f"'{name}' is not allowed."))


def _field_names(node: Any, where: str) -> list[tuple[Any, str]]:
    """Walk arbitrary JSON (it may be badly shaped) and collect (field name, location)."""
    found: list[tuple[Any, str]] = []
    if isinstance(node, list):
        for index, child in enumerate(node):
            found += _field_names(child, f"{where}[{index}]")
    elif isinstance(node, dict):
        if "field" in node:
            found.append((node["field"], where))
        for key, child in node.items():
            if key != "field":
                found += _field_names(child, f"{where}.{key}")
    return found


def _check_engine(result: ValidationResult) -> None:
    """Ask the engine's own rule check, so a proposal is never accepted that the engine would
    refuse to run. Skipped when the schema already failed: its errors would be noise on top."""
    if any(p.code in ("schema", "unknown_field") for p in result.problems):
        return
    rules = _dict(_dict(result.scheme).get("version")).get("rules")
    try:
        validate_rules(rules)  # type: ignore[arg-type]
    except RuleError as error:
        result.problems.append(Problem("engine_rejects", "scheme.version.rules", str(error)))


def _check_identity(result: ValidationResult, slug: str, source_url: str) -> None:
    scheme = _dict(result.scheme)
    version = _dict(scheme.get("version"))
    if scheme.get("slug") != slug:
        message = f"Expected '{slug}', got {scheme.get('slug')!r}."
        result.problems.append(Problem("slug_mismatch", "scheme.slug", message))
    if version.get("source_url") != source_url:
        message = f"Expected the given source URL, got {version.get('source_url')!r}."
        result.problems.append(Problem("source_url_mismatch", "scheme.version.source_url", message))
    for name in ("verified_at", "approved_by"):
        if version.get(name) is not None:
            message = "Only a human may set this; it must be null."
            result.problems.append(Problem("claims_verified", f"scheme.version.{name}", message))


def _check_quotes(result: ValidationResult, source_text: str) -> None:
    rules = _dict(_dict(_dict(result.scheme).get("version")).get("rules"))
    top_level = rules.get("all")
    rule_count = len(top_level) if isinstance(top_level, list) else None
    source = _squash(source_text)
    quoted: set[int] = set()

    for position, entry in enumerate(result.quotes):
        where = f"rule_quotes[{position}]"
        entry = _dict(entry)
        index, quote = entry.get("index"), entry.get("quote")
        if not isinstance(index, int) or isinstance(index, bool) or not isinstance(quote, str):
            message = 'Each entry must look like {"index": 0, "quote": "..."}.'
            result.problems.append(Problem("bad_quote", where, message))
            continue
        if rule_count is not None and not 0 <= index < rule_count:
            message = f"index {index} is outside rules.all (0 to {rule_count - 1})."
            result.problems.append(Problem("bad_quote", where, message))
            continue
        squashed = _squash(quote)
        if len(squashed) < MIN_QUOTE_CHARS:
            message = f"Quote is shorter than {MIN_QUOTE_CHARS} characters."
            result.problems.append(Problem("quote_too_short", where, message))
        elif squashed not in source:
            message = f"Quote is not found word for word in the source text: {quote[:80]!r}"
            result.problems.append(Problem("quote_not_in_source", where, message))
        else:
            quoted.add(index)

    for index in range(rule_count or 0):
        if index not in quoted:
            where = f"scheme.version.rules.all[{index}]"
            result.problems.append(Problem("missing_quote", where, "No valid source quote."))


def _squash(text: str) -> str:
    """Collapse all whitespace, so a quote still matches across a line break in the pasted text."""
    return " ".join(text.split())


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
