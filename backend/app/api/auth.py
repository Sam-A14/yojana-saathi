"""Sign in with an emailed 6-digit code. No passwords.

Limits (all counted in the database, so they survive restarts and work with many workers):
  * a code lives 10 minutes and allows 5 wrong guesses, then it is dead;
  * 3 codes per email per hour;
  * a global daily cap (EMAIL_DAILY_LIMIT) that protects the email provider's free quota.

Nothing here writes a code to a log. The code exists in the request body, the email, and (as a
keyed hash) the database.
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentSession, CurrentUser, DbSession, Mailer, Now
from app.api.google import GoogleTokenError, Verifier
from app.api.schemas import (
    Email,
    GoogleSignInIn,
    MeOut,
    RequestCodeIn,
    RequestCodeOut,
    SessionOut,
    VerifyIn,
)
from app.api.security import hash_code, hash_token, hashes_match, new_code, new_token
from app.config import get_settings
from app.db.models import Household, LoginCode, User, UserSession
from app.email import EmailError, Message

router = APIRouter(tags=["auth"])

CODE_LIFETIME = timedelta(minutes=10)
MAX_WRONG_GUESSES = 5
CODES_PER_EMAIL_PER_HOUR = 3
SESSION_LIFETIME = timedelta(days=30)
# Google puts either spelling in the "iss" claim of an ID token.
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


def _problem(status: int, code: str, message: str, **extra: object) -> HTTPException:
    """An error the frontend can tell apart (detail.code) and show in words (detail.message)."""
    return HTTPException(status_code=status, detail={"code": code, "message": message, **extra})


def _lock_email(db: Session, email: str) -> None:
    """Make two requests for the same email take turns, so the limits and the wrong-guess counter
    cannot be beaten by sending many requests at the same instant. Released at commit."""
    db.execute(select(func.pg_advisory_xact_lock(func.hashtext(email))))


def _count_codes(db: Session, since: datetime, email: str | None = None) -> int:
    query = select(func.count()).select_from(LoginCode).where(LoginCode.created_at >= since)
    if email is not None:
        query = query.where(LoginCode.email == email)
    return db.scalar(query) or 0


def _email_for(language: str, code: str) -> tuple[str, str]:
    # needs native review: the Hindi text is a first draft.
    if language == "hi":
        return (
            "योजना साथी: आपका साइन-इन कोड",
            f"आपका साइन-इन कोड {code} है।\n\n"
            "यह 10 मिनट तक चलेगा। अगर आपने इसे नहीं माँगा, तो इस ईमेल को अनदेखा कर दीजिए।\n\n"
            "यह केवल जानकारी है, सरकारी निर्णय नहीं। यह सरकारी ऐप नहीं है।",
        )
    return (
        "Yojana Saathi: your sign-in code",
        f"Your sign-in code is {code}.\n\n"
        "It works for 10 minutes. If you did not ask for it, you can ignore this email.\n\n"
        "Guidance only, not an official decision. Not a government app.",
    )


@router.post("/auth/request-code", status_code=202, response_model=RequestCodeOut)
def request_code(data: RequestCodeIn, db: DbSession, now: Now, mailer: Mailer) -> RequestCodeOut:
    settings = get_settings()
    secret = settings.auth_secret_checked
    _lock_email(db, data.email)

    # Old rows are of no use to either limit (they look back one hour and one day).
    db.execute(delete(LoginCode).where(LoginCode.created_at < now - timedelta(days=2)))

    if _count_codes(db, now - timedelta(hours=1), data.email) >= CODES_PER_EMAIL_PER_HOUR:
        raise _problem(
            429, "too_many_codes", "Too many codes for this email. Please try again in an hour."
        )
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)  # UTC, like the provider's
    if _count_codes(db, day_start) >= settings.email_daily_limit:
        raise _problem(503, "busy", "Sign-in is busy today. Please try again tomorrow.")

    code = new_code()
    db.add(
        LoginCode(
            email=data.email,
            code_hash=hash_code(secret, data.email, code),
            language=data.language,
            expires_at=now + CODE_LIFETIME,
            created_at=now,
        )
    )
    db.flush()
    subject, text = _email_for(data.language, code)
    try:
        mailer.send(Message(to=data.email, subject=subject, text=text))
    except EmailError:
        # Not sent: roll back, so a failed send uses up neither the 3 codes nor the day's quota.
        db.rollback()
        raise _problem(
            503, "email_failed", "We could not send the email. Please try again in a minute."
        ) from None
    db.commit()
    return RequestCodeOut(expires_in_minutes=int(CODE_LIFETIME.total_seconds() // 60))


@router.post("/auth/verify", response_model=SessionOut)
def verify_code(data: VerifyIn, db: DbSession, now: Now) -> SessionOut:
    secret = get_settings().auth_secret_checked
    _lock_email(db, data.email)

    # Only the newest code counts: asking for a new one cancels the old one.
    latest = db.scalar(
        select(LoginCode)
        .where(LoginCode.email == data.email)
        .order_by(LoginCode.created_at.desc())
        .limit(1)
    )
    wrong = _problem(401, "invalid_code", "That code is not right. Please check it and try again.")
    if latest is None or latest.used_at is not None:
        raise wrong
    if latest.expires_at <= now:
        raise _problem(401, "code_expired", "That code has expired. Please ask for a new one.")
    if latest.attempts >= MAX_WRONG_GUESSES:
        raise _problem(401, "too_many_attempts", "Too many wrong tries. Please ask for a new code.")

    if not hashes_match(latest.code_hash, hash_code(secret, data.email, data.code)):
        latest.attempts += 1
        left = MAX_WRONG_GUESSES - latest.attempts
        db.commit()  # the wrong guess must be remembered even though we answer with an error
        raise _problem(
            401,
            "invalid_code",
            "That code is not right. Please check it and try again.",
            attempts_left=left,
        )

    latest.used_at = now
    user = _find_or_create_user(db, data.email, latest.language)
    out = _open_session(db, user, now)
    db.commit()
    return out


def _find_or_create_user(db: Session, email: str, language: str) -> User:
    """The one user for this (lower-case) email, made on first sign-in. Email codes and Google
    both come through here, so both reach the same account and the same household."""
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, language=language)
        db.add(user)
        db.flush()
    return user


def _open_session(db: Session, user: User, now: datetime) -> SessionOut:
    """Issue the 30-day session token. The caller commits."""
    db.execute(delete(UserSession).where(UserSession.expires_at <= now))  # tidy up
    token = new_token()
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(token),
        created_at=now,
        expires_at=now + SESSION_LIFETIME,
    )
    db.add(session)
    return SessionOut(access_token=token, expires_at=session.expires_at)


def _google_email(claims: dict[str, Any], client_id: str, now: datetime) -> str | None:
    """The email in verified Google claims, or None if the token is not usable for us.

    Signature is already proven. Here: it was issued to OUR app (a token made for another app's
    client ID must not sign anyone in here), by Google, not expired, and Google vouches for the
    email. An unverified email could be anyone's, so it never signs in.
    """
    exp = claims.get("exp")
    valid = (
        claims.get("aud") == client_id
        and claims.get("iss") in GOOGLE_ISSUERS
        and isinstance(exp, int | float)
        and exp > now.timestamp()
        and claims.get("email_verified") is True  # a real boolean, not the string "true"
    )
    if not valid:
        return None
    try:
        return TypeAdapter(Email).validate_python(claims.get("email"))
    except ValidationError:
        return None


@router.post("/auth/google", response_model=SessionOut)
def sign_in_with_google(
    data: GoogleSignInIn, db: DbSession, now: Now, verify: Verifier
) -> SessionOut:
    """Sign in with a Google ID token. We keep only the email: not the name, photo or token.

    The email-code limits do not apply: no email is sent and nothing here uses the daily quota.
    """
    client_id = get_settings().google_client_id
    if not client_id:
        raise _problem(
            503,
            "google_unavailable",
            "Sign-in with Google is not available right now. Please use your email instead.",
        )
    # One answer for every kind of bad token, so the reply teaches an attacker nothing.
    refused = _problem(
        401,
        "invalid_google_token",
        "We could not check your Google sign-in. Please try again, or use your email instead.",
    )
    try:
        claims = verify(data.credential)
    except GoogleTokenError:
        raise refused from None
    email = _google_email(claims, client_id, now)
    if email is None:
        raise refused

    _lock_email(db, email)  # same lock as email codes: two sign-ins cannot create two users
    user = _find_or_create_user(db, email, data.language)
    out = _open_session(db, user, now)
    db.commit()
    return out


@router.get("/me", response_model=MeOut)
def read_me(user: CurrentUser, db: DbSession) -> MeOut:
    """Who is signed in, and which household (if any) is theirs: where the app goes next."""
    household_id = db.scalar(select(Household.id).where(Household.user_id == user.id))
    return MeOut(email=user.email, language=user.language, household_id=household_id)


@router.post("/auth/sign-out", status_code=204)
def sign_out(session: CurrentSession, db: DbSession) -> Response:
    db.execute(delete(UserSession).where(UserSession.id == session.id))
    db.commit()
    return Response(status_code=204)


@router.delete("/me", status_code=204)
def delete_me(user: CurrentUser, db: DbSession) -> Response:
    """Delete my data: the user, their email, and everything that belongs to them.

    The database removes the household, members, documents, results, alerts and sessions with the
    user (ON DELETE CASCADE). Pending sign-in codes are keyed by email, not user, so they go too.
    """
    db.execute(delete(LoginCode).where(LoginCode.email == user.email))
    db.execute(delete(User).where(User.id == user.id))
    db.commit()
    return Response(status_code=204)
