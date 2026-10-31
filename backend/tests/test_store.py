# 센터 저장소(backlog 07): 메모리·SQLite 두 구현에 같은 테스트를 돌리고, SQLite는 재시작 뒤에도 남는지 본다.
# 상담 채팅의 토큰·메시지(backlog 14)와 통화 자막(backlog 18)도 같은 방식으로 본다.

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app import clock
from app.schemas import CenterCase
from app.settings import load_settings
from app.store import CenterStore, MemoryStore, MessageTranslation, open_store
from app.store_sqlite import SqliteStore

STARTED = datetime(2026, 10, 26, 12, 0, 0, tzinfo=clock.SEOUL)
AT = datetime(2026, 10, 26, 13, 0, 0, 123000, tzinfo=clock.SEOUL)


@pytest.fixture(params=["memory", "sqlite"])
def store(request, tmp_path: Path):
    s: CenterStore = MemoryStore(STARTED) if request.param == "memory" else SqliteStore(str(tmp_path / "center.db"), STARTED)
    yield s
    s.close()


def live_case(store: CenterStore, at: datetime = AT, contact: str = "010-0000-0000") -> CenterCase:
    template = store.get("C-1001")
    assert template is not None

    def make(case_id: str) -> CenterCase:
        return template.model_copy(update={"id": case_id, "created_at": clock.iso_utc(at), "live": True, "contact": contact})

    return store.add_live(at, make)


def test_mock_cases_and_stats(store: CenterStore):
    cases = store.all()
    assert {c.id for c in cases} == {f"C-{n}" for n in range(1001, 1025)}
    assert [c.created_at for c in cases] == sorted((c.created_at for c in cases), reverse=True)
    assert len(store.stat_records) == 420


def test_add_live_goes_first_and_round_trips(store: CenterStore):
    c = live_case(store)

    assert c.id == f"C-{str(clock.epoch_ms(AT))[-5:]}"
    assert store.all()[0] == c
    assert store.get(c.id) == c


def test_same_millisecond_ids_get_suffix(store: CenterStore):
    first, second, third = (live_case(store) for _ in range(3))

    assert (second.id, third.id) == (f"{first.id}-2", f"{first.id}-3")
    # 같은 시각이면 나중에 넣은 것이 앞이다.
    assert [c.id for c in store.all()[:3]] == [third.id, second.id, first.id]


def test_set_status_on_mock_and_live(store: CenterStore):
    c = live_case(store)

    assert store.set_status("C-1024", "done").status == "done"
    assert store.set_status(c.id, "progress").status == "progress"
    assert store.set_status(c.id, "done").status == "done"
    assert {x.id: x.status for x in store.all()}[c.id] == "done"
    assert store.set_status("C-0", "done") is None
    assert store.get("C-0") is None


def test_reset_clears_live_and_status(store: CenterStore):
    live_case(store)
    store.set_status("C-1024", "done")
    store.reset()

    cases = store.all()
    assert len(cases) == 24
    assert all(c.status == MemoryStore(STARTED).get(c.id).status for c in cases)


def test_chat_messages_per_case_in_order(store: CenterStore):
    first = store.add_message("C-1001", "worker", "하나", AT)
    store.add_message("C-1002", "center", "다른 방", AT)
    store.add_message("C-1001", "center", "둘", AT)

    # 번역을 넘기지 않으면 번역 필드는 None이다(backlog 30 전에 저장된 메시지와 같다).
    no_translation = {"lang": None, "translated": None, "translatedLang": None, "translation": None}
    assert first.model_dump(by_alias=True) == {
        "id": "m-1",
        "caseId": "C-1001",
        "from": "worker",
        "text": "하나",
        **no_translation,
        "at": clock.iso_utc(AT),
    }
    assert [(m.id, m.from_, m.text) for m in store.messages("C-1001")] == [("m-1", "worker", "하나"), ("m-2", "center", "둘")]
    assert [m.id for m in store.messages("C-1002")] == ["m-1"]
    assert store.messages("C-0") == []


def test_chat_message_keeps_translation(store: CenterStore):
    ok = store.add_message("C-1001", "worker", "Tay tôi đau", AT, MessageTranslation("vi", "ko", "ok", "손이 아파요"))
    store.add_message("C-1001", "center", "괜찮으세요?", AT, MessageTranslation("ko", "vi", "skipped"))

    assert (ok.lang, ok.translated, ok.translated_lang, ok.translation) == ("vi", "손이 아파요", "ko", "ok")
    assert [(m.lang, m.translated, m.translated_lang, m.translation) for m in store.messages("C-1001")] == [
        ("vi", "손이 아파요", "ko", "ok"),
        ("ko", None, "vi", "skipped"),
    ]


