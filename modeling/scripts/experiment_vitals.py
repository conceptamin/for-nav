# 발표용 비교 실험(backlog 09): 버튼 피처만 쓴 응급도 모델 vs 버튼 + 활력징후 모델을 valid로 비교한다. test는 읽지 않는다.
#   uv run python scripts/experiment_vitals.py   reports/experiment_vitals.{json,md}, reports/figures/experiment_vitals_*.png

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # uv run 없이 실행해도 src를 찾는다

from fornav_modeling import experiment_vitals  # noqa: E402

start = time.perf_counter()
data = ROOT / "data"
experiment_vitals.run(data / "processed", data / "splits", ROOT / "reports")
print((ROOT / "reports" / f"{experiment_vitals.REPORT_NAME}.md").read_text())
print(f"{time.perf_counter() - start:.1f}초")
