# 04. 응급도 분류 모델(LightGBM)

상태: 대기
의존: 03

## 목표
버튼 피처만으로 3단계 응급도를 예측하는 LightGBM 모델을 학습하고, 응급 재현율을 우선하는 임계값을 검증셋으로 정한다. SHAP으로 판단 근거를 낼 수 있게 한다.

## 범위
- 하는 것
  - `models/acuity.py`: 학습(seed·`deterministic=True`·`num_threads=1` 고정), 예측, 임계값 적용. 로지스틱 회귀 비교 모델도 같은 인터페이스로
  - 임계값: `emergency` 확률이 기준값 이상이면 응급으로. 검증셋에서 응급 재현율 목표를 먼저 정하고 그 목표를 만족하는 임계값 중 정밀도가 가장 높은 값을 고른다. 목표치는 사용자와 확인
  - `explain.py`: SHAP 값 계산, 상위 기여 피처 n개를 `{feature, value, contribution}`로 반환
  - `evaluate.py`: 클래스별 재현율·정밀도(분자·분모), 혼동행렬, Top-1 정확도. 결과를 `reports/acuity_<round>.json`과 표로 저장
  - `scripts/train_acuity.py`, `scripts/evaluate.py --model acuity`
  - 테스트: 같은 seed 두 번 학습 → 같은 모델 문자열 해시
- 하지 않는 것
  - 활력징후 피처(09), 내보내기·메타데이터 형식 확정(08), 백엔드 연결

## 입력·출력
- 입력: `data/processed/triage.parquet`, `data/splits/triage_*`, `features/buttons.py`
- 출력: `models/acuity/v0/model.txt`(LightGBM 텍스트)와 임시 메타데이터, `reports/acuity_v0.json`, `tests/test_determinism.py`

## 완료 기준
- [ ] `uv run python scripts/train_acuity.py`가 로컬에서 5분 안에 끝남
- [ ] 검증셋 기준 클래스별 재현율·정밀도가 분자·분모와 함께 결과에 있음(LightGBM, 로지스틱 회귀 각각)
- [ ] 임계값 선택 기준과 선택된 값이 적혀 있음
- [ ] **테스트셋 평가는 한 번만** 하고, 그 수치를 "최종"으로 표시해 적음. 이후 조정이 생기면 새 라운드로 기록
- [ ] `tests/test_determinism.py` 통과
- [ ] SHAP 상위 피처 예시 3건이 결과에 있음

## 결과

## 메모
- 비교 모델이 더 좋으면 그대로 적고 어느 쪽을 서빙할지 사용자와 정한다
- 데이터가 작으므로 valid 수치의 신뢰구간이 넓다. 가능하면 train+valid로 5겹 교차검증 수치도 함께 적는다(test는 쓰지 않는다)
