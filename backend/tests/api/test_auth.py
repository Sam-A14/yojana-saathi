"""Sign in with an emailed code: the flow, and every limit around it."""

import logging
import re
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_now
from app.api.security import hash_code
from app.config import get_settings
from app.db.models import Household, LoginCode, Member, User, UserSession
from app.email import FakeEmailClient
from app.main import app

EMAIL = "asha@example.com"


class Clock:
    """Time that only moves when a test says so (codes expire, limits reset)."""

    def __init__(self) -> None:
        self.now = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)

    def advance(self, **delta: float) -> None:
        self.now += timedelta(**delta)


@pytest.fixture
def clock() -> Clock:
    fixed = Clock()
    app.dependency_overrides[get_now] = lambda: fixed.now
    return fixed


def code_in(mailbox: FakeEmailClient) -> str:
    match = re.search(r"\b(\d{6})\b", mailbox.sent[-1].text)
    assert match, "the email has no 6-digit code"
    return match.group(1)


def ask(client: TestClient, email: str = EMAIL, **extra: str):  # noqa: ANN201
    return client.post("/auth/request-code", json={"email": email, **extra})


def verify(client: TestClient, code: str, email: str = EMAIL):  # noqa: ANN201
    return client.post("/auth/verify", json={"email": email, "code": code})


def sign_in(client: TestClient, mailbox: FakeEmailClient, email: str = EMAIL) -> dict[str, str]:
    assert ask(client, email).status_code == 202
    response = verify(client, code_in(mailbox), email)
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# --- the happy path ------------------------------------------------------------------------


def test_a_code_is_emailed_and_opens_a_session(
    client: TestClient, mailbox: FakeEmailClient, clock: Clock
) -> None:
    response = ask(client)

    assert response.status_code == 202
    assert response.json() == {"status": "sent", "expires_in_minutes": 10}
    assert [m.to for m in mailbox.sent] == [EMAIL]
    code = code_in(mailbox)
    assert len(code) == 6

    opened = verify(client, code)

    assert opened.status_code == 200
    body = opened.json()
    assert len(body["access_token"]) >= 40
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    me = client.get("/me", headers=headers)
    assert me.json() == {"email": EMAIL, "language": "en", "household_id": None}


def test_the_same_person_signing_in_again_is_the_same_user(
    client: TestClient, db: Session, mailbox: FakeEmailClient, clock: Clock
) -> None:
    sign_in(client, mailbox)
    clock.advance(minutes=1)
    sign_in(client, mailbox)

    assert db.scalar(select(func.count()).select_from(User)) == 1
    assert db.scalar(select(func.count()).select_from(UserSession)) == 2


def test_the_email_is_trimmed_and_lowercased(client: TestClient, mailbox: FakeEmailClient) -> None:
    ask(client, "  Asha@Example.COM ")

    assert mailbox.sent[0].to == "asha@example.com"
    assert verify(client, code_in(mailbox), "ASHA@example.com").status_code == 200


def test_the_answer_is_the_same_for_a_known_and_an_unknown_address(
    client: TestClient, mailbox: FakeEmailClient, clock: Clock
) -> None:
    sign_in(client, mailbox)  # asha@ now has an account
    known = ask(client)
    unknown = ask(client, "nobody@example.com")

    assert (known.status_code, known.json()) == (unknown.status_code, unknown.json())


def test_a_hindi_request_gets_a_hindi_email_and_a_hindi_user(
    client: TestClient, db: Session, mailbox: FakeEmailClient
) -> None:
    ask(client, language="hi")

    assert "साइन-इन" in mailbox.sent[0].text
    verify(client, code_in(mailbox))
    assert db.scalar(select(User.language).where(User.email == EMAIL)) == "hi"


# --- storage and logging -------------------------------------------------------------------


def test_the_code_is_stored_only_as_a_keyed_hash(
    client: TestClient, db: Session, mailbox: FakeEmailClient, clock: Clock
) -> None:
    ask(client)
    code = code_in(mailbox)

    row = db.scalar(select(LoginCode))
    assert row is not None
    assert code not in row.code_hash
    assert row.code_hash == hash_code(get_settings().auth_secret_checked, EMAIL, code)
    # Without the server secret the stored hash cannot be recomputed from the code.
    assert row.code_hash != hash_code("some-other-secret-some-other-secret-1", EMAIL, code)


