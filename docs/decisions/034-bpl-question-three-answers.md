# 034 – The BPL question: Yes / No / Not sure, and "Not sure" is never "No"

## Context
`households.is_bpl` exists (decision 033) but nobody could answer it. A wrong guess here is
costly either way: "no" hides schemes the family may get, and a missing answer must stay "unknown" so
the family is asked instead of rejected.

## Decision
- **One question on the home screen** (setup step 1 and "Household details"), using the same
  Yes / No / Not sure control as the person questions (`YesNoGroup`). The wording is the owner's:
  "Is your family on the BPL (Below Poverty Line) list?" with the hint "A BPL ration card is one sign."
  Hindi uses "गरीबी रेखा से नीचे (BPL)"; it is marked for native review.
- **"Not sure" is the starting point and saves `null`,** never `false`. A family that skips the question is
  saved as unknown. Changing from "No" back to "Not sure" sends `null` and clears the answer.
- **A result that needs it** says "We need to know if your family is BPL" with the usual "Answer this" link,
  which opens the household screen (`/household/edit`), where the question is.
- **Size for older readers:** the answers are the shared control's boxes (about 56px tall, 20px text), the hint
  and the question are 18px or larger. A test measures the tap boxes and the text sizes in the browser.
- **Edit screen:** an older server that does not send `is_bpl` shows "Not sure".

## Alternatives
- A checkbox ("We are BPL"): a missing tick cannot be told from "no".
- Ask only people who say their income is low: assumes what the BPL list means, and BPL lists are state lists.
- Put it in the family-papers step with the BPL card: mixes a status with its proof (decision 033).

## Consequences
- The hint tells people the card is evidence, not the answer: a BPL family without the card can still say yes.
- No scheme uses `is_bpl` yet, so asking has no effect on results until IGNWPS (and later IGNOAPS) are switched.
- States keep their own BPL lists; the words say "the BPL list" because we cannot check which state's.
