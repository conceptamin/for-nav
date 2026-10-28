# SHAP 판단 근거(backlog 04). LightGBM 모델의 TreeSHAP 값을 LightGBM 내장 계산(pred_contrib)으로 구한다.
# shap 라이브러리의 TreeExplainer와 같은 값이다(tests/test_acuity.py에서 확인). 서빙에서 shap 패키지 없이 쓸 수 있게 이쪽을 쓴다.
# 기여도 단위는 클래스별 원점수(log-odds, softmax 전)다. 양수면 그 클래스 쪽으로 민다.

import math

import lightgbm as lgb
import numpy as np

from fornav_modeling.features.buttons import FEATURE_NAMES


def shap_values(booster: lgb.Booster, X: np.ndarray) -> np.ndarray:
    """(행 수, 클래스 수, 피처 수) SHAP 값. 기준값(bias) 열은 뺀다."""
    raw = booster.predict(X, pred_contrib=True)
    per_class = raw.reshape(len(X), booster.num_model_per_iteration(), len(FEATURE_NAMES) + 1)
    return per_class[:, :, :-1]


def top_contributions(booster: lgb.Booster, x: np.ndarray, class_index: int, n: int = 3) -> list[dict]:
    """한 행에서 class_index 클래스에 대한 기여가 큰 피처 n개를 |기여도| 큰 순으로 {feature, value, contribution}.
    기여도가 0인 피처는 넣지 않는다. 같은 |기여도|면 FEATURE_NAMES 순서."""
    contributions = shap_values(booster, x.reshape(1, -1))[0, class_index]
    order = sorted((i for i in range(len(FEATURE_NAMES)) if contributions[i] != 0), key=lambda i: (-abs(contributions[i]), i))
    return [
        {
            "feature": FEATURE_NAMES[i],
            "value": None if math.isnan(x[i]) else float(x[i]),
            "contribution": round(float(contributions[i]), 4),
        }
        for i in order[:n]
    ]
