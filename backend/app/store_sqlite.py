# 센터 사례 SQLite 저장소(backlog 07). DB_PATH가 있을 때 store.py가 고른다. 표준 라이브러리 sqlite3만 쓴다.
# 사례 표는 다섯이다. live_cases: 근로자가 보낸 사례 본문(JSON), case_status: mock·live 사례의 바뀐 상태·분야·조치·연계 기관(분야 열부터는 frontend backlog 41, 옛 파일에는 열 때 더한다),
# chat_tokens·chat_messages: 상담 채팅(backlog 14)의 근로자 토큰과 메시지(번역 열은 backlog 30, 옛 파일에는 열 때 더한다). chat_reads: 역할별 읽은 자리(backlog 28). call_captions: 통화 자막(backlog 18, translation이 NULL이면 번역 전).
# 센터 직원 로그인(backlog 17) 표도 넷이다. center_staff: 직원 이메일, auth_code_requests: 보내기 제한용 요청 기록,
# auth_codes: 이메일별 코드 해시, center_sessions: 세션 토큰 해시. reset은 이 넷을 비우지 않는다.
# 근로자 Google 로그인(backlog 21)은 worker_sessions 하나다(세션 토큰 해시와 계정 키, 이름·이메일 없음). reset은 이것도 비우지 않는다.
# 근로자 앱 푸시(backlog 28)는 push_devices 하나다(사례 id·기기 토큰·플랫폼·notice·갱신 시각, 계정과 잇지 않는다). reset이 비운다.
# mock 사례·통계 레코드는 메모리 저장소와 같이 시작 시 메모리에서 만든다(시드 고정이라 id가 같다).
# 연락처·자유 입력·채팅 메시지·자막이 평문으로 남는다(데모 범위, README "센터 저장소").
# live_cases 본문은 저장할 때의 계약 그대로 남는다. 읽을 때 옛 계약을 지금 계약으로 바꾸고, 그래도 못 읽는 본문은 건너뛴다(backlog 29).

import json
import logging
import sqlite3
from collections.abc import Callable
from datetime import datetime
from threading import Lock
from typing import Any

from pydantic import ValidationError

from app import clock
from app.data.mock import StatRecord, build_mock_cases, build_stat_records
from app.rules.urgency import default_category
from app.schemas import Caption, CasePatch, CenterCase, ChatMessage, ChatRole, TranslationStatus
from app.store import (
    CODE_REQUEST_KEEP,
    PUSH_CASES_PER_DEVICE,
    PUSH_DEVICE_KEEP,
    PUSH_DEVICES_PER_CASE,
    AuthCode,
    MessageTranslation,
    PushDevice,
    apply_changes,
    caption_number,
    latest_first,
    make_message,
    next_case_id,
    oldest_over,
    read_ids,
)
from app.vocab import Lang

