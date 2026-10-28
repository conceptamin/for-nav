# 05. 진료과 매핑 표 구축

상태: 완료
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
- [x] 세 CSV가 `labels/department.py` 검증을 통과(`uv run pytest tests/test_labels.py`)
- [x] `disease_department.csv`: 41종 질환 전부 매핑됨. 질병 코드를 못 찾은 질환은 `reviewed=no`로 표시하고 건수를 적는다
- [x] `symptom_map.csv`: 매핑된 증상 수 / 132가 적혀 있음
- [x] `button_department.csv`: 부위 13 × 증상 전체 조합 중 채운 조합 수 / 전체가 적혀 있고, 외상·산재 조합이 최소 10개 있음
- [x] 백엔드 명확 케이스 규칙과 어긋나는 행이 0개
- [x] 진료과 검증셋의 정의와 건수가 결과에 있음
- [x] 대량 수집한 출처는 이용약관 확인 결과가 적혀 있음

## 결과
- 실행(2026-10-28)
  - `uv run python scripts/build_tables.py` → `disease_department.csv`(168행), `button_department.csv`(566행), `data/splits/dept_valid.txt`(29개)를 쓰고 다시 읽어 검증한다(`symptom_map.csv`도 Kaggle 원본 증상과 같은지 확인). 출력 요약: `diseases 41`, `symptoms_mapped 75 / 131`, `button_combos 129`, `button_pairs_filled 110 / 195`, `clear_case_conflicts []`, `valid_combos 29`
  - `uv run ruff check . && uv run ruff format --check .` → `All checks passed!`. `uv run pytest` → `126 passed`(`tests/test_labels.py` 59개 — 기존 7개 + 진료과 표 52개)
- 만든 파일
  - 코드: `data/hira.py`(HIRA 적재·진료과 대응), `data/kaggle_symptom.py`(질환·증상 이름 정리), `labels/department.py`(표 읽기·검증·만들기, 명확 케이스 대조, 검증셋), `scripts/build_tables.py`
  - 사람이 고치는 입력 표(`data/tables/`): `disease_kcd.csv`(질환 → KCD), `button_kcd.csv`(조합 → KCD 또는 직접 적은 분포), `symptom_map.csv`, `department_guide.csv`(검증셋 정답)
  - 만드는 표: `disease_department.csv`, `button_department.csv` — 손으로 고치지 않고 입력 표를 고친 뒤 `build_tables.py`로 다시 만든다
  - 범위에 적힌 두 표만으로는 "질환·조합 → KCD"를 고칠 자리가 없어 입력 표 두 개(`disease_kcd.csv`, `button_kcd.csv`)를 더했다. 행마다 KCD 선택 이유를 `note`에 적었다
- 결정 사항(사용자와 정함, 2026-10-28)
  - **HIRA 진료과 → `Department` 10종**: 가까운 과로 흡수한다. 신경외과·재활의학과·마취통증의학과 → ortho, 성형외과·심장혈관흉부외과 → surgery, 결핵과 → internal, 치과 12종 → dental, 일반의·보건기관의과 → family. 소아청소년과·산부인과·비뇨의학과·정신건강의학과·응급의학과·영상·검사·한방 등은 버리고 남은 과로 다시 합을 1로 맞춘다. 대응표는 `hira.HIRA_DEPARTMENTS` 한 곳이고, 모르는 과 이름이 나오면 멈춘다
  - **추가로 정한 것(구현 중 발견)**: 신경외과를 일괄 ortho로 두면 뇌내출혈(I61)이 정형외과 77%가 된다. 신경외과 환자 중 뇌·중추신경 코드(I60–I69, S06, G00–G47)는 neuro로 보낸다. 바꾼 뒤 I61은 neuro 65%, S06은 neuro 79%
  - **두 파일 합치기**: 병원급과 의원급의 **환자수**를 그대로 더한다(의원급 가중 없음). 명세서청구건수는 만성질환 재방문이 부풀린다
  - **비율 다듬기**: 1% 미만은 버리고 합을 1로 다시 맞춘 뒤 소수 넷째 자리로 반올림한다. 검증은 합 1 ± 0.001
  - **`button_department.csv` 만드는 법**: 조합 → KCD(LLM 초안) → HIRA 비율. HIRA에 거의 나오지 않는 직업환경의학과가 필요한 화학물질 노출 10개 조합만 `manual` 분포(LLM 초안, occ 0.4가 1순위)로 적었다. 백엔드 규칙표(chemical → occ)에 맞춘 것이다
  - **손상 여부**: `injury`는 `yes`/`no`/`any`. 같은 (부위, 증상)에 `any`와 `yes`/`no`를 섞지 않는다
