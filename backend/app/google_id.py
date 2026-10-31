# 근로자 Google 로그인(backlog 21): 프론트가 Google Identity Services로 받은 ID 토큰을 검증하고 계정 고유 번호(sub)만 돌려준다.
# Google 공개 키를 받는 외부 호출이라 mail.py처럼 프로토콜 뒤에 두고 테스트는 가짜(tests/fakes.py)로 바꾼다.
# 토큰·sub는 로그에 남기지 않는다. 실패는 GoogleIdError 하나로 올리고 종류(예외 이름)만 담는다.

from collections.abc import Callable
from functools import partial
from typing import Any, Protocol

from google.auth import exceptions as google_exceptions
from google.auth.transport.requests import Request as RequestsTransport
from google.oauth2 import id_token

from app.settings import Settings

# 공개 키를 받을 때의 시간 제한. google-auth 기본값(120초)은 로그인 화면이 기다리기에 너무 길다
CERTS_TIMEOUT_S = 10.0


class GoogleIdError(Exception):
    """ID 토큰을 받아들이지 않았다(서명·발급자·대상·만료·형식, 공개 키를 받지 못함). 이유를 응답으로 나누지 않는다."""


class TokenVerifier(Protocol):
    def verify(self, credential: str) -> str:
        """맞는 토큰이면 sub를 돌려주고, 아니면 GoogleIdError를 올린다."""
        ...


class GoogleVerifier:
    """서명, 발급자(accounts.google.com), 대상(aud == 클라이언트 ID), 만료를 google-auth가 함께 확인한다.

    네트워크로 공개 키를 받으므로 동기 경로(스레드 풀)에서 부른다. `transport`는 테스트가 공개 키 응답을 바꿔 끼울 자리다.
    """

    def __init__(self, client_id: str, transport: Callable[..., Any] | None = None) -> None:
        self._client_id = client_id
        self._transport = transport or partial(RequestsTransport(), timeout=CERTS_TIMEOUT_S)

    def verify(self, credential: str) -> str:
        try:
            claims = id_token.verify_oauth2_token(credential, self._transport, self._client_id)
        except (ValueError, google_exceptions.GoogleAuthError) as e:
            raise GoogleIdError(type(e).__name__) from None
        sub = claims.get("sub")
        if not isinstance(sub, str) or not sub:
            raise GoogleIdError("NoSub")
        return sub


def make_verifier(s: Settings) -> TokenVerifier | None:
    """근로자 로그인이 꺼져 있으면 None이다."""
    if s.worker_auth != "google":
        return None
    return GoogleVerifier(s.google_client_id)
