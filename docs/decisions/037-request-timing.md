# 037 – Time every request, and measure the database round trip

## Context
Saving a household was very slow on the live site while Render was kept warm. Two suspects: the free
database (Neon) suspending after a few idle minutes, and the number of database round trips per request
multiplied by the distance between Render and Neon. `/health` never touches the database, so keeping it
warm says nothing about Neon. Without numbers from production this stays a guess.

## Decision
- **A timing middleware** (`app/timing.py`, plain ASGI) records, per request: total time, time inside
  database statements, number of statements, and number of new connections. It writes one log line to
  stdout (Render shows it) and sets a `Server-Timing` header. Slow requests (over 2 s) are warnings.
- **Nothing identifying is logged:** the route pattern (`/households/{household_id}`), never the URL;
  no ids, tokens or bodies. Unknown paths are logged as `(no route)`.
- **Numbers per request, not global:** a context variable holds them, so concurrent requests and the
  worker threads never mix them up.
- **`GET /health/db`** runs four `SELECT 1` and reports the first (connection included) and the median of
  the other three, which is one network round trip. It is a diagnostic, not an uptime check: it wakes the
  database.
- **Known blind spot, stated:** SQLAlchemy does not report the round trips psycopg makes itself (BEGIN,
  COMMIT, ROLLBACK, the pool's pre-ping), so `db` is lower than the real database time on a far-away
  database. `total` is the honest figure; `/health/db` gives the price of one round trip to read it with.

## Alternatives
- Guess and fix: a fix aimed at the wrong cause costs a deploy and leaves the problem.
- An APM service (Sentry performance, Datadog): more to learn and configure for the first question; the
  header and log line need nothing new.
- Time inside each endpoint: touches every endpoint; middleware plus engine events touches none.

## Consequences
- A deploy adds a few microseconds per statement (two timer reads).
- The log is the evidence: read a few `timing` lines for a save, and `round_trip_ms` from `/health/db`.
