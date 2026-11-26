# 028 — The "Continue with Google" button (frontend)

Builds on [027](027-google-sign-in.md) (the backend) and [019](019-email-otp-login.md) /
[020](020-frontend-session-and-example.md) (the email flow and the session).

## Context
The backend can sign someone in from a Google ID token. The sign-in page needs a button that gets
that token and hands it over, without changing what happens after sign-in, and without breaking the
rules for older and low-vision users (decisions 018, 021, 026: 48px+ tap targets, nothing under 16px).

## Decision
- **Google Identity Services, Google's own button.** `lib/google.ts` loads
  `accounts.google.com/gsi/client` once and `components/GoogleSignIn.tsx` asks it to draw the official
  "Continue with Google" button (outline theme, `continue_with` wording, the page language). The ID
  token goes to `POST /auth/google` and nowhere else; it is not stored.
- **The button is scaled up 1.4 times.** Google's largest button is 40px tall with 14px text, under
  our 48px and 16px minimums. We cannot draw our own: only Google's button gives us an ID token without
  a redirect. So the whole official button is scaled (40 x 1.4 = 56px tall, text about 20px), the same
  height as our other buttons. Its look is unchanged, only its size. The height is reserved from the
  start so the page does not jump when it appears.
- **Switched on by `NEXT_PUBLIC_GOOGLE_CLIENT_ID`.** Missing or blank: no button, no "or" line, no
  Google sentence, and the heading stays "Sign in with email". The button also vanishes (with its
  "or") if Google's script cannot load (offline, ad blocker), so the email form is never left under a
  lone "or".
- **After sign-in the same path as a code.** `/auth/google` answers with only a token, so the page asks
  `GET /me` for the email and household, saves `{token, email, householdId}` like the code flow, and the
  existing `nextPathFor` sends the person to setup or the dashboard.
- **`auto_select: false`.** Google must not sign anyone in without a tap: the phone may be shared.
- **Privacy.** `/privacy` says Google tells us the email and we keep only that, and that the Google
  button comes from Google so Google can see the sign-in page was opened. The sign-in page repeats the
  first sentence when the button is shown.
- **Tests follow the build.** The client ID is baked into the site at build time, so one build shows
  one state. CI builds twice: the usual build (no ID) runs the whole suite, then a second build with a
  dummy ID runs `google-signin.spec.ts`. Google's script is replaced by a plain button in the tests.

## Alternatives
- **Our own styled button.** Would meet the size rules exactly, but cannot produce an ID token. The
  "One Tap" prompt can, but browsers and users can silence it, so the button could silently do nothing.
- **Leave Google's button at 40px.** Official, but fails our 48px rule for the people we build for.
- **A runtime setting for the client ID.** A server route or an extra request just to read a public
  value; the build-time variable is simpler and matches `NEXT_PUBLIC_API_URL`.

## Consequences
- Google sign-in works only where its Authorized JavaScript origins allow: the production site and
  localhost. On Vercel previews the button shows if the variable is set there, but Google refuses it.
  Set the variable for Production only if that confusion matters (README).
- If the window is resized after the button is drawn (phone turned sideways), it keeps its first width.
- Scaling a cross-origin iframe is outside Google's published customisations. If Google ever objects,
  the fallback is the unscaled button plus a larger "or use your email" button.
- Hindi strings for this change are marked "needs native review" in `messages/hi.ts`. Google draws the
  button's own words in Hindi itself.
- The landing page link now says just "Sign in" (it used to say "Sign in with email"), because Google
  is an option too. The home page and the header then both have a "Sign in" link, so tests find the
  landing one inside `<main>` and the header one inside the banner. The dashboard's "not signed in"
  link still says "Sign in with email".
