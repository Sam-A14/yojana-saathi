"""Gemini over plain HTTPS (httpx, already a dependency), so no extra SDK to learn or pin."""

import time
from collections.abc import Callable

import httpx

from app.llm.base import LLMClient, LLMError

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
# Reading a long scheme page and writing JSON can take a while.
TIMEOUT_SECONDS = 120.0
# 429 = quota / rate limit, 503 = model overloaded. Both usually clear within a minute, so waiting
# and asking again works. 400 / 403 / 404 mean our request or key is wrong: retrying cannot help.
RETRY_STATUSES = frozenset({429, 503})
# Seconds to wait before retry 1, 2 and 3. Growing waits give a busy service time to recover.
RETRY_WAITS = (5.0, 15.0, 45.0)
# Timeouts and dropped connections are as temporary as a 429. Other httpx errors (bad URL, too many
# redirects) are bugs on our side and fail at once.
RETRY_ERRORS = (httpx.TimeoutException, httpx.NetworkError)


class GeminiClient(LLMClient):
    def __init__(
        self,
        api_key: str,
        model: str,
        http: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.model = model
        self._api_key = api_key
        # Tests pass a fake-transport client and a recording sleep; nothing else ever needs to.
        self._http = http or httpx.Client(timeout=TIMEOUT_SECONDS)
        self._sleep = sleep

    def complete_json(self, *, system: str, prompt: str, temperature: float) -> str:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                # Asks Gemini for JSON text. Our validator, not Gemini, decides if it is correct.
                "responseMimeType": "application/json",
            },
        }
        for wait in (*RETRY_WAITS, None):
            failure = self._try_once(body)
            if isinstance(failure, httpx.Response):
                if failure.status_code == 200:
                    return _text_of(failure)
                if failure.status_code not in RETRY_STATUSES:
                    raise LLMError(
                        f"Gemini returned HTTP {failure.status_code}: {failure.text[:300]}"
                    )
                reason = f"HTTP {failure.status_code}: {failure.text[:300]}"
            else:
                reason = f"could not reach Gemini: {type(failure).__name__}"
            if wait is None:
                raise LLMError(f"Gemini failed after {len(RETRY_WAITS)} retries ({reason})")
            self._sleep(wait)
        raise AssertionError("unreachable: the last loop pass always returns or raises")

    def _try_once(self, body: dict[str, object]) -> httpx.Response | Exception:
        """One request. Returns the response, or the temporary error that is worth retrying."""
        try:
            # The key goes in a header, not the URL, so it cannot end up in an error message or log.
            return self._http.post(
                f"{BASE_URL}/{self.model}:generateContent",
                json=body,
                headers={"x-goog-api-key": self._api_key},
            )
        except RETRY_ERRORS as error:
            return error
        except httpx.HTTPError as error:
            raise LLMError(f"Could not reach Gemini: {type(error).__name__}") from error


def _text_of(response: httpx.Response) -> str:
    try:
        parts = response.json()["candidates"][0]["content"]["parts"]
        return "".join(part["text"] for part in parts)
    except (ValueError, KeyError, IndexError, TypeError) as error:
        # Typically a safety block or an empty answer: there is no candidate to read.
        raise LLMError(f"Gemini sent no usable answer: {response.text[:300]}") from error
