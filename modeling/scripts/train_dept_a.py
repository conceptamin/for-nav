# 진료과 모델 A(증상 → 질환 → 진료과)를 train으로 학습하고 valid·진료과 검증셋으로 평가한다(backlog 06). test는 읽지 않는다.
#   uv run python scripts/train_dept_a.py              models/dept_a/v0/, reports/dept_a_v0.{json,md}
#   uv run python scripts/train_dept_a.py --round v1   새 라운드

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # uv run 없이 실행해도 src를 찾는다

from fornav_modeling.models import dept_a  # noqa: E402

parser = argparse.ArgumentParser(description="진료과 모델 A 학습과 검증셋 평가")
parser.add_argument("--round", default="v0", help="라운드 이름(모델 폴더·리포트 이름)")
args = parser.parse_args()

start = time.perf_counter()
data = ROOT / "data"
dept_a.train_round(
    data / "processed", data / "splits", data / "tables", ROOT / "models" / "dept_a" / args.round, ROOT / "reports", args.round
)
print((ROOT / "reports" / f"dept_a_{args.round}.md").read_text())
print(f"{time.perf_counter() - start:.1f}초")
