"""LLM 호출 인터페이스.

공급자 구현(`app/llm_providers/`)은 `LLMClient`만 따른다. 기능 쪽(추출·템플릿·번역)은 프롬프트와 출력 스키마만 정하고
`generate()`를 부른다. 테스트는 가짜 구현을 쓰고 외부 LLM을 호출하지 않는다.
프롬프트·LLM 응답 원문은 로그·예외 메시지·예외 체인에 넣지 않는다.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 10.0
# 첫 호출 + 재시도 1회.
DEFAULT_ATTEMPTS = 2


@dataclass(frozen=True)
class LLMPrompt:
    """system은 코드에 둔 상수, user에만 사용자 자유 입력을 넣는다."""

    system: str
    user: str


class LLMClient(Protocol):
    async def complete(self, prompt: LLMPrompt, *, output_schema: dict[str, Any]) -> str:
        """공급자의 응답 본문(JSON 문자열)을 돌려준다.

        `output_schema`는 출력 모델의 JSON 스키마다. 공급자에 JSON 출력 강제 옵션이 있으면 쓴다.
        공급자 오류는 `LLMError`로 바꿔 올린다.
        """
        ...

    async def aclose(self) -> None:
        """연결을 닫는다. 서버는 시작 시 한 번 만든 클라이언트를 종료 시 닫는다."""
        ...


class LLMError(Exception):
    """공급자 호출 실패. `kind`는 짧은 식별자(SDK 예외 이름, stop_reason)이고 프롬프트·응답 원문을 넣지 않는다."""

    def __init__(self, kind: str) -> None:
        super().__init__(kind)
        self.kind = kind


class LLMUnavailableError(Exception):
    """재시도 후에도 스키마에 맞는 출력을 받지 못했다. 부르는 쪽은 기본 템플릿·규칙으로 돌아간다."""

    def __init__(self) -> None:
        super().__init__("LLM 출력을 받지 못했습니다")


def _failure(exc: Exception) -> str:
    # 검증 오류의 문자열에는 응답 원문이 들어 있으므로 예외 종류만 남긴다.
    return f"LLMError/{exc.kind}" if isinstance(exc, LLMError) else type(exc).__name__


async def generate[OutputT: BaseModel](
    client: LLMClient,
    prompt: LLMPrompt,
    output_type: type[OutputT],
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    attempts: int = DEFAULT_ATTEMPTS,
) -> OutputT:
    """호출마다 시간 제한을 두고, 실패하거나 출력이 스키마에 맞지 않으면 다시 호출한다."""
    schema = output_type.model_json_schema()
    for attempt in range(1, attempts + 1):
        try:
            async with asyncio.timeout(timeout_s):
                raw = await client.complete(prompt, output_schema=schema)
            return output_type.model_validate_json(raw)
        except (TimeoutError, LLMError, ValidationError) as exc:
            logger.warning("llm attempt=%d/%d failed=%s", attempt, attempts, _failure(exc))
    # except 블록 밖에서 올려 원문이 담긴 예외가 __context__로 이어지지 않게 한다.
    raise LLMUnavailableError
