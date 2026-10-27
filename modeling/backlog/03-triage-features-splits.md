# 03. 응급도 데이터 표준화, 버튼 피처, 분할 고정

상태: 대기
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
- [ ] `uv run python scripts/make_splits.py`를 두 번 실행해도 id 목록과 test 해시가 같음
- [ ] 라벨 3단계 각 건수(분자·분모)가 전체·train·valid·test별로 결과에 적혀 있음
- [ ] 주증상 매핑 표의 커버리지(매핑된 행 수 / 전체 행 수)가 적혀 있고, 매핑 안 된 주증상 상위 20개가 `reports/`에 있음
- [ ] 버튼 피처 중 원본에 없는 것과 처리 방법이 적혀 있음
- [ ] `tests/test_features.py`, `tests/test_labels.py`, `tests/test_split_isolation.py` 통과
- [ ] test 비율은 20%, valid 15% 이내. 바꾸면 이유를 적는다

## 결과

## 메모
- 데이터가 약 1,200건이라 test는 200여 건이다. 응급 클래스가 적으면 층화가 깨질 수 있으니 클래스별 최소 건수를 결과에 적는다
- 주증상 매핑은 사람이 검토해야 한다. LLM으로 초안을 만들었다면 출처 열에 그렇게 적고 검토 전까지 `reviewed=no`로 둔다
- (02에서) 원본은 Kaggle CSV가 아니라 PLOS ONE S1 Appendix `data/raw/kaggle_triage/pone.0216972.s001.xlsx`다. pandas로 xlsx를 읽으려면 `openpyxl`을 의존성에 추가해야 한다(02에서는 추가하지 않음)
- (02에서) 라벨은 `KTAS_expert`, 비교용은 `KTAS_RN`. `Age`는 반올림되지 않은 값(예 67.5)이 있고, 활력징후 열에 `측불`(측정 불가) 문자열, `NRS_pain` 빈칸 556건이 있다. 열 설명은 `data/README.md`
