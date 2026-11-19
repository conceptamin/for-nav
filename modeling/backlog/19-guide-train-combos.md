# 19. 모델 B 학습용 병원 안내 조합 수집(v5)

상태: 완료
의존: 13, 18

## 목표
모델 B v4는 최종 평가 조합(18)과 같은 표 행을 학습에서 빼며 내과 쪽 조합을 잃었고, 학습 라벨이 HIRA 상병 통계뿐이라 병원 안내와 어긋난다. 이미 약관을 확인한 병원 질환백과(서울대병원·세브란스·삼성서울)에서 **평가 조합과 겹치지 않는** 조합을 더 모아 모델 B의 학습 라벨로 쓰고, 성능을 올려 v5로 기록한다(사용자 지시 2026-11-19 "데이터 더 수집해라"). 그 뒤 앙상블을 버튼 수별 가중치로 바꿔 v6으로 서빙한다(사용자 결정).

## 범위
- 하는 것
  1. 세 병원 질환백과에서 질환 페이지의 진료과 칸을 읽어 버튼 조합(부위 1~2, 증상 1~2, 손상 여부) → 진료과(1순위, 2순위)를 모은다. 05·18과 같이 진료과 사실·URL·대조용 짧은 표기만 적고 본문은 옮기지 않는다
  2. 조정용(`dept_valid.txt`)·최종 평가용(`dept_test.txt`) 조합과 겹치는 행은 뺀다. 여러 개 선택 행은 부위 × 증상의 어느 쌍이라도 평가 조합과 `same_combo`면 뺀다
  3. 모은 행을 모델 B 학습 행으로 더한다(HIRA 표 행과 함께). 라벨은 1순위·2순위 분포
  4. 모델 B v5 학습, 앙상블 v5 조정, test·최종 31건 1회 평가, 서빙 결정
  5. (v5 결과를 보고 사용자 결정) 앙상블 가중치·폴백 기준값을 버튼 수 묶음마다 고르는 v6
- 하지 않는 것
  - 평가용 표(`department_guide.csv`, `department_guide_test.csv`)와 고정 해시 변경
  - 새 출처(약관 미확인 사이트) 추가, `backend/` 수정

## 입력·출력
- 입력: 세 병원 질환백과 페이지, `data/tables/button_department.csv`, `data/splits/{dept_valid,dept_test}.txt`
- 출력: `data/tables/department_guide_train.csv`, `models/dept_b/v5/`, `models/ensemble/{v5,v6}/`, `reports/dept_b_{compare,v5}.*`, `reports/ensemble_{v5,v6}{,_test}.*`, 서빙 `models/*/v6/`

## 완료 기준
- [x] 출처별 수집 행 수, 평가 조합과 겹쳐 뺀 행 수, 1순위 진료과별 건수를 분자·분모로 적음
- [x] 학습 표가 평가 조합과 겹치지 않음을 테스트로 확인
- [x] 모델 B·앙상블을 v4와 같은 조정 셋(안내 29, Kaggle·DDXPlus valid)으로 비교하고 leave-one-out을 적음
- [x] test·최종 31건을 v5에서 한 번만 평가해 v4와 나란히 적음(같은 test를 세 번째 보는 것도 적음)
- [x] `uv run ruff check . && uv run ruff format --check .`, `uv run pytest` 통과. 같은 seed 두 번 → 같은 해시

## 결과
2026-11-19. 브랜치 `modeling/guide-train-combos`.

