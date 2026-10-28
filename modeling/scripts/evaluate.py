# test 평가 명령. data/test를 읽는 유일한 명령이다. 라운드마다 한 번만 실행하고 결과를 '최종'으로 기록한다.
#   uv run python scripts/evaluate.py --model acuity --round v0   reports/acuity_v0_test.{json,md}

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # package = false라 설치되지 않으므로 src를 직접 찾는다

from fornav_modeling.data import split  # noqa: E402
from fornav_modeling.models import acuity  # noqa: E402

parser = argparse.ArgumentParser(description="저장한 모델을 test로 한 번 평가한다")
parser.add_argument("--model", required=True, choices=["acuity"])
parser.add_argument("--round", required=True, help="평가할 라운드(models/<model>/<round>)")
args = parser.parse_args()

test = split.load_test(ROOT / "data" / "test", ROOT / "data" / "splits")  # 해시가 다르면 멈춘다
acuity.evaluate_test_round(test, ROOT / "models" / "acuity" / args.round, ROOT / "reports", args.round)
print((ROOT / "reports" / f"acuity_{args.round}_test.md").read_text())
