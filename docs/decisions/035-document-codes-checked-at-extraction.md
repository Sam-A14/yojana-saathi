# 035 – Document codes are checked when a proposal is extracted, not only when it is approved

## Context
Approve scheme proposal run #1 (review item 3, IGNOAPS) was refused with "the file would not load:
document 'aadhaar' is not in documents.json". The refusal was right: the seed loader accepts only the
codes in `data/documents.json` (here `aadhaar_card`). But the extraction had passed the same proposal as
valid, so a person read and chose to approve something the approval step could never write. Two gaps:
- the extractor prompt told the model `"code": "<document code>"` without listing the codes, and
- the validator checked every field used in rules against the allowed list, but not the codes in
  `version.documents`.

## Decision
- **The prompt lists the codes.** A new "ALLOWED DOCUMENT CODES" section gives every code in
  `documents.json` with its English name, says to spell it exactly ("aadhaar_card, not aadhaar"), and says what to do
  with a paper that is not on the list: leave it out of `documents` and put it in
  `labeller_notes.not_encoded`. A person adds a new document to `documents.json` first.
- **The validator checks them.** `unknown_document` (a code not in `documents.json`) and `duplicate_document` are
  problems at `scheme.version.documents[i].code`. The codes are read from the same allowed-field list that
  already comes from `documents.json`, so there is one source of truth.
- **Rule of thumb now stated in the validator:** a proposal that is called valid must be one the approval step
  can write. Anything the seed loader would refuse (decision 004) is refused at extraction, with the reason.

## Alternatives
- Map near-misses ("aadhaar" to "aadhaar_card") automatically: guesses on a person's behalf in data that ends up in front of families.
- Leave it to the approval step: works, but only after a person has already read and chosen the proposal.
- Add the missing code to `documents.json` for every new spelling: grows the catalogue with the model's typos.

## Consequences
- Old review items (like item 3) are unchanged: they are `is_valid = true` in the database and still cannot be approved. Run
  Extract scheme rules again; the new item is checked and the model is told the codes.
- A scheme that needs a paper not in `documents.json` now gets a flagged note instead of a made-up code.
