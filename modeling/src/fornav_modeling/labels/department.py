# 진료과 라벨 표: 질환 → 진료과 비율(모델 A), 버튼 조합 → 진료과 분포(모델 B), 진료과 검증셋.
# 사람이 고치는 입력 표(data/tables/)
#   disease_kcd.csv       Kaggle 질환 → KCD 3단 코드(|로 여러 개)
#   button_kcd.csv        (부위, 증상, 손상 여부) → KCD 코드, 또는 HIRA에 없는 분포를 직접 적은 manual 열
#   department_guide.csv  병원·공공 안내가 말하는 조합별 진료과 — Top-2 적중률의 정답(검증셋)
#   symptom_map.csv       Kaggle 증상 → 우리 BodyPart·Symptom(모델 A가 Kaggle 행을 버튼 입력으로 옮길 때 쓴다). 없으면 none
# 만드는 표(build_tables.py가 쓴다. 손으로 고치지 않는다)
#   disease_department.csv, button_department.csv  KCD 코드의 HIRA 환자 비율. 1% 미만은 버리고 다시 합을 1로 맞춘다
# 질환명은 이 모듈과 모델 A 내부까지만 쓴다(06 이후 산출물에 내보내지 않는다).
# DDXPlus 질환(backlog 16): KCD 3단 코드가 Kaggle 질환과 겹치면 그 Kaggle 라벨로 합치고, 아니면 `ddxplus:<KCD>` 라벨을 쓴다
#   (KCD가 같은 DDXPlus 질환끼리도 한 라벨이 된다). 진료과 비율은 어느 쪽이든 그 KCD의 HIRA 분포다(사용자 결정, 2026-11-19).

import csv
import hashlib
import re
from collections import Counter
from pathlib import Path
from typing import NamedTuple

from fornav_modeling.data.hira import SOURCE as HIRA_SOURCE
from fornav_modeling.data.hira import department_ratio
from fornav_modeling.schema import BODY_PARTS, DEPARTMENTS, SYMPTOMS, BodyPart, Department, Symptom

DISEASE_KCD = "disease_kcd.csv"
BUTTON_KCD = "button_kcd.csv"
GUIDE = "department_guide.csv"
SYMPTOM_MAP = "symptom_map.csv"
NONE = "none"
DISEASE_DEPARTMENT = "disease_department.csv"
BUTTON_DEPARTMENT = "button_department.csv"
VALID_IDS = "dept_valid.txt"  # data/splits/ 아래
# 최종 평가용 안내 조합(backlog 18). 조정용(GUIDE)과 다른 출처에서 모아 사람이 검토한 행만 TEST_IDS로 고정한다.
# 정답 표(GUIDE_TEST)는 고정 명령과 평가 명령만 읽는다. 학습은 조합 id 목록(TEST_IDS)만 읽어 같은 조합을 학습에서 뺀다.
GUIDE_TEST = "department_guide_test.csv"
TEST_IDS = "dept_test.txt"  # data/splits/ 아래
TEST_IDS_HASH = "dept_test.sha256"  # 고정한 행(정답 포함)의 sha256

DISEASE_COLUMNS = ["disease", "kcd", "department", "ratio", "source", "reviewed"]
BUTTON_COLUMNS = ["body_part", "symptom", "injury", "department", "prob", "source", "reviewed"]
GUIDE_COLUMNS = ["body_part", "symptom", "injury", "department", "alt", "url", "site", "evidence", "note", "source", "reviewed"]
INJURIES = ("yes", "no", "any")
PROB_FLOOR = 0.01  # 이보다 작은 비율은 통계 잡음으로 보고 버린다
SUM_TOLERANCE = 1e-3  # 소수 넷째 자리 반올림 오차
_KCD = re.compile(r"[A-Z]\d\d")

Distribution = dict[Department, float]


class TableError(ValueError):
    pass


def combo_id(body_part: str, symptom: str, injury: str) -> str:
    return f"{body_part}-{symptom}-{injury}"