logger = logging.getLogger(__name__)

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
    lang TEXT,
    translated TEXT,
    translated_lang TEXT,
    translation TEXT,
    PRIMARY KEY (case_id, id)
);
CREATE TABLE IF NOT EXISTS chat_reads (
    case_id TEXT NOT NULL,
    role TEXT NOT NULL,
    n INTEGER NOT NULL,
    PRIMARY KEY (case_id, role)
);
CREATE TABLE IF NOT EXISTS call_captions (
    case_id TEXT NOT NULL,
    n INTEGER NOT NULL,
    sender TEXT NOT NULL,
    text TEXT NOT NULL,
    lang TEXT NOT NULL,
    translated TEXT,
    translated_lang TEXT NOT NULL,
    translation TEXT,
    at TEXT NOT NULL,
    PRIMARY KEY (case_id, n)
);
CREATE TABLE IF NOT EXISTS center_staff (
    email TEXT PRIMARY KEY,
    added_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS auth_code_requests (
    email TEXT NOT NULL,
    at TEXT NOT NULL,
    sent INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS auth_codes (
    email TEXT PRIMARY KEY,
    code_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    attempts INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS center_sessions (
    token_hash TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS worker_sessions (
    token_hash TEXT PRIMARY KEY,
    account TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS push_devices (
    case_id TEXT NOT NULL,
    device_token TEXT NOT NULL,
    platform TEXT NOT NULL,
    notice TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (case_id, device_token)
);
"""

CAPTION_SELECT = "SELECT n, sender, text, lang, translated, translated_lang, translation, at FROM call_captions"


def caption_row(row: tuple) -> Caption:
    n, sender, text, lang, translated, translated_lang, translation, at = row
    return Caption(
        id=f"c-{n}",
        from_=sender,
        text=text,
        lang=lang,
        translated=translated,
        translated_lang=translated_lang,
        translation=translation,
        at=at,
    )


def _case_from_body(body: str) -> CenterCase | None:
    """live_cases 본문 하나를 읽는다. 읽을 수 없으면 None이고, 본문은 로그에 남기지 않는다."""
    try:
        data = json.loads(body)
    except ValueError:
        data = None
    if not isinstance(data, dict):
        logger.warning("live case skipped id=None error=NotObject")
        return None
    # backlog 23 전 본문은 요청 종류가 하나(requestType)다. 한 칸 배열로 읽는다
    if "requestTypes" not in data and "requestType" in data:
        data["requestTypes"] = [data.pop("requestType")]
    # frontend backlog 41 전 본문에는 분야·조치가 없다. 분야는 접수 때와 같은 규칙으로, 조치·연계 기관은 []로 채운다
    if "category" not in data:
        request_types = data.get("requestTypes")
        data["category"] = default_category(data.get("coveragePath"), request_types if isinstance(request_types, list) else [])
    data.setdefault("actions", [])
    data.setdefault("referredTo", [])
    # frontend backlog 42 전 본문에는 국적이 없다
    data.setdefault("nationality", None)
    try:
        return CenterCase.model_validate(data)
    except ValidationError as exc:
        logger.warning("live case skipped id=%s error=%s", data.get("id"), type(exc).__name__)
        return None


# 채팅 번역(backlog 30)이 더한 열. 이 항목 전에 만든 DB 파일에는 없으므로 열 때 더한다(옛 메시지는 NULL).
CHAT_TRANSLATION_COLUMNS = ("lang", "translated", "translated_lang", "translation")
# 사례 분야·조치(frontend backlog 41)가 더한 열. 옛 파일의 행은 NULL이고 NULL은 "바꾸지 않음"이다. actions·referred_to는 JSON 배열
CASE_CHANGE_COLUMNS = ("category", "actions", "referred_to")


def _add_missing_columns(db: sqlite3.Connection, table: str, columns: tuple[str, ...]) -> None:
    have = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
    for column in columns:
        if column not in have:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")


class SqliteStore:
    def __init__(self, path: str, now: datetime | None = None) -> None:
        started = now or clock.now()
        self._lock = Lock()
        # FastAPI 동기 경로는 스레드 풀에서 돈다. 연결 하나를 잠금으로 나눠 쓴다(다중 프로세스 동시 쓰기는 범위 밖).
        self._db = sqlite3.connect(path, check_same_thread=False)
        with self._db:
            self._db.executescript(SCHEMA)
            _add_missing_columns(self._db, "chat_messages", CHAT_TRANSLATION_COLUMNS)
            _add_missing_columns(self._db, "case_status", CASE_CHANGE_COLUMNS)
        self._mock = build_mock_cases(started)
        self.stat_records: list[StatRecord] = build_stat_records(started)

    def _live(self) -> list[CenterCase]:
        # 같은 접수 시각이면 나중에 넣은 것이 앞(메모리 저장소의 insert(0)과 같다).
        rows = self._db.execute("SELECT body FROM live_cases ORDER BY rowid DESC").fetchall()
        # 사례 하나를 못 읽어도 접수함 전체가 500이 되지 않게 그 사례만 뺀다
        return [c for (body,) in rows if (c := _case_from_body(body)) is not None]

    def _changes(self, case_id: str | None = None) -> dict[str, dict[str, Any]]:
        """사례 id → 바꾼 필드. case_id를 주면 그 사례만 읽는다."""
        sql = "SELECT id, status, category, actions, referred_to FROM case_status"
        rows = self._db.execute(sql + " WHERE id = ?", (case_id,)) if case_id else self._db.execute(sql)
        return {
            i: {
                "status": status,
                "category": category,
                "actions": json.loads(actions) if actions else None,
                "referred_to": json.loads(referred_to) if referred_to else None,
            }
            for (i, status, category, actions, referred_to) in rows
        }

    def all(self) -> list[CenterCase]:
        with self._lock:
            changes = self._changes()
            cases = [apply_changes(c, changes.get(c.id)) for c in [*self._live(), *self._mock]]
        return latest_first(cases)

    def get(self, case_id: str) -> CenterCase | None:
        with self._lock:
            row = self._db.execute("SELECT body FROM live_cases WHERE id = ?", (case_id,)).fetchone()
            c = _case_from_body(row[0]) if row else next((m for m in self._mock if m.id == case_id), None)
            if c is None:
                return None
            changes = self._changes(case_id).get(case_id)
        return apply_changes(c, changes)

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

    def update_case(self, case_id: str, patch: CasePatch) -> CenterCase | None:
        c = self.get(case_id)
        if c is None:
            return None
        # status 열은 NOT NULL이라 행을 처음 만들 때 지금 상태를 함께 적는다. 보내지 않은 필드는 그대로 둔다(COALESCE)
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO case_status (id, status, category, actions, referred_to) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET status = COALESCE(?, status), category = COALESCE(?, category), "
                "actions = COALESCE(?, actions), referred_to = COALESCE(?, referred_to)",
                (
                    case_id,
                    patch.status or c.status,
                    patch.category,
                    None if patch.actions is None else json.dumps(patch.actions),
                    None if patch.referred_to is None else json.dumps(patch.referred_to),
                    patch.status,
                    patch.category,
                    None if patch.actions is None else json.dumps(patch.actions),
                    None if patch.referred_to is None else json.dumps(patch.referred_to),
                ),
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

    def add_message(
        self, case_id: str, sender: ChatRole, text: str, at: datetime, translation: MessageTranslation | None = None
    ) -> ChatMessage:
        with self._lock:
            (count,) = self._db.execute("SELECT COUNT(*) FROM chat_messages WHERE case_id = ?", (case_id,)).fetchone()
            m = make_message(case_id, count, sender, text, at, translation)
            with self._db:
                self._db.execute(
                    "INSERT INTO chat_messages (id, case_id, sender, text, at, lang, translated, translated_lang, translation)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (m.id, m.case_id, m.from_, m.text, m.at, m.lang, m.translated, m.translated_lang, m.translation),
                )
        return m

    def messages(self, case_id: str) -> list[ChatMessage]:
        with self._lock:
            rows = self._db.execute(
                "SELECT id, sender, text, at, lang, translated, translated_lang, translation FROM chat_messages WHERE case_id = ? ORDER BY rowid",
                (case_id,),
            ).fetchall()
        return [
            ChatMessage(
                id=i, case_id=case_id, from_=sender, text=text, at=at, lang=lang, translated=tr, translated_lang=tr_lang, translation=status
            )
            for (i, sender, text, at, lang, tr, tr_lang, status) in rows
        ]

    def mark_read(self, case_id: str, role: ChatRole, n: int) -> bool:
        with self._lock, self._db:
            cur = self._db.execute(
                "INSERT INTO chat_reads (case_id, role, n) VALUES (?, ?, ?) ON CONFLICT(case_id, role) DO UPDATE SET n = excluded.n WHERE excluded.n > chat_reads.n",
                (case_id, role, n),
            )
        return cur.rowcount > 0

    def read_marks(self, case_id: str) -> dict[ChatRole, str | None]:
        with self._lock:
            rows = self._db.execute("SELECT role, n FROM chat_reads WHERE case_id = ?", (case_id,)).fetchall()
        return read_ids(dict(rows))

    def center_message_summary(self, case_id: str) -> tuple[int, str | None]:
        with self._lock:
            count, last = self._db.execute(
                "SELECT COUNT(*), MAX(at) FROM chat_messages WHERE case_id = ? AND sender = 'center'", (case_id,)
            ).fetchone()
        return count, last

    def add_caption(self, case_id: str, sender: ChatRole, text: str, lang: Lang, translated_lang: Lang, at: datetime) -> str:
        with self._lock, self._db:
            (n,) = self._db.execute("SELECT COALESCE(MAX(n), 0) + 1 FROM call_captions WHERE case_id = ?", (case_id,)).fetchone()
            self._db.execute(
                "INSERT INTO call_captions (case_id, n, sender, text, lang, translated_lang, at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (case_id, n, sender, text, lang, translated_lang, clock.iso_utc(at)),
            )
        return f"c-{n}"

    def set_caption_translation(
        self, case_id: str, caption_id: str, translation: TranslationStatus, translated: str | None
    ) -> Caption | None:
        n = caption_number(caption_id)
        if n is None:
            return None
        with self._lock:
            with self._db:
                cur = self._db.execute(
                    "UPDATE call_captions SET translation = ?, translated = ? WHERE case_id = ? AND n = ? AND translation IS NULL",
                    (translation, translated, case_id, n),
                )
            if cur.rowcount != 1:
                return None
            row = self._db.execute(f"{CAPTION_SELECT} WHERE case_id = ? AND n = ?", (case_id, n)).fetchone()
        return caption_row(row)

    def captions(self, case_id: str) -> list[Caption]:
        with self._lock:
            rows = self._db.execute(f"{CAPTION_SELECT} WHERE case_id = ? AND translation IS NOT NULL ORDER BY n", (case_id,)).fetchall()
        return [caption_row(r) for r in rows]

    def is_staff(self, email: str) -> bool:
        with self._lock:
            return self._db.execute("SELECT 1 FROM center_staff WHERE email = ?", (email,)).fetchone() is not None

    def add_staff(self, email: str, at: datetime) -> bool:
        with self._lock, self._db:
            cur = self._db.execute("INSERT OR IGNORE INTO center_staff (email, added_at) VALUES (?, ?)", (email, clock.iso_utc(at)))
        return cur.rowcount == 1

    def remove_staff(self, email: str) -> bool:
        with self._lock, self._db:
            cur = self._db.execute("DELETE FROM center_staff WHERE email = ?", (email,))
            self._db.execute("DELETE FROM auth_codes WHERE email = ?", (email,))
            self._db.execute("DELETE FROM center_sessions WHERE email = ?", (email,))
        return cur.rowcount == 1

    def list_staff(self) -> list[str]:
        with self._lock:
            return [e for (e,) in self._db.execute("SELECT email FROM center_staff ORDER BY email")]

    def add_code_request(self, email: str, at: datetime, sent: bool) -> None:
        with self._lock, self._db:
            self._db.execute("DELETE FROM auth_code_requests WHERE at <= ?", (clock.iso_utc(at - CODE_REQUEST_KEEP),))
            self._db.execute("INSERT INTO auth_code_requests (email, at, sent) VALUES (?, ?, ?)", (email, clock.iso_utc(at), int(sent)))

    def code_requests(self, email: str, since: datetime) -> int:
        with self._lock:
            (n,) = self._db.execute(
                "SELECT COUNT(*) FROM auth_code_requests WHERE email = ? AND at > ?", (email, clock.iso_utc(since))
            ).fetchone()
        return n

    def sent_codes(self, since: datetime) -> int:
        with self._lock:
            (n,) = self._db.execute("SELECT COUNT(*) FROM auth_code_requests WHERE sent = 1 AND at > ?", (clock.iso_utc(since),)).fetchone()
        return n

    def set_code(self, email: str, code_hash: str, expires_at: datetime) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO auth_codes (email, code_hash, expires_at, attempts) VALUES (?, ?, ?, 0) "
                "ON CONFLICT(email) DO UPDATE SET code_hash = excluded.code_hash, expires_at = excluded.expires_at, attempts = 0",
                (email, code_hash, clock.iso_utc(expires_at)),
            )

    def get_code(self, email: str) -> AuthCode | None:
        with self._lock:
            row = self._db.execute("SELECT code_hash, expires_at, attempts FROM auth_codes WHERE email = ?", (email,)).fetchone()
        return AuthCode(*row) if row else None

    def add_code_attempt(self, email: str) -> int:
        with self._lock, self._db:
            self._db.execute("UPDATE auth_codes SET attempts = attempts + 1 WHERE email = ?", (email,))
            row = self._db.execute("SELECT attempts FROM auth_codes WHERE email = ?", (email,)).fetchone()
        return row[0] if row else 0

    def delete_code(self, email: str) -> None:
        with self._lock, self._db:
            self._db.execute("DELETE FROM auth_codes WHERE email = ?", (email,))

    def add_session(self, token_hash: str, email: str, created_at: datetime, expires_at: datetime) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO center_sessions (token_hash, email, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (token_hash, email, clock.iso_utc(created_at), clock.iso_utc(expires_at)),
            )

    def session_email(self, token_hash: str, now: datetime) -> str | None:
        with self._lock:
            row = self._db.execute(
                "SELECT email FROM center_sessions WHERE token_hash = ? AND expires_at > ?", (token_hash, clock.iso_utc(now))
            ).fetchone()
        return row[0] if row else None

    def delete_session(self, token_hash: str) -> None:
        with self._lock, self._db:
            self._db.execute("DELETE FROM center_sessions WHERE token_hash = ?", (token_hash,))

    def add_worker_session(self, token_hash: str, account: str, created_at: datetime, expires_at: datetime) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO worker_sessions (token_hash, account, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (token_hash, account, clock.iso_utc(created_at), clock.iso_utc(expires_at)),
            )

    def worker_account(self, token_hash: str, now: datetime) -> str | None:
        with self._lock:
            row = self._db.execute(
                "SELECT account FROM worker_sessions WHERE token_hash = ? AND expires_at > ?", (token_hash, clock.iso_utc(now))
            ).fetchone()
        return row[0] if row else None

    def delete_worker_session(self, token_hash: str) -> None:
        with self._lock, self._db:
            self._db.execute("DELETE FROM worker_sessions WHERE token_hash = ?", (token_hash,))

    def _push_rows(self, where: str, arg: str) -> list[PushDevice]:
        rows = self._db.execute(
            f"SELECT case_id, device_token, platform, notice, updated_at FROM push_devices WHERE {where} = ? ORDER BY rowid", (arg,)
        ).fetchall()
        return [PushDevice(*r) for r in rows]

    def add_push_device(self, case_id: str, device_token: str, platform: str, notice: str, at: datetime) -> None:
        with self._lock, self._db:
            self._db.execute("DELETE FROM push_devices WHERE updated_at <= ?", (clock.iso_utc(at - PUSH_DEVICE_KEEP),))
            # REPLACE는 지우고 다시 넣어 rowid가 끝으로 간다(메모리 저장소의 넣은 순서와 같다)
            self._db.execute(
                "INSERT OR REPLACE INTO push_devices (case_id, device_token, platform, notice, updated_at) VALUES (?, ?, ?, ?, ?)",
                (case_id, device_token, platform, notice, clock.iso_utc(at)),
            )
            for where, arg, limit in (("device_token", device_token, PUSH_CASES_PER_DEVICE), ("case_id", case_id, PUSH_DEVICES_PER_CASE)):
                for d in oldest_over(self._push_rows(where, arg), limit):
                    self._db.execute("DELETE FROM push_devices WHERE case_id = ? AND device_token = ?", (d.case_id, d.device_token))

    def push_devices(self, case_id: str, now: datetime) -> list[PushDevice]:
        with self._lock:
            with self._db:
                self._db.execute("DELETE FROM push_devices WHERE updated_at <= ?", (clock.iso_utc(now - PUSH_DEVICE_KEEP),))
            return self._push_rows("case_id", case_id)

    def remove_push_device(self, device_token: str) -> None:
        with self._lock, self._db:
            self._db.execute("DELETE FROM push_devices WHERE device_token = ?", (device_token,))

    def reset(self) -> None:
        """사례 표 여섯과 푸시 기기 묶음을 비운다. 직원·로그인 표와 파일은 그대로 둔다."""
        with self._lock, self._db:
            for table in ("live_cases", "case_status", "chat_tokens", "chat_messages", "chat_reads", "call_captions", "push_devices"):
                self._db.execute(f"DELETE FROM {table}")

    def close(self) -> None:
        self._db.close()
