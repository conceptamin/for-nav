# 센터 직원 로그인(backlog 17). 직원 이메일은 저장소에 두고, 메일로 보낸 6자리 코드가 맞으면 세션 쿠키를 준다.
# 근로자 Google 로그인(backlog 21). ID 토큰 검증(app/google_id.py)이 돌려준 sub에서 계정 키를 만들고 근로자 세션 쿠키를 준다.
# 코드와 세션 토큰은 sha256 해시만 저장한다. 이메일·코드·토큰·sub·계정 키는 로그에 남기지 않는다.
# 경로(routers/auth.py, routers/center.py)는 이 함수들을 부르고 응답만 만든다.

import hashlib
import re
import secrets
from datetime import datetime, timedelta

from fastapi import Response

from app import clock
from app.mail import Mailer
from app.schemas import EMAIL_MAX_LEN, EMAIL_PATTERN
from app.store import CenterStore

COOKIE = "fornav_center"
WORKER_COOKIE = "fornav_worker"
# 계정 키 = sha256(접두어 + sub)의 앞 32자. 접두어는 다른 서비스가 같은 sub로 만든 해시와 맞춰 보지 못하게 붙인다
ACCOUNT_PREFIX = "fornav-worker:"
ACCOUNT_LEN = 32
CODE_TTL = timedelta(minutes=10)
CODE_MAX_ATTEMPTS = 5
# 보내기 제한. 이메일별 제한은 등록되지 않은 이메일에도 똑같이 건다(429로 등록 여부를 떠보지 못하게).
RESEND_AFTER = timedelta(seconds=60)
PER_EMAIL_WINDOW = timedelta(hours=1)
PER_EMAIL_MAX = 5
# 서버 전체 제한은 실제로 보낸 메일만 센다(메일 무료 한도 보호). 등록되지 않은 이메일 요청으로 직원 로그인을 막지 못하게 한다.
GLOBAL_WINDOW = timedelta(minutes=10)
GLOBAL_MAX = 30

MAIL_SUBJECT = "for-nav 센터 로그인 코드"


class RateLimitedError(Exception):
    """코드 요청이 보내기 제한을 넘었다."""


def normalize_email(raw: str) -> str:
    return raw.strip().lower()


def valid_email(email: str) -> bool:
    """직원 등록 명령줄(scripts/staff.py)이 쓴다. 경로는 스키마(StaffEmail)가 같은 모양으로 검사한다."""
    return len(email) <= EMAIL_MAX_LEN and re.fullmatch(EMAIL_PATTERN, email) is not None


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_code() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def mail_text(code: str) -> str:
    return f"로그인 코드: {code}\n\n10분 동안 유효합니다. 요청하지 않았다면 이 메일을 무시하세요."


def check_rate(store: CenterStore, email: str, registered: bool, now: datetime) -> None:
    if store.code_requests(email, now - RESEND_AFTER) > 0 or store.code_requests(email, now - PER_EMAIL_WINDOW) >= PER_EMAIL_MAX:
        raise RateLimitedError
    if registered and store.sent_codes(now - GLOBAL_WINDOW) >= GLOBAL_MAX:
        raise RateLimitedError


async def request_code(store: CenterStore, mailer: Mailer, email: str, now: datetime) -> None:
    """등록된 직원이면 새 코드를 만들어 메일로 보낸다(이전 코드는 무효). 등록되지 않은 이메일은 기록만 하고 보내지 않는다.

    제한을 넘으면 RateLimitedError, 메일 발송이 실패하면 MailError를 올린다.
    """
    email = normalize_email(email)
    registered = store.is_staff(email)
    check_rate(store, email, registered, now)
    store.add_code_request(email, now, sent=registered)
    if not registered:
        return
    code = new_code()
    store.set_code(email, hash_secret(code), now + CODE_TTL)
    await mailer.send(email, MAIL_SUBJECT, mail_text(code))


def verify_code(store: CenterStore, email: str, code: str, now: datetime, session_days: int) -> str | None:
    """코드가 맞으면 새 세션 토큰(쿠키 값)을 돌려준다. 틀림·만료·없음은 모두 None이다(이유를 나누지 않는다).

    맞든 틀리든 CODE_MAX_ATTEMPTS번 틀린 코드는 지우고, 맞은 코드도 한 번 쓰면 지운다.
    """
    email = normalize_email(email)
    saved = store.get_code(email)
    if saved is None:
        return None
    if saved.expires_at <= clock.iso_utc(now):
        store.delete_code(email)
        return None
    if not secrets.compare_digest(saved.code_hash, hash_secret(code.strip())):
        if store.add_code_attempt(email) >= CODE_MAX_ATTEMPTS:
            store.delete_code(email)
        return None
    store.delete_code(email)
    # 코드를 받은 뒤 직원 목록에서 빠졌으면 세션을 주지 않는다.
    if not store.is_staff(email):
        return None
    token = secrets.token_urlsafe(32)
    store.add_session(hash_secret(token), email, now, now + timedelta(days=session_days))
    return token


def session_email(store: CenterStore, token: str | None, now: datetime) -> str | None:
    """쿠키 값으로 로그인한 직원 이메일을 찾는다. 쿠키가 없거나 세션이 끝났으면 None."""
    if not token:
        return None
    return store.session_email(hash_secret(token), now)


def end_session(store: CenterStore, token: str | None) -> None:
    if token:
        store.delete_session(hash_secret(token))


def account_key(sub: str) -> str:
    """Google sub에서 근로자 계정 키를 만든다. 같은 sub면 늘 같고, sub 원문으로 되돌릴 수 없다."""
    return hash_secret(ACCOUNT_PREFIX + sub)[:ACCOUNT_LEN]


def start_worker_session(store: CenterStore, sub: str, now: datetime, session_days: int) -> tuple[str, str]:
    """검증한 sub로 새 근로자 세션을 만든다. (세션 토큰(쿠키 값), 계정 키)를 돌려준다. sub 원문은 저장하지 않는다."""
    account = account_key(sub)
    token = secrets.token_urlsafe(32)
    store.add_worker_session(hash_secret(token), account, now, now + timedelta(days=session_days))
    return token, account


def worker_account(store: CenterStore, token: str | None, now: datetime) -> str | None:
    """쿠키 값으로 로그인한 근로자 계정 키를 찾는다. 쿠키가 없거나 세션이 끝났으면 None."""
    if not token:
        return None
    return store.worker_account(hash_secret(token), now)


def end_worker_session(store: CenterStore, token: str | None) -> None:
    if token:
        store.delete_worker_session(hash_secret(token))


def set_session_cookie(response: Response, token: str, days: int, secure: bool, name: str = COOKIE) -> None:
    response.set_cookie(name, token, max_age=days * 24 * 60 * 60, path="/", secure=secure, httponly=True, samesite="lax")


def clear_session_cookie(response: Response, secure: bool, name: str = COOKIE) -> None:
    response.delete_cookie(name, path="/", secure=secure, httponly=True, samesite="lax")