- `disease_department.csv`: Kaggle 질환 **41 / 41** 매핑. HIRA 통계에서 코드를 못 찾은 질환 **0개**. KCD-8로 바뀐 코드(뎅기열 A97, 치핵 K64)는 새 코드를 썼다. KCD 선택이 LLM 초안이라 41개 모두 `reviewed=no`다. B17·B18처럼 3단에서 여러 간염형이 한 코드에 묶인 경우는 `disease_kcd.csv` `note`에 적었다
- `symptom_map.csv`: 분모는 **131**로 바꿨다. `Symptom-severity.csv` 133행에서 중복 `fluid_overload` 1행과 증상이 아닌 `prognosis`를 빼면 131이고, `dataset.csv`의 공백을 지운 고유 증상도 131로 같다(`kaggle_symptom.symptoms`가 두 파일이 같은지 확인한다). 우리 `Symptom`으로 매핑된 증상 **75 / 131**, `BodyPart`가 하나라도 붙은 증상 **101 / 131**. 나머지 56개는 `symptoms=none`(병력·검사값·피로처럼 버튼에 없는 것). 전부 LLM 초안, `reviewed=no`
- `button_department.csv`: 부위 13 × 증상 15 = 195 중 **110 / 195** (부위, 증상) 쌍을 채웠고, 손상 여부로 나눈 조합은 **129개**(kcd 119, manual 10). `injury=yes` 56개, `no` 24개, `any` 49개. 외상·산재 조합은 `injury=yes` **56개**이고 그중 `note`가 `산재:`로 시작하는 조합(기계 끼임 S67, 연마·용접 이물 T15, 용접 화상 T23, 요추 염좌, 화학물질 노출 등)이 **21개**다. 채우지 않은 85쌍은 말이 안 되거나(치아×화상, 눈×기침 등) 이물감(`foreign`, 눈 전용 증상)과 다른 부위의 조합이다
- 백엔드 명확 케이스 대조: 눈·이물감 → ophth, 치아 → dental 조합 중 표의 1순위가 다른 조합 **0개**. `eye-chemical-any`는 백엔드가 chemical을 먼저 봐 occ를 내므로 명확 케이스에서 뺐다(표는 T26 → ophth 89%). 레드플래그(chemicalEye)라 진료과 추천까지 오지 않는다. 백엔드 규칙 순서가 바뀌면 `test_clear_case_mirrors_backend_rule_order`가 깨진다
- 참고(완료 기준 아님): 백엔드 규칙표 전체와 비교하면 백엔드 1순위가 표 1순위와 같은 조합 87 / 129, 표 상위 2개 안에 드는 조합 95 / 129. 어긋나는 34개 중 18개가 열상·출혈(백엔드 surgery, HIRA는 정형외과가 1순위. 예: 손 열상 S61 정형외과 60%, 외과 12%)이다
- **진료과 검증셋**
  - 정의: 병원 공개 안내 페이지의 "진료과" 항목에서 조합별 정답(1순위, 있으면 2순위)을 가져온 `department_guide.csv`의 조합. `dept_valid.txt`는 그 combo_id 목록이다. 07(모델 B)은 `same_combo`로 이 조합과 같은 표 행을 학습에서 뺀다(손상 여부가 같거나 한쪽이 `any`면 같은 조합). 현재 표 129개 중 28개가 빠진다
  - 건수: **29개**(서울대병원 N의학정보 28, 원주세브란스 직업환경의학과 소개 1). 1순위 진료과: ortho 6, internal 4, ophth 4, neuro 4, family 3, ent 2, derm 2, surgery 2, occ 1, dental 1. 29개 중 `injury=yes` 6개
  - 모두 `reviewed=no`다. 행 수집은 Claude가 페이지를 직접 열어 확인했지만 사람이 검토하지 않았다. 06·07은 Top-2 적중률을 `reviewed` 별로 나눠 적는다
  - 페이지는 진료과를 순서 없이 나열한다. 1순위는 나열 순서에서 처음 매핑되는 과다. 검토가 필요한 행: `chest-chemical-any`(진료과 소개 페이지라 약한 근거), `whole-chemical-any`(납 중독 → family, occ 후보), `skin-cut-yes`(찰과상 페이지), `skin-chemical-any`(일반 접촉 피부염), `skin-burn-no`(일광화상), `ent-pain-yes`(외상성 고막 천공)
  - 참고: 표(HIRA) 자체의 상위 2개가 검증셋 1순위를 맞히는 비율 24 / 28(1순위 일치 19 / 28). 모델이 아니라 라벨 표와 검증셋이 얼마나 일치하는지를 본 값이다. 표에 행이 없는 검증 조합 2개(`ent-pain-yes`, `skin-burn-no`)는 뺐다
