# 046 — Seed the database when a merge changes the data

## Context
Merging a scheme pull request did nothing for families until the owner remembered to run **Seed
database** by hand. The goal is: paste a source, review the Hindi and the diff, click Merge.

## Decision
- **Seed database** also runs on a push to `main` that changes `data/schemes_seed/**` (except the
  template) or `data/documents.json`. The manual button stays.
- A new first step waits until the database is at the newest migration
  (`python -m app.db.migration_status`, up to 15 minutes, a check every 20 seconds). A merge starts
  the Render deploy (which runs the migrations) and this workflow at the same moment; without the
  wait, a pull request that adds a column and a scheme fails with a SQL error.
- The workflow still refuses any branch but `main`, and the existing concurrency group keeps two
  seeds from racing.
- `documents.json` is a trigger because a new paper code that no scheme change accompanies would
  otherwise never reach the database.

## Alternatives
- Run `alembic upgrade head` from the workflow: it would make the workflow own the migrations, and
  the deploy already does that. Waiting keeps one owner for the schema.
- Seed from the deploy itself: Render's free tier has no shell or hook for it.
- Keep it manual: it needs the owner to remember a step after every merge.

## Consequences
- A merge is the approval and the publish. There is no pause between "Merge" and "families see it",
  so the checklist (`docs/scheme-review-checklist.md`) is read before merging.
- If the deploy fails or takes over 15 minutes the seed fails with a clear message. After the deploy
  is fixed, run the workflow by hand (nothing is lost; the seed is safe to repeat).
- A change to `schemes_seed` that the loader refuses (a typo) fails the run after the merge, not
  before. CI already runs the seed-file tests on the pull request, which catches nearly all of it.
