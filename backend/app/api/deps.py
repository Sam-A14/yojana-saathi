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


def current_session(
    db: DbSession,
    now: Now,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UserSession:
    # HTTPBearer already returns None for a missing header, a non-Bearer scheme or an empty token.
    token = credentials.credentials.strip() if credentials else ""
    if not token:
        raise _not_signed_in()
    session = db.scalar(
        select(UserSession).where(
            UserSession.token_hash == hash_token(token), UserSession.expires_at > now
        )
    )
    if session is None:
        raise _not_signed_in()
    return session


def current_user(session: Annotated[UserSession, Depends(current_session)], db: DbSession) -> User:
    user = db.get(User, session.user_id)
    if user is None:  # cannot happen (sessions are deleted with their user), but fail closed
        raise _not_signed_in()
    return user


CurrentSession = Annotated[UserSession, Depends(current_session)]
CurrentUser = Annotated[User, Depends(current_user)]


def current_household(household_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Household:
    """The household in the URL, but only if it belongs to the signed-in user (else 403)."""
    household = db.get(Household, household_id)
    if household is None or household.user_id != user.id:
        raise _denied()
    return household


OwnHousehold = Annotated[Household, Depends(current_household)]


def get_today() -> date:
    """Today's date in India. A dependency so tests can fix the date (ages depend on it)."""
    return datetime.now(INDIA).date()


Today = Annotated[date, Depends(get_today)]
