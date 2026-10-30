# 규칙 + 모델 합친 평가(backlog 12). test 데이터는 쓰지 않고 합성 행으로 본다.

import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fornav_modeling import pipeline
from fornav_modeling.predict import VERSION

MODELING = Path(__file__).resolve().parents[1]
ROWS = pd.DataFrame(
    [
        {
            "id": "t1",
            "body_parts": ["chest"],
            "symptoms": ["pain"],
            "pain_score": 7.0,
            "mental": "alert",
            "age_group": "65plus",
            "sex": "male",
            "injury": False,
            "acuity": "emergency",
        },
        {
            "id": "t2",
            "body_parts": ["hand"],
            "symptoms": ["cut", "bleeding"],
            "pain_score": float("nan"),
            "mental": "alert",
            "age_group": "under30",
            "sex": "female",
            "injury": True,
            "acuity": "outpatient",
        },
        {
            "id": "t3",
            "body_parts": ["abdomen"],
            "symptoms": ["pain", "nausea"],
            "pain_score": 3.0,
            "mental": "verbal",
            "age_group": "45to64",
            "sex": "female",
            "injury": False,
            "acuity": "emergency",
        },
    ]
)


def test_to_intake_full_keeps_known_inputs_and_drops_missing():
    full = pipeline.to_intake(ROWS.iloc[1].to_dict(), "full")
    assert full["injury"] is True and full["age_group"] == "under30" and "pain_score" not in full
    assert pipeline.to_intake(ROWS.iloc[0].to_dict(), "full")["pain_score"] == 7


def test_to_intake_backend_sends_only_body_parts_and_symptoms():
    intake = pipeline.to_intake(ROWS.iloc[0].to_dict(), "backend")
    assert not set(pipeline.ACUITY_INPUTS) & set(intake)
    assert intake["body_parts"] == ["chest"] and intake["symptoms"] == ["pain"]


def test_emergency_metrics_counts():
    m = pipeline.emergency_metrics(np.array([True, True, False, False]), np.array([True, False, True, False]))
    assert m["recall"] == {"n": 1, "of": 2, "value": 0.5}
    assert m["flagged"]["n"] == 2 and m["precision"]["n"] == 1 and m["precision"]["of"] == 2


def test_rules_or_model_and_single_run(tmp_path):
    def fake_rules(intakes):
        return [{"by_rule": i["id"] == "t1", "by_score": False} for i in intakes]

    report = pipeline.evaluate_test_round(ROWS, fake_rules, tmp_path)
    results = report["results"]
    assert report["version"] == VERSION and report["emergency"] == 2
    assert results["규칙만"]["recall"]["n"] == 1
    for profile in pipeline.PROFILES:
        combined, model = results[f"규칙 + 모델, {profile} (서빙)"], results[f"모델만, {profile}"]
        assert combined["recall"]["n"] >= max(model["recall"]["n"], results["규칙만"]["recall"]["n"])
        assert combined["flagged"]["n"] >= model["flagged"]["n"]
    assert (tmp_path / f"pipeline_{VERSION}_test.md").exists()
    with pytest.raises(FileExistsError):
        pipeline.evaluate_test_round(ROWS, fake_rules, tmp_path)


@pytest.mark.skipif(shutil.which("uv") is None, reason="backend 환경을 부르려면 uv가 필요하다")
def test_backend_rules_runs_backend_triage():
    rules = pipeline.backend_rules(MODELING.parent / "backend")
    flags = rules([pipeline.to_intake(r, "backend") for r in ROWS.to_dict("records")])
    # 가슴 + 통증은 버튼 조합 규칙으로 응급, 손 베임·출혈은 규칙 아님·보조 점수 2(임계값 3 미만)
    assert flags[0] == {"by_rule": True, "by_score": False}
    assert flags[1] == {"by_rule": False, "by_score": False}
