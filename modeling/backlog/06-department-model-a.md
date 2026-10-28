# 06. 진료과 모델 A(증상 → 질환 → 진료과)

상태: 완료
의존: 05

## 목표
Kaggle 증상 데이터로 질환 확률을 예측하는 LightGBM 다중 분류 모델을 학습하고, `disease_department.csv`로 진료과 확률 분포로 바꾼다. 질환 확률은 내부 산출물이고 바깥으로는 진료과 분포만 나간다.

## 범위
- 하는 것
  - `data/kaggle_symptom.py`: 원본 → 표준 테이블, `symptom_map.csv`로 우리 `Symptom`·`BodyPart` 피처로 변환. 매핑 안 된 증상은 버린다
  - `data/split.py` 확장: 질환 데이터 분할(`data/splits/symptom_*`), test 해시 고정
  - `models/dept_a.py`: 학습(seed 고정), 질환 확률 예측, 질환 확률 × 질환별 진료과 비율 합산 → `Department` 10종 분포. 출력 dict에는 질환명이 없다
  - `evaluate.py` 확장: 진료과 Top-1·Top-2 적중률(분자·분모). 정답은 질환 라벨을 표로 바꾼 1순위 진료과
  - `scripts/train_dept_a.py`, `scripts/evaluate.py --model dept_a`
- 하지 않는 것
  - 외상·산재 조합 보강(모델 B 역할), 앙상블(08)

## 입력·출력
- 입력: `data/raw/kaggle_symptom/`, `data/tables/symptom_map.csv`, `data/tables/disease_department.csv`
- 출력: `models/dept_a/v0/model.txt`, `data/splits/symptom_*`, `reports/dept_a_v0.json`

## 완료 기준
- [x] 학습 5분 이내, 같은 seed 두 번 → 같은 해시(`tests/test_determinism.py` 확장)
- [x] 검증셋 Top-1·Top-2 적중률이 분자·분모와 함께 있음
- [x] 변환 후 피처 수(우리 증상·부위로 매핑된 수)와 버린 증상 수가 적혀 있음
- [x] 출력 dict의 키가 `Department` 10종만이라는 테스트 통과(질환명 비노출)
- [x] 테스트셋 평가는 한 번만, "최종" 표시

