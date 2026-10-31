# 센터 직원 로그인 경로(backlog 17). 코드 만들기·확인·세션은 app/auth.py가 하고 여기서는 응답과 쿠키만 만든다.
# CENTER_AUTH=off이면 /me만 응답하고(required: false) 나머지는 404다.
# 근로자 Google 로그인 경로(backlog 21)는 /auth/worker/* 이다. WORKER_AUTH=off이면 /worker/me만 응답하고 /worker/google은 404다.

import logging

from fastapi import APIRouter, HTTPException, Request, Response, status

from app import auth, clock
from app.google_id import GoogleIdError, TokenVerifier
from app.mail import Mailer, MailError
from app.schemas import AuthCodeIn, AuthMe, AuthVerifyIn, WorkerGoogleIn, WorkerMe
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


# ---------------------------------------------------------------------------
# 근로자 Google 로그인(backlog 21)
# ---------------------------------------------------------------------------
@router.get("/worker/me")
def worker_me(request: Request) -> WorkerMe:
    """근로자 화면이 들어올 때 부른다. 세션이 없어도 401이 아니라 `account: null`이다."""
    if settings.worker_auth != "google":
        return WorkerMe(required=False, account=None)
    return WorkerMe(required=True, account=auth.worker_account(store, request.cookies.get(auth.WORKER_COOKIE), clock.now()))


@router.post("/worker/google")
def worker_google(body: WorkerGoogleIn, request: Request, response: Response) -> WorkerMe:
    """ID 토큰을 검증하고 근로자 세션 쿠키를 준다. 공개 키를 받는 네트워크 호출이 있어 동기 경로(스레드 풀)로 둔다."""
    if settings.worker_auth != "google":
        raise HTTPException(status_code=404, detail="근로자 로그인을 쓰지 않는다")
    verifier: TokenVerifier = request.app.state.google_id
    try:
        sub = verifier.verify(body.credential)
    except GoogleIdError as e:
        # 실패 종류(예외 이름)와 request id만 남긴다. 토큰은 남기지 않는다.
        logger.warning("Google 로그인 확인 실패 %s request_id=%s", e, request.state.request_id)
        raise HTTPException(status_code=401, detail="Google 로그인을 확인하지 못했다") from None
    token, account = auth.start_worker_session(store, sub, clock.now(), settings.worker_session_days)
    auth.set_session_cookie(response, token, settings.worker_session_days, settings.center_cookie_secure, name=auth.WORKER_COOKIE)
    return WorkerMe(required=True, account=account)


@router.post("/worker/logout", status_code=status.HTTP_204_NO_CONTENT)
def worker_logout(request: Request) -> Response:
    """근로자 세션을 지우고 쿠키를 비운다. 세션이 없어도 204다."""
    auth.end_worker_session(store, request.cookies.get(auth.WORKER_COOKIE))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    auth.clear_session_cookie(response, settings.center_cookie_secure, name=auth.WORKER_COOKIE)
    return response
