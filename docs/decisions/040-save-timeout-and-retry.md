# 040 – A save gives up after 15 seconds; PATCH and PUT are tried once more

## Context
`fetch` has no time limit of its own: a request that is neither answered nor refused (for example on a
connection that went stale while the page sat open) never ends, and a screen that shows "Saving…" waits with
it. We first suspected that for a report of an endless "Saving…" with no request in the server log. **That
was not the cause of that report** (decision 041: the page was stuck by its own leftover state, and no request
was ever sent). The missing time limit is still a real gap, so the limit and retry below are kept as
a safety net for the stall that can happen on a phone.

## Decision
- **Every request that changes something** (`PATCH`, `PUT`, `POST`, `DELETE`) is cut off after **15 seconds**
  with an `AbortController` (`limits.writeTimeoutMs` in `lib/api.ts`).
- **`PATCH` and `PUT` are tried once more** after a stall, automatically, on a fresh connection. They set fields
  to the values sent, so doing one twice leaves the same result. **`POST` and `DELETE` are never repeated**: a
  first attempt that "timed out" may still have arrived, and a second one would add a second person.
- **Only a stall is retried.** A refused connection ("network") or a server error is reported at once and not
  repeated: retrying would only double the wait.
- **Then a message:** "Saving is taking too long. Your answers are still here. Try again." (its own error kind
  `timeout`, shown by every page that already shows errors). The form is usable again with everything the person
  typed. The Hindi is marked for the owner's review.
- **Reads (`GET`) are not timed out.** The first request after the host has slept can legitimately take up to a
  minute and the "waking up" banner promises that; giving up at 15 seconds would turn a slow start into an error.

## Alternatives
- Time out reads as well: breaks the cold start, the very case the banner exists for.
- Retry `POST` too: risks saving a person twice.
- A longer limit (30 s): the person waits twice as long for the same stalled connection.
- Show a "Cancel" button instead: asks a non-technical person to decide something the app can decide.

## Consequences
- A save on a genuinely slow cold server can now fail with the message after 30 seconds (two tries) where it
  would before have waited up to a minute. Trying again then works because the server is awake.
- A timed-out `POST` (adding a person) can leave the person added; the message says "try again", so the list
  may show them twice. The server has no duplicate check; noted, not solved here.
- The 15 seconds is a number in one place, and tests shorten it.
