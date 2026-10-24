import asyncio
import logging

import pytest
from fakes import FakeLLMClient, provider_error
from pydantic import BaseModel

from app.llm import DEFAULT_ATTEMPTS, LLMPrompt, LLMUnavailableError, generate

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
