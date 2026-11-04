# 016 — Delete my data, Forget this device, and shared phones

## Context
Many families share one phone. Two different things can be meant by "remove me": erase the family
from our server, or just stop this phone from opening it. Mixing them would either lose a family's
data by accident or leave it behind on a server when someone thought it was gone.

## Decision
- **Delete my data** calls `DELETE /households/{id}` (the database cascades to people, papers and
  results), then clears this phone, then shows its own `/deleted` page. It asks first, says it cannot
  be undone and that the family code will stop working, and offers "No, keep my data" as an equal
  button. If the server cannot be reached, nothing is cleared and the person can try again.
- **Forget this device** only clears the family code from this phone. The family stays on the server
  and opens again with its code. It asks first, with a reminder to keep the printed code safe, because
  without it the family cannot be opened again by anyone.
- Both live under "Your data" at the bottom of the dashboard, as two separate buttons.
- Pages keep their own state when Next.js hides them (cacheComponents keeps up to 3 routes). On a
  shared phone that showed a second family the first family's typed answers. Tests found and fixed three:
  the setup form came back with the last district, income and area; the "I have saved my family
  code" box stayed ticked; and the pasted code stayed in the Resume box. The first two are fixed by
  structure (the form and the code screen are keyed by the family), the third by clearing the box.
- "Your data was deleted" is its own page, not a flag in dashboard state, so it cannot greet the next
  family by mistake.

## Alternatives
- One "Remove my data" button that does both: the person cannot choose, and a mistake is permanent.
- Keep the state-preserving behaviour and reset everything on navigation (`router.bfcacheId`): the
  Next.js docs call it a last resort, and it also removes state that is useful on Back.

## Consequences
- The dashboard and scheme screens are keyed by the family too, as a precaution. I tried to make a
  test fail without it (forget on one family, resume another, then slow server, then Back) and could
  not, so it is a precaution and not a proven fix. Why those two screens behave differently from the
  setup form is not understood; if it matters, check `useRouter().bfcacheId` and the Next.js docs on
  preserving UI state.
- A phone that was not "forgotten" keeps the family code in `localStorage`. There is no auto-expiry yet.
