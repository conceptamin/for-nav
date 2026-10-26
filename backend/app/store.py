# 센터 사례 메모리 저장소. 목업이므로 재시작하면 mock 시드 상태로 돌아간다.
# mock 사례는 서버 시작 시 한 번만 만들고, 근로자가 실제로 보낸 사례(live)와 상태 변경만 따로 둔다.

from collections.abc import Callable
from datetime import datetime
from threading import Lock

from app import clock
from app.data.mock import StatRecord, build_mock_cases, build_stat_records
from app.schemas import CaseStatus, CenterCase


class CenterStore:
    def __init__(self, now: datetime | None = None) -> None:
        started = now or clock.now()
        self._lock = Lock()
        self._mock = build_mock_cases(started)
        self.stat_records: list[StatRecord] = build_stat_records(started)
        self._live: list[CenterCase] = []
        self._status: dict[str, CaseStatus] = {}

    def _with_status(self, c: CenterCase) -> CenterCase:
        s = self._status.get(c.id)
        return c.model_copy(update={"status": s}) if s else c

    def all(self) -> list[CenterCase]:
        """최신순 전체 목록(상태 변경 반영)."""
        with self._lock:
            cases = [self._with_status(c) for c in [*self._live, *self._mock]]
        return sorted(cases, key=lambda c: clock.parse_iso(c.created_at), reverse=True)

    def get(self, case_id: str) -> CenterCase | None:
        with self._lock:
            for c in [*self._live, *self._mock]:
                if c.id == case_id:
                    return self._with_status(c)
        return None

    def add_live(self, at: datetime, make: Callable[[str], CenterCase]) -> CenterCase:
        """id를 정해 `make(id)`로 만든 사례를 맨 앞에 넣는다.
        id는 `C-` + 접수 시각 밀리초 끝 5자리(프론트와 같음)이고, 겹치면 뒤에 -2, -3…을 붙인다."""
        base = f"C-{str(clock.epoch_ms(at))[-5:]}"
        with self._lock:
            taken = {c.id for c in [*self._live, *self._mock]}
            case_id, n = base, 2
            while case_id in taken:
                case_id, n = f"{base}-{n}", n + 1
            c = make(case_id)
            self._live.insert(0, c)
        return c

    def set_status(self, case_id: str, status: CaseStatus) -> CenterCase | None:
        if self.get(case_id) is None:
            return None
        with self._lock:
            self._status[case_id] = status
        return self.get(case_id)

    def reset(self) -> None:
        """데모 초기화: 실제 전송 사례와 상태 변경을 지운다. mock은 처음 상태로 돌아간다."""
        with self._lock:
            self._live.clear()
            self._status.clear()


store = CenterStore()