### 수집(1·2단계)
- 약관은 05·18에서 확인한 그대로다(서울대병원 제13조, 세브란스 회원 약관 제18조, 삼성서울병원 이용약관 제22조: 사전 승낙 없는 영리목적·제3자 이용 금지). 진료과 사실·URL·대조용 짧은 표기만 적었다. 비영리 데모 학습용
- 방법: 병원마다 Claude 하위 에이전트가 질환 페이지를 열어(curl·WebFetch) 진료과 칸을 읽고 버튼 조합을 붙였다. 두 번 돌렸다(1차 237행, 2차 245행). 진료과 대응은 18과 같다(신경외과는 뇌 → neuro, 척추 → ortho, 응급의학과·소아청소년과·센터는 건너뜀)
- 넣지 않은 행: 평가 표(`department_guide*.csv`)에 이미 쓴 페이지 29행(1차 22, 2차 7), 동상을 화상 버튼으로 붙인 행, 세브란스가 "주 호소가 아니라 부 증상"이라고 짚은 7행(말라리아·패혈증·크론병·급성 췌장염·변비·쿠싱·내향성 손발톱). 1·2순위가 같은 진료과로 대응된 6행은 2순위를 비웠다
- **`department_guide_train.csv` 446행**(서울대병원 169, 삼성서울 157, 세브란스 120), 모두 `reviewed=no`. 버튼 키 64개(같은 키의 행은 분포를 평균), 그중 두 개 선택 키 13개
  - 1순위: internal 203, neuro 83, derm 51, ent 41, surgery 32, ortho 26, family 5, dental 5, ophth 0, occ 0 (/ 446)
  - 손상 여부: no 425, yes 15, any 6 (/ 446). 세 병원 질환백과에 골절·염좌·열상 페이지가 거의 없거나 진료과 칸이 없어 외상은 적다
  - 평가 조합과 겹치는 행 0 / 446(부위 × 증상 쌍 기준, `tests/test_guide_final.py`)
- 확인: 세브란스 6 / 6, 삼성서울 4 / 4 페이지를 다시 받아 진료과 칸이 표기와 같음을 봤다. 서울대병원은 제목 5 / 5가 같았고 진료과 이름이 본문에 있음을 봤다(칸만 따로 떼어 읽지는 못했다)

### 모델 B 설정 비교 (`uv run python scripts/compare_dept_b.py …` → `reports/dept_b_compare.{json,md}`)
고르는 규칙(데이터를 보기 전에 정함): 후보마다 B를 학습해 조정 셋에서 앙상블 가중치·기준값을 고르고, leave-one-out 출처 균형 Top-2가 가장 큰 후보. 칸은 Top-1/Top-2, 분모는 안내 29 · Kaggle valid 18 · DDXPlus valid 375

| 후보 | B 단독 안내·Kaggle·DDXPlus | 앙상블 LOO 안내·Kaggle·DDXPlus |
|---|---|---|
| v0(v4와 같음) | 17/23 · 7/10 · 158/203 | 13/22 · 12/14 · 303/364 |
| v0 + 안내 | 21/25 · 13/15 · 190/252 | 21/23 · 14/15 · 221/354 |
| 넓힌 범위·seed 5 + 안내 | 20/25 · 13/16 · 211/321 | 21/25 · 14/15 · 251/356 |
| 넓힌 범위·seed 5 + 합성(평균) | 19/22 · 9/11 · 110/152 | 16/24 · 11/15 · 236/351 |
| **넓힌 범위·seed 5 + 합성 + 안내(선택)** | 21/25 · 12/17 · 164/217 | 9/25 · 13/15 · 334/368 |

- 모은 데이터로 모델 B 단독은 모든 셋에서 좋아졌다(안내 Top-1 17 → 21, Kaggle Top-2 10 → 15~17, DDXPlus Top-2 203 → 217~321)

### 모델 B v5 (`uv run python scripts/train_dept_b.py --round v5 --setting wide_seeds5_pairs_mean_guide`, 24.3초)
- 은닉 32, L2 0.003, 에폭 110, seed 5개 평균. 학습 885행(표 90조합 + 합성 쌍 + 안내 키 64). 같은 seed로 다시 학습 → `weights.json` sha256 `6ee1671e…1dfe` 같음
- 안내 조합 29건: v5 21/29 · 25/29(v4 17/29 · 23/29, 표 상한 20/29 · 25/29, 로지스틱 14/29 · 18/29), 외상·산재 10건 7/10 · 8/10
- 07의 표에 없던 조합: 손 + 베임·출혈(손상 있음) surgery·ortho, 온몸 + 출혈(손상 있음) surgery·internal, 머리·온몸 + 발열·기침 internal·ent

