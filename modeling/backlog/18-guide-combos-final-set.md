# 18. 진료과 안내 조합을 늘리고 최종 평가용 조합을 따로 고정하기

상태: 진행 중
의존: 05

## 목표
앱 입력 그대로인 "부위·증상(·손상 여부) → 진료과" 정답은 지금 `department_guide.csv`의 29건뿐이다. 29건 모두 사람이 검토하지 않았고(`reviewed=no`), 앙상블 가중치·폴백 기준값을 고르는 데 이미 썼다(`models/ensemble/v2/metadata.json` `selection_rule`). 그래서 실사용에 가장 가까운 수치(안내 Top-1 17 / 29, leave-one-out Top-2 20 / 29)도 조정에 쓴 셋의 값이다.

다른 출처에서 안내 조합을 더 모은다. 사람이 검토한 뒤 **모델 출력을 보기 전에** 최종 평가용 조합을 떼어 id 목록·해시로 고정한다(Kaggle test와 같은 방식). 기존 29건은 조정용으로 남긴다. 이 일은 backlog 13의 1단계를 앞당긴 것이다.

## 범위
- 하는 것
  1. **출처 고르기와 약관 확인**: 05가 쓴 서울대병원 N의학정보·원주세브란스 **밖의** 공개 안내에서 고른다. 후보는 국가건강정보포털(질병관리청), 다른 대학병원 건강정보, 공공기관 증상별 안내다. 출처마다 이용약관을 확인해 `## 결과`에 적는다. 05처럼 본문은 옮기지 않고 진료과 사실·URL·대조용 짧은 표기만 적는다. 서울아산병원은 05에서 넣지 않기로 했다(사용자 결정). 사전협의를 하지 않았으면 넣지 않는다
  2. **조합 모으기**: `department_guide.csv`와 같은 열(`body_part, symptom, injury, department, alt, url, site, evidence, note, source, reviewed`)에 행을 더한다. 기존 29건과 같은 조합(`same_combo`)은 최종 평가용 후보에서 뺀다. 버튼 조합에 맞지 않는 안내(진단명만 있는 페이지 등)는 넣지 않는다
  3. **사람 검토**: 새 행과 기존 29건을 사람이 읽고 `reviewed=yes|no`를 정한다. 05가 검토가 필요하다고 적은 6건을 포함한다. 검토는 사용자(또는 사용자가 정한 사람)가 하고, Claude는 검토용 목록(조합, 진료과, URL, 근거 표기)을 만든다
  4. **최종 평가용 조합 고정**: 새로 모은 행 중 `reviewed=yes`를 `data/splits/dept_test.txt`(combo_id 목록)와 `dept_test.sha256`으로 고정한다. **이 단계까지 모델 A·B·앙상블의 출력을 새 조합에 대해 보지 않는다.** 고정한 뒤에는 학습·조정·오류 분석에 쓰지 않는다(`CLAUDE.md` 데이터의 test 규칙과 같다). 최종 평가는 16의 test 1회 평가 때 함께 한다
  5. **격리 테스트**: `tests/test_split_isolation.py`에 두 가지를 더한다
     - 모델 B 학습은 `dept_test.txt` 조합과 같은 표 행을 학습에서 뺀다(`same_combo`, 지금 `dept_valid`와 같은 방식)
     - 학습·조정 명령이 `dept_test.txt`를 열지 않는다
- 하지 않는 것
  - 모델 학습·조정·평가(16과 13이 한다)
  - 표(`button_department.csv`, HIRA) 라벨 수정. 13의 3·4단계다
  - LLM이 진료과를 정한 행을 최종 평가용에 넣는 것. 최종 평가용은 공개 안내에서 가져와 사람이 검토한 행만 쓴다
  - 우리 서비스 사용자의 입력을 쓰는 것(`CLAUDE.md` 데이터)

## 입력·출력
- 입력: 공개 안내 페이지(사실과 URL만), `data/tables/department_guide.csv`, `data/splits/dept_valid.txt`
- 출력: 늘어난 `department_guide.csv`, `data/splits/dept_test.txt`·`dept_test.sha256`(새로 만든다), 검토 결과가 반영된 `reviewed` 열, `data/README.md` 출처 절. `labels/department.py`가 `dept_test.txt`를 읽는 함수(평가 명령만 부른다)

