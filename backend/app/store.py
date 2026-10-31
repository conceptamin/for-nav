# 센터 사례 저장소. DB_PATH가 비면 메모리(재시작하면 mock 시드 상태로 돌아간다), 있으면 SQLite 파일(store_sqlite.py)이다.
# 어느 쪽이든 mock 사례·통계 레코드는 서버 시작 시 한 번 메모리에서 만들고, 근로자가 실제로 보낸 사례(live)와 상태 변경만 따로 둔다.
# 상담 채팅(backlog 14)의 근로자 토큰과 메시지, 통화 자막(backlog 18), 센터 직원 로그인(backlog 17)의 직원 목록·코드·세션,
# 근로자 Google 로그인(backlog 21)의 세션(계정 키만, 이름·이메일 없음), 근로자 앱 푸시 기기 토큰(backlog 28, 사례에만 묶는다)도 같은 저장소에 둔다.
# 로그인 코드와 세션 토큰은 해시만 받는다(app/auth.py가 만든다). 시각은 iso_utc 문자열로 두어 문자열 비교가 시각 비교가 된다.

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from threading import Lock
from typing import Protocol

from app import clock
from app.data.mock import StatRecord, build_mock_cases, build_stat_records
from app.schemas import Caption, CaseStatus, CenterCase, ChatMessage, ChatRole, TranslationStatus
from app.settings import settings
from app.vocab import Lang

# 코드 요청 기록은 보내기 제한(app/auth.py)이 보는 가장 긴 구간만큼만 남긴다.
CODE_REQUEST_KEEP = timedelta(hours=1)
# 푸시 기기 묶음(backlog 28)은 마지막 등록 뒤 이만큼만 남긴다. 앱을 열 때마다 웹이 다시 등록하므로 쓰는 기기는 계속 남는다
PUSH_DEVICE_KEEP = timedelta(days=30)
# 기기 하나에 묶는 사례 수, 사례 하나에 묶는 기기 수. 넘으면 가장 오래 갱신하지 않은 묶음을 지운다
PUSH_CASES_PER_DEVICE = 20
PUSH_DEVICES_PER_CASE = 5


@dataclass(frozen=True)
class AuthCode:
    """직원 이메일 하나에 하나뿐인 로그인 코드. 새 코드를 넣으면 이전 코드를 덮는다."""

    code_hash: str
    expires_at: str
    attempts: int = 0