def test_sqlite_adds_translation_columns_to_old_file(tmp_path: Path):
    """backlog 30 전에 만든 DB 파일(chat_messages에 번역 열 없음)을 열면 열이 더해지고 옛 메시지는 번역 필드가 None이다."""
    path = str(tmp_path / "center.db")
    db = sqlite3.connect(path)
    with db:
        db.execute(
            "CREATE TABLE chat_messages (id TEXT NOT NULL, case_id TEXT NOT NULL, sender TEXT NOT NULL, text TEXT NOT NULL, at TEXT NOT NULL, PRIMARY KEY (case_id, id))"
        )
        db.execute("INSERT INTO chat_messages VALUES ('m-1', 'C-1001', 'worker', '하나', ?)", (clock.iso_utc(AT),))
    db.close()

    store = SqliteStore(path, STARTED)
    try:
        [old] = store.messages("C-1001")
        assert (old.id, old.text, old.lang, old.translated, old.translated_lang, old.translation) == ("m-1", "하나", None, None, None, None)
        new = store.add_message("C-1001", "center", "둘", AT, MessageTranslation("ko", "vi", "ok", "hai"))
        assert new.id == "m-2"
        assert store.messages("C-1001")[1] == new
    finally:
        store.close()
    # 두 번째로 열 때는 이미 열이 있다
    SqliteStore(path, STARTED).close()


def test_chat_token(store: CenterStore):
    c = live_case(store)
    assert store.chat_token(c.id) is None
    store.set_chat_token(c.id, "t-1")
    assert store.chat_token(c.id) == "t-1"
    assert store.chat_token("C-1001") is None


def test_reset_clears_chat(store: CenterStore):
    c = live_case(store)
    store.set_chat_token(c.id, "t-1")
    store.add_message("C-1001", "center", "x", AT)
    store.reset()

    assert store.chat_token(c.id) is None
    assert store.messages("C-1001") == []
    assert store.add_message("C-1001", "center", "y", AT).id == "m-1"


def test_sqlite_chat_survives_restart(tmp_path: Path):
    path = str(tmp_path / "center.db")
    first = SqliteStore(path, STARTED)
    c = live_case(first)
    first.set_chat_token(c.id, "t-1")
    sent = [first.add_message(c.id, "worker", "하나", AT), first.add_message(c.id, "center", "둘", AT)]
    first.close()

    second = SqliteStore(path, STARTED)
    try:
        assert second.chat_token(c.id) == "t-1"
        assert second.messages(c.id) == sent
        assert second.add_message(c.id, "worker", "셋", AT).id == "m-3"
    finally:
        second.close()


def test_sqlite_survives_restart(tmp_path: Path):
    path = str(tmp_path / "center.db")
    first = SqliteStore(path, STARTED)
    c = live_case(first)
    first.set_status(c.id, "progress")
    first.set_status("C-1024", "done")
    first.close()

    # 재시작: 시작 시각이 달라도 mock id는 같고, live 사례와 상태가 남는다.
    second = SqliteStore(path, datetime(2026, 10, 27, 9, 0, tzinfo=clock.SEOUL))
    try:
        assert second.get(c.id) == c.model_copy(update={"status": "progress"})
        assert second.get("C-1024").status == "done"
        assert len(second.all()) == 25
    finally:
        second.close()


def test_sqlite_opens_old_cases_with_emergency_flag(tmp_path: Path):
    # backlog 26 전에 저장한 사례 본문에는 emergencyFlag가 있다. 읽을 때 버린다.
    import json
    import sqlite3

    path = str(tmp_path / "center.db")
    first = SqliteStore(path, STARTED)
    c = live_case(first)
    first.close()
    db = sqlite3.connect(path)
    db.execute("UPDATE live_cases SET body = ? WHERE id = ?", (json.dumps({**c.model_dump(by_alias=True), "emergencyFlag": True}), c.id))
    db.commit()
    db.close()

    second = SqliteStore(path, STARTED)
    try:
        assert second.get(c.id) == c
        assert len(second.all()) == 25
    finally:
        second.close()


def _rewrite_body(path: str, case_id: str, body: str) -> None:
    import sqlite3

    db = sqlite3.connect(path)
    db.execute("UPDATE live_cases SET body = ? WHERE id = ?", (body, case_id))
    db.commit()
    db.close()


