"""요청마다 `request_id`를 붙이고 본문 없는 접근 로그를 남긴다.

접근 로그에는 경로, 상태 코드, 소요 시간, `request_id`만 남긴다. 쿼리 문자열과 본문은 읽지 않는다.
처리하지 못한 예외는 여기서 500으로 바꾸고 예외 종류만 남긴다. 예외 메시지에 요청 값이 섞일 수 있어
Uvicorn이 traceback을 찍지 않도록 다시 올리지 않는다.
"""

import logging
import time
import uuid

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.errors import INTERNAL_ERROR, error_response

REQUEST_ID_HEADER = "X-Request-ID"

access_logger = logging.getLogger("app.access")
error_logger = logging.getLogger("app.error")


def new_request_id() -> str:
    return f"req-{uuid.uuid4().hex}"


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = new_request_id()
        scope.setdefault("state", {})["request_id"] = request_id
        status_code = 500
        response_started = False
        started_at = time.perf_counter()

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception as exc:
            error_logger.error("unhandled=%s request_id=%s", type(exc).__name__, request_id)
            if not response_started:
                response = error_response(500, INTERNAL_ERROR, request_id)
                await response(scope, receive, send_with_request_id)
        finally:
            duration_ms = (time.perf_counter() - started_at) * 1000
            access_logger.info(
                "path=%r status=%d duration_ms=%.1f request_id=%s",
                scope["path"],
                status_code,
                duration_ms,
                request_id,
            )