# ---------------------------------------------------------------------------
# 입력 표
# ---------------------------------------------------------------------------
def _read(tables_dir: Path, name: str) -> list[dict[str, str]]:
    with (tables_dir / name).open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if not row["source"] or row["reviewed"] not in ("yes", "no"):
            raise TableError(f"{name}: source가 비었거나 reviewed가 yes/no가 아닌 행 {row}")
    return rows


def _kcds(name: str, value: str) -> list[str]:
    codes = [v for v in value.split("|") if v]
    if bad := [c for c in codes if not _KCD.fullmatch(c)]:
        raise TableError(f"{name}: KCD 3단 코드 형식이 아니다 {bad}")
    return codes


def _check_combo(name: str, row: dict[str, str]) -> None:
    if row["body_part"] not in BODY_PARTS or row["symptom"] not in SYMPTOMS or row["injury"] not in INJURIES:
        raise TableError(f"{name}: 열거값 밖의 조합 {combo_id(row['body_part'], row['symptom'], row['injury'])}")


def parse_manual(value: str) -> Distribution:
    """'occ:0.4|internal:0.6' → 분포. 합이 1이 아니거나 진료과가 열거값 밖이면 TableError."""
    dist: Distribution = {}
    for part in value.split("|"):
        department, _, prob = part.partition(":")
        if department not in DEPARTMENTS or department in dist:
            raise TableError(f"manual 분포에 모르는 진료과이거나 중복: {value!r}")
        dist[department] = float(prob)
    check_distribution(f"manual {value!r}", dist)
    return dist


def read_disease_kcd(tables_dir: Path) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for row in _read(tables_dir, DISEASE_KCD):
        if row["disease"] in mapping:
            raise TableError(f"{DISEASE_KCD}: 중복 질환 {row['disease']!r}")
        mapping[row["disease"]] = _kcds(DISEASE_KCD, row["kcd"])
    return mapping


DDXPLUS_LABEL_PREFIX = "ddxplus:"


def ddxplus_labels(condition_kcd: dict[str, list[str]], disease_kcd: dict[str, list[str]]) -> dict[str, str]:
    """DDXPlus icd10-id → 모델 A 질환 라벨. KCD가 Kaggle 질환 하나와 겹치면 그 라벨, 없으면 ddxplus:<KCD>. 둘 이상과 겹치면 TableError."""
    labels = {}
    for icd10, codes in condition_kcd.items():
        hits = [disease for disease, kcds in disease_kcd.items() if set(kcds) & set(codes)]
        if len(hits) > 1:
            raise TableError(f"DDXPlus {icd10}의 KCD {codes}가 Kaggle 질환 {len(hits)}개와 겹친다. 합칠 라벨을 정한다")
        labels[icd10] = hits[0] if hits else DDXPLUS_LABEL_PREFIX + "|".join(codes)
    return labels


def ddxplus_label_kcd(condition_kcd: dict[str, list[str]], disease_kcd: dict[str, list[str]]) -> dict[str, list[str]]:
    """Kaggle로 합치지 않은 DDXPlus 라벨 → KCD 코드. disease_department.csv에 Kaggle 질환과 함께 쓴다."""
    labels = ddxplus_labels(condition_kcd, disease_kcd)
    return {label: condition_kcd[icd10] for icd10, label in sorted(labels.items()) if label.startswith(DDXPLUS_LABEL_PREFIX)}


def read_button_kcd(tables_dir: Path) -> list[dict[str, str]]:
    """조합마다 kcd와 manual 중 하나만 있다. 같은 (부위, 증상)에 any와 yes/no가 섞이면 안 된다."""
    rows = _read(tables_dir, BUTTON_KCD)
    seen: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        _check_combo(BUTTON_KCD, row)
        cid = combo_id(row["body_part"], row["symptom"], row["injury"])
        if bool(row["kcd"]) == bool(row["manual"]):
            raise TableError(f"{BUTTON_KCD}: {cid}는 kcd와 manual 중 하나만 채운다")
        if row["kcd"]:
            _kcds(BUTTON_KCD, row["kcd"])
        else:
            parse_manual(row["manual"])
        injuries = seen.setdefault((row["body_part"], row["symptom"]), set())
        if row["injury"] in injuries or "any" in injuries or (injuries and row["injury"] == "any"):
            raise TableError(f"{BUTTON_KCD}: {cid}가 중복이거나 any와 yes/no가 섞였다")
        injuries.add(row["injury"])
    return rows


