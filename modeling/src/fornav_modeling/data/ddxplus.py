# DDXPlus 합성 환자(backlog 17) → 버튼 벡터 표. 원본 설명·라이선스는 data/README.md "ddxplus" 절에 있다.
# - 근거 → 버튼: data/tables/ddxplus_evidence_map.csv. 근거 행(value 빈 칸)은 그 근거가 있으면 붙는 부위·증상이고,
#   값 행(value=V_…)은 그 값이 있을 때 더 붙는 부위·증상이다. 부위를 묻는 근거 넷은 값 행을 함께 쓴다(evidence 열에 |로 묶는다).
# - 범주·다중 선택 근거는 값이 원본의 default_value(예: 통증 부위 "nowhere", 세기 0)면 없는 것으로 본다.
# - 병력(is_antecedent)은 버튼 입력이 아니라 쓰지 않는다. 나이·성별도 쓰지 않는다(모델 A가 서빙에서 받지 않는다).
# - 질환 → KCD: data/tables/ddxplus_condition_kcd.csv(icd10-id 기준). 질환명은 표·리포트에 넣지 않고, 라벨은 "ddxplus:<icd10-id>"다.
# - 표준 테이블은 Kaggle(kaggle_symptom.standardize)과 같은 규칙이다. 우리 Symptom이 하나도 없는 환자는 버리고,
#   (질환, 버튼 벡터)가 같은 환자는 한 행으로 합친다. 합친 환자 수는 patients 열에 남긴다(가중치로 쓸지는 backlog 16이 정한다).
# - DDXPlus 자체의 train·validate·test 구분은 쓰지 않는다. 세 파일을 그 순서로 읽고, 분할은 16이 버튼 벡터 단위로 다시 한다.

import csv
import io
import json
import re
import zipfile
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from fornav_modeling.labels.department import NONE, TableError, _kcds, _read, _values
from fornav_modeling.schema import BODY_PARTS, SYMPTOMS, BodyPart, Symptom

RAW = Path("ddxplus")  # data/raw/ 아래
CONDITIONS_FILE = RAW / "release_conditions.json"
EVIDENCES_FILE = RAW / "release_evidences.json"
PATIENT_PARTS = ("train", "validate", "test")
EVIDENCE_MAP = "ddxplus_evidence_map.csv"
CONDITION_KCD = "ddxplus_condition_kcd.csv"
PROCESSED_FILE = Path("ddxplus") / "ddxplus.csv"  # data/processed/ 아래
LOCATION_EVIDENCES = ("E_55", "E_57", "E_133", "E_152")  # 같은 부위 값 목록을 쓰는 다중 선택 근거
LABEL_PREFIX = "ddxplus:"
TRAUMA = ("cut", "bleeding", "burn", "cantmove", "chemical", "foreign")  # 리포트에서 얼마나 비는지 보는 증상
COLUMNS = ["id", "disease", "kcd", "body_parts", "symptoms", "patients"]

Buttons = tuple[list[BodyPart], list[Symptom]]
_ITEM = re.compile(r"'([^']*)'")


@dataclass(frozen=True)
class EvidenceMap:
    evidence: dict[str, Buttons]  # 근거 → 붙는 부위·증상
    value: dict[tuple[str, str], Buttons]  # (근거, 값) → 더 붙는 부위·증상
    defaults: dict[str, str]  # 범주·다중 선택 근거의 기본값(없음과 같다)


# ---------------------------------------------------------------------------
# 원본·표 읽기
# ---------------------------------------------------------------------------
def read_conditions(raw_dir: Path) -> dict[str, str]:
    """질환 이름(PATHOLOGY 열 값) → icd10-id."""
    conditions = json.loads((raw_dir / CONDITIONS_FILE).read_text(encoding="utf-8"))
    return {name: c["icd10-id"] for name, c in conditions.items()}


def read_evidences(raw_dir: Path) -> dict[str, dict]:
    return json.loads((raw_dir / EVIDENCES_FILE).read_text(encoding="utf-8"))


def read_condition_kcd(tables_dir: Path) -> dict[str, list[str]]:
    """icd10-id → KCD 3단 코드 목록."""
    mapping: dict[str, list[str]] = {}
    for row in _read(tables_dir, CONDITION_KCD):
        if row["icd10"] in mapping:
            raise TableError(f"{CONDITION_KCD}: 중복 코드 {row['icd10']!r}")
        mapping[row["icd10"]] = _kcds(CONDITION_KCD, row["kcd"])
    return mapping


