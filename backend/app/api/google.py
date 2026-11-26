"""Checking a Google ID token: the one place that talks to google-auth.

Split in two on purpose:
  * `verify_google_signature` (here) proves the token was signed by Google's current public keys
    and returns the claims. That is the part we must not write ourselves.
  * `app/api/auth.py` then checks what the token is *for*: audience, issuer, expiry and a verified
    email. Those are our rules, so they live in our code where our tests can break them.

The token is never stored or logged; only the email in it is used.
"""

from typing import Annotated, Any, Protocol

from fastapi import Depends
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token


class GoogleTokenError(Exception):
    """The token is not a genuine, currently valid Google ID token. Carries no token text."""


class GoogleVerifier(Protocol):
    def __call__(self, credential: str) -> dict[str, Any]: ...


def verify_google_signature(
    credential: str, request: google_requests.Request | None = None
) -> dict[str, Any]:
    """Verify the signature (and Google's own time and issuer checks) and return the claims.

    The audience is left to our own code, which knows the client ID. `request` is a parameter only
    so a test can serve its own public keys instead of calling Google.
    """
    try:
        claims = id_token.verify_oauth2_token(
            credential, request or google_requests.Request(), audience=None
        )
    except (ValueError, TypeError):
        # Bad signature, expired, wrong issuer, malformed, or Google's keys unreachable.
        raise GoogleTokenError from None
    return dict(claims)


def get_google_verifier() -> GoogleVerifier:
    """A dependency so tests can swap in a fake that returns chosen claims."""
    return verify_google_signature


Verifier = Annotated[GoogleVerifier, Depends(get_google_verifier)]
