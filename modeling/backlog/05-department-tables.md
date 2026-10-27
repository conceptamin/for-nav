# 05. 진료과 매핑 표 구축

상태: 대기
의존: 02

## 목표
진료과 모델 A·B가 공유하는 두 표를 만든다. 질환 → 진료과 비율(HIRA 통계)과 버튼 조합 → 진료과 분포(모델 B 라벨)다. 두 표는 사람이 검토하는 CSV로 두고 행마다 출처를 남긴다.

## 범위
- 하는 것
  - `data/hira.py`: HIRA 통계 적재, 질병 코드별 진료과 방문 비율 계산
  - `data/tables/disease_department.csv`: Kaggle 질환 41종 → 질병 코드(KCD) → `Department` 10종 비율. 열: `disease, kcd, department, ratio, source, reviewed`
  - `data/tables/symptom_map.csv`: Kaggle 증상 132종 → 우리 `Symptom`·`BodyPart`. 매핑 안 되는 증상은 `none`으로 두고 건수를 적는다
  - `data/tables/button_department.csv`: 버튼 조합(부위 × 증상, 필요시 손상 여부) → 진료과 분포. 1차 출처는 HIRA 통계와 대학병원 증상별 진료과 안내, 국가건강정보포털. 열: `body_part, symptom, injury, department, prob, source, reviewed`
  - 외상·산업재해 조합(기계 끼임, 화상, 화학물질 노출 등)을 표에 직접 포함한다
  - `labels/department.py`: 두 표를 읽어 검증(비율 합 1, `Department` 열거값만, 중복 없음)
  - 백엔드 명확 케이스 규칙(치아 → 치과, 눈 → 안과)과 표가 어긋나지 않는지 확인
  - 진료과 검증셋 정의: Top-2 적중률을 셀 "정답"을 어디서 가져올지 정한다(초안: 대학병원 안내에서 만든 조합 중 사람이 검토한 행을 검증용으로 분리)
- 하지 않는 것
  - 모델 학습(06, 07), HIRA API 자동 호출(공개 파일로 충분)

## 입력·출력
- 입력: `data/raw/hira/`, `data/raw/kaggle_symptom/`, `backend/app/rules/triage.py`(규칙표 대조용, 읽기만)
- 출력: 위 CSV 3종, `labels/department.py`, `data/splits/dept_valid.txt`(검증용 조합 id), `tests/test_labels.py` 확장

## 완료 기준
- [ ] 세 CSV가 `labels/department.py` 검증을 통과(`uv run pytest tests/test_labels.py`)
- [ ] `disease_department.csv`: 41종 질환 전부 매핑됨. 질병 코드를 못 찾은 질환은 `reviewed=no`로 표시하고 건수를 적는다
- [ ] `symptom_map.csv`: 매핑된 증상 수 / 132가 적혀 있음
- [ ] `button_department.csv`: 부위 13 × 증상 전체 조합 중 채운 조합 수 / 전체가 적혀 있고, 외상·산재 조합이 최소 10개 있음
- [ ] 백엔드 명확 케이스 규칙과 어긋나는 행이 0개
- [ ] 진료과 검증셋의 정의와 건수가 결과에 있음
- [ ] 대량 수집한 출처는 이용약관 확인 결과가 적혀 있음

## 결과

## 메모
- 표의 `source` 값 예: `hira:2024`, `snuh-guide`, `llm-draft`. `llm-draft` 행은 사람이 검토해 `reviewed=yes`가 되기 전에는 학습 라벨로만 쓰고 검증에는 쓰지 않는다
- 질환명은 이 표와 모델 A 내부까지만 쓴다. 06 이후 산출물에 질환명이 나가지 않게 한다
- (02에서) HIRA는 2025년 파일 두 건이다: 병원급 이상 진료과목별(`hospital_department_disease_2025.csv`, 진료과목 48종)과 의원급 표시과목별(`clinic_specialty_disease_2025.csv`, 표시과목 26종). 둘 다 cp949 CSV, KCD 3단 주상병코드. 두 파일을 어떻게 합칠지(의원급 가중 등)는 여기서 정한다. `source` 값은 `hira:2025`가 된다
- (02에서) `Symptom-severity.csv`는 133행인데 중복 1행이 있어 고유 증상은 132개이고, 그중 `prognosis`는 증상이 아니다. `dataset.csv`의 고유 증상은 131개이며 `dischromic _patches`처럼 공백이 섞인 표기가 3개 있다. 완료 기준의 분모 132를 쓸지 정리 후 수로 바꿀지 결과에 적는다