def _values(name: str, key: str, value: str, allowed: tuple[str, ...]) -> list[str]:
    if value == NONE:
        return []
    values = value.split("|")
    if bad := [v for v in values if v not in allowed] or len(set(values)) != len(values):
        raise TableError(f"{name}: {key}에 열거값 밖이거나 중복된 값 {bad or values}")
    return values


def read_symptom_map(tables_dir: Path) -> dict[str, tuple[list[BodyPart], list[Symptom]]]:
    """Kaggle 증상 → (body_parts, symptoms). none은 빈 목록이다."""
    mapping: dict[str, tuple[list[BodyPart], list[Symptom]]] = {}
    for row in _read(tables_dir, SYMPTOM_MAP):
        key = row["kaggle_symptom"]
        if key in mapping:
            raise TableError(f"{SYMPTOM_MAP}: 중복 증상 {key!r}")
        mapping[key] = (_values(SYMPTOM_MAP, key, row["body_parts"], BODY_PARTS), _values(SYMPTOM_MAP, key, row["symptoms"], SYMPTOMS))
    return mapping


# ---------------------------------------------------------------------------
# 만드는 표
# ---------------------------------------------------------------------------
def trim(dist: Distribution) -> Distribution:
    """PROB_FLOOR 미만을 버리고 합을 1로 맞춘 뒤 소수 넷째 자리로 반올림한다. 확률이 큰 순."""
    kept = {d: p for d, p in dist.items() if p >= PROB_FLOOR}
    total = sum(kept.values())
    return {d: round(p / total, 4) for d, p in sorted(kept.items(), key=lambda kv: (-kv[1], DEPARTMENTS.index(kv[0])))}


def build_disease_department(disease_kcd: dict[str, list[str]], counts: dict[str, Counter]) -> list[dict[str, str]]:
    """질환마다 KCD 코드의 HIRA 비율. KCD 매핑이 아직 사람 검토 전이라 reviewed는 모두 no다."""
    rows = []
    for disease, kcds in disease_kcd.items():
        for department, ratio in trim(department_ratio(counts, kcds)).items():
            rows.append(
                {
                    "disease": disease,
                    "kcd": "|".join(kcds),
                    "department": department,
                    "ratio": f"{ratio:.4f}",
                    "source": HIRA_SOURCE,
                    "reviewed": "no",
                }
            )
    return rows


def build_button_department(button_kcd: list[dict[str, str]], counts: dict[str, Counter]) -> list[dict[str, str]]:
    """조합마다 KCD 코드의 HIRA 비율(source=hira:2025) 또는 manual 분포(source=입력 표의 source)."""
    rows = []
    for row in button_kcd:
        if row["kcd"]:
            dist, source = trim(department_ratio(counts, row["kcd"].split("|"))), HIRA_SOURCE
        else:
            dist, source = parse_manual(row["manual"]), row["source"]
        for department, prob in dist.items():
            rows.append(
                {k: row[k] for k in ("body_part", "symptom", "injury")}
                | {"department": department, "prob": f"{prob:.4f}", "source": source, "reviewed": row["reviewed"]}
            )
    return rows


