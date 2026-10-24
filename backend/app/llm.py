"""LLM 호출 인터페이스.

공급자 구현은 `LLMClient`만 따른다. 테스트는 가짜 구현을 쓰고 외부 LLM을 호출하지 않는다.
프롬프트·LLM 응답 원문은 로그·예외 메시지에 넣지 않는다.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 10.0
# 첫 호출 + 재시도 1회.
DEFAULT_ATTEMPTS = 2

OutputT = TypeVar("OutputT", bound=BaseModel)


@dataclass(frozen=True)
class LLMPrompt:
    system: str
    user: str


class LLMClient(Protocol):
    async def complete(self, prompt: LLMPrompt) -> str:
        """공급자의 응답 본문(JSON 문자열)을 돌려준다. 공급자 오류는 `LLMError`로 바꿔 올린다."""
        ...


class LLMError(Exception):
    """공급자 호출 실패. 메시지에 프롬프트·응답 원문을 넣지 않는다."""


class LLMUnavailableError(Exception):
    """재시도 후에도 스키마에 맞는 출력을 받지 못했다. API에서는 503 `LLM_UNAVAILABLE`이다."""

    def __init__(self) -> None:
        super().__init__("LLM 출력을 받지 못했습니다")


async def generate(
    client: LLMClient,
    prompt: LLMPrompt,
    output_type: type[OutputT],
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    attempts: int = DEFAULT_ATTEMPTS,
) -> OutputT:
    """호출마다 시간 제한을 두고, 실패하거나 출력이 스키마에 맞지 않으면 다시 호출한다."""
    for attempt in range(1, attempts + 1):
        try:
            async with asyncio.timeout(timeout_s):
                raw = await client.complete(prompt)
            return output_type.model_validate_json(raw)
        except (TimeoutError, LLMError, ValidationError) as exc:
            # 검증 오류의 문자열에는 응답 원문이 들어 있으므로 예외 종류만 남긴다.
            logger.warning("llm attempt=%d/%d failed=%s", attempt, attempts, type(exc).__name__)
    # except 블록 밖에서 올려 원문이 담긴 예외가 __context__로 이어지지 않게 한다.
    raise LLMUnavailableError