def read_evidence_map(tables_dir: Path, evidences: dict[str, dict]) -> EvidenceMap:
    """표를 읽고 원본 근거 정의와 맞춘다. 증상 근거마다 근거 행이 하나 있어야 하고, 부위 근거는 모든 값에 값 행이 있어야 한다."""
    by_evidence: dict[str, Buttons] = {}
    by_value: dict[tuple[str, str], Buttons] = {}
    for row in _read(tables_dir, EVIDENCE_MAP):
        key = f"{row['evidence']}/{row['value']}"
        buttons = (_values(EVIDENCE_MAP, key, row["body_parts"], BODY_PARTS), _values(EVIDENCE_MAP, key, row["symptoms"], SYMPTOMS))
        for evidence in row["evidence"].split("|"):
            if evidence not in evidences or evidences[evidence]["is_antecedent"]:
                raise TableError(f"{EVIDENCE_MAP}: 원본의 증상 근거가 아니다 {evidence!r}")
            if not row["value"]:
                if evidence in by_evidence:
                    raise TableError(f"{EVIDENCE_MAP}: 중복 근거 행 {evidence!r}")
                by_evidence[evidence] = buttons
                continue
            if row["value"] not in evidences[evidence]["possible-values"]:
                raise TableError(f"{EVIDENCE_MAP}: {evidence}에 없는 값 {row['value']!r}")
            if (evidence, row["value"]) in by_value:
                raise TableError(f"{EVIDENCE_MAP}: 중복 값 행 {key!r}")
            by_value[(evidence, row["value"])] = buttons
    symptom_evidences = {k for k, v in evidences.items() if not v["is_antecedent"]}
    if missing := sorted(symptom_evidences - set(by_evidence)):
        raise TableError(f"{EVIDENCE_MAP}: 근거 행이 없는 증상 근거 {missing}")
    for evidence in (e for e in LOCATION_EVIDENCES if e in evidences):
        if missing := [v for v in evidences[evidence]["possible-values"] if (evidence, v) not in by_value]:
            raise TableError(f"{EVIDENCE_MAP}: {evidence}의 값 행이 없다 {missing[:5]}…")
    defaults = {k: str(v["default_value"]) for k, v in evidences.items() if v["data_type"] in ("C", "M")}
    return EvidenceMap(by_evidence, by_value, defaults)


def iter_patients(raw_dir: Path) -> Iterator[tuple[str, str]]:
    """(PATHOLOGY, EVIDENCES) 행을 train → validate → test 순으로."""
    for part in PATIENT_PARTS:
        with zipfile.ZipFile(raw_dir / RAW / f"release_{part}_patients.zip") as zf:
            (member,) = zf.namelist()
            with zf.open(member) as f:
                for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", newline="")):
                    yield row["PATHOLOGY"], row["EVIDENCES"]


# ---------------------------------------------------------------------------
# 변환
# ---------------------------------------------------------------------------
def parse_evidences(raw: str) -> list[tuple[str, str | None]]:
    """ "['E_53', 'E_55_@_V_89', 'E_56_@_2']" → [("E_53", None), ("E_55", "V_89"), ("E_56", "2")]."""
    items = []
    for item in _ITEM.findall(raw):
        evidence, sep, value = item.partition("_@_")
        items.append((evidence, value if sep else None))
    return items


def patient_buttons(evidences: Iterable[tuple[str, str | None]], emap: EvidenceMap) -> Buttons:
    """환자 근거 → (부위, 증상). schema 순서의 목록이다. 기본값인 범주·다중 선택 값과 병력은 건너뛴다."""
    body: set[str] = set()
    symptoms: set[str] = set()
    present: set[str] = set()
    for evidence, value in evidences:
        if evidence not in emap.evidence:
            continue  # 병력(antecedent). 증상 근거는 read_evidence_map이 모두 있는지 확인했다
        if value is not None and value == emap.defaults.get(evidence):
            continue
        present.add(evidence)
        if value is not None and (extra := emap.value.get((evidence, value))):
            body.update(extra[0])
            symptoms.update(extra[1])
    for evidence in present:
        body.update(emap.evidence[evidence][0])
        symptoms.update(emap.evidence[evidence][1])
    return [b for b in BODY_PARTS if b in body], [s for s in SYMPTOMS if s in symptoms]


