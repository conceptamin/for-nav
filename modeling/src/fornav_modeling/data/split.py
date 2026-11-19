# 질환·증상 데이터(진료과 모델 A)를 train/valid/test로 나누고 id 목록으로 고정한다.
# - 출처 두 개를 한 표로 합친다(backlog 16): Kaggle(kaggle_symptom.standardize)과 DDXPlus(ddxplus.read_processed, build_ddxplus.py가 만든다).
#   행은 (출처, 질환 라벨, 버튼 벡터)마다 하나다. DDXPlus 질환 라벨은 labels/department.ddxplus_labels로 Kaggle 라벨과 합친다.
# - 같은 버튼 벡터의 행은 출처와 상관없이 언제나 같은 셋에 넣는다(StratifiedGroupKFold, 질환 층화). 모델이 보는 것은 버튼 벡터라
#   같은 벡터가 train과 test에 함께 있으면 외운 답을 맞힌 것이 된다. 옛 분할(v2)은 행 id로만 나눠 test 59행 중 42행이 train과 벡터가 같았다.
# - share 열: 같은 출처·같은 벡터 안에서 그 행(질환)의 몫. 합이 1이다. DDXPlus는 환자 수 비율, Kaggle은 빈도가 없어 균등.
#   학습 가중치는 이것을 출처마다 합이 같게 늘린 값이다(train_weights, 사용자 결정 2026-11-19).
# - data/splits/symptom_{train,valid,test}.txt: id 목록(git 포함). 한번 커밋한 목록은 바꾸지 않는다(바꾸려면 사용자에게 묻는다)
#   옛 목록은 data/splits/v2/에 기록으로 둔다(backlog 16, 사용자 승인 2026-11-19)
# - data/splits/symptom_test.sha256: 재생성한 data/test/symptom_test.parquet의 sha256(git 포함)
# - data/processed/symptom.parquet: train·valid 행만(split 열). 학습·조정은 이 파일만 읽는다
# - data/test/symptom_test.parquet: test 행만. 평가 명령만 load_symptom_test로 읽는다
# test 행은 processed에 넣지 않아, 학습 쪽 코드가 test 행을 메모리에 올릴 길 자체를 없앤다.

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from fornav_modeling.data import ddxplus, kaggle_symptom
from fornav_modeling.data.download import sha256_file

SEED = 20261027
TEST_FOLDS = 5  # 전체를 5겹 → 한 겹이 test(20%)
VALID_FOLDS = 5  # 나머지를 5겹 → 한 겹이 valid(전체의 16%). 옛 비율 15%에 가장 가까운 정수 겹 수
SPLITS = ("train", "valid", "test")
DEV_SPLITS = ("train", "valid")
SOURCES = ("kaggle", "ddxplus")
COLUMNS = ["id", "source", "disease", "body_parts", "symptoms", "vector", "share"]

SYMPTOM_PROCESSED_FILE = "symptom.parquet"
SYMPTOM_TEST_FILE = "symptom_test.parquet"
SYMPTOM_TEST_HASH_FILE = "symptom_test.sha256"


class SplitError(RuntimeError):
    pass


def vector_key(body_parts, symptoms) -> str:
    """버튼 벡터 → 그룹 열쇠. body_parts·symptoms는 schema 순서의 목록이다."""
    return "|".join(body_parts) + "/" + "|".join(symptoms)


def split_ids(table: pd.DataFrame, label: str = "disease", group: str = "vector", seed: int = SEED) -> dict[str, list[str]]:
    """그룹(버튼 벡터)을 한 셋에 모으면서 라벨로 층화해 나눈다. 같은 테이블·seed면 같은 결과. 각 목록은 id 순으로 정렬한다."""
    table = table.reset_index(drop=True)
    rest, test = next(StratifiedGroupKFold(TEST_FOLDS, shuffle=True, random_state=seed).split(table, table[label], table[group]))
    rest_table = table.iloc[rest].reset_index(drop=True)
    train, valid = next(
        StratifiedGroupKFold(VALID_FOLDS, shuffle=True, random_state=seed).split(rest_table, rest_table[label], rest_table[group])
    )
    return {
        "train": sorted(rest_table["id"].iloc[train]),
        "valid": sorted(rest_table["id"].iloc[valid]),
        "test": sorted(table["id"].iloc[test]),
    }


def split_path(splits_dir: Path, name: str, prefix: str = "symptom") -> Path:
    return splits_dir / f"{prefix}_{name}.txt"


def read_split_ids(splits_dir: Path, name: str, prefix: str = "symptom") -> list[str]:
    return split_path(splits_dir, name, prefix).read_text().split()


