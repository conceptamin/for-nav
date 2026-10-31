# 서버 설정값. 발표 전에 코드를 고치지 않고 바꿀 수 있도록 환경 변수에서 시작 시 한 번 읽는다.
# 불변 객체 하나만 두고, 값이 잘못되면 서버가 뜨지 않게 시작 시점에 거절한다.
# 뒤 항목도 여기에 필드를 더해 같은 방식으로 받는다.

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from app.llm import DEFAULT_ATTEMPTS, DEFAULT_TIMEOUT_S, LLMClient
from app.llm_providers.anthropic import AnthropicClient
from app.schemas import CenterHours

# 센터 운영 시간. PRD Q1 미결: 확인 전까지 평일 09:00~18:00으로 가정한다.
DEFAULT_CENTER_HOURS = "09:00-18:00"
# 제도 정보 기준일. 실제 운영 시 담당자가 확인한 날짜로 바꾼다.
DEFAULT_INFO_DATE = "2026-10-24"
DEFAULT_CORS_ORIGINS = "http://localhost:5180"
# LLM 공급자는 하나만 지원한다. 모델은 짧은 추출·슬롯 채우기·번역용으로 빠르고 싼 쪽을 기본으로 둔다.
LLM_PROVIDERS = ("anthropic",)
DEFAULT_LLM_PROVIDER = "anthropic"
DEFAULT_LLM_MODEL = "claude-haiku-5-5"

# 센터 직원 로그인(backlog 17). off면 센터 경로가 로그인 없이 열린다(로컬 개발·테스트 기본값)
CENTER_AUTH_MODES = ("off", "email")
# 로그인 코드 메일. console은 로컬 개발 전용(코드를 표준 출력에 찍는다)
MAIL_PROVIDERS = ("resend", "console")
DEFAULT_CENTER_SESSION_DAYS = 30

# 요일 번호는 프론트(JS Date.getDay)와 같이 0=일요일 … 6=토요일. 운영일은 평일로 고정한다.
WEEKDAYS = [1, 2, 3, 4, 5]

_HOURS = re.compile(r"(\d{2}):00-(\d{2}):00")


@dataclass(frozen=True)
class Settings:
    center_hours: CenterHours
    info_date: str
    cors_origins: tuple[str, ...]
    llm_provider: str = DEFAULT_LLM_PROVIDER
    llm_model: str = DEFAULT_LLM_MODEL
    # 빈 문자열이면 LLM을 쓰지 않는다. repr·로그에 키가 찍히지 않게 repr에서 뺀다.
    llm_api_key: str = field(default="", repr=False)
    llm_timeout_s: float = DEFAULT_TIMEOUT_S
    llm_attempts: int = DEFAULT_ATTEMPTS
    # LLM 호출 제한(backlog 20). 0이면 그 제한을 끈다. 넘으면 LLM 없이 대체 동작으로 응답한다
    llm_rate_per_min: int = 0
    llm_daily_limit: int = 0
    # 클라이언트 IP를 담은 헤더(소문자, 예: cf-connecting-ip). TCP 상대가 루프백(터널)일 때만 믿는다. 빈 값이면 상대 주소
    llm_client_ip_header: str = ""
    # 센터 사례 SQLite 파일. 빈 문자열이면 메모리 저장소(재시작하면 mock 시드 상태)
    db_path: str = ""

    # 프론트 빌드 폴더(frontend/dist). 빈 문자열이면 정적 파일을 서빙하지 않는다(API만)
    static_dir: str = ""
    # 모델 아티팩트 폴더(modeling/models). 빈 문자열이면 모델 없이 규칙·보조 점수로 동작한다
    model_dir: str = ""

    # 센터 직원 로그인(backlog 17). email이면 센터 경로가 직원 세션을 확인한다
    center_auth: str = "off"
    mail_provider: str = "resend"
    # 메일 공급자 키. LLM 키처럼 repr·로그에 찍히지 않게 뺀다
    mail_api_key: str = field(default="", repr=False)
    # 보내는 사람, 예: `for-nav 센터 <no-reply@for-nav.com>`
    mail_from: str = ""
    center_session_days: int = DEFAULT_CENTER_SESSION_DAYS
    # 세션 쿠키의 Secure. 로컬 http 개발에서만 false로 둔다
    center_cookie_secure: bool = True


