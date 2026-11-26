# 032 – Approving a proposal opens a pull request; nothing publishes without it

## Context
An extracted proposal sits in `review_items`. Turning it into a verified scheme meant copying JSON
by hand into `data/schemes_seed/<slug>.json`, setting `verified_at` and `approved_by`, and opening a
pull request. Slow, and easy to get wrong. Rule 3 of the project still holds: nothing reaches
families without a person reading it.

## Decision
- **Manual workflow "Approve scheme proposal"** (`workflow_dispatch`, `main` only) with inputs
  `review_item_id` and `approver`. It runs `python -m app.pipeline.approve`, which reads the item,
  writes `data/schemes_seed/<slug>.json`, and the workflow opens a pull request.
- **Refusals (exit 1, nothing written):** the item is not `pending`; `is_valid` is false; the slug
  is missing, malformed or differs from the item's; a rule has no stored quote; `benefit_text_en` is
  set but has no stored quote (an item from before decision 030); or the finished file fails the
  schema, the document list check or the rules engine. `is_valid` is not trusted alone: the checks
  run again on the file about to be written.
- **`verified_at` is today and `approved_by` is the typed name,** set only here. The extractor
  insists both are null, so a model cannot verify its own work. The pull request also records the
  GitHub user who ran the workflow, because the typed name is a claim, not a login.
- **Read-only database use.** The command only selects. The review item stays `pending`: marking it
  approved before the merge would be a decision outside the pull request. The same `DATABASE_URL`
  secret is used as in the seed workflow, so it is not itself read-only.
- **The description carries the evidence:** each top-level rule next to its quote, the benefit text
  next to its quote, the diff of the file, and a re-check of the quotes against
  `data/scheme_sources/<slug>.txt` as it is now (a changed source file is called out). Model text is
  only ever shown inside code fences longer than any backtick run it contains, and inline values are
  flattened to one line, so it cannot add headings or notify people.
- **Self-check in the job, no token.** A pull request opened with `GITHUB_TOKEN` does not start
  other workflows, so CI does not run on it. The job runs the seed-file and test-profile tests itself,
  and the description says closing and reopening the pull request starts the normal CI. A personal
  access token would remove that step but is a long-lived credential.
- **Tests no longer pin the exact set of schemes.** Four tests said "exactly pm-kisan and ignwps"; they
  would have failed on the first approved scheme. They now say "at least those two" and still reject
  the template's placeholders.
- **Keys are written in a person's order** (`field`, `op`, `value`), because JSONB returns the
  shortest key first and the same rule should read the same in every seed file.

## Alternatives
- Write to the database directly on approval: faster, but publishes without a reviewed diff.
- Commit to `main` from the workflow: no review at all.
- Make the workflow update the review item to `approved`: hides the fact that the merge has not
  happened; the item is already linked to the file by its number in the pull request.
- A personal access token so CI starts by itself: removes one click, adds a secret that can push code.

## Consequences
- Anyone who can run workflows on `main` can open pull requests from database content; the review
  and the merge are the real gate, and branch protection should require them.
- Proposals for a scheme that already has a seed file overwrite it in the pull request. The diff shows
  exactly what changes, and the loader adds a new version (decision 004).
- A new scheme has no test profile (`data/test_profiles/`) until someone writes one; the pull
  request checklist says so.
- Review items older than decision 030 cannot be approved until extracted again.
