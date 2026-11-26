# 027 — Sign in with Google (backend)

Builds on [019](019-email-otp-login.md). The button on the sign-in page comes in a second change.

## Context
Email codes only reach the owner's own address until a domain is verified with the email provider
(019). Until then nobody else can sign in. Google sign-in needs no domain and costs nothing, and the
spec already lists "Google or email OTP".

## Decision
- **`POST /auth/google`** takes `{credential, language?}`, where `credential` is the ID token Google's
  button gives the page. It returns the same `{access_token, expires_at}` as `/auth/verify`: one
  helper (`_open_session`) issues the 30-day session for both, so a Google session and an email
  session are indistinguishable afterwards.
- **The check is split in two.** `verify_google_signature` (`app/api/google.py`) only proves the
  token was signed by Google's current public keys, using the official `google-auth` library, and
  returns the claims. `auth.py` then checks what the token is *for*: `aud` equals our
  `GOOGLE_CLIENT_ID`, `iss` is `accounts.google.com` or `https://accounts.google.com` (Google uses
  both), `exp` is in the future, and `email_verified` is a real `true`. Our checks live in our code, so
  tests with a fake verifier really exercise them. One test runs the real library against a key made
  inside the test, to prove a wrong key, edited claims, an expired token and garbage all fail.
- **The user is found or created by lower-case email**, in the same `users` table, under the same
  per-email advisory lock the email-code flow uses. So both ways in reach the same household, and two
  simultaneous first sign-ins cannot create two users.
- **Only the email is kept.** The Google `sub`, name, photo and the token itself are never stored or
  logged. The language is taken from the request, and only when a new user is created.
- **One answer for every bad token** (`401 invalid_google_token`), so the reply does not say which
  check failed. `503 google_unavailable` if `GOOGLE_CLIENT_ID` is unset: the feature is simply off.
- **Email-code limits are untouched.** Google sign-in sends no email and uses none of the 3 an hour or
  80 a day.
- **New dependencies:** `google-auth` (the verification), `requests` (the transport it uses to fetch
  Google's public keys), and `cryptography` (its faster RSA backend; the tests also use it
  to make a signing key).

## Alternatives
- **Verify the token ourselves** (fetch the keys, check the JWT). More code to explain, more room for
  a subtle mistake in the one place a mistake means taking over accounts. Rejected: use the library.
- **Let the library check the audience too.** Fewer lines, but then a fake verifier in tests would
  skip the audience check and the test would prove nothing. Rejected.
- **The Google redirect (OAuth code) flow.** It needs a server-side secret and redirect URIs, which
  also cannot be wildcarded for previews. The ID-token flow needs only the public client ID.
- **Key users by Google's `sub`.** Safer if an address is ever reassigned, but it means storing one
  more identifier and linking it to email-code users. Not done: the owner decided "email only".

## Consequences
- **Email is the only identity key.** If a Google Workspace address is closed and later given to
  someone else, that person signs in to the old household, the same trust we already place in email
  codes. A `sub` column would fix it; add one if this product ever holds data that makes it matter.
- A stolen ID token works until it expires (about an hour); there is no `nonce` binding and no per-IP
  limit on this endpoint. The same exposure as a stolen session token, and 019 already notes no
  per-IP limit.
- Google's public keys are fetched from Google on every sign-in (the library does not cache them
  unless we add a cache; one extra request of about 100 ms is fine at this size); if Google
  is unreachable, `/auth/google` answers `401`, and the email option still works.
- Google's allowed origins cannot include Vercel preview URLs, so Google sign-in works only on the
  production site and localhost (README, "Sign in with Google").
