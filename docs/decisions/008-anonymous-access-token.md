# 008 — Opening a household without a login

> **Superseded by [019](019-email-otp-login.md).** The anonymous token was removed when email login arrived.

## Context
Login (Google or email OTP) comes later, together with alerts. The family dashboard needs a backend
now, but we do not want to ask for an email, a password or any identity number to use it
(CLAUDE.md rule 3). `households.user_id` was `NOT NULL`, and `users.email` is required and unique.

## Decision
- Creating a household returns a random access token (`secrets.token_urlsafe(32)`, 256 bits). It is
  sent as `Authorization: Bearer <token>`. Only its SHA-256 hash is stored (`households.access_token_hash`).
- Migration 0004 makes `user_id` nullable and adds a CHECK that a household has a user or a token
  hash. When login arrives, it fills in `user_id` for the households a person claims.
- A wrong, missing or malformed token, and an id that does not exist, all give the same 403. A
  different answer for "no such household" would let a stranger find out which ids exist.
  A member id from another household is a 404, because the caller has already proved they own
  their own household.
- The token is shown once and cannot be recovered; the create response says so.
- Unexpected errors become a plain `500 {"detail": ...}`; details go to the server log only.

## Alternatives
- A placeholder `users` row per household with a fake email: keeps the schema, but a fake email in a
  unique, required column is a hack, and it makes "claim this household on login" awkward.
- bcrypt or argon2 for the token: these slow down guessing of human-chosen passwords. A 256-bit
  random token cannot be guessed, so a fast hash is enough and keeps lookups an indexed equality.
- Token in the URL: ends up in logs, browser history and referrer headers. A header does not.
- 404 for a household that is not yours: leaks which ids exist.

## Consequences
- Losing the token means losing access to that household, including the ability to delete it, until
  login can claim it. The frontend must say this plainly and offer to copy or download the token.
- Anyone can create households (no rate limit yet). Spam would fill the table; add a limit before launch.
- Anyone holding the token has full access, like a shared link. The frontend should keep it in
  the browser's storage and never put it in a URL.
