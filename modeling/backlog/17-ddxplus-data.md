# 17. DDXPlus 합성 환자 데이터를 버튼 벡터로 옮겨 모델 A 학습 데이터 늘리기

상태: 완료
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
- [x] 1의 확인 결과(라이선스 이름·버전, URL, sha256, 행 수, 질환 목록 확인 여부, 통증 부위 근거 코드)가 `data/README.md`와 `## 결과`에 있고, 사용자가 다음 단계로 가도 된다고 한 날짜가 `## 결과`에 있다
- [x] `uv run ruff check . && uv run ruff format --check .`, `uv run pytest` 통과. 원본이 없는 환경(CI)에서는 변환 테스트를 건너뛴다(지금 방식)
- [x] 같은 원본으로 두 번 돌리면 `data/processed/ddxplus/`의 해시가 같다
- [x] 6의 수치가 모두 분자 / 분모로 리포트에 있다
- [x] 리포트·표·아티팩트에 질환명이 없다(표에는 근거 코드와 KCD만 있다)
- [x] 하위 작업 3·4의 표에 `source`·`reviewed` 열이 있고, `reviewed=no` 행 수가 `## 결과`에 있다

## 결과
### 1단계 확인(2026-11-17)
- 라이선스: **CC BY 4.0**. figshare 웹 페이지는 자동 요청을 막지만(403) API `GET https://api.figshare.com/v2/articles/22687585`이 `license.name = "CC BY 4.0"`을 돌려준다. 영어판 버전 2, 게시 2026-03-09. 그 밖의 이용 제한 문구는 없다
- 내려받기: 로그인 없이 `https://ndownloader.figshare.com/files/<id>`로 받았다. 파일 5개의 md5가 API `computed_md5`와 모두 같다. 파일 id·크기·sha256은 `data/README.md` "ddxplus" 절에 있다
- 행 수: train 1,025,602 / validate 132,448 / test 134,529, 합계 1,292,579
- 질환 49종 목록·`icd10-id`를 확인했다. KCD 3단 고유 48개이고 **HIRA에 없는 코드는 0 / 48**이다. Kaggle 질환과 같은 KCD를 쓰는 질환은 처음에 5 / 49로 적었으나, Kaggle 쪽 여러 코드 칸을 나누지 않고 비교한 실수였다. 바로 센 값은 **7 / 49**다(A15, B20, I21, J18, J30, J45, K21)
- 외상: 손상 코드 질환은 3 / 49(S22 자발성 늑골 골절, T78 아나필락시스, T61 스콤브로이드 식중독)이고 열상·염좌·화상은 없다. 메모의 예상과 같다. 외상 범위는 18과 13이 맡는다
- 통증 부위 근거: 영어판 `E_55`("Do you feel pain somewhere?", 다중 선택)다. `E_57`(통증이 퍼지는 곳), `E_133`(발진 부위), `E_152`(부기 부위)도 같은 부위 값 165개를 쓴다. 부위 값은 손가락·좌우까지 나뉘어 있어 버튼 부위 13종으로 옮길 수 있다
- HIRA 원본은 `data/README.md`의 sha256과 같은 파일로 대조했다
- 다음 단계(2~6) 진행 승인: 2026-11-17 사용자 확인

### 2~6단계(2026-11-17)
- 실행
  - `uv run python scripts/download_data.py --verify` → 원본 11개 모두 `ok`(ddxplus 5개 포함)
  - `uv run python scripts/build_ddxplus.py` → 약 25초. 두 번 돌려 `data/processed/ddxplus/ddxplus.csv`의 sha256이 같다(`206a96dd…0e828`)
  - `uv run ruff check . && uv run ruff format --check .` → 통과, `uv run pytest` → 144 passed(새 테스트 `tests/test_ddxplus.py` 15개, 원본이 없으면 2개는 건너뛴다)
- 변환(`reports/ddxplus_v0.{json,md}`)
  - 원본 환자 1,292,579명 중 우리 증상이 없어 뺀 환자 15,129 / 1,292,579, 남은 환자 1,277,450 / 1,292,579
  - (질환, 버튼 벡터) 중복을 지운 뒤 **2,372행**, 질환 49 / 49가 남는다
- 버튼 벡터
  - DDXPlus 고유 벡터 **2,067개**(Kaggle 112개). 겹치는 벡터 28 / 2,067, 합치면 2,151개
  - 질환이 둘 이상인 DDXPlus 벡터 178 / 2,067
  - 겹치는 벡터에 든 환자 28,381 / 1,277,450
- 행당 켜진 버튼 수: 부위 평균 DDXPlus 4.73, Kaggle 3.84. 부위 3개 이상인 행이 DDXPlus 2,054 / 2,372, Kaggle 197 / 292. 증상 평균은 2.79와 2.71이다. 앱 사용자는 보통 한두 개를 누르므로 두 데이터 모두 실제 입력보다 버튼이 많다(아래 메모)
- KCD: 3단 코드 48개, HIRA에 없는 코드 0 / 48. Kaggle과 같은 KCD를 쓰는 질환 7 / 49
- 외상: `cut`·`burn`·`chemical`·`foreign` 행 0 / 2,372, `bleeding` 266 / 2,372, `cantmove` 139 / 2,372. 예상대로 열상·화상·화학 노출은 비어 있다
- 매핑 표
  - `ddxplus_evidence_map.csv` 275행 = 근거 행 110(증상 근거 전부) + 부위 값 행 165. 부위 값 행은 근거 넷(`E_55|E_57|E_133|E_152`)이 같이 쓴다. **275 / 275가 `reviewed=no`**(LLM 초안). 부위 값 165개 중 버튼 부위가 없는 값(생식기·항문, "nowhere")은 19개다
  - `ddxplus_condition_kcd.csv` 49행, **49 / 49가 `reviewed=no`**. `icd10-id`를 3단으로 자르기만 했다(폐렴 `j17, j18` → `J17|J18`)
