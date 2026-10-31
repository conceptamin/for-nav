# 15. 응급도 분류 모델과 학습 자산 지우기

상태: 대기
의존: backend 26(서버가 `model.acuity`를 읽지 않음)

## 목표
앱이 응급 여부를 판정하지 않기로 했다(frontend 43, backend 26, 사용자와 정함 2026-10-31). 응급도 3단계 모델(즉시 응급 / 오늘 병원 / 외래·약국)은 쓰는 곳이 없어진다. `predict()`를 진료과 전용으로 줄이고, 응급도 학습·평가 자산을 지운다. 기록은 git 이력에 남는다.

## 범위
- 하는 것
  - `predict.py`
    - 출력을 `{ departmentProba, departmentTop2, departmentFallback }`으로 줄인다
    - `ACUITIES`, `acuity_features`, `decide_acuity`, 응급도 "모름" 처리(`UNKNOWN_*`)를 뺀다
    - `load_artifacts`는 `dept_a`·`dept_b`·`ensemble`만 읽는다
  - `export.py`, `scripts/export_models.py`: `acuity/` 내보내기
  - `schema.py`: `AgeGroup`·`Mental`과 `Intake`의 `age_group`·`sex`·`mental`·`pain_score`를 뺀다(백엔드 26과 같게). `tests/test_schema.py`도 맞춘다
  - 지우는 것
    - 응급도 모델: `models/acuity.py`, `scripts/train_acuity.py`, `models/acuity/`, `reports/acuity_*`, `explain.py`(SHAP은 응급도만 썼다)
    - 응급 판정 평가: `pipeline.py`, `scripts/evaluate.py`의 `pipeline` 분기, `reports/pipeline_v2_test.*`
    - 트리아지 데이터: `labels/ktas.py`, `data/kaggle_triage.py`, `data/download.py`의 `kaggle_triage`, `scripts/make_splits.py`의 응급도 분할, `data/splits/triage_*`, `reports/triage_*`
    - 활력징후 실험: `experiment_vitals.py`, `scripts/experiment_vitals.py`, `reports/experiment_vitals*`, `reports/figures/experiment_vitals_*`
    - 노트북: `notebooks/04_acuity_model_report.ipynb`
    - 테스트: 위 파일에 딸린 `test_acuity`·`test_labels`(KTAS 부분)·`test_pipeline`·`test_experiment_vitals`, 그리고 `test_determinism`·`test_split_isolation`·`test_predict_contract`·`test_features`의 응급도 부분
  - `README.md`·`data/README.md`·`pyproject.toml` 설명: 응급도 분류 행, 응급도 모델 세부 절, 데이터 표의 Kaggle Triage·MIMIC-IV-ED, 명령 목록, `predict()` 출력 예시
  - `CLAUDE.md`: 첫 줄 소개, 폴더 표(`kaggle_triage.py`·`vitals.py`·`ktas.py`·`acuity.py`·`explain.py`·`experiment_vitals.py`·`pipeline.py`·`train_acuity.py`·`models/acuity/`), "설계에서 바꾸지 않는 것"의 "규칙이 모델보다 먼저다"·"피처는 버튼으로 받을 수 있는 것만"(통증·의식·나이대·성별)·"응급도는 3단계다", 평가 지표(응급 재현율·레드플래그 누락), 출력 형태(`acuity`·`acuityProba`·`shap`)
  - `backlog/14-center-consult-data.md`: 응급 키워드 범위 점검을 범위에서 뺀다
- 하지 않는 것
  - `features/buttons.py`의 `FEATURE_NAMES` 순서·인코딩. 진료과 모델 A가 이 순서로 학습했다. A의 실제 피처 중요도에 `pain_score`·`mental`·`age_group`·`sex_male`·`onset`이 없으므로 줄일 수는 있지만, 모델을 다시 학습해 버전을 올려야 하니 따로 한다
  - 진료과 모델 A·B·앙상블 아티팩트(`v2` 그대로)

## 파일
- 수정: `src/fornav_modeling/{predict,export,schema}.py`, `scripts/{evaluate,export_models,make_splits}.py`, `src/fornav_modeling/data/download.py`, `tests/`, 문서
- 삭제: 위 목록
- 출력 계약: `predict()`에서 `acuity`·`acuityProba`·`shap`이 빠진다. 백엔드는 backend 26부터 읽지 않는다

## 완료 기준
- [ ] `uv run ruff check . && uv run pytest` 통과
- [ ] `test_predict_contract`: `predict()`가 학습 코드를 import하지 않고, 출력 키가 진료과 셋이다
- [ ] `models/acuity/`가 없어도 `load_artifacts`가 통과하고, 진료과 Top-2가 지우기 전과 같다(ensemble 조정 셋 73건)
- [ ] backend에서 `MODEL_DIR=../modeling/models`로 `uv run pytest`와 `/api/triage` 수동 호출이 통과한다

## 결과

## 메모
- 메인 체크아웃에 커밋하지 않은 `notebooks/04_acuity_model_report.ipynb` 수정이 있다(2026-10-31). 지우기 전에 살릴지 사용자에게 묻는다
- 지금까지의 응급도 backlog(04, 09, 10, 12)는 기록으로 두고 고치지 않는다
