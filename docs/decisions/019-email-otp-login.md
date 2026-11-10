# 019 — Sign in with an emailed one-time code

Supersedes [008](008-anonymous-access-token.md) (anonymous access token) and
[012](012-family-code-format.md) (the family code).

## Context
A family code is a bearer secret the family has to save and paste. Lose it and the household is
gone, and nobody can delete it. The product also needs an email address later, for alerts. The
owner decided: sign in first, no passwords.

## Decision
- **Flow.** `POST /auth/request-code` emails a 6-digit code; `POST /auth/verify` returns a session
  token; the frontend sends it as `Authorization: Bearer`. The first successful sign-in creates the
  user. A user has one household (`households.user_id` is NOT NULL and unique).
- **Limits, all counted in the database** (so they survive restarts and several workers): a code
  lives 10 minutes; 5 wrong guesses kill it; only the newest code counts; 3 codes per email per hour;
  a global cap of 80 codes per UTC day (`EMAIL_DAILY_LIMIT`) answers `503 busy` before Resend's free
  quota (about 100 a day) runs out. A per-email advisory lock makes two simultaneous requests take
  turns, so the limits and the guess counter cannot be beaten by racing.
- **Codes are stored as HMAC-SHA256 with a server secret** (`AUTH_SECRET`), the email being part of
  the input. A 6-digit code has a million values; an unkeyed hash would be reversible in a blink if
  the table leaked. The secret is not in the database, so a database-only leak is not enough.
- **Session token**: 256 random bits, stored as SHA-256 (as decided in 008), valid 30 days,
  sent as a Bearer header and kept in the browser's `localStorage`.
- **Same answer for any address** from `request-code`, so it cannot be used to find out who has an
  account. Different statuses for different problems: `401` not signed in, `403` signed in but not
  your household (the same answer for someone else's household and for one that does not exist).
- **Email** goes through an `EmailClient` interface (`app/email/`): a Resend client and an in-memory
  fake for tests, chosen by `EMAIL_PROVIDER`. `EMAIL_FROM` is a setting, so moving from Resend's
  test sender to the owner's own domain is a configuration change. Nothing logs a message, and an
  `EmailError` carries only a status number. A failed send is rolled back, so it uses up no quota.
- **Delete my data is `DELETE /me`.** It removes the user and their email; the household, members,
  documents, results, alerts and sessions go with them through `ON DELETE CASCADE`. Pending codes
  are keyed by email, so they are deleted explicitly. The old `DELETE /households/{id}` is gone.
- **Migration 0005** deletes households that have no user (test data, agreed with the owner).

## Alternatives
- **Cookie session.** The frontend (Vercel) and backend (Render) are different sites, so the cookie
  would need `SameSite=None` and credentialed CORS, and Safari and Chrome block such cookies more and
  more. A Bearer token works everywhere. The cost is that the token sits in `localStorage`, where
  script on the page could read it; the app renders no user-supplied HTML.
- **Anonymous start, sign in at the end.** Less friction up front, but two ways to own a household
  and a "claim" step. Rejected; the example dashboard lets people see value before giving an email.
- **Passwords, or Google sign-in.** Passwords add reset flows and a thing to leak; Google can be
  added later next to this.
- **Rate limits in memory.** Simpler, but lost on every restart, and wrong with more than one worker.
- **A slow password hash (bcrypt) for codes.** It would slow guessing, but the guess limit already
  allows only 5 tries per code, and the HMAC secret protects the table.

## Consequences
- Anyone can ask for codes for any address, up to the limits. A person cannot be flooded (3 an hour),
  but a determined attacker can use the day's 80 codes and block sign-in until tomorrow. There is no
  per-IP limit yet; add one before launch if that happens.
- Until a domain is verified with Resend, only the owner's own address receives codes (see README,
  "Going live with a custom domain").
- `AUTH_SECRET` must never change while users exist, or waiting codes stop working (sessions do not
  depend on it).
- The frontend, which still uses the family code, stops working against this backend until the
  frontend PR (C2) is deployed.
