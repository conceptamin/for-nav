# KTAS → 응급도 3단계 변환, 진료과 표(backlog 05).

import re
from pathlib import Path

import pytest

from fornav_modeling.data import hira
from fornav_modeling.labels import department as dept
from fornav_modeling.labels.ktas import ACUITIES, ktas_to_acuity
from fornav_modeling.schema import DEPARTMENTS


def test_label_order_is_fixed():
    assert ACUITIES == ("emergency", "today", "outpatient")


@pytest.mark.parametrize(("ktas", "acuity"), [(1, "emergency"), (2, "emergency"), (3, "today"), (4, "outpatient"), (5, "outpatient")])
def test_ktas_to_acuity(ktas, acuity):
    assert ktas_to_acuity(ktas) == acuity


@pytest.mark.parametrize("ktas", [0, 6, -1, None, True, "1"])
def test_invalid_ktas_raises(ktas):
    with pytest.raises(ValueError):
        ktas_to_acuity(ktas)


# ---------------------------------------------------------------------------
# 진료과 표(backlog 05). 커밋된 표만 읽고 원본(data/raw)은 쓰지 않는다. HIRA 적재는 작은 가짜 파일로 확인한다.
# ---------------------------------------------------------------------------

MODELING = Path(__file__).resolve().parents[1]
TABLES = MODELING / "data" / "tables"
SPLITS = MODELING / "data" / "splits"
TRIAGE_RULES = MODELING.parent / "backend" / "app" / "rules" / "triage.py"


def test_committed_input_tables_are_valid():
    assert len(dept.read_disease_kcd(TABLES)) == 41
    dept.read_button_kcd(TABLES)
    dept.read_guide(TABLES)


def test_committed_symptom_map_is_valid():
    mapping = dept.read_symptom_map(TABLES)
    assert len(mapping) == 131
    assert sum(bool(symptoms) for _, symptoms in mapping.values()) == 75


@pytest.mark.parametrize(
    "row",
    [
        "itching,skin,rash,,,no",
        "itching,nose,rash,,x,no",
        "itching,skin,rash|itch,,x,no",
        "itching,skin|skin,rash,,x,no",
        "itching,,rash,,x,no",
    ],
)
def test_read_symptom_map_rejects(tmp_path, row):
    _write(tmp_path / dept.SYMPTOM_MAP, "kaggle_symptom,body_parts,symptoms,note,source,reviewed\n" + row + "\n")
    with pytest.raises(dept.TableError):
        dept.read_symptom_map(tmp_path)


def test_read_symptom_map_none_is_empty(tmp_path):
    _write(tmp_path / dept.SYMPTOM_MAP, "kaggle_symptom,body_parts,symptoms,note,source,reviewed\nfatigue,whole,none,,x,no\n")
    assert dept.read_symptom_map(tmp_path) == {"fatigue": (["whole"], [])}


def test_committed_disease_table_covers_every_disease():
    table = dept.read_disease_department(TABLES)
    assert set(table) == set(dept.read_disease_kcd(TABLES))


def test_committed_button_table_matches_input_combos():
    table = dept.read_button_department(TABLES)
    combos = {dept.combo_id(r["body_part"], r["symptom"], r["injury"]) for r in dept.read_button_kcd(TABLES)}
    assert set(table) == combos


def test_button_table_agrees_with_backend_clear_cases():
    assert dept.clear_case_conflicts(dept.read_button_department(TABLES)) == []


def test_valid_ids_are_guide_combos():
    assert (SPLITS / dept.VALID_IDS).read_text().split() == sorted(dept.read_guide(TABLES))


def test_clear_case_mirrors_backend_rule_order():
    # clear_case는 백엔드 recommend_department의 앞 세 분기를 옮긴 것이다. 백엔드가 순서나 조건을 바꾸면 여기서 깨진다.
    body = TRIAGE_RULES.read_text().split("def recommend_department", 1)[1]
    branches = re.findall(r'if (.+?):\n\s+return DepartmentPair\(primary="(\w+)"', body)
    assert branches[:3] == [('"chemical" in s', "occ"), ('"eye" in b or "foreign" in s', "ophth"), ('"teeth" in b', "dental")]
    assert dept.clear_case("eye", "chemical") is None
    assert dept.clear_case("arm", "foreign") == "ophth"
    assert dept.clear_case("teeth", "pain") == "dental"
    assert dept.clear_case("hand", "cut") is None


def test_trim_drops_small_and_renormalizes():
    assert dept.trim({"internal": 0.6, "family": 0.395, "ent": 0.005}) == {"internal": 0.603, "family": 0.397}


def test_top_breaks_ties_by_department_order():
    assert dept.top({"family": 0.5, "ortho": 0.5}, 1) == ["ortho"]


@pytest.mark.parametrize("value", ["occ:0.5|derm:0.4", "occ:0.5|xyz:0.5", "occ:0.5|occ:0.5", "occ:1.5|derm:-0.5"])
def test_parse_manual_rejects_bad_distributions(value):
    with pytest.raises(dept.TableError):
        dept.parse_manual(value)


def test_parse_manual():
    assert dept.parse_manual("occ:0.4|internal:0.6") == {"occ": 0.4, "internal": 0.6}


