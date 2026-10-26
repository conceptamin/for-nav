# 02. 외부 데이터 내려받기와 사용 조건 기록

상태: 대기
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
- [ ] `uv run python scripts/download_data.py --verify`가 세 출처 모두 해시 일치로 끝남
- [ ] `data/README.md`에 세 출처의 URL·라이선스·확인 날짜·sha256·행 수가 있음
- [ ] 라이선스가 학습·평가 사용을 허락하는지 출처별로 한 줄씩 판단이 적혀 있음. 비상업 조건이면 그 조건이 적혀 있음
- [ ] 식별 정보 열 점검 결과가 적혀 있음(없으면 "없음")

## 결과

## 메모
- Kaggle 데이터는 로그인이 필요하다. 자동 내려받기가 안 되면 수동 다운로드 경로를 받아 해시만 검증하는 방식도 허용한다
- HIRA 통계는 파일 형식(xlsx/csv)과 집계 단위(질병 소분류 코드)를 결과에 적어 05에서 그대로 쓴다
