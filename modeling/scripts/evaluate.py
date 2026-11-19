# test 평가 명령. data/test를 읽는 유일한 명령이다. 라운드마다 한 번만 실행하고 결과를 '최종'으로 기록한다.
#   uv run python scripts/evaluate.py --model dept_a --round v0   reports/dept_a_v0_test.{json,md}
#   uv run python scripts/evaluate.py --model dept_b --round v0   reports/dept_b_v0_test.{json,md} (Kaggle 질환·증상 test, 모델 A와 같은 행)
#   uv run python scripts/evaluate.py --model ensemble --round v4   reports/ensemble_v4_test.{json,md}
#     앙상블은 18의 최종 평가용 안내 조합(dept_test.txt, 고정 해시 확인)도 함께 평가한다

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # uv run 없이 실행해도 src를 찾는다

from fornav_modeling.data import split  # noqa: E402
from fornav_modeling.labels import department  # noqa: E402
from fornav_modeling.models import dept_a, dept_b, ensemble  # noqa: E402

parser = argparse.ArgumentParser(description="저장한 모델을 test로 한 번 평가한다")
parser.add_argument("--model", required=True, choices=["dept_a", "dept_b", "ensemble"])
parser.add_argument("--round", required=True, help="평가할 라운드(models/<model>/<round>)")
args = parser.parse_args()

data = ROOT / "data"
model_dir = ROOT / "models" / args.model / args.round
test = split.load_symptom_test(data / "test", data / "splits")  # 해시가 다르면 멈춘다
if args.model == "ensemble":
    final_guide = department.load_guide_test(data / "tables", data / "splits")  # 고정한 행과 다르면 멈춘다
    ensemble.evaluate_test_round(test, ROOT / "models", data / "tables", ROOT / "reports", args.round, final_guide)
else:
    {"dept_a": dept_a, "dept_b": dept_b}[args.model].evaluate_test_round(test, model_dir, data / "tables", ROOT / "reports", args.round)
print((ROOT / "reports" / f"{args.model}_{args.round}_test.md").read_text())
