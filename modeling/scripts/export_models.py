# 서빙 아티팩트를 models/{acuity,dept_a,dept_b,ensemble}/v1/에 쓴다(backlog 08). 학습·조정·test 평가가 끝난 뒤에 돌린다.
#   uv run python scripts/export_models.py

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # uv run 없이 실행해도 src를 찾는다

from fornav_modeling import export  # noqa: E402

created_at = datetime.now(UTC).isoformat(timespec="seconds")
for name, meta in export.export_all(ROOT / "models", ROOT / "reports", created_at).items():
    print(name, meta["model_version"], json.dumps(meta["files"]))
