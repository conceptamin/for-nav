"""LLM 호출 제한(backlog 20).

공개 주소에서 로그인 없이 부를 수 있는 LLM 자리(추출·템플릿 슬롯·번역·통화 자막)의 비용 상한이다.
공급자 호출 한 번(재시도 포함)을 하나로 세고, 클라이언트 IP별 최근 60초와 서버 전체 하루(Asia/Seoul)에 상한을 둔다.
넘으면 `LLMError(LIMITED)`를 올려 기존 실패 경로를 탄다. 부르는 쪽은 키워드 사전·기본 템플릿·원문으로 응답하고 API는 바뀌지 않는다.
상태는 프로세스 메모리에 있어 서버를 다시 띄우면 0부터 센다(`--workers 1` 전제는 채팅·통화와 같다).
"""

import logging
from collections import deque
from datetime import date
from typing import Any

from starlette.requests import HTTPConnection

from app import clock
from app.llm import LIMITED, LLMClient, LLMError, LLMPrompt

logger = logging.getLogger(__name__)

WINDOW_S = 60.0
# 터널(cloudflared)이 같은 기기에서 붙는 주소. 이 상대가 보낸 IP 헤더만 믿는다.
LOOPBACK = frozenset({"127.0.0.1", "::1"})


class LLMLimiter:
    def __init__(self, per_min: int = 0, daily: int = 0, ip_header: str = "") -> None:
        self.per_min = per_min
        self.daily = daily
        self.ip_header = ip_header
        self._recent: dict[str, deque[float]] = {}
        self._day: date | None = None
        self._today = 0
        self._swept = 0.0

    @property
    def enabled(self) -> bool:
        return bool(self.per_min or self.daily)

    def take(self, key: str) -> bool:
        """호출 하나를 센다. 상한을 넘었으면 세지 않고 False다. await가 없어 이벤트 루프 안에서 끊기지 않는다."""
        now = clock.now()
        t = now.timestamp()
        if now.date() != self._day:
            self._day, self._today = now.date(), 0
        self._sweep(t)
        if self.daily and self._today >= self.daily:
            # IP는 개인 정보라 로그에 남기지 않는다.
            logger.warning("llm limited scope=daily")
            return False
        if self.per_min:
            recent = self._recent.setdefault(key, deque())
            while recent and recent[0] <= t - WINDOW_S:
                recent.popleft()
            if len(recent) >= self.per_min:
                logger.warning("llm limited scope=ip")
                return False
            recent.append(t)
        self._today += 1
        return True

    def _sweep(self, t: float) -> None:
        # 다시 오지 않는 IP가 쌓이지 않게 1분에 한 번, 창이 빈 IP를 지운다.
        if t - self._swept < WINDOW_S:
            return
        self._swept = t
        self._recent = {k: q for k, q in self._recent.items() if q and q[-1] > t - WINDOW_S}

    def wrap(self, client: LLMClient | None, conn: HTTPConnection) -> LLMClient | None:
        """요청을 보낸 클라이언트 몫으로 세는 클라이언트. LLM이 없거나 제한이 모두 꺼져 있으면 그대로 돌려준다."""
        if client is None or not self.enabled:
            return client
        return LimitedLLMClient(client, self, client_key(conn, self.ip_header))


def client_key(conn: HTTPConnection, ip_header: str) -> str:
    """TCP 상대 주소. 상대가 루프백(같은 기기의 터널)이고 헤더 이름이 있으면 그 헤더 값이다.

    서버는 0.0.0.0으로 떠 있어 같은 망에서 직접 붙은 클라이언트가 헤더를 꾸밀 수 있으므로 루프백 밖에서는 헤더를 보지 않는다.
    """
    peer = conn.client.host if conn.client else ""
    if ip_header and peer in LOOPBACK:
        forwarded = conn.headers.get(ip_header, "").strip()
        if forwarded:
            return forwarded
    return peer


class LimitedLLMClient:
    def __init__(self, inner: LLMClient, limiter: LLMLimiter, key: str) -> None:
        self._inner = inner
        self._limiter = limiter
        self._key = key

    async def complete(self, prompt: LLMPrompt, *, output_schema: dict[str, Any]) -> str:
        if not self._limiter.take(self._key):
            raise LLMError(LIMITED)
        return await self._inner.complete(prompt, output_schema=output_schema)

    async def aclose(self) -> None:
        # 감싼 클라이언트는 서버가 시작할 때 만들고 끝날 때 닫는다.
        pass
