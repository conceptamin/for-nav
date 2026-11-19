# 16. 질환·증상 데이터를 버튼 벡터 단위로 다시 나누고 모델 A·앙상블을 다시 평가하기(v3)

상태: 완료
의존: 03, 06, 08, 17, 18

## 목표
질환·증상 데이터의 중복은 `(질환, 원본 증상 집합)` 기준으로 지운다(`src/fornav_modeling/data/kaggle_symptom.py` `standardize`). 그런데 모델 A가 보는 것은 버튼으로 옮긴 벡터(부위·증상)이고, 원본 증상이 달라도 버튼 벡터는 같아질 수 있다. 분할(`data/split.py` `split_ids`)은 행 id로만 하므로 같은 벡터가 train과 test에 함께 들어간다. 2026-11-16 리뷰에서 다시 만들어 보니 292행의 고유 버튼 벡터는 112개였고, test 59행 중 42행이 train에 같은 벡터로 있었다(그중 41행은 질환도 같다). valid는 44행 중 30행이 그렇다. 그래서 `models/dept_a/v2/metadata.json`의 test 수치(Top-1 56 / 59, Top-2 58 / 59)와 루트 `README.md`의 "진료과 test Top-2 98.3%"는 부풀려진 값이다. 버튼 벡터가 셋 사이에 겹치지 않게 다시 나누고, 모델 A와 앙상블을 다시 학습·조정해 새 test에서 한 번만 평가한다.

**데이터를 먼저 모은다(2026-11-17 사용자 결정).** 17(DDXPlus)과 18(안내 조합 확대·최종 평가용 고정)이 끝난 뒤, Kaggle과 DDXPlus를 합친 데이터로 한 번만 나눈다. 지금 데이터로 먼저 나누면 데이터를 더할 때 test를 또 바꿔야 한다.

**시작 전에 사용자 승인이 필요하다.** `CLAUDE.md`(데이터)는 한번 커밋한 test id 목록을 바꾸려면 사용자에게 묻고 이유를 backlog에 남기라고 한다. 승인 날짜를 `## 결과`에 적는다.

## 범위
- 하는 것
  0. **두 출처 합치기**: Kaggle과 17의 DDXPlus 변환 결과를 한 표로 합친다. 질환 라벨을 어떻게 합칠지(17 메모의 권고: 합집합, KCD 3단이 같으면 같은 라벨)와 중복 제거 뒤 빈도를 가중치로 남길지를 시작할 때 사용자와 정한다. 출처 열을 남겨 수치를 출처별로 나눠 적는다
  1. **중복 기준 변경**: `standardize`가 `(질환, 버튼 벡터)` 기준으로 중복을 지운다. 지금 데이터로 292행 → 118행이고, 질환 40개, 벡터 112개다. 벡터 5개는 질환이 둘 이상이다(같은 버튼 입력에 정답이 여럿). 원본 행 수·지운 행 수를 변환 요약에 남긴다
  2. **그룹 분할**: 같은 버튼 벡터의 행은 언제나 같은 셋에 넣는다. `StratifiedGroupKFold(shuffle=True, random_state=SEED)`처럼 그룹을 지키면서 질환 층화를 최대한 맞추는 방식을 쓰고, 비율(test 20%, valid 15%)은 지금과 같다. 행이 한두 개뿐인 질환이 많아 층화가 완전히 맞지 않는다. 셋별 질환 수를 리포트에 적는다
  3. **새 id 목록 고정**: `data/splits/symptom_{train,valid,test}.txt`와 `symptom_test.sha256`을 새로 쓴다. 옛 목록은 `data/splits/v2/`로 옮겨 기록으로 남긴다(옛 수치를 재현할 수 있게)
  4. **모델 A v3**: 새 train으로 학습한다. 교차검증 조기 종료도 train 안에서 벡터 그룹 단위로 나눈다(지금은 train 안에도 같은 벡터가 있어 조기 종료가 새고, 189행에 954 rounds가 나왔다). rounds 수를 v2와 함께 적는다
  5. **앙상블 v3**: 08과 같은 규칙으로 A:B 가중치와 폴백 기준값을 다시 고른다(조정 셋 = 안내 조합 중 18의 최종 평가용이 아닌 것 + 새 valid). 모델 B는 Kaggle 데이터를 쓰지 않으므로 v2 가중치를 그대로 쓴다
  6. **test 한 번 평가**: 새 test(출처별로 나눠 적는다)와 18의 최종 평가용 안내 조합에서 A·B·앙상블을 한 번만 평가한다. 08 표와 같은 형식으로 분자·분모와 함께 적고, v2 수치는 "벡터가 겹친 분할" 표시를 붙여 나란히 둔다
  7. **서빙 묶음 v3**: `models/{dept_a,dept_b,ensemble}/v3/`로 내보내고 `predict.py`의 `VERSION`을 `v3`로 바꾼다. `dept_b/v3`는 v2와 같은 가중치이고 메타데이터에 그렇게 적는다. v2 폴더는 기록으로 남긴다
  8. **누수 방지 테스트**: `tests/test_split_isolation.py`에 "train·valid·test가 같은 버튼 벡터를 공유하지 않는다"를 더한다(원본이 없는 CI에서는 건너뛰는 지금 방식을 따른다)
  9. 지금 아무것도 단언하지 않는 `tests/test_predict_contract.py`의 `test_loading_artifacts_never_unpickles`를 지운다(같은 뜻을 소스 검사 테스트가 이미 지킨다)
