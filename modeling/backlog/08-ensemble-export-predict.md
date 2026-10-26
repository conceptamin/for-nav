# 08. 진료과 앙상블, 폴백, 모델 내보내기, 예측 함수

상태: 대기
의존: 04, 06, 07

## 목표
모델 A·B를 가중 평균해 상위 2개 진료과를 내고, 확신도가 낮으면 가정의학과·내과로 폴백한다. 응급도·진료과 모델을 코드 실행 없이 불러올 수 있는 형식으로 내보내고, 백엔드가 부를 `predict.py` 순수 함수를 완성한다.

## 범위
- 하는 것
  - `models/ensemble.py`: A·B 분포 가중 평균(초기 0.5:0.5), 검증셋으로 가중치 격자 탐색, 상위 2개 선택, 폴백 기준(최대 확률이 기준값 미만이면 `family`, 그 다음 `internal`)
  - `export.py`: `models/<name>/v1/` 아래 아티팩트와 `metadata.json`(모델 버전, 학습 데이터 sha256, seed, 임계값, 가중치, 폴백 기준, 피처 순서, 라벨 순서, 검증·최종 측정값, 생성 시각)
  - `predict.py`: 입력 `Intake` dict(snake_case) → `{ "acuity": "emergency"|"today"|"outpatient", "acuityProba": {...}, "departmentProba": {...}, "shap": [...] }`. 아티팩트만 읽고 학습 코드를 import하지 않는다
  - `scripts/tune_ensemble.py`, `scripts/export_models.py`, `scripts/evaluate.py --model ensemble`
  - `tests/test_predict_contract.py`: 출력 키·형태, `departmentProba` 키가 `Department` 10종만, 확률 합 1, 아티팩트 로드 시 pickle 미사용
  - `README.md`에 아티팩트 형식과 `predict` 사용법 반영
- 하지 않는 것
  - 백엔드 라우터·스키마 수정(`backend/` 브랜치로), LLM 리포트, 병원 연결

## 입력·출력
- 입력: 04·06·07의 v0 모델, `data/splits/dept_valid.txt`
- 출력: `models/{acuity,dept_a,dept_b,ensemble}/v1/`, `predict.py`, `reports/ensemble_v1.json`

## 완료 기준
- [ ] 앙상블 검증 Top-2 적중률이 A 단독·B 단독과 함께 분자·분모로 적혀 있음. 선택된 가중치와 폴백 기준값이 적혀 있음
- [ ] 폴백이 발동한 비율(검증셋)이 적혀 있음
- [ ] `tests/test_predict_contract.py` 통과. `grep -r pickle src/`가 비어 있음
- [ ] `models/*/v1/metadata.json`에 위 항목이 모두 있음
- [ ] `uv run python -c "from fornav_modeling.predict import predict; print(predict({...}))"` 예시 입력 3건(내과 질환, 외상, 치아)의 출력이 결과에 있음
- [ ] 응급도·진료과 테스트셋 최종 수치가 "최종" 표시로 적혀 있음

## 결과

## 메모
- `acuity` 문자열 값(`emergency`/`today`/`outpatient`)은 백엔드 `TriageResult.model`에 아직 정의되지 않았다. 백엔드 연결 시 확인이 필요하다고 알린다
- 레드플래그·명확 케이스 규칙은 백엔드가 모델 앞에서 실행한다. `predict`는 규칙을 포함하지 않는다
