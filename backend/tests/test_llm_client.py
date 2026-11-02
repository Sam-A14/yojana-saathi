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


def gemini_with(handler: httpx.MockTransport, waits: list[float] | None = None) -> GeminiClient:
    # The recorder replaces time.sleep: tests run instantly and can check the waits.
    recorder = waits if waits is not None else []
    return GeminiClient(
        "secret-key",
        "gemini-test",
        http=httpx.Client(transport=handler),
        sleep=recorder.append,
    )


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
    transport = httpx.MockTransport(lambda request: httpx.Response(403, text="bad key"))
    with pytest.raises(LLMError, match="403") as caught:
        gemini_with(transport).complete_json(system="s", prompt="p", temperature=0)
    assert "secret-key" not in str(caught.value)


def test_gemini_answer_without_candidates_is_an_llm_error() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"candidates": []}))
    with pytest.raises(LLMError, match="no usable answer"):
        gemini_with(transport).complete_json(system="s", prompt="p", temperature=0)


OK_REPLY = {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}


def scripted(*steps: object) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    """A transport that plays the steps in order: a status code answers, an exception is raised."""
    queue = list(steps)
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        step = queue.pop(0)
        if isinstance(step, Exception):
            raise step
        assert isinstance(step, int)
        return (
            httpx.Response(step, json=OK_REPLY) if step == 200 else httpx.Response(step, text="no")
        )

    return httpx.MockTransport(handle), seen


@pytest.mark.parametrize("status", [429, 503])
def test_gemini_retries_temporary_statuses_then_succeeds(status: int) -> None:
    transport, seen = scripted(status, status, 200)
    waits: list[float] = []

    out = gemini_with(transport, waits).complete_json(system="s", prompt="p", temperature=0)

    assert out == "{}"
    assert len(seen) == 3
    assert waits == [5, 15]


def test_gemini_gives_up_after_three_retries_with_a_clear_message() -> None:
    transport, seen = scripted(503, 503, 503, 503)
    waits: list[float] = []

    with pytest.raises(LLMError, match="failed after 3 retries.*HTTP 503") as caught:
        gemini_with(transport, waits).complete_json(system="s", prompt="p", temperature=0)

    assert len(seen) == 4  # the first try plus three retries
    assert waits == [5, 15, 45]
    assert "secret-key" not in str(caught.value)


@pytest.mark.parametrize("status", [400, 403, 404])
def test_gemini_does_not_retry_errors_that_waiting_cannot_fix(status: int) -> None:
    transport, seen = scripted(status)
    waits: list[float] = []

    with pytest.raises(LLMError, match=str(status)):
        gemini_with(transport, waits).complete_json(system="s", prompt="p", temperature=0)

    assert len(seen) == 1
    assert waits == []


@pytest.mark.parametrize(
    "error",
    [httpx.ReadTimeout("slow"), httpx.ConnectTimeout("slow"), httpx.ConnectError("down")],
)
def test_gemini_retries_timeouts_and_connection_errors_then_succeeds(error: Exception) -> None:
    transport, seen = scripted(error, 200)
    waits: list[float] = []

    out = gemini_with(transport, waits).complete_json(system="s", prompt="p", temperature=0)

    assert out == "{}"
    assert len(seen) == 2
    assert waits == [5]


def test_gemini_network_failure_that_never_clears_is_an_llm_error() -> None:
    transport, seen = scripted(*[httpx.ConnectError("down")] * 4)
    waits: list[float] = []

    with pytest.raises(LLMError, match="failed after 3 retries.*ConnectError"):
        gemini_with(transport, waits).complete_json(system="s", prompt="p", temperature=0)

    assert len(seen) == 4
    assert waits == [5, 15, 45]


def test_gemini_other_http_library_errors_fail_at_once() -> None:
    transport, seen = scripted(httpx.TooManyRedirects("loop"))
    waits: list[float] = []

    with pytest.raises(LLMError, match="TooManyRedirects"):
        gemini_with(transport, waits).complete_json(system="s", prompt="p", temperature=0)

    assert len(seen) == 1
    assert waits == []