- 하지 않는 것
  - 안내 조합 평가셋 변경·분리(backlog 13의 1단계. 아래 메모)
  - 피처·진료과 10종 변경, 모델 B 재학습, `backend/` 수정
  - 루트 `README.md`, `docs/architecture/modeling-backend-flow.md`의 수치 수정. modeling 폴더 밖이라 이 항목이 병합된 뒤 `docs/` 브랜치로 따로 한다(아래 메모)
  - 새 test 결과를 보고 모델·피처를 다시 고치는 것(test는 한 번만 본다)

## 입력·출력
- 입력: `data/raw/`(Kaggle 원본), `data/tables/`, `data/splits/dept_valid.txt`, `models/dept_b/v2/`
- 출력: 새 `data/splits/symptom_*.txt`·`symptom_test.sha256`, `data/splits/v2/`(옛 목록), `models/{dept_a,dept_b,ensemble}/v3/`, `reports/dept_a_v3{,_test}.{json,md}`, `reports/ensemble_v3{,_test}.{json,md}`, `README.md`(modeling)의 서빙 버전·수치. 새 폴더 `data/splits/v2/`는 `CLAUDE.md`·`README.md`의 폴더 표에 함께 적는다

## 완료 기준
- [x] 사용자 승인 날짜가 `## 결과`에 있다
- [x] `uv run ruff check . && uv run ruff format --check .`, `uv run pytest` 통과. 같은 seed 두 번 → 같은 분할·같은 `model.txt` 해시
- [x] 세 셋 사이에 겹치는 버튼 벡터가 0개이고, 이를 확인하는 테스트가 있다
- [x] 셋별 행 수·벡터 수·질환 수, 지운 중복 행 수를 분자·분모로 적는다
- [x] 모델 A v3의 rounds 수, valid Top-1·Top-2를 v2와 함께 적는다
- [x] 앙상블 v3의 가중치·폴백 기준값, 조정 셋 결과와 leave-one-out 결과를 적는다
- [x] 새 test 1회 결과(A·B·앙상블, Top-1·Top-2·폴백 비율)를 분자·분모로 적고, v2 test 수치를 "벡터가 겹친 분할"로 표시해 나란히 둔다
- [x] `predict` 예시 입력 3건(08과 같은 입력)의 v2·v3 출력을 나란히 적는다
- [x] `backend/`에서 `MODEL_DIR=../modeling/models`로 실제 `/api/triage`를 한 번 불러 `model` 필드가 나오는 것을 확인한다(백엔드 테스트는 모델을 가짜로 바꾸므로 이 경로를 지켜 주지 않는다)

