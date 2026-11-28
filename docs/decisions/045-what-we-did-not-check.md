# 045 — "What we did not check": conditions the app cannot test, shown to families

## Context
Some official conditions cannot be written as rules (citizenship, a sworn affidavit, "no other
scholarship", a parent's occupation). The extractor lists them in `labeller_notes.not_encoded`, but
that field is for labellers: it is not in the database and families never see it. A family told
"may qualify" for IGNOAPS was not told that the office also asks for an affidavit. That is an
honesty gap in the product, not only a data gap.

## Decision
- New columns `scheme_versions.not_checked_en` (JSONB list of strings, never NULL, `[]` = nothing to
  say) and `not_checked_hi` (JSONB list or NULL = not written yet). Seed files carry them in
  `version`, with the same names; the schema checks they are lists of non-empty strings and that the
  Hindi list has one line per English line.
- They are part of what makes a version "material" (decision 004): changing a line adds a new
  version, like a changed benefit text, so history shows what families were told.
- The approve step copies the extractor's `not_encoded` lines into `version.not_checked_en` and no
  longer keeps a second copy in `labeller_notes`. The extractor prompt now asks for plain sentences a
  parent can follow aloud, because these lines are read by families. The approve PR lists them under
  "What we did not check" so the reviewer reads them as a family would.
- The API sends both lists with every scheme summary (so the results response carries them too). The
  scheme page shows a "What we did not check" section when the English list is not empty. Hindi
  shows the English lines until a Hindi list exists, the same fallback as the benefit text.
- IGNOAPS gets two lines: citizenship, and not receiving another pension (the affidavit).

## Alternatives
- Keep `not_encoded` as labeller-only and write the family text by hand later: leaves the gap open
  for every new scheme, and nothing forces the wording to be plain.
- Translate on the fly with an LLM: the LLM only extracts rules and writes explanations, and a
  mistranslated condition is worse than an English one. Hindi is written by a person.
- Store the lines in a separate table: one more join for a short list that always travels with the
  version.

## Consequences
- The two older example schemes (PM-KISAN, IGNWPS) have `[]` until someone writes plain lines for
  their `not_encoded` notes, which are technical. They show no section, which is not the same as
  "nothing was left unchecked"; their `labeller_notes.not_encoded` still lists what was.
- Every extracted scheme's `not_encoded` lines now reach families after review, so the reviewer
  must read them as a parent would.
