# 센터 사례 저장소. DB_PATH가 비면 메모리(재시작하면 mock 시드 상태로 돌아간다), 있으면 SQLite 파일(store_sqlite.py)이다.
# 어느 쪽이든 mock 사례·통계 레코드는 서버 시작 시 한 번 메모리에서 만들고, 근로자가 실제로 보낸 사례(live)와 상태 변경만 따로 둔다.

from collections.abc import Callable, Iterable
from datetime import datetime
from threading import Lock
from typing import Protocol

from app import clock
from app.data.mock import StatRecord, build_mock_cases, build_stat_records
from app.schemas import CaseStatus, CenterCase
from app.settings import settings


class CenterStore(Protocol):
    stat_records: list[StatRecord]

    def all(self) -> list[CenterCase]:
        """최신순 전체 목록(상태 변경 반영)."""
        ...

    def get(self, case_id: str) -> CenterCase | None: ...

    def add_live(self, at: datetime, make: Callable[[str], CenterCase]) -> CenterCase:
        """id를 정해 `make(id)`로 만든 사례를 맨 앞에 넣는다(id 규칙은 `next_case_id`)."""
        ...

    def set_status(self, case_id: str, status: CaseStatus) -> CenterCase | None: ...

    def reset(self) -> None:
        """데모 초기화: 실제 전송 사례와 상태 변경을 지운다. mock은 처음 상태로 돌아간다."""
        ...

    def close(self) -> None: ...


def next_case_id(at: datetime, taken: Iterable[str]) -> str:
    """`C-` + 접수 시각 밀리초 끝 5자리(프론트와 같음). 겹치면 뒤에 -2, -3…을 붙인다."""
    base = f"C-{str(clock.epoch_ms(at))[-5:]}"
    used = set(taken)
    case_id, n = base, 2
    while case_id in used:
        case_id, n = f"{base}-{n}", n + 1
    return case_id


def latest_first(cases: list[CenterCase]) -> list[CenterCase]:
    """접수 시각 최신순. 같은 시각이면 넘긴 순서(live 최신 → mock)를 지킨다."""
    return sorted(cases, key=lambda c: clock.parse_iso(c.created_at), reverse=True)


def with_status(c: CenterCase, status: CaseStatus | None) -> CenterCase:
    return c.model_copy(update={"status": status}) if status else c


class MemoryStore:
    def __init__(self, now: datetime | None = None) -> None:
        started = now or clock.now()
        self._lock = Lock()
        self._mock = build_mock_cases(started)
        self.stat_records: list[StatRecord] = build_stat_records(started)
        self._live: list[CenterCase] = []
        self._status: dict[str, CaseStatus] = {}

    def all(self) -> list[CenterCase]:
        with self._lock:
            cases = [with_status(c, self._status.get(c.id)) for c in [*self._live, *self._mock]]
        return latest_first(cases)

    def get(self, case_id: str) -> CenterCase | None:
        with self._lock:
            for c in [*self._live, *self._mock]:
                if c.id == case_id:
                    return with_status(c, self._status.get(c.id))
        return None

    def add_live(self, at: datetime, make: Callable[[str], CenterCase]) -> CenterCase:
        with self._lock:
            c = make(next_case_id(at, (c.id for c in [*self._live, *self._mock])))
            self._live.insert(0, c)
        return c

    def set_status(self, case_id: str, status: CaseStatus) -> CenterCase | None:
        if self.get(case_id) is None:
            return None
        with self._lock:
            self._status[case_id] = status
        return self.get(case_id)

    def reset(self) -> None:
        with self._lock:
            self._live.clear()
            self._status.clear()

    def close(self) -> None:
        pass


def open_store(db_path: str, now: datetime | None = None) -> CenterStore:
    if not db_path:
        return MemoryStore(now)
    from app.store_sqlite import SqliteStore

    return SqliteStore(db_path, now)


store: CenterStore = open_store(settings.db_path)
