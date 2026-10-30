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
    # 센터 사례 SQLite 파일. 빈 문자열이면 메모리 저장소(재시작하면 mock 시드 상태)
    db_path: str = ""
    # 모델 아티팩트 폴더(modeling/models). 빈 문자열이면 모델 없이 규칙·보조 점수로 동작한다
    model_dir: str = ""


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


def _db_path(raw: str) -> str:
    path = raw.strip()
    if path and not Path(path).parent.is_dir():
        raise ValueError(f"DB_PATH의 폴더가 없다: {raw!r}")
    return path


def _model_dir(raw: str) -> str:
    path = raw.strip()
    if path and not Path(path).is_dir():
        raise ValueError(f"MODEL_DIR는 있는 폴더여야 한다: {raw!r}")
    return path


def load_settings(env: Mapping[str, str] = os.environ) -> Settings:
    return Settings(
        center_hours=_center_hours(env.get("CENTER_HOURS", DEFAULT_CENTER_HOURS)),
        info_date=_info_date(env.get("INFO_DATE", DEFAULT_INFO_DATE)),
        cors_origins=_cors_origins(env.get("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)),
        llm_provider=_llm_provider(env.get("LLM_PROVIDER", DEFAULT_LLM_PROVIDER)),
        llm_model=_llm_model(env.get("LLM_MODEL", DEFAULT_LLM_MODEL)),
        llm_api_key=env.get("LLM_API_KEY", "").strip(),
        llm_timeout_s=_llm_timeout_s(env.get("LLM_TIMEOUT_S", str(DEFAULT_TIMEOUT_S))),
        llm_attempts=_llm_attempts(env.get("LLM_ATTEMPTS", str(DEFAULT_ATTEMPTS))),
        db_path=_db_path(env.get("DB_PATH", "")),
        model_dir=_model_dir(env.get("MODEL_DIR", "")),
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
