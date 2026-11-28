# 043 — current_study_level: what a person is studying now

## Context
The UP SC/ST Pre Matric scholarship is for students "in Class 9 or 10". `education` cannot say that:
it is the highest level finished, so a child in Class 9 (finished Class 8) has no matching value,
and the family's reading of "Up to class 10" is ambiguous for a child still in Class 10.

## Decision
A new nullable member fact `current_study_level`, a closed list: `class_1_8`, `class_9_10`,
`class_11_12`, `undergraduate`, `postgraduate`, `other`. NULL means not answered, which the engine
treats as unknown (never "no"). The question is asked only when `is_student` is true (frontend PR).
It is a rule field, in the scheme schema, in the extractor's field list (with a hint that says
"studying now, not highest finished"), and in the closed-value table the validator and accuracy
normaliser use. `engine.py` is not touched: it reads the field list from `rules/fields.py`.

## Alternatives
- A yes/no `in_class_9_or_10`: smallest, but each new scheme would need its own boolean.
- Reuse `education`: it means something else, and mixing two meanings corrupts both.
- A database CHECK constraint on the list: skipped, like `education`; the API refuses other words.

## Consequences
- Post-Matric schemes reuse the same field.
- A member who is not a student keeps NULL; a rule on this field says unknown for them, which is
  why such a rule should be written together with `is_student` (the scheme's own rules decide).
- Existing members are NULL (unknown), so nobody's results change until they answer.
