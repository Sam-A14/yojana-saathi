# 051 — In-app alerts ("What's new for your family"), made by a daily job

## Context
The first schema had an `alerts` table meant for email. For the freeze the owner wants a minimal
version with **no email**: a list on the dashboard, filled once a day.

## Decision
- **Three kinds of news**, each decided by the rules engine, never by the LLM:
  - `new_scheme`: a member's status for a scheme is now "eligible" and was not at the last run.
  - `age_threshold`: a member reaches an age at which a scheme starts to fit.
  - `rule_change`: a scheme's current version changed since this family last had a result for it.
- **The "before" is `eligibility_results`**, a table that existed but was unused. The job rewrites
  it for every family on every run (one row per member and scheme, "not eligible" included).
- **A family is never flooded on its first look.** A member with no stored results is saved quietly;
  only changes after that are news. Same for a member added later.
- **Ages come from a birth year only**, so "within 60 days" cannot be exact. An age alert is made
  from 60 days before 1 January of the year the member reaches the age (the earliest possible
  birthday) until the end of that year, once. The wording says "in 2027", not a date. Which ages
  count is read from the schemes' own rules (`age gte N`, `age between [N, M]`), so a new scheme
  needs no change here. Upper limits are not alerts.
- **Storage:** migration 0010 adds `alerts.read_at` (NULL = unread) and `alerts.dedupe_key` with a
  unique index on (user, key). The job inserts with `ON CONFLICT DO NOTHING`, so running it twice,
  or every day, repeats nothing. In-app alerts are stored as `sent`: nothing else delivers them.
- **Payload, not prose.** The row holds the member's nickname and scheme names; the web app writes
  the sentence in English or Hindi.
- **API:** `GET /households/{id}/alerts` (newest 50 and the unread count), `POST .../alerts/{id}/read`
  and `POST .../alerts/read-all`. A family sees and marks only its own alerts.
- **Job:** `python -m app.alerts.daily`, run by the "Daily alerts" workflow at 02:47 India time and
  by hand. One family's failure is logged and skipped; the run then exits 1 so it shows red.

## Alternatives
- Email: needs a sender, unsubscribe and privacy work. Out of scope for the freeze.
- Compute the news when the dashboard opens: slower page, no memory of "before", no "read" state.
- Exact "within 60 days" for age: impossible without a birth date, which we do not store.

## Consequences
- The first run only saves a baseline: alerts start from the second day.
- A member is "seen" once results are stored for them. With no active scheme at all nothing is
  stored, so that member would be treated as new again; the catalogue is never empty in practice.
- "Now fits" also fires when a family corrects an answer and a scheme moves from near-miss to
  eligible, which is good news too, not only a new scheme.
- The list keeps the 50 newest. Older rows stay in the table.
