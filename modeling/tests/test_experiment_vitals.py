# 발표용 활력징후 실험(backlog 09). 서빙 경로가 활력징후·실험 코드를 import하지 않는지, 피처 행렬이 버튼 피처 뒤에 활력징후를 붙이는지,
# 같은 seed 두 번 → 같은 모델인지.

import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from fornav_modeling import experiment_vitals as E
from fornav_modeling.features.buttons import FEATURE_NAMES, featurize_many
from fornav_modeling.features.vitals import VITAL_FEATURES, vitals_features

MODELING = Path(__file__).resolve().parents[1]
ROW = {"body_parts": ["chest"], "symptoms": ["pain"], "pain_score": 7.0, "mental": "alert", "age_group": "65plus", "sex": "male"}


def test_predict_does_not_import_vitals():
    code = "import sys; import fornav_modeling.predict; print('\\n'.join(sys.modules))"
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True, cwd=MODELING, env={"PYTHONPATH": str(MODELING / "src")}
    )
    loaded = set(result.stdout.split())
    assert "fornav_modeling.features.vitals" not in loaded and "fornav_modeling.experiment_vitals" not in loaded
    assert "vitals" not in (MODELING / "src" / "fornav_modeling" / "predict.py").read_text()


def test_vitals_features_keep_missing_as_nan():
    values = vitals_features({"sbp": 120.0, "dbp": None, "hr": 88, "rr": 18.0, "bt": 36.5, "saturation": math.nan})
    assert values[:1] == [120.0] and math.isnan(values[1]) and values[2:5] == [88.0, 18.0, 36.5] and math.isnan(values[5])


def test_feature_matrix_appends_vitals_after_buttons():
    rows = pd.DataFrame(
        [ROW | {"sbp": 90.0, "dbp": 60.0, "hr": 120.0, "rr": 24.0, "bt": 38.2, "saturation": None}, ROW | dict.fromkeys(VITAL_FEATURES)]
    )
    buttons = E.feature_matrix(rows, "buttons")
    both = E.feature_matrix(rows, "buttons_vitals")
    assert buttons.shape == (2, len(FEATURE_NAMES)) and both.shape == (2, len(E.SETUPS["buttons_vitals"]))
    np.testing.assert_array_equal(buttons, featurize_many(rows.to_dict("records")))
    np.testing.assert_array_equal(both[:, : len(FEATURE_NAMES)], buttons)
    np.testing.assert_array_equal(both[0, len(FEATURE_NAMES) :], [90.0, 60.0, 120.0, 24.0, 38.2, np.nan])
    assert np.isnan(both[1, len(FEATURE_NAMES) :]).all()


def test_same_seed_same_model():
    rng = np.random.default_rng(0)
    names = E.SETUPS["buttons_vitals"]
    X = rng.integers(0, 2, size=(300, len(names))).astype(np.float64)
    X[:, -len(VITAL_FEATURES) :] = rng.normal(100, 20, size=(300, len(VITAL_FEATURES)))
    X[rng.random(300) < 0.3, -1] = np.nan
    y = np.where(X[:, -4] > 110, 0, np.where(X[:, 0] > 0, 1, 2))
    first, second = (E.train_lightgbm(X, y, names).model_to_string() for _ in range(2))
    assert first == second
    shap = E.shap_values(E.train_lightgbm(X, y, names), X[:5])
    assert shap.shape == (5, 3, len(names))