def test_the_session_token_is_stored_only_as_a_hash(
    client: TestClient, db: Session, mailbox: FakeEmailClient
) -> None:
    headers = sign_in(client, mailbox)
    token = headers["Authorization"].removeprefix("Bearer ")

    stored = db.scalar(select(UserSession.token_hash))
    assert stored is not None
    assert token not in stored


def test_codes_are_never_logged(
    client: TestClient, mailbox: FakeEmailClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)

    ask(client)
    code = code_in(mailbox)
    verify(client, "000000" if code != "000000" else "111111")  # a wrong guess
    verify(client, code)  # the right one
    # A failed send is logged nowhere with its content either.
    mailbox.fail = True
    ask(client, "other@example.com")

    assert code not in caplog.text
    assert get_settings().auth_secret_checked not in caplog.text


# --- limits --------------------------------------------------------------------------------


def test_a_wrong_code_says_how_many_tries_are_left(
    client: TestClient, mailbox: FakeEmailClient, clock: Clock
) -> None:
    ask(client)
    wrong = "000000" if code_in(mailbox) != "000000" else "111111"

    response = verify(client, wrong)

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_code"
    assert response.json()["detail"]["attempts_left"] == 4


def test_five_wrong_guesses_kill_the_code_even_for_the_right_answer(
    client: TestClient, mailbox: FakeEmailClient, clock: Clock
) -> None:
    ask(client)
    right = code_in(mailbox)
    wrong = "000000" if right != "000000" else "111111"
    for _ in range(5):
        assert verify(client, wrong).status_code == 401

    response = verify(client, right)

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "too_many_attempts"


def test_a_code_works_for_ten_minutes_and_not_longer(
    client: TestClient, mailbox: FakeEmailClient, clock: Clock
) -> None:
    ask(client)
    code = code_in(mailbox)
    clock.advance(minutes=9, seconds=59)
    assert verify(client, code).status_code == 200

    ask(client)
    code = code_in(mailbox)
    clock.advance(minutes=10, seconds=1)
    response = verify(client, code)

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "code_expired"


def test_a_code_can_be_used_only_once(
    client: TestClient, mailbox: FakeEmailClient, clock: Clock
) -> None:
    ask(client)
    code = code_in(mailbox)

    assert verify(client, code).status_code == 200
    assert verify(client, code).status_code == 401


def test_asking_for_a_new_code_cancels_the_old_one(
    client: TestClient, mailbox: FakeEmailClient, clock: Clock
) -> None:
    ask(client)
    old = code_in(mailbox)
    ask(client)
    new = code_in(mailbox)
    if old == new:  # one in a million: ask again so the test cannot fail by chance
        pytest.skip("two equal random codes")

    assert verify(client, old).status_code == 401
    assert verify(client, new).status_code == 200


def test_verify_without_asking_first_is_the_same_plain_error(client: TestClient) -> None:
    response = verify(client, "123456", "never-asked@example.com")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_code"


def test_three_codes_per_email_per_hour(
    client: TestClient, mailbox: FakeEmailClient, clock: Clock
) -> None:
    for _ in range(3):
        assert ask(client).status_code == 202
        clock.advance(minutes=5)

    blocked = ask(client)

    assert blocked.status_code == 429
    assert blocked.json()["detail"]["code"] == "too_many_codes"
    assert len(mailbox.sent) == 3  # the fourth was not sent
    assert ask(client, "someone.else@example.com").status_code == 202  # other emails are fine

    clock.advance(minutes=46)  # the first code is now more than an hour old
    assert ask(client).status_code == 202


def test_a_global_daily_cap_protects_the_email_quota(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, mailbox: FakeEmailClient, clock: Clock
) -> None:
    monkeypatch.setenv("EMAIL_DAILY_LIMIT", "2")
    get_settings.cache_clear()
    assert ask(client, "a@example.com").status_code == 202
    assert ask(client, "b@example.com").status_code == 202

    busy = ask(client, "c@example.com")

    assert busy.status_code == 503
    assert busy.json()["detail"]["code"] == "busy"
    assert "tomorrow" in busy.json()["detail"]["message"]
    assert len(mailbox.sent) == 2

    clock.advance(hours=24)  # a new UTC day
    assert ask(client, "c@example.com").status_code == 202


