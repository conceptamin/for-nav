# 규칙 + 응급도 모델을 합친 응급 판정 평가(backlog 12). 서빙 경로가 아니다.
# 백엔드 /api/triage와 같은 순서다: 레드플래그·버튼 조합 규칙(backend app.rules.triage) → 응급도 모델(predict). 둘 중 하나라도 응급이면 응급.
# - 규칙은 backend 코드를 그대로 부르고 여기에 다시 적지 않는다. backend는 pydantic이 필요해 이 환경에서 import하지 않고,
#   backend 폴더의 uv 환경에서 subprocess로 부른다. 입력·출력은 표준 입출력 JSON으로만 주고받는다(파일로 쓰지 않는다).
# - 자유 입력은 없다(Kaggle 원본은 의료진이 쓴 주증상이라 사용자 문장이 아니다). 규칙은 버튼 조합 분기만 지난다.
# - 이 모듈은 데이터를 읽지 않는다. test 행은 평가 명령(scripts/evaluate.py)이 읽어서 넘긴다.

import json
import math
import os
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fornav_modeling.evaluate import ratio
from fornav_modeling.predict import VERSION, predict

# 입력 모양(models/acuity.py의 PROFILES와 같은 이름). backend: 부위·증상만 보낸다 — 나머지는 predict가 "모름"으로 처리한다
PROFILES = ("full", "backend")
ACUITY_INPUTS = ("pain_score", "mental", "age_group", "sex", "injury")
_BASE = {"language": "ko", "created_at": "2026-10-30T00:00:00Z"}  # 규칙·모델이 쓰지 않는 필수 필드

# backend 환경에서 돈다. Intake마다 규칙 판정(by_rule)과 모델이 없을 때의 보조 점수 판정(by_model)을 돌려준다
_BACKEND_CODE = """
import json, sys
from app.rules.triage import triage
from app.schemas import Intake
out = []
for d in json.load(sys.stdin):
    r = triage(Intake.model_validate(d))
    out.append({"by_rule": r.by_rule, "by_score": r.by_model})
print(json.dumps(out))
"""

Rules = Callable[[list[dict]], list[dict]]


def to_intake(row: Mapping[str, Any], profile: str) -> dict:
    """표준 테이블 한 행 → predict 입력 dict(백엔드 Intake 필드 이름). 값이 없으면 키를 넣지 않는다(백엔드 Intake와 같다)."""
    intake = {"id": row["id"], **_BASE, "body_parts": list(row["body_parts"]), "symptoms": list(row["symptoms"])}
    if profile == "full":
        for key in ACUITY_INPUTS:
            value = row.get(key)
            if value is None or (isinstance(value, float) and math.isnan(value)):
                continue
            intake[key] = int(value) if key == "pain_score" else bool(value) if key == "injury" else value
    elif profile != "backend":
        raise ValueError(f"모르는 입력 모양: {profile!r}")
    return intake


def backend_rules(backend_dir: Path) -> Rules:
    """backend 폴더의 uv 환경에서 app.rules.triage.triage를 부르는 함수. 부위·증상만 넘긴다(규칙은 응급도 입력 필드를 쓰지 않는다)."""
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}  # 이 환경이 아니라 backend 환경을 쓰게 한다

    def run(intakes: list[dict]) -> list[dict]:
        payload = [
            {
                "id": i["id"],
                "language": i["language"],
                "createdAt": i["created_at"],
                "bodyParts": i["body_parts"],
                "symptoms": i["symptoms"],
            }
            for i in intakes
        ]
        result = subprocess.run(
            ["uv", "run", "--quiet", "--directory", str(backend_dir), "python", "-c", _BACKEND_CODE],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        return json.loads(result.stdout)

    return run


def emergency_metrics(is_emergency: np.ndarray, flagged: np.ndarray) -> dict:
    """응급 재현율, 응급으로 본 건수, 응급 판정의 정밀도. 칸은 분자·분모."""
    return {
        "recall": ratio((flagged & is_emergency).sum(), is_emergency.sum()),
        "flagged": ratio(flagged.sum(), len(flagged)),
        "precision": ratio((flagged & is_emergency).sum(), flagged.sum()),
    }


def evaluate_test_round(test: pd.DataFrame, rules: Rules, reports_dir: Path, models_dir: Path | None = None) -> dict:
    """서빙 묶음(predict.VERSION)과 백엔드 규칙으로 test를 평가해 '최종'으로 기록한다. 한 번만 — 이미 있으면 멈춘다."""
    name = f"pipeline_{VERSION}_test"
    if (reports_dir / f"{name}.json").exists():
        raise FileExistsError(f"{name}.json이 이미 있다. test 평가는 한 번만 한다")
    rows = test.to_dict("records")
    is_emergency = test["acuity"].to_numpy() == "emergency"
    flags = rules([to_intake(r, "backend") for r in rows])
    by_rule = np.array([f["by_rule"] for f in flags])
    by_score = np.array([f["by_score"] for f in flags])

    results = {
        "규칙만": emergency_metrics(is_emergency, by_rule),
        "규칙 + 보조 점수(모델 없음, 프론트 오프라인과 같음)": emergency_metrics(is_emergency, by_rule | by_score),
    }
    for profile in PROFILES:
        by_model = np.array([predict(to_intake(r, profile), models_dir)["acuity"] == "emergency" for r in rows])
        results[f"모델만, {profile}"] = emergency_metrics(is_emergency, by_model)
        results[f"규칙 + 모델, {profile} (서빙)"] = emergency_metrics(is_emergency, by_rule | by_model)

    report = {
        "version": VERSION,
        "final": True,
        "note": "test 평가는 한 번만 했다. 규칙은 backend app.rules.triage, 모델은 predict. 자유 입력 없음(버튼 조합 규칙만)",
        "rows": len(test),
        "emergency": int(is_emergency.sum()),
        "results": results,
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / f"{name}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (reports_dir / f"{name}.md").write_text(f"# {name}\n\n" + _table(results))
    return report


def _table(results: Mapping[str, dict]) -> str:
    lines = ["| 판정 | 응급 재현율 | 응급으로 본 건수 | 응급 판정 정밀도 |", "|---|---|---|---|"]
    for label, m in results.items():
        lines.append(f"| {label} | {_cell(m['recall'])} | {_cell(m['flagged'])} | {_cell(m['precision'])} |")
    return "\n".join(lines) + "\n"


def _cell(r: dict) -> str:
    return f"{r['n']}/{r['of']} ({'-' if r['value'] is None else f'{r["value"]:.1%}'})"
