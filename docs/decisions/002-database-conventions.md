# 002 – Database conventions

## Context
Session 2 creates the tables from `PROJECT_SPEC.md` section 5. Several small choices repeat across
all eleven tables and are hard to change once data exists.

## Decision
- **Ids:** UUIDs for family data (users, households, members) so ids in URLs cannot be guessed.
  Plain integers for catalogue and pipeline tables (schemes, versions, documents, review items,
  alerts), which are not secret and are easier to read in logs.
- **Fixed value lists** (status, level, gender, …) are `VARCHAR` plus a `CHECK` constraint, not
  native Postgres enums.
- **Not enforced in the database:** `marital_status`, `category`, `income_band`, `occupation`,
  `education`. Their allowed values belong to the rules field list, which is added with the rules
  engine and checked by the API.
- **Unanswered is NULL.** Household and member attributes are nullable, because the rules engine
  must tell "not answered" (unknown) apart from any real answer.
- **Deleting a user cascades** (ON DELETE CASCADE) through household, members, member documents,
  eligibility results and alerts, done by the database itself. Rows that point at the shared
  catalogue use RESTRICT, so a scheme version or document in use cannot be deleted by accident.
- **Constraint names are fixed** by a naming convention so migrations are repeatable.
- **`schemes.current_version_id`** and `scheme_versions.scheme_id` point at each other. The first
  is nullable and added after both tables exist (`use_alter`).
- **Columns the spec left open** (chosen here): `scheme_documents.applies_to` is `applicant` or
  `household`; `review_items` has scheme_id (nullable), proposed_rules_json, source_quote, status,
  reviewed_by, created_at, reviewed_at; `alerts` has user_id, type, status, payload_json,
  scheduled_for, sent_at, created_at.

## Alternatives
- Native enums: stricter, but adding a value needs special migration code.
- Integer ids everywhere: simpler, but sequential ids in URLs invite guessing.
- Checking every value list in the database: duplicates the rules field list and drifts from it.

## Consequences
- Adding an allowed value to a CHECK list needs a migration (drop and recreate the constraint).
- The API layer must validate the value lists the database does not.
- Account deletion is one `DELETE` on the user row.