## 완료 기준
- [ ] 출처별 이용약관 확인 결과와 URL이 `## 결과`에 있다
- [ ] 안내 조합 수가 출처별·`reviewed`별 분자 / 분모로 적혀 있다(기존 29 포함)
- [ ] 최종 평가용 조합이 **30건 이상**이고, 1순위 진료과별 건수와 `injury=yes` 건수가 적혀 있다. 30건이 안 되면 그 수와 이유를 적고 사용자와 기준을 다시 정한다
- [ ] 최종 평가용 조합과 조정용(`dept_valid.txt`)이 겹치지 않고(`same_combo` 기준 0건), 이를 확인하는 테스트가 있다
- [ ] 고정 날짜와 "고정 전 모델 출력을 보지 않았다"는 확인이 `## 결과`에 있다
- [ ] `uv run ruff check . && uv run ruff format --check .`, `uv run pytest` 통과

## 결과
### 1·2단계: 출처·약관 확인과 조합 모으기(2026-11-17)
- 출처와 이용약관(확인 2026-11-17)
  - 세브란스병원 질환백과(`severance`, https://sev.severance.healthcare/health/encyclopedia/): 페이지 끝 "진료과" 칸에 병원별 진료과가 있다. 회원 약관 제18조(https://member.severance.healthcare/member/policy/agreement.do)는 사전 승낙 없는 **영리목적** 이용과 제3자 이용을 막는다. 05의 서울대병원과 같은 조건이라 진료과 사실·URL·짧은 대조 표기만 비영리 데모 검증용으로 적었다
  - 삼성서울병원 질환백과(`samsung`, https://www.samsunghospital.com/home/healthInfo/): "관련진료과" 칸이 있다. 이용약관 제22조(https://www.samsunghospital.com/home/member/agreement.do)도 사전 승낙 없는 영리목적 이용·제3자 이용을 막는다. 같은 방식으로 적었다
  - 인제대 백병원 질병백과(`paik`, https://www.paik.ac.kr/paik/user/bbs/BMSR00052/): "[진료과]" 칸이 있다. 약관 제12조②는 위와 같지만, **제11조④가 "개인적인 이용 외에 복사, 가공, … 배포 … 제3자에게 제공하는 행위"를 막아 셋 중 가장 엄하다**(https://www.paik.ac.kr/paik/user/bbs/BMSR00072/view.do?menuNo=200153). 저장소가 공개라 "제3자 제공"에 걸릴 수 있어 **사용자 결정으로 넣지 않았다**(2026-11-17). 처음 모은 15건(외상 10건)은 표에서 지웠다
  - 쓰지 않은 출처: 국가건강정보포털은 공공누리 제4유형으로 이용은 되지만 진료과 칸이 없다. 분당서울대·경희·아주대는 진료과 칸이 없다. 서울성모·고려대 안암은 페이지를 JavaScript로 그려 읽지 못했다. 부산대·울산대는 질환백과를 찾지 못했다. 서울아산은 05 결정대로 넣지 않았다
- 모은 조합: `data/tables/department_guide_test.csv`에 **36행**(세브란스 22, 삼성 14). 모두 `reviewed=no`. 백병원 15건을 빼기 전에는 51행이었다. 수집은 Claude가 페이지를 열어 진료과 칸을 확인했고, 그중 3건(뇌진탕·식중독·발목 염좌)은 다시 받아 표기가 같은지 대조했다(발목 염좌는 백병원이라 함께 빠졌다)
  - 1순위 진료과: ortho 8, derm 7, internal 6, ent 5, neuro 4, surgery 3, family 1, ophth 1, dental 1, occ 0(진폐증의 2순위로만 있다)
  - `injury=yes` 7 / 36. 백병원을 빼며 외상 조합이 17건에서 7건으로 줄었다. 외상 조합은 최종 평가에서 얇다
  - 조정용 29건과 같은 조합(`same_combo`) 0건(`check_guide_test_disjoint`)
  - 수집할 때 매핑이 약하다고 표시한 행 5건: `head-pain-yes`(안면골 골절), `arm-pain-yes`(회전근개 파열), `hand-pain-yes`(복합부위통증증후군), `whole-cantmove-yes`(파상풍), `leg-cantmove-no`(척추관협착증). 모두 틀림이어도 31건이다
  - 진료과 칸이 있는 페이지를 찾지 못한 조합: 눈 화학 화상, 손·팔·다리·발 베임, 손가락 골절, 끼임(압궤), 들다가 허리 삠. 세브란스 "상황별 응급처치"(베인 상처·눈 이물질 등)에는 진료과 칸이 없다
- 진료과 대응: 05·HIRA 표와 같다(내과 계열 → internal, 마취통증의학과·재활의학과·척추 신경외과 → ortho, 성형외과·심장혈관외과 → surgery, 구강악안면외과 → dental, 응급의학과·소아청소년과·센터 이름은 건너뛴다). 뇌진탕의 신경외과는 neuro, 척수손상·디스크의 신경외과는 ortho로 봤다
- 구현(3·4단계를 위한 코드, 아직 고정하지 않았다)
  - 최종 평가용 정답은 **조정용과 다른 파일**(`department_guide_test.csv`)에 둔다. `build_tables.py`가 `department_guide.csv`의 모든 행을 `dept_valid.txt`(조정용)로 쓰기 때문에 같은 표에 두면 조정에 섞인다
  - `labels/department.py`: `freeze_guide_test`(검토한 행 → `dept_test.txt`·`dept_test.sha256`, 이미 있으면 멈춤, 조정용과 겹치면 멈춤), `load_guide_test`(해시가 다르면 멈춤, 평가 명령만), `held_test_ids`(id만), `check_guide_test_disjoint`. `scripts/freeze_guide_test.py`
  - 모델 B 학습(`dept_b.split_table`)은 최종 평가용 조합과 같은 표 행을 학습에서도 검증용에서도 뺀다. 학습은 id 목록(`dept_test.txt`)만 읽고 정답 표는 읽지 않는다. 범위 5의 "학습·조정 명령이 `dept_test.txt`를 열지 않는다"는 이렇게 바꿨다: **정답 표(`department_guide_test.csv`)를 여는 코드는 정의·고정 명령·평가 명령뿐이다**(`tests/test_guide_final.py`). 같은 조합을 학습에서 빼려면 id는 읽어야 해서다
  - `uv run ruff check . && uv run ruff format --check .` → 통과, `uv run pytest` → 137 passed(새 테스트 `tests/test_guide_final.py` 8개)
- 3단계(사람 검토): 검토용 목록을 저장소 밖 작업 파일로 만들었다(최종 평가용 36 + 조정용 29). 결과 대기

## 메모
- 출처: 2026-11-17 데이터 수집 논의. 16을 하기 전에 데이터를 먼저 모으기로 했다. 17(DDXPlus)은 버튼 벡터의 범위를 넓히고, 이 항목은 진료과 정답의 수와 신뢰도를 늘린다
- 13과의 관계: 13의 1단계(평가셋 확대)를 이 항목으로 옮겼다. 13의 나머지 단계(교차검증, 외상 라벨 보정, 빈 조합, 여러 개 선택, 모델 정리)는 그대로다
- 16과의 관계: 16의 앙상블 조정 셋은 "안내 조합 중 최종 평가용이 아닌 것 + 새 Kaggle valid"가 된다. 16의 test 1회 평가 때 이 최종 평가용 조합도 함께 평가해 따로 적는다
- 30건 기준: 1순위 진료과 10종이 고르게 들어가기에는 적다. 한 건이 3%p쯤이다. 수치를 적을 때 그대로 분자 / 분모로 둔다
- 외상 조합(`injury=yes`)은 지금 29건 중 6건이다. 근로자에게 흔한 조합이므로 최종 평가용에 일부러 더 찾는다(열상·염좌·골절·화상). 다만 열상·출혈은 HIRA(정형외과)와 백엔드 규칙표(외과)가 다르다(05 메모). 안내 페이지가 말하는 진료과를 그대로 적고 고치지 않는다
