# 최종 평가용 안내 조합을 고정한다(backlog 18). 사람이 검토(reviewed=yes)를 마친 뒤 한 번만 돌린다.
#   uv run python scripts/freeze_guide_test.py   data/splits/dept_test.txt·dept_test.sha256을 쓴다
# 이미 고정했으면 멈춘다. 고정 전에 새 조합에 대한 모델 출력을 보지 않는다.

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # uv run 없이 실행해도 src를 찾는다

from fornav_modeling.labels import department  # noqa: E402

data = ROOT / "data"
print(json.dumps(department.freeze_guide_test(data / "tables", data / "splits"), ensure_ascii=False, indent=2))