def test_a_failed_send_uses_up_no_quota(
    client: TestClient, db: Session, mailbox: FakeEmailClient, clock: Clock
) -> None:
    mailbox.fail = True
    for _ in range(4):
        response = ask(client)
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "email_failed"
    assert db.scalar(select(func.count()).select_from(LoginCode)) == 0

    mailbox.fail = False
    assert ask(client).status_code == 202  # not blocked by the failures above


@pytest.mark.parametrize(
    "body",
    [
        {"email": "not-an-email"},
        {"email": "a@b"},
        {"email": ""},
        {"email": "a@example.com", "language": "fr"},
        {"email": "a@example.com", "phone": "9999999999"},
        {"email": "a" * 250 + "@example.com"},
    ],
)
def test_bad_request_code_input_is_422(client: TestClient, mailbox: FakeEmailClient, body) -> None:
    assert client.post("/auth/request-code", json=body).status_code == 422
    assert mailbox.sent == []


@pytest.mark.parametrize("code", ["12345", "1234567", "abcdef", "12 456", ""])
def test_a_code_must_be_exactly_six_digits(client: TestClient, code: str) -> None:
    assert verify(client, code).status_code == 422


# --- sessions ------------------------------------------------------------------------------


def test_a_session_lasts_thirty_days(
    client: TestClient, mailbox: FakeEmailClient, clock: Clock
) -> None:
    headers = sign_in(client, mailbox)

    clock.advance(days=29, hours=23)
    assert client.get("/me", headers=headers).status_code == 200
    clock.advance(hours=2)
    assert client.get("/me", headers=headers).status_code == 401


def test_sign_out_ends_that_session_only(
    client: TestClient, mailbox: FakeEmailClient, clock: Clock
) -> None:
    phone = sign_in(client, mailbox)
    clock.advance(minutes=1)
    laptop = sign_in(client, mailbox)

    assert client.post("/auth/sign-out", headers=phone).status_code == 204

    assert client.get("/me", headers=phone).status_code == 401
    assert client.get("/me", headers=laptop).status_code == 200


def test_me_and_sign_out_need_a_session(client: TestClient) -> None:
    assert client.get("/me").status_code == 401
    assert client.post("/auth/sign-out").status_code == 401
    assert client.delete("/me").status_code == 401


def test_me_shows_the_household_once_there_is_one(
    client: TestClient, mailbox: FakeEmailClient, clock: Clock
) -> None:
    headers = sign_in(client, mailbox)
    created = client.post("/households", json={"state": "UP"}, headers=headers).json()

    assert client.get("/me", headers=headers).json()["household_id"] == created["id"]


# --- delete my data ------------------------------------------------------------------------


def test_delete_me_removes_the_user_their_email_and_everything_under_them(
    client: TestClient,
    db: Session,
    seeded,
    mailbox: FakeEmailClient,
    clock: Clock,
) -> None:
    mine = sign_in(client, mailbox, EMAIL)
    clock.advance(minutes=1)
    other = sign_in(client, mailbox, "other@example.com")
    for headers in (mine, other):
        household = client.post("/households", json={"state": "UP"}, headers=headers).json()
        member = client.post(
            f"/households/{household['id']}/members",
            json={"nickname": "Asha", "relation": "self"},
            headers=headers,
        ).json()
        client.put(
            f"/households/{household['id']}/members/{member['id']}/documents",
            json={"documents": {"bpl_card": True}},
            headers=headers,
        )
    ask(client, EMAIL)  # a pending code for the email must go too

    assert client.delete("/me", headers=mine).status_code == 204

    # The email is gone from every table that could hold it.
    assert db.scalar(select(func.count()).select_from(User).where(User.email == EMAIL)) == 0
    assert (
        db.scalar(select(func.count()).select_from(LoginCode).where(LoginCode.email == EMAIL)) == 0
    )
    # ...and so is everything under that user (database cascade). The other family is untouched.
    assert db.scalar(select(func.count()).select_from(Household)) == 1
    assert db.scalar(select(func.count()).select_from(Member)) == 1
    assert db.scalar(select(func.count()).select_from(UserSession)) == 1
    assert client.get("/me", headers=mine).status_code == 401
    assert client.get("/me", headers=other).status_code == 200
