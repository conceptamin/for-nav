# 모델 B 설정 후보를 조정 셋(안내 조합 + 질환·증상 valid)에서 앙상블로 비교해 고른다(backlog 19). test는 읽지 않는다.
#   uv run python scripts/compare_dept_b.py v0 v0_guide ...   reports/dept_b_compare.{json,md}

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # uv run 없이 실행해도 src를 찾는다

from fornav_modeling.models import ensemble  # noqa: E402

start = time.perf_counter()
data = ROOT / "data"
names = sys.argv[1:] or ["v0", "v0_guide"]
report = ensemble.compare_b_settings(data / "processed", data / "splits", data / "tables", ROOT / "models", ROOT / "reports", names)
print((ROOT / "reports" / "dept_b_compare.md").read_text())
print(f"선택: {report['chosen']}, {time.perf_counter() - start:.0f}초")
