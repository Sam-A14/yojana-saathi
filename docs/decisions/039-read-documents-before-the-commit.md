# 039 – Editing a person reads their documents before the commit

## Context
`PATCH .../members/{id}` saved the change, committed, and only then read the person's documents for the
answer. A commit gives the connection back to the pool, so the read checked one out again: the pool's
pre-ping, `BEGIN`, the `SELECT`, and a `ROLLBACK` on release. Three of those four are pure overhead, and each is
a network round trip when the database is far away (decision 038 has the measurements).

## Decision
- `update_member` applies the change, reads the documents (same transaction, nothing about them changes),
  then commits and returns. One connection checkout for the whole request.
- A test records the SQL in order and asserts the documents are read once and **before** the commit, so a later
  edit that moves the read back after it fails.

## Alternatives
- Re-use the documents the client already has: the server must not trust the client for the answer.
- Make the answer not include documents: changes the API for a saving of three round trips.

## Consequences
- The saving only appears together with decision 038's `eager_defaults`: until `updated_at` stops being read
  back after a save, that refresh needs the second checkout anyway. Measured on the real API behind a link modelled at 80 ms,
  editing a person goes from 11 to 7 round trips (921 to 604 ms) with both changes, and from 14 to 14
  with this change alone.