def _center_hours(raw: str) -> CenterHours:
    # 프론트 CenterHours는 시 단위만 있으므로 분은 00만 받는다.
    m = _HOURS.fullmatch(raw.strip())
    if not m:
        raise ValueError(f"CENTER_HOURS는 HH:00-HH:00 형식이어야 한다: {raw!r}")
    open_hour, close_hour = int(m[1]), int(m[2])
    if not 0 <= open_hour < close_hour <= 24:
        raise ValueError(f"CENTER_HOURS는 0 ≤ 시작 < 끝 ≤ 24여야 한다: {raw!r}")
    return CenterHours(open_hour=open_hour, close_hour=close_hour, workdays=WEEKDAYS)


def _info_date(raw: str) -> str:
    try:
        return date.fromisoformat(raw.strip()).isoformat()
    except ValueError:
        raise ValueError(f"INFO_DATE는 YYYY-MM-DD 형식이어야 한다: {raw!r}") from None


def _cors_origins(raw: str) -> tuple[str, ...]:
    return tuple(o.strip() for o in raw.split(",") if o.strip())


def _llm_provider(raw: str) -> str:
    provider = raw.strip()
    if provider not in LLM_PROVIDERS:
        raise ValueError(f"LLM_PROVIDER는 {', '.join(LLM_PROVIDERS)} 중 하나여야 한다: {raw!r}")
    return provider


def _llm_model(raw: str) -> str:
    if not raw.strip():
        raise ValueError("LLM_MODEL이 비어 있다")
    return raw.strip()


def _llm_timeout_s(raw: str) -> float:
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"LLM_TIMEOUT_S는 초 단위 숫자여야 한다: {raw!r}") from None
    if not value > 0:
        raise ValueError(f"LLM_TIMEOUT_S는 0보다 커야 한다: {raw!r}")
    return value


def _llm_attempts(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"LLM_ATTEMPTS는 정수여야 한다: {raw!r}") from None
    if value < 1:
        raise ValueError(f"LLM_ATTEMPTS는 1 이상이어야 한다: {raw!r}")
    return value


