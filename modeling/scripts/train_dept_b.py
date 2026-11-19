# 진료과 모델 B(버튼 조합 → 진료과 분포, MLP)를 표로 학습하고 진료과 검증셋·질환·증상 valid로 평가한다(backlog 07, 13). test는 읽지 않는다.
#   uv run python scripts/train_dept_b.py                                  models/dept_b/v0/, reports/dept_b_v0.{json,md}
#   uv run python scripts/train_dept_b.py --round v4 --setting <후보 이름>  설정은 scripts/cv_dept_b.py가 고른 것(dept_b.CANDIDATES)

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # uv run 없이 실행해도 src를 찾는다

from fornav_modeling.models import dept_b  # noqa: E402

parser = argparse.ArgumentParser(description="진료과 모델 B 학습과 검증셋 평가")
parser.add_argument("--round", default="v0", help="라운드 이름(모델 폴더·리포트 이름)")
parser.add_argument("--setting", default="v0", choices=sorted(dept_b.CANDIDATES), help="학습 설정")
args = parser.parse_args()

start = time.perf_counter()
data = ROOT / "data"
dept_b.train_round(data / "tables", data / "splits", data / "processed", ROOT / "models", ROOT / "reports", args.round, args.setting)
print((ROOT / "reports" / f"dept_b_{args.round}.md").read_text())
print(f"{time.perf_counter() - start:.1f}초")
