# 진료과 라벨 표를 만든다(backlog 05).
#   uv run python scripts/build_tables.py   data/tables의 disease_department.csv·button_department.csv, data/splits/dept_valid.txt를 쓴다

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # uv run 없이 실행해도 src를 찾는다

from fornav_modeling.labels import department  # noqa: E402

data = ROOT / "data"
report = department.build_tables(data / "raw", data / "tables", data / "splits")
print(json.dumps(report, ensure_ascii=False, indent=2))
