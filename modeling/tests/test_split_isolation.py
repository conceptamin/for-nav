# 분할이 결정적이고 겹치지 않는지, 학습 쪽 경로가 data/test를 열지 않는지.

import os
import re
from pathlib import Path

import pandas as pd
import pytest

from fornav_modeling.data import split
from fornav_modeling.data.split import SplitError

MODELING = Path(__file__).resolve().parents[1]

# data/test를 읽어도 되는 곳: 분할을 만드는 코드와 평가 명령(04에서 추가)뿐이다.
TEST_READERS = {"src/fornav_modeling/data/split.py", "scripts/make_splits.py", "scripts/evaluate.py"}


def synthetic_table(n=200):
    labels = ["emergency"] * (n // 5) + ["today"] * (2 * n // 5) + ["outpatient"] * (n - n // 5 - 2 * n // 5)
    return pd.DataFrame({"id": [f"triage_{i:04d}" for i in range(1, n + 1)], "acuity": labels})


def test_split_is_deterministic_disjoint_and_complete():
    table = synthetic_table()
    ids = split.split_ids(table)
    assert ids == split.split_ids(table.copy())
    sets = {name: set(v) for name, v in ids.items()}
    assert not (sets["train"] & sets["valid"]) and not (sets["train"] & sets["test"]) and not (sets["valid"] & sets["test"])
    assert sets["train"] | sets["valid"] | sets["test"] == set(table["id"])
    assert len(ids["test"]) == 40 and len(ids["valid"]) == 30


def test_split_is_stratified():
    table = synthetic_table()
    labels = dict(zip(table["id"], table["acuity"], strict=True))
    for name, ids in split.split_ids(table).items():
        share = sum(labels[i] == "emergency" for i in ids) / len(ids)
        assert share == pytest.approx(0.2, abs=0.02), name


def test_committed_splits_are_disjoint():
    ids = {name: split.read_split_ids(MODELING / "data" / "splits", name) for name in split.SPLITS}
    assert sum(len(v) for v in ids.values()) == len(set().union(*ids.values())) == 1267
    assert all(v == sorted(v) for v in ids.values())


@pytest.fixture
def written(tmp_path):
    """processed/splits/test를 실제 파일 형식대로 만든다."""
    table = synthetic_table(100)
    ids = split.split_ids(table)
    split_of = {i: name for name, v in ids.items() for i in v}
    table.insert(1, "split", table["id"].map(split_of))
    dirs = {name: tmp_path / name for name in ("processed", "splits", "test")}
    for d in dirs.values():
        d.mkdir()
    table[table["split"] != "test"].reset_index(drop=True).to_parquet(dirs["processed"] / split.PROCESSED_FILE, index=False)
    table[table["split"] == "test"].reset_index(drop=True).to_parquet(dirs["test"] / split.TEST_FILE, index=False)
    for name, v in ids.items():
        split.split_path(dirs["splits"], name).write_text("\n".join(v) + "\n")
    test_hash = split.sha256_file(dirs["test"] / split.TEST_FILE)
    (dirs["splits"] / split.TEST_HASH_FILE).write_text(f"{test_hash}  {split.TEST_FILE}\n")
    return dirs, ids


@pytest.mark.skipif(os.name != "posix" or os.geteuid() == 0, reason="권한으로 막을 수 없는 환경")
def test_load_dev_does_not_open_test_dir(written):
    dirs, ids = written
    dirs["test"].chmod(0)  # 열려고 하면 PermissionError
    try:
        for name in split.DEV_SPLITS:
            rows = split.load_dev(dirs["processed"], dirs["splits"], name)
            assert rows["id"].tolist() == ids[name]
            assert not set(rows["id"]) & set(ids["test"])
    finally:
        dirs["test"].chmod(0o755)


def test_load_dev_refuses_test(written):
    dirs, _ = written
    with pytest.raises(ValueError):
        split.load_dev(dirs["processed"], dirs["splits"], "test")


def test_processed_has_no_test_rows(written):
    dirs, ids = written
    processed = pd.read_parquet(dirs["processed"] / split.PROCESSED_FILE)
    assert not set(processed["id"]) & set(ids["test"])


def test_load_test_stops_on_hash_mismatch(written):
    dirs, ids = written
    assert split.load_test(dirs["test"], dirs["splits"])["id"].tolist() == ids["test"]
    (dirs["test"] / split.TEST_FILE).write_bytes(b"changed")
    with pytest.raises(SplitError):
        split.load_test(dirs["test"], dirs["splits"])


def test_only_evaluation_code_references_test_data():
    # 학습·조정 명령(scripts/train_*.py, tune_*.py 등)과 패키지 코드가 test 데이터에 닿는 이름을 쓰지 않는지 본다.
    pattern = re.compile(r"load_test|TEST_FILE|TEST_HASH_FILE|data/test|\"test\"\s*/|/\s*\"test\"")
    offenders = []
    for path in [*(MODELING / "src").rglob("*.py"), *(MODELING / "scripts").glob("*.py")]:
        relative = path.relative_to(MODELING).as_posix()
        if relative not in TEST_READERS and pattern.search(path.read_text()):
            offenders.append(relative)
    assert offenders == []