def test_sqlite_opens_old_cases_with_single_request_type(tmp_path: Path):
    # backlog 23 전에 저장한 사례 본문은 requestType 하나다. 한 칸 배열로 읽는다(backlog 29).
    import json

    path = str(tmp_path / "center.db")
    first = SqliteStore(path, STARTED)
    c = live_case(first)
    first.close()
    old = {k: v for k, v in c.model_dump(by_alias=True).items() if k != "requestTypes"}
    _rewrite_body(path, c.id, json.dumps({**old, "requestType": c.request_types[0]}))

    second = SqliteStore(path, STARTED)
    try:
        assert second.get(c.id) == c.model_copy(update={"request_types": c.request_types[:1]})
        assert len(second.all()) == 25
    finally:
        second.close()


@pytest.mark.parametrize("body", ["{not json", "[]", '{"id": "C-9999", "summaryKo": "읽지 못할 본문"}'])
def test_sqlite_skips_unreadable_case(tmp_path: Path, caplog: pytest.LogCaptureFixture, body: str):
    # 본문 하나를 못 읽어도 접수함 전체가 500이 되지 않는다. 그 사례만 빠지고 본문은 로그에 남지 않는다(backlog 29).
    path = str(tmp_path / "center.db")
    first = SqliteStore(path, STARTED)
    c = live_case(first)
    kept = live_case(first, AT + timedelta(minutes=1))
    first.close()
    _rewrite_body(path, c.id, body)

    second = SqliteStore(path, STARTED)
    try:
        cases = second.all()
        assert len(cases) == 25
        assert kept in cases
        assert second.get(c.id) is None
    finally:
        second.close()
    assert "live case skipped" in caplog.text
    assert "읽지 못할 본문" not in caplog.text


def test_sqlite_reset_keeps_file(tmp_path: Path):
    path = tmp_path / "center.db"
    s = SqliteStore(str(path), STARTED)
    live_case(s)
    s.reset()
    s.close()

    assert path.exists()
    reopened = SqliteStore(str(path), STARTED)
    try:
        assert len(reopened.all()) == 24
    finally:
        reopened.close()


def test_open_store_picks_by_db_path(tmp_path: Path):
    assert isinstance(open_store("", STARTED), MemoryStore)
    s = open_store(str(tmp_path / "center.db"), STARTED)
    try:
        assert isinstance(s, SqliteStore)
    finally:
        s.close()


def test_db_path_folder_must_exist(tmp_path: Path):
    assert load_settings({"DB_PATH": str(tmp_path / "center.db")}).db_path == str(tmp_path / "center.db")
    with pytest.raises(ValueError, match="DB_PATH"):
        load_settings({"DB_PATH": str(tmp_path / "nope" / "center.db")})


# ---------------------------------------------------------------------------
# 통화 자막(backlog 18): 사례별 번호, 번역 전 자막 빼기, 초기화, SQLite 재시작
# ---------------------------------------------------------------------------
def add_caption(store: CenterStore, case_id: str = "C-1001", text: str = "Tay tôi") -> str:
    return store.add_caption(case_id, "worker", text, "vi", "ko", AT)


def test_caption_ids_per_case_and_pending_is_hidden(store: CenterStore):
    assert [add_caption(store), add_caption(store), add_caption(store, "C-1002")] == ["c-1", "c-2", "c-1"]
    assert store.captions("C-1001") == []

    second = store.set_caption_translation("C-1001", "c-2", "ok", "손")
    assert second.model_dump(by_alias=True) == {
        "id": "c-2",
        "from": "worker",
        "text": "Tay tôi",
        "lang": "vi",
        "translated": "손",
        "translatedLang": "ko",
        "translation": "ok",
        "at": clock.iso_utc(AT),
    }
    assert store.captions("C-1001") == [second]
    first = store.set_caption_translation("C-1001", "c-1", "skipped", None)
    # 번역이 거꾸로 끝나도 번호 순서다.
    assert [c.id for c in store.captions("C-1001")] == ["c-1", "c-2"]
    assert (first.translated, first.translation) == (None, "skipped")
    assert store.captions("C-1002") == []


def test_caption_translation_fills_only_pending(store: CenterStore):
    add_caption(store)
    assert store.set_caption_translation("C-1001", "c-1", "ok", "손") is not None
    # 이미 채운 자막·없는 자막·잘못된 번호는 None이고 바뀌지 않는다.
    assert store.set_caption_translation("C-1001", "c-1", "skipped", None) is None
    assert store.set_caption_translation("C-1001", "c-9", "ok", "x") is None
    assert store.set_caption_translation("C-1001", "m-1", "ok", "x") is None
    assert store.set_caption_translation("C-0", "c-1", "ok", "x") is None
    assert [(c.translated, c.translation) for c in store.captions("C-1001")] == [("손", "ok")]