def standardize(
    patients: Iterable[tuple[str, str]], conditions: dict[str, str], condition_kcd: dict[str, list[str]], emap: EvidenceMap
) -> tuple[pd.DataFrame, dict]:
    """환자 행 → (표준 테이블, 변환 요약). id는 남은 행의 첫 등장 순서로 ddxplus_000001부터 매긴다. 요약에 질환명은 없다."""
    if missing := sorted(set(conditions.values()) - set(condition_kcd)):
        raise TableError(f"{CONDITION_KCD}에 없는 icd10-id {missing}")
    groups: dict[tuple[str, tuple[str, ...], tuple[str, ...]], int] = {}
    raw_rows = dropped = 0
    for pathology, raw in patients:
        raw_rows += 1
        icd10 = conditions[pathology]
        body, symptoms = patient_buttons(parse_evidences(raw), emap)
        if not symptoms:
            dropped += 1
            continue
        key = (icd10, tuple(body), tuple(symptoms))
        groups[key] = groups.get(key, 0) + 1
    records = [
        {
            "id": f"ddxplus_{i:06d}",
            "disease": LABEL_PREFIX + icd10,
            "kcd": "|".join(condition_kcd[icd10]),
            "body_parts": "|".join(body),
            "symptoms": "|".join(symptoms),
            "patients": n,
        }
        for i, ((icd10, body, symptoms), n) in enumerate(groups.items(), start=1)
    ]
    table = pd.DataFrame(records, columns=COLUMNS)
    summary = {
        "raw_patients": raw_rows,
        "dropped_no_symptom": dropped,
        "kept_patients": raw_rows - dropped,
        "rows": len(table),
        "diseases": int(table["disease"].nunique()),
        "diseases_lost": len(set(conditions.values())) - int(table["disease"].nunique()),
    }
    return table, summary


def write_processed(table: pd.DataFrame, processed_dir: Path) -> Path:
    path = processed_dir / PROCESSED_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False, lineterminator="\n")
    return path


def read_processed(processed_dir: Path) -> pd.DataFrame:
    return pd.read_csv(processed_dir / PROCESSED_FILE, dtype=str, keep_default_na=False).astype({"patients": int})


