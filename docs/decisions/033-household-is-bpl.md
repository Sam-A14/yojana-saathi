# 033 – `is_bpl`: a household yes/no, separate from the BPL card

## Context
Schemes such as IGNOAPS ask for a family "living Below Poverty Line". The rules could only see the
`bpl_card` document, and IGNWPS used `has_bpl_card` as a stand-in. A card is proof of BPL status, not the
status: a BPL family without the card in hand would fail the rule and be told "not eligible", which is
a false negative, the harm this product exists to prevent.

## Decision
- **One nullable yes/no on the household:** `households.is_bpl` (migration 0006), a rule field in
  `rules/fields.py` (`HOUSEHOLD_FIELDS`) and in `data/scheme.schema.json`. `NULL` means "not answered
  yet" and the engine turns it into "unknown", never "no". Existing households stay `NULL`.
- **API:** `is_bpl` on household create, update and read, as `StrictBool | None`. `"yes"`, `1` and
  `"true"` are 422s; `null` clears the answer, as for every other household answer.
- **The document stays a document.** `bpl_card` is still a household-level document ("has / doesn't
  have"); rules use `is_bpl` for the condition, and a scheme can still list `bpl_card` as required so a
  BPL family without the card is shown it as missing.
- **No identity or financial number** is stored (rule 3): it is a yes/no, not a card number.
- **Hints and accuracy:** the extractor prompt hints that `is_bpl` is the household status and that
  the card is a different thing; `accuracy.py` treats `is_bpl` as a yes/no field, and a test pins that
  list to the yes/no columns of both the `members` and `households` tables.
- **Frontend is a separate PR:** until the setup question exists nobody can answer it, so every
  household stays `unknown` for rules that use `is_bpl`. No existing scheme uses it yet.

## Alternatives
- Keep `has_bpl_card` as the stand-in (what IGNWPS does): no code, but false negatives.
- Mark `has_bpl_card` as fixable: a non-BPL family would be told to "get a BPL card", which does not exist for them.
- Ask per member: BPL is a household list; asking each member would let the answers disagree.

## Consequences
- A scheme that needs BPL can say so honestly, and a family that has not answered is asked, not rejected.
- States keep their own BPL lists; the question text must say "your state's BPL list", because we cannot check it.
- IGNWPS still uses `has_bpl_card` until its own PR switches it to `is_bpl` (keeping `bpl_card` as a required document).
