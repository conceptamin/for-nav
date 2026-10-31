# 질환·증상 원본(진료과 모델 A)을 표준 테이블로 바꾸고 train/valid/test를 id 목록으로 고정한다(backlog 06).
#   uv run python scripts/make_splits.py           data/processed, data/test, data/splits, reports를 만든다
#   uv run python scripts/make_splits.py --force   커밋된 id 목록·test 해시와 달라도 덮어쓴다(사용자와 정한 뒤에만)

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # uv run 없이 실행해도 src를 찾는다

from fornav_modeling.data import split  # noqa: E402

parser = argparse.ArgumentParser(description="질환·증상 데이터 표준화와 train/valid/test 분할")
parser.add_argument("--force", action="store_true", help="커밋된 분할과 달라도 덮어쓴다")
args = parser.parse_args()

data = ROOT / "data"
dirs = (data / "raw", data / "tables", data / "processed", data / "splits", data / "test", ROOT / "reports")
print(json.dumps(split.make_symptom_splits(*dirs, force=args.force), ensure_ascii=False, indent=2))
