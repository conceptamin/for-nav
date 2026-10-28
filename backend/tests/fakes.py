"""테스트용 가짜 LLM. 외부 네트워크에 접속하지 않고 받은 프롬프트와 출력 스키마를 기록한다."""

import asyncio
from collections.abc import Iterable
from typing import Any

from app.llm import LLMError, LLMPrompt

# 차례마다 돌려줄 값. 문자열은 응답 본문, 예외는 그대로 올리고, None이면 시간 초과까지 기다린다.
Reply = str | Exception | None


class FakeLLMClient:
    def __init__(self, replies: Iterable[Reply]) -> None:
        self._replies = list(replies)
        self.prompts: list[LLMPrompt] = []
        self.schemas: list[dict[str, Any]] = []

    async def complete(self, prompt: LLMPrompt, *, output_schema: dict[str, Any]) -> str:
        self.prompts.append(prompt)
        self.schemas.append(output_schema)
        if not self._replies:
            raise AssertionError("준비한 응답보다 많이 호출했다")
        reply = self._replies.pop(0)
        if reply is None:
            await asyncio.Event().wait()
            raise AssertionError("시간 제한이 걸리지 않았다")
        if isinstance(reply, Exception):
            raise reply
        return reply

    async def aclose(self) -> None:
        pass


def provider_error(kind: str = "APIConnectionError") -> LLMError:
    return LLMError(kind)
