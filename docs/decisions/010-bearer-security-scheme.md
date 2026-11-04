# 010 — Declare the access token as an HTTP bearer security scheme

## Context
Decision 008 sends the household token as `Authorization: Bearer <token>`. We read it with a
`Header(...)` parameter named `authorization`. Swagger UI (/docs) silently ignores header
parameters called Authorization, so every household endpoint was impossible to try from /docs.

## Decision
- `current_household` (in `app/api/deps.py`) depends on FastAPI's `HTTPBearer(auto_error=False)`.
  OpenAPI now declares an `http` / `bearer` security scheme, and /docs shows an **Authorize** button.
- `auto_error=False` so a missing or malformed token still reaches our own check and gives the
  same 403 and the same message as a wrong token (decision 008: failures must look alike).
- The hand-written `_bearer_token` parser is gone: `HTTPBearer` already treats a missing header,
  a non-Bearer scheme and an empty token as "no credentials".
- `tests/api/test_openapi_security.py` pins it: the scheme is declared, every `/households/{id}...`
  operation requires it, public endpoints and `POST /households` do not, and no `Authorization`
  header parameter is left.

## Alternatives
- `APIKeyHeader(name="Authorization")`: also shows in /docs, but the user would have to type the
  word "Bearer " themselves, and the schema would describe it as an API key.
- Leave the header parameter and tell people to use curl: keeps the bug and makes demos harder.
- `auto_error=True`: simpler, but the 403 text would differ from ours and could reveal which part was wrong.

## Consequences
- The request/response behaviour is unchanged (all existing token tests pass untouched).
- The OpenAPI schema has changed: generated clients would now see a security scheme and no
  `authorization` parameter.
