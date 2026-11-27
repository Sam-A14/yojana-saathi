"""What every endpoint needs: a database session, and proof of who is calling."""

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.facts import INDIA
from app.api.security import hash_token
from app.config import get_settings
from app.db.models import Household, User, UserSession
from app.db.session import new_session
from app.email import EmailClient, build_email_client


def get_db() -> Iterator[Session]:
    """One session per request. Closing without commit rolls back, so a failed request leaves no
    half-written data. Endpoints that change data call commit() themselves."""
    session = new_session()
    try:
        yield session
    finally:
        session.close()


DbSession = Annotated[Session, Depends(get_db)]


# Two different failures, on purpose:
# - 401: you are not signed in (no session, or it expired). The frontend sends you to sign in.
# - 403: you are signed in, but this household is not yours. The same answer whether it belongs
#   to someone else or does not exist, so a stranger cannot find out which ids exist.
def _not_signed_in() -> HTTPException:
    return HTTPException(status_code=401, detail="Please sign in.")


def _denied() -> HTTPException:
    return HTTPException(status_code=403, detail="No such household for your account.")


# HTTPBearer (rather than a plain "Authorization" header parameter) is what makes /docs show an
# Authorize button: Swagger UI ignores header parameters named Authorization, but it does understand
# a declared security scheme. auto_error=False because the built-in error would be a different
# status and message from ours (see _not_signed_in).
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="The session token returned by POST /auth/verify.",
)


def get_now() -> datetime:
    """The current moment (UTC). A dependency so tests can move time (codes expire, limits)."""
    return datetime.now(UTC)


Now = Annotated[datetime, Depends(get_now)]


@lru_cache
def _email_client() -> EmailClient:
    return build_email_client(get_settings())


def get_email_client() -> EmailClient:
    """A dependency so tests can swap in a fake that records what would have been sent."""
    return _email_client()


Mailer = Annotated[EmailClient, Depends(get_email_client)]


def bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    """The session token from the Authorization header, or 401. No database: a request with no token
    is turned away before anything else is read."""
    # HTTPBearer already returns None for a missing header, a non-Bearer scheme or an empty token.
    token = credentials.credentials.strip() if credentials else ""
    if not token:
        raise _not_signed_in()
    return token


Token = Annotated[str, Depends(bearer_token)]

# Every request that needs to know who is calling used to read the session, then the user, then
# (for a household URL) the household: three round trips to the database before any work started.
# Each lookup below is ONE query. A round trip is the expensive part of a request when the
# database is a network away (docs/decisions/038).


def current_session(db: DbSession, now: Now, token: Token) -> UserSession:
    session = db.scalar(
        select(UserSession).where(
            UserSession.token_hash == hash_token(token), UserSession.expires_at > now
        )
    )
    if session is None:
        raise _not_signed_in()
    return session


def current_user(db: DbSession, now: Now, token: Token) -> User:
    """The signed-in user: the session and the user are found by one join."""
    user = db.scalar(
        select(User)
        .join(UserSession, UserSession.user_id == User.id)
        .where(UserSession.token_hash == hash_token(token), UserSession.expires_at > now)
    )
    if user is None:
        raise _not_signed_in()
    return user


CurrentSession = Annotated[UserSession, Depends(current_session)]
CurrentUser = Annotated[User, Depends(current_user)]


def current_household(household_id: uuid.UUID, db: DbSession, now: Now, token: Token) -> Household:
    """The household in the URL, but only if it belongs to the signed-in user (else 403).

    One query answers all of it: is the session valid (no row: 401), and does this household
    belong to that session's user (row with no household: 403). The household is joined on BOTH its
    id and its owner, so someone else's household comes back as "none", exactly like one that does
    not exist.
    """
    row = db.execute(
        select(UserSession.id, Household)
        .outerjoin(
            Household,
            (Household.id == household_id) & (Household.user_id == UserSession.user_id),
        )
        .where(UserSession.token_hash == hash_token(token), UserSession.expires_at > now)
    ).first()
    if row is None:
        raise _not_signed_in()
    household = row[1]
    if household is None:
        raise _denied()
    return household


OwnHousehold = Annotated[Household, Depends(current_household)]


def get_today() -> date:
    """Today's date in India. A dependency so tests can fix the date (ages depend on it)."""
    return datetime.now(INDIA).date()


Today = Annotated[date, Depends(get_today)]
