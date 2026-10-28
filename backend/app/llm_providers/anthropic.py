"""Anthropic Messages API 어댑터.

시간 제한과 재시도는 `app.llm.generate()`가 맡으므로 SDK 자체 재시도는 끈다(켜 두면 한 번의 시간 제한 안에서 몰래 다시 부른다).
응답은 `output_config.format`(JSON 스키마)으로 고정한다. SDK 예외는 메시지를 버리고 예외 이름만 `LLMError`로 올린다.
"""

from typing import Any

import anthropic

from app.llm import LLMError, LLMPrompt

# 추출·슬롯 채우기·짧은 번역용이다. 사고(thinking) 토큰도 여기에 포함되므로 짧은 출력보다 넉넉히 둔다.
MAX_TOKENS = 4096
# 짧고 정해진 형식의 작업이라 지연을 줄이는 쪽을 고른다. Haiku 5.5 기본값은 medium이다.
EFFORT = "low"


class AnthropicClient:
    def __init__(self, *, api_key: str, model: str, http_client: anthropic.DefaultAsyncHttpxClient | None = None) -> None:
        # http_client는 테스트에서 네트워크 없이 응답을 흉내낼 때만 넘긴다.
        self.model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=0, http_client=http_client)

    async def complete(self, prompt: LLMPrompt, *, output_schema: dict[str, Any]) -> str:
        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=prompt.system,
                messages=[{"role": "user", "content": prompt.user}],
                output_config={
                    "effort": EFFORT,
                    "format": {"type": "json_schema", "schema": anthropic.transform_schema(output_schema)},
                },
            )
        except anthropic.AnthropicError as exc:
            # 오류 메시지·본문에는 요청 내용이 섞일 수 있어 이름만 남기고 체인을 끊는다.
            raise LLMError(type(exc).__name__) from None
        # 거절(refusal)·길이 초과(max_tokens)면 스키마에 맞는 출력이 아닐 수 있다.
        if response.stop_reason != "end_turn":
            raise LLMError(f"stop_reason={response.stop_reason}")
        text = next((block.text for block in response.content if block.type == "text"), None)
        if text is None:
            raise LLMError("no_text")
        return text

    async def aclose(self) -> None:
        await self._client.close()
