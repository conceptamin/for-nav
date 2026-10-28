# 04. 응급도 분류 모델(LightGBM)

상태: 완료
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
- [x] `uv run python scripts/train_acuity.py`가 로컬에서 5분 안에 끝남
- [x] 검증셋 기준 클래스별 재현율·정밀도가 분자·분모와 함께 결과에 있음(LightGBM, 로지스틱 회귀 각각)
- [x] 임계값 선택 기준과 선택된 값이 적혀 있음
- [x] **테스트셋 평가는 한 번만** 하고, 그 수치를 "최종"으로 표시해 적음. 이후 조정이 생기면 새 라운드로 기록
- [x] `tests/test_determinism.py` 통과
- [x] SHAP 상위 피처 예시 3건이 결과에 있음

## 결과
- 실행(2026-10-28)
  - `uv run python scripts/train_acuity.py` → 약 1초(`time` 0.94초 total). `models/acuity/v0/{model.txt,logistic.json,metadata.json}`, `reports/acuity_v0.{json,md}`를 만든다. test는 읽지 않는다
  - 결정성: 산출물을 지우고 다시 학습 → `model.txt`, `logistic.json`, `metadata.json`, `reports/acuity_v0.json`의 sha256이 모두 같음. `model.txt` `bec5c99116c1bc21d27017ac9e71761b76733a49377b40eefb0cf4955c255c21`
  - `uv run python scripts/evaluate.py --model acuity --round v0` → test 평가 1회, `reports/acuity_v0_test.{json,md}`. 다시 실행하면 `FileExistsError`로 멈춘다(라운드마다 한 번)
  - `uv run ruff check . && uv run ruff format --check .` → `All checks passed!`, `40 files already formatted`. `uv run pytest` → `79 passed`(기존 67 + `test_determinism.py` 3, `test_acuity.py` 9)
- 모델
  - LightGBM: multiclass, `learning_rate=0.05`, `num_leaves=15`, `min_data_in_leaf=20`, `lambda_l2=1.0`, seed `20261028`, `deterministic=True`, `num_threads=1`, `force_row_wise=True`. 라운드 수 86 — train 안 층화 5겹 교차검증 조기 종료(multi_logloss, 50라운드)로 정했다. valid는 라운드 수에 쓰지 않았다
  - 로지스틱 회귀(비교): 결측 → train 중앙값, 표준화, 다항 로지스틱(`C=1.0`). 같은 인터페이스(`fit`, `predict_proba`, `to_text`/`from_text`), JSON으로 저장
  - 둘 다 train 823행으로만 학습, valid 190행은 임계값과 평가에만 썼다
- 임계값(검증셋으로만 정함)
  - 기준: 검증셋 응급 재현율 목표 **95%**(사용자와 정함). 이를 만족하는 임계값 중 응급 정밀도가 가장 높은 것(같으면 높은 쪽). 경계는 고른 행의 확률과 바로 아래 확률의 중간으로 둬서 소수점 차이로 뒤집히지 않게 했다
  - 결정 규칙: `emergency` 확률 ≥ 임계값이면 응급, 아니면 `today`·`outpatient` 중 확률이 큰 쪽
  - LightGBM **0.0738**: 응급 재현율 36 / 37, 응급 정밀도 36 / 99. 로지스틱 0.0598: 36 / 37, 36 / 112
  - 임계값이 매우 낮다. 재현율 95%를 맞추려면 valid 190건 중 99건(52%)을 응급으로 본다
- 검증셋(valid 190건) — 칸은 분자 / 분모

| 모델·규칙 | emergency 재현율 | today 재현율 | outpatient 재현율 | emergency 정밀도 | today 정밀도 | outpatient 정밀도 | 정확도 |
|---|---|---|---|---|---|---|---|
| LightGBM argmax | 25/37 | 47/73 | 66/80 | 25/34 | 47/69 | 66/87 | 138/190 (72.6%) |
| LightGBM 임계값 | **36/37** | 26/73 | 50/80 | 36/99 | 26/31 | 50/60 | 112/190 (59.0%) |
| 로지스틱 argmax | 26/37 | 40/73 | 56/80 | 26/40 | 40/68 | 56/82 | 122/190 (64.2%) |
| 로지스틱 임계값 | 36/37 | 20/73 | 40/80 | 36/112 | 20/32 | 40/46 | 96/190 (50.5%) |

  - 혼동행렬(LightGBM 임계값, 행 = 정답 emergency/today/outpatient, 열 = 예측): `[[36, 1, 0], [37, 26, 10], [26, 4, 50]]`
- train+valid 5겹 교차검증(1,013건, 응급 197건. 라운드 수 86 고정, 임계값은 위 valid 값 그대로 — valid 행에는 낙관적)
  - LightGBM: 임계값 응급 재현율 184 / 197(93.4%), 정밀도 184 / 500, 정확도 616 / 1,013. argmax 정확도 738 / 1,013(72.9%)
  - 로지스틱: 임계값 응급 재현율 179 / 197(90.9%), 정밀도 179 / 529, 정확도 558 / 1,013. argmax 정확도 708 / 1,013(69.9%)
- **최종: test 평가(v0, 1회, 254건, 응급 49건)**

