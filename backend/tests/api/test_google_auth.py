"""Sign in with Google: our checks on the token, and one real signature check.

Most tests use a fake verifier that returns chosen claims, so they exercise OUR rules (audience,
issuer, expiry, verified email, find-or-create). The last section runs the real google-auth
verification against a key made inside the test, so a bad signature is proven to fail too.
"""

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from google.auth import crypt, jwt
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_now
from app.api.google import GoogleTokenError, get_google_verifier, verify_google_signature
from app.config import get_settings
from app.db.models import LoginCode, User, UserSession
from app.email import FakeEmailClient
from app.main import app
from tests.api.test_auth import ask, code_in, sign_in, verify

CLIENT_ID = "123-abc.apps.googleusercontent.com"
NOW = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
EMAIL = "asha@example.com"


def good_claims(**changes: Any) -> dict[str, Any]:
    """What a genuine token for our app holds, including the personal details we must NOT keep."""
    claims: dict[str, Any] = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "exp": int((NOW + timedelta(minutes=50)).timestamp()),
        "iat": int((NOW - timedelta(minutes=10)).timestamp()),
        "sub": "112233445566778899",
        "email": EMAIL,
        "email_verified": True,
        "name": "Asha Verma",
        "picture": "https://example.com/asha.jpg",
        "given_name": "Asha",
    }
    claims.update(changes)
    return claims


class FakeGoogle:
    """Stands in for the signature check: returns the claims, or says the token is bad."""

    def __init__(self) -> None:
        self.claims: dict[str, Any] = good_claims()
        self.reject = False
        self.calls: list[str] = []

    def __call__(self, credential: str) -> dict[str, Any]:
        self.calls.append(credential)
        if self.reject:
            raise GoogleTokenError
        return dict(self.claims)


@pytest.fixture
def google(monkeypatch: pytest.MonkeyPatch) -> FakeGoogle:
    fake = FakeGoogle()
    monkeypatch.setenv("GOOGLE_CLIENT_ID", CLIENT_ID)
    get_settings.cache_clear()
    app.dependency_overrides[get_google_verifier] = lambda: fake
    app.dependency_overrides[get_now] = lambda: NOW
    return fake


def sign_in_google(client: TestClient, **extra: str):  # noqa: ANN201
    return client.post("/auth/google", json={"credential": "a-google-id-token", **extra})


def bearer(response: Any) -> dict[str, str]:
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# --- the happy path ------------------------------------------------------------------------


def test_a_valid_token_opens_a_session(client: TestClient, google: FakeGoogle) -> None:
    response = sign_in_google(client)

    assert response.status_code == 200
    body = response.json()
    assert len(body["access_token"]) >= 40
    assert datetime.fromisoformat(body["expires_at"]) == NOW + timedelta(days=30)
    me = client.get("/me", headers=bearer(response))
    assert me.json() == {"email": EMAIL, "language": "en", "household_id": None}
    assert google.calls == ["a-google-id-token"]


@pytest.mark.parametrize("issuer", ["accounts.google.com", "https://accounts.google.com"])
def test_both_spellings_of_googles_issuer_are_accepted(
    client: TestClient, google: FakeGoogle, issuer: str
) -> None:
    google.claims = good_claims(iss=issuer)

    assert sign_in_google(client).status_code == 200


def test_the_email_is_lowercased_so_it_matches_email_code_users(
    client: TestClient, db: Session, google: FakeGoogle
) -> None:
    google.claims = good_claims(email="Asha@Example.COM")

    sign_in_google(client)

    assert db.scalar(select(User.email)) == EMAIL


def test_a_new_hindi_user_gets_the_language_asked_for(
    client: TestClient, db: Session, google: FakeGoogle
) -> None:
    sign_in_google(client, language="hi")

    assert db.scalar(select(User.language)) == "hi"


def test_signing_in_twice_is_one_user_with_two_sessions(
    client: TestClient, db: Session, google: FakeGoogle
) -> None:
    sign_in_google(client)
    sign_in_google(client)

    assert db.scalar(select(func.count()).select_from(User)) == 1
    assert db.scalar(select(func.count()).select_from(UserSession)) == 2


# --- the token is refused ------------------------------------------------------------------


def refused(client: TestClient, db: Session) -> None:
    response = sign_in_google(client)
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_google_token"
    # A refused token leaves nothing behind: no user, no session.
    assert db.scalar(select(func.count()).select_from(User)) == 0
    assert db.scalar(select(func.count()).select_from(UserSession)) == 0


def test_a_token_made_for_another_app_is_refused(
    client: TestClient, db: Session, google: FakeGoogle
) -> None:
    google.claims = good_claims(aud="999-someone-else.apps.googleusercontent.com")

    refused(client, db)


def test_an_unverified_email_is_refused(
    client: TestClient, db: Session, google: FakeGoogle
) -> None:
    google.claims = good_claims(email_verified=False)

    refused(client, db)


