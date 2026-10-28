# 03. 응급도 데이터 표준화, 버튼 피처, 분할 고정

상태: 완료
의존: 02

## 목표
Kaggle 응급도 원본을 버튼 피처와 3단계 라벨로 바꾸고, train/valid/test를 id 목록으로 고정한다. 이후 응급도 모델(04)과 발표용 실험(09)이 같은 피처 함수와 같은 분할을 쓴다.

## 범위
- 하는 것
  - `data/kaggle_triage.py`: 원본 → 표준 테이블(행 id 부여, 열 이름 정리, 식별 정보 열 제거)
  - `labels/ktas.py`: KTAS 1–2 → `emergency`, 3 → `today`, 4–5 → `outpatient`. 전문가 KTAS 열을 라벨로 쓰고 간호사 KTAS 열은 비교용으로만 둔다
  - 원본 열 → 버튼 피처 매핑을 확정한다. 주증상(자유 텍스트) → `BodyPart`·`Symptom` 카테고리 매핑 표(`data/tables/chief_complaint_map.csv`, 출처 열 포함), 통증 점수, 의식 상태, 나이대, 성별, 손상 여부. **원본에 없는 피처(발생 시점 등)는 결측으로 두고 그 사실을 결과에 적는다**
  - `features/buttons.py`: `Intake` 형태 dict → 피처 벡터. 학습과 서빙이 같은 함수를 쓴다. 피처 순서를 상수로 고정
  - `features/vitals.py`: 활력징후 피처(09 전용). 서빙 경로에서 import되지 않게 한다
  - `data/split.py`, `scripts/make_splits.py`: 층화(라벨 기준) 분할, seed 고정, `data/splits/triage_{train,valid,test}.txt`(id 목록)와 `data/splits/triage_test.sha256` 커밋. `data/test/`는 재생성
  - 테스트: 피처 함수 결정성, 라벨 변환, 분할 겹침 없음, 학습 명령이 `data/test/`를 열지 않음
- 하지 않는 것
  - 모델 학습(04), 활력징후 모델 실험(09)

## 입력·출력
- 입력: `data/raw/kaggle_triage/`, `schema.py`
- 출력: `data/processed/triage.parquet`(git 제외), `data/tables/chief_complaint_map.csv`, `data/splits/triage_*`, `features/buttons.py`, `features/vitals.py`, `labels/ktas.py`, 테스트 4종

## 완료 기준
- [x] `uv run python scripts/make_splits.py`를 두 번 실행해도 id 목록과 test 해시가 같음
- [x] 라벨 3단계 각 건수(분자·분모)가 전체·train·valid·test별로 결과에 적혀 있음
- [x] 주증상 매핑 표의 커버리지(매핑된 행 수 / 전체 행 수)가 적혀 있고, 매핑 안 된 주증상 상위 20개가 `reports/`에 있음
- [x] 버튼 피처 중 원본에 없는 것과 처리 방법이 적혀 있음
- [x] `tests/test_features.py`, `tests/test_labels.py`, `tests/test_split_isolation.py` 통과
- [x] test 비율은 20%, valid 15% 이내. 바꾸면 이유를 적는다

## 결과
- 실행(2026-10-27)
  - `uv run python scripts/make_splits.py` → 4초 안에 끝남. `data/processed/triage.parquet`, `data/test/triage_test.parquet`, `data/splits/triage_{train,valid,test}.txt`, `data/splits/triage_test.sha256`, `reports/triage_splits.json`, `reports/triage_unmapped_chief_complaints.csv`를 만든다
  - 두 번 실행(두 번째는 processed·test 파일을 지운 뒤) → `data/splits/` 5개 파일과 두 parquet의 sha256이 모두 같음. test 해시 `755e1a5de73b9aa04260f1c1a7d8a6a3f4d678fa8aa0d08250c0c99f16c7c046`
  - 깨지는지 확인: `triage_valid.txt`에 id 한 줄을 덧붙이고 실행 → `SplitError`(커밋된 내용과 다름), 종료 코드 1. 되돌리면 다시 통과
  - `uv run ruff check . && uv run ruff format --check .` → `All checks passed!`, `31 files already formatted`. `uv run pytest` → `67 passed`(기존 21 + `test_features.py` 26, `test_labels.py` 12, `test_split_isolation.py` 8)
- 라벨 건수(`KTAS_expert` 기준, 괄호는 비교용 `KTAS_RN`)

