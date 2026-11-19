# 질환·증상 원본(Kaggle Disease Symptom Prediction) → 질환명·증상명 목록. 원본 설명은 data/README.md에 있다.
# 원본 표기 정리: 증상명은 앞뒤 공백이 붙어 있고 `dischromic _patches`처럼 중간에 공백이 섞인 것이 있어 공백을 모두 지운다
# (Symptom-severity.csv의 표기와 같아진다). 질환명은 `Diabetes `처럼 끝 공백이 있어 앞뒤 공백을 지우고 연속 공백을 하나로 줄인다.
# 표준 테이블(standardize): 원본 4,920행은 같은 (질환, 증상 집합)이 6~90번씩 반복된 것이라 304개 고유 행으로 줄인다.
# 반복을 남기면 같은 행이 train과 test에 함께 들어간다. 반복 횟수는 원본을 만든 쪽의 생성 방식이라 가중치로 쓰지 않는다.
# 모델이 보는 것은 버튼 벡터라, 원본 증상이 달라도 버튼 벡터가 같으면 같은 행이다. 그래서 (질환, 버튼 벡터)로 한 번 더 줄인다(backlog 16).
# 증상은 symptom_map.csv로 우리 BodyPart·Symptom으로 옮기고, 우리 Symptom이 하나도 남지 않는 행은 버린다
# (백엔드는 증상이 없으면 진료과를 추천하지 않으므로 그런 입력이 모델까지 오지 않는다).

import csv
from pathlib import Path

import pandas as pd

from fornav_modeling.schema import BODY_PARTS, SYMPTOMS

DATASET_FILE = Path("kaggle_symptom") / "dataset.csv"  # data/raw/ 아래
SEVERITY_FILE = Path("kaggle_symptom") / "Symptom-severity.csv"
NOT_A_SYMPTOM = "prognosis"  # Symptom-severity.csv에 증상처럼 들어 있는 행


def normalize_symptom(name: str) -> str:
    return "".join(name.split())


def normalize_disease(name: str) -> str:
    return " ".join(name.split())


def read_dataset(raw_dir: Path) -> list[tuple[str, list[str]]]:
    """(질환명, 증상명 목록) 행. 빈 칸은 뺀다."""
    with (raw_dir / DATASET_FILE).open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader)
        return [(normalize_disease(row[0]), [normalize_symptom(v) for v in row[1:] if v.strip()]) for row in reader]


def diseases(raw_dir: Path) -> list[str]:
    return sorted({disease for disease, _ in read_dataset(raw_dir)})


def symptoms(raw_dir: Path) -> list[str]:
    """dataset.csv에 나오는 증상명. Symptom-severity.csv의 증상명(prognosis 제외)과 다르면 ValueError."""
    in_dataset = {s for _, row in read_dataset(raw_dir) for s in row}
    with (raw_dir / SEVERITY_FILE).open(encoding="utf-8", newline="") as f:
        in_severity = {normalize_symptom(row["Symptom"]) for row in csv.DictReader(f)} - {NOT_A_SYMPTOM}
    if in_dataset != in_severity:
        raise ValueError(
            f"증상명이 두 파일에서 다르다: dataset만 {sorted(in_dataset - in_severity)}, severity만 {sorted(in_severity - in_dataset)}"
        )
    return sorted(in_dataset)


def standardize(rows: list[tuple[str, list[str]]], symptom_map: dict[str, tuple[list[str], list[str]]]) -> tuple[pd.DataFrame, dict]:
    """원본 행 → (표준 테이블, 변환 요약). (질환, 버튼 벡터)마다 한 행이고, id는 원본 첫 등장 순서로 symptom_0001부터 매긴다.
    body_parts·symptoms는 schema 순서의 목록이라 features/buttons.featurize에 그대로 넘길 수 있다."""
    if missing := sorted({s for _, row in rows for s in row} - set(symptom_map)):
        raise KeyError(f"symptom_map에 없는 증상 {missing}")
    unique: dict[tuple[str, frozenset[str]], list[str]] = {}
    for disease, row in rows:
        unique.setdefault((disease, frozenset(row)), sorted(set(row)))
    vectors: dict[tuple[str, tuple[str, ...], tuple[str, ...]], None] = {}
    dropped, used = [], set()
    for (disease, _), raw in unique.items():
        body_parts = {b for s in raw for b in symptom_map[s][0]}
        symptoms = {y for s in raw for y in symptom_map[s][1]}
        if not symptoms:
            dropped.append(disease)
            continue
        used |= {s for s in raw if symptom_map[s][0] or symptom_map[s][1]}
        key = (disease, tuple(b for b in BODY_PARTS if b in body_parts), tuple(y for y in SYMPTOMS if y in symptoms))
        vectors.setdefault(key, None)
    table = pd.DataFrame(
        [{"disease": d, "body_parts": list(b), "symptoms": list(y)} for d, b, y in vectors], columns=["disease", "body_parts", "symptoms"]
    )
    table.insert(0, "id", [f"symptom_{i:04d}" for i in range(1, len(table) + 1)])
    kept = len(unique) - len(dropped)
    summary = {
        "raw_rows": len(rows),
        "unique_rows": len(unique),
        "dropped_no_symptom": {
            "rows": len(dropped),
            "diseases_lost": len(set(dropped) - set(table["disease"])),
        },  # 질환명은 리포트에 내지 않는다
        "same_disease_and_vector": {"n": kept - len(table), "of": kept},  # 원본 증상은 달라도 버튼 벡터가 같아 합친 행
        "rows": len(table),
        "vectors": len({(b, y) for _, b, y in vectors}),
        "diseases": int(table["disease"].nunique()),
        "kaggle_symptoms": {
            "total": len(symptom_map),
            "to_our_symptom": sum(bool(v[1]) for v in symptom_map.values()),
            "dropped": sum(not v[1] for v in symptom_map.values()),
            "mapped_seen_in_rows": len(used),
        },
        "button_features_seen": {
            "body_parts": sorted({b for _, bs, _ in vectors for b in bs}, key=BODY_PARTS.index),
            "symptoms": sorted({y for _, _, ys in vectors for y in ys}, key=SYMPTOMS.index),
        },
    }
    return table, summary