@pytest.mark.parametrize("flag", ["true", 1, None])
def test_email_verified_must_be_a_real_true(
    client: TestClient, db: Session, google: FakeGoogle, flag: object
) -> None:
    google.claims = good_claims(email_verified=flag)

    refused(client, db)


def test_a_missing_email_verified_is_refused(
    client: TestClient, db: Session, google: FakeGoogle
) -> None:
    del google.claims["email_verified"]

    refused(client, db)


def test_an_expired_token_is_refused(client: TestClient, db: Session, google: FakeGoogle) -> None:
    google.claims = good_claims(exp=int((NOW - timedelta(seconds=1)).timestamp()))

    refused(client, db)


def test_a_token_expiring_exactly_now_is_refused(
    client: TestClient, db: Session, google: FakeGoogle
) -> None:
    google.claims = good_claims(exp=int(NOW.timestamp()))

    refused(client, db)


def test_a_token_from_another_issuer_is_refused(
    client: TestClient, db: Session, google: FakeGoogle
) -> None:
    google.claims = good_claims(iss="https://accounts.evil.example.com")

    refused(client, db)


@pytest.mark.parametrize("email", [None, "", "not-an-email", 42])
def test_a_token_without_a_usable_email_is_refused(
    client: TestClient, db: Session, google: FakeGoogle, email: object
) -> None:
    google.claims = good_claims(email=email)

    refused(client, db)


def test_a_token_whose_signature_check_fails_is_refused(
    client: TestClient, db: Session, google: FakeGoogle
) -> None:
    google.reject = True

    refused(client, db)


def test_every_refusal_gives_the_same_answer(client: TestClient, google: FakeGoogle) -> None:
    answers = []
    for claims in (
        good_claims(aud="other"),
        good_claims(email_verified=False),
        good_claims(exp=1),
        good_claims(iss="x"),
    ):
        google.claims = claims
        answers.append(sign_in_google(client).json())

    assert all(answer == answers[0] for answer in answers)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"credential": ""},
        {"credential": "   "},
        {"credential": "x" * 5000},
        {"credential": "x", "language": "fr"},
        {"credential": "x", "email": "someone@example.com"},  # the email comes from Google only
    ],
)
def test_bad_request_input_is_422(client: TestClient, google: FakeGoogle, body: dict) -> None:
    assert client.post("/auth/google", json=body).status_code == 422
    assert google.calls == []


# --- switched off --------------------------------------------------------------------------


@pytest.mark.parametrize("value", [None, ""])
def test_without_a_client_id_google_sign_in_is_unavailable(
    client: TestClient,
    google: FakeGoogle,
    monkeypatch: pytest.MonkeyPatch,
    value: str | None,
) -> None:
    if value is None:
        monkeypatch.delenv("GOOGLE_CLIENT_ID")
    else:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", value)
    get_settings.cache_clear()

    response = sign_in_google(client)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "google_unavailable"
    assert google.calls == []  # no token is even looked at


# --- same account as email codes -----------------------------------------------------------


def test_an_email_code_user_signing_in_with_google_reaches_the_same_household(
    client: TestClient, db: Session, google: FakeGoogle, mailbox: FakeEmailClient
) -> None:
    by_email = sign_in(client, mailbox, EMAIL)
    household = client.post("/households", json={"state": "UP"}, headers=by_email).json()

    by_google = bearer(sign_in_google(client))

    me = client.get("/me", headers=by_google).json()
    assert me["household_id"] == household["id"]
    assert client.get(f"/households/{household['id']}", headers=by_google).status_code == 200
    assert db.scalar(select(func.count()).select_from(User)) == 1


def test_a_google_user_can_later_use_an_email_code_for_the_same_household(
    client: TestClient, db: Session, google: FakeGoogle, mailbox: FakeEmailClient
) -> None:
    by_google = bearer(sign_in_google(client))
    household = client.post("/households", json={"state": "UP"}, headers=by_google).json()

    assert ask(client, EMAIL).status_code == 202
    opened = verify(client, code_in(mailbox), EMAIL)

    me = client.get("/me", headers=bearer(opened)).json()
    assert me["household_id"] == household["id"]


def test_google_sessions_work_like_any_other_and_can_sign_out(
    client: TestClient, google: FakeGoogle
) -> None:
    headers = bearer(sign_in_google(client))

    assert client.post("/auth/sign-out", headers=headers).status_code == 204
    assert client.get("/me", headers=headers).status_code == 401


def test_delete_me_works_for_a_google_user(
    client: TestClient, db: Session, google: FakeGoogle
) -> None:
    headers = bearer(sign_in_google(client))

    assert client.delete("/me", headers=headers).status_code == 204
    assert db.scalar(select(func.count()).select_from(User)) == 0


