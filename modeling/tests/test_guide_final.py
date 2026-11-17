# 최종 평가용 안내 조합(backlog 18): 조정용과 겹치지 않고, 고정한 뒤 바뀌면 멈추고, 학습은 id만 읽어 같은 조합을 뺀다.

import re
from pathlib import Path

import pytest

from fornav_modeling.labels import department as dept
from fornav_modeling.labels.department import TableError
from fornav_modeling.models import dept_b

MODELING = Path(__file__).resolve().parents[1]
TABLES = MODELING / "data" / "tables"
HEADER = ",".join(dept.GUIDE_COLUMNS) + "\n"
# 정답 표를 읽어도 되는 곳: 정의(department.py), 고정 명령, 평가 명령
GUIDE_TEST_READERS = {"src/fornav_modeling/labels/department.py", "scripts/freeze_guide_test.py", "scripts/evaluate.py"}


def row(body, symptom, injury, department="ortho", reviewed="yes", url="https://example.org/a") -> str:
    return f"{body},{symptom},{injury},{department},,{url},ex,제목 진료과: 정형외과,,test,{reviewed}\n"


@pytest.fixture
def dirs(tmp_path):
    tables, splits = tmp_path / "tables", tmp_path / "splits"
    tables.mkdir()
    splits.mkdir()
    (tables / dept.GUIDE).write_text(HEADER + row("back", "pain", "no"))
    (tables / dept.GUIDE_TEST).write_text(
        HEADER + row("hand", "cut", "yes", "surgery") + row("leg", "swelling", "yes") + row("foot", "pain", "yes", reviewed="no")
    )
    return tables, splits


def test_freeze_keeps_only_reviewed_rows(dirs):
    tables, splits = dirs
    summary = dept.freeze_guide_test(tables, splits)
    assert summary == {"combos": 2, "by_department": {"surgery": 1, "ortho": 1}, "injury_yes": 2}
    assert dept.held_test_ids(splits) == ["hand-cut-yes", "leg-swelling-yes"]
    ids, answers = dept.load_guide_test(tables, splits)
    assert ids == ["hand-cut-yes", "leg-swelling-yes"] and answers["hand-cut-yes"].department == "surgery"


def test_freeze_refuses_twice(dirs):
    tables, splits = dirs
    dept.freeze_guide_test(tables, splits)
    with pytest.raises(TableError, match="이미"):
        dept.freeze_guide_test(tables, splits)


def test_load_stops_when_reviewed_rows_change(dirs):
    tables, splits = dirs
    dept.freeze_guide_test(tables, splits)
    path = tables / dept.GUIDE_TEST
    path.write_text(path.read_text().replace("hand,cut,yes,surgery", "hand,cut,yes,ortho"))
    with pytest.raises(TableError, match="고정한"):
        dept.load_guide_test(tables, splits)


def test_freeze_refuses_combo_shared_with_tuning_set(dirs):
    tables, splits = dirs
    (tables / dept.GUIDE_TEST).write_text(HEADER + row("back", "pain", "any"))  # any는 조정용 back-pain-no와 같은 조합
    assert dept.check_guide_test_disjoint(tables) == ["back-pain-any"]
    with pytest.raises(TableError, match="같은 조합"):
        dept.freeze_guide_test(tables, splits)


def test_held_test_ids_empty_before_freeze(tmp_path):
    assert dept.held_test_ids(tmp_path) == []


def test_model_b_training_drops_final_combos():
    table = {"hand-cut-yes": {"surgery": 1.0}, "back-pain-no": {"ortho": 1.0}, "leg-pain-no": {"ortho": 1.0}}
    train, held = dept_b.split_table(table, ["back-pain-no"], ["hand-cut-any"])
    assert set(train) == {"leg-pain-no"} and set(held) == {"back-pain-no"}


def test_committed_final_table_is_valid_and_disjoint():
    dept.read_guide(TABLES, dept.GUIDE_TEST)
    assert dept.check_guide_test_disjoint(TABLES) == []


def test_committed_freeze_matches_table():
    # 2026-11-17 고정: 검토한 31건. 정답 표의 reviewed=yes 행이 바뀌면 해시가 달라져 멈춘다
    splits = MODELING / "data" / "splits"
    ids, answers = dept.load_guide_test(TABLES, splits)
    assert ids == dept.held_test_ids(splits) == sorted(answers)
    assert len(ids) == 31


def test_only_freeze_and_evaluation_read_final_answers():
    pattern = re.compile(r"GUIDE_TEST\b|load_guide_test|department_guide_test")
    offenders = []
    for path in [*(MODELING / "src").rglob("*.py"), *(MODELING / "scripts").glob("*.py")]:
        relative = path.relative_to(MODELING).as_posix()
        if relative not in GUIDE_TEST_READERS and pattern.search(path.read_text()):
            offenders.append(relative)
    assert offenders == []