def _limit(name: str, raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{name}는 정수여야 한다: {raw!r}") from None
    if value < 0:
        raise ValueError(f"{name}는 0 이상이어야 한다(0이면 끈다): {raw!r}")
    return value


def _db_path(raw: str) -> str:
    path = raw.strip()
    if path and not Path(path).parent.is_dir():
        raise ValueError(f"DB_PATH의 폴더가 없다: {raw!r}")
    return path


def _static_dir(raw: str) -> str:
    path = raw.strip()
    if path and not (Path(path) / "index.html").is_file():
        raise ValueError(f"STATIC_DIR에 index.html이 없다(프론트를 먼저 빌드한다): {raw!r}")
    return path


def _model_dir(raw: str) -> str:
    path = raw.strip()
    if path and not Path(path).is_dir():
        raise ValueError(f"MODEL_DIR는 있는 폴더여야 한다: {raw!r}")
    return path


def _choice(name: str, raw: str, choices: tuple[str, ...]) -> str:
    value = raw.strip()
    if value not in choices:
        raise ValueError(f"{name}는 {', '.join(choices)} 중 하나여야 한다: {raw!r}")
    return value


def _session_days(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"CENTER_SESSION_DAYS는 정수여야 한다: {raw!r}") from None
    if value < 1:
        raise ValueError(f"CENTER_SESSION_DAYS는 1 이상이어야 한다: {raw!r}")
    return value


def _bool(name: str, raw: str) -> bool:
    value = raw.strip().lower()
    if value not in ("true", "false"):
        raise ValueError(f"{name}는 true 또는 false여야 한다: {raw!r}")
    return value == "true"


def _check_center_auth(s: Settings) -> Settings:
    """센터 로그인을 켰을 때 함께 있어야 하는 값. 하나라도 빠지면 서버가 뜨지 않는다."""
    if s.center_auth != "email":
        return s
    if not s.db_path:
        raise ValueError("CENTER_AUTH=email이면 DB_PATH가 있어야 한다(직원 목록·세션을 SQLite에 둔다)")
    if s.mail_provider == "resend" and not (s.mail_api_key and s.mail_from):
        raise ValueError("MAIL_PROVIDER=resend이면 MAIL_API_KEY와 MAIL_FROM이 있어야 한다")
    # console은 코드를 표준 출력에 찍으므로 운영(Secure 쿠키)에서 켜지지 않게 한다
    if s.mail_provider == "console" and s.center_cookie_secure:
        raise ValueError("MAIL_PROVIDER=console은 CENTER_COOKIE_SECURE=false(로컬 http 개발)일 때만 쓴다")
    return s


def load_settings(env: Mapping[str, str] = os.environ) -> Settings:
    return _check_center_auth(
        Settings(
            center_hours=_center_hours(env.get("CENTER_HOURS", DEFAULT_CENTER_HOURS)),
            info_date=_info_date(env.get("INFO_DATE", DEFAULT_INFO_DATE)),
            cors_origins=_cors_origins(env.get("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)),
            llm_provider=_llm_provider(env.get("LLM_PROVIDER", DEFAULT_LLM_PROVIDER)),
            llm_model=_llm_model(env.get("LLM_MODEL", DEFAULT_LLM_MODEL)),
            llm_api_key=env.get("LLM_API_KEY", "").strip(),
            llm_timeout_s=_llm_timeout_s(env.get("LLM_TIMEOUT_S", str(DEFAULT_TIMEOUT_S))),
            llm_attempts=_llm_attempts(env.get("LLM_ATTEMPTS", str(DEFAULT_ATTEMPTS))),
            llm_rate_per_min=_limit("LLM_RATE_PER_MIN", env.get("LLM_RATE_PER_MIN", "0")),
            llm_daily_limit=_limit("LLM_DAILY_LIMIT", env.get("LLM_DAILY_LIMIT", "0")),
            llm_client_ip_header=env.get("LLM_CLIENT_IP_HEADER", "").strip().lower(),
            db_path=_db_path(env.get("DB_PATH", "")),
            static_dir=_static_dir(env.get("STATIC_DIR", "")),
            model_dir=_model_dir(env.get("MODEL_DIR", "")),
            center_auth=_choice("CENTER_AUTH", env.get("CENTER_AUTH", "off"), CENTER_AUTH_MODES),
            mail_provider=_choice("MAIL_PROVIDER", env.get("MAIL_PROVIDER", "resend"), MAIL_PROVIDERS),
            mail_api_key=env.get("MAIL_API_KEY", "").strip(),
            mail_from=env.get("MAIL_FROM", "").strip(),
            center_session_days=_session_days(env.get("CENTER_SESSION_DAYS", str(DEFAULT_CENTER_SESSION_DAYS))),
            center_cookie_secure=_bool("CENTER_COOKIE_SECURE", env.get("CENTER_COOKIE_SECURE", "true")),
        )
    )


settings = load_settings()


def get_llm_client(s: Settings | None = None) -> LLMClient | None:
    """키가 비면 None이다. 부르는 쪽은 None이면 LLM 자리를 건너뛰고 기본 템플릿·규칙으로 동작한다(발표장 네트워크 대비).

    부를 때마다 새 클라이언트를 만든다. 서버에서는 시작 시 한 번 만들어 두고 종료 시 닫는다.
    """
    s = s or settings
    if not s.llm_api_key:
        return None
    return AnthropicClient(api_key=s.llm_api_key, model=s.llm_model)
