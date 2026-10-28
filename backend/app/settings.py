# 서버 설정값. 발표 전에 코드를 고치지 않고 바꿀 수 있도록 환경 변수에서 시작 시 한 번 읽는다.
# 불변 객체 하나만 두고, 값이 잘못되면 서버가 뜨지 않게 시작 시점에 거절한다.
# 뒤 항목(LLM, 모델, DB)도 여기에 필드를 더해 같은 방식으로 받는다.

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from app.schemas import CenterHours

# 센터 운영 시간. PRD Q1 미결: 확인 전까지 평일 09:00~18:00으로 가정한다.
DEFAULT_CENTER_HOURS = "09:00-18:00"
# 제도 정보 기준일. 실제 운영 시 담당자가 확인한 날짜로 바꾼다.
DEFAULT_INFO_DATE = "2026-10-24"
DEFAULT_CORS_ORIGINS = "http://localhost:5180"

# 요일 번호는 프론트(JS Date.getDay)와 같이 0=일요일 … 6=토요일. 운영일은 평일로 고정한다.
WEEKDAYS = [1, 2, 3, 4, 5]

_HOURS = re.compile(r"(\d{2}):00-(\d{2}):00")


@dataclass(frozen=True)
class Settings:
    center_hours: CenterHours
    info_date: str
    cors_origins: tuple[str, ...]


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


def load_settings(env: Mapping[str, str] = os.environ) -> Settings:
    return Settings(
        center_hours=_center_hours(env.get("CENTER_HOURS", DEFAULT_CENTER_HOURS)),
        info_date=_info_date(env.get("INFO_DATE", DEFAULT_INFO_DATE)),
        cors_origins=_cors_origins(env.get("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)),
    )


settings = load_settings()
