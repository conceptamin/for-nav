# 06. 진료과 모델 A(증상 → 질환 → 진료과)

상태: 대기
의존: 05

## 목표
Kaggle 증상 데이터로 질환 확률을 예측하는 LightGBM 다중 분류 모델을 학습하고, `disease_department.csv`로 진료과 확률 분포로 바꾼다. 질환 확률은 내부 산출물이고 바깥으로는 진료과 분포만 나간다.

## 범위
- 하는 것
  - `data/kaggle_symptom.py`: 원본 → 표준 테이블, `symptom_map.csv`로 우리 `Symptom`·`BodyPart` 피처로 변환. 매핑 안 된 증상은 버린다
  - `data/split.py` 확장: 질환 데이터 분할(`data/splits/symptom_*`), test 해시 고정
  - `models/dept_a.py`: 학습(seed 고정), 질환 확률 예측, 질환 확률 × 질환별 진료과 비율 합산 → `Department` 10종 분포. 출력 dict에는 질환명이 없다
  - `evaluate.py` 확장: 진료과 Top-1·Top-2 적중률(분자·분모). 정답은 질환 라벨을 표로 바꾼 1순위 진료과
  - `scripts/train_dept_a.py`, `scripts/evaluate.py --model dept_a`
- 하지 않는 것
  - 외상·산재 조합 보강(모델 B 역할), 앙상블(08)

## 입력·출력
- 입력: `data/raw/kaggle_symptom/`, `data/tables/symptom_map.csv`, `data/tables/disease_department.csv`
- 출력: `models/dept_a/v0/model.txt`, `data/splits/symptom_*`, `reports/dept_a_v0.json`

## 완료 기준
- [ ] 학습 5분 이내, 같은 seed 두 번 → 같은 해시(`tests/test_determinism.py` 확장)
- [ ] 검증셋 Top-1·Top-2 적중률이 분자·분모와 함께 있음
- [ ] 변환 후 피처 수(우리 증상·부위로 매핑된 수)와 버린 증상 수가 적혀 있음
- [ ] 출력 dict의 키가 `Department` 10종만이라는 테스트 통과(질환명 비노출)
- [ ] 테스트셋 평가는 한 번만, "최종" 표시

## 결과

## 메모
- 영어권 데이터라 외상 증상이 부족하다. 외상 조합에서 성능이 낮게 나오면 그대로 적고 앙상블 가중치(08)에서 다룬다
