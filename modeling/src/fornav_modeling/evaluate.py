# 지표 계산. 수치는 항상 분자·분모와 함께 둔다({"n": 분자, "of": 분모, "value": 비율}).
# 이 모듈은 데이터를 읽지 않는다. test 행은 평가 명령(scripts/evaluate.py)이 읽어서 넘긴다.

from collections.abc import Mapping

import numpy as np


def ratio(n: int, of: int) -> dict:
    return {"n": int(n), "of": int(of), "value": round(n / of, 4) if of else None}


def _cell(r: dict) -> str:
    value = "-" if r["value"] is None else f"{r['value']:.1%}"
    return f"{r['n']}/{r['of']} ({value})"


def topk_metrics(proba: np.ndarray, y_true: np.ndarray, labels: tuple[str, ...], ks: tuple[int, ...] = (1, 2)) -> dict:
    """Top-k 적중률(정답이 확률 상위 k개 안에 든 비율)과 정답 클래스별 분자·분모. 동점은 labels 순서가 앞선 쪽이 위다."""
    y_true = np.asarray(y_true)
    order = np.argsort(-proba, axis=1, kind="stable")  # 동점이면 열 번호(labels 순서)가 작은 쪽이 앞
    hits = {k: (order[:, :k] == y_true[:, None]).any(axis=1) for k in ks}
    return {
        **{f"top{k}": ratio(hits[k].sum(), len(y_true)) for k in ks},
        "per_class": {
            label: {f"top{k}": ratio(hits[k][y_true == i].sum(), (y_true == i).sum()) for k in ks}
            for i, label in enumerate(labels)
            if (y_true == i).any()
        },
    }


def topk_table(results: Mapping[str, dict], ks: tuple[int, ...] = (1, 2)) -> str:
    """{이름: topk_metrics 결과} → 마크다운 표."""
    lines = ["| 모델·평가셋 | " + " | ".join(f"Top-{k}" for k in ks) + " |", "|" + "---|" * (len(ks) + 1)]
    lines += ["| " + " | ".join([name, *(_cell(m[f"top{k}"]) for k in ks)]) + " |" for name, m in results.items()]
    return "\n".join(lines) + "\n"
