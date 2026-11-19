# 분할이 결정적이고 겹치지 않는지(행도 버튼 벡터도), 두 출처를 합치는 규칙, 학습 쪽 경로가 data/test를 열지 않는지.

import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fornav_modeling.data import ddxplus, split
from fornav_modeling.data.split import SplitError

MODELING = Path(__file__).resolve().parents[1]
DATA = MODELING / "data"
HAS_SOURCES = (DATA / "raw" / "kaggle_symptom" / "dataset.csv").exists() and (DATA / "processed" / ddxplus.PROCESSED_FILE).exists()

# data/test를 읽어도 되는 곳: 분할을 만드는 코드와 평가 명령(04에서 추가)뿐이다.
TEST_READERS = {"src/fornav_modeling/data/split.py", "scripts/make_splits.py", "scripts/evaluate.py"}


def synthetic_table(n=200):
    """질환 셋(비율 1:2:2), 두 행씩 같은 버튼 벡터. 벡터 하나에는 질환이 하나다."""
    labels = ["d0"] * (n // 5) + ["d1"] * (2 * n // 5) + ["d2"] * (n - n // 5 - 2 * n // 5)
    return pd.DataFrame(
        {"id": [f"symptom_{i:04d}" for i in range(1, n + 1)], "disease": labels, "vector": [f"v{i // 2}" for i in range(n)]}
    )


def test_split_is_deterministic_disjoint_and_complete():
    table = synthetic_table()
    ids = split.split_ids(table)
    assert ids == split.split_ids(table.copy())
    sets = {name: set(v) for name, v in ids.items()}
    assert not (sets["train"] & sets["valid"]) and not (sets["train"] & sets["test"]) and not (sets["valid"] & sets["test"])
    assert sets["train"] | sets["valid"] | sets["test"] == set(table["id"])
    assert len(ids["test"]) == 40 and len(ids["valid"]) == 32  # 5겹 중 하나, 나머지의 5겹 중 하나


def test_split_keeps_vector_groups_together():
    table = synthetic_table()
    vector = dict(zip(table["id"], table["vector"], strict=True))
    by_split = {name: {vector[i] for i in v} for name, v in split.split_ids(table).items()}
    assert not (by_split["train"] & by_split["valid"]) and not (by_split["train"] & by_split["test"])
    assert not (by_split["valid"] & by_split["test"])


def test_split_is_stratified():
    table = synthetic_table()
    labels = dict(zip(table["id"], table["disease"], strict=True))
    for name, ids in split.split_ids(table).items():
        share = sum(labels[i] == "d0" for i in ids) / len(ids)
        assert share == pytest.approx(0.2, abs=0.05), name


def test_combine_sources_merges_labels_and_keeps_vector_shares():
    kaggle = pd.DataFrame(
        {
            "id": ["symptom_0001", "symptom_0002"],
            "disease": ["K", "L"],
            "body_parts": [["skin"], ["skin"]],
            "symptoms": [["rash"], ["rash"]],
        }
    )
    ddx = pd.DataFrame(
        {
            "id": ["ddxplus_000001", "ddxplus_000002", "ddxplus_000003"],
            "disease": ["ddxplus:x1", "ddxplus:x2", "ddxplus:y"],
            "kcd": ["X01", "X01", "Y01"],
            "body_parts": ["skin", "skin", ""],
            "symptoms": ["rash", "rash", "fever"],
            "patients": [3, 1, 4],
        }
    )
    # x1·x2는 KCD가 같아 한 라벨(ddxplus:X01)이 되고 같은 벡터라 한 행으로 합친다. y는 Kaggle K와 KCD가 겹친다고 본다
    table, summary = split.combine_sources(kaggle, ddx, {"x1": "ddxplus:X01", "x2": "ddxplus:X01", "y": "K"})
    rows = table.set_index("id")
    assert list(rows.index) == ["ddxplus_000001", "ddxplus_000003", "symptom_0001", "symptom_0002"]
    assert rows.loc["ddxplus_000001", "disease"] == "ddxplus:X01" and rows.loc["ddxplus_000003", "disease"] == "K"
    assert rows["share"].to_dict() == {"ddxplus_000001": 1.0, "ddxplus_000003": 1.0, "symptom_0001": 0.5, "symptom_0002": 0.5}
    assert rows.loc["ddxplus_000003", "vector"] == "/fever" and rows.loc["symptom_0001", "vector"] == "skin/rash"
    assert summary["ddxplus_rows_merged_by_label"] == 1 and summary["vectors"]["shared"] == 1


def test_train_weights_balance_sources():
    table = pd.DataFrame({"source": ["kaggle"] * 2 + ["ddxplus"] * 6, "share": [1.0, 1.0, 0.5, 0.5, 1.0, 1.0, 0.25, 0.75]})
    w = split.train_weights(table)
    assert w[:2].sum() == pytest.approx(w[2:].sum()) and w.mean() == pytest.approx(1.0)
    assert w[2] == pytest.approx(w[3]) and w[7] == pytest.approx(3 * w[6])


def test_committed_splits_are_disjoint():
    ids = {name: split.read_split_ids(DATA / "splits", name) for name in split.SPLITS}
    assert sum(len(v) for v in ids.values()) == len(set().union(*ids.values())) == 2457
    assert all(v == sorted(v) for v in ids.values())


@pytest.mark.skipif(not HAS_SOURCES, reason="원본이 없다(download_data.py, build_ddxplus.py)")
def test_committed_splits_share_no_button_vector():
    # 원본으로 표를 다시 만들어, 커밋한 id 목록의 세 셋이 같은 버튼 벡터를 갖지 않는지 본다(data/test는 열지 않는다)
    table, _ = split.symptom_table(DATA / "raw", DATA / "tables", DATA / "processed")
    vector = dict(zip(table["id"], table["vector"], strict=True))
    ids = {name: split.read_split_ids(DATA / "splits", name) for name in split.SPLITS}
    assert set(vector) == set().union(*ids.values())
    sets = {name: {vector[i] for i in v} for name, v in ids.items()}
    assert not (sets["train"] & sets["valid"]) and not (sets["train"] & sets["test"]) and not (sets["valid"] & sets["test"])
    assert np.isclose(table.groupby(["source", "vector"])["share"].sum(), 1.0).all()


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
    table[table["split"] != "test"].reset_index(drop=True).to_parquet(dirs["processed"] / split.SYMPTOM_PROCESSED_FILE, index=False)
    table[table["split"] == "test"].reset_index(drop=True).to_parquet(dirs["test"] / split.SYMPTOM_TEST_FILE, index=False)
    for name, v in ids.items():
        split.split_path(dirs["splits"], name).write_text("\n".join(v) + "\n")
    test_hash = split.sha256_file(dirs["test"] / split.SYMPTOM_TEST_FILE)
    (dirs["splits"] / split.SYMPTOM_TEST_HASH_FILE).write_text(f"{test_hash}  {split.SYMPTOM_TEST_FILE}\n")
    return dirs, ids


@pytest.mark.skipif(os.name != "posix" or os.geteuid() == 0, reason="권한으로 막을 수 없는 환경")
def test_load_dev_does_not_open_test_dir(written):
    dirs, ids = written
    dirs["test"].chmod(0)  # 열려고 하면 PermissionError
    try:
        for name in split.DEV_SPLITS:
            rows = split.load_symptom_dev(dirs["processed"], dirs["splits"], name)
            assert rows["id"].tolist() == ids[name]
            assert not set(rows["id"]) & set(ids["test"])
    finally:
        dirs["test"].chmod(0o755)


def test_load_dev_refuses_test(written):
    dirs, _ = written
    with pytest.raises(ValueError):
        split.load_symptom_dev(dirs["processed"], dirs["splits"], "test")


def test_processed_has_no_test_rows(written):
    dirs, ids = written
    processed = pd.read_parquet(dirs["processed"] / split.SYMPTOM_PROCESSED_FILE)
    assert not set(processed["id"]) & set(ids["test"])


def test_load_test_stops_on_hash_mismatch(written):
    dirs, ids = written
    assert split.load_symptom_test(dirs["test"], dirs["splits"])["id"].tolist() == ids["test"]
    (dirs["test"] / split.SYMPTOM_TEST_FILE).write_bytes(b"changed")
    with pytest.raises(SplitError):
        split.load_symptom_test(dirs["test"], dirs["splits"])


def test_only_evaluation_code_references_test_data():
    # 학습·조정 명령(scripts/train_*.py, tune_*.py 등)과 패키지 코드가 test 데이터에 닿는 이름을 쓰지 않는지 본다.
    pattern = re.compile(r"load_test|TEST_FILE|TEST_HASH_FILE|data/test|\"test\"\s*/|/\s*\"test\"")
    offenders = []
    for path in [*(MODELING / "src").rglob("*.py"), *(MODELING / "scripts").glob("*.py")]:
        relative = path.relative_to(MODELING).as_posix()
        if relative not in TEST_READERS and pattern.search(path.read_text()):
            offenders.append(relative)
    assert offenders == []
