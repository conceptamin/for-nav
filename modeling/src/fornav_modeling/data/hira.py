# HIRA 2025 질병별 진료과 통계 → KCD 3단 코드별 진료과 환자 수. 원본 설명은 data/README.md에 있다.
# - 병원급 이상(진료과목 48종)과 의원급(표시과목 26종) 두 파일의 환자수를 그대로 더한다. 의원급 가중은 두지 않는다:
#   우리 안내는 외래 의원을 찾는 것이라 의원급 비중이 큰 쪽이 맞고, 환자수 합이 곧 그 비중이다(backlog 05 결정).
# - 가중치는 환자수다. 명세서청구건수·입내원일수는 만성질환 재방문이 부풀려 "처음 어느 과에 가는가"와 멀어진다.
# - HIRA 진료과목 → Department 10종 대응은 HIRA_DEPARTMENTS 한 곳에서 정한다. None은 버리는 과다.

import csv
from collections import Counter
from pathlib import Path

from fornav_modeling.schema import Department

RAW_FILES = {
    # 파일(data/raw/ 아래) → 진료과 열 이름
    Path("hira") / "hospital_department_disease_2025.csv": "진료과목",
    Path("hira") / "clinic_specialty_disease_2025.csv": "표시과목",
}
SOURCE = "hira:2025"

_DENTAL = [
    "치과",
    "치과보존과",
    "구강악안면외과",
    "치주과",
    "치과보철과",
    "구강내과",
    "소아치과",
    "통합치의학과",
    "치과교정과",
    "영상치의학과",
    "예방치과",
    "구강병리과",
]
_ORIENTAL = ["침구과", "한방내과", "한방", "한방재활의학과", "한방안·이비인후·피부과", "사상체질과", "한방부인과", "한방소아과"]

# 두 파일에 나오는 진료과 이름 전부. 새 이름이 나오면 hira_department가 멈춘다.
HIRA_DEPARTMENTS: dict[str, Department | None] = {
    "내과": "internal",
    "결핵과": "internal",
    "정형외과": "ortho",
    # 척추·통증·재활 진료가 대부분이라 근골격 쪽으로 흡수한다. 신경외과의 뇌 질환 코드는 hira_department가 neuro로 돌린다
    "신경외과": "ortho",
    "재활의학과": "ortho",
    "마취통증의학과": "ortho",
    "외과": "surgery",
    # 열상 봉합·화상, 하지정맥류처럼 외과와 겹치는 처치가 많다
    "성형외과": "surgery",
    "심장혈관흉부외과": "surgery",
    "신경과": "neuro",
    "안과": "ophth",
    "이비인후과": "ent",
    "피부과": "derm",
    **dict.fromkeys(_DENTAL, "dental"),
    "가정의학과": "family",
    # 전문과목을 표시하지 않은 의원과 보건소 의사. 1차 진료라 가정의학과로 본다
    "일반의": "family",
    "보건기관의과": "family",
    "직업환경의학과": "occ",
    # 우리 진료과에 없거나(근로자 대상이 아닌 과 포함) 진료과가 아닌 지원 부서는 버린다
    "소아청소년과": None,
    "산부인과": None,
    "비뇨의학과": None,
    "정신건강의학과": None,
    "응급의학과": None,
    "방사선종양학과": None,
    "영상의학과": None,
    "진단방사선과,영상의학과": None,
    "핵의학과": None,
    "진단검사의학과": None,
    "병리과": None,
    "예방의학과": None,
    **dict.fromkeys(_ORIENTAL, None),
}


# 신경외과 환자 중 뇌·중추신경 질환(뇌혈관 I60–I69, 두개내 손상 S06, 중추신경계 G00–G47)은 신경과 쪽이 맞다.
# 일괄 ortho로 두면 뇌출혈(I61)이 정형외과 77%가 된다.
def _brain(kcd: str) -> bool:
    return "I60" <= kcd <= "I69" or kcd == "S06" or "G00" <= kcd <= "G47"


def hira_department(name: str, kcd: str) -> Department | None:
    if name not in HIRA_DEPARTMENTS:
        raise ValueError(f"HIRA_DEPARTMENTS에 없는 진료과 이름: {name!r}")
    if name == "신경외과" and _brain(kcd):
        return "neuro"
    return HIRA_DEPARTMENTS[name]


def read_counts(raw_dir: Path) -> dict[str, Counter[Department]]:
    """KCD 3단 코드 → Department별 환자 수(두 파일 합). 버리는 과의 환자는 세지 않는다."""
    counts: dict[str, Counter[Department]] = {}
    for file, department_column in RAW_FILES.items():
        with (raw_dir / file).open(encoding="cp949", newline="") as f:
            for row in csv.DictReader(f):
                department = hira_department(row[department_column], row["주상병코드"])
                if department is None:
                    continue
                counts.setdefault(row["주상병코드"], Counter())[department] += int(row["환자수"])
    return counts


def department_ratio(counts: dict[str, Counter[Department]], kcds: list[str]) -> dict[Department, float]:
    """여러 코드의 환자 수를 더해 비율로. 코드가 하나도 통계에 없으면 KeyError."""
    total: Counter[Department] = Counter()
    if missing := [k for k in kcds if k not in counts]:
        raise KeyError(f"HIRA 통계에 없는 KCD 코드: {missing}")
    for kcd in kcds:
        total += counts[kcd]
    n = sum(total.values())
    return {department: count / n for department, count in total.most_common()}