- 이용약관 확인(2026-10-28)
  - HIRA: 공공누리 제1유형(02에서 확인, `data/README.md`)
  - 서울대병원(https://www.snuh.org/footer/service.do 제13조): 사전 승낙 없이 복제·배포해 영리목적으로 이용하거나 제3자에게 이용하게 하지 못한다. 본문은 옮기지 않고 진료과 사실과 URL, 대조용 짧은 표기(`evidence`: 페이지 제목 + 진료과 항목 값)만 비영리 데모 검증용으로 적었다
  - 원주세브란스: 이용약관 페이지가 없고 "ALL RIGHTS RESERVED" 표기만 있다. 사실과 URL만 적었다
  - **서울아산병원 질환백과는 넣지 않았다(사용자 결정)**. 의료정보운영방침(https://www.amc.seoul.kr/asan/footer/medicalPolicy.do)이 외부 이용에 사전협의를 요구하고 저장소가 공개라서다. 후보 11개는 아래 메모에 남겼다
- 남은 문제
  - 입력 표 네 개 모두 `reviewed=no`. 사람 검토 전에는 학습 라벨로만 쓰고, 검증셋은 검토 후에 확정한다
  - 열상·출혈 조합에서 HIRA(정형외과)와 백엔드 규칙표(외과)가 다르다. 어느 쪽이 맞는지는 백엔드와 정할 일이라 여기서 고치지 않았다(아래 메모)

## 메모
- 표의 `source` 값 예: `hira:2024`, `snuh-guide`, `llm-draft`. `llm-draft` 행은 사람이 검토해 `reviewed=yes`가 되기 전에는 학습 라벨로만 쓰고 검증에는 쓰지 않는다
- 질환명은 이 표와 모델 A 내부까지만 쓴다. 06 이후 산출물에 질환명이 나가지 않게 한다
- (02에서) HIRA는 2025년 파일 두 건이다: 병원급 이상 진료과목별(`hospital_department_disease_2025.csv`, 진료과목 48종)과 의원급 표시과목별(`clinic_specialty_disease_2025.csv`, 표시과목 26종). 둘 다 cp949 CSV, KCD 3단 주상병코드. 두 파일을 어떻게 합칠지(의원급 가중 등)는 여기서 정한다. `source` 값은 `hira:2025`가 된다
- (02에서) `Symptom-severity.csv`는 133행인데 중복 1행이 있어 고유 증상은 132개이고, 그중 `prognosis`는 증상이 아니다. `dataset.csv`의 고유 증상은 131개이며 `dischromic _patches`처럼 공백이 섞인 표기가 3개 있다. 완료 기준의 분모 132를 쓸지 정리 후 수로 바꿀지 결과에 적는다
- (05에서) 백엔드 `recommend_department`는 열상·출혈을 외과 1순위로 보내지만, HIRA는 팔·손·다리·발 열상(S41·S51·S61·S81·S91)의 1순위가 정형외과다. 백엔드 규칙표를 HIRA에 맞출지는 `backend/` 작업에서 정한다
- (05에서) 서울아산병원 질환백과 검증셋 후보 11개(웹마스터 사전협의 후 `department_guide.csv`에 넣을 수 있음): `chest-breath-no` internal, `ent-fever-no` ent, `hand-cut-yes` surgery(alt ortho, 가나다순 나열이라 순서 불확실), `hand-pain-yes` ortho, `hand-rash-no` derm, `hand-swelling-yes` surgery(alt ortho, 순서 불확실), `head-pain-yes` neuro, `leg-swelling-yes` ortho, `skin-rash-no` derm, `teeth-swelling-no` dental, `whole-dizzy-no` family. URL은 `https://www.amc.seoul.kr/asan/healthinfo/disease/diseaseDetail.do?contentId=` 뒤에 차례로 31811, 32442, 31770, 31566, 32169, 32295, 30520, 33574, 31797, 32464, 32328
- (05에서) 06 모델 A는 Kaggle 증상을 `symptom_map.csv`로 버튼 입력에 옮긴다. `symptoms=none` 증상 56개는 버튼으로 받을 수 없어 서빙 시 피처가 되지 않는다
