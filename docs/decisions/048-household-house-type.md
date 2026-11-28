# 048 — household.house_type: what kind of house the family lives in

## Context
PMAY-Gramin is for households that have no house, or live in a kutcha or dilapidated one. No fact
the app holds says anything about housing, so the scheme could not be encoded.

## Decision
A new nullable household fact `house_type`, a closed list: `no_house`, `kutcha`, `pucca`. NULL means
not answered, which the engine treats as unknown (never "no"). It is a household fact (asked once
for the whole family), a rule field, part of the scheme schema, the household API (a word outside
the list is a 422), and the closed-value table the validator and the extractor prompt both read.
`engine.py` is not touched: it reads the field list from `rules/fields.py`. The question in the
setup and edit forms comes in the frontend PR; no scheme uses the field yet.

## Alternatives
- A yes/no `has_pucca_house`: loses the difference between "no house" and "kutcha", which a family
  may not want to be lumped together and which other schemes ask about separately.
- Rooms, walls and roof as separate facts (PMAY-G's own test): far more questions for a parent. The
  family's single answer is trusted; the finer conditions go in the scheme's "Rules we can't check".
- A member-level fact: a house belongs to the household, not to a person.
- A database CHECK constraint on the list: skipped, like `education`; the API refuses other words.

## Consequences
- Existing households are NULL, so nobody's results change until they answer.
- A scheme that needs it asks the family through the "we need to know" prompt, which leads to the
  household edit screen (like state, area and income).
- "Dilapidated" is not a value: a family with a decaying pucca house answers `pucca` and the scheme
  says unknown or no. The scheme's not-checked lines should say the office decides.
