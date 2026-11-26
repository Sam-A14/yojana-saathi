# 025 — A public privacy page, and copy that only says what the app does today

## Context
Privacy was a few sentences scattered over the home page, the sign-in screen and "Your data". Three
of them promised that we keep the email address "to send you alerts" later, but alerts are not
built, and decision 018 says copy must not promise them. They also said "we never sell or share it"
while the sign-in code is sent through an email service, which does receive the address.

## Decision
- **`/privacy` is a public page** with one section per question: what we keep, what we never ask
  for, why, how it is used, who else sees it, how long we keep it, how to delete it, and a link to
  the public code. It is linked from the footer (every page), the sign-in screen, the home page's
  privacy block, "Your data" on the dashboard, and the "your data was deleted" page.
- **Every sentence is about what the app does today**, checked against the code (table below).
  Nothing about alerts. A test fails if the word "alert" (or "अलर्ट") appears on the home page,
  sign-in, privacy or deleted pages; when alerts are built, change that test and this page together.
- **Say plainly where the email goes:** to the email service (Resend), only to send the code.
- **Say what deleting cannot reach.** We delete from our database; we cannot promise that copies in
  our providers' backups or the email service's own records are gone, so the page says they may remain.
- **"Deleted from our server" became "from our database"** on the buttons and messages, for the same reason.

## What each claim rests on
| Claim | Where it comes from |
| --- | --- |
| Email, language kept | `User.email`, `User.language`, `LoginCode` (`db/models/`) |
| Home and person facts kept | `Household`, `Member` columns (`db/models/family.py`) |
| Papers kept as yes / no only, never numbers | `MemberDocument.has` is a boolean; no field for a number exists |
| No Aadhaar, PAN, bank or phone number, no password | no such column anywhere in `db/models/`; sign-in is a code by email |
| Email service gets the address and the code | `ResendEmailClient` sends `Message(to, subject, text)` (`email/client.py`); the text contains the code |
| Code works 10 minutes; only a scrambled copy kept | `CODE_LIFETIME`, `LoginCode.code_hash` (`api/auth.py`) |
| Signed in up to 30 days | `SESSION_LIFETIME` (`api/auth.py`) |
| Delete removes user, household, people, papers, results, sessions, pending codes | `delete_me` and `ON DELETE CASCADE` on every table that points at `users` (`api/auth.py`, `db/models/`) |
| Answers are not sent to any AI service | no module under `api/` imports `app.llm`; the LLM is used only by the rule-extraction job |
| Rules decide the result | the rules engine in `rules/` (CLAUDE.md, rule 1) |
| No advertising or analytics code | none in `backend/app` or in `frontend/package.json` |
| Kept on the phone: sign-in key, language, text size, colour | `lib/session.ts`, `LanguageToggle`, `TextSizeToggle`, `ThemeToggle` |

Not claimed, because the code cannot show it: encryption at rest, the hosting providers' practices,
backup schedules, any retention period beyond "until you delete it" (there is no automatic deletion today).

## Alternatives
- **A section inside "Your data" only:** hidden behind a sign-in, so nobody could read it before
  giving an email. A public page can be read first.
- **Naming every hosting provider:** the code does not show them; only Resend is certain, so only
  Resend is named, and the rest is "our hosting and database services".
- **A longer legal text:** harder to read aloud to a parent, and every extra sentence is one more
  thing that has to stay true.

## Consequences
- If a new service receives family data (for example an AI model that writes explanations from
  answers), or alerts ship, this page, the table above and the "no alerts" test must change first.
- "Until you delete it" is true only while there is no automatic clean-up of old accounts.
- All the new Hindi is a first draft, marked "needs native review" in `messages/hi.ts`.
