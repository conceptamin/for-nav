# 10. 응급도 v2: "모름"이 섞인 입력에 맞춘 학습과 임계값

상태: 완료
의존: 04, 08

## 목표
지금 백엔드는 부위·증상만 보내서, 08의 응급도(v0 모델 + 최악값 채움)는 valid 190건 중 153건을 응급으로 본다. 학습 때 성별·나이대·손상 여부·통증 점수가 비어 있는 행을 함께 보여 줘 모델이 결측을 배우게 하고, 임계값을 "다 앎"과 "지금 백엔드 입력" 두 입력 모양에서 모두 응급 재현율 95%를 넘게 다시 정한다.

## 범위
- 하는 것
  - `models/acuity.py`: train 행을 원본 + 네 값을 모두 지운 복사본 + 값마다 절반 확률로 지운 복사본으로 늘려 학습(seed 고정). 라운드 수 교차검증은 같은 원본 행의 복사본을 같은 겹에 둔다
  - 임계값: 두 입력 모양 각각에서 재현율 95%를 만족하는 임계값 중 작은 쪽(둘 다 만족)
  - `predict.py`: 최악값 채움을 빼고 모르는 값은 결측으로 넘긴다. 의식 상태 모름 → alert는 유지
  - `export.py`: 서빙 묶음을 `models/*/v2/`로 올린다(응급도는 v2, 진료과는 v0·앙상블 v1을 그대로)
  - test 평가 1회("최종"), 두 입력 모양으로 나눠 적는다
- 하지 않는 것
  - 백엔드 `Intake`에 필드 추가(`backend/` 작업), 진료과 모델·앙상블 다시 조정

## 입력·출력
- 입력: `data/processed/triage.parquet`, `data/splits/triage_*`
- 출력: `models/acuity/v2/`, `reports/acuity_v2*.{json,md}`, `models/{acuity,dept_a,dept_b,ensemble}/v2/`(서빙 묶음)

## 완료 기준
- [x] 같은 seed로 두 번 학습 → 같은 모델 해시
- [x] valid에서 두 입력 모양 모두 응급 재현율 ≥ 95%(분자·분모), 응급 예측 건수가 v0 + 최악값 채움(153 / 190)과 함께 적혀 있음
- [x] test 평가 1회, 두 입력 모양별 응급 재현율·응급 예측 건수가 "최종"으로 적혀 있음
- [x] `predict`가 모르는 값을 결측으로 넘기고, `tests/test_predict_contract.py`가 v2 묶음으로 통과