def combine_sources(kaggle: pd.DataFrame, ddx: pd.DataFrame, labels: dict[str, str]) -> tuple[pd.DataFrame, dict]:
    """Kaggle 표준 테이블 + DDXPlus 표준 테이블(ddxplus.read_processed) → 한 표. labels는 DDXPlus icd10-id → 질환 라벨.
    DDXPlus는 라벨을 합친 뒤 같은 (라벨, 벡터)가 되면 환자 수를 더해 한 행으로 둔다(id는 먼저 나온 행)."""
    kaggle_rows = pd.DataFrame(
        {
            "id": kaggle["id"],
            "source": "kaggle",
            "disease": kaggle["disease"],
            "body_parts": kaggle["body_parts"],
            "symptoms": kaggle["symptoms"],
            "patients": 1,
        }
    )
    merged: dict[tuple[str, str, str], dict] = {}
    for row in ddx.itertuples():
        label = labels[row.disease.removeprefix(ddxplus.LABEL_PREFIX)]
        key = (label, row.body_parts, row.symptoms)
        if key in merged:
            merged[key]["patients"] += row.patients
        else:
            merged[key] = {
                "id": row.id,
                "source": "ddxplus",
                "disease": label,
                "body_parts": [v for v in row.body_parts.split("|") if v],
                "symptoms": [v for v in row.symptoms.split("|") if v],
                "patients": row.patients,
            }
    ddx_rows = pd.DataFrame(list(merged.values()), columns=kaggle_rows.columns)
    table = pd.concat([kaggle_rows, ddx_rows], ignore_index=True)
    table["vector"] = [vector_key(b, s) for b, s in zip(table["body_parts"], table["symptoms"], strict=True)]
    table["share"] = table["patients"] / table.groupby(["source", "vector"])["patients"].transform("sum")
    summary = {
        "ddxplus_rows_before_label_merge": len(ddx),
        "ddxplus_rows_merged_by_label": len(ddx) - len(ddx_rows),
        "rows": {s: int((table["source"] == s).sum()) for s in SOURCES},
        "labels": int(table["disease"].nunique()),
        "labels_shared_by_sources": len(set(kaggle_rows["disease"]) & set(ddx_rows["disease"])),
        "vectors": {
            **{s: int(table.loc[table["source"] == s, "vector"].nunique()) for s in SOURCES},
            "shared": len(set(table.loc[table["source"] == "kaggle", "vector"]) & set(table.loc[table["source"] == "ddxplus", "vector"])),
            "all": int(table["vector"].nunique()),
        },
        "vectors_with_several_labels": int((table.groupby("vector")["disease"].nunique() > 1).sum()),
    }
    return table[COLUMNS].sort_values("id", ignore_index=True), summary


def train_weights(table: pd.DataFrame) -> np.ndarray:
    """학습 가중치: share를 출처마다 합이 (행 수 / 출처 수)가 되게 늘린다. 평균 가중치는 1이다."""
    sources = table["source"].unique()
    totals = table.groupby("source")["share"].transform("sum")
    return (table["share"] * len(table) / len(sources) / totals).to_numpy(dtype=np.float64)


def symptom_table(raw_dir: Path, tables_dir: Path, processed_dir: Path) -> tuple[pd.DataFrame, dict]:
    from fornav_modeling.labels.department import ddxplus_labels, read_disease_kcd, read_symptom_map

    kaggle, kaggle_summary = kaggle_symptom.standardize(kaggle_symptom.read_dataset(raw_dir), read_symptom_map(tables_dir))
    labels = ddxplus_labels(ddxplus.read_condition_kcd(tables_dir), read_disease_kcd(tables_dir))
    table, summary = combine_sources(kaggle, ddxplus.read_processed(processed_dir), labels)
    return table, {"kaggle": kaggle_summary, "combined": summary}


def make_symptom_splits(
    raw_dir: Path, tables_dir: Path, processed_dir: Path, splits_dir: Path, test_dir: Path, reports_dir: Path, force: bool = False
) -> dict:
    """원본 → 두 출처를 합친 표준 테이블 → 벡터 그룹·질환 층화 분할 → 파일 쓰기 → 리포트(질환명 없이 건수만)."""
    table, summary = symptom_table(raw_dir, tables_dir, processed_dir)
    ids = split_ids(table)
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
    report = {"seed": SEED, "folds": {"test": TEST_FOLDS, "valid": VALID_FOLDS}, "conversion": summary, **split_summary(table, ids)}
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "symptom_splits.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def split_summary(table: pd.DataFrame, ids: dict[str, list[str]]) -> dict:
    """셋별 행·벡터·질환 수(출처별)와 셋 사이 벡터 겹침. 질환명은 넣지 않는다."""
    rows = table.set_index("id")
    sets = {name: rows.loc[ids[name]] for name in SPLITS}
    vectors = {name: set(part["vector"]) for name, part in sets.items()}
    all_labels = set(table["disease"])
    return {
        "rows": {name: {"n": len(part), "of": len(table)} for name, part in sets.items()},
        "rows_by_source": {name: dict(Counter(part["source"])) for name, part in sets.items()},
        "vectors": {name: len(v) for name, v in vectors.items()},
        "diseases": {name: {"n": int(part["disease"].nunique()), "of": len(all_labels)} for name, part in sets.items()},
        "diseases_only_outside_train": {
            name: len(set(part["disease"]) - set(sets["train"]["disease"])) for name, part in sets.items() if name != "train"
        },
        "shared_vectors": {
            "train_valid": len(vectors["train"] & vectors["valid"]),
            "train_test": len(vectors["train"] & vectors["test"]),
            "valid_test": len(vectors["valid"] & vectors["test"]),
        },
    }


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