- 만든 파일: `src/fornav_modeling/data/ddxplus.py`, `scripts/build_ddxplus.py`, `data/tables/ddxplus_evidence_map.csv`, `data/tables/ddxplus_condition_kcd.csv`, `reports/ddxplus_v0.{json,md}`, `tests/test_ddxplus.py`. `download.py`에 `ddxplus` 출처, `CLAUDE.md`·`README.md` 폴더 표와 명령 목록
- 결정
  - 범주·다중 선택 근거는 값이 원본 `default_value`(통증 부위 "nowhere", 세기 0 등)면 없는 것으로 본다. 그러지 않으면 통증 세기 0인 환자도 통증이 켜진다
  - 버리는 기준은 Kaggle과 같이 "우리 증상이 하나도 없는 환자"다(문서의 "버튼이 하나도 없는 환자"보다 조금 넓다. 부위만 있고 증상이 없는 입력은 백엔드가 모델까지 보내지 않는다)
  - 질환 라벨은 이름이 아니라 `ddxplus:<icd10-id>`이고, 조건 표도 `icd10-id`를 열쇠로 한다. 표·리포트에 질환명이 없는 것을 테스트로 확인한다(원본이 있을 때)
  - 처리 결과는 CSV로 쓴다(같은 입력이면 같은 바이트). 합친 환자 수를 `patients` 열에 남긴다
  - 부위 값 대응: 입안·입술·목 앞(갑상연골·기관·턱 밑)은 `ent`, 잇몸은 `teeth`, 목 뒤·엉덩이·장골능은 `back`, 겨드랑이는 `arm`, 고관절은 `leg`. 생식기·항문은 버튼 부위가 없어 `none`이다

## 메모
- 출처: 2026-11-17 데이터 수집 논의. 사용자가 "지금 데이터로는 뭘 해도 아쉽다"고 해서, 16을 하기 전에 데이터를 먼저 모으기로 했다
- **라벨 공간(16에서 정한다)**: 모델 A는 질환 확률에 질환별 진료과 비율을 곱해 진료과 10종 확률을 낸다(`models/dept_a/v2/metadata.json` `output`). 두 출처를 합칠 때 권하는 방법은 이렇다. 질환 라벨은 두 출처의 합집합으로 두고, KCD 3단 코드가 같으면 같은 라벨로 합친다. 진료과 비율은 그 KCD의 HIRA 분포를 쓴다. 이렇게 하면 서빙 구조(`predict.py`, `departments.json`)는 그대로다
- 치우침: DDXPlus는 급성기 진료를 전제로 만들어 호흡기·심장·감염 질환이 많다. 근로자에게 흔한 외상·근골격 증상은 거의 없을 것으로 본다(6에서 확인). 외상 쪽 범위는 이 데이터로 채워지지 않는다. 모델 B의 표(05)와 18의 안내 조합이 맡는다
- 생성 방식: 상용 의료 지식베이스와 규칙 기반 진단 시스템으로 만든 합성 데이터다(GitHub README). 실제 환자 기록이 아니다. 출처와 함께 메타데이터에 적는다
- 크기: 원본 약 130만 행이다. 학습·평가 명령은 로컬에서 몇 분 안에 끝나야 한다(`CLAUDE.md`). 변환은 한 번 하고 `data/processed/`에 저장해 학습은 줄어든 표만 읽게 한다
- 중복 제거 뒤 빈도: `(질환, 버튼 벡터)` 중복을 지우면 "이 벡터에 이 질환이 몇 명이었나"가 사라진다. 한 벡터에 질환이 여럿이면 균등하게 나오게 된다. 빈도를 가중치로 남길지는 16에서 정하고, 6에서 질환이 둘 이상인 벡터 수를 먼저 본다
- 조사 출처(2026-11-17): GitHub README(`icd10-id`, 근거 형식 B/C/M, `E_`·`V_` 코드, 환자 열 `AGE, SEX, PATHOLOGY, EVIDENCES, INITIAL_EVIDENCE, DIFFERENTIAL_DIAGNOSIS`), 논문 https://arxiv.org/abs/2205.09148 (근거 223개 = 이진 208 + 범주 10 + 다중 선택 5)
- **16으로 넘기는 것(2026-11-17, 17 결과에서)**
  - 행당 버튼 수: 두 출처 모두 부위가 평균 4개 안팎으로 켜져 있어 사용자 입력(한두 개)과 다르다. 학습 행에서 일부 버튼만 남긴 행을 만들지(13의 5단계 "여러 개 선택"과 반대 방향), 평가를 버튼 수별로 나눠 적을지 정한다
  - 크기 차이: DDXPlus 2,372행 대 Kaggle 292행이다. 합치면 DDXPlus 질환(호흡기·심장·감염) 쪽으로 쏠린다. 출처별 가중치나 출처별 평가를 정한다
  - 질환이 둘 이상인 벡터 178개가 있다. `patients` 열을 가중치로 쓰면 그 벡터의 질환 비율이 살아난다
  - 매핑 표 275 + 49행이 모두 `reviewed=no`다. 16에서 학습에 쓰기 전에 사람이 볼 범위를 정한다(최소한 부위 값 165행)

