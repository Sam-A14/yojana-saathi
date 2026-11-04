# 012 — The "family code" is the household id and the token, joined by a dot

## Context
Decision 008 gives a household one secret access token, shown once. But every household route is
`/households/{household_id}/...` and nothing can look a household up by its token (only a hash is
stored). So a person who "resumes with their token" would still need the household id, which they
never saw.

## Decision
- The code shown to the family is `<household id>.<token>`. The frontend builds and splits it
  (`lib/family-code.ts`); the backend is unchanged.
- The code is saved in `localStorage` (inside try/catch, with an in-memory fallback) the moment the
  household is created, because that is the only time the token exists. It is never put in a URL.
- Pasting is forgiving: spaces and line breaks inside the code are ignored, and the code is found
  inside a whole pasted text file (the downloaded file has other words in it).
- Copy, Download as text and Print are offered, and a checkbox ("I have saved it") must be ticked
  before going on. The screen says plainly that the code cannot be recovered.

## Alternatives
- A backend route that finds a household by token: a new public endpoint and a new way to probe
  tokens, to save about 40 characters.
- Store a short code and a separate id: two things to lose instead of one.

## Consequences
- The code is about 80 characters: copy and paste is the realistic path, typing it from paper is not.
  Print is therefore mostly a backup for someone who can scan or retype it.
- Anyone who holds the code has full access, like a shared link (decision 008). On a shared phone
  the saved copy stays in the browser until it is cleared; a "Forget this device" button comes with
  the dashboard.
