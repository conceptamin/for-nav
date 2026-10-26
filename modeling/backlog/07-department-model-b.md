# 07. 진료과 모델 B(버튼 조합 → 진료과 분포, 소프트 라벨 MLP)

상태: 대기
의존: 05

## 목표
`button_department.csv`의 진료과 분포를 소프트 라벨로 학습하는 소형 MLP를 만든다. 표에 없는 버튼 조합에도 분포를 내고, 외상·산재 조합을 직접 다룬다.

## 범위
- 하는 것
  - 구현 방식 결정(아래 메모). 결정은 구현 전에 사용자와 확인
  - `models/dept_b.py`: 입력은 `features/buttons.py` 피처 벡터, 출력은 `Department` 10종 소프트맥스. 손실은 소프트 라벨 교차엔트로피. seed 고정
  - 학습·검증 분리: 표의 행을 `reviewed=yes`인 것만 검증(`data/splits/dept_valid.txt`), 나머지로 학습. 겹치지 않게
  - 가중치를 JSON으로 내보내는 함수(층 크기, 가중치, 편향, 피처 순서, 라벨 순서)
  - `evaluate.py` 확장: 검증 행에서 Top-1·Top-2 적중률, 분포 간 KL
  - `scripts/train_dept_b.py`, `scripts/evaluate.py --model dept_b`
- 하지 않는 것
  - 앙상블·폴백(08)

## 입력·출력
- 입력: `data/tables/button_department.csv`, `features/buttons.py`
- 출력: `models/dept_b/v0/weights.json`, `reports/dept_b_v0.json`

## 완료 기준
- [ ] 학습 1분 이내, 같은 seed 두 번 → 같은 가중치 해시
- [ ] 검증 행 Top-1·Top-2 적중률이 분자·분모와 함께 있음
- [ ] 표에 없는 조합 5개를 넣었을 때 분포 합이 1이고 상위 2개가 상식과 어긋나지 않음(예시를 결과에 적는다)
- [ ] 외상·산재 조합의 적중률을 따로 적음
- [ ] `weights.json`만으로 numpy 추론이 학습 코드와 같은 결과를 냄(테스트)

## 결과

## 메모
- 구현 방식 두 가지. (a) numpy로 2층 MLP를 직접 구현한다. 표가 수백 행이라 충분하고 JSON 내보내기와 결정성이 쉽다. (b) PyTorch를 추가한다. 의존성이 무거워지고 결정성 보장이 번거롭다. 초안 추천은 (a)
- 행이 적어 과적합이 쉽다. 은닉층은 작게(예: 32), 드롭아웃 대신 L2와 조기 종료를 검증 손실로