### 앙상블 v5(가중치 하나) — test 1회
- 조정: A 0.6, 폴백 기준 0.2. 조정 셋 Top-2 409 / 422(v4 402 / 422), leave-one-out 408 / 422. 안내 Top-1은 9 / 29로 떨어졌다
- test(`reports/ensemble_v5_test`): 질환·증상 test 435/492 · 474/492(v4 368 · 467), 최종 안내 31건 9/31 · 21/31(v4 14 · 22). B 단독은 최종 31건 18/31 · 25/31(v4 B 17 · 20)
- 진단: 가중치 하나가 질환·증상 valid(버튼 5개 이상이 대부분)에 맞춰 A 쪽으로 가 앱 같은 2개짜리 입력에서 좋은 B를 덮었다. 같은 test·최종 31건을 v3·v4에 이어 세 번째로 봤다

### 앙상블 v6(버튼 수별) — 사용자 결정 후, test 1회
- 규칙(`ensemble.select_by_buttons`): 버튼(부위 + 증상) 2개 이하 / 3~4개 / 5개 이상 묶음마다 출처 균형 (Top-1 + Top-2) 적중 최대. 동점 규칙은 그대로. Top-1을 넣은 것은 v5 조정 셋의 2개 이하 묶음에서 Top-2가 가중치에 거의 무관하고(안내 25~26 / 29) Top-1이 크게 갈리는(9~22 / 29) 것을 **본 뒤** 정했다
- 선택: 2개 이하 A 0.2 · 기준 0.2, 3~4개 A 0.8 · 0.3, 5개 이상 A 0.7 · 0.3. 모델은 A v3, B v5 그대로
- 조정 셋: 385/422 · 409/422(leave-one-out 378 · 406), 안내 22/29 · 25/29(LOO 20 · 23), Kaggle 13/18 · 15/18, DDXPlus 350/375 · 369/375
- test(`uv run python scripts/evaluate.py --model ensemble --round v6`, 같은 test를 네 번째로 봤다)

| 평가셋 | v6 — 최종 | v5 | v4 | v3(참고, 최종 31건은 부풀려짐) |
|---|---|---|---|---|
| 질환·증상 test 492 | **452 · 475** | 435 · 474 | 368 · 467 | 329 · 473 |
| Kaggle test 22 | 17 · 18 | 18 · 19 | 15 · 18 | 16 · 19 |
| DDXPlus test 470 | 435 · 457 | 417 · 455 | 353 · 449 | 313 · 454 |
| 최종 안내 31 | **17 · 26** | 9 · 21 | 14 · 22 | 19 · 23 |
| 최종 안내 외상 3 | 2 · 2 | 0 · 1 | 1 · 2 | 2 · 2 |

(칸은 Top-1 · Top-2. 폴백은 v6 test에서 1 / 492, 최종 31건 0)

### 서빙 (`uv run python scripts/export_models.py`)
- `models/{dept_a,dept_b,ensemble}/v6/`, `predict.VERSION = "v6"`. 모델 A `model.txt` `920b09c4…a2ed3b`(v3 그대로), `dept_b/v6/weights.json` `6ee1671e…1dfe`(= dept_b/v5), `ensemble/v6/ensemble.json` `c91f6a81…1ac4`
- `predict`는 입력의 버튼 수(부위 + 증상)로 `ensemble.json`의 `by_buttons`에서 가중치·기준값을 고른다(`predict.ensemble_rule`). 조정·평가(`ensemble.rule_outcomes`)와 서빙이 같은지 테스트로 확인
- 백엔드: `MODEL_DIR=../modeling/models`로 `POST /api/triage` 200. 손 + 베임(손상 있음) → surgery 0.32 · ortho 0.24(v4는 internal이 1순위), 가슴 + 어지러움 → internal, 머리·온몸 + 발열·기침·구역 → internal · family
- 검사: modeling `uv run ruff check . && uv run ruff format --check .` 통과, `uv run pytest` 171 passed. backend `uv run pytest` 3101 passed

### 남은 문제
- 같은 test·최종 31건을 네 라운드(v3~v6)에서 봤다. 라운드마다 한 번이지만 고르는 쪽이 test에 맞춰질 위험이 쌓인다. 다음 개선은 새 최종 평가 조합을 따로 모아 고정한 뒤 재는 것이 좋다
- 수집 행은 모두 `reviewed=no`이고 외상·정형외과·직업환경의학과가 적다
- v6의 Top-1 기준은 결과를 본 뒤 정했다(위)

## 메모
