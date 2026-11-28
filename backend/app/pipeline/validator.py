"""Checks a model's answer before a human sees it.

The rule here: invalid output is KEPT but FLAGGED, never dropped. A reviewer learns from seeing
what the model got wrong, and a silent drop would hide a bad extraction behind "nothing came back".

Checks, in order:  parseable JSON -> expected shape -> scheme.schema.json -> only allowed fields ->
engine accepts the rules -> every value has the right type for its field -> every document code
exists -> slug/URL/verified fields -> a real quote for every top-level rule, taken from the Details
or Eligibility section -> no rule about a paper
unless the Eligibility section says so -> a real quote for the benefit text.

A proposal this validator calls valid must be one the approval step can write: whatever the seed
loader would refuse (decision 004) is refused here first, with the reason, instead of at approval.
"""

import json
from dataclasses import dataclass, field
from typing import Any

from jsonschema import Draft202012Validator

from app.db.seed import schema_problems
from app.pipeline.field_types import value_problem
from app.pipeline.sections import eligibility_text, rule_quote_text, sections_containing
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
    quotes: list[Any] = field(default_factory=list)  # one per top-level rule
    # Words from the source that state the benefit; the proof behind benefit_text_en.
    benefit_quote: str | None = None

    @property
    def is_valid(self) -> bool:
        return not self.problems

    def stored_quotes(self) -> list[Any]:
        """What goes in review_items.source_quotes: the rule quotes, then the benefit quote.

        The benefit entry says which text it supports ({"field": ..., "quote": ...}) and has no
        index, so it can never be mistaken for a rule's quote. No new column or migration needed.
        """
        if not self.benefit_quote:
            return list(self.quotes)
        return [*self.quotes, {"field": "benefit_text_en", "quote": self.benefit_quote}]


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
    benefit_quote = parsed.get("benefit_quote")
    if benefit_quote is None or isinstance(benefit_quote, str):
        result.benefit_quote = benefit_quote
    else:
        result.problems.append(Problem("bad_shape", "benefit_quote", "Must be null or text."))
    if result.scheme is None:
        return result

    _check_schema(result, schema_validator)
    _check_fields(result, set(allowed))
    _check_engine(result)
    _check_value_types(result)
    _check_documents(result, _document_codes(allowed))
    _check_identity(result, slug, source_url)
    if isinstance(quotes, list):
        _check_quotes(result, source_text)
        _check_papers_are_not_eligibility(result, source_text)
    _check_benefit(result, source_text)
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


def _conditions(node: Any, where: str) -> list[tuple[dict[str, Any], str]]:
    """Every condition ({"field": ..., "op": ...}) anywhere in a rule tree, with where it is.
    The tree may be badly shaped (it is a model's output), so anything unexpected is skipped."""
    found: list[tuple[dict[str, Any], str]] = []
    if isinstance(node, list):
        for index, child in enumerate(node):
            found += _conditions(child, f"{where}[{index}]")
    elif isinstance(node, dict):
        if "field" in node:
            found.append((node, where))
        else:
            for key, child in node.items():
                found += _conditions(child, f"{where}.{key}")
    return found


def _check_value_types(result: ValidationResult) -> None:
    """A rule value must be the kind of thing its field holds (field_types.py). The engine compares
    exactly, so is_bpl eq "yes" is a valid rule that nobody can ever meet: nobody is eligible."""
    rules = _dict(_dict(_dict(result.scheme).get("version")).get("rules"))
    for condition, where in _conditions(rules.get("all"), "scheme.version.rules.all"):
        problem = value_problem(condition)
        if problem:
            result.problems.append(Problem("invalid_value_type", where, problem))


def _check_papers_are_not_eligibility(result: ValidationResult, source_text: str) -> None:
    """Papers a family must bring belong in version.documents. A rule on a has_<document> field is
    allowed only when its source quote is inside the Eligibility section of the source, because
    then the source itself states "you must hold this" as a condition. A quote from "Documents
    Required" (or from a source with no Eligibility section) is not that."""
    rules = _dict(_dict(_dict(result.scheme).get("version")).get("rules"))
    top_level = rules.get("all")
    if not isinstance(top_level, list):
        return
    quotes = {
        entry["index"]: entry["quote"]
        for entry in map(_dict, result.quotes)
        if isinstance(entry.get("index"), int) and isinstance(entry.get("quote"), str)
    }
    eligibility = _squash(eligibility_text(source_text))
    for index, rule in enumerate(top_level):
        where = f"scheme.version.rules.all[{index}]"
        papers = sorted(
            {
                str(c["field"]).removeprefix("has_")
                for c, _ in _conditions(rule, where)
                if isinstance(c.get("field"), str) and c["field"].startswith("has_")
            }
        )
        if not papers:
            continue
        quote = quotes.get(index)
        if quote is not None and eligibility and _squash(quote) in eligibility:
            continue
        message = (
            f"Rule {index} is about the paper {', '.join(papers)}. Papers the source asks for go "
            "only in version.documents; a rule about a paper needs a quote from the source's "
            "Eligibility section, and this quote is not from there."
        )
        result.problems.append(Problem("document_as_rule", where, message))


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


