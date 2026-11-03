"""What every endpoint needs: a database session, and proof the caller owns the household."""

import uuid
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

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


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def current_household(
    household_id: uuid.UUID,
    db: DbSession,
    authorization: Annotated[str | None, Header(description="Bearer <access token>")] = None,
) -> Household:
    """The household in the URL, but only if the caller's token belongs to it (else 403)."""
    token = _bearer_token(authorization)
    household = db.get(Household, household_id)
    stored = (household.access_token_hash if household else None) or _NO_HASH
    given = hash_token(token) if token else ""
    if household is None or token is None or not hashes_match(stored, given):
        raise _denied()
    return household


OwnHousehold = Annotated[Household, Depends(current_household)]
