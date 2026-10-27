# 응급도 원본(PLOS ONE S1 Appendix xlsx) → 표준 테이블. 원본 열 설명은 data/README.md에 있다.
# 표준 테이블 한 행은 featurize(features/buttons.py)에 그대로 넘길 수 있는 버튼 입력 열 + 라벨 + 활력징후(09 전용)다.
# 식별 정보 열은 원본에 없다(backlog 02). 버튼·라벨·활력징후에 쓰지 않는 열과 내원 후 결과 열(진단, 처치 결과,
# 체류 시간, 오분류 여부)은 라벨 누출을 막으려고 여기서 뺀다.

import csv
from pathlib import Path

import pandas as pd

from fornav_modeling.features.buttons import MENTALS, SEXES, age_to_group
from fornav_modeling.features.vitals import VITAL_FEATURES
from fornav_modeling.labels.ktas import ktas_to_acuity
from fornav_modeling.schema import BODY_PARTS, SYMPTOMS

RAW_FILE = Path("kaggle_triage") / "pone.0216972.s001.xlsx"  # data/raw/ 아래
CHIEF_COMPLAINT_MAP = "chief_complaint_map.csv"  # data/tables/ 아래

# 원본 코드값(data/README.md). Mental은 AVPU 순서 1~4다.
_SEX = {1: "female", 2: "male"}
_INJURY = {1: False, 2: True}
_MENTAL = dict(enumerate(MENTALS, start=1))
_VITAL_COLUMNS = {"SBP": "sbp", "DBP": "dbp", "HR": "hr", "RR": "rr", "BT": "bt", "Saturation": "saturation"}
_NOT_MEASURED = "측불"  # 측정 불가

assert set(_SEX.values()) == set(SEXES) and tuple(_VITAL_COLUMNS.values()) == VITAL_FEATURES


def read_raw(raw_dir: Path) -> pd.DataFrame:
    return pd.read_excel(raw_dir / RAW_FILE, sheet_name=0)


def normalize_complaint(text: str) -> str:
    """주증상 자유 텍스트의 비교 키. 앞뒤 공백 제거, 소문자, 연속 공백 하나로."""
    return " ".join(str(text).strip().lower().split())


def read_chief_complaint_map(tables_dir: Path) -> dict[str, tuple[list[str], list[str]]]:
    """정규화한 주증상 → (body_parts, symptoms). 열거값 밖의 값이나 중복 키가 있으면 ValueError."""
    mapping = {}
    with (tables_dir / CHIEF_COMPLAINT_MAP).open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            key = row["chief_complaint"]
            body_parts = [v for v in row["body_parts"].split("|") if v]
            symptoms = [v for v in row["symptoms"].split("|") if v]
            if key != normalize_complaint(key) or key in mapping:
                raise ValueError(f"{CHIEF_COMPLAINT_MAP}: 정규화되지 않았거나 중복된 키 {key!r}")
            if unknown := (set(body_parts) - set(BODY_PARTS)) | (set(symptoms) - set(SYMPTOMS)):
                raise ValueError(f"{CHIEF_COMPLAINT_MAP}: {key!r}에 열거값 밖의 값 {sorted(unknown)}")
            if not row["source"] or row["reviewed"] not in ("yes", "no"):
                raise ValueError(f"{CHIEF_COMPLAINT_MAP}: {key!r}의 source가 비었거나 reviewed가 yes/no가 아니다")
            mapping[key] = (body_parts, symptoms)
    return mapping


def standardize(raw: pd.DataFrame, chief_complaint_map: dict[str, tuple[list[str], list[str]]]) -> pd.DataFrame:
    """원본 → 표준 테이블. id는 원본 행 순서로 triage_0001부터 매긴다.
    매핑 표에 없는 주증상이 있으면 KeyError — 표에 행을 더한 뒤 다시 돌린다."""
    raw = raw.reset_index(drop=True)
    complaints = raw["Chief_complain"].map(normalize_complaint)
    if missing := sorted(set(complaints) - set(chief_complaint_map)):
        raise KeyError(f"{CHIEF_COMPLAINT_MAP}에 없는 주증상 {len(missing)}개: {missing[:5]}")
    mapped = complaints.map(chief_complaint_map)

    # 통증 없음(Pain=0)은 0점. 통증 있음인데 NRS가 빈 행은 점수를 모르므로 NaN.
    pain_score = raw["NRS_pain"].where(raw["Pain"] == 1, 0.0).astype("float64")

    table = pd.DataFrame(
        {
            "id": [f"triage_{i:04d}" for i in range(1, len(raw) + 1)],
            # 버튼 입력(featurize가 읽는 키)
            "body_parts": mapped.map(lambda m: m[0]),
            "symptoms": mapped.map(lambda m: m[1]),
            "pain_score": pain_score,
            "mental": raw["Mental"].map(_strict(_MENTAL, "Mental")),
            "age_group": raw["Age"].map(age_to_group),
            "onset": pd.Series([None] * len(raw), dtype="object"),  # 원본에 없음
            "sex": raw["Sex"].map(_strict(_SEX, "Sex")),
            "injury": raw["Injury"].map(_strict(_INJURY, "Injury")).astype(bool),
            # 버튼 입력의 근거(오류 분석용)
            "age": raw["Age"].astype("float64"),
            "chief_complaint": complaints,
            "chief_complaint_mapped": mapped.map(lambda m: bool(m[0] or m[1])),
            # 활력징후(09 전용)
            **{name: _vital(raw[column]) for column, name in _VITAL_COLUMNS.items()},
            # 라벨: 전문가 KTAS. 간호사 KTAS는 비교용
            "ktas_expert": raw["KTAS_expert"].astype("int64"),
            "ktas_rn": raw["KTAS_RN"].astype("int64"),
            "acuity": raw["KTAS_expert"].map(ktas_to_acuity),
            "acuity_rn": raw["KTAS_RN"].map(ktas_to_acuity),
        }
    )
    return table


def _strict(mapping: dict, column: str):
    def lookup(value):
        if value not in mapping:
            raise ValueError(f"원본 {column} 열에 모르는 코드: {value!r}")
        return mapping[value]

    return lookup


def _vital(column: pd.Series) -> pd.Series:
    """측정 불가·빈칸 → NaN. 그 밖의 숫자가 아닌 값은 ValueError로 멈춘다."""
    cleaned = column.map(lambda v: None if isinstance(v, str) and v.strip() in (_NOT_MEASURED, "") else v)
    return pd.to_numeric(cleaned, errors="raise").astype("float64")
