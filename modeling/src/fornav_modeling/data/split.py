# 응급도 데이터를 train/valid/test로 나누고 id 목록으로 고정한다.
# - data/splits/triage_{train,valid,test}.txt: id 목록(git 포함). 한번 커밋한 목록은 바꾸지 않는다(바꾸려면 사용자에게 묻는다)
# - data/splits/triage_test.sha256: 재생성한 data/test/triage_test.parquet의 sha256(git 포함)
# - data/processed/triage.parquet: train·valid 행만(split 열). 학습·임계값 조정은 이 파일만 읽는다
# - data/test/triage_test.parquet: test 행만. 평가 명령만 load_test로 읽는다
# test 행은 processed에 넣지 않아, 학습 쪽 코드가 test 행을 메모리에 올릴 길 자체를 없앤다.
# 질환·증상 데이터(backlog 06)도 같은 방식이다: data/splits/symptom_*.txt, symptom_test.sha256, data/processed/symptom.parquet,
# data/test/symptom_test.parquet. 질환으로 층화한다.

import json
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from fornav_modeling.data import kaggle_symptom, kaggle_triage
from fornav_modeling.data.download import sha256_file
from fornav_modeling.features.buttons import FEATURE_NAMES, featurize_many
from fornav_modeling.labels.ktas import ACUITIES

SEED = 20261027
TEST_SIZE = 0.20  # 전체 대비
VALID_SIZE = 0.15  # 전체 대비
SPLITS = ("train", "valid", "test")
DEV_SPLITS = ("train", "valid")

PROCESSED_FILE = "triage.parquet"
TEST_FILE = "triage_test.parquet"
TEST_HASH_FILE = "triage_test.sha256"
SYMPTOM_PROCESSED_FILE = "symptom.parquet"
SYMPTOM_TEST_FILE = "symptom_test.parquet"
SYMPTOM_TEST_HASH_FILE = "symptom_test.sha256"


class SplitError(RuntimeError):
    pass


def split_ids(table: pd.DataFrame, label: str = "acuity", seed: int = SEED) -> dict[str, list[str]]:
    """라벨로 층화해 나눈다. 같은 테이블·seed면 같은 결과. 각 목록은 id 순으로 정렬한다."""
    ids, labels = table["id"].tolist(), table[label].tolist()
    rest_ids, test_ids, rest_labels, _ = train_test_split(ids, labels, test_size=TEST_SIZE, stratify=labels, random_state=seed)
    train_ids, valid_ids = train_test_split(rest_ids, test_size=VALID_SIZE / (1 - TEST_SIZE), stratify=rest_labels, random_state=seed)
    return {"train": sorted(train_ids), "valid": sorted(valid_ids), "test": sorted(test_ids)}


def split_path(splits_dir: Path, name: str, prefix: str = "triage") -> Path:
    return splits_dir / f"{prefix}_{name}.txt"


def read_split_ids(splits_dir: Path, name: str, prefix: str = "triage") -> list[str]:
    return split_path(splits_dir, name, prefix).read_text().split()


def make_splits(
    raw_dir: Path, tables_dir: Path, processed_dir: Path, splits_dir: Path, test_dir: Path, reports_dir: Path, force: bool = False
) -> dict:
    """원본 → 표준 테이블 → 분할 → 파일 쓰기 → 리포트. 리포트 dict를 돌려준다.
    이미 커밋된 id 목록·test 해시와 다르게 나오면 SplitError(force=True면 덮어쓴다)."""
    table = kaggle_triage.standardize(kaggle_triage.read_raw(raw_dir), kaggle_triage.read_chief_complaint_map(tables_dir))
    _write_dataset(
        table, split_ids(table), "triage", (PROCESSED_FILE, TEST_FILE, TEST_HASH_FILE), processed_dir, splits_dir, test_dir, force
    )

    report = build_report(table)
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "triage_splits.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    unmapped = pd.DataFrame(report["chief_complaint"]["unmapped_top20"])
    unmapped.to_csv(reports_dir / "triage_unmapped_chief_complaints.csv", index=False)
    return report


