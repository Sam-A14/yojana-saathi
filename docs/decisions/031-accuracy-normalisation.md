# 031 – Accuracy: report an exact and a normalised score

## Context
The first real run scored 29% on pm-kisan, but part of the gap was spelling, not meaning. The seed
file says "no member is a government employee other than Group D" as `govt_employee eq "other"`;
the model wrote `neq "none"` and `neq "group_d"` together. Same answer for every family, different
leaves. Likewise `eq true` and `is_true`. Counting these as a miss plus an extra hides how well the
model reads the text.

## Decision
- **Two scores, always side by side.** *Exact* is the old leaf comparison. *Normalised* first
  rewrites both rule trees (seed and proposal) into one canonical form, then compares leaves. The exact score
  never changes; normalising can only add matches, and the report lists which rewrites fired.
- **Boolean rewrite:** `eq true` becomes `is_true`, only for yes/no fields (`BOOLEAN_FIELDS` plus
  `has_*`). Both give the same answer for true, false and missing (unknown). They differ only for a
  non-yes/no value, which is bad data (`eq` says false, `is_true` raises). `eq false` is not rewritten.
- **Closed-list rewrite:** for a field with a fixed list of answers (`CLOSED_VALUES`: gender,
  area_type, marital_status, category, education, occupation from the API/DB lists, plus
  govt_employee and pension_band from `rules/fields.py`), every `eq / neq / in / not_in` becomes one
  `in [sorted set]`. Conditions on the same field under one `all` intersect; under one `any`
  they unite. A missing fact is unknown for every operator, before and after, so no answer changes.
- **Not rewritten, so still a difference:** a field with no closed list (state, district, age...),
  a value outside the list, an empty result ("never true"), conditions split across `any_member`
  or `not` boundaries, and `not(eq x)` against `neq x`.
- **Report:** per scheme, "exact" and "normalised" precision and recall; the lists of what is still
  different; the rewrites that differ between the two sides (identical ones are only counted); and
  an OVERALL pair.
- **Safety net:** a test runs the real engine on original and rewritten rules for every combination
  of facts, missing included, and requires the same status. Another pins `BOOLEAN_FIELDS` to the
  `members` table's yes/no columns.

## Alternatives
- Rewrite everything, including `state`: would call `neq UP` equal to "any other state list", which
  is only true if we had listed every state.
- Evaluate both rules on generated families and call equal rules a match: exact semantics, but
  needs a family generator and still cannot say *which condition* is wrong.
- Only report the normalised score: hides how often the model needs the help.

## Consequences
- The normalised score is higher by design. Read it with the exact one, and with the lists.
- Adding a closed-list field (a new tuple of answers) means adding it to `CLOSED_VALUES`; the same
  list that validates family answers is the one that makes the rewrite safe.
- The leaf comparison still does not remember grouping (decision 006); normalising does not change that.
