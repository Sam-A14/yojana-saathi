# 015 — Showing a scheme rule in plain words

## Context
The scheme page must show why a person may qualify, each rule ticked or crossed. The API sends each
rule as JSON, for example `{"not": {"any_member": {"field": "paid_income_tax_last_year", "op": "is_true"}}}`.
The backend has no text for rules (the `explain.py` in the spec does not exist yet), and a parent
cannot read JSON.

## Decision
- The frontend turns rule JSON into words. `lib/rules.ts` parses it into a typed tree (`Condition`)
  and returns `null` for any shape it does not know. `lib/rule-text.ts` turns the tree into a sentence
  from `messages/` (so English and Hindi share the code), as "Label: condition", for example
  "Age: 40 or more", "Has BPL card", "No one in the family: Paid income tax last year".
- Anything not understood (an unknown field, a new shape) shows a plain "we cannot show this in words
  yet, see the official website" sentence. It never shows JSON and never a guess.
- This decides nothing about eligibility. Which rules pass, fail or are unknown comes from the engine
  (CLAUDE.md rule 1). The frontend only describes them.
- An "unknown" result lists what would settle it (`neededAnswers` in `lib/rules.ts`): a question per
  missing fact, with a link to the setup screen where it can be answered. When only the exact age or
  income would settle it, the family cannot answer, so the screen explains in plain words that it
  depends on the exact value and points to the official website.
- The unit tests run every top-level rule of every seeded scheme through the parser and the text
  in both languages, so a new seed rule that cannot be shown fails CI.

## Alternatives
- The backend writes the sentences: one source of truth, but it means a schema change plus Hindi text
  stored per rule, and the extraction pipeline would have to produce it.
- Show the original source quote: not stored yet, and it is legal text, not plain words.
- Ask an LLM to explain each rule: slower, can be wrong, costs money, and rule 1 says the LLM only
  extracts and writes explanations ahead of time, never at request time for a decision. Not needed here.

## Consequences
- A new field or operator needs a message in both languages (the type check enforces the Hindi half).
- "Label: condition" is a little stiff ("No one in the family: Government pension: ₹10,000 a month or
  more and Government job: not Lowest-level post (Group D)"). Clear and checkable, not poetry. A
  Hindi speaker should read these aloud before launch.
- Household facts (income, area, state) have no screen to change them yet, so a question about them is
  shown without a link.
