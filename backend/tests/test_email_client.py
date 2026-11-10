"""The email client: what is sent to Resend, and that failures never carry the message."""

import httpx
import pytest

from app.config import Settings
from app.email import (
    EmailError,
    FakeEmailClient,
    Message,
    ResendEmailClient,
    build_email_client,
)

MESSAGE = Message(to="asha@example.com", subject="Hello", text="Your sign-in code is 482913.")


def resend_with(handler) -> ResendEmailClient:  # noqa: ANN001
    return ResendEmailClient(
        "re_test_key", "Yojana Saathi <hello@example.org>", httpx.MockTransport(handler)
    )


def test_resend_gets_the_message_the_key_and_the_configured_sender() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"id": "abc"})

    resend_with(handler).send(MESSAGE)

    (request,) = seen
    assert str(request.url) == "https://api.resend.com/emails"
    assert request.headers["authorization"] == "Bearer re_test_key"
    body = httpx.Response(200, content=request.content).json()
    assert body == {
        "from": "Yojana Saathi <hello@example.org>",
        "to": ["asha@example.com"],
        "subject": "Hello",
        "text": "Your sign-in code is 482913.",
    }


def test_a_provider_error_carries_only_the_status_never_the_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"message": "bad request mentioning 482913"})

    with pytest.raises(EmailError) as error:
        resend_with(handler).send(MESSAGE)

    assert "422" in str(error.value)
    assert "482913" not in str(error.value)


def test_a_network_failure_carries_no_request_details() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("could not connect to api.resend.com with 482913")

    with pytest.raises(EmailError) as error:
        resend_with(handler).send(MESSAGE)

    assert "482913" not in str(error.value)
    assert error.value.__cause__ is None


def test_the_fake_keeps_messages_and_can_be_told_to_fail() -> None:
    fake = FakeEmailClient()
    fake.send(MESSAGE)
    assert fake.sent == [MESSAGE]

    fake.fail = True
    with pytest.raises(EmailError):
        fake.send(MESSAGE)


def test_the_provider_and_sender_are_settings() -> None:
    assert isinstance(build_email_client(Settings(email_provider="fake")), FakeEmailClient)

    built = build_email_client(
        Settings(email_provider="resend", resend_api_key="re_x", email_from="Me <me@example.org>")
    )
    assert isinstance(built, ResendEmailClient)


def test_the_default_sender_is_resends_onboarding_address() -> None:
    assert Settings().email_from == "Yojana Saathi <onboarding@resend.dev>"


def test_resend_without_a_key_and_unknown_providers_fail_loudly() -> None:
    with pytest.raises(RuntimeError, match="RESEND_API_KEY"):
        build_email_client(Settings(email_provider="resend", resend_api_key=None))
    with pytest.raises(RuntimeError, match="EMAIL_PROVIDER"):
        build_email_client(Settings(email_provider="smoke-signals"))


@pytest.mark.parametrize("secret", [None, "", "too-short"])
def test_the_auth_secret_must_be_long(secret: str | None) -> None:
    with pytest.raises(RuntimeError, match="AUTH_SECRET"):
        _ = Settings(auth_secret=secret).auth_secret_checked