def test_reset_clears_captions(store: CenterStore):
    add_caption(store)
    store.set_caption_translation("C-1001", "c-1", "ok", "손")
    add_caption(store)
    store.reset()

    assert store.captions("C-1001") == []
    assert store.set_caption_translation("C-1001", "c-2", "ok", "x") is None
    assert add_caption(store) == "c-1"


def test_sqlite_captions_survive_restart(tmp_path: Path):
    path = str(tmp_path / "center.db")
    first = SqliteStore(path, STARTED)
    add_caption(first)
    add_caption(first)
    sent = [first.set_caption_translation("C-1001", i, "ok", "손") for i in ("c-1", "c-2")]
    first.close()

    second = SqliteStore(path, STARTED)
    try:
        assert second.captions("C-1001") == sent
        assert add_caption(second) == "c-3"
    finally:
        second.close()


# ---------------------------------------------------------------------------
# 센터 직원 로그인(backlog 17): 직원 목록, 코드, 요청 기록, 세션
# ---------------------------------------------------------------------------
STAFF = "staff@example.org"


def test_staff_add_remove_list(store: CenterStore):
    assert store.add_staff(STAFF, AT) is True
    assert store.add_staff(STAFF, AT) is False
    assert store.add_staff("a@example.org", AT) is True
    assert store.list_staff() == ["a@example.org", STAFF]
    assert store.is_staff(STAFF) and not store.is_staff("who@example.org")
    assert store.remove_staff(STAFF) is True
    assert store.remove_staff(STAFF) is False
    assert store.list_staff() == ["a@example.org"]


def test_code_attempts_and_replace(store: CenterStore):
    store.set_code(STAFF, "h1", AT)
    assert store.add_code_attempt(STAFF) == 1
    assert store.add_code_attempt(STAFF) == 2
    store.set_code(STAFF, "h2", AT)
    code = store.get_code(STAFF)
    assert code is not None and (code.code_hash, code.attempts, code.expires_at) == ("h2", 0, clock.iso_utc(AT))
    store.delete_code(STAFF)
    assert store.get_code(STAFF) is None
    assert store.add_code_attempt(STAFF) == 0


def test_code_requests_window_and_prune(store: CenterStore):
    store.add_code_request(STAFF, AT, sent=True)
    store.add_code_request("who@example.org", AT, sent=False)
    assert store.code_requests(STAFF, AT - timedelta(seconds=1)) == 1
    assert store.code_requests(STAFF, AT) == 0
    assert store.sent_codes(AT - timedelta(seconds=1)) == 1
    # 1시간이 지난 기록은 다음 요청 때 지운다.
    store.add_code_request(STAFF, AT + timedelta(hours=1), sent=True)
    assert store.code_requests(STAFF, AT - timedelta(days=1)) == 1


def test_sessions_expire_and_end_with_staff(store: CenterStore):
    store.add_staff(STAFF, AT)
    store.add_session("t1", STAFF, AT, AT + timedelta(days=30))
    assert store.session_email("t1", AT + timedelta(days=29)) == STAFF
    assert store.session_email("t1", AT + timedelta(days=30)) is None
    store.delete_session("t1")
    assert store.session_email("t1", AT) is None
    store.add_session("t2", STAFF, AT, AT + timedelta(days=30))
    store.set_code(STAFF, "h", AT + timedelta(minutes=10))
    store.remove_staff(STAFF)
    assert store.session_email("t2", AT) is None
    assert store.get_code(STAFF) is None


def test_reset_keeps_login_data(store: CenterStore):
    store.add_staff(STAFF, AT)
    store.add_session("t1", STAFF, AT, AT + timedelta(days=30))
    store.reset()
    assert store.is_staff(STAFF)
    assert store.session_email("t1", AT) == STAFF


def test_sqlite_keeps_login_data_after_restart(tmp_path: Path):
    path = str(tmp_path / "center.db")
    s = SqliteStore(path, STARTED)
    s.add_staff(STAFF, AT)
    s.add_session("t1", STAFF, AT, AT + timedelta(days=30))
    s.close()
    s = SqliteStore(path, STARTED)
    assert s.list_staff() == [STAFF]
    assert s.session_email("t1", AT) == STAFF
    s.close()