def make_symptom_splits(
    raw_dir: Path, tables_dir: Path, processed_dir: Path, splits_dir: Path, test_dir: Path, reports_dir: Path, force: bool = False
) -> dict:
    """질환·증상 원본 → 표준 테이블 → 질환 층화 분할 → 파일 쓰기 → 리포트(질환명 없이 건수만)."""
    from fornav_modeling.labels.department import read_symptom_map

    table, summary = kaggle_symptom.standardize(kaggle_symptom.read_dataset(raw_dir), read_symptom_map(tables_dir))
    ids = split_ids(table, label="disease")
    _write_dataset(
        table,
        ids,
        "symptom",
        (SYMPTOM_PROCESSED_FILE, SYMPTOM_TEST_FILE, SYMPTOM_TEST_HASH_FILE),
        processed_dir,
        splits_dir,
        test_dir,
        force,
    )
    labels = dict(zip(table["id"], table["disease"], strict=True))
    report = {
        "seed": SEED,
        "sizes": {"test": TEST_SIZE, "valid": VALID_SIZE},
        "conversion": summary,
        "rows": {name: len(ids[name]) for name in SPLITS},
        "diseases_per_split": {name: len({labels[i] for i in ids[name]}) for name in SPLITS},
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "symptom_splits.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def load_dev(processed_dir: Path, splits_dir: Path, name: str) -> pd.DataFrame:
    """응급도 학습·검증용 행. name은 "train" 또는 "valid"만 받는다. data/test는 열지 않는다."""
    return _load_dev(processed_dir / PROCESSED_FILE, splits_dir, name, "triage")


def load_test(test_dir: Path, splits_dir: Path) -> pd.DataFrame:
    """평가 명령 전용. 재생성한 test 파일의 해시가 커밋된 해시와 다르면 SplitError로 멈춘다."""
    return _load_test(test_dir / TEST_FILE, splits_dir / TEST_HASH_FILE)


def load_symptom_dev(processed_dir: Path, splits_dir: Path, name: str) -> pd.DataFrame:
    return _load_dev(processed_dir / SYMPTOM_PROCESSED_FILE, splits_dir, name, "symptom")


def load_symptom_test(test_dir: Path, splits_dir: Path) -> pd.DataFrame:
    return _load_test(test_dir / SYMPTOM_TEST_FILE, splits_dir / SYMPTOM_TEST_HASH_FILE)


def _write_dataset(
    table: pd.DataFrame,
    ids: dict[str, list[str]],
    prefix: str,
    files: tuple[str, str, str],
    processed_dir: Path,
    splits_dir: Path,
    test_dir: Path,
    force: bool,
) -> None:
    """table에 split 열을 넣고 dev(processed)·test·id 목록·test 해시를 쓴다. 커밋된 목록·해시와 다르면 SplitError."""
    processed_file, test_file, hash_file = files
    _check_unchanged(splits_dir, {split_path(splits_dir, n, prefix).name: _id_text(ids[n]) for n in SPLITS}, force)
    split_of = {i: name for name in SPLITS for i in ids[name]}
    table.insert(1, "split", table["id"].map(split_of))
    processed_dir.mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)
    table[table["split"] != "test"].reset_index(drop=True).to_parquet(processed_dir / processed_file, index=False)
    table[table["split"] == "test"].reset_index(drop=True).to_parquet(test_dir / test_file, index=False)
    test_hash = f"{sha256_file(test_dir / test_file)}  {test_file}\n"
    _check_unchanged(splits_dir, {hash_file: test_hash}, force)
    splits_dir.mkdir(parents=True, exist_ok=True)
    for name in SPLITS:
        split_path(splits_dir, name, prefix).write_text(_id_text(ids[name]))
    (splits_dir / hash_file).write_text(test_hash)


def _load_dev(path: Path, splits_dir: Path, name: str, prefix: str) -> pd.DataFrame:
    if name not in DEV_SPLITS:
        raise ValueError(f"학습 쪽 로더는 {DEV_SPLITS}만 읽는다: {name!r}. test는 평가 명령에서 읽는다")
    table = pd.read_parquet(path)
    rows = table[table["split"] == name].reset_index(drop=True)
    if rows["id"].tolist() != read_split_ids(splits_dir, name, prefix):
        raise SplitError(f"{path.name}의 {name} 행이 id 목록과 다르다. scripts/make_splits.py를 다시 돌린다")
    return rows


def _load_test(path: Path, hash_path: Path) -> pd.DataFrame:
    expected = hash_path.read_text().split()[0]
    if not path.exists() or sha256_file(path) != expected:
        raise SplitError(f"{path}가 없거나 해시가 {hash_path.name}와 다르다. scripts/make_splits.py로 다시 만든다")
    return pd.read_parquet(path)


def build_report(table: pd.DataFrame) -> dict:
    """라벨 건수(분자·분모), 주증상 매핑 커버리지, 피처 결측을 분할별로 센다. table에는 split 열이 있어야 한다."""
    groups = {"all": table, **{name: table[table["split"] == name] for name in SPLITS}}
    features = pd.DataFrame(featurize_many(table.to_dict("records")), columns=FEATURE_NAMES)
    unmapped = table.loc[~table["chief_complaint_mapped"], "chief_complaint"].value_counts()
    return {
        "seed": SEED,
        "sizes": {"test": TEST_SIZE, "valid": VALID_SIZE},
        "labels": {
            name: {
                "total": len(rows),
                "acuity": {a: int((rows["acuity"] == a).sum()) for a in ACUITIES},
                "acuity_rn": {a: int((rows["acuity_rn"] == a).sum()) for a in ACUITIES},
            }
            for name, rows in groups.items()
        },
        "chief_complaint": {
            "mapped_rows": {name: [int(rows["chief_complaint_mapped"].sum()), len(rows)] for name, rows in groups.items()},
            "unique": int(table["chief_complaint"].nunique()),
            "unmapped_unique": len(unmapped),
            "unmapped_top20": [{"chief_complaint": k, "rows": int(v)} for k, v in unmapped.head(20).items()],
        },
        "feature_missing": {name: int(features[name].isna().sum()) for name in FEATURE_NAMES if features[name].isna().any()},
        "feature_rows": len(features),
    }


def _id_text(ids: list[str]) -> str:
    return "\n".join(ids) + "\n"


def _check_unchanged(splits_dir: Path, expected: dict[str, str], force: bool) -> None:
    if force:
        return
    for name, text in expected.items():
        path = splits_dir / name
        if path.exists() and path.read_text() != text:
            raise SplitError(
                f"{path}가 커밋된 내용과 다르게 나왔다. 분할은 고정이므로 원인을 확인하고, 바꿔야 하면 사용자와 정한 뒤 --force로 덮어쓴다"
            )
