# 질환·증상 원본(Kaggle Disease Symptom Prediction) → 질환명·증상명 목록. 원본 설명은 data/README.md에 있다.
# 원본 표기 정리: 증상명은 앞뒤 공백이 붙어 있고 `dischromic _patches`처럼 중간에 공백이 섞인 것이 있어 공백을 모두 지운다
# (Symptom-severity.csv의 표기와 같아진다). 질환명은 `Diabetes `처럼 끝 공백이 있어 앞뒤 공백을 지우고 연속 공백을 하나로 줄인다.

import csv
from pathlib import Path

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
