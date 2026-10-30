# 응급도·진료과 모델 연결(backlog 06). modeling의 predict()를 부르는 얇은 층이다.
# 피처 계산·임계값·버전은 modeling 쪽(predict.py, metadata.json)을 그대로 쓰고 여기에 다시 적지 않는다.
# 모델링 코드는 PYTHONPATH에 modeling/src를 넣어 import한다. MODEL_DIR이 비면 import하지 않는다(CI·기본 실행은 모델 없음).
# 아티팩트는 LightGBM 텍스트 모델과 JSON만 읽는다(modeling read_verified가 sha256을 확인한다).

import logging
from collections.abc import Callable
from pathlib import Path

from app.schemas import Intake, ModelPrediction

logger = logging.getLogger(__name__)

Predictor = Callable[[Intake], ModelPrediction]


def load_model(model_dir: str) -> Predictor | None:
    """서버 시작 시 한 번 부른다. 아티팩트를 미리 읽어 검증하고, 실패하면 서버가 뜨지 않는다."""
    if not model_dir:
        return None
    try:
        from fornav_modeling import predict as modeling
    except ImportError as exc:
        raise RuntimeError("MODEL_DIR를 쓰려면 PYTHONPATH에 modeling/src를 넣는다(README '실행')") from exc
    root = Path(model_dir)
    modeling.load_artifacts(str(root))

    def predict(intake: Intake) -> ModelPrediction:
        # 모델 입력은 Intake의 Python 필드 이름(snake_case) dict다. 값이 없는 선택 필드는 키가 빠지고, 모델링이 결측으로 다룬다.
        return ModelPrediction.model_validate(modeling.predict(intake.model_dump(), root))

    return predict


def run_model(model: Predictor | None, intake: Intake) -> ModelPrediction | None:
    """모델 예측. 모델이 없거나 예측 중 오류가 나면 None이고, 응급 판정은 규칙·보조 점수로 돌아간다."""
    if model is None:
        return None
    try:
        return model(intake)
    except Exception as exc:
        # 입력값이 들어갈 수 있는 예외 메시지는 남기지 않는다.
        logger.warning("model predict failed=%s", type(exc).__name__)
        return None
