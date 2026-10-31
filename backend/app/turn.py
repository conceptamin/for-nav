# 통화 TURN 자격 증명(backlog 31). 이동통신망끼리처럼 STUN만으로 음성이 붙지 않는 망에서 Cloudflare TURN이 음성을 중계한다.
# TURN 키는 오래 쓰는 비밀값이라 서버에만 두고, 통화를 걸거나 받을 때마다 짧게 유효한 자격 증명을 새로 받아 그 사례의 근로자·센터에게만 준다.
# 외부 호출이라 push.py처럼 프로토콜(TurnIssuer) 뒤에 두고 테스트는 가짜(tests/fakes.py)로 바꾼다. 설정이 없으면 발급기가 없다(None).
# 실패하면 빈 목록을 돌려주고 프론트가 자기 STUN 기본값으로 건다(통화가 TURN 때문에 막히지 않는다).
# 키·API 토큰·발급한 username·credential은 로그·예외에 넣지 않는다.

import logging
from typing import Any, Protocol

import httpx

from app.settings import Settings

logger = logging.getLogger(__name__)

CLOUDFLARE_TURN_URL = "https://rtc.live.cloudflare.com/v1/turn/keys/{key_id}/credentials/generate-ice-servers"
# 발급 한 번의 시간 제한. 재시도하지 않는다(통화 시작을 오래 붙잡지 않게)
DEFAULT_TIMEOUT_S = 3.0
# 브라우저는 53번 포트를 막아 그 주소는 시간 초과로만 끝난다(Cloudflare 문서). 받으면 뺀다
_BLOCKED_PORT = ":53"


class TurnError(Exception):
    """받지 못했다. `kind`는 짧은 식별자(HTTP 상태, 예외 이름)이고 키·자격 증명을 넣지 않는다."""

    def __init__(self, kind: str) -> None:
        super().__init__(kind)
        self.kind = kind


class TurnIssuer(Protocol):
    async def issue(self) -> list[dict[str, Any]]:
        """RTCPeerConnection에 그대로 넣을 iceServers. 실패는 TurnError로 올린다."""
        ...


def _browser_urls(urls: Any) -> list[str]:
    items = [urls] if isinstance(urls, str) else urls if isinstance(urls, list) else []
    return [u for u in items if isinstance(u, str) and not u.split("?", 1)[0].endswith(_BLOCKED_PORT)]


def clean_ice_servers(raw: Any) -> list[dict[str, Any]]:
    """공급자 응답에서 브라우저가 쓸 수 있는 항목(urls, username, credential)만 남긴다. 모양이 틀리면 TurnError."""
    servers = raw.get("iceServers") if isinstance(raw, dict) else None
    if not isinstance(servers, list):
        raise TurnError("bad_response")
    out: list[dict[str, Any]] = []
    for s in servers:
        if not isinstance(s, dict):
            continue
        urls = _browser_urls(s.get("urls"))
        if not urls:
            continue
        item: dict[str, Any] = {"urls": urls}
        for k in ("username", "credential"):
            if isinstance(s.get(k), str):
                item[k] = s[k]
        out.append(item)
    if not out:
        raise TurnError("bad_response")
    return out


class CloudflareTurn:
    def __init__(
        self,
        key_id: str,
        api_token: str,
        ttl_s: int,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._url = CLOUDFLARE_TURN_URL.format(key_id=key_id)
        self._token = api_token
        self._ttl_s = ttl_s
        self._timeout_s = timeout_s
        self._transport = transport

    async def issue(self) -> list[dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s, transport=self._transport) as client:
                r = await client.post(self._url, headers={"Authorization": f"Bearer {self._token}"}, json={"ttl": self._ttl_s})
        except httpx.HTTPError as e:
            raise TurnError(type(e).__name__) from None
        if r.status_code not in (200, 201):
            raise TurnError(f"http_{r.status_code}")
        try:
            body = r.json()
        except ValueError:
            raise TurnError("bad_response") from None
        return clean_ice_servers(body)


def make_turn_issuer(s: Settings) -> TurnIssuer | None:
    """TURN=cloudflare이고 키 ID·API 토큰이 있을 때만 발급기를 만든다. 빠졌으면 경고 한 줄 뒤 None(STUN만)."""
    if s.turn != "cloudflare":
        return None
    if not (s.turn_key_id and s.turn_api_token):
        logger.warning("turn off: TURN_KEY_ID와 TURN_API_TOKEN이 있어야 한다")
        return None
    return CloudflareTurn(s.turn_key_id, s.turn_api_token, s.turn_ttl_s)


async def ice_servers(issuer: TurnIssuer | None) -> list[dict[str, Any]]:
    """발급기가 없거나 실패하면 빈 목록. 실패는 종류만 남긴다."""
    if issuer is None:
        return []
    try:
        return await issuer.issue()
    except TurnError as e:
        logger.warning("turn issue failed: %s", e.kind)
        return []
