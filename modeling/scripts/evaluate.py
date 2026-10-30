# test 평가 명령. data/test를 읽는 유일한 명령이다. 라운드마다 한 번만 실행하고 결과를 '최종'으로 기록한다.
#   uv run python scripts/evaluate.py --model acuity --round v0   reports/acuity_v0_test.{json,md}
#   uv run python scripts/evaluate.py --model dept_a --round v0   reports/dept_a_v0_test.{json,md}
#   uv run python scripts/evaluate.py --model dept_b --round v0   reports/dept_b_v0_test.{json,md} (Kaggle 질환·증상 test, 모델 A와 같은 행)
#   uv run python scripts/evaluate.py --model ensemble --round v1   reports/ensemble_v1_test.{json,md}
#   uv run python scripts/evaluate.py --model pipeline --round v2   reports/pipeline_v2_test.{json,md} (백엔드 규칙 + 서빙 묶음, backlog 12)

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # uv run 없이 실행해도 src를 찾는다

from fornav_modeling import pipeline  # noqa: E402
from fornav_modeling.data import split  # noqa: E402
from fornav_modeling.models import acuity, dept_a, dept_b, ensemble  # noqa: E402
from fornav_modeling.predict import VERSION  # noqa: E402

parser = argparse.ArgumentParser(description="저장한 모델을 test로 한 번 평가한다")
parser.add_argument("--model", required=True, choices=["acuity", "dept_a", "dept_b", "ensemble", "pipeline"])
parser.add_argument("--round", required=True, help="평가할 라운드(models/<model>/<round>)")
args = parser.parse_args()

data = ROOT / "data"
model_dir = ROOT / "models" / args.model / args.round
if args.model == "ensemble":
    test = split.load_symptom_test(data / "test", data / "splits")  # 해시가 다르면 멈춘다
    ensemble.evaluate_test_round(test, ROOT / "models", data / "tables", ROOT / "reports", args.round)
elif args.model in ("dept_a", "dept_b"):
    test = split.load_symptom_test(data / "test", data / "splits")  # 해시가 다르면 멈춘다
    {"dept_a": dept_a, "dept_b": dept_b}[args.model].evaluate_test_round(test, model_dir, data / "tables", ROOT / "reports", args.round)
elif args.model == "pipeline":
    if args.round != VERSION:
        parser.error(f"pipeline은 서빙 묶음({VERSION})만 평가한다")
    test = split.load_test(data / "test", data / "splits")  # 해시가 다르면 멈춘다
    pipeline.evaluate_test_round(test, pipeline.backend_rules(ROOT.parent / "backend"), ROOT / "reports")
else:
    test = split.load_test(data / "test", data / "splits")
    acuity.evaluate_test_round(test, model_dir, ROOT / "reports", args.round)
print((ROOT / "reports" / f"{args.model}_{args.round}_test.md").read_text())