## 결과
- 실행(2026-10-28). 08 브랜치(`modeling/ensemble-predict`, PR #49) 위에서 작업했다
  - `uv run python scripts/train_acuity.py --round v2 --unknown-inputs` → 0.5초. `models/acuity/v2/{model.txt,logistic.json,metadata.json}`, `reports/acuity_v2.{json,md}`
  - 결정성: 다시 학습 → `model.txt` sha256 같음 `934ffc0d4528bea87c9f95f8646d97aca8775eda484b54ebeb4404e42cf72cd2`. v0도 다시 학습해 바뀌지 않음을 확인했다(라운드 수 교차검증 겹을 `grouped_folds`로 뺀 뒤에도 같다)
  - `uv run python scripts/evaluate.py --model acuity --round v2` → test 1회, `reports/acuity_v2_test.{json,md}`
  - `uv run python scripts/export_models.py` → 서빙 묶음 `models/{acuity,dept_a,dept_b,ensemble}/v2/`. 진료과·앙상블 파일은 v0·v1과 바이트가 같다. 08의 `v1` 묶음은 그대로 둔다
  - `uv run ruff check . && uv run ruff format --check .` → `All checks passed!`. `uv run pytest` → `173 passed`(기존 167 + `test_acuity.py` 4, `test_determinism.py` 1, `test_predict_contract.py` 최악값 테스트 1개를 결측 테스트 2개로 바꿈)
- 학습
  - train 823행 × 3(원본, `sex_male`·`age_group`·`injury`·`pain_score`를 모두 지운 복사본, 값마다 확률 0.5로 지운 복사본) = 2,469행. 의식 상태는 predict가 모름 → alert로 채우므로 지우지 않았다
  - 라운드 수: 원본 행 단위 층화 5겹 교차검증(같은 행의 복사본은 같은 겹) 조기 종료 → **80**(v0은 86). 하이퍼파라미터는 v0과 같다
  - 임계값: "다 앎"(full)과 "지금 백엔드 입력"(backend: 네 값 결측, 의식 alert) 각각에 v0과 같은 규칙(재현율 ≥ 95% 중 정밀도 최대)을 적용해 작은 쪽. full 0.0717, backend 0.1014 → **0.0717**
- **valid(190건, 실제 응급 37건)**, LightGBM 임계값 규칙. 칸은 분자 / 분모

| 모델·입력 | 응급 재현율 | 응급으로 본 건수 | 정확도 |
|---|---|---|---|
| v0, 다 앎(04) | 36 / 37 | 99 / 190 | 112 / 190 |
| v0 + 최악값 채움, 지금 백엔드 입력(08) | 35 / 37 | **153 / 190** | — |
| **v2, 다 앎** | **36 / 37** | **103 / 190** | 108 / 190 |
| **v2, 지금 백엔드 입력** | **36 / 37** | **115 / 190** | 93 / 190 |

  - 08 대비 지금 백엔드 입력에서 응급으로 보는 건수가 153 → 115로 줄고 재현율은 35 → 36 / 37
  - train+valid 5겹 교차검증(1,013건, 응급 197건): full 재현율 183 / 197, 응급 판정 490 / 1,013. backend 재현율 186 / 197, 응급 판정 548 / 1,013(valid로 정한 임계값이라 valid 행에 낙관적)
- **최종: test 평가(v2, 1회, 254건, 실제 응급 49건)**

| 모델·입력 | 응급 재현율 | 응급으로 본 건수 | 정확도 |
|---|---|---|---|
| 참고: v0, 다 앎(04 최종) | 42 / 49 (85.7%) | 129 / 254 | 140 / 254 |
| **v2, 다 앎 — 최종** | **42 / 49 (85.7%)** | **129 / 254** | 142 / 254 |
| **v2, 지금 백엔드 입력 — 최종** | **40 / 49 (81.6%)** | **129 / 254** | 124 / 254 |

  - **test 재현율이 valid 목표 95%에 못 미친다**(04와 같은 문제). valid 응급이 37건뿐이라 임계값이 valid에 맞춰졌다. 지금 백엔드 입력이면 응급 49건 중 9건을 놓친다
  - v0 + 최악값 채움을 test로 재지는 않았다(v0 라운드의 test 평가는 04에서 이미 했다)
  - 비교용 로지스틱(서빙 안 함): full 45 / 49, 응급 판정 194 / 254. backend 45 / 49, 208 / 254
- `predict` 예시(나이대·성별·손상 여부·통증 점수를 주지 않음, `PYTHONPATH=src`)

| 입력 | 08(v1) | **v2** `acuity` | `acuityProba`(응급/오늘/외래) | `departmentTop2` |
|---|---|---|---|---|
| 배 + 통증·구역·열 | emergency | outpatient | 0.040 / 0.391 / 0.569 | internal, family |
| 손 + 베임·출혈, 손상 있음 | emergency | outpatient | 0.016 / 0.105 / 0.878 | surgery, ortho |
| 치아 + 통증·부기 | emergency | outpatient | 0.015 / 0.067 / 0.918 | dental, internal |
| 치아 + 통증·부기, 30–44세·남성·손상 없음·통증 5 | today | outpatient | 0.022 / 0.257 / 0.721 | dental, internal |

  - 진료과 결과는 08과 같다(진료과 모델·앙상블은 바꾸지 않았다)
- 결정 사항
  - 사용자: 결측을 학습하고 predict는 결측을 넘긴다(08의 최악값 채움을 뺀다), 재현율 목표 95% 유지
  - 서빙 묶음을 v2로 올렸다. 응급도 v2는 학습 라운드 폴더와 서빙 폴더가 같아, export가 학습 `metadata.json`에 서빙 항목을 덧붙인다. 응급도 v2를 다시 학습하면 export도 다시 돌려야 한다(안 하면 `predict`가 `ArtifactError`로 멈춘다)
- 구현 중 사고와 복구: `predict.VERSION`을 v2로 바꾼 뒤 아직 고치지 않은 export를 돌려, `models/acuity/v2/model.txt`가 v0 모델로 덮였다(test 평가는 그 전에 끝났다). 같은 seed로 scratch 폴더에 다시 학습해 `model.txt` sha256이 test 리포트에 적힌 값(`934ffc0d…`)과 같고 `reports/acuity_v2.json`이 바이트까지 같은 것을 확인한 뒤 되돌렸다. 새 export는 학습 폴더와 서빙 폴더가 같으면 모델 파일을 쓰지 않는다
- 남은 문제
  - 지금 백엔드 입력이면 응급 판정이 여전히 valid 60%, test 51%다. 부위·증상만으로는 재현율 95%에 이 정도가 한계다(아래 메모의 사전 탐색). 더 줄이려면 백엔드가 나이대·성별·손상 여부·통증 점수를 받아야 한다(`backend/` 작업)
  - test 재현율 81.6~85.7%로 목표에 못 미친다. 응급 행이 적은 valid로 임계값을 정하는 한계다

## 메모
- 사용자 결정(2026-10-28): 모델이 결측을 배우게 하고 predict는 결측을 그대로 넘긴다. 재현율 목표 95% 유지
- 사전 탐색(train/valid만, `select_threshold`를 각 입력 모양에 따로 적용): 지금 백엔드 입력에서 응급 예측 v0 + 최악값 153 / 190 → v2 115 / 190(재현율 36 / 37). 부위·증상만 쓰는 모델도 119 / 190이라, 입력이 부위·증상뿐이면 재현율 95%에 응급 60% 안팎이 한계다. 더 줄이려면 백엔드가 나이대·성별·손상 여부·통증 점수를 받아야 한다