@dataclass(frozen=True)
class PushDevice:
    """사례 하나에 묶인 기기 하나(backlog 28). 계정·세션과 잇지 않는다."""

    case_id: str
    device_token: str
    platform: str
    notice: str
    updated_at: str


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

    def set_chat_token(self, case_id: str, token: str) -> None: ...

    def chat_token(self, case_id: str) -> str | None:
        """근로자 채팅 토큰. mock 사례에는 없다."""
        ...

    def add_message(self, case_id: str, sender: ChatRole, text: str, at: datetime) -> ChatMessage:
        """사례 채팅 끝에 메시지를 더한다(id 규칙은 `make_message`)."""
        ...

    def messages(self, case_id: str) -> list[ChatMessage]:
        """보낸 순서대로."""
        ...

    # 상담 채팅 읽음(backlog 28). 역할마다 사례 안 메시지 번호 하나(어디까지 읽었나)만 둔다.
    def mark_read(self, case_id: str, role: ChatRole, n: int) -> bool:
        """역할의 읽은 자리를 n으로 옮긴다. 이미 n 이상이면 그대로 두고 False."""
        ...

    def read_marks(self, case_id: str) -> dict[ChatRole, str | None]:
        """역할별 마지막으로 읽은 메시지 id. 읽은 것이 없으면 None."""
        ...

    def center_message_summary(self, case_id: str) -> tuple[int, str | None]:
        """센터가 보낸 메시지 수와 마지막 시각(backlog 27)."""
        ...

    # 통화 자막(backlog 18). 받자마자 번역 전 상태로 넣고, 번역이 끝나면 채운다.
    def add_caption(self, case_id: str, sender: ChatRole, text: str, lang: Lang, translated_lang: Lang, at: datetime) -> str:
        """받은 순서대로 사례 안 번호를 정해 `c-<n>`을 돌려준다."""
        ...

    def set_caption_translation(
        self, case_id: str, caption_id: str, translation: TranslationStatus, translated: str | None
    ) -> Caption | None:
        """번역 전 자막을 채운다. 그런 자막이 없으면(데모 초기화로 지워졌거나 이미 채웠으면) None."""
        ...

    def captions(self, case_id: str) -> list[Caption]:
        """번역이 끝난 자막만 번호 순서대로."""
        ...

    # 센터 직원 로그인(backlog 17). 이메일은 app/auth.py가 소문자로 맞춰 넘긴다.
    def is_staff(self, email: str) -> bool: ...

    def add_staff(self, email: str, at: datetime) -> bool:
        """새로 더했으면 True, 이미 있으면 False."""
        ...

    def remove_staff(self, email: str) -> bool:
        """그 직원의 코드와 세션도 지운다. 없던 이메일이면 False."""
        ...

    def list_staff(self) -> list[str]:
        """이메일 순."""
        ...

    def add_code_request(self, email: str, at: datetime, sent: bool) -> None:
        """코드 요청 한 번(등록되지 않은 이메일 포함)을 남긴다. `sent`는 실제로 메일을 보냈는지. CODE_REQUEST_KEEP보다 오래된 기록은 지운다."""
        ...

    def code_requests(self, email: str, since: datetime) -> int:
        """그 이메일로 `since` 뒤에 받은 코드 요청 수."""
        ...

    def sent_codes(self, since: datetime) -> int:
        """서버 전체에서 `since` 뒤에 실제로 보낸 메일 수."""
        ...

    def set_code(self, email: str, code_hash: str, expires_at: datetime) -> None: ...

    def get_code(self, email: str) -> AuthCode | None: ...

    def add_code_attempt(self, email: str) -> int:
        """틀린 시도를 하나 올리고 지금까지의 수를 돌려준다. 코드가 없으면 0."""
        ...

    def delete_code(self, email: str) -> None: ...

    def add_session(self, token_hash: str, email: str, created_at: datetime, expires_at: datetime) -> None: ...

    def session_email(self, token_hash: str, now: datetime) -> str | None:
        """만료되지 않은 세션의 직원 이메일."""
        ...

    def delete_session(self, token_hash: str) -> None: ...

    # 근로자 Google 로그인(backlog 21). 계정 키는 app/auth.py가 sub에서 만든다.
    def add_worker_session(self, token_hash: str, account: str, created_at: datetime, expires_at: datetime) -> None: ...

    def worker_account(self, token_hash: str, now: datetime) -> str | None:
        """만료되지 않은 근로자 세션의 계정 키."""
        ...

    def delete_worker_session(self, token_hash: str) -> None: ...

    # 근로자 앱 푸시(backlog 28). 저장하는 것은 (사례 id, 기기 토큰, 플랫폼, notice, 갱신 시각)뿐이다.
    def add_push_device(self, case_id: str, device_token: str, platform: str, notice: str, at: datetime) -> None:
        """기기를 사례에 묶는다. 이미 있으면 platform·notice·갱신 시각만 바꾼다.
        PUSH_DEVICE_KEEP보다 오래된 묶음을 먼저 지우고, 기기·사례별 상한을 넘으면 가장 오래 갱신하지 않은 묶음을 지운다."""
        ...

    def push_devices(self, case_id: str, now: datetime) -> list[PushDevice]:
        """그 사례에 묶인 기기. PUSH_DEVICE_KEEP보다 오래된 묶음은 지운 뒤 돌려준다."""
        ...

    def remove_push_device(self, device_token: str) -> None:
        """그 기기의 묶음을 모두 지운다. 없으면 아무것도 하지 않는다."""
        ...

    def reset(self) -> None:
        """데모 초기화: 실제 전송 사례, 상태 변경, 채팅 토큰·메시지·읽음, 통화 자막, 푸시 기기 묶음을 지운다. mock은 처음 상태로 돌아간다.
        직원 목록·로그인 코드·세션과 근로자 세션은 그대로 둔다(초기화한 직원과 근로자가 로그아웃되지 않게)."""
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


def make_message(case_id: str, count: int, sender: ChatRole, text: str, at: datetime) -> ChatMessage:
    """`count`는 그 사례에 이미 있는 메시지 수다. id는 사례 안에서 m-1, m-2…로 늘어난다."""
    return ChatMessage(id=f"m-{count + 1}", case_id=case_id, from_=sender, text=text, at=clock.iso_utc(at))


def message_number(message_id: str) -> int | None:
    """`m-<n>`의 n. 형식이 다르면 None."""
    prefix, _, n = message_id.partition("-")
    return int(n) if prefix == "m" and n.isdecimal() else None


def read_ids(marks: dict[ChatRole, int]) -> dict[ChatRole, str | None]:
    return {role: (f"m-{marks[role]}" if role in marks else None) for role in ("worker", "center")}


