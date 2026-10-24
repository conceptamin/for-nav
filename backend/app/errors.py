"""공통 오류 응답. 계약 1장의 `{"error": {"code", "message", "request_id"}}` 형식을 따른다.

`message`는 개발자용 한국어 고정 문구다. 요청 값·예외 메시지·검증 상세를 담지 않는다.
"""

from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from app.llm import LLMUnavailableError


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorBody


_HTTP_ERRORS: dict[int, tuple[str, str]] = {
    400: ("BAD_REQUEST", "요청 형식이 올바르지 않습니다."),
    404: ("NOT_FOUND", "없는 경로입니다."),
    405: ("METHOD_NOT_ALLOWED", "허용하지 않는 메서드입니다."),
}
_OTHER_HTTP_ERROR = ("HTTP_ERROR", "요청을 처리할 수 없습니다.")
VALIDATION_ERROR = ("VALIDATION_ERROR", "입력 검증에 실패했습니다.")
LLM_UNAVAILABLE = ("LLM_UNAVAILABLE", "LLM 응답을 받지 못했습니다.")
INTERNAL_ERROR = ("INTERNAL_ERROR", "서버 내부 오류입니다.")


def request_id_of(request: Request) -> str:
    # RequestContextMiddleware가 넣는다. 미들웨어 밖에서 만든 요청이면 빈 값 대신 표식을 둔다.
    return str(getattr(request.state, "request_id", "req-unknown"))


def error_response(
    status_code: int,
    error: tuple[str, str],
    request_id: str,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    code, message = error
    body = ErrorResponse(error=ErrorBody(code=code, message=message, request_id=request_id))
    return JSONResponse(body.model_dump(), status_code=status_code, headers=headers)


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    error = _HTTP_ERRORS.get(exc.status_code, _OTHER_HTTP_ERROR)
    # 405의 Allow처럼 프레임워크가 붙인 헤더는 유지한다.
    return error_response(exc.status_code, error, request_id_of(request), exc.headers)


async def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    # FastAPI 기본 422 본문은 입력값(`input`)을 되돌려 보내므로 쓰지 않는다.
    return error_response(422, VALIDATION_ERROR, request_id_of(request))


async def _llm_unavailable(request: Request, exc: Exception) -> JSONResponse:
    return error_response(503, LLM_UNAVAILABLE, request_id_of(request))


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(LLMUnavailableError, _llm_unavailable)