| 분할 | emergency | today | outpatient | 합 |
|---|---|---|---|---|
| 전체 | 246 / 1,267 (232) | 487 / 1,267 (447) | 534 / 1,267 (588) | 1,267 |
| train | 160 / 823 (151) | 316 / 823 (286) | 347 / 823 (386) | 823 (65.0%) |
| valid | 37 / 190 (35) | 73 / 190 (71) | 80 / 190 (84) | 190 (15.0%) |
| test | 49 / 254 (46) | 98 / 254 (90) | 107 / 254 (118) | 254 (20.0%) |

  - 클래스별 최소 건수는 valid의 emergency 37건이다. 층화가 유지돼 세 분할 모두 emergency 비율이 19.3–19.5%다(160/823, 37/190, 49/254)
  - KTAS 1(26건)은 emergency에 합쳐져 따로 층화하지 않았다
- 주증상 매핑(`data/tables/chief_complaint_map.csv`)
  - 정규화(앞뒤 공백 제거·소문자·공백 하나로) 후 고유 주증상 422개 전부를 행으로 둔다. 그중 `BodyPart`나 `Symptom`이 하나라도 붙은 것 328개, 빈 것 94개
  - 커버리지(매핑된 행 / 전체 행): 전체 1,063 / 1,267(83.9%), train 694 / 823(84.3%), valid 158 / 190(83.2%), test 211 / 254(83.1%)
  - 매핑 안 된 주증상 상위 20개: `reports/triage_unmapped_chief_complaints.csv`. 1위부터 `mental change` 22, `general weakness` 21, `syncope` 10, `dysarthria` 10, `post seizure` 7. 의식 변화·경련·실신·전신 쇠약·비뇨기 증상·시술 목적 방문이 대부분이고, 이에 맞는 버튼 어휘가 없다
  - 만든 방법: 키워드 규칙으로 초안을 만들고 422행을 한 줄씩 보며 고쳤다. 출처 열은 `LLM 초안(Claude Opus 5.5): 키워드 규칙 후 행별 수정`, 전부 `reviewed=no`. **사람 검토 전이다**
  - 판단이 들어간 규칙은 `note` 열에 적었다: 어지러움 → `head`, 옆구리(flank) → `back`, 목(neck) → `ent`(한국어 표기 "귀·코·목"), 전신 쇠약 → 비움(`cantmove`와 다름), 호흡곤란 → `chest`, 구토 → `abdomen`, 발열 → `whole`
- 버튼 피처(`features/buttons.py`, 34개, 순서는 `FEATURE_NAMES`로 고정)
  - `body_*` 13개, `symptom_*` 15개: 여러 개 선택 → 0/1. 빈 목록은 모두 0
  - `pain_score` 0–10, `mental` AVPU 0–3, `age_group` 0–3(`under30`, `30to44`, `45to64`, `65plus`), `onset` 0–3(`ONSETS` 순서), `sex_male` 0/1, `injury` 0/1. 모르면 NaN
  - **원본에 없는 피처와 처리**
    - `onset`(발생 시점): 원본에 열이 없어 1,267행 전부 NaN. 이 데이터로 학습한 모델은 발생 시점을 쓰지 못한다. 서빙 때 값이 들어와도 학습에서 본 적 없는 값이라 영향이 없다고 보고 04에서 확인한다
    - `pain_score`: `Pain=0`(통증 없음) 553행은 0점, `Pain=1`인데 `NRS_pain`이 빈 3행은 NaN
    - `age_group`: 원본은 나이(소수 포함)라 구간으로 바꾼다. 구간 경계는 이번에 정했다(앱 화면에 나이대 버튼이 아직 없음)
    - `body_parts`·`symptoms`: 원본은 자유 텍스트라 위 매핑 표로 바꾼다. 매핑 안 된 204행은 둘 다 빈 목록
  - 결측 건수: `onset` 1,267 / 1,267, `pain_score` 3 / 1,267. 나머지는 0