## 결과
### 결정(2026-11-19)
- **사용자 승인 2026-11-19**: test id 목록 교체를 승인했다. 옛 목록(`symptom_{train,valid,test}.txt`, `symptom_test.sha256`)은 `data/splits/v2/`로 옮겼다
- 사용자가 정한 것
  - 질환 라벨: 두 출처의 합집합. KCD 3단이 Kaggle 질환과 겹치는 DDXPlus 질환(7개)은 그 Kaggle 라벨로 합치고, 나머지는 `ddxplus:<KCD>` 라벨이다(KCD가 같은 DDXPlus 질환 2쌍도 한 라벨). 라벨 80개 = Kaggle 40 + DDXPlus 40. 진료과 비율은 그 KCD의 HIRA 분포로 `disease_department.csv`에 더했다(`labels/department.ddxplus_labels`)
  - 가중치: 같은 출처·같은 버튼 벡터 안 질환 몫(DDXPlus는 환자 수 비율, Kaggle은 빈도가 없어 균등)을, 출처마다 합이 같게 늘린다(`split.train_weights`, 평균 1)
  - DDXPlus 매핑 표(근거 275 + 질환 49행)는 검토 없이 쓰고 `reviewed=no`를 메타데이터에 적는다(`dept_a/v3` `data.sources`)
- Claude가 정한 것
  - 행당 버튼 수: 학습 행은 바꾸지 않고(줄인 행을 만드는 것은 13의 일), 평가를 버튼 수(부위 + 증상)별로 `2개`, `3~4개`, `5개 이상`으로 나눠 적는다
  - valid 비율: `StratifiedGroupKFold`는 겹 수로 나눠서, test는 5겹 중 하나(20%), valid는 나머지의 5겹 중 하나(전체의 16%)다. 15%에 가장 가까운 정수 겹 수다
  - 모델 A 클래스: `disease_department.csv`의 라벨 80개 전부. 벡터 단위로 나누면 행이 적은 질환이 train에 안 들어갈 수 있다(train에 있는 라벨 77개)
  - **앙상블 선택 규칙을 08과 다르게 했다**: 08은 Top-2 적중 수를 그대로 더했다(안내 29 + Kaggle valid 44). 지금 valid는 DDXPlus 375건이라 그대로 더하면 앱 입력에 가까운 안내 조합 29건이 묻힌다. 출처(안내 조합, Kaggle valid, DDXPlus valid)마다 Top-2 적중률을 같은 비중으로 더한 값으로 고른다(사용자가 고른 출처 균형과 같은 생각). 동점 규칙은 08과 같다
  - 조정 셋의 안내 조합: `dept_valid.txt` 29건 전부(18의 최종 평가용과 겹치는 조합은 0건). 리포트 문구 `"안내 조합 29건은 모두 reviewed=no"`는 실제 건수(`guide_reviewed`: 23 / 29)로 바꿨다

### 데이터·분할
- `uv run python scripts/build_ddxplus.py` → `uv run python scripts/build_tables.py` → `uv run python scripts/make_splits.py`
- Kaggle 중복 기준 변경: (질환, 원본 증상 집합) 304행 → 우리 증상 없는 12행 제외 292행 → (질환, 버튼 벡터) **118행**(합친 행 174 / 292), 벡터 112개, 질환 40개
- DDXPlus: 2,372행 → 라벨을 합친 뒤 같은 (라벨, 벡터)가 된 33행을 환자 수를 더해 합쳐 **2,339행**
- 합친 표 2,457행, 고유 벡터 2,151개(Kaggle 112, DDXPlus 2,067, 공유 28), 질환이 둘 이상인 벡터 195개

