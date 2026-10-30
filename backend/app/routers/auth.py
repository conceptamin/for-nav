# 센터 직원 로그인 경로(backlog 17). 코드 만들기·확인·세션은 app/auth.py가 하고 여기서는 응답과 쿠키만 만든다.
# CENTER_AUTH=off이면 /me만 응답하고(required: false) 나머지는 404다.

import logging

from fastapi import APIRouter, HTTPException, Request, Response, status

from app import auth, clock
from app.mail import Mailer, MailError
from app.schemas import AuthCodeIn, AuthMe, AuthVerifyIn
from app.settings import settings
from app.store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth")


def _require_enabled() -> None:
    if settings.center_auth != "email":
        raise HTTPException(status_code=404, detail="센터 로그인을 쓰지 않는다")


@router.get("/me")
def me(request: Request) -> AuthMe:
    """센터 화면이 들어올 때 부른다. 세션이 없어도 401이 아니라 `email: null`이다."""
    if settings.center_auth != "email":
        return AuthMe(required=False, email=None)
    return AuthMe(required=True, email=auth.session_email(store, request.cookies.get(auth.COOKIE), clock.now()))


@router.post("/code", status_code=status.HTTP_202_ACCEPTED)
async def request_code(body: AuthCodeIn, request: Request) -> Response:
    """등록된 직원이면 코드를 메일로 보낸다. 등록 여부와 관계없이 같은 202다."""
    _require_enabled()
    mailer: Mailer = request.app.state.mail
    try:
        await auth.request_code(store, mailer, body.email, clock.now())
    except auth.RateLimitedError:
        raise HTTPException(status_code=429, detail="요청이 너무 많다. 잠시 뒤 다시 시도한다") from None
    except MailError as e:
        # 실패를 응답으로 알리면 등록된 이메일인지 드러나므로 202를 그대로 주고 기록만 남긴다(받는 사람은 남기지 않는다).
        logger.warning("로그인 코드 메일 실패 %s request_id=%s", e, request.state.request_id)
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post("/verify")
def verify(body: AuthVerifyIn, response: Response) -> AuthMe:
    _require_enabled()
    token = auth.verify_code(store, body.email, body.code, clock.now(), settings.center_session_days)
    if token is None:
        raise HTTPException(status_code=401, detail="코드가 맞지 않거나 만료되었다")
    auth.set_session_cookie(response, token, settings.center_session_days, settings.center_cookie_secure)
    return AuthMe(required=True, email=body.email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> Response:
    """세션을 지우고 쿠키를 비운다. 세션이 없어도 204다."""
    auth.end_session(store, request.cookies.get(auth.COOKIE))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    auth.clear_session_cookie(response, settings.center_cookie_secure)
    return response
