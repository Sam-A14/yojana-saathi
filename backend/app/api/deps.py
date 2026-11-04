"""What every endpoint needs: a database session, and proof the caller owns the household."""

import uuid
from collections.abc import Iterator
from datetime import date, datetime
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.facts import INDIA
from app.api.security import hash_token, hashes_match
from app.db.models import Household
from app.db.session import new_session


def get_db() -> Iterator[Session]:
    """One session per request. Closing without commit rolls back, so a failed request leaves no
    half-written data. Endpoints that change data call commit() themselves."""
    session = new_session()
    try:
        yield session
    finally:
        session.close()


DbSession = Annotated[Session, Depends(get_db)]


# The same message for every failure. Different messages (or 404 vs 403) would let a stranger
# find out which household ids exist.
def _denied() -> HTTPException:
    detail = "Missing or invalid access token for this household."
    return HTTPException(status_code=403, detail=detail)


# What we compare against when the household does not exist, so both paths do the same work.
_NO_HASH = hash_token("no such household")


# HTTPBearer (rather than a plain "Authorization" header parameter) is what makes /docs show an
# Authorize button: Swagger UI ignores header parameters named Authorization, but it does understand
# a declared security scheme. auto_error=False because the built-in error would be a different
# status and message from ours (see _denied), and would tell a stranger which part was wrong.
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="The family's access token, as returned once by POST /households.",
)


def current_household(
    household_id: uuid.UUID,
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Household:
    """The household in the URL, but only if the caller's token belongs to it (else 403)."""
    # HTTPBearer already returns None for a missing header, a non-Bearer scheme or an empty token.
    token = credentials.credentials.strip() if credentials else ""
    household = db.get(Household, household_id)
    stored = (household.access_token_hash if household else None) or _NO_HASH
    given = hash_token(token) if token else ""
    if household is None or not token or not hashes_match(stored, given):
        raise _denied()
    return household


OwnHousehold = Annotated[Household, Depends(current_household)]


def get_today() -> date:
    """Today's date in India. A dependency so tests can fix the date (ages depend on it)."""
    return datetime.now(INDIA).date()


Today = Annotated[date, Depends(get_today)]
