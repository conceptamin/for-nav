# 16. 질환·증상 데이터를 버튼 벡터 단위로 다시 나누고 모델 A·앙상블을 다시 평가하기(v3)

상태: 대기
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
- [ ] 사용자 승인 날짜가 `## 결과`에 있다
- [ ] `uv run ruff check . && uv run ruff format --check .`, `uv run pytest` 통과. 같은 seed 두 번 → 같은 분할·같은 `model.txt` 해시
- [ ] 세 셋 사이에 겹치는 버튼 벡터가 0개이고, 이를 확인하는 테스트가 있다
- [ ] 셋별 행 수·벡터 수·질환 수, 지운 중복 행 수를 분자·분모로 적는다
- [ ] 모델 A v3의 rounds 수, valid Top-1·Top-2를 v2와 함께 적는다
- [ ] 앙상블 v3의 가중치·폴백 기준값, 조정 셋 결과와 leave-one-out 결과를 적는다
- [ ] 새 test 1회 결과(A·B·앙상블, Top-1·Top-2·폴백 비율)를 분자·분모로 적고, v2 test 수치를 "벡터가 겹친 분할"로 표시해 나란히 둔다
- [ ] `predict` 예시 입력 3건(08과 같은 입력)의 v2·v3 출력을 나란히 적는다
- [ ] `backend/`에서 `MODEL_DIR=../modeling/models`로 실제 `/api/triage`를 한 번 불러 `model` 필드가 나오는 것을 확인한다(백엔드 테스트는 모델을 가짜로 바꾸므로 이 경로를 지켜 주지 않는다)

## 결과
(구현 후 작성)

## 메모
- 출처: 2026-11-16 코드 리뷰. 겹침 확인은 스크래치 스크립트로 했고 저장소는 바뀌지 않았다. 이 확인에서 옛 test에 대해 "train에 있던 벡터 / 없던 벡터"별 모델 A 적중률(Top-1 41 / 42, 15 / 17)을 계산했다. 옛 test는 이미 열어 본 셈이라 새로 나누는 것이 맞다
- (2026-11-16 기준) 새 test는 작다. Kaggle만이면 118행의 20%로 24행 안팎이라 한 건이 4%p쯤이다. 17로 DDXPlus를 합치면 커진다. 수치를 낮게 보이게 하거나 숨기지 않고 그대로 적는다
- 버전: 13이 계획한 `dept_b/v3`·`ensemble/v3`는 이 항목 뒤로 밀려 `v4`가 된다(13 `## 메모`에 적음)
- 이 항목이 병합되면 `docs/` 브랜치로 루트 `README.md`의 모델 표·"진료과 test Top-2 98.3%"와 `docs/architecture/modeling-backend-flow.md`의 수치를 새 값으로 바꾼다
- (2026-11-17, 18에서) 최종 평가용 안내 조합 31건을 고정했다(`dept_test.txt`). 조정용 29건 중 `reviewed=yes`는 23건이다. `models/ensemble.py`의 리포트 문구 `"안내 조합 29건은 모두 reviewed=no"`는 이 항목에서 조정 셋을 바꿀 때 실제 건수로 고친다
