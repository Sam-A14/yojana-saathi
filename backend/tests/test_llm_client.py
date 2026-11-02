import json

import httpx
import pytest

from app.config import Settings
from app.llm import FakeLLM, GeminiClient, LLMError, get_llm_client


def settings(**values: object) -> Settings:
    # _env_file=None: ignore any developer .env, so the test only sees what it passes in.
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


def test_fake_returns_its_answer_and_records_the_call() -> None:
    fake = FakeLLM(response='{"ok": true}')
    out = fake.complete_json(system="s", prompt="p", temperature=0.1)
    assert out == '{"ok": true}'
    assert fake.calls == [{"system": "s", "prompt": "p", "temperature": 0.1}]


def test_provider_fake_gives_the_fake() -> None:
    assert isinstance(get_llm_client(settings(llm_provider="fake")), FakeLLM)


def test_unknown_provider_is_an_error() -> None:
    with pytest.raises(LLMError, match="Unknown LLM_PROVIDER"):
        get_llm_client(settings(llm_provider="skynet"))


def test_tests_can_never_build_the_real_client() -> None:
    # PYTEST_CURRENT_TEST is set by pytest itself while this test runs.
    with pytest.raises(LLMError, match="fake"):
        get_llm_client(settings(llm_provider="gemini", llm_api_key="key"))


def test_gemini_needs_a_key_and_then_builds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST")  # pretend we are the real workflow
    with pytest.raises(LLMError, match="LLM_API_KEY"):
        get_llm_client(settings(llm_provider="gemini"))
    client = get_llm_client(settings(llm_provider="gemini", llm_api_key="k", llm_model="m"))
    assert isinstance(client, GeminiClient)
    assert client.model == "m"


def gemini_with(handler: httpx.MockTransport) -> GeminiClient:
    return GeminiClient("secret-key", "gemini-test", http=httpx.Client(transport=handler))


def test_gemini_request_and_reply() -> None:
    seen: dict[str, object] = {}

    def handle(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key_header"] = request.headers.get("x-goog-api-key")
        seen["body"] = json.loads(request.content)
        reply = {"candidates": [{"content": {"parts": [{"text": '{"a":'}, {"text": " 1}"}]}}]}
        return httpx.Response(200, json=reply)

    out = gemini_with(httpx.MockTransport(handle)).complete_json(
        system="be exact", prompt="extract", temperature=0.1
    )

    assert out == '{"a": 1}'
    assert str(seen["url"]).endswith("/gemini-test:generateContent")
    assert "secret-key" not in str(seen["url"])  # the key travels in a header only
    assert seen["key_header"] == "secret-key"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["generationConfig"] == {"temperature": 0.1, "responseMimeType": "application/json"}
    assert body["systemInstruction"]["parts"][0]["text"] == "be exact"
    assert body["contents"][0]["parts"][0]["text"] == "extract"


def test_gemini_http_error_is_an_llm_error_without_the_key() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(429, text="quota"))
    with pytest.raises(LLMError, match="429") as caught:
        gemini_with(transport).complete_json(system="s", prompt="p", temperature=0)
    assert "secret-key" not in str(caught.value)


def test_gemini_answer_without_candidates_is_an_llm_error() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"candidates": []}))
    with pytest.raises(LLMError, match="no usable answer"):
        gemini_with(transport).complete_json(system="s", prompt="p", temperature=0)


def test_gemini_network_failure_is_an_llm_error() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(LLMError, match="ConnectError"):
        gemini_with(httpx.MockTransport(boom)).complete_json(system="s", prompt="p", temperature=0)
