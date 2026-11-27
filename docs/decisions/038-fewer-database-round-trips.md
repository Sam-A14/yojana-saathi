# 038 – One lookup for who is calling, and no read-back after a save

## Context
Saving a household was slow on the live site. Counting the statements the database really received (not
only the ones the ORM reports) showed 10 to 14 round trips per request, and a round trip is the expensive
part when the database is across a network (and a new connection, after the database slept, costs several
more). Two of the causes were avoidable:
- Every request looked up the session, then the user, then (for a household URL) the household: three
  round trips before any work started.
- After a save, the response read `updated_at` back: the database sets it, the commit expired it, and
  serialising the answer opened a second connection (pre-ping, BEGIN, SELECT, ROLLBACK): four round trips.

## Decision
- **One query per lookup.** `current_user` joins `users` to `sessions` (was 2 queries). `current_household`
  is a single `sessions LEFT JOIN households` on the household's id **and** its owner (was 3): no row means 401
  (no valid session); a row with no household means 403. Someone else's household and one that does not
  exist both come back as "no household", so they still get the identical 403 and a stranger still cannot
  tell which ids exist. A request with no token is still turned away first (401), before the household id is
  read, by a small `bearer_token` dependency that touches no database.
- **`eager_defaults` on `Household` and `Member`.** Their `updated_at` is set by the database on UPDATE; with
  this setting the UPDATE returns it (`UPDATE ... RETURNING updated_at`), so nothing is read back.
- **Tests count what is sent** (SQL statements per request, in `tests/api/test_round_trips.py`), and the
  access tests (401, 403, expired session, no token) are written so they would fail if the rules moved. Run
  on the old code, the four counting tests fail and the five access tests pass.

## Measured (the real API, a local database behind a link modelled at 80 ms round trip)
Round trips and whole-request time, before to after: edit household 11 to 5 (937 to 427 ms); create
household 7 to 6; add a person 9 to 7; edit a person 14 to 11; dashboard 10 to 8 (843 to 675 ms). The model
is a model, but the counts are exact.

## Alternatives
- Cache the session in memory: saves the query but means a signed-out session keeps working for a while.
- Drop `pool_pre_ping`: saves one round trip per checkout, but a connection the database closed (Neon, after
  its idle minutes) would then fail a real request instead of being replaced.
- Return the household from the lookup and the user from a second query only when needed: that is what this
  is; no endpoint needs both together.

## Consequences
- `current_household` no longer loads the `User`. Nothing used it alongside the household.
- Further savings exist (the person endpoints read documents after the commit, which costs a second checkout),
  left for a later change.
