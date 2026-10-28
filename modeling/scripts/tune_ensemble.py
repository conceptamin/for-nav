# 진료과 앙상블 가중치와 폴백 기준값을 조정 셋(안내 조합 + Kaggle valid)으로 고른다(backlog 08). test는 읽지 않는다.
#   uv run python scripts/tune_ensemble.py   models/ensemble/v1/ensemble.json, reports/ensemble_v1.{json,md}

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # package = false라 설치되지 않으므로 src를 직접 찾는다

from fornav_modeling.models import ensemble  # noqa: E402

parser = argparse.ArgumentParser(description="진료과 앙상블 가중치·폴백 기준값 조정")
parser.add_argument("--round", default="v1", help="라운드 이름(모델 폴더·리포트 이름)")
args = parser.parse_args()

start = time.perf_counter()
data = ROOT / "data"
ensemble.tune_round(data / "processed", data / "splits", data / "tables", ROOT / "models", ROOT / "reports", args.round)
print((ROOT / "reports" / f"ensemble_{args.round}.md").read_text())
print(f"{time.perf_counter() - start:.1f}초")
