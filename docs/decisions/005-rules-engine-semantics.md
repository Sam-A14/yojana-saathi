# 005 – Rules engine: unknown, household rules, near misses

## Context
Eligibility must come only from a deterministic engine (CLAUDE.md rule 1) and must be explainable
to a parent. Three questions had no obvious answer: what a missing fact means, how a rule can talk
about other family members (PM-KISAN excludes a family if *any* member paid income tax), and what
"near miss" means once rules contain `any` and `not`.

## Decision
- **Three-valued logic.** Every rule is true, false or unknown. A missing fact is unknown for every
  operator, including `neq` and `not_in`. `all`/`any` follow Kleene logic: a definite false (for
  `all`) or true (for `any`) beats unknown; `not` of unknown is unknown.
- **`any_member`.** `{"any_member": <rule>}` is true if the inner rule holds for at least one
  household member, evaluated one member at a time (so "pensioner AND not Group D" means one
  person). "No member ..." is `{"not": {"any_member": ...}}`. The result lists the nicknames of the
  members who satisfied it, so a failed exclusion can say who caused it. An optional `"among"` key
  is reserved; only `"household"` works today.
- **Near miss = eligible once fixable items are fixed.** If the rules fail, evaluate again with every
  condition on a `fixable` field pretended fixed. If that passes, the status is `near_miss`. A fixed
  condition is forced to the value that *helps*: true normally, false under an odd number of `not`s.
  If the second pass is still unknown, the status is `unknown`.
- **Malformed rules raise `RuleError`**, they never become `unknown`. Unknown means the family's data
  is incomplete; a bad rule is our bug. The engine validates the whole rule tree first.
- **Pure inputs.** `evaluate(member, HouseholdFacts, rules)` takes plain mappings. Turning birth year
  into `age` and database rows into mappings belongs to the API layer.
- **Missing document answer = unknown**, not "doesn't have". Only an explicit "no" is false.

## Alternatives
- Treat missing as false: simple, but families who simply were not asked would be told "not
  eligible" and never asked.
- Near miss as "failed fields are a subset of `fixable`": breaks with `any` (a fixable branch is
  enough) and with `not`.
- Naive relaxation (force fixable conditions to true): wrong under `not`.
- `any_member` only at the rule root: cannot express "pension 10k+ and not Group D" for one person.

## Consequences
- The household is not PM-KISAN's "family" (husband, wife, minor children). In a joint family an
  adult relative's exclusion can wrongly exclude the whole household. Fix later with member links
  and `"among": "applicant_family"`; recorded in `not_encoded` of `pm-kisan.json`.
- Results are per member. For household-level schemes every member gets the same answer; the
  dashboard must de-duplicate.
- The engine checks `has_*` field names only by prefix; the JSON schema and `test_seed_files.py`
  check them against `documents.json`.