# ---------------------------------------------------------------------------
# 겹침 리포트
# ---------------------------------------------------------------------------
def _vector(body_parts: Iterable[str], symptoms: Iterable[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return tuple(body_parts), tuple(symptoms)


def _split(value: str) -> list[str]:
    return [v for v in value.split("|") if v and v != NONE]


def overlap_report(
    table: pd.DataFrame, summary: dict, kaggle: pd.DataFrame, kaggle_kcd: dict[str, list[str]], hira_codes: set[str]
) -> dict:
    """DDXPlus 표와 Kaggle 표준 테이블의 버튼 벡터 겹침. 분자·분모로 쓰고 질환명은 넣지 않는다."""
    ddx_vectors: dict[tuple, set[str]] = {}
    patients_by_vector: Counter = Counter()
    for row in table.itertuples():
        v = _vector(_split(row.body_parts), _split(row.symptoms))
        ddx_vectors.setdefault(v, set()).add(row.disease)
        patients_by_vector[v] += row.patients
    kaggle_vectors = {_vector(r.body_parts, r.symptoms) for r in kaggle.itertuples()}
    shared = set(ddx_vectors) & kaggle_vectors
    ddx_kcds = {k for kcd in table["kcd"].unique() for k in kcd.split("|")}
    kaggle_codes = {k for codes in kaggle_kcd.values() for k in codes}
    disease_kcd = dict(zip(table["disease"], table["kcd"], strict=False))
    rows_by_symptom = Counter(s for v in table["symptoms"] for s in _split(v))
    rows_by_body = Counter(b for v in table["body_parts"] for b in _split(v))
    kept = summary["kept_patients"]
    return {
        "conversion": summary,
        "vectors": {
            "ddxplus": len(ddx_vectors),
            "kaggle": len(kaggle_vectors),
            "shared": len(shared),
            "ddxplus_only": len(ddx_vectors) - len(shared),
            "union": len(set(ddx_vectors) | kaggle_vectors),
            "ddxplus_multi_disease": sum(len(d) > 1 for d in ddx_vectors.values()),
            "patients_in_shared_vectors": {"n": sum(patients_by_vector[v] for v in shared), "of": kept},
        },
        "kcd": {
            "codes": len(ddx_kcds),
            "missing_in_hira": len(ddx_kcds - hira_codes),
            "diseases_sharing_kaggle_kcd": {
                "n": sum(any(k in kaggle_codes for k in kcd.split("|")) for kcd in disease_kcd.values()),
                "of": len(disease_kcd),
            },
        },
        "buttons_per_row": {
            "ddxplus": _buttons_per_row([_split(b) for b in table["body_parts"]], [_split(x) for x in table["symptoms"]]),
            "kaggle": _buttons_per_row(list(kaggle["body_parts"]), list(kaggle["symptoms"])),
        },
        "rows_by_body_part": {b: {"n": rows_by_body.get(b, 0), "of": len(table)} for b in BODY_PARTS},
        "rows_by_symptom": {s: {"n": rows_by_symptom.get(s, 0), "of": len(table)} for s in SYMPTOMS},
        "trauma_symptom_rows": {s: {"n": rows_by_symptom.get(s, 0), "of": len(table)} for s in TRAUMA},
    }


def _buttons_per_row(body_parts: list[list[str]], symptoms: list[list[str]]) -> dict:
    """행마다 켜진 부위·증상 수의 평균과 분포(1개, 2개, 3개 이상). 앱 사용자는 보통 한두 개를 누른다."""

    def stats(lists: list[list[str]]) -> dict:
        counts = [len(x) for x in lists]
        return {
            "mean": round(sum(counts) / len(counts), 2),
            "one": {"n": sum(c == 1 for c in counts), "of": len(counts)},
            "two": {"n": sum(c == 2 for c in counts), "of": len(counts)},
            "three_or_more": {"n": sum(c >= 3 for c in counts), "of": len(counts)},
        }

    return {"body_parts": stats(body_parts), "symptoms": stats(symptoms)}


def report_markdown(report: dict) -> str:
    c, v, k = report["conversion"], report["vectors"], report["kcd"]

    def frac(d: dict) -> str:
        return f"{d['n']} / {d['of']}"

    lines = [
        "# ddxplus_v0",
        "",
        "DDXPlus 합성 환자를 버튼 벡터로 옮긴 결과(backlog 17). 질환명은 넣지 않는다. 매핑 표는 모두 `reviewed=no`(LLM 초안)다.",
        "",
        "## 변환",
        "",
        "| 항목 | 값 |",
        "|---|---|",
        f"| 원본 환자 | {c['raw_patients']} |",
        f"| 우리 증상이 없어 뺀 환자 | {c['dropped_no_symptom']} / {c['raw_patients']} |",
        f"| 남은 환자 | {c['kept_patients']} / {c['raw_patients']} |",
        f"| (질환, 버튼 벡터) 중복을 지운 행 | {c['rows']} |",
        f"| 질환 | {c['diseases']} (모든 행이 빠진 질환 {c['diseases_lost']}) |",
        "",
        "## 버튼 벡터",
        "",
        "| 항목 | 값 |",
        "|---|---|",
        f"| DDXPlus 고유 벡터 | {v['ddxplus']} |",
        f"| Kaggle 고유 벡터 | {v['kaggle']} |",
        f"| 겹치는 벡터 | {v['shared']} / {v['ddxplus']} |",
        f"| 합친 고유 벡터 | {v['union']} |",
        f"| 질환이 둘 이상인 DDXPlus 벡터 | {v['ddxplus_multi_disease']} / {v['ddxplus']} |",
        f"| 겹치는 벡터에 든 환자 | {frac(v['patients_in_shared_vectors'])} |",
        "",
        "## 행당 켜진 버튼 수",
        "",
        "| 출처 | 부위 평균 | 부위 1개 | 부위 3개 이상 | 증상 평균 | 증상 1개 | 증상 3개 이상 |",
        "|---|---|---|---|---|---|---|",
        *(
            f"| {name} | {b['mean']} | {frac(b['one'])} | {frac(b['three_or_more'])} | {y['mean']} | {frac(y['one'])} | {frac(y['three_or_more'])} |"
            for name, per in report["buttons_per_row"].items()
            for b, y in [(per["body_parts"], per["symptoms"])]
        ),
        "",
        "## KCD",
        "",
        f"- KCD 3단 코드 {k['codes']}개, HIRA 통계에 없는 코드 {k['missing_in_hira']} / {k['codes']}",
        f"- Kaggle 질환과 같은 KCD를 쓰는 질환 {frac(k['diseases_sharing_kaggle_kcd'])}",
        "",
        "## 부위·증상별 행 수",
        "",
        "| 부위 | 행 |",
        "|---|---|",
        *(f"| {b} | {frac(d)} |" for b, d in report["rows_by_body_part"].items()),
        "",
        "| 증상 | 행 |",
        "|---|---|",
        *(f"| {s} | {frac(d)} |" for s, d in report["rows_by_symptom"].items()),
        "",
    ]
    return "\n".join(lines)


def build(raw_dir: Path, tables_dir: Path, processed_dir: Path, reports_dir: Path) -> dict:
    """원본 → 표준 테이블(data/processed/ddxplus/) → Kaggle과의 겹침 리포트(reports/ddxplus_v0.{json,md})."""
    from fornav_modeling.data import hira, kaggle_symptom
    from fornav_modeling.labels.department import read_disease_kcd, read_symptom_map

    emap = read_evidence_map(tables_dir, read_evidences(raw_dir))
    table, summary = standardize(iter_patients(raw_dir), read_conditions(raw_dir), read_condition_kcd(tables_dir), emap)
    write_processed(table, processed_dir)
    kaggle, _ = kaggle_symptom.standardize(kaggle_symptom.read_dataset(raw_dir), read_symptom_map(tables_dir))
    report = overlap_report(table, summary, kaggle, read_disease_kcd(tables_dir), set(hira.read_counts(raw_dir)))
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "ddxplus_v0.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (reports_dir / "ddxplus_v0.md").write_text(report_markdown(report))
    return report