## 결과
- 실행(2026-10-28). 05 브랜치(`modeling/department-tables`, PR #45) 위에서 작업했다
  - `uv run python scripts/make_splits.py --dataset symptom` → `data/processed/symptom.parquet`, `data/test/symptom_test.parquet`, `data/splits/symptom_{train,valid,test}.txt`, `symptom_test.sha256`, `reports/symptom_splits.json`. 응급도 분할(`make_splits.py` 기본값)은 다시 돌려도 바뀌지 않음을 확인했다
  - `uv run python scripts/train_dept_a.py` → **3.1초**. `models/dept_a/v0/{model.txt,departments.json,metadata.json}`, `reports/dept_a_v0.{json,md}`. test는 읽지 않는다
  - 결정성: 다시 학습 → `model.txt`, `departments.json`, `metadata.json`, `reports/dept_a_v0.json`의 sha256이 모두 같음. `model.txt` `8fa6048612abefddaf5ca2d0155b652c8d1ada8415be7d5d33862160995b5933`. `tests/test_determinism.py`에 모델 A 두 개를 더했다
  - `uv run python scripts/evaluate.py --model dept_a --round v0` → test 1회, `reports/dept_a_v0_test.{json,md}`. 다시 실행하면 `FileExistsError`로 멈춘다
  - `uv run ruff check . && uv run ruff format --check .` → `All checks passed!`. `uv run pytest` → `137 passed`(기존 126 + `test_dept_a.py` 9, `test_determinism.py` 2)
- 데이터 변환(`kaggle_symptom.standardize`)
  - **중복 제거**: 원본 4,920행은 같은 (질환, 증상 집합)이 6~90번 반복된 것이라 고유 **304행**으로 줄였다. 남기면 같은 행이 train과 test에 함께 들어간다. 반복 횟수는 원본 생성 방식이라 가중치로 쓰지 않았다
  - **우리 증상이 하나도 없는 행 12개를 버렸다** → **292행, 질환 40종**. 당뇨병은 증상 10개(다뇨·체중 감소·피로 등)가 모두 우리 `Symptom`에 없어 9행 전부 빠져 모델 A에서 사라졌다(`symptom_map.csv`에서 버튼 증상이 붙지 않음). 백엔드는 증상이 없으면 진료과를 추천하지 않으므로 그런 입력이 모델까지 오지 않는다
  - 피처: `features/buttons.py`의 34개 피처를 그대로 쓴다(서빙과 같은 함수). Kaggle 증상 131개 중 우리 `Symptom`으로 가는 것 **75개**, 버린 증상 **56개**. 남은 행에 실제로 나오는 버튼 피처는 부위 **12 / 13**(치아 없음), 증상 **11 / 15**(베임·화상·화학물질·이물감 없음). 나머지 피처(통증 점수·의식·나이대·발생 시점·성별·손상 여부)는 원본에 없어 전부 결측이고, 서빙 때 값이 들어와도 예측이 바뀌지 않는다(`test_non_button_features_do_not_change_prediction`)
  - 분할: 질환으로 층화, 응급도와 같은 비율(test 20%, valid 15%)과 seed `20261027`. train **189** / valid **44** / test **59**, 세 분할 모두 질환 40종이 들어 있다
- 모델
  - LightGBM multiclass(질환 40종), `learning_rate=0.05`, `num_leaves=7`, `min_data_in_leaf=3`, `lambda_l2=1.0`, seed `20261028`, `deterministic=True`, `num_threads=1`. 질환당 train 행이 2~7개라 04보다 잎을 작게 두고, 라운드 수는 train 안 층화 **3겹** 교차검증 조기 종료로 정했다(5겹은 한 겹에 질환이 빠진다). 라운드 수 **954**(상한 1,000에 가깝다 — 데이터가 작아 손실이 천천히 줄어든다). 하이퍼파라미터는 valid로 고르지 않았다
  - 진료과 확률 = 질환 확률 × `disease_department.csv`의 질환별 진료과 비율. 내보내는 `departments.json`에는 질환 번호별 비율 행렬만 있고 질환명이 없다. `models/dept_a/`, `reports/dept_a_*`, `reports/symptom_splits.json`에 Kaggle 질환명 41개 중 어느 것도 나오지 않음을 확인했다
- 정답: 질환 라벨을 `disease_department.csv`로 바꾼 1순위 진료과. 질환 40종의 1순위 진료과가 내과 25종이라 정답이 내과로 쏠린다(valid 44건 중 26건, test 59건 중 40건)
- 검증셋 — 칸은 분자 / 분모

| 모델·평가셋 | Top-1 | Top-2 |
|---|---|---|
| LightGBM valid(Kaggle 44건) | 40 / 44 (90.9%) | 42 / 44 (95.5%) |
| 기준선: 입력을 보지 않고 train 질환 빈도 분포(valid) | 26 / 44 (59.1%) | 31 / 44 (70.5%) |
| LightGBM train+valid 3겹 교차검증(233건) | 221 / 233 (94.8%) | 226 / 233 (97.0%) |
| **LightGBM 진료과 검증셋(05의 안내 조합 29건)** | **5 / 29 (17.2%)** | **10 / 29 (34.5%)** |

  - 질환 자체의 1순위 적중(내부 지표, 질환명 없이 건수만): valid 35 / 44, 교차검증 196 / 233
  - valid 정답 진료과별 Top-2: internal 26 / 26, family 5 / 5, neuro 3 / 3, derm 3 / 3, ortho 2 / 3, ent 2 / 2, surgery 1 / 2. 기준선은 internal·family만 맞힌다
  - **진료과 검증셋에서는 낮다.** 이 셋은 부위 하나 + 증상 하나 조합이고, Kaggle은 증상 여러 개로 질환을 맞히는 데이터라 입력 모양이 다르다. 정답 진료과별 Top-2: internal 4 / 4, family 3 / 3, ortho 2 / 6, neuro 1 / 4, ophth 0 / 4, ent 0 / 2, derm 0 / 2, surgery 0 / 2, dental 0 / 1, occ 0 / 1. 학습 데이터에 없는 눈·치아·외상·화학물질 쪽을 못 맞힌다. 29건 모두 `reviewed=no`라 사람 검토 후 다시 잰다
- **최종: test 평가(v0, 1회, Kaggle 59건)**

| 모델·평가셋 | Top-1 | Top-2 |
|---|---|---|
| LightGBM test(Kaggle) — 최종 | **56 / 59 (94.9%)** | **58 / 59 (98.3%)** |

  - 정답 진료과별 Top-2: internal 40 / 40, family 5 / 5, ortho 3 / 3, surgery 3 / 3, derm 3 / 3, ent 2 / 2, neuro 2 / 3
  - Kaggle 안에서는 높지만, 실제 버튼 입력에 가까운 진료과 검증셋(17.2% / 34.5%)과 차이가 크다. 모델 A 단독으로 쓰지 말고 앙상블(08)에서 내과 질환 쪽 근거로만 쓰는 게 맞다
- 남은 문제
  - 당뇨병처럼 증상이 버튼에 없는 질환은 모델 A가 다루지 못한다
  - 진료과 검증셋 성능은 모델 B(07)·앙상블(08)과 같은 셋으로 비교한다

## 메모
- 영어권 데이터라 외상 증상이 부족하다. 외상 조합에서 성능이 낮게 나오면 그대로 적고 앙상블 가중치(08)에서 다룬다