| 셋 | 행 | Kaggle | DDXPlus | 벡터 | 질환(라벨 80개 중) |
|---|---|---|---|---|---|
| train | 1,572 / 2,457 | 78 | 1,494 | 1,377 | 77 |
| valid | 393 / 2,457 | 18 | 375 | 344 | 57(train에 없는 라벨 3) |
| test | 492 / 2,457 | 22 | 470 | 430 | 62(train에 없는 라벨 2) |

- 셋 사이 공유 벡터: train–valid 0, train–test 0, valid–test 0(`tests/test_split_isolation.py::test_committed_splits_share_no_button_vector`, 원본이 없으면 건너뛴다)
- 같은 seed로 다시 돌리면 같은 목록이 나온다: `make_splits.py`를 두 번 돌려 커밋 대조(`_check_unchanged`)가 통과했고, 목록·test 해시의 sha256이 같았다

### 모델 A v3
- `uv run python scripts/train_dept_a.py --round v3` → 6초. 같은 seed로 두 번 → `model.txt` sha256 `920b09c4…a2ed3b` 같음
- rounds: **156**(v2 954). 교차검증 겹을 버튼 벡터 단위로 나눴다
- valid(진료과 Top-1 / Top-2)

| 평가셋 | v3 | 기준선(train 질환 빈도, 입력 안 봄) | v2(벡터가 겹친 분할) |
|---|---|---|---|
| valid 전체 | 367/393 · 379/393 | 326/393 · 339/393 | — |
| valid Kaggle | 12/18 · 14/18 | 13/18 · 13/18 | 40/44 · 42/44 |
| valid DDXPlus | 355/375 · 365/375 | 313/375 · 326/375 | — |
| valid 버튼 2개 / 3~4개 / 5개 이상 | 6/9 · 6/9, 35/50 · 43/50, 326/334 · 330/334 | | |
| train+valid 3겹(벡터 그룹) | 1841/1965 · 1912/1965 | | 221/233 · 226/233 |
| 조정용 안내 조합 29 | 3/29 · 10/29 | | 5/29 · 10/29 |

- **읽을 때 주의**: DDXPlus는 정답 진료과의 83%(313 / 375)가 내과라, 입력을 보지 않는 기준선도 Top-1 313/375다. 전체·DDXPlus 수치는 높아 보이지만 기준선과의 차이를 봐야 한다. Kaggle valid는 Top-1이 기준선보다 낮다(12 대 13 / 18)

### 앙상블 v3
- `uv run python scripts/tune_ensemble.py --round v3`(모델 A `dept_a/v3`, 모델 B `dept_b/v0`) → **A 0.4 : B 0.6, 폴백 기준 0.25**(v2: A 0.5, 0.25)
- 조정 셋 결과(Top-1 · Top-2 · 폴백)

| 평가셋 | 선택 | leave-one-out | A 단독 | B 단독 |
|---|---|---|---|---|
| 안내 조합 29 | 16 · 22 · 1 | 16 · 20 · 1 | 3 · 10 · 0 | 18 · 23 · 0 |
| 안내 조합 reviewed=yes 23 | 15 · 19 · 0 | 15 · 18 · 0 | 3 · 8 · 0 | 15 · 20 · 0 |
| 안내 외상 10 | 4 · 6 · 1 | 4 · 5 · 1 | 0 · 3 · 0 | 6 · 7 · 0 |
| Kaggle valid 18 | 10 · 15 · 0 | 10 · 14 · 0 | 12 · 14 · 0 | 6 · 13 · 0 |
| DDXPlus valid 375 | 266 · 362 · 0 | 266 · 362 · 0 | 355 · 365 · 0 | 171 · 253 · 0 |

- v2 조정 셋(안내 29 + Kaggle valid 44, 벡터가 겹친 분할): 선택 65/73 Top-2, leave-one-out 63/73, 안내 조합 22/29(leave-one-out 20/29)
- 선택은 Top-2만 보므로 Top-1이 A 단독보다 많이 낮다(DDXPlus valid 266 대 355 / 375)

