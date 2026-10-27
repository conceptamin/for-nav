# KTAS 1~5 → 응급도 3단계. 라벨은 전문가가 정한 KTAS(원본 KTAS_expert)이고,
# 간호사가 정한 KTAS(KTAS_RN)는 같은 함수로 바꿔 비교용으로만 둔다.

from typing import Literal, get_args

Acuity = Literal["emergency", "today", "outpatient"]
ACUITIES: tuple[Acuity, ...] = get_args(Acuity)  # 모델의 라벨 순서

_KTAS_TO_ACUITY: dict[int, Acuity] = {1: "emergency", 2: "emergency", 3: "today", 4: "outpatient", 5: "outpatient"}


def ktas_to_acuity(ktas: int) -> Acuity:
    """KTAS 1–2 → emergency, 3 → today, 4–5 → outpatient. 그 밖의 값은 ValueError."""
    if isinstance(ktas, bool) or ktas not in _KTAS_TO_ACUITY:
        raise ValueError(f"KTAS는 1~5여야 한다: {ktas!r}")
    return _KTAS_TO_ACUITY[int(ktas)]
