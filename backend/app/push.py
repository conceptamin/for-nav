# 근로자 앱 푸시 알림(backlog 28). 센터가 채팅에 쓰거나 상태를 바꾸면 그 사례에 묶인 기기로 FCM 알림 한 줄을 보낸다.
# 외부 호출이라 mail.py처럼 프로토콜(PushSender) 뒤에 두고 테스트는 가짜(tests/fakes.py)로 바꾼다. 설정이 없으면 발송기가 없다(None).
# 발송은 응답을 먼저 끝낸 뒤 백그라운드 작업으로 돈다(시간 제한, 재시도 없음). 실패는 종류만 로그에 남긴다.
# 기기 토큰·채팅 토큰·notice·메시지 본문은 로그·예외에 넣지 않는다.

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

import httpx
from google.auth import crypt
from google.auth import jwt as google_jwt

from app import clock
from app.settings import Settings
from app.store import CenterStore, PushDevice

logger = logging.getLogger(__name__)

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
FCM_SEND_URL = "https://fcm.googleapis.com/v1/projects/{project}/messages:send"
DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"
JWT_BEARER = "urn:ietf:params:oauth:grant-type:jwt-bearer"
# 발송 한 번(접근 토큰 받기 포함)의 시간 제한. 재시도하지 않는다
DEFAULT_TIMEOUT_S = 5.0
# 접근 토큰은 만료 이만큼 전에 새로 받는다
TOKEN_MARGIN = timedelta(seconds=60)
# 사례마다 이 간격 안의 두 번째 사건은 보내지 않는다(결정 3)
PUSH_INTERVAL = timedelta(seconds=60)

# 알림 제목은 앱 이름 하나다(결정 2). 본문은 근로자가 등록할 때 보낸 notice다
PUSH_TITLE = "for nav"
# FCM이 이렇게 답하면 그 기기 토큰은 다시 쓸 수 없으므로 지운다
UNREGISTERED = "UNREGISTERED"
INVALID_ARGUMENT = "INVALID_ARGUMENT"
GONE_KINDS = frozenset({UNREGISTERED, INVALID_ARGUMENT})

_KIND = re.compile(r"[A-Z_]{1,40}")
_FCM_ERROR_TYPE = "type.googleapis.com/google.firebase.fcm.v1.FcmError"


class PushError(Exception):
    """보내지 못했다. `kind`는 짧은 식별자(FCM 오류 코드, 예외 이름, HTTP 상태)이고 토큰·본문을 넣지 않는다."""

    def __init__(self, kind: str) -> None:
        super().__init__(kind)
        self.kind = kind


class PushSender(Protocol):
    async def send(self, device_token: str, platform: str, title: str, body: str, data: dict[str, str], collapse: str) -> None:
        """기기 하나에 알림 한 통. 실패는 PushError로 올린다."""
        ...


def fcm_message(device_token: str, title: str, body: str, data: dict[str, str], collapse: str) -> dict:
    """FCM HTTP v1 메시지. collapse(사례 id)를 Android collapse_key·tag와 APNs apns-collapse-id로 주어 알림 센터에 사례당 한 줄만 남긴다."""
    return {
        "token": device_token,
        "notification": {"title": title, "body": body},
        "data": data,
        "android": {"collapse_key": collapse, "notification": {"tag": collapse}},
        "apns": {"headers": {"apns-collapse-id": collapse}},
    }


def _error_kind(r: httpx.Response) -> str:
    """FCM 오류 응답에서 종류만 뽑는다. FcmError.errorCode가 있으면 그것, 없으면 error.status, 그것도 없으면 HTTP 상태."""
    try:
        err = r.json().get("error", {})
        codes = [d.get("errorCode") for d in err.get("details", []) if d.get("@type") == _FCM_ERROR_TYPE]
        for kind in [*codes, err.get("status")]:
            if isinstance(kind, str) and _KIND.fullmatch(kind):
                return kind
    except (ValueError, AttributeError, TypeError):
        pass
    return f"HTTP {r.status_code}"


@dataclass(frozen=True)
class ServiceAccount:
    email: str
    token_uri: str
    signer: crypt.Signer


def load_service_account(path: str) -> ServiceAccount:
    """서비스 계정 키 JSON을 읽는다. 파일이 없거나 형식이 틀리면 OSError·ValueError."""
    with open(path, encoding="utf-8") as f:
        info = json.load(f)
    if not isinstance(info, dict) or info.get("type") != "service_account" or not info.get("client_email"):
        raise ValueError("NotServiceAccount")
    return ServiceAccount(
        email=info["client_email"],
        token_uri=info.get("token_uri") or DEFAULT_TOKEN_URI,
        signer=crypt.RSASigner.from_service_account_info(info),
    )