### test 1회 평가(2026-11-19)
- `uv run python scripts/evaluate.py --model dept_a --round v3`, `uv run python scripts/evaluate.py --model ensemble --round v3`(18의 최종 평가용 31건을 해시 확인 뒤 함께). 각 한 번만 돌렸다

| 평가셋 | 앙상블 v3 — 최종 | A 단독 | B 단독 |
|---|---|---|---|
| test 전체 492 | 329 · 473 · 0 | 454 · 471 · 0 | 211 · 356 · 0 |
| test Kaggle 22 | 16 · 19 · 0 | 16 · 18 · 0 | 12 · 16 · 0 |
| test DDXPlus 470 | 313 · 454 · 0 | 438 · 453 · 0 | 199 · 340 · 0 |
| test 버튼 2개 18 | 11 · 12 · 0 | 11 · 14 · 0 | 11 · 14 · 0 |
| test 버튼 3~4개 49 | 23 · 44 · 0 | 39 · 44 · 0 | 12 · 21 · 0 |
| test 버튼 5개 이상 425 | 295 · 417 · 0 | 404 · 413 · 0 | 188 · 321 · 0 |
| **최종 평가용 안내 조합 31(18)** | **19 · 23 · 0** | 6 · 15 · 0 | 19 · 24 · 0 |
| 그중 외상 3 | 2 · 2 · 0 | 0 · 0 · 0 | 2 · 2 · 0 |

- v2 test(**벡터가 겹친 분할**, Kaggle 59행): 앙상블 52 · 58 · 0, A 단독 56 · 58, B 단독 27 · 45. 루트 `README.md`의 "진료과 test Top-2 98.3%"는 이 A 단독 값이다
- 읽을 때 주의
  - 앱 입력에 가장 가까운 최종 평가용 안내 조합에서 앙상블 Top-2는 23/31이고 B 단독(24/31)보다 1건 낮다. A 단독은 15/31이다
  - **모델 B 수치는 낙관적이다**: 모델 B(`dept_b/v0` = v2·v3 가중치)는 18 이전에 학습해, 최종 평가용 31 조합 중 26개와 같은 조합의 표 행(`button_department.csv`, HIRA 라벨)으로 학습했다. 정답(안내 페이지)과 라벨 출처는 다르지만 입력은 본 적이 있다. 이 항목은 모델 B를 다시 학습하지 않는다(범위). 18 규칙대로 그 행을 뺀 모델 B는 13에서 만든다
  - test Top-2 전체 473/492는 DDXPlus(내과 위주)가 대부분이라 앱 사용 장면의 성능으로 읽지 않는다. 버튼 2개 행은 18건뿐이다
  - test에서 버튼 2개 행은 앙상블 Top-2(12/18)가 A·B 단독(14/18)보다 낮다

### 서빙 묶음 v3
- `uv run python scripts/export_models.py` → `models/{dept_a,dept_b,ensemble}/v3/`, `predict.VERSION = "v3"`. `dept_b/v3`는 v2와 같은 가중치(`weights.json` sha256 `fd6930ea…`)이고 메타데이터 `same_weights_as`에 적었다. 모델 B의 최종 수치는 앙상블 test의 "B 단독"에서 옮겼다(옛 `dept_b_v0_test`는 옛 분할 값). v2 폴더는 남겼다
- `predict` 예시(08과 같은 입력, `departmentTop2`와 두 확률, 폴백 없음)

| 입력 | v2 | v3 |
|---|---|---|
| 배 + 통증·구역·열 | internal 0.767, family 0.181 | internal 0.761, family 0.196 |
| 손 + 베임·출혈, 손상 있음 | surgery 0.448, ortho 0.321 | **ortho 0.378, internal 0.334** |
| 치아 + 통증·부기 | dental 0.424, internal 0.314 | dental 0.509, internal 0.381 |

  - 손 열상의 2순위가 내과로 바뀌었다. A 가중치가 0.4로 줄었지만 모델 A가 내과 위주인 DDXPlus로 학습해 외상 입력에도 내과 확률을 크게 낸다
