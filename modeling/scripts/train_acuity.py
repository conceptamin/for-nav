# 응급도 모델(LightGBM + 비교용 로지스틱 회귀)을 train으로 학습하고 valid로 임계값을 정한다(backlog 04). test는 읽지 않는다.
#   uv run python scripts/train_acuity.py              models/acuity/v0/, reports/acuity_v0.{json,md}
#   uv run python scripts/train_acuity.py --round v1   새 라운드
#   uv run python scripts/train_acuity.py --round v2 --unknown-inputs   결측을 섞어 학습하고 두 입력 모양으로 임계값(backlog 10)

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # package = false라 설치되지 않으므로 src를 직접 찾는다

from fornav_modeling.models import acuity  # noqa: E402

parser = argparse.ArgumentParser(description="응급도 모델 학습과 검증셋 평가")
parser.add_argument("--round", default="v0", help="라운드 이름(모델 폴더·리포트 이름)")
parser.add_argument("--unknown-inputs", action="store_true", help="성별·나이대·손상 여부·통증 점수가 빈 행을 섞어 학습한다")
args = parser.parse_args()

start = time.perf_counter()
data = ROOT / "data"
acuity.train_round(
    data / "processed", data / "splits", ROOT / "models" / "acuity" / args.round, ROOT / "reports", args.round, args.unknown_inputs
)
print((ROOT / "reports" / f"acuity_{args.round}.md").read_text())
print(f"{time.perf_counter() - start:.1f}초")
