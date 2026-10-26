# 서버 시각. 규칙·템플릿은 결정적이고, 시각이 필요한 곳(createdAt, 운영 시간 외 판정, 나이)만 여기를 쓴다.
# 테스트에서 시각을 고정할 수 있도록 다른 모듈은 `clock.now()`로 부른다.

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

SEOUL = ZoneInfo("Asia/Seoul")


def now() -> datetime:
    return datetime.now(SEOUL)


def epoch_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def iso_utc(dt: datetime) -> str:
    """JS Date.toISOString()과 같은 형식(UTC, 밀리초, Z)."""
    u = dt.astimezone(UTC)
    return u.strftime("%Y-%m-%dT%H:%M:%S.") + f"{u.microsecond // 1000:03d}Z"


def parse_iso(s: str) -> datetime:
    """ISO 문자열을 시간대 있는 datetime으로 읽는다. 시간대가 없으면 Asia/Seoul로 본다."""
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=SEOUL)
