# 진료과 모델 B 학습 설정 후보와 비교 기준선을 학습 표 반복 교차검증으로 재고 설정을 고른다(backlog 13). 안내 조합·test는 쓰지 않는다.
#   uv run python scripts/cv_dept_b.py     reports/dept_b_cv.{json,md}

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # uv run 없이 실행해도 src를 찾는다

from fornav_modeling.models import dept_b  # noqa: E402

start = time.perf_counter()
data = ROOT / "data"
report = dept_b.cv_round(data / "tables", data / "splits", ROOT / "reports")
print((ROOT / "reports" / "dept_b_cv.md").read_text())
print(f"선택: {report['chosen']}, {time.perf_counter() - start:.0f}초")