def write_table(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# 만든 표 읽기·검증
# ---------------------------------------------------------------------------
def check_distribution(where: str, dist: Distribution) -> None:
    if unknown := set(dist) - set(DEPARTMENTS):
        raise TableError(f"{where}: Department 열거값 밖의 진료과 {sorted(unknown)}")
    if any(p <= 0 for p in dist.values()) or abs(sum(dist.values()) - 1) > SUM_TOLERANCE:
        raise TableError(f"{where}: 확률이 0 이하이거나 합이 1이 아니다 ({sum(dist.values()):.4f})")


def _read_long(tables_dir: Path, name: str, key_columns: tuple[str, ...], value_column: str) -> dict[tuple[str, ...], Distribution]:
    tables: dict[tuple[str, ...], Distribution] = {}
    for row in _read(tables_dir, name):
        key = tuple(row[c] for c in key_columns)
        dist = tables.setdefault(key, {})
        if row["department"] in dist:
            raise TableError(f"{name}: {key}에 진료과 {row['department']} 행이 중복")
        dist[row["department"]] = float(row[value_column])
    for key, dist in tables.items():
        check_distribution(f"{name} {key}", dist)
    return tables


def read_disease_department(tables_dir: Path) -> dict[str, Distribution]:
    return {key[0]: dist for key, dist in _read_long(tables_dir, DISEASE_DEPARTMENT, ("disease",), "ratio").items()}


def read_button_department(tables_dir: Path) -> dict[str, Distribution]:
    """combo_id → 분포. 열거값·any 혼용 검사는 입력 표(read_button_kcd)와 같다."""
    tables = _read_long(tables_dir, BUTTON_DEPARTMENT, ("body_part", "symptom", "injury"), "prob")
    for body_part, symptom, injury in tables:
        _check_combo(BUTTON_DEPARTMENT, {"body_part": body_part, "symptom": symptom, "injury": injury})
    return {combo_id(*key): dist for key, dist in tables.items()}


def top(dist: Distribution, k: int) -> list[Department]:
    return [d for d, _ in sorted(dist.items(), key=lambda kv: (-kv[1], DEPARTMENTS.index(kv[0])))[:k]]


# ---------------------------------------------------------------------------
# 백엔드 명확 케이스 규칙과 대조
# ---------------------------------------------------------------------------
def clear_case(body_part: BodyPart, symptom: Symptom) -> Department | None:
    """백엔드 recommend_department(backend/app/rules/triage.py)의 명확 케이스: 눈·이물감 → 안과, 치아 → 치과.
    백엔드는 chemical을 이보다 먼저 봐 occ를 내므로, chemical 조합은 명확 케이스가 아니다."""
    if symptom == "chemical":
        return None
    if body_part == "eye" or symptom == "foreign":
        return "ophth"
    if body_part == "teeth":
        return "dental"
    return None


def clear_case_conflicts(button_department: dict[str, Distribution]) -> list[str]:
    """명확 케이스 조합인데 표의 1순위가 규칙과 다른 combo_id."""
    conflicts = []
    for cid, dist in button_department.items():
        body_part, symptom, _ = cid.split("-")
        expected = clear_case(body_part, symptom)
        if expected is not None and top(dist, 1) != [expected]:
            conflicts.append(cid)
    return conflicts


# ---------------------------------------------------------------------------
# 진료과 검증셋
# ---------------------------------------------------------------------------
class GuideAnswer(NamedTuple):
    department: Department  # 정답 1순위
    alt: Department | None  # 2순위(없으면 None)
    reviewed: bool


def read_guide(tables_dir: Path, name: str = GUIDE) -> dict[str, GuideAnswer]:
    """combo_id → 정답. 출처 URL이 없거나 진료과가 열거값 밖이면 TableError."""
    guide: dict[str, GuideAnswer] = {}
    for row in _read(tables_dir, name):
        _check_combo(name, row)
        cid = combo_id(row["body_part"], row["symptom"], row["injury"])
        alt = row["alt"] or None
        if row["department"] not in DEPARTMENTS or (alt is not None and (alt not in DEPARTMENTS or alt == row["department"])):
            raise TableError(f"{name}: {cid}의 진료과가 열거값 밖이거나 1·2순위가 같다")
        if not row["url"].startswith("https://") or cid in guide:
            raise TableError(f"{name}: {cid}의 url이 https가 아니거나 조합이 중복")
        guide[cid] = GuideAnswer(row["department"], alt, row["reviewed"] == "yes")
    return guide


INJURY_FLAGS = {"yes": True, "no": False, "any": None}  # combo_id의 손상 여부 → 버튼 입력값(any는 모름)
TRAUMA_SYMPTOMS = ("cut", "burn", "chemical", "foreign")


def combo_intake(cid: str) -> dict:
    """combo_id → features/buttons.featurize에 넘길 입력 dict(부위 1, 증상 1, 손상 여부)."""
    body_part, symptom, injury = cid.split("-")
    return {"body_parts": [body_part], "symptoms": [symptom], "injury": INJURY_FLAGS[injury]}


def is_trauma(cid: str) -> bool:
    """외상·산재 조합: 손상 있음이거나 베임·화상·화학물질·이물감."""
    _, symptom, injury = cid.split("-")
    return injury == "yes" or symptom in TRAUMA_SYMPTOMS


def guide_set(tables_dir: Path, splits_dir: Path) -> tuple[list[str], dict[str, GuideAnswer]]:
    """진료과 검증셋: dept_valid.txt의 combo_id 순서와 정답. 두 파일이 어긋나면 TableError."""
    guide = read_guide(tables_dir)
    ids = (splits_dir / VALID_IDS).read_text().split()
    if ids != sorted(guide):
        raise TableError(f"{VALID_IDS}와 {GUIDE}가 다르다. scripts/build_tables.py를 다시 돌린다")
    return ids, guide


def _guide_test_rows(tables_dir: Path) -> list[dict[str, str]]:
    """최종 평가용 표에서 사람이 검토한(reviewed=yes) 행. combo_id 순."""
    read_guide(tables_dir, GUIDE_TEST)  # 형식 검사
    rows = [r for r in _read(tables_dir, GUIDE_TEST) if r["reviewed"] == "yes"]
    return sorted(rows, key=lambda r: combo_id(r["body_part"], r["symptom"], r["injury"]))


def _rows_sha256(rows: list[dict[str, str]]) -> str:
    text = "".join(",".join(row[c] for c in GUIDE_COLUMNS) + "\n" for row in rows)
    return hashlib.sha256(text.encode()).hexdigest()


def check_guide_test_disjoint(tables_dir: Path) -> list[str]:
    """최종 평가용 조합 중 조정용 조합과 same_combo인 것. 비어 있어야 한다."""
    valid = list(read_guide(tables_dir))
    return sorted(cid for cid in read_guide(tables_dir, GUIDE_TEST) if any(same_combo(cid, v) for v in valid))


def freeze_guide_test(tables_dir: Path, splits_dir: Path, force: bool = False) -> dict:
    """검토한 최종 평가용 행을 id 목록과 해시로 고정한다. 이미 고정했으면 force 없이는 멈춘다(test 목록은 바꾸지 않는다)."""
    ids_path, hash_path = splits_dir / TEST_IDS, splits_dir / TEST_IDS_HASH
    if ids_path.exists() and not force:
        raise TableError(f"{TEST_IDS}가 이미 있다. 바꾸려면 사용자에게 묻고 이유를 backlog에 남긴 뒤 force로 다시 쓴다")
    if overlap := check_guide_test_disjoint(tables_dir):
        raise TableError(f"{GUIDE_TEST}에 조정용 조합과 같은 조합이 있다 {overlap}")
    rows = _guide_test_rows(tables_dir)
    ids = [combo_id(r["body_part"], r["symptom"], r["injury"]) for r in rows]
    ids_path.write_text("".join(f"{cid}\n" for cid in ids))
    hash_path.write_text(f"{_rows_sha256(rows)}  {GUIDE_TEST} reviewed=yes\n")
    return {
        "combos": len(ids),
        "by_department": dict(Counter(r["department"] for r in rows)),
        "injury_yes": sum(r["injury"] == "yes" for r in rows),
    }


def held_test_ids(splits_dir: Path) -> list[str]:
    """최종 평가용 조합 id(정답 없음). 학습이 같은 조합을 빼는 데만 쓴다. 아직 고정하지 않았으면 빈 목록."""
    path = splits_dir / TEST_IDS
    return path.read_text().split() if path.exists() else []


def load_guide_test(tables_dir: Path, splits_dir: Path) -> tuple[list[str], dict[str, GuideAnswer]]:
    """평가 명령만 부른다. 고정한 행과 해시가 다르면 멈춘다."""
    rows = _guide_test_rows(tables_dir)
    expected = (splits_dir / TEST_IDS_HASH).read_text().split()[0]
    ids = held_test_ids(splits_dir)
    if _rows_sha256(rows) != expected or ids != [combo_id(r["body_part"], r["symptom"], r["injury"]) for r in rows]:
        raise TableError(f"{GUIDE_TEST}의 검토 행이 고정한 {TEST_IDS}·{TEST_IDS_HASH}와 다르다")
    answers = read_guide(tables_dir, GUIDE_TEST)
    return ids, {cid: answers[cid] for cid in ids}


def same_combo(a: str, b: str) -> bool:
    """부위·증상이 같고 손상 여부가 같거나 한쪽이 any. 검증셋 조합을 학습 표에서 뺄 때 쓴다."""
    *ab, ai = a.split("-")
    *bb, bi = b.split("-")
    return ab == bb and (ai == bi or "any" in (ai, bi))


# ---------------------------------------------------------------------------
# 표 만들기(scripts/build_tables.py)
# ---------------------------------------------------------------------------
def build_tables(raw_dir: Path, tables_dir: Path, splits_dir: Path) -> dict:
    """입력 표 + HIRA 원본 → 만드는 표 두 개와 검증셋 id 목록을 쓰고, 다시 읽어 검증한 뒤 요약을 돌려준다."""
    from fornav_modeling.data import ddxplus, hira, kaggle_symptom

    counts = hira.read_counts(raw_dir)
    disease_kcd = read_disease_kcd(tables_dir)
    if missing := sorted(set(kaggle_symptom.diseases(raw_dir)) - set(disease_kcd)):
        raise TableError(f"{DISEASE_KCD}에 없는 Kaggle 질환 {missing}")
    label_kcd = disease_kcd | ddxplus_label_kcd(ddxplus.read_condition_kcd(tables_dir), disease_kcd)
    symptom_map = read_symptom_map(tables_dir)
    if set(symptom_map) != set(kaggle_symptom.symptoms(raw_dir)):
        raise TableError(f"{SYMPTOM_MAP}의 증상이 Kaggle 원본의 증상과 다르다")
    button_kcd = read_button_kcd(tables_dir)
    write_table(tables_dir / DISEASE_DEPARTMENT, DISEASE_COLUMNS, build_disease_department(label_kcd, counts))
    write_table(tables_dir / BUTTON_DEPARTMENT, BUTTON_COLUMNS, build_button_department(button_kcd, counts))

    diseases = read_disease_department(tables_dir)
    buttons = read_button_department(tables_dir)
    guide = read_guide(tables_dir)
    (splits_dir / VALID_IDS).write_text("".join(f"{cid}\n" for cid in sorted(guide)))
    pairs = {tuple(cid.split("-")[:2]) for cid in buttons}
    return {
        "diseases": len(diseases),
        "symptoms_mapped": sum(bool(symptoms) for _, symptoms in symptom_map.values()),
        "symptoms_total": len(symptom_map),
        "button_combos": len(buttons),
        "button_pairs_filled": len(pairs),
        "button_pairs_total": len(BODY_PARTS) * len(SYMPTOMS),
        "button_by_source": dict(Counter("manual" if r["manual"] else "kcd" for r in button_kcd)),
        "clear_case_conflicts": clear_case_conflicts(buttons),
        "valid_combos": len(guide),
    }
