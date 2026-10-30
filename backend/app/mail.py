# 메일 발송(backlog 17): 센터 직원 로그인 코드 한 통. 외부 호출이라 llm.py처럼 프로토콜 뒤에 두고 테스트는 가짜(tests/fakes.py)로 바꾼다.
# 받는 사람·본문(코드)은 로그에 남기지 않는다. 실패는 MailError 하나로 올리고 종류만 담는다.

from typing import Protocol

import httpx

from app.settings import Settings

RESEND_URL = "https://api.resend.com/emails"
DEFAULT_TIMEOUT_S = 10.0


class MailError(Exception):
    """메일을 보내지 못했다. 메시지는 오류 종류(예외 이름, HTTP 상태)만 담는다."""


class Mailer(Protocol):
    async def send(self, to: str, subject: str, text: str) -> None: ...


class ResendMailer:
    def __init__(self, api_key: str, sender: str, timeout_s: float = DEFAULT_TIMEOUT_S) -> None:
        self._api_key = api_key
        self._sender = sender
        self._timeout_s = timeout_s

    async def send(self, to: str, subject: str, text: str) -> None:
        # 로그인 코드는 드물게 보내므로 연결을 들고 있지 않고 부를 때마다 연다.
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                r = await client.post(
                    RESEND_URL,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={"from": self._sender, "to": [to], "subject": subject, "text": text},
                )
        except httpx.HTTPError as e:
            raise MailError(type(e).__name__) from None
        if r.status_code >= 300:
            raise MailError(f"HTTP {r.status_code}")


class ConsoleMailer:
    """로컬 개발 전용. 설정이 CENTER_COOKIE_SECURE=false일 때만 고른다(settings._check_center_auth).
    로거가 아니라 표준 출력에 찍어 접근 로그·앱 로그에 남지 않게 한다. 받는 사람은 찍지 않는다."""

    async def send(self, to: str, subject: str, text: str) -> None:
        print(f"[console mail] {subject}\n{text}", flush=True)


def make_mailer(s: Settings) -> Mailer | None:
    """센터 로그인이 꺼져 있으면 None이다."""
    if s.center_auth != "email":
        return None
    if s.mail_provider == "console":
        return ConsoleMailer()
    return ResendMailer(s.mail_api_key, s.mail_from)
