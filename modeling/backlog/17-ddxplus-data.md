# 17. DDXPlus 합성 환자 데이터를 버튼 벡터로 옮겨 모델 A 학습 데이터 늘리기

상태: 대기
의존: 02, 05

## 목표
모델 A가 보는 입력은 버튼 벡터(부위 13 × 증상 14)다. 지금 학습 데이터인 Kaggle "Disease Symptom Prediction"은 중복을 지우면 292행이고, 고유 버튼 벡터는 112개뿐이다(backlog 16 목표). 질환 하나에 증상 목록이 한두 개라서 버튼으로 옮기면 같은 벡터로 뭉친다. 그래서 행을 더 모아도 같은 종류의 데이터로는 나아지지 않는다(2026-11-17 사용자와 확인).

DDXPlus는 합성 환자 약 130만 명의 기록이다. 질환 49종에 증상·병력 근거가 223개 있고, 한 환자에 증상이 여러 개 있다. 이 데이터를 버튼 벡터로 옮겨 **입력 조합의 범위를 넓힌다.** 분할·학습은 하지 않는다. 16이 Kaggle과 이 데이터를 합쳐 버튼 벡터 단위로 한 번에 나눈다.

## 범위
- 하는 것
  1. **먼저 확인하고 멈춘다**(사용자에게 결과를 보이고 다음 단계로 간다)
     - figshare 영어판(https://figshare.com/articles/dataset/DDXPlus_Dataset_English_/22687585)의 라이선스 이름·버전. GitHub README(https://github.com/mila-iqia/ddxplus)에는 "CC-BY licence"라고만 적혀 있고, 2026-11-17 조사에서 figshare 페이지는 자동 요청을 막아(403) 직접 확인하지 못했다. CC BY 계열이 아니거나 표시가 없으면 쓰지 않는다(`CLAUDE.md` 데이터)
     - 로그인 없이 받을 수 있는 내려받기 URL, 파일별 크기·sha256, train·validate·test 행 수
     - 질환 49종 목록과 `release_conditions.json`의 `icd10-id`. 외상·손상 질환이 있는지
     - 통증 부위를 묻는 근거(프랑스어판 이름 `douleurxx_endroitducorps`)의 영어판 `E_` 코드와 값(`V_`) 목록
     - 위 내용을 `data/README.md`에 새 절로 적는다. 요약 표에 행을 하나 더한다
  2. **내려받기**: `data/download.py`에 `ddxplus/` 출처를 더한다(영어판, 받은 바이트 그대로, sha256 고정). `tests/test_download.py`가 문서와 해시가 같은지 확인한다
  3. **근거 → 버튼 표** `data/tables/ddxplus_evidence_map.csv`: 증상 근거(병력 `is_antecedent`는 뺀다)와 범주·다중 선택 값마다 `body_parts`·`symptoms`를 적는다. 열은 `symptom_map.csv`와 같고(`evidence, value, body_parts, symptoms, note, source, reviewed`), 버튼에 없는 근거는 `none`이다. LLM 초안이면 `source`에 그렇게 적고 `reviewed=no`
  4. **질환 → KCD 표** `data/tables/ddxplus_condition_kcd.csv`: `icd10-id`를 KCD 3단 코드(영문 1자 + 숫자 2자)로 줄인다. 진료과 비율은 Kaggle 질환과 같은 HIRA 표(05)에서 그 KCD로 찾는다. HIRA에 없는 코드는 건수를 적고 `reviewed=no`로 둔다
  5. **변환** `data/ddxplus.py`와 `scripts/build_ddxplus.py`: 환자마다 근거 → 버튼 벡터, 질환 → KCD를 만든다. 결과는 `data/processed/ddxplus/`(git 제외)에 둔다. 버튼이 하나도 없는 환자는 뺀다. 16과 같이 `(질환, 버튼 벡터)` 기준으로 중복을 지운다. 변환 요약을 리포트로 남긴다
  6. **겹침 보고** `reports/ddxplus_v0.{json,md}`: 아래를 분자·분모로 적는다
     - 원본 환자 수, 버튼이 없어 뺀 수, 중복을 지운 뒤 행 수
     - 고유 버튼 벡터 수, Kaggle 112개와 겹치는 벡터 수
     - 질환이 둘 이상인 벡터 수
     - KCD를 못 찾은 질환 수
     - Kaggle 질환과 같은 KCD 3단 코드를 쓰는 질환 수
     - 부위·증상별 행 수. 외상 증상(`cut`·`bleeding`·`burn`·`cantmove`)과 `chemical`이 얼마나 비는지
- 하지 않는 것
  - train·valid·test 분할, 모델 학습·평가. 16이 합친 데이터로 한 번에 한다. DDXPlus 자체의 train·validate·test 구분은 쓰지 않는다(16이 버튼 벡터 단위로 다시 나눈다)
  - 나이·성별 피처 사용. 모델 A는 쓰지 않는다(README "향후 계획")
  - 질환명을 아티팩트·리포트에 노출. 리포트에는 질환 수·KCD 수만 적는다(`CLAUDE.md` 설계 원칙)
  - 진료과 10종·버튼 열거값 변경, `backend/` 수정

## 입력·출력
- 입력: `data/raw/ddxplus/`(git 제외, 2에서 받는다), `data/tables/`의 HIRA 기반 표(05)
- 출력: `data/tables/ddxplus_evidence_map.csv`, `data/tables/ddxplus_condition_kcd.csv`, `data/processed/ddxplus/`(git 제외), `reports/ddxplus_v0.{json,md}`, `data/README.md`의 새 절과 요약 표 행. 새 모듈 `data/ddxplus.py`와 스크립트는 `CLAUDE.md`·`README.md`의 폴더 표에 함께 적는다

## 완료 기준
- [ ] 1의 확인 결과(라이선스 이름·버전, URL, sha256, 행 수, 질환 목록 확인 여부, 통증 부위 근거 코드)가 `data/README.md`와 `## 결과`에 있고, 사용자가 다음 단계로 가도 된다고 한 날짜가 `## 결과`에 있다
- [ ] `uv run ruff check . && uv run ruff format --check .`, `uv run pytest` 통과. 원본이 없는 환경(CI)에서는 변환 테스트를 건너뛴다(지금 방식)
- [ ] 같은 원본으로 두 번 돌리면 `data/processed/ddxplus/`의 해시가 같다
- [ ] 6의 수치가 모두 분자 / 분모로 리포트에 있다
- [ ] 리포트·표·아티팩트에 질환명이 없다(표에는 근거 코드와 KCD만 있다)
- [ ] 하위 작업 3·4의 표에 `source`·`reviewed` 열이 있고, `reviewed=no` 행 수가 `## 결과`에 있다

## 결과
(구현 후 작성)

## 메모
- 출처: 2026-11-17 데이터 수집 논의. 사용자가 "지금 데이터로는 뭘 해도 아쉽다"고 해서, 16을 하기 전에 데이터를 먼저 모으기로 했다
- **라벨 공간(16에서 정한다)**: 모델 A는 질환 확률에 질환별 진료과 비율을 곱해 진료과 10종 확률을 낸다(`models/dept_a/v2/metadata.json` `output`). 두 출처를 합칠 때 권하는 방법은 이렇다. 질환 라벨은 두 출처의 합집합으로 두고, KCD 3단 코드가 같으면 같은 라벨로 합친다. 진료과 비율은 그 KCD의 HIRA 분포를 쓴다. 이렇게 하면 서빙 구조(`predict.py`, `departments.json`)는 그대로다
- 치우침: DDXPlus는 급성기 진료를 전제로 만들어 호흡기·심장·감염 질환이 많다. 근로자에게 흔한 외상·근골격 증상은 거의 없을 것으로 본다(6에서 확인). 외상 쪽 범위는 이 데이터로 채워지지 않는다. 모델 B의 표(05)와 18의 안내 조합이 맡는다
- 생성 방식: 상용 의료 지식베이스와 규칙 기반 진단 시스템으로 만든 합성 데이터다(GitHub README). 실제 환자 기록이 아니다. 출처와 함께 메타데이터에 적는다
- 크기: 원본 약 130만 행이다. 학습·평가 명령은 로컬에서 몇 분 안에 끝나야 한다(`CLAUDE.md`). 변환은 한 번 하고 `data/processed/`에 저장해 학습은 줄어든 표만 읽게 한다
- 중복 제거 뒤 빈도: `(질환, 버튼 벡터)` 중복을 지우면 "이 벡터에 이 질환이 몇 명이었나"가 사라진다. 한 벡터에 질환이 여럿이면 균등하게 나오게 된다. 빈도를 가중치로 남길지는 16에서 정하고, 6에서 질환이 둘 이상인 벡터 수를 먼저 본다
- 조사 출처(2026-11-17): GitHub README(`icd10-id`, 근거 형식 B/C/M, `E_`·`V_` 코드, 환자 열 `AGE, SEX, PATHOLOGY, EVIDENCES, INITIAL_EVIDENCE, DIFFERENTIAL_DIAGNOSIS`), 논문 https://arxiv.org/abs/2205.09148 (근거 223개 = 이진 208 + 범주 10 + 다중 선택 5)
