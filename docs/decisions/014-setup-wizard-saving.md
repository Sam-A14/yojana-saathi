# 014 — How the setup wizard saves, and what "not sure" means

## Context
A family answers about 50 questions across five screens, often on a cheap phone with a flaky
connection. Losing answers, or turning a shrug into a wrong answer, are the two ways to fail.

## Decision
- **Save at every step, not at the end.** Basics create the household (`POST`). A person is saved
  the moment its form is submitted (`POST`/`PATCH`/`DELETE`). Documents are saved on "Save and
  continue", the exclusion answers on "Finish". The step reached is kept in `localStorage`, so
  "Continue where I stopped" works, and moving forward never moves it backwards.
- **"Not sure" is null.** Every optional question offers it and starts on it. The API stores null as
  "not answered", and the rules engine then says "unknown" (decision 009) instead of guessing.
- **Documents.** `PUT .../documents` replaces the whole set, so a "not sure" document is simply left
  out of the request. Family-level papers (the list comes from `GET /documents`, which reads the same
  `HOUSEHOLD_DOCUMENT_CODES` the eligibility step uses) are asked once and written to every member,
  so a "no" is a real "no" for everyone and not "never asked".
- **Exclusion questions use `PATCH`** with only the five PM-KISAN facts, so nothing else about a
  person is touched, and editing a person's details never wipes these answers.
- **Adults** are those aged 18 or more by birth year, plus anyone with no birth year (skipping them
  could hide a real exclusion).
- **Starting again never silently replaces a saved code:** if one exists on the phone, the first
  screen asks whether to continue or start a new family.

## Alternatives
- One big form submitted at the end: a closed tab would lose everything, and the token (shown once)
  could be lost with it.
- Writing family papers only on the first member: other members would read as "not asked".
- Sending `false` for "not sure": would turn a shrug into a "no" and hide documents the family may have.

## Consequences
- More requests (one per person at the documents and exclusions steps, sent in parallel). Each is
  idempotent, so retrying after an error is safe.
- The document list is long for a big household. A later change can ask only about papers that
  matter for each person.