def oldest_over(rows: list[PushDevice], limit: int) -> list[PushDevice]:
    """상한을 넘는 만큼 가장 오래 갱신하지 않은 묶음. rows는 넣은 순서(같은 시각이면 앞이 오래된 것)다."""
    return sorted(rows, key=lambda d: d.updated_at)[: max(0, len(rows) - limit)]


def caption_number(caption_id: str) -> int | None:
    """`c-<n>`의 n. 형식이 다르면 None."""
    prefix, _, n = caption_id.partition("-")
    return int(n) if prefix == "c" and n.isdecimal() else None


class MemoryStore:
    def __init__(self, now: datetime | None = None) -> None:
        started = now or clock.now()
        self._lock = Lock()
        self._mock = build_mock_cases(started)
        self.stat_records: list[StatRecord] = build_stat_records(started)
        self._live: list[CenterCase] = []
        self._status: dict[str, CaseStatus] = {}
        self._tokens: dict[str, str] = {}
        self._messages: dict[str, list[ChatMessage]] = {}
        self._reads: dict[str, dict[ChatRole, int]] = {}
        # 사례별 자막과 번역이 끝났는지. 번역 전 자막의 translation 값은 자리만 채운 것이다.
        self._captions: dict[str, list[tuple[Caption, bool]]] = {}
        self._staff: set[str] = set()
        self._code_requests: list[tuple[str, str, bool]] = []
        self._codes: dict[str, AuthCode] = {}
        self._sessions: dict[str, tuple[str, str]] = {}
        self._worker_sessions: dict[str, tuple[str, str]] = {}
        # (사례 id, 기기 토큰) → 묶음. 갱신하면 끝으로 옮겨 넣은 순서가 갱신 순서다
        self._push: dict[tuple[str, str], PushDevice] = {}

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

    def set_chat_token(self, case_id: str, token: str) -> None:
        with self._lock:
            self._tokens[case_id] = token

    def chat_token(self, case_id: str) -> str | None:
        with self._lock:
            return self._tokens.get(case_id)

    def add_message(self, case_id: str, sender: ChatRole, text: str, at: datetime) -> ChatMessage:
        with self._lock:
            msgs = self._messages.setdefault(case_id, [])
            m = make_message(case_id, len(msgs), sender, text, at)
            msgs.append(m)
        return m

    def messages(self, case_id: str) -> list[ChatMessage]:
        with self._lock:
            return list(self._messages.get(case_id, []))

    def mark_read(self, case_id: str, role: ChatRole, n: int) -> bool:
        with self._lock:
            marks = self._reads.setdefault(case_id, {})
            if marks.get(role, 0) >= n:
                return False
            marks[role] = n
        return True

    def read_marks(self, case_id: str) -> dict[ChatRole, str | None]:
        with self._lock:
            return read_ids(self._reads.get(case_id, {}))

    def center_message_summary(self, case_id: str) -> tuple[int, str | None]:
        mine = [m for m in self.messages(case_id) if m.from_ == "center"]
        return len(mine), (mine[-1].at if mine else None)

    def add_caption(self, case_id: str, sender: ChatRole, text: str, lang: Lang, translated_lang: Lang, at: datetime) -> str:
        with self._lock:
            rows = self._captions.setdefault(case_id, [])
            c = Caption(
                id=f"c-{len(rows) + 1}",
                from_=sender,
                text=text,
                lang=lang,
                translated=None,
                translated_lang=translated_lang,
                translation="skipped",
                at=clock.iso_utc(at),
            )
            rows.append((c, False))
        return c.id

    def set_caption_translation(
        self, case_id: str, caption_id: str, translation: TranslationStatus, translated: str | None
    ) -> Caption | None:
        n = caption_number(caption_id)
        with self._lock:
            rows = self._captions.get(case_id, [])
            if n is None or not 0 < n <= len(rows) or rows[n - 1][1]:
                return None
            c = rows[n - 1][0].model_copy(update={"translation": translation, "translated": translated})
            rows[n - 1] = (c, True)
        return c

    def captions(self, case_id: str) -> list[Caption]:
        with self._lock:
            return [c for c, done in self._captions.get(case_id, []) if done]

    def is_staff(self, email: str) -> bool:
        with self._lock:
            return email in self._staff

    def add_staff(self, email: str, at: datetime) -> bool:
        with self._lock:
            added = email not in self._staff
            self._staff.add(email)
        return added

    def remove_staff(self, email: str) -> bool:
        with self._lock:
            if email not in self._staff:
                return False
            self._staff.discard(email)
            self._codes.pop(email, None)
            self._sessions = {h: s for h, s in self._sessions.items() if s[0] != email}
        return True

    def list_staff(self) -> list[str]:
        with self._lock:
            return sorted(self._staff)

    def add_code_request(self, email: str, at: datetime, sent: bool) -> None:
        keep_after = clock.iso_utc(at - CODE_REQUEST_KEEP)
        with self._lock:
            self._code_requests = [r for r in self._code_requests if r[1] > keep_after]
            self._code_requests.append((email, clock.iso_utc(at), sent))

    def code_requests(self, email: str, since: datetime) -> int:
        after = clock.iso_utc(since)
        with self._lock:
            return sum(1 for e, at, _ in self._code_requests if e == email and at > after)

    def sent_codes(self, since: datetime) -> int:
        after = clock.iso_utc(since)
        with self._lock:
            return sum(1 for _, at, sent in self._code_requests if sent and at > after)

    def set_code(self, email: str, code_hash: str, expires_at: datetime) -> None:
        with self._lock:
            self._codes[email] = AuthCode(code_hash, clock.iso_utc(expires_at))

    def get_code(self, email: str) -> AuthCode | None:
        with self._lock:
            return self._codes.get(email)

    def add_code_attempt(self, email: str) -> int:
        with self._lock:
            code = self._codes.get(email)
            if code is None:
                return 0
            self._codes[email] = replace(code, attempts=code.attempts + 1)
            return code.attempts + 1

    def delete_code(self, email: str) -> None:
        with self._lock:
            self._codes.pop(email, None)

    def add_session(self, token_hash: str, email: str, created_at: datetime, expires_at: datetime) -> None:
        with self._lock:
            self._sessions[token_hash] = (email, clock.iso_utc(expires_at))

    def session_email(self, token_hash: str, now: datetime) -> str | None:
        with self._lock:
            s = self._sessions.get(token_hash)
        return s[0] if s and s[1] > clock.iso_utc(now) else None

    def delete_session(self, token_hash: str) -> None:
        with self._lock:
            self._sessions.pop(token_hash, None)

    def add_worker_session(self, token_hash: str, account: str, created_at: datetime, expires_at: datetime) -> None:
        with self._lock:
            self._worker_sessions[token_hash] = (account, clock.iso_utc(expires_at))

    def worker_account(self, token_hash: str, now: datetime) -> str | None:
        with self._lock:
            s = self._worker_sessions.get(token_hash)
        return s[0] if s and s[1] > clock.iso_utc(now) else None

    def delete_worker_session(self, token_hash: str) -> None:
        with self._lock:
            self._worker_sessions.pop(token_hash, None)

    def _prune_push(self, now: datetime) -> None:
        keep_after = clock.iso_utc(now - PUSH_DEVICE_KEEP)
        self._push = {k: d for k, d in self._push.items() if d.updated_at > keep_after}

    def add_push_device(self, case_id: str, device_token: str, platform: str, notice: str, at: datetime) -> None:
        with self._lock:
            self._prune_push(at)
            self._push.pop((case_id, device_token), None)
            self._push[(case_id, device_token)] = PushDevice(case_id, device_token, platform, notice, clock.iso_utc(at))
            for rows, limit in (
                ([d for d in self._push.values() if d.device_token == device_token], PUSH_CASES_PER_DEVICE),
                ([d for d in self._push.values() if d.case_id == case_id], PUSH_DEVICES_PER_CASE),
            ):
                for d in oldest_over(rows, limit):
                    del self._push[(d.case_id, d.device_token)]

    def push_devices(self, case_id: str, now: datetime) -> list[PushDevice]:
        with self._lock:
            self._prune_push(now)
            return [d for d in self._push.values() if d.case_id == case_id]

    def remove_push_device(self, device_token: str) -> None:
        with self._lock:
            self._push = {k: d for k, d in self._push.items() if d.device_token != device_token}

    def reset(self) -> None:
        with self._lock:
            self._live.clear()
            self._status.clear()
            self._tokens.clear()
            self._messages.clear()
            self._reads.clear()
            self._captions.clear()
            self._push.clear()

    def close(self) -> None:
        pass


def open_store(db_path: str, now: datetime | None = None) -> CenterStore:
    if not db_path:
        return MemoryStore(now)
    from app.store_sqlite import SqliteStore

    return SqliteStore(db_path, now)


store: CenterStore = open_store(settings.db_path)