def test_same_combo():
    assert dept.same_combo("hand-cut-yes", "hand-cut-any")
    assert dept.same_combo("hand-cut-yes", "hand-cut-yes")
    assert not dept.same_combo("hand-cut-yes", "hand-cut-no")
    assert not dept.same_combo("hand-cut-yes", "arm-cut-yes")


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


BUTTON_HEADER = "body_part,symptom,injury,kcd,manual,note,source,reviewed\n"


@pytest.mark.parametrize(
    "rows",
    [
        "hand,cut,yes,S61,occ:1,,x,no\n",  # kcd와 manual을 둘 다 채움
        "hand,cut,yes,,,,x,no\n",  # 둘 다 비움
        "hand,cut,yes,S61,,,x,no\nhand,cut,any,S61,,,x,no\n",  # any와 yes 혼용
        "hand,cut,yes,S61,,,x,no\nhand,cut,yes,S62,,,x,no\n",  # 중복
        "nose,cut,yes,S61,,,x,no\n",  # 열거값 밖
        "hand,cut,maybe,S61,,,x,no\n",
        "hand,cut,yes,S6,,,x,no\n",  # KCD 형식
        "hand,cut,yes,S61,,,,no\n",  # source 없음
        "hand,cut,yes,S61,,,x,maybe\n",
    ],
)
def test_read_button_kcd_rejects(tmp_path, rows):
    _write(tmp_path / dept.BUTTON_KCD, BUTTON_HEADER + rows)
    with pytest.raises(dept.TableError):
        dept.read_button_kcd(tmp_path)


@pytest.mark.parametrize(
    "rows",
    [
        "hand,cut,yes,ortho,0.6,x,no\nhand,cut,yes,family,0.3,x,no\n",  # 합이 1이 아님
        "hand,cut,yes,ortho,0.6,x,no\nhand,cut,yes,ortho,0.4,x,no\n",  # 진료과 중복
        "hand,cut,yes,ortho,0.6,x,no\nhand,cut,yes,urology,0.4,x,no\n",  # 열거값 밖
        "nose,cut,yes,ortho,1.0,x,no\n",
    ],
)
def test_read_button_department_rejects(tmp_path, rows):
    _write(tmp_path / dept.BUTTON_DEPARTMENT, ",".join(dept.BUTTON_COLUMNS) + "\n" + rows)
    with pytest.raises(dept.TableError):
        dept.read_button_department(tmp_path)


def test_clear_case_conflicts_finds_wrong_top():
    table = {"eye-pain-no": {"family": 0.6, "ophth": 0.4}, "teeth-pain-any": {"dental": 1.0}, "eye-chemical-any": {"occ": 1.0}}
    assert dept.clear_case_conflicts(table) == ["eye-pain-no"]


GUIDE_HEADER = "body_part,symptom,injury,department,alt,url,site,evidence,note,source,reviewed\n"


@pytest.mark.parametrize(
    "rows",
    [
        "hand,cut,yes,ortho,ortho,https://a,s,e,,x,no\n",  # 1·2순위 같음
        "hand,cut,yes,urology,,https://a,s,e,,x,no\n",
        "hand,cut,yes,ortho,,http://a,s,e,,x,no\n",  # https 아님
        "hand,cut,yes,ortho,,https://a,s,e,,x,no\nhand,cut,yes,surgery,,https://b,s,e,,x,no\n",
    ],
)
def test_read_guide_rejects(tmp_path, rows):
    _write(tmp_path / dept.GUIDE, GUIDE_HEADER + rows)
    with pytest.raises(dept.TableError):
        dept.read_guide(tmp_path)


# HIRA 적재 ------------------------------------------------------------------


def test_every_hira_department_maps_to_known_value():
    assert {v for v in hira.HIRA_DEPARTMENTS.values() if v is not None} <= set(DEPARTMENTS)


def test_hira_department_rejects_unknown_name():
    with pytest.raises(ValueError):
        hira.hira_department("우주의학과", "A00")


@pytest.mark.parametrize(("kcd", "expected"), [("I61", "neuro"), ("S06", "neuro"), ("G43", "neuro"), ("M54", "ortho"), ("G56", "ortho")])
def test_neurosurgery_brain_codes_go_to_neuro(kcd, expected):
    assert hira.hira_department("신경외과", kcd) == expected


def test_read_counts_sums_both_files_and_drops_unmapped(tmp_path):
    header = "진료년도,{col},주상병코드,환자수,명세서청구건수,입내원일수,보험자부담금(선별포함),요양급여비용총액(선별포함)\n"
    (tmp_path / "hira").mkdir()
    for file, column in hira.RAW_FILES.items():
        rows = "2025,내과,J00,10 ,1 ,1 ,1 ,1 \n2025,소아청소년과,J00,99 ,1 ,1 ,1 ,1 \n2025,일반의,J00,5 ,1 ,1 ,1 ,1 \n"
        (tmp_path / file).write_text(header.format(col=column) + rows, encoding="cp949")
    counts = hira.read_counts(tmp_path)
    assert counts == {"J00": {"internal": 20, "family": 10}}
    assert hira.department_ratio(counts, ["J00"]) == {"internal": 2 / 3, "family": 1 / 3}
    with pytest.raises(KeyError):
        hira.department_ratio(counts, ["J00", "Z99"])
