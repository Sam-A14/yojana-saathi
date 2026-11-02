# 004 – Scheme seed format, versioning, and how data reaches production

## Context
Schemes are labelled by hand (ground truth for the LLM extractor later) and must reach the
database without a shell on Render. Eligibility results point at scheme version ids, so a version
must never change under them.

## Decision
- **One file per scheme** (`data/schemes_seed/<slug>.json`): scheme fields plus exactly one version
  (rules, benefit text, deadlines, source, documents). Checked by `data/scheme.schema.json`.
- **Strict list of rule fields** in the schema. A typo becomes an error while labelling instead of a
  silent "unknown" for every family. The list is the member and household attributes plus one
  `has_<code>` field per document in `documents.json`; a test keeps the `has_` part in sync.
- **Document gaps and rules are separate.** `scheme_documents` says which documents a scheme needs;
  rules say who qualifies. A document appears in `fixable` only when having it is also a condition.
- **Loader versioning:** if rules, benefit text, deadlines, source or document list differ from the
  current version, add version N+1 and make it current. If only `verified_at` / `approved_by`
  differ, update in place. No hash column: the file's content is compared with the stored row.
- **Validate everything, then write in one transaction.** One bad file loads nothing.
- **Examples carry their own warning:** `labeller_notes` (never stored) plus `verified_at = NULL`
  and `approved_by = seed-example-unverified` (stored), so the database itself says "not verified".
- **Reaching production:** a manual GitHub Actions workflow runs the loader against a
  `DATABASE_URL` secret. It only runs from `main`.

## Alternatives
- Free-text field names: no list to maintain, but typos pass silently.
- Overwrite version 1 on every change: simpler, but silently rewrites what past results meant.
- Run the loader on every Render start: needs `data/` shipped with the backend, and publishes data
  on every deploy with no human step.
- Run the loader from a laptop: the owner has no local Python setup.

## Consequences
- Adding a document means editing `documents.json` and the field list in the schema together.
- Anyone who can run workflows on `main` can change production data; the secret is the real gate.
- Seeded example schemes will appear in the database. The API must hide or label schemes with
  `verified_at = NULL` before real families use the app.
- `labeller_notes` is not in the database, so `not_encoded` conditions are not yet shown to users.
