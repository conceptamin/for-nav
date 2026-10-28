# 08. 진료과 앙상블, 폴백, 모델 내보내기, 예측 함수

상태: 완료
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
- [x] 앙상블 검증 Top-2 적중률이 A 단독·B 단독과 함께 분자·분모로 적혀 있음. 선택된 가중치와 폴백 기준값이 적혀 있음
- [x] 폴백이 발동한 비율(검증셋)이 적혀 있음
- [x] `tests/test_predict_contract.py` 통과. `grep -r pickle src/`가 비어 있음
- [x] `models/*/v1/metadata.json`에 위 항목이 모두 있음
- [x] `uv run python -c "from fornav_modeling.predict import predict; print(predict({...}))"` 예시 입력 3건(내과 질환, 외상, 치아)의 출력이 결과에 있음
- [x] 응급도·진료과 테스트셋 최종 수치가 "최종" 표시로 적혀 있음

## 결과
- 실행(2026-10-28). 07 브랜치(`modeling/department-model-b`, PR #48) 위에서 작업했다
  - `uv run python scripts/tune_ensemble.py` → 1.7초. `models/ensemble/v1/ensemble.json`, `reports/ensemble_v1.{json,md}`
  - `uv run python scripts/evaluate.py --model ensemble --round v1` → test 1회, `reports/ensemble_v1_test.{json,md}`
  - `uv run python scripts/export_models.py` → `models/{acuity,dept_a,dept_b,ensemble}/v1/`. 다시 돌리면 `metadata.json`의 `created_at`만 바뀐다(모델 파일 sha256은 v0과 같다: 응급도 `bec5c991…`, 모델 A `8fa60486…`, 모델 B `fd6930ea…`, 앙상블 `fd3e6811…`)
  - `uv run ruff check . && uv run ruff format --check .` → `All checks passed!`. `uv run pytest` → `167 passed`(기존 148 + `test_predict_contract.py` 19). `grep -r pickle src/` → 비어 있음(`models/acuity.py` 주석의 낱말 하나를 바꿨다)
- 결정 사항(사용자와 정함, 2026-10-28)
  - **응급도 "모름" 처리**: 의식 상태를 모르면 alert(앱을 쓰는 사람). 성별·나이대·손상 여부를 모르면 가능한 값 조합(최대 16개)을 모두 넣어 응급 확률이 가장 높은 조합을 쓴다. 규칙은 `models/acuity/v1/metadata.json`의 `unknown_inputs`에 있다
  - **조정 셋**: 진료과 검증셋(안내 조합 29건) + Kaggle valid 44건 = 73건. Top-2 적중 수가 기준. 같은 행으로 고르고 재면 낙관적이라 leave-one-out 수치를 함께 적는다
  - **출력**: 네 키(`acuity`, `acuityProba`, `departmentProba`, `shap`)에 `departmentTop2`, `departmentFallback`을 더했다. 백엔드는 `departmentTop2`를 `DepartmentPair`에 바로 옮긴다
  - **추가로 정한 것(구현 중 발견)**: 동점일 때 폴백 기준값을 낮은 쪽으로 고르면 적중 수가 같은 0.0(폴백 없음)이 뽑혀 설계 원칙 "확신도가 낮으면 폴백"이 사라졌다. 적중을 잃지 않는 범위에서 **높은 기준값**을 고르게 바꿨다. 그 결과 기준값이 0.0 → 0.25
  - `departmentProba`는 합 1로 다시 맞춰 내보낸다. 모델 A의 질환별 진료과 비율이 소수 넷째 자리 반올림이라 합이 1에서 1e-5쯤 벗어난다. 상위 2개·폴백은 조정·평가와 같게 맞추기 전 값으로 고른다
  - 모델 B의 추론 함수(`forward`, `predict_from_weights`)를 `predict.py`로 옮기고 `models/dept_b.py`가 가져다 쓴다(서빙과 학습이 같은 함수). 모델 B 산출물은 그대로다
- **선택**: 모델 A 가중치 **0.5**(B 0.5), 폴백 기준값 **0.25**(앙상블 최대 확률 < 0.25이면 상위 2개 = 가정의학과, 내과). 격자: A 가중치 0.0~1.0(0.1 간격) × 기준값 {0.0, 0.15~0.60(0.05 간격)}. Top-2 적중 65 / 73이 가중치 0.4·0.5·0.6, 기준값 0.0~0.25에서 같았다
- **조정 셋 결과** — 칸은 분자 / 분모

| 규칙 | 73건 Top-2 | 안내 29 Top-1 | 안내 29 Top-2 | Kaggle valid 44 Top-1 | Kaggle valid 44 Top-2 | 안내 중 외상·산재 10 Top-2 |
|---|---|---|---|---|---|---|
| A 단독 | 52 / 73 | 5 / 29 | 10 / 29 | 40 / 44 | 42 / 44 | 2 / 10 |
| B 단독 | 57 / 73 | 18 / 29 | 23 / 29 | 24 / 44 | 34 / 44 | 7 / 10 |
| 0.5 : 0.5, 폴백 없음 | 65 / 73 | 17 / 29 | 22 / 29 | 37 / 44 | 43 / 44 | 6 / 10 |
| **선택(0.5, 폴백 0.25)** | **65 / 73** | 17 / 29 | **22 / 29** | 37 / 44 | **43 / 44** | 6 / 10 |
| leave-one-out(선택 규칙) | 63 / 73 | 16 / 29 | 20 / 29 | 37 / 44 | 43 / 44 | 5 / 10 |

  - 앙상블은 두 셋을 합친 73건에서 A·B 단독보다 낫지만, 안내 조합 29건만 보면 B 단독(23 / 29)보다 하나 적다(22 / 29). Kaggle 쪽(A가 강함)과 안내 쪽(B가 강함)을 함께 맞추는 가중치라서다
  - **폴백 발동**: 조정 셋 **1 / 73**(안내 1 / 29, Kaggle valid 0 / 44). 발동한 행은 `head-pain-no`(앙상블 최대 확률 0.233, 정답 신경과 → 폴백으로 Top-2를 놓침). leave-one-out에서는 2 / 73
  - 안내 조합 29건은 모두 `reviewed=no`
- **최종: test 평가(v1, 1회)**
  - 진료과(Kaggle test 59건, 정답 = 질환의 1순위 진료과)

| 규칙 | Top-1 | Top-2 | 폴백 |
|---|---|---|---|
| **앙상블(0.5, 폴백 0.25) — 최종** | **52 / 59** | **58 / 59** | 0 / 59 |
| A 단독 | 56 / 59 | 58 / 59 | 0 / 59 |
| B 단독 | 27 / 59 | 45 / 59 | 0 / 59 |

  - 응급도(04 최종, v1은 같은 모델): LightGBM 임계값 0.0738, test 254건 응급 재현율 **42 / 49(85.7%)**, 정확도 140 / 254
  - 진료과 모델에는 안내 조합과 별도인 테스트셋이 없어, 버튼 입력에 가까운 조합의 최종 수치는 없다(07 메모)
- **`predict` 예시**(`PYTHONPATH=src uv run python -c "from fornav_modeling.predict import predict; ..."`. `package = false`라 `src`를 직접 경로에 넣는다). 나이대·성별·손상 여부는 주지 않았다(지금 백엔드 `Intake`와 같음)

| 입력 | `acuity` | `acuityProba`(응급/오늘/외래) | `departmentTop2` | 폴백 | `shap` 상위 |
|---|---|---|---|---|---|
| 배 + 통증·구역·열(내과 질환) | emergency | 0.169 / 0.652 / 0.179 | internal, family | 아니오 | 열 +0.73, 구역 +0.70, 통증 점수(모름) −0.40 |
| 손 + 베임·출혈, 손상 있음(외상) | emergency | 0.078 / 0.254 / 0.668 | surgery, ortho | 아니오 | 통증 점수(모름) −0.72, 출혈 −0.23, 가슴(아님) −0.19 |
| 치아 + 통증·부기 | emergency | 0.089 / 0.338 / 0.573 | dental, internal | 아니오 | 통증 점수(모름) −0.76, 가슴(아님) −0.23, 의식 alert −0.13 |
| 치아 + 통증·부기, 30–44세·남성·손상 없음·통증 5 | today | 0.044 / 0.650 / 0.305 | dental, internal | 아니오 | 통증 점수 +0.65, 배(아님) −0.41, 나이대 +0.22 |

  - 진료과는 셋 다 상식과 맞다(내과 질환 → 내과, 손 열상 → 외과·정형외과, 치아 → 치과)
- **주의: 응급도가 거의 다 응급으로 나온다.** 04의 임계값(0.0738, 재현율 95% 목표)이 낮은 데다 "모름"을 최악값으로 채우기 때문이다. 응급도 valid 190건(실제 응급 37건)에 같은 규칙을 적용해 보면:

| 입력 | 응급 / 오늘 / 외래 예측 | 응급 재현율 |
|---|---|---|
| 다 앎 | 99 / 31 / 60 | 36 / 37 |
| 나이대 모름 | 123 / 25 / 42 | 36 / 37 |
| 성별·나이대·손상 여부 모름 | 147 / 14 / 29 | 37 / 37 |
| + 통증 점수·의식 모름(지금 백엔드 입력과 같음) | **153 / 30 / 7** | 35 / 37 |

  - 지금 백엔드 입력이면 190건 중 153건(81%)을 응급으로 본다. 응급 안내가 남발되면 안내가 의미를 잃는다. 해결은 이 backlog 범위 밖이라 아래 메모에 남겼다
- 남은 문제
  - 응급 과다(위). 백엔드 `Intake`에 나이대·성별·손상 여부·통증 점수를 받거나, 04 임계값을 새 라운드에서 다시 정해야 한다
  - `acuity` 문자열 값(`emergency`/`today`/`outpatient`)과 `departmentTop2`·`departmentFallback`은 백엔드 `TriageResult.model`에 아직 정의되지 않았다. 백엔드 연결 시 확인이 필요하다

## 메모
- `acuity` 문자열 값(`emergency`/`today`/`outpatient`)은 백엔드 `TriageResult.model`에 아직 정의되지 않았다. 백엔드 연결 시 확인이 필요하다고 알린다
- 레드플래그·명확 케이스 규칙은 백엔드가 모델 앞에서 실행한다. `predict`는 규칙을 포함하지 않는다
- (04 이후 확인) **응급도 모델에 "모름"이 들어올 때의 처리를 `predict.py`에서 정해야 한다.** 학습 데이터에 결측이 없던 피처는 LightGBM이 서빙 때 들어온 NaN을 0으로 바꿔 처리한다. 응급도 v0 모델(`models/acuity/v0/model.txt`)에 valid 190행으로 확인했다(NaN을 넣은 예측 = 0을 넣은 예측, 2026-10-28)
  - `sex_male` → 여성(0), `mental` → alert(0), `age_group` → 30세 미만(0), `injury` → 손상 없음(0). 비교용 로지스틱 회귀는 train 중앙값으로 채운다(남성, alert, 45–64세, 손상 없음)
  - 특히 나이대를 모를 때 응급 확률이 가장 낮은 구간(30세 미만)으로 보므로, 응급을 놓치지 않는다는 원칙과 반대 방향이다
  - 선택지: ① 이 값들을 필수 입력으로 받는다(백엔드 `Intake`·프론트 버튼과 함께 정함) ② `predict`가 모를 때 보수적인 값으로 채운다(예: 나이대 65세 이상, 의식 alert 유지 여부는 따로 정함). 어느 쪽인지 사용자와 정하고, 정한 규칙을 `metadata.json`에 적는다
  - `pain_score`(train에 결측 3건)와 `onset`(전부 결측)은 학습 때 결측을 봤으므로 이 문제에 해당하지 않는다
- (08에서) **응급 과다**: 지금 백엔드 입력(부위·증상뿐)이면 응급도 valid 190건 중 153건이 응급으로 나온다. 선택지 ① 백엔드 `Intake`·프론트 버튼에 나이대·성별·손상 여부·통증 점수를 더한다(`backend/` 작업) ② 04 응급도를 새 라운드(v2)로 학습해 "모름"이 섞인 입력으로 임계값을 다시 정한다(학습 때 일부 행의 값을 지워 결측을 보게 하는 방법 포함). 어느 쪽인지 사용자와 정한다
- (08에서) 앙상블 가중치·폴백 기준은 진료과 검증셋과 Kaggle valid로 정했다. 안내 조합을 사람이 검토(`reviewed=yes`)하거나 더 모으면 `tune_ensemble.py`를 새 라운드로 다시 돌린다
