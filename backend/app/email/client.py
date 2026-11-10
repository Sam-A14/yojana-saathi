"""Sending email, behind one small interface so the provider can be switched (like app/llm/).

Messages can contain a sign-in code, so nothing in this file logs a message, and an error carries
only a status number, never what we sent or what the provider answered.
"""

from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.config import Settings

RESEND_URL = "https://api.resend.com/emails"


@dataclass(frozen=True)
class Message:
    to: str
    subject: str
    text: str


class EmailError(Exception):
    """The email could not be sent. The message never includes the email's content."""


class EmailClient(Protocol):
    def send(self, message: Message) -> None:
        """Send or raise EmailError."""
        ...


@dataclass
class FakeEmailClient:
    """Keeps messages in memory, for tests. Set `fail` to make the next sends fail."""

    sent: list[Message] = field(default_factory=list)
    fail: bool = False

    def send(self, message: Message) -> None:
        if self.fail:
            raise EmailError("Fake email failure.")
        self.sent.append(message)


class ResendEmailClient:
    def __init__(
        self,
        api_key: str,
        from_address: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._from = from_address
        self._transport = transport

    def send(self, message: Message) -> None:
        payload = {
            "from": self._from,
            "to": [message.to],
            "subject": message.subject,
            "text": message.text,
        }
        try:
            with httpx.Client(timeout=10, transport=self._transport) as http:
                response = http.post(
                    RESEND_URL, json=payload, headers={"Authorization": f"Bearer {self._api_key}"}
                )
        except httpx.HTTPError as error:
            # type(error).__name__ only: the exception text can include the request.
            raise EmailError(f"Could not reach Resend ({type(error).__name__}).") from None
        if response.status_code >= 300:
            raise EmailError(f"Resend answered with status {response.status_code}.")


def build_email_client(settings: Settings) -> EmailClient:
    if settings.email_provider == "fake":
        return FakeEmailClient()
    if settings.email_provider == "resend":
        if not settings.resend_api_key:
            raise RuntimeError("RESEND_API_KEY is not set. See backend/.env.example.")
        return ResendEmailClient(settings.resend_api_key, settings.email_from)
    raise RuntimeError(
        f"Unknown EMAIL_PROVIDER '{settings.email_provider}'. Use 'resend' or 'fake'."
    )
