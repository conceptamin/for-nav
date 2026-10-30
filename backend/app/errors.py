# 공통 오류 형식과 요청 id·접근 로그.
# 모든 오류는 { "error": { "code", "message", "requestId" } }로 나간다.
# 로그에는 메서드·경로·상태 코드·소요 ms·request id만 남긴다. 쿼리 문자열·본문·헤더·예외 메시지는 남기지 않는다.

import logging
import re
import time
import traceback
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

log = logging.getLogger("app.access")

REQUEST_ID_HEADER = "X-Request-Id"
# 클라이언트가 보낸 id는 로그에 그대로 남으므로 짧은 안전 문자만 받는다. 그 밖이면 새로 만든다.
_SAFE_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")

CODES = {404: "NOT_FOUND", 422: "VALIDATION", 500: "INTERNAL"}


def _code(status: int) -> str:
    return CODES.get(status) or ("INTERNAL" if status >= 500 else "BAD_REQUEST")


def error_body(status: int, message: str, request_id: str) -> dict:
    return {"error": {"code": _code(status), "message": message, "requestId": request_id}}


def _request_id(scope: Scope) -> str:
    return scope.get("state", {}).get("request_id", "")


async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "요청을 처리할 수 없다"
    return JSONResponse(error_body(exc.status_code, message, _request_id(request.scope)), status_code=exc.status_code, headers=exc.headers)


async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # 검증 오류의 msg·input에는 요청 값이 들어갈 수 있으므로 어긋난 필드 위치만 알려 준다.
    fields = sorted({".".join(str(p) for p in e.get("loc", ())) for e in exc.errors()})
    message = "요청 형식이 올바르지 않다: " + ", ".join(fields) if fields else "요청 형식이 올바르지 않다"
    return JSONResponse(error_body(422, message, _request_id(request.scope)), status_code=422)


def _frames(exc: BaseException) -> str:
    """예외 위치만 남긴다. 예외 메시지는 요청 값을 담을 수 있어 빼고 타입 이름만 쓴다."""
    tb = traceback.extract_tb(exc.__traceback__)
    return " < ".join(f"{f.filename.rsplit('/', 1)[-1]}:{f.lineno} {f.name}" for f in reversed(tb[-5:]))


class RequestContextMiddleware:
    """요청 id를 정하고(받은 값 또는 새 값) 응답 헤더에 붙이며, 접근 로그 한 줄을 남긴다.
    처리 중 예외는 여기서 500 오류 형식으로 바꾼다. 다시 던지면 서버가 예외 메시지까지 로그에 남기기 때문이다."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "websocket":
            await self._websocket(scope, receive, send)
            return
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _assign_request_id(scope)
        started = time.perf_counter()
        status = 500
        response_started = False

        async def send_with_id(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                status, response_started = message["status"], True
                message["headers"] = [*message.get("headers", []), (REQUEST_ID_HEADER.lower().encode(), request_id.encode())]
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception as exc:
            status = 500
            log.error("unhandled %s at %s request_id=%s", type(exc).__name__, _frames(exc), request_id)
            if not response_started:
                await JSONResponse(error_body(500, "서버 오류가 발생했다", request_id), status_code=500)(scope, receive, send_with_id)
        finally:
            ms = (time.perf_counter() - started) * 1000
            log.info("%s %s %d %.1fms request_id=%s", scope["method"], scope["path"], status, ms, request_id)

    async def _websocket(self, scope: Scope, receive: Receive, send: Send) -> None:
        """WebSocket(상담 채팅, backlog 14)은 연결이 끝날 때 한 줄: WS, 경로, 닫힘 코드, 연결 시간, request id.
        쿼리 문자열(채팅 토큰)과 메시지 본문은 남기지 않는다."""
        request_id = _assign_request_id(scope)
        started = time.perf_counter()
        # 서버가 닫으면 그 코드, 클라이언트가 끊으면 받은 코드. 둘 다 없으면 1006(비정상 종료)이다.
        code = 1006

        async def receive_with_code() -> Message:
            nonlocal code
            message = await receive()
            if message["type"] == "websocket.disconnect":
                code = message.get("code", 1005)
            return message

        async def send_with_code(message: Message) -> None:
            nonlocal code
            if message["type"] == "websocket.close":
                code = message.get("code", 1000)
            await send(message)

        try:
            await self.app(scope, receive_with_code, send_with_code)
        except Exception as exc:
            code = 1011
            log.error("unhandled %s at %s request_id=%s", type(exc).__name__, _frames(exc), request_id)
        finally:
            ms = (time.perf_counter() - started) * 1000
            log.info("WS %s %d %.1fms request_id=%s", scope["path"], code, ms, request_id)


def _assign_request_id(scope: Scope) -> str:
    sent = dict(scope["headers"]).get(REQUEST_ID_HEADER.lower().encode(), b"").decode("latin-1")
    request_id = sent if _SAFE_ID.fullmatch(sent) else uuid.uuid4().hex
    scope.setdefault("state", {})["request_id"] = request_id
    return request_id


class _DropWebSocketLines(logging.Filter):
    """uvicorn은 WebSocket 연결마다 `"WebSocket <경로?쿼리>" [accepted]`를 uvicorn.error에 남긴다.
    쿼리에 채팅 토큰이 들어가고 클라이언트 주소도 붙으므로 버리고, 미들웨어의 `WS …` 한 줄로 대신한다."""

    def filter(self, record: logging.LogRecord) -> bool:
        return '"WebSocket ' not in str(record.msg)


def _setup_logging() -> None:
    # uvicorn 접근 로그는 쿼리 문자열과 클라이언트 주소를 남기므로 끄고 위 한 줄로 대신한다.
    logging.getLogger("uvicorn.access").disabled = True
    uvicorn_error = logging.getLogger("uvicorn.error")
    if not any(isinstance(f, _DropWebSocketLines) for f in uvicorn_error.filters):
        uvicorn_error.addFilter(_DropWebSocketLines())
    app_log = logging.getLogger("app")
    app_log.setLevel(logging.INFO)
    if not app_log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        app_log.addHandler(handler)


def install(app: FastAPI) -> None:
    """오류 처리기와 요청 id·접근 로그 미들웨어를 단다. CORS보다 먼저 불러 CORS 안쪽에 둔다(오류 응답에도 CORS 헤더가 붙게)."""
    _setup_logging()
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_middleware(RequestContextMiddleware)