- 활력징후(`features/vitals.py`, 09 전용): `sbp`, `dbp`, `hr`, `rr`, `bt`, `saturation`. 원본 `측불`과 빈칸은 NaN, 그 밖의 숫자가 아닌 값이 나오면 멈춘다. `buttons.py`가 import하지 않는지 테스트한다
- 만든 파일: `src/fornav_modeling/data/kaggle_triage.py`, `src/fornav_modeling/data/split.py`, `src/fornav_modeling/features/buttons.py`, `src/fornav_modeling/features/vitals.py`, `src/fornav_modeling/labels/ktas.py`, `scripts/make_splits.py`, `data/tables/chief_complaint_map.csv`, `data/splits/triage_*`, `reports/triage_splits.json`, `reports/triage_unmapped_chief_complaints.csv`, 테스트 3개. 고친 파일: `pyproject.toml`·`uv.lock`(`openpyxl==3.1.5`, `pyarrow==26.0.0` 추가)
- 결정
  - **`data/processed/triage.parquet`에는 train·valid 행만 넣는다.** test 행은 `data/test/triage_test.parquet`에만 있다. 학습 쪽 코드는 `split.load_dev(..., "train"|"valid")`로 processed만 읽고, `"test"`를 주면 `ValueError`. test는 `split.load_test`가 해시를 확인한 뒤에만 돌려준다(평가 명령 전용)
  - 분할: seed `20261027`, test 20%를 먼저 층화로 떼고, 남은 것에서 전체의 15%(=남은 것의 18.75%)를 valid로 층화해 뗀다. id는 원본 행 순서로 `triage_0001`~`triage_1267`. 원본 해시가 고정이라 id도 고정이다
  - 이미 있는 id 목록·test 해시와 다르게 나오면 덮어쓰지 않고 멈춘다. 바꿔야 하면 사용자와 정한 뒤 `--force`
  - test 해시는 parquet 파일 바이트의 sha256이다. pandas·pyarrow 버전이 바뀌면 같은 내용이어도 해시가 바뀔 수 있다. 그때는 멈춘 원인이 버전임을 확인하고 사용자와 정한 뒤 `--force`로 해시만 새로 쓴다
  - 표준 테이블에서 뺀 열: `Group`, `Patients number per hour`, `Arrival mode`(버튼으로 못 받음), `Diagnosis in ED`, `Disposition`, `Length of stay_min`, `KTAS duration_min`, `Error_group`, `mistriage`(내원 후 결과라 라벨 누출 위험). 식별 정보 열은 원본에 없다(02)
  - "학습 명령이 `data/test/`를 열지 않음"은 두 가지로 확인한다. ① `data/test`의 권한을 0으로 바꾼 채 `load_dev`가 train·valid를 읽는다 ② `src/`·`scripts/`에서 test 데이터에 닿는 이름(`load_test`, `TEST_FILE`, `data/test` 등)을 쓰는 파일이 `split.py`, `make_splits.py`, `scripts/evaluate.py`(04에서 추가)뿐이다. 04의 `train_acuity.py`가 생기면 ②가 바로 검사한다
  - `pyarrow`: pandas가 parquet을 읽고 쓰려면 필요하다
- 남은 문제
  - 매핑 표 사람 검토(`reviewed=no` 422행). 검토로 매핑이 바뀌면 피처가 바뀌므로 04 학습 전에 하는 것이 좋다. 분할은 라벨로만 나눠 매핑이 바뀌어도 그대로다
  - 매핑 표는 test 행의 주증상까지 포함한 422개 전체로 만들었다. 라벨을 보지 않는 어휘 대응이라 그대로 두었지만, 엄밀하게는 test 쪽 텍스트를 본 셈이다

## 메모
- 데이터가 약 1,200건이라 test는 200여 건이다. 응급 클래스가 적으면 층화가 깨질 수 있으니 클래스별 최소 건수를 결과에 적는다
- 주증상 매핑은 사람이 검토해야 한다. LLM으로 초안을 만들었다면 출처 열에 그렇게 적고 검토 전까지 `reviewed=no`로 둔다
- (02에서) 원본은 Kaggle CSV가 아니라 PLOS ONE S1 Appendix `data/raw/kaggle_triage/pone.0216972.s001.xlsx`다. pandas로 xlsx를 읽으려면 `openpyxl`을 의존성에 추가해야 한다(02에서는 추가하지 않음)
- (02에서) 라벨은 `KTAS_expert`, 비교용은 `KTAS_RN`. `Age`는 반올림되지 않은 값(예 67.5)이 있고, 활력징후 열에 `측불`(측정 불가) 문자열, `NRS_pain` 빈칸 556건이 있다. 열 설명은 `data/README.md`
- (03에서) 백엔드 `Intake`에는 통증 점수·의식 상태·나이대·성별·손상 여부 필드가 없다. `featurize`는 같은 dict에 `pain_score`, `mental`, `age_group`, `sex`, `injury` 키로 더 받는다(값은 `features/buttons.py`의 `MENTALS`, `AGE_GROUPS`, `SEXES`). 서빙 연결(08, 백엔드 작업) 때 백엔드 `Intake`에 이 필드를 더할지 사용자와 정해야 한다. 이 작업에서는 `backend/`를 고치지 않았다
  - (2026-10-28) 백엔드 backlog 10에서 `Intake`에 `age_group`·`sex`·`injury`·`pain_score`·`mental` 선택 필드를 더했다. 모델링 `schema.py`에 같은 필드와 열거값(`AgeGroup`, `Sex`, `Mental`)을 옮기고, `features/buttons.py`는 그 열거값을 가져다 쓴다(값·순서는 그대로라 피처와 모델은 바뀌지 않는다)
