"""A model that returns canned answers. Used by every test, so CI never calls a real API."""

from app.llm.base import LLMClient


class FakeLLM(LLMClient):
    def __init__(self, response: str = "{}", model: str = "fake-model") -> None:
        self.response = response
        self.model = model
        # Tests read these to check what the extractor actually sent.
        self.calls: list[dict[str, object]] = []

    def complete_json(self, *, system: str, prompt: str, temperature: float) -> str:
        self.calls.append({"system": system, "prompt": prompt, "temperature": temperature})
        return self.response
