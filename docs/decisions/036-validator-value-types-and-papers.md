# 036 – The validator checks value types, and keeps papers out of eligibility rules

## Context
Review item 4 (IGNOAPS) passed validation and was wrong in three ways:
1. `is_bpl eq "yes"`. The engine compares exactly, so the text "yes" is not true: a valid rule that nobody can ever meet.
2. Rules on `has_<document>` fields, quoted from "Documents Required". Those are papers to bring, not conditions of eligibility.
3. The residential-proof alternatives ("Voter card/ Electricity Bill/ Aadhar Card") all marked required.
The validator proves a quote exists, not that the rule means what the quote says (decision 006); these are
mistakes it can catch mechanically.

## Decision
- **Value types** (`app/pipeline/field_types.py`, problem `invalid_value_type` at the condition's position):
  - *yes/no fields* (the yes/no facts and every `has_<document>`): `is_true`, or `eq` / `neq` with `true` / `false`. The text "yes", the number 1, `in` and `gte` are refused.
  - *fields with a fixed list* (gender, area, marital status, category, education, occupation, govt_employee, pension_band): `eq` / `neq` / `in` / `not_in` with listed answers only.
  - *numbers* (age, income limit): numbers (true is not 1); *text* (state, district): text.
  - The table is shared with the accuracy normaliser (which already knew the closed lists and the yes/no fields). A test fails if a rule field has no type, so adding a field forces a decision. Every condition in the committed seed files passes (no false alarms).
- **Papers are not eligibility** (`document_as_rule` at the rule's position): a rule that uses any `has_<document>` field is refused unless its source quote is inside the **Eligibility** section of the source. Sections are read by `app/pipeline/sections.py` (heading lines such as Eligibility, Documents Required, Benefits, Details, FAQ). A source with no Eligibility heading (a press release, a PDF) cannot show that, so a paper rule from it is refused; the paper goes in `version.documents`.
- **Prompt:** "Papers listed under documents go ONLY in version.documents, never in rules" (system and user prompt); yes/no fields take `is_true` or `true`/`false`, never "yes"; and when the source gives alternatives ("X/ Y/ Z", "X or Y"), mark none required and say so in `labeller_notes.notes`.

## Alternatives
- Fix only the prompt: the model already ignored a similar instruction; a check is cheaper than a human catching it.
- Reject every `has_` rule: simpler, but a source that really says "you must hold a ration card" under Eligibility would need a hand edit.
- Detect alternatives in the validator: free text is too varied to parse; the check would be a guess. Left to the prompt and the reviewer.

## Consequences
- A flagged item cannot be approved (decision 032). Review items already in the database were validated by the older code and stay "valid"; extract again to get the new checks.
- A scheme whose Eligibility section is not a separate heading will have its paper rules refused. Acceptable: those papers belong in documents anyway.
- "Required" on alternatives is still a human check in the pull request (the prompt asks for `required: false` and a note).
- `backend/tests/ignoaps_item4.json` is review item 4's exact Proposal block from the Extract run summary, unedited. The old validator called it valid (checked on `main`); the new one flags it with 7 problems (`invalid_value_type` once, `document_as_rule` six times), and the same proposal with only those mistakes fixed passes.