- 백엔드 확인: `cd backend && MODEL_DIR=../modeling/models uv run python …`(`TestClient(app)`을 lifespan과 함께 열어 실제 앱으로 호출) → `POST /api/triage`(배 + 통증·구역·열) 200, `model.departmentProba`가 나오고 `department`는 internal / family, `predict.VERSION` v3

### 코드·테스트
- `data/kaggle_symptom.py`(벡터 기준 중복 제거), `data/split.py`(두 출처 합치기 `combine_sources`, 그룹 분할, `train_weights`, 리포트), `labels/department.py`(`ddxplus_labels`, `build_tables`가 DDXPlus 라벨도 쓴다), `models/dept_a.py`(가중치, 그룹 겹, 출처·버튼 수별 평가, 출처별 기준선), `models/ensemble.py`(행렬 계산, 출처 균형 선택, 최종 평가용 조합 평가), `export.py`, `predict.py`, `scripts/evaluate.py`
- 테스트: 그룹 분할·출처 합치기·가중치·커밋 분할의 벡터 비공유(`test_split_isolation.py`), 라벨 합치기(`test_labels.py`), 앙상블 계산이 서빙 `top2`와 같은지·출처 균형 점수·동점 규칙(`test_ensemble.py` 새 파일), 벡터 중복 제거(`test_dept_a.py`). 아무것도 단언하지 않던 `test_loading_artifacts_never_unpickles`를 지웠다. `test_tampered_artifact_is_refused`는 고른 가중치 값에 기대지 않게 고쳤다
- `uv run ruff check . && uv run ruff format --check .` → 통과, `uv run pytest` → 160 passed

### 남은 것
- 이 항목이 병합되면 `docs/` 브랜치로 루트 `README.md`의 "진료과 test Top-2 98.3%"와 `docs/architecture/modeling-backend-flow.md`의 수치를 바꾼다(메모)
- 모델 B를 18 규칙대로 다시 학습하고(최종 평가용 조합 행 제외), 외상 입력에서 모델 A의 내과 쏠림을 줄이는 일은 13에서 한다
- DDXPlus 매핑 표 검토(`reviewed=no` 324행)는 하지 않았다

## 메모
- 출처: 2026-11-16 코드 리뷰. 겹침 확인은 스크래치 스크립트로 했고 저장소는 바뀌지 않았다. 이 확인에서 옛 test에 대해 "train에 있던 벡터 / 없던 벡터"별 모델 A 적중률(Top-1 41 / 42, 15 / 17)을 계산했다. 옛 test는 이미 열어 본 셈이라 새로 나누는 것이 맞다
- (2026-11-16 기준) 새 test는 작다. Kaggle만이면 118행의 20%로 24행 안팎이라 한 건이 4%p쯤이다. 17로 DDXPlus를 합치면 커진다. 수치를 낮게 보이게 하거나 숨기지 않고 그대로 적는다
- 버전: 13이 계획한 `dept_b/v3`·`ensemble/v3`는 이 항목 뒤로 밀려 `v4`가 된다(13 `## 메모`에 적음)
- 이 항목이 병합되면 `docs/` 브랜치로 루트 `README.md`의 모델 표·"진료과 test Top-2 98.3%"와 `docs/architecture/modeling-backend-flow.md`의 수치를 새 값으로 바꾼다
- 17 결과(2026-11-17): DDXPlus 2,372행·고유 벡터 2,067개가 생겼다. 합칠 때 정할 것(행당 버튼 수, 출처 크기 차이, `patients` 가중치, 매핑 표 검토 범위)은 17 `## 메모` 끝에 적었다
- (2026-11-17, 18에서) 최종 평가용 안내 조합 31건을 고정했다(`dept_test.txt`). 조정용 29건 중 `reviewed=yes`는 23건이다. `models/ensemble.py`의 리포트 문구 `"안내 조합 29건은 모두 reviewed=no"`는 이 항목에서 조정 셋을 바꿀 때 실제 건수로 고친다
