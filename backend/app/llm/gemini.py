"""Gemini over plain HTTPS (httpx, already a dependency), so no extra SDK to learn or pin."""

import httpx

from app.llm.base import LLMClient, LLMError

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
# Reading a long scheme page and writing JSON can take a while.
TIMEOUT_SECONDS = 120.0


class GeminiClient(LLMClient):
    def __init__(self, api_key: str, model: str, http: httpx.Client | None = None) -> None:
        self.model = model
        self._api_key = api_key
        # Tests pass a client with a fake transport; nothing else ever needs to.
        self._http = http or httpx.Client(timeout=TIMEOUT_SECONDS)

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
        try:
            # The key goes in a header, not the URL, so it cannot end up in an error message or log.
            response = self._http.post(
                f"{BASE_URL}/{self.model}:generateContent",
                json=body,
                headers={"x-goog-api-key": self._api_key},
            )
        except httpx.HTTPError as error:
            raise LLMError(f"Could not reach Gemini: {type(error).__name__}") from error
        if response.status_code != 200:
            raise LLMError(f"Gemini returned HTTP {response.status_code}: {response.text[:300]}")
        return _text_of(response)


def _text_of(response: httpx.Response) -> str:
    try:
        parts = response.json()["candidates"][0]["content"]["parts"]
        return "".join(part["text"] for part in parts)
    except (ValueError, KeyError, IndexError, TypeError) as error:
        # Typically a safety block or an empty answer: there is no candidate to read.
        raise LLMError(f"Gemini sent no usable answer: {response.text[:300]}") from error