# --- what we keep, and what we leave alone -------------------------------------------------


def test_only_the_email_is_kept_never_the_name_photo_id_or_token(
    client: TestClient, db: Session, google: FakeGoogle
) -> None:
    sign_in_google(client)

    stored = " ".join(
        str(value)
        for model in (User, UserSession)
        for row in db.scalars(select(model))
        for value in vars(row).values()
    )
    for personal in ("Asha Verma", "Asha", "asha.jpg", "112233445566778899", "a-google-id-token"):
        assert personal not in stored
    assert EMAIL in stored


def test_google_sign_in_does_not_touch_the_email_code_limits(
    client: TestClient, db: Session, google: FakeGoogle, mailbox: FakeEmailClient
) -> None:
    for _ in range(5):
        sign_in_google(client)

    assert mailbox.sent == []
    assert db.scalar(select(func.count()).select_from(LoginCode)) == 0
    for _ in range(3):  # the full 3 an hour are still there
        assert ask(client).status_code == 202
    assert ask(client).status_code == 429  # and the per-email limit still works as before


def test_the_token_is_never_logged(
    client: TestClient, google: FakeGoogle, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)

    sign_in_google(client)
    google.reject = True
    sign_in_google(client)

    assert "a-google-id-token" not in caplog.text


# --- the real signature check (google-auth, with a key made here) --------------------------


class _Response:
    status = 200

    def __init__(self, body: dict[str, str]) -> None:
        self.data = json.dumps(body).encode()


def _key() -> tuple[crypt.RSASigner, str]:
    """A fresh signing key and its public half, in the PEM form google-auth reads."""
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return crypt.RSASigner.from_string(private_pem, key_id="key-1"), public_pem.decode()


@pytest.fixture(scope="module")
def signing() -> tuple[crypt.RSASigner, crypt.RSASigner, str]:
    """(Google's key, an attacker's key under the same key id, Google's published public key)."""
    google_signer, google_public = _key()
    attacker_signer, _ = _key()
    return google_signer, attacker_signer, google_public


def _fake_certs(public_pem: str) -> Callable[..., _Response]:
    """Serves 'Google's' public keys from memory instead of calling Google."""

    def serve(url: str, method: str = "GET", **_: Any) -> _Response:
        assert url.startswith("https://www.googleapis.com/oauth2/")  # the real keys' address
        return _Response({"key-1": public_pem})

    return serve


def _real_claims(**changes: Any) -> dict[str, Any]:
    now = datetime.now(UTC)
    timing = {
        "exp": int((now + timedelta(minutes=30)).timestamp()),
        "iat": int(now.timestamp()),
    }
    return good_claims(**{**timing, **changes})


def _check(token: bytes, public_pem: str) -> dict[str, Any]:
    request: Any = _fake_certs(public_pem)
    return verify_google_signature(token.decode(), request)


def test_the_real_check_accepts_a_token_signed_by_googles_key(signing) -> None:  # noqa: ANN001
    google_signer, _, public_pem = signing
    token = jwt.encode(google_signer, _real_claims())

    claims = _check(token, public_pem)

    assert claims["email"] == EMAIL
    assert claims["aud"] == CLIENT_ID


def test_the_real_check_refuses_a_token_signed_by_another_key(signing) -> None:  # noqa: ANN001
    _, attacker_signer, public_pem = signing
    token = jwt.encode(attacker_signer, _real_claims())

    with pytest.raises(GoogleTokenError):
        _check(token, public_pem)


def test_the_real_check_refuses_a_token_whose_claims_were_edited(signing) -> None:  # noqa: ANN001
    google_signer, _, public_pem = signing
    header, _, signature = jwt.encode(google_signer, _real_claims()).decode().split(".")
    forged_claims = jwt.encode(google_signer, _real_claims(email="victim@example.com"))
    forged_payload = forged_claims.decode().split(".")[1]
    token = ".".join([header, forged_payload, signature]).encode()

    with pytest.raises(GoogleTokenError):
        _check(token, public_pem)


def test_the_real_check_refuses_an_expired_token(signing) -> None:  # noqa: ANN001
    google_signer, _, public_pem = signing
    long_ago = int((datetime.now(UTC) - timedelta(hours=2)).timestamp())
    token = jwt.encode(google_signer, _real_claims(exp=long_ago, iat=long_ago - 3600))

    with pytest.raises(GoogleTokenError):
        _check(token, public_pem)


def test_the_real_check_refuses_garbage(signing) -> None:  # noqa: ANN001
    _, _, public_pem = signing

    with pytest.raises(GoogleTokenError):
        _check(b"not.a.jwt", public_pem)
    with pytest.raises(GoogleTokenError):
        _check(b"", public_pem)


def test_the_default_verifier_is_the_real_one() -> None:
    assert get_google_verifier() is verify_google_signature
