"""테스트용 가짜 LLM·메일·Google ID 토큰 검증·푸시 발송. 외부 네트워크에 접속하지 않고 받은 프롬프트와 출력 스키마, 보낸 메일, 확인한 토큰, 보낸 알림을 기록한다."""

import asyncio
import re
from collections.abc import Iterable
from typing import Any

from app.google_id import GoogleIdError
from app.llm import LLMError, LLMPrompt
from app.mail import MailError
from app.push import UNREGISTERED, PushError

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


class FakeMailer:
    """테스트용 가짜 메일(backlog 17). 보낸 메일을 모으고, `fail`이면 공급자 실패처럼 MailError를 올린다."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.sent: list[tuple[str, str, str]] = []

    async def send(self, to: str, subject: str, text: str) -> None:
        if self.fail:
            raise MailError("HTTP 500")
        self.sent.append((to, subject, text))

    def last_code(self) -> str:
        m = re.search(r"\d{6}", self.sent[-1][2])
        assert m, "메일에 6자리 코드가 없다"
        return m.group()


class FakeVerifier:
    """테스트용 가짜 Google ID 토큰 검증(backlog 21). 정해 둔 토큰이면 그 sub를, 아니면 GoogleIdError를 올린다."""

    def __init__(self, tokens: dict[str, str]) -> None:
        self.tokens = tokens
        self.seen: list[str] = []

    def verify(self, credential: str) -> str:
        self.seen.append(credential)
        if credential not in self.tokens:
            raise GoogleIdError("ValueError")
        return self.tokens[credential]


class FakePushSender:
    """테스트용 가짜 푸시 발송(backlog 28). 보낸 알림을 `sent`에, 시도한 기기 토큰을 `attempts`에 쌓는다.

    `unregistered`의 토큰은 FCM이 없는 토큰이라고 답한 것처럼 PushError(UNREGISTERED)로, `fail`이 있으면 그 예외로 실패한다.
    `hang`이면 시간 제한까지 기다린다.
    """

    def __init__(self, unregistered: Iterable[str] = (), fail: Exception | None = None, hang: bool = False) -> None:
        self.unregistered = set(unregistered)
        self.fail = fail
        self.hang = hang
        self.sent: list[dict[str, Any]] = []
        self.attempts: list[str] = []

    async def send(self, device_token: str, platform: str, title: str, body: str, data: dict[str, str], collapse: str) -> None:
        self.attempts.append(device_token)
        if self.hang:
            await asyncio.Event().wait()
        if device_token in self.unregistered:
            raise PushError(UNREGISTERED)
        if self.fail is not None:
            raise self.fail
        self.sent.append({"token": device_token, "platform": platform, "title": title, "body": body, "data": data, "collapse": collapse})
