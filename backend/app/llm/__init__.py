"""LLM wrapper. Use get_llm_client(); never import a provider class from the pipeline."""

import os

from app.config import Settings, get_settings
from app.llm.base import LLMClient, LLMError
from app.llm.fake import FakeLLM
from app.llm.gemini import GeminiClient

__all__ = ["FakeLLM", "GeminiClient", "LLMClient", "LLMError", "get_llm_client"]


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    settings = settings or get_settings()
    provider = settings.llm_provider.lower()
    if provider == "fake":
        return FakeLLM()
    if provider == "gemini":
        # Second safety net behind the test fixture: pytest sets this variable while a test runs,
        # so a test that forgot to use the fake still cannot spend money or need a key.
        # (We cannot test for the CI variable instead: GitHub sets CI=true in the real
        # extraction workflow too.)
        if os.environ.get("PYTEST_CURRENT_TEST"):
            raise LLMError("Tests must use the fake LLM, not a real provider.")
        if not settings.llm_api_key:
            raise LLMError("LLM_API_KEY is not set. See backend/.env.example.")
        return GeminiClient(settings.llm_api_key, settings.llm_model)
    raise LLMError(f"Unknown LLM_PROVIDER '{settings.llm_provider}'. Use 'gemini' or 'fake'.")
