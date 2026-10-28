# 02. 외부 데이터 내려받기와 사용 조건 기록

상태: 완료
의존: 01

## 목표
`README.md` 데이터 출처 표의 공개 데이터를 재현 가능하게 내려받고, 라이선스·해시를 기록해 이후 항목이 같은 파일을 쓰게 한다. 사용 조건이 맞지 않는 데이터는 여기서 걸러낸다.

## 범위
- 하는 것
  - 대상 3종: Kaggle Emergency Service – Triage Application(응급도), Kaggle Disease Symptom Prediction(진료과 모델 A), HIRA 보건의료빅데이터개방시스템 질병별 진료과 통계(질환 → 진료과 매핑)
  - 각 데이터의 라이선스 원문을 확인해 학습·평가 사용 가능 여부를 판단한다. 허락하지 않거나 표시가 없으면 **멈추고 사용자에게 묻는다**
  - `data/download.py`: 출처별 내려받기(Kaggle은 `kaggle` CLI 또는 수동 다운로드 후 경로 지정), sha256 계산·검증
  - `scripts/download_data.py`: 내려받기 → 해시 검증 → `data/raw/<출처>/`에 저장
  - `data/README.md`: 파일별 출처 URL, 라이선스, 확인 날짜, sha256, 행 수, 열 목록
  - 식별 정보(이름·연락처·기관명) 열이 있는지 점검하고 있으면 가공 단계에서 지울 열로 표시
- 하지 않는 것
  - 전처리·라벨 변환(03, 05), MIMIC-IV-ED(일정상 제외), 병원 정보 API(백엔드 범위)

## 입력·출력
- 입력: 각 출처의 공개 페이지
- 출력: `data/raw/kaggle_triage/`, `data/raw/kaggle_symptom/`, `data/raw/hira/`(git 제외), `data/README.md`, `scripts/download_data.py`

## 완료 기준
- [x] `uv run python scripts/download_data.py --verify`가 세 출처 모두 해시 일치로 끝남
- [x] `data/README.md`에 세 출처의 URL·라이선스·확인 날짜·sha256·행 수가 있음
- [x] 라이선스가 학습·평가 사용을 허락하는지 출처별로 한 줄씩 판단이 적혀 있음. 비상업 조건이면 그 조건이 적혀 있음
- [x] 식별 정보 열 점검 결과가 적혀 있음(없으면 "없음")

## 결과
- 실행(확인 날짜 2026-10-27)
  - `uv run python scripts/download_data.py --verify` (빈 `data/raw/`) → 7개 `missing`, 종료 코드 1
  - `uv run python scripts/download_data.py` → 3출처 7개 파일 내려받음, 모두 `ok`. 다시 실행하면 `내려받음 0개`
  - `uv run python scripts/download_data.py --verify` → 7개 파일 모두 `ok`, 종료 코드 0
  - 깨지는지 확인: `hira/clinic_specialty_disease_2025.csv` 끝에 한 줄 덧붙임 → `mismatch`, 종료 코드 1. 내려받기 명령을 다시 실행하면 그 파일만 다시 받아 `ok`
  - 수동 경로: `kaggle_symptom/` 파일을 지우고 `--kaggle-zip <수동으로 받은 zip>` → 4개 저장, `ok`
  - `uv run ruff check . && uv run ruff format --check .` → `All checks passed!`, `22 files already formatted`. `uv run pytest` → `21 passed`(기존 12 + `tests/test_download.py` 9)
- 출처·라이선스·해시(자세한 열 설명은 `data/README.md`)