def _document_codes(allowed: list[str]) -> set[str]:
    """The document codes in documents.json, read back from the allowed fields (one has_<code> each,
    made from that same file), so there is a single source of truth."""
    return {name.removeprefix("has_") for name in allowed if name.startswith("has_")}


def _check_documents(result: ValidationResult, known: set[str]) -> None:
    """version.documents may only name papers that exist in documents.json, each once. The seed
    loader refuses anything else, so the proposal is flagged now rather than when approved."""
    documents = _dict(_dict(result.scheme).get("version")).get("documents")
    seen: set[str] = set()
    for index, entry in enumerate(documents if isinstance(documents, list) else []):
        code = _dict(entry).get("code")
        where = f"scheme.version.documents[{index}].code"
        if not isinstance(code, str):
            continue  # the schema check reports a missing or non-text code
        if code not in known:
            message = f"'{code}' is not in documents.json; use one of the allowed document codes."
            result.problems.append(Problem("unknown_document", where, message))
        elif code in seen:
            result.problems.append(
                Problem("duplicate_document", where, f"'{code}' is listed twice.")
            )
        seen.add(code)


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
    # A source with section headings: a rule quote must sit under Details, Eligibility or
    # Exclusions. A source without headings has no sections to tell apart, so the whole text is
    # accepted as before.
    allowed_text = rule_quote_text(source_text)
    allowed = source if allowed_text is None else _squash(allowed_text)
    quoted: set[int] = set()
    wrong_section: set[int] = set()  # already told why; no second 'no valid quote' line

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
        elif squashed not in allowed:
            found_in = ", ".join(sections_containing(source_text, quote)) or "no section"
            message = (
                "A rule quote must come from the Details, Eligibility or Exclusions section. "
                f"This quote is under: {found_in}. Papers go in version.documents, and anything "
                "else in labeller_notes.not_encoded."
            )
            result.problems.append(Problem("quote_wrong_section", where, message))
            wrong_section.add(index)
        else:
            quoted.add(index)

    for index in range(rule_count or 0):
        if index not in quoted and index not in wrong_section:
            where = f"scheme.version.rules.all[{index}]"
            result.problems.append(Problem("missing_quote", where, "No valid source quote."))


def _check_benefit(result: ValidationResult, source_text: str) -> None:
    """Benefit text is shown to families as fact, so it needs the same proof as a rule: words copied
    from the source. No supporting text means no benefit text, in either language."""
    version = _dict(_dict(result.scheme).get("version"))
    text_en, text_hi = version.get("benefit_text_en"), version.get("benefit_text_hi")
    if text_en is None:
        if text_hi is not None:
            where = "scheme.version.benefit_text_hi"
            message = "benefit_text_hi must be null when benefit_text_en is null."
            result.problems.append(Problem("benefit_hi_without_en", where, message))
        return
    where = "scheme.version.benefit_text_en"
    quote = result.benefit_quote
    squashed = _squash(quote) if quote else ""
    if not squashed:
        message = "benefit_text_en needs a benefit_quote from the source, or it must be null."
        result.problems.append(Problem("benefit_unquoted", where, message))
    elif len(squashed) < MIN_QUOTE_CHARS:
        message = f"Benefit quote is shorter than {MIN_QUOTE_CHARS} characters."
        result.problems.append(Problem("benefit_quote_too_short", where, message))
    elif squashed not in _squash(source_text):
        message = f"Benefit quote is not found word for word in the source text: {squashed[:80]!r}"
        result.problems.append(Problem("benefit_quote_not_in_source", where, message))


def _squash(text: str) -> str:
    """Collapse all whitespace, so a quote still matches across a line break in the pasted text."""
    return " ".join(text.split())


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
