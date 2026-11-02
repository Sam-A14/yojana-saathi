# 006 – LLM rule extraction: proposals only, validated, scored against hand labels

## Context
Rules for ~100 schemes cannot all be typed by hand, but an LLM that gets one condition wrong
tells a family they qualify when they do not (or the reverse). CLAUDE.md rule 1: the LLM never
decides eligibility. It may only turn scheme text into rules, which a person then reviews.

## Decision
- **One interface** (`app/llm/base.py`: `complete_json` returns raw text), a Gemini implementation
  over `httpx`, and a fake. `LLM_PROVIDER` picks one. The pipeline only sees the interface.
- **Raw text in, raw text kept.** The wrapper returns the model's exact string so unparseable
  output can be stored and flagged instead of crashing inside a parser.
- **Answer shape:** `{"scheme": <same shape as a seed file>, "rule_quotes": [{"index", "quote"}]}`.
  Quotes live beside the rules because `scheme.schema.json` forbids extra keys inside rules. One
  quote per top-level rule (the unit the result page shows as one reason); nested conditions are
  covered by their parent's quote.
- **Validator** (invalid output is saved, flagged, never dropped): parseable JSON (NaN rejected,
  JSONB cannot store it) -> shape -> `scheme.schema.json` -> every field on the allowed list ->
  `engine.validate_rules` accepts it -> slug and source URL match the input -> `verified_at` and
  `approved_by` are null (only a human verifies) -> every top-level rule has a quote of at least
  10 characters that appears **word for word** (whitespace-insensitive) in the source text.
- **Storage:** `review_items` gets `scheme_slug`, `source_url`, `is_valid`, `validation_errors`,
  `source_quotes`, `raw_output`, `model` (migration 0003). `proposed_rules_json` holds the proposed
  scheme (`{}` if unreadable). Status is always `pending`; nothing writes to `scheme_versions`.
- **Accuracy** compares sets of leaf conditions `(wrappers, field, op, value)` against the seed file.
  Rule order, child order and `in`-list order do not matter; `not`/`any_member` wrappers do. The
  report lists the missed and the extra conditions, not just the percentages.
- **Workflow** `Extract scheme rules`: manual, `main` only, slug validated and passed by environment
  variable, report written to the run summary and not to the log (model text could contain `::`
  workflow commands).
- **CI never calls a real API:** an autouse test fixture forces the fake provider and removes the key;
  `get_llm_client` also refuses Gemini while pytest is running. We cannot key this on `CI=true`,
  because GitHub sets that in the real extraction workflow too.

## Alternatives
- Google's SDK: one more dependency, and structured-output mode cannot express our schema's
  `$ref` / `if-then`, so our own validator is needed anyway.
- Quote inside each rule: simplest to read, but the schema (and the engine) reject extra keys.
- Tree-shape comparison for accuracy: stricter, but a harmless regrouping would score as a miss.
- Dropping invalid output: cleaner table, but hides bad extractions and loses debugging evidence.

## Consequences
- The score is only as trustworthy as the seed file. `verified_at: null` seed files are unverified
  labels; a high score against them means agreement, not correctness.
- Leaf matching does not remember sibling grouping: two same-shaped groups regrouped across each
  other still score 100%. Human review is the real gate.
- Re-running a slug adds another pending row (kept as evidence); the review queue should show the
  latest per slug.
- The quote check proves the quote exists, not that it supports the rule. A reviewer still reads it.
- Source text sent to Gemini is public scheme text, but anything pasted into `scheme_sources/`
  goes to a third party; paste only public pages.
