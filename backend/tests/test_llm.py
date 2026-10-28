# LLM 호출 계층: 시간 제한·재시도·스키마 검증·원문 미기록, 그리고 Anthropic 어댑터(네트워크 없이 가짜 전송으로).

import asyncio
import json
import logging

import anthropic
import httpx2
import pytest
from fakes import FakeLLMClient, provider_error
from pydantic import BaseModel

from app.llm import DEFAULT_ATTEMPTS, LLMError, LLMPrompt, LLMUnavailableError, generate
from app.llm_providers.anthropic import AnthropicClient

PROMPT = LLMPrompt(system="출력은 JSON", user="합성 입력")
RAW_MARKER = "llm-raw-output-must-not-be-logged-5c1d"


class Extracted(BaseModel):
    task: str | None


def run(client: FakeLLMClient, *, timeout_s: float = 1.0) -> Extracted:
    return asyncio.run(generate(client, PROMPT, Extracted, timeout_s=timeout_s))


def test_valid_output_is_parsed_with_one_call() -> None:
    client = FakeLLMClient(['{"task": null}'])

    assert run(client) == Extracted(task=None)
    assert client.prompts == [PROMPT]
    assert client.schemas == [Extracted.model_json_schema()]


@pytest.mark.parametrize(
    "first",
    [
        f'{{"task": 1, "note": "{RAW_MARKER}"}}',  # 스키마 불일치
        f"not json {RAW_MARKER}",  # JSON 아님
        provider_error(),
        None,  # 시간 초과
    ],
    ids=["schema", "not-json", "provider-error", "timeout"],
)
def test_failure_is_retried_once(first: str | Exception | None) -> None:
    client = FakeLLMClient([first, '{"task": "welding"}'])

    assert run(client, timeout_s=0.05) == Extracted(task="welding")
    assert len(client.prompts) == 2


def test_gives_up_after_retry_without_third_call() -> None:
    client = FakeLLMClient([provider_error(), None, '{"task": "never-read"}'])

    with pytest.raises(LLMUnavailableError) as exc_info:
        run(client, timeout_s=0.05)

    assert len(client.prompts) == DEFAULT_ATTEMPTS == 2
    assert exc_info.value.__context__ is None
    assert exc_info.value.__cause__ is None


def test_raw_output_is_not_logged_or_chained(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    client = FakeLLMClient([f'{{"task": "{RAW_MARKER}"', f"[{RAW_MARKER}]"])

    with pytest.raises(LLMUnavailableError) as exc_info:
        run(client)

    assert [r.getMessage() for r in caplog.records if r.name == "app.llm"] == [
        "llm attempt=1/2 failed=ValidationError",
        "llm attempt=2/2 failed=ValidationError",
    ]
    assert RAW_MARKER not in caplog.text
    assert RAW_MARKER not in str(exc_info.value)


def test_failure_log_names_provider_error_kind(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    client = FakeLLMClient([provider_error("RateLimitError"), None])

    with pytest.raises(LLMUnavailableError):
        run(client, timeout_s=0.05)

    assert [r.getMessage() for r in caplog.records if r.name == "app.llm"] == [
        "llm attempt=1/2 failed=LLMError/RateLimitError",
        "llm attempt=2/2 failed=TimeoutError",
    ]


# --- Anthropic 어댑터: 가짜 전송으로 요청 형태와 오류 변환을 본다 ---


def _message(text: str, stop_reason: str = "end_turn") -> dict:
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-haiku-5-5",
        "content": [{"type": "thinking", "thinking": "", "signature": "sig"}, {"type": "text", "text": text}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }


def _adapter(handler) -> AnthropicClient:
    http_client = anthropic.DefaultAsyncHttpxClient(transport=httpx2.MockTransport(handler))
    return AnthropicClient(api_key="test-key", model="claude-haiku-5-5", http_client=http_client)


def _complete(client: AnthropicClient) -> str:
    return asyncio.run(client.complete(PROMPT, output_schema=Extracted.model_json_schema()))


def test_adapter_sends_prompt_and_json_schema() -> None:
    requests: list[dict] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(json.loads(request.content))
        return httpx2.Response(200, json=_message('{"task": "welding"}'))

    assert _complete(_adapter(handler)) == '{"task": "welding"}'

    [body] = requests
    assert body["model"] == "claude-haiku-5-5"
    assert body["system"] == PROMPT.system
    assert body["messages"] == [{"role": "user", "content": PROMPT.user}]
    output_format = body["output_config"]["format"]
    assert output_format["type"] == "json_schema"
    assert output_format["schema"]["additionalProperties"] is False
    assert set(output_format["schema"]["properties"]) == {"task"}


@pytest.mark.parametrize(
    ("response", "kind"),
    [
        (httpx2.Response(429, json={"type": "error", "error": {"type": "rate_limit_error", "message": RAW_MARKER}}), "RateLimitError"),
        (httpx2.Response(500, json={"type": "error", "error": {"type": "api_error", "message": RAW_MARKER}}), "InternalServerError"),
        (httpx2.Response(200, json=_message(RAW_MARKER, stop_reason="refusal")), "stop_reason=refusal"),
        (httpx2.Response(200, json=_message(RAW_MARKER, stop_reason="max_tokens")), "stop_reason=max_tokens"),
    ],
    ids=["rate-limit", "server-error", "refusal", "max-tokens"],
)
def test_adapter_raises_llm_error_without_raw_text(response: httpx2.Response, kind: str) -> None:
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return response

    with pytest.raises(LLMError) as exc_info:
        _complete(_adapter(handler))

    assert exc_info.value.kind == kind
    assert RAW_MARKER not in str(exc_info.value)
    # SDK 예외(본문에 원문이 있을 수 있다)는 트레이스백에 이어 찍히지 않는다.
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__context__ is None or exc_info.value.__suppress_context__
    # 재시도는 generate()가 맡으므로 SDK는 한 번만 부른다.
    assert calls == 1


def test_adapter_connection_error_is_llm_error() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("offline", request=request)

    with pytest.raises(LLMError) as exc_info:
        _complete(_adapter(handler))

    assert exc_info.value.kind == "APIConnectionError"
