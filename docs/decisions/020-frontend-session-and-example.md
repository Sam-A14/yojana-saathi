# 020 — How the frontend holds the session, and the example family

Builds on [019](019-email-otp-login.md) (the backend side of email login).

## Context
The app used a "family code" (household id + token) kept in `localStorage`, with the wizard's
progress stored next to it. With email login the server knows who a person is and what they have
done, so the browser needs far less. We also wanted people to see the value before giving an email.

## Decision
- **The session is `{token, email, householdId}` in `localStorage` (`lib/session.ts`)**, with the
  same in-memory fallback as before for blocked storage. The old `yojana.family` key is deleted.
- **`Family` stays `{id, token}`, now meaning household id + session token.** Every API function and
  most screens are unchanged; `useFamily()` builds it from the session.
- **No stored wizard step.** After sign-in the server decides where to go (`lib/next-path.ts`): no
  household -> first setup screen; household without members -> add the family; otherwise the
  dashboard. This also works on a second phone. The wizard is 4 steps (the code screen is gone).
- **A 401 on a request that carried a session ends that session** (in `lib/api.ts`), so every screen
  falls back to "sign in" instead of retrying with a dead token. A 403 stays "not this household".
- **Slow server message.** Every request starts a 3-second timer; if it is still waiting, a banner
  says the server is waking up (`lib/slow-requests.ts`, `WakingBanner`). The home page also calls
  `/health` once, so the backend wakes while the person reads.
- **"See an example" is the real screens fed with fixed data.** `lib/example-eligibility.json` is
  real rules-engine output for an invented family (a copy of the test fixture). `/example` and
  `/example/scheme/[slug]` reuse `MemberResults` and `SchemeDetail`, so there is no second
  design to keep in step, no server call and no sign-in. Every example page carries an "Example" banner.
- **The code box takes digits only and has no `maxLength`.** A maximum length would cut "123 456"
  (pasted from an email with a space) to five digits before our filter keeps the first six.

## Alternatives
- Keep a stored wizard step: more local state that can disagree with the server.
- A hand-made example dashboard: free to look any way, but it would drift from the real screens.
- Warm the server on every page: more requests than needed; the home page is where people arrive.

## Consequences
- The example includes two made-up schemes ("Example Scholarship", "Example Income-Limit Scheme") from
  the test data next to the real seeded ones. They are labelled "Example" by name.
- The session token in `localStorage` is readable by script on the page (see 019); the app renders
  no user-supplied HTML.
- Decisions [012](012-family-code-format.md) and [016](016-delete-forget-and-shared-phones.md)
  (family code, "Forget this device") are replaced by this and 019.
