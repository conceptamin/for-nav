# 지표 계산. 수치는 항상 분자·분모와 함께 둔다({"n": 분자, "of": 분모, "value": 비율}).
# 이 모듈은 데이터를 읽지 않는다. test 행은 평가 명령(scripts/evaluate.py)이 읽어서 넘긴다.

from collections.abc import Mapping

import numpy as np

from fornav_modeling.labels.ktas import ACUITIES


def ratio(n: int, of: int) -> dict:
    return {"n": int(n), "of": int(of), "value": round(n / of, 4) if of else None}


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray, labels: tuple[str, ...] = ACUITIES) -> dict:
    """클래스별 재현율·정밀도, Top-1 정확도, 혼동행렬(행 = 정답, 열 = 예측, labels 순서)."""
    k = len(labels)
    confusion = np.zeros((k, k), dtype=np.int64)
    np.add.at(confusion, (np.asarray(y_true), np.asarray(y_pred)), 1)
    return {
        "per_class": {
            label: {
                "recall": ratio(confusion[i, i], confusion[i].sum()),
                "precision": ratio(confusion[i, i], confusion[:, i].sum()),
            }
            for i, label in enumerate(labels)
        },
        "accuracy": ratio(np.trace(confusion), confusion.sum()),
        "confusion": {"labels": list(labels), "rows": "정답", "columns": "예측", "matrix": confusion.tolist()},
    }


def metrics_table(results: Mapping[str, dict], labels: tuple[str, ...] = ACUITIES) -> str:
    """{이름: classification_metrics 결과} → 마크다운 표. 칸은 `분자/분모 (비율)`."""
    header = ["모델·규칙", *(f"{a} 재현율" for a in labels), *(f"{a} 정밀도" for a in labels), "정확도"]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for name, m in results.items():
        cells = [
            *(_cell(m["per_class"][a]["recall"]) for a in labels),
            *(_cell(m["per_class"][a]["precision"]) for a in labels),
            _cell(m["accuracy"]),
        ]
        lines.append("| " + " | ".join([name, *cells]) + " |")
    return "\n".join(lines) + "\n"


def _cell(r: dict) -> str:
    value = "-" if r["value"] is None else f"{r['value']:.1%}"
    return f"{r['n']}/{r['of']} ({value})"
