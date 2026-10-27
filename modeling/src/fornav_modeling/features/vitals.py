# 활력징후 피처. 발표용 비교 실험(backlog 09) 전용이다.
# 버튼으로 받을 수 없는 값이라 서빙 모델에는 넣지 않는다. buttons.py와 predict.py는 이 모듈을 import하지 않는다.

import math
from collections.abc import Mapping
from typing import Any

# kaggle_triage 표준 테이블의 열 이름 그대로. 측정 불가(원본 "측불")와 빈칸은 표준화 단계에서 NaN이 된다.
VITAL_FEATURES: tuple[str, ...] = ("sbp", "dbp", "hr", "rr", "bt", "saturation")


def vitals_features(row: Mapping[str, Any]) -> list[float]:
    """표준 테이블 행 → VITAL_FEATURES 순서의 float 목록. 값이 없으면 NaN."""
    return [math.nan if row.get(name) is None else float(row[name]) for name in VITAL_FEATURES]