| 출처 | 파일 | sha256 | 행 | 라이선스 → 판단 |
|---|---|---|---|---|
| 응급도: PLOS ONE e0216972 S1 Appendix | `kaggle_triage/pone.0216972.s001.xlsx` | `f631c951…14beb0` | 1,267 | CC BY 4.0 → 학습·평가 가능, 출처 표시 |
| Kaggle Disease Symptom Prediction v2 | `kaggle_symptom/dataset.csv` 외 3개 | `ebbd391c…9c9618` 외 | 4,920 (+133/41/41) | CC BY-SA 4.0 → 학습·평가 가능, 출처 표시, 가공 데이터 배포 시 동일 라이선스 |
| HIRA 병원급이상 진료과목별 상병 통계 2025 | `hira/hospital_department_disease_2025.csv` | `cb3db831…6be00b` | 30,331 | 공공누리 제1유형 → 학습·평가 가능, 출처 표시 |
| HIRA 의원급 표시과목별 상병 통계 2025 | `hira/clinic_specialty_disease_2025.csv` | `50ea3afc…ecefbba2c` | 22,598 | 공공누리 제1유형 → 학습·평가 가능, 출처 표시 |

  - 비상업 조건이 있는 데이터는 없다
  - HIRA 형식·집계 단위(05에서 그대로 씀): CSV, cp949 인코딩, 열 8개(`진료년도`, `진료과목`/`표시과목`, `주상병코드`, `환자수`, `명세서청구건수`, `입내원일수`, `보험자부담금(선별포함)`, `요양급여비용총액(선별포함)`), 진료년도 2025 × 진료과목 × **KCD 3단 주상병코드**(3자, 병원급 1,663종·의원급 1,654종)
- 식별 정보 점검: 세 출처 모두 **없음**. 응급도 데이터의 자유 텍스트 열(`Chief_complain`, `Diagnosis in ED`)에서 이메일·전화번호 형태를 찾았고 상병코드 1건(`S376`)만 나왔다. HIRA는 진료과목·상병 단위 집계로 기관명 열이 없다. 지울 열 없음
- 만든 파일: `src/fornav_modeling/data/download.py`, `scripts/download_data.py`, `tests/test_download.py`, `data/README.md`. 고친 파일: `README.md`(데이터 출처 표 비고), `backlog/03`·`backlog/05`의 `## 메모`
- 결정
  - **응급도 원본은 Kaggle 판이 아니라 PLOS ONE S1 Appendix를 받는다(사용자 결정).** Kaggle 판은 라이선스가 "Other (specified in description)"인데 설명에 라이선스 문구가 없다. 같은 1,267행 × 24열이고 원본 쪽이 `Age`를 반올림하지 않았다. 폴더 이름 `kaggle_triage`는 CLAUDE.md·03과 맞추려고 데이터셋 이름대로 둔다
  - **HIRA는 병원급 이상과 의원급 두 파일을 모두 받는다(사용자 결정).** 서비스가 연결하는 곳이 의원이므로 의원급 표시과목 분포도 필요하다. 합치는 방법은 05에서 정한다
  - HIRA 원래 파일 이름이 한국어·공백이라 영문 이름으로 저장하고, 원래 이름은 `data/README.md`에 적었다
  - 원본은 받은 바이트 그대로 저장한다(cp949 변환 안 함). 해시가 출처 파일과 같아야 다시 받아도 비교할 수 있다
  - 내려받기는 표준 라이브러리 `urllib`만 쓴다. Kaggle은 `kaggle` CLI 대신 API를 직접 부르고(`Authorization: Bearer`, 버전 2 고정), 토큰이 없으면 `--kaggle-zip`으로 수동 zip을 받는다. 새 의존성 없음
  - 받은 파일을 전부 검증한 뒤에 저장한다. 해시가 하나라도 다르면 아무것도 쓰지 않는다
  - `package = false`라 스크립트가 패키지를 찾지 못해, `scripts/download_data.py` 첫머리에서 `src`를 `sys.path`에 넣는다. 이후 스크립트도 같은 두 줄을 쓴다
  - `tests/test_download.py`는 네트워크 없이 돈다(`_fetch`를 바꿔 끼움). 코드의 해시가 `data/README.md`에 모두 있는지도 확인한다
- 남은 문제
  - HIRA 파일은 연 1회 갱신되고(차기 2027-08-14) 그때 URL과 해시가 바뀐다. 2025년 파일이 내려지면 내려받기가 실패하므로 그때 새 파일로 바꾸고 이 표를 고친다
  - data.go.kr과 PLOS 서버가 막히면 자동 내려받기가 안 된다. 그때는 각 페이지에서 받은 파일을 `data/raw/<출처>/`에 위 이름으로 두고 `--verify`로 확인한다

## 메모
- Kaggle 데이터는 로그인이 필요하다. 자동 내려받기가 안 되면 수동 다운로드 경로를 받아 해시만 검증하는 방식도 허용한다
- HIRA 통계는 파일 형식(xlsx/csv)과 집계 단위(질병 소분류 코드)를 결과에 적어 05에서 그대로 쓴다
