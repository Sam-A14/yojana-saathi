# 030 – Benefit text needs a source quote

## Context
Rules were checked word for word against the source (decision 006), but `benefit_text_en` was not.
It is shown to families as fact ("what you receive"), so an amount or a frequency the model
made up is as harmful as a wrong rule, and a reviewer had nothing to check it against.

## Decision
- **The answer gets one more key**, `benefit_quote`, beside `scheme` and `rule_quotes` (the schema
  forbids extra keys inside the scheme, as with rule quotes).
- **Validator:** if `benefit_text_en` is not null, `benefit_quote` must be at least 10 characters
  and appear word for word (whitespace-insensitive) in the source text. Problems:
  `benefit_unquoted`, `benefit_quote_too_short`, `benefit_quote_not_in_source`. If there is no
  supporting text, `benefit_text_en` must be null.
- **Hindi follows English:** `benefit_text_hi` must be null whenever `benefit_text_en` is null
  (`benefit_hi_without_en`). A Hindi text next to a quoted English one is allowed; it is still a
  translation, which a person checks.
- **Storage:** no migration. The quote is appended to `review_items.source_quotes` as
  `{"field": "benefit_text_en", "quote": "..."}`. Rule quotes keep `{"index", "quote"}`, so the two
  kinds cannot be confused, and a row with no benefit quote looks exactly as before.
- **Prompt and report:** the prompt asks for the quote and for nulls when the text does not state
  the benefit; the run summary prints `benefit_quote` next to `rule_quotes`.

## Alternatives
- A new column for the quote: clearer to query, but a migration for one string.
- Quote only a number or amount: smaller, but the sentence around it can still be wrong.
- Require `benefit_text_hi` to be null always: stricter, but it was not asked for and a person can
  translate a quoted English text.

## Consequences
- As with rule quotes, the check proves the words exist in the source, not that they support the
  benefit text. A reviewer still reads both side by side.
- Old review items have no benefit entry. Approval tools must treat a missing entry as "no quote".
- The seed files are hand-labelled and are not checked by this rule.
