# 센터 사례 SQLite 저장소(backlog 07). DB_PATH가 있을 때 store.py가 고른다. 표준 라이브러리 sqlite3만 쓴다.
# 표는 넷이다. live_cases: 근로자가 보낸 사례 본문(JSON), case_status: mock·live 사례의 바뀐 상태,
# chat_tokens·chat_messages: 상담 채팅(backlog 14)의 근로자 토큰과 메시지.
# mock 사례·통계 레코드는 메모리 저장소와 같이 시작 시 메모리에서 만든다(시드 고정이라 id가 같다).
# 연락처·자유 입력·채팅 메시지가 평문으로 남는다(데모 범위, README "센터 저장소").

import sqlite3
from collections.abc import Callable
from datetime import datetime
from threading import Lock

from app import clock
from app.data.mock import StatRecord, build_mock_cases, build_stat_records
from app.schemas import CaseStatus, CenterCase, ChatMessage, ChatRole
from app.store import latest_first, make_message, next_case_id, with_status

SCHEMA = """
CREATE TABLE IF NOT EXISTS live_cases (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS case_status (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_tokens (
    case_id TEXT PRIMARY KEY,
    token TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    sender TEXT NOT NULL,
    text TEXT NOT NULL,
    at TEXT NOT NULL,
    PRIMARY KEY (case_id, id)
);
"""


class SqliteStore:
    def __init__(self, path: str, now: datetime | None = None) -> None:
        started = now or clock.now()
        self._lock = Lock()
        # FastAPI 동기 경로는 스레드 풀에서 돈다. 연결 하나를 잠금으로 나눠 쓴다(다중 프로세스 동시 쓰기는 범위 밖).
        self._db = sqlite3.connect(path, check_same_thread=False)
        with self._db:
            self._db.executescript(SCHEMA)
        self._mock = build_mock_cases(started)
        self.stat_records: list[StatRecord] = build_stat_records(started)

    def _live(self) -> list[CenterCase]:
        # 같은 접수 시각이면 나중에 넣은 것이 앞(메모리 저장소의 insert(0)과 같다).
        rows = self._db.execute("SELECT body FROM live_cases ORDER BY rowid DESC").fetchall()
        return [CenterCase.model_validate_json(body) for (body,) in rows]

    def _status(self) -> dict[str, CaseStatus]:
        return dict(self._db.execute("SELECT id, status FROM case_status").fetchall())

    def all(self) -> list[CenterCase]:
        with self._lock:
            status = self._status()
            cases = [with_status(c, status.get(c.id)) for c in [*self._live(), *self._mock]]
        return latest_first(cases)

    def get(self, case_id: str) -> CenterCase | None:
        with self._lock:
            row = self._db.execute("SELECT body FROM live_cases WHERE id = ?", (case_id,)).fetchone()
            c = CenterCase.model_validate_json(row[0]) if row else next((m for m in self._mock if m.id == case_id), None)
            if c is None:
                return None
            status = self._db.execute("SELECT status FROM case_status WHERE id = ?", (case_id,)).fetchone()
        return with_status(c, status[0] if status else None)

    def add_live(self, at: datetime, make: Callable[[str], CenterCase]) -> CenterCase:
        with self._lock:
            live_ids = [i for (i,) in self._db.execute("SELECT id FROM live_cases")]
            c = make(next_case_id(at, [*live_ids, *(m.id for m in self._mock)]))
            with self._db:
                self._db.execute(
                    "INSERT INTO live_cases (id, created_at, body) VALUES (?, ?, ?)",
                    (c.id, c.created_at, c.model_dump_json(by_alias=True)),
                )
        return c

    def set_status(self, case_id: str, status: CaseStatus) -> CenterCase | None:
        if self.get(case_id) is None:
            return None
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO case_status (id, status) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET status = excluded.status",
                (case_id, status),
            )
        return self.get(case_id)

    def set_chat_token(self, case_id: str, token: str) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO chat_tokens (case_id, token) VALUES (?, ?) ON CONFLICT(case_id) DO UPDATE SET token = excluded.token",
                (case_id, token),
            )

    def chat_token(self, case_id: str) -> str | None:
        with self._lock:
            row = self._db.execute("SELECT token FROM chat_tokens WHERE case_id = ?", (case_id,)).fetchone()
        return row[0] if row else None

    def add_message(self, case_id: str, sender: ChatRole, text: str, at: datetime) -> ChatMessage:
        with self._lock:
            (count,) = self._db.execute("SELECT COUNT(*) FROM chat_messages WHERE case_id = ?", (case_id,)).fetchone()
            m = make_message(case_id, count, sender, text, at)
            with self._db:
                self._db.execute(
                    "INSERT INTO chat_messages (id, case_id, sender, text, at) VALUES (?, ?, ?, ?, ?)",
                    (m.id, m.case_id, m.from_, m.text, m.at),
                )
        return m

    def messages(self, case_id: str) -> list[ChatMessage]:
        with self._lock:
            rows = self._db.execute(
                "SELECT id, sender, text, at FROM chat_messages WHERE case_id = ? ORDER BY rowid", (case_id,)
            ).fetchall()
        return [ChatMessage(id=i, case_id=case_id, from_=sender, text=text, at=at) for (i, sender, text, at) in rows]

    def reset(self) -> None:
        """네 표를 비운다. 파일은 지우지 않는다."""
        with self._lock, self._db:
            for table in ("live_cases", "case_status", "chat_tokens", "chat_messages"):
                self._db.execute(f"DELETE FROM {table}")

    def close(self) -> None:
        self._db.close()