| 모델·규칙 | emergency 재현율 | today 재현율 | outpatient 재현율 | emergency 정밀도 | today 정밀도 | outpatient 정밀도 | 정확도 |
|---|---|---|---|---|---|---|---|
| LightGBM argmax | 24/49 | 61/98 | 88/107 | 24/40 | 61/92 | 88/122 | 173/254 (68.1%) |
| LightGBM 임계값 | **42/49 (85.7%)** | 32/98 | 66/107 | 42/129 | 32/43 | 66/82 | 140/254 (55.1%) |
| 로지스틱 argmax | 26/49 | 54/98 | 80/107 | 26/43 | 54/90 | 80/121 | 160/254 (63.0%) |
| 로지스틱 임계값 | 41/49 (83.7%) | 29/98 | 62/107 | 41/134 | 29/43 | 62/77 | 132/254 (52.0%) |

  - **test 응급 재현율 85.7%(42 / 49)로 검증셋 목표 95%에 못 미친다.** valid 응급이 37건뿐이라 임계값이 valid에 맞춰졌고, 교차검증(93.4%)보다도 낮다. 7건을 놓친다
  - 혼동행렬(LightGBM 임계값): `[[42, 4, 3], [53, 32, 13], [34, 7, 66]]`
- 비교 모델: 로지스틱 회귀가 valid·교차검증·test 모두 LightGBM보다 같거나 낮다(같은 응급 재현율에서 정밀도가 낮다). 서빙 후보는 LightGBM으로 둔다. test 수치를 보고 고른 것이 아니라 valid·교차검증으로 정했다
- SHAP 예시(valid, LightGBM, 최종 예측 클래스마다 id 순 첫 행. 기여도는 그 클래스의 원점수 단위, `reports/acuity_v0.json`의 `shap_examples_valid`)
  - `triage_0006` 정답 outpatient → 예측 **emergency**(응급 확률 0.0751, 임계값 바로 위): `symptom_fever`=1 +0.361, `body_chest`=0 −0.239, `pain_score`=3 −0.214
  - `triage_0017` 정답 outpatient → 예측 **today**: `body_abdomen`=1 +0.545, `pain_score`=4 +0.391, `sex_male`=1 −0.129
  - `triage_0009` 정답 outpatient → 예측 **outpatient**: `pain_score`=3 +1.157, `body_chest`=0 +0.393, `symptom_pain`=1 +0.347
  - 첫 예시처럼 임계값이 낮아 응급으로 잡힌 행은 응급 쪽 기여가 작다. 리포트 문장에 SHAP을 넣을 때는 이 점을 고려한다
- 발생 시점(`onset`, 03에서 넘김): valid 190행에 `onset`을 0~3으로 채워도 두 모델의 확률 변화 최댓값이 0.0. 학습 데이터에 없던 값이라 서빙 때 들어와도 예측에 영향이 없다(테스트 `test_unseen_onset_does_not_change_prediction`로도 확인)
- 만든 파일: `src/fornav_modeling/models/acuity.py`, `src/fornav_modeling/explain.py`, `src/fornav_modeling/evaluate.py`, `scripts/train_acuity.py`, `scripts/evaluate.py`, `tests/test_determinism.py`, `tests/test_acuity.py`, `models/acuity/v0/{model.txt,logistic.json,metadata.json}`, `reports/acuity_v0.{json,md}`, `reports/acuity_v0_test.{json,md}`
- 결정
  - SHAP 값은 LightGBM 내장 `pred_contrib`(TreeSHAP)로 구한다. `shap.TreeExplainer`와 값이 같은지 테스트로 확인했고, 서빙(08)에서 shap 패키지 없이 쓸 수 있다. `top_contributions`는 `{feature, value, contribution}`, |기여도| 순, 0은 뺀다
  - test 평가 결과는 `reports/acuity_<round>_test.json`에 `"final": true`로 쓰고, 파일이 있으면 다시 평가하지 않는다. 이 라운드를 test로 평가한 뒤 학습 결과가 바뀌면 `train_round`가 덮어쓰지 않고 멈춘다
  - test 평가는 서빙 후보(LightGBM)와 비교 모델(로지스틱)을 같은 1회에 함께 했다. 비교 수치를 남기기 위해서이고, 서빙 선택에는 쓰지 않았다
  - `metadata.json`은 임시 형식이다(모델 파일 해시, 학습 데이터 해시, seed, 파라미터, 라운드 수, 임계값, 피처·라벨 순서). 형식 확정은 08
  - 패키지 `evaluate.py`는 지표만 계산하고 데이터를 읽지 않는다. test를 읽는 곳은 `scripts/evaluate.py` 하나다(`test_split_isolation.py`가 검사)
- 남은 문제
  - 주증상 매핑 표가 사람 검토 전(`reviewed=no`)이다. 이 결과는 LLM 초안 표 기준이다. 검토 후 다시 학습하면 v1 라운드로 기록한다
  - test 응급 재현율 85.7%. 놓친 응급 7건은 test라 열어 보지 않는다. 개선은 train·valid의 오류 분석으로 새 라운드에서 한다
  - 응급 정밀도가 낮다(test 42 / 129). 응급이 아닌 사람 상당수를 응급실로 안내하게 된다. 레드플래그 규칙(모델 앞)이 함께 동작할 때의 결과는 아직 재지 않았다

## 메모
- 비교 모델이 더 좋으면 그대로 적고 어느 쪽을 서빙할지 사용자와 정한다
- 데이터가 작으므로 valid 수치의 신뢰구간이 넓다. 가능하면 train+valid로 5겹 교차검증 수치도 함께 적는다(test는 쓰지 않는다)
- (04에서) 개선 후보(새 라운드에서, 사용자와 정한 뒤): 매핑 표 검토, 매핑 안 된 주증상(의식 변화·전신 쇠약·실신 등)에 맞는 버튼 어휘, 임계값을 train+valid 교차검증 예측으로 정하기(valid 37건보다 안정적), 클래스 가중치
