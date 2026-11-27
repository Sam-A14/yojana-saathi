# 041 – Pages are kept alive, so a "Saving…" flag must be cleared when the page is shown again

## Context
On the live site, Household > Edit > Save showed "Saving…" for good. Nothing was wrong with the network:
the server log showed no request, the console had no errors, and the browser's list showed only the
page's loading requests, because **no save was ever sent**. Reproduced locally against the real backend:

1. Save on the edit page works: one PATCH, then the dashboard.
2. Next.js does not throw the edit page away when you navigate off it. It keeps it alive, hidden, with its state.
   The button still said "Saving…" (hidden) because the page set `saving = true` before the request and only
   cleared it when the request failed; after a good save it relied on the navigation to get rid of it.
3. The next time the person opened "Edit household details", the kept page was shown again, with its button
   still "Saving…" and disabled. Nothing was running and nothing could finish.

The same pattern was in the household edit page and in setup steps 1, 3 and 4.

## Decision
- `useResetWhenShown(reset)` (`lib/use-reset-when-shown.ts`): runs `reset` each time a page is shown, first time
  and on every return (effects run again when a hidden page is shown). The four pages that set a busy flag and
  navigate on success use it to clear `saving` and any old error.
- Not "clear it right after the save": the button would come back for the moment before the next page appears,
  and a double click could send a second save (a second person, in the setup steps).
- Tests (`tests/e2e/save-stuck.spec.ts`): one Save sends exactly one PATCH and reaches the dashboard within
  2 seconds; opening the edit page again after a good save shows an enabled "Save changes", and a second save
  sends a second PATCH (three times in a row); going back to the papers step is not stuck either. Without the fix
  the first save passes and the return visits fail.

## Alternatives
- Mark the pages so Next.js does not keep them: loses the behaviour that keeps typed answers when someone goes
  back and forth, and fights the framework.
- Remount the page with a changing key on every visit: same loss, and the key has to come from somewhere.
- Reset in each handler's success path: the double-click window above.

## Consequences
- Any new page with a busy flag that navigates away on success needs the same line; the sign-in page already
  did the equivalent by hand (its verify function).
- A page that is shown again briefly shows its old state for one frame before the effect clears it.