class FcmSender:
    """FCM HTTP v1 발송. 접근 토큰은 google-auth 서명기로 만든 서비스 계정 JWT를 httpx로 바꿔 받고, 만료 전까지 메모리에 둔다.

    google-auth의 자격 증명 refresh는 동기 requests 전송이라 이벤트 루프를 막으므로 토큰 교환만 httpx로 직접 한다.
    `transport`는 테스트가 가짜 전송(httpx.MockTransport)을 끼울 자리다.
    """

    def __init__(self, project_id: str, account: ServiceAccount, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._url = FCM_SEND_URL.format(project=project_id)
        self._account = account
        self._transport = transport
        self._token: str | None = None
        self._token_until: datetime | None = None
        self._lock = asyncio.Lock()

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        async with self._lock:
            now = clock.now()
            if self._token and self._token_until and now < self._token_until:
                return self._token
            iat = int(now.timestamp())
            payload = {"iss": self._account.email, "scope": FCM_SCOPE, "aud": self._account.token_uri, "iat": iat, "exp": iat + 3600}
            assertion = google_jwt.encode(self._account.signer, payload).decode()
            r = await client.post(self._account.token_uri, data={"grant_type": JWT_BEARER, "assertion": assertion})
            if r.status_code >= 300:
                raise PushError(f"token HTTP {r.status_code}")
            try:
                body = r.json()
                token, expires_in = body["access_token"], int(body.get("expires_in", 3600))
            except (ValueError, KeyError, TypeError):
                raise PushError("token BadResponse") from None
            self._token, self._token_until = token, now + timedelta(seconds=expires_in) - TOKEN_MARGIN
            return token

    async def send(self, device_token: str, platform: str, title: str, body: str, data: dict[str, str], collapse: str) -> None:
        # 플랫폼과 관계없이 같은 메시지다. iOS는 FCM이 APNs로 넘긴다(결정 5)
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_S, transport=self._transport) as client:
                token = await self._access_token(client)
                r = await client.post(
                    self._url,
                    headers={"Authorization": f"Bearer {token}"},
                    json={"message": fcm_message(device_token, title, body, data, collapse)},
                )
        except httpx.HTTPError as e:
            raise PushError(type(e).__name__) from None
        if r.status_code == 401:
            # 토큰이 서버 쪽에서 먼저 끝났다. 다음 발송에서 새로 받는다(지금 것은 재시도하지 않는다)
            self._token = None
        if r.status_code >= 300:
            raise PushError(_error_kind(r))


def make_push_sender(s: Settings) -> PushSender | None:
    """PUSH=off(기본)이면 None. fcm인데 값이 빠졌거나 키 파일을 못 읽으면 경고 한 줄을 남기고 None(서버는 그대로 뜬다)."""
    if s.push != "fcm":
        return None
    if not (s.fcm_project_id and s.fcm_credentials_file):
        logger.warning("push off: PUSH=fcm인데 FCM_PROJECT_ID·FCM_CREDENTIALS_FILE이 없다")
        return None
    try:
        account = load_service_account(s.fcm_credentials_file)
    except (OSError, ValueError) as e:
        logger.warning("push off: FCM 서비스 계정 키를 읽지 못했다 %s", type(e).__name__)
        return None
    return FcmSender(s.fcm_project_id, account)


class PushNotifier:
    """사례 하나의 사건(센터 채팅 글, 상태 변경)을 묶인 기기로 보낸다. 사례마다 PUSH_INTERVAL에 한 번까지, 근로자가 채팅에 붙어 있으면 건너뛴다.

    마지막 발송 시각은 프로세스 메모리다(채팅 연결과 같이 --workers 1 기준).
    """

    def __init__(self, sender: PushSender | None, timeout_s: float = DEFAULT_TIMEOUT_S) -> None:
        self.sender = sender
        self.timeout_s = timeout_s
        self._last: dict[str, datetime] = {}
        self._tasks: set[asyncio.Task] = set()

    def notify(self, store: CenterStore, case_id: str, now: datetime, *, watching: bool) -> None:
        """보낼지 정하고 발송을 백그라운드 작업으로 띄운다. 기다리지 않고, 실패해도 부르는 쪽(채팅·PATCH)에 올리지 않는다."""
        if self.sender is None or watching:
            return
        last = self._last.get(case_id)
        if last is not None and now - last < PUSH_INTERVAL:
            return
        try:
            devices = store.push_devices(case_id, now)
        except Exception as e:
            logger.warning("push skipped kind=%s", type(e).__name__)
            return
        if not devices:
            return
        self._last[case_id] = now
        task = asyncio.create_task(self._send_all(store, devices))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _send_all(self, store: CenterStore, devices: list[PushDevice]) -> None:
        await asyncio.gather(*(self._send_one(store, d) for d in devices))

    async def _send_one(self, store: CenterStore, d: PushDevice) -> None:
        assert self.sender is not None
        # data에는 kind·caseId만 둔다. 메시지 본문·상태 이름은 넣지 않는다(결정 2)
        data = {"kind": "center", "caseId": d.case_id}
        try:
            async with asyncio.timeout(self.timeout_s):
                await self.sender.send(d.device_token, d.platform, PUSH_TITLE, d.notice, data, d.case_id)
        except PushError as e:
            logger.warning("push failed kind=%s", e.kind)
            if e.kind in GONE_KINDS:
                self._forget(store, d.device_token)
        except TimeoutError:
            logger.warning("push failed kind=Timeout")
        except Exception as e:
            logger.warning("push failed kind=%s", type(e).__name__)

    @staticmethod
    def _forget(store: CenterStore, device_token: str) -> None:
        try:
            store.remove_push_device(device_token)
        except Exception as e:
            logger.warning("push remove failed kind=%s", type(e).__name__)

    async def drain(self) -> None:
        """띄운 발송이 모두 끝날 때까지 기다린다(테스트용)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)
