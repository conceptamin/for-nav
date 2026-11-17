# DDXPlus → 버튼 벡터 변환(backlog 17). 규칙은 작은 가짜 근거 정의로 확인한다.
# 커밋한 매핑 표가 원본 정의와 맞는지는 원본(data/raw/ddxplus, git 제외)이 있을 때만 확인하고, 없으면(CI) 건너뛴다.

import json
from pathlib import Path

import pytest

from fornav_modeling.data import ddxplus
from fornav_modeling.labels.department import TableError

MODELING = Path(__file__).resolve().parents[1]
TABLES = MODELING / "data" / "tables"
RAW = MODELING / "data" / "raw"
REPORTS = MODELING / "reports"
HAS_RAW = (RAW / ddxplus.EVIDENCES_FILE).exists() and (RAW / ddxplus.CONDITIONS_FILE).exists()
needs_raw = pytest.mark.skipif(not HAS_RAW, reason="DDXPlus 원본이 없다(scripts/download_data.py --source ddxplus)")

HEADER = "evidence,value,body_parts,symptoms,note,source,reviewed\n"
SRC = "llm-draft(test),no"
# 가짜 근거 정의: 이진 발열, 다중 선택 통증 부위(기본값 V_0 = 없음), 범주 통증 세기(기본값 0), 병력 하나
EVIDENCES = {
    "E_1": {"is_antecedent": False, "data_type": "B", "default_value": 0, "possible-values": []},
    "E_55": {"is_antecedent": False, "data_type": "M", "default_value": "V_0", "possible-values": ["V_0", "V_1", "V_2"]},
    "E_56": {"is_antecedent": False, "data_type": "C", "default_value": 0, "possible-values": [0, 1, 2]},
    "E_9": {"is_antecedent": True, "data_type": "B", "default_value": 0, "possible-values": []},
}
MAP_ROWS = [
    f"E_1,,whole,fever,,{SRC}",
    f"E_55,,none,pain,,{SRC}",
    f"E_56,,none,none,,{SRC}",
    f"E_55,V_0,none,none,,{SRC}",
    f"E_55,V_1,hand,none,,{SRC}",
    f"E_55,V_2,arm|hand,none,,{SRC}",
]


def write_map(tmp_path: Path, rows: list[str]) -> Path:
    (tmp_path / ddxplus.EVIDENCE_MAP).write_text(HEADER + "\n".join(rows) + "\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def emap(tmp_path) -> ddxplus.EvidenceMap:
    return ddxplus.read_evidence_map(write_map(tmp_path, MAP_ROWS), EVIDENCES)


def test_parse_evidences():
    assert ddxplus.parse_evidences("['E_53', 'E_55_@_V_89', 'E_56_@_2']") == [("E_53", None), ("E_55", "V_89"), ("E_56", "2")]
    assert ddxplus.parse_evidences("[]") == []


def test_buttons_from_evidence_and_value_rows(emap):
    # 부위 값 둘(V_1 손, V_2 팔·손) + 통증 근거 행, 발열, 병력은 무시. 결과는 schema 순서
    body, symptoms = ddxplus.patient_buttons([("E_9", None), ("E_55", "V_2"), ("E_55", "V_1"), ("E_1", None)], emap)
    assert body == ["arm", "hand", "whole"]
    assert symptoms == ["pain", "fever"]


def test_default_value_means_absent(emap):
    # 통증 부위 "없음"(V_0)과 세기 0은 근거가 없는 것과 같다
    assert ddxplus.patient_buttons([("E_55", "V_0"), ("E_56", "0")], emap) == ([], [])
    assert ddxplus.patient_buttons([("E_56", "2")], emap) == ([], [])


def test_standardize_merges_same_disease_and_vector(emap):
    patients = [
        ("A", "['E_55_@_V_1']"),
        ("A", "['E_55_@_V_1', 'E_9']"),  # 병력만 다르다 → 같은 행
        ("B", "['E_55_@_V_1']"),  # 질환이 다르다 → 다른 행
        ("A", "['E_56_@_2']"),  # 우리 증상이 없다 → 뺀다
    ]
    table, summary = ddxplus.standardize(patients, {"A": "x01", "B": "Y02.1"}, {"x01": ["X01"], "Y02.1": ["Y02"]}, emap)
    assert table.to_dict("records") == [
        {"id": "ddxplus_000001", "disease": "ddxplus:x01", "kcd": "X01", "body_parts": "hand", "symptoms": "pain", "patients": 2},
        {"id": "ddxplus_000002", "disease": "ddxplus:Y02.1", "kcd": "Y02", "body_parts": "hand", "symptoms": "pain", "patients": 1},
    ]
    assert summary == {"raw_patients": 4, "dropped_no_symptom": 1, "kept_patients": 3, "rows": 2, "diseases": 2, "diseases_lost": 0}
    again, _ = ddxplus.standardize(patients, {"A": "x01", "B": "Y02.1"}, {"x01": ["X01"], "Y02.1": ["Y02"]}, emap)
    assert again.equals(table)


def test_standardize_needs_every_condition_in_kcd_table(emap):
    with pytest.raises(TableError, match="icd10-id"):
        ddxplus.standardize([], {"A": "x01"}, {}, emap)


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        (MAP_ROWS[1:], "근거 행이 없는"),  # E_1 근거 행이 없다
        ([r for r in MAP_ROWS if ",V_2," not in r], "값 행이 없다"),  # 부위 값 하나가 빠졌다
        ([*MAP_ROWS, f"E_55,V_9,hand,none,,{SRC}"], "없는 값"),
        ([*MAP_ROWS, f"E_9,,none,none,,{SRC}"], "증상 근거가 아니다"),  # 병력은 표에 넣지 않는다
        ([*MAP_ROWS, f"E_1,,whole,fever,,{SRC}"], "중복 근거"),
        ([*MAP_ROWS[:-1], f"E_55,V_2,wrist,none,,{SRC}"], "열거값 밖"),
    ],
)
def test_evidence_map_rejects(tmp_path, rows, message):
    with pytest.raises(TableError, match=message):
        ddxplus.read_evidence_map(write_map(tmp_path, rows), EVIDENCES)


def test_committed_condition_table_is_valid():
    mapping = ddxplus.read_condition_kcd(TABLES)
    assert len(mapping) == 49


@needs_raw
def test_committed_tables_match_raw_definitions():
    evidences = ddxplus.read_evidences(RAW)
    emap = ddxplus.read_evidence_map(TABLES, evidences)
    assert len(emap.evidence) == sum(not v["is_antecedent"] for v in evidences.values()) == 110
    assert set(ddxplus.read_conditions(RAW).values()) == set(ddxplus.read_condition_kcd(TABLES))


@needs_raw
def test_no_disease_names_in_tables_or_report():
    names = [n.lower() for n in ddxplus.read_conditions(RAW)]
    texts = [(TABLES / ddxplus.EVIDENCE_MAP), (TABLES / ddxplus.CONDITION_KCD), REPORTS / "ddxplus_v0.json", REPORTS / "ddxplus_v0.md"]
    for path in texts:
        text = path.read_text(encoding="utf-8").lower()
        assert not [n for n in names if n in text], path.name


def test_committed_report_has_no_disease_labels():
    # 리포트에는 건수만 있다. 질환 라벨(ddxplus:…)이 키나 값으로 새지 않는다
    report = json.loads((REPORTS / "ddxplus_v0.json").read_text(encoding="utf-8"))
    assert ddxplus.LABEL_PREFIX not in json.dumps(report)
