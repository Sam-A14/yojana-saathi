# 023 — Six code boxes over one input, and a 30-second resend wait

## Context
The sign-in code was one wide text box. Six separate boxes are easier to read and to check against
the email, but six real inputs are a known trap: they break paste, the phone's code suggestion,
delete and screen readers. People also tapped "Send me a new code" several times in a row.

## Decision
- **One real `<input>` under six drawn boxes** (`components/OtpInput.tsx`). The input is invisible
  and covers all the boxes, so the whole row is one 56px-tall tap target. It keeps
  `autocomplete="one-time-code"`, a numeric keyboard, paste and delete as they were. The boxes are a
  picture (`aria-hidden`); a screen reader hears one field labelled "6-digit code".
- **Digits only, first six kept:** "123 456" pasted from an email becomes 123456. There is no
  `maxLength`, because the browser would cut "123 456" to five digits before the filter runs.
- **Resend wait:** after a code is sent, "Send me a new code" is disabled for 30 seconds, with the
  seconds written above it in normal-contrast text (a greyed-out button alone is hard to read). The
  number changes every second, so it is hidden from screen readers; they get one sentence when the
  wait starts and one when it ends.
- **The wait is only a convenience.** The server enforces its own limits (codes per email per hour,
  and a daily cap) and does not trust the page. The countdown uses an end time, not tick counting,
  so a phone that pauses the page still shows the right number.
- **Room for "Continue with Google":** the email form is its own card, and a comment marks the spot
  above it. Nothing is drawn for a button that does not exist yet: an empty gap would look like a
  bug, and a disabled Google button would promise something we do not have.

## Alternatives
- **Six real inputs with auto-advance:** the classic look, but paste, autofill and screen readers
  all need extra code to work, and each box would be a small tap target.
- **Auto-submit on the sixth digit:** faster, but a mistyped code would be sent without a chance to
  look, and the screen has one clear main action (Sign in).
- **A longer wait or a growing wait:** more protection, but that is the server's job.

## Consequences
- The existing "send a new code" test now skips the wait with Playwright's fake clock.
- Each box is about 36px wide on a 360px phone; the 48px rule is met by the row as a whole.
- Two new Hindi sentences are marked "needs native review" in `messages/hi.ts`.
