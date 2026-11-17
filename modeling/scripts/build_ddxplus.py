# DDXPlus 합성 환자를 버튼 벡터 표로 옮기고 Kaggle과의 겹침을 리포트로 쓴다(backlog 17).
#   uv run python scripts/build_ddxplus.py   data/processed/ddxplus/ddxplus.csv, reports/ddxplus_v0.{json,md}를 쓴다
# 원본은 scripts/download_data.py --source ddxplus로 받는다. 분할·학습은 하지 않는다(backlog 16).

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # uv run 없이 실행해도 src를 찾는다

from fornav_modeling.data import ddxplus  # noqa: E402

data = ROOT / "data"
report = ddxplus.build(data / "raw", data / "tables", data / "processed", ROOT / "reports")
print(json.dumps(report["conversion"] | report["vectors"], ensure_ascii=False, indent=2))
