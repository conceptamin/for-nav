# 센터 저장소(backlog 07): 메모리·SQLite 두 구현에 같은 테스트를 돌리고, SQLite는 재시작 뒤에도 남는지 본다.

from datetime import datetime
from pathlib import Path

import pytest

from app import clock
from app.schemas import CenterCase
from app.settings import load_settings
from app.store import CenterStore, MemoryStore, open_store
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
