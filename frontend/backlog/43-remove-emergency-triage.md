# 43. 앱이 응급 여부를 판정하지 않게 하기

상태: 완료
의존: 없음(backend 26과 한 PR로 낸다. 메모)

## 목표
앱은 증상 입력으로 응급 여부를 판정하고(키워드 규칙 OR 보조 점수, 서버는 모델이 있으면 응급도 모델), 응급이면 S-06 `/emergency`로 보내 "응급 상황일 수 있습니다"를 띄운다. 판정이 맞지 않으면 사람에게 헛된 확신을 준다. 응급이라고 하면 놀라게 하고, 응급 화면이 뜨지 않으면 괜찮다고 믿게 한다(사용자와 정함, 2026-10-31). 앱은 응급 여부를 판단하지 않고 진료과·제도 경로·접수 문장만 안내한다. 판정과 관계없이 늘 보이는 119 안내(하단 독의 119 버튼, "심해지면 119" 문구, 결과 화면의 응급실 지도 검색)는 남긴다.

## 범위
- 하는 것
  - `domain/triage.ts`
    - 응급 규칙(`EMERGENCY_KEYWORDS*`, `HEAD_INJURY*`, `VOMIT*`, `SEVERITY*`, `ruleReasons`, `modelScore`, `MODEL_THRESHOLD`), `EmergencyReason`, `REASON_KO`를 뺀다
    - `TriageResult`에서 `emergency`·`reasons`·`byRule`·`byModel`·`modelScore`를 빼 `{ department, missing }`(+ 서버 선택 필드 `model`)만 남긴다
    - 응급도 모델 입력(`ageGroup`·`sex`·`painScore`·`mental`)과 `ageGroupFromBirthDate`·`profileAnswers`를 뺀다. `injury`는 진료과 모델 B 입력이라 남긴다
  - `pages/worker/Intake.tsx`
    - `EmergencyPage`, `checkEmergency`와 단계마다 부르던 응급 선별, `ResultPage`의 `/emergency` 리다이렉트를 뺀다
    - 추가 질문에서 `pain`·`ageGroup`·`sex`를 뺀다(`MORE_QUESTIONS`, 건너뛰기 판단, 프로필로 채우던 부분)
  - `main.tsx`: `/emergency` 경로(S-06). `app-front/src/main.tsx`도 같은 경로를 뺀다
  - `pages/worker/Visit.tsx`: `tri.emergency` 리다이렉트
  - `api/worker.ts`: `screenEmergency`, `checkTriage`의 "응급이면 서버를 기다리지 않음" 분기와 `emergency` 필드 검사(`department`만 본다), 응급 판정 시간 제한 문구
  - `state/AppState.tsx`: `emergencySeen`과 그 저장. `components/CenterSheet.tsx`: `emergencyFlag` 전송
  - `components/WorkerLayout.tsx`: `/emergency` 예외(스크롤 등장·센터 시트·119 독 숨김)만 뺀다. 119 독은 그대로다. `components/reveal.ts` 주석
  - `components/common.tsx`: `PainRange`
  - 센터
    - `domain/centerCase.ts`: `CenterCase`·요청의 `emergencyFlag`, `rateUrgency`의 응급 +3. 남는 규칙은 업무 중 +2, 보험증 없음 +1, 3 이상 높음·1 이상 보통이다
    - `domain/templates.ts`: 센터 요약의 "응급 판정 이력" 줄
    - `pages/center/Center.tsx`: 상세의 "응급 판정 이력" 칸
    - `state/centerStore.ts`: 옛 저장 사례의 `emergencyFlag`는 읽을 때 버린다
    - `data/mock.ts`
  - 문구
    - `i18n/*.ts` 20개 언어: `emTitle`·`emBody`·`emReasons`·`emShowKo`·`emLocationHint`·`emInterpret`·`emRuleNote`·`call119`·`painQ`·`ageGroupQ`. `bar119`·`worse119`·`mapEr`·`sex`(가입 화면)는 남긴다
    - `domain/lang/*.ts`·`types.ts`: `emergency` 묶음, `terms.ageGroups`
    - `domain/vocab.ts`: `AGE_GROUPS`·`Mental`과 관련 타입
  - `styles.css`: 응급 히어로(`.em-*`) 규칙. 119 독 규칙은 남긴다
  - `scripts/dump-fixtures.ts`: 응급 판정 입력·출력과 `rateUrgency`의 `emergencyFlag`. `parity.json`, `dump-lang-packs`로 `backend/app/lang/packs.json`을 다시 만든다
  - `README.md`: 첫 줄 소개, 화면 표(S-06), "비동기 UX 규칙"의 응급 항목, 상태의 경계(응급 이력), 백엔드 대응 표의 응급 감지·`TriageResult.model`
  - `CLAUDE.md`: "응급 판정은 늦어지면 안 된다"를 "119 안내와 하단 119 버튼은 네트워크·로딩 상태와 관계없이 보인다"만 남기고, 추출 대체의 이유(응급 판정 지연)를 고친다. "모델 결과는 응급도와 진료과까지만"을 "진료과까지만"으로, 완료 기준 예시의 `/emergency`, reveal 예외의 "응급 화면", `modeling` 메모 예시(응급도 3단계 표시, SHAP 표시)를 고친다
- 하지 않는 것
  - 하단 119 독, `Worse119`, 응급실 지도 검색, Flutter 오프라인 화면의 119 버튼. 판정 없는 고정 안내라 남긴다
  - `backend/` 코드(backend 26), `modeling/`(modeling 15)

## 화면·파일
- 화면: S-05 `/intake`(질문 3개 줄어듦), S-06 `/emergency`(삭제), S-07 `/result`, C-01·C-02 `/center`
- 수정: 위 목록, `backend/tests/fixtures/parity.json`·`backend/app/lang/packs.json`(재생성)
- API: `POST /api/triage` 응답에서 `emergency`·`reasons`·`byRule`·`byModel`·`modelScore`가 빠진다. `Intake`에서 `ageGroup`·`sex`·`painScore`·`mental`이 빠진다. `POST /api/center/cases` 요청과 `CenterCase` 응답에서 `emergencyFlag`가 빠진다

## 완료 기준
- [x] `npm run build` 통과
- [x] 360px에서 "숨을 못 쉬어요", "가슴이 아파요"를 입력해도 `/emergency`로 가지 않고 `/result`에 진료과가 나온다. 하단 119 독은 모든 근로자 화면에 그대로 있다
- [x] `/emergency`를 직접 열면 없는 경로 처리(홈으로)가 된다
- [x] 추가 질문에 통증·나이대·성별이 없고, 손상 여부는 있다
- [x] 단독 모드 센터 화면이 열리고, 옛 꼴 사례(`emergencyFlag` 있음)를 localStorage에 넣어도 목록·상세가 열린다
- [x] `parity.json` 재생성 → 응급 항목이 빠지고 `generatedAt`이 바뀐다. `packs.json`은 `emergency`·`ageGroups`만 빠진다
- [x] 원어민 검수: 빠지는 키만 있고 새 문구 키는 없다

## 결과
- 검사
  - `cd frontend && npm run build` → 통과. `cd app-front && npm run build` → 통과(공유 import하는 `EmergencyPage`를 `app-front/src/main.tsx`에서도 뺐다)
  - `npx rolldown scripts/dump-fixtures.ts … && TZ=Asia/Seoul node … > ../backend/tests/fixtures/parity.json` → 재생성. `triage` 439 → 205건(응급 예문·머리 부상·보조 점수 경계 입력을 뺐다), `urgency` 32 → 16건(응급 이력 축이 빠졌다), `center` 400건·`mockCases` 24건은 내용만 바뀌었다(요약의 "응급 판정 이력" 줄, mock 난수 하나가 빠져 순서가 밀림)
  - `dump-lang-packs` → `backend/app/lang/packs.json` 재생성. origin/main과 비교해 19개 언어 모두 `emergency`와 `terms.ageGroups`만 빠졌다
  - backend `uv run pytest` → 2836 통과(backend 26과 같은 PR)
- 브라우저(Playwright 헤드리스 Chromium, 360×780, 저장소를 채워 온보딩을 건너뜀)
  - 단독 모드 ko·en·vi: `/intake`에서 가슴 + 통증 + "숨을 못 쉬겠어요, 가슴이 아파요"(언어별 같은 뜻) → 추가 질문 5개(발생 시점·손상 여부·업무 중·업종·구군) → `/result` 내과·가정의학과. 하단 119 독 있음. `/emergency` 직접 열기 → `/`
  - API 모드 ko(`MODEL_DIR=../modeling/models`로 띄운 서버): 배 + 통증 → `/result` 가정의학과(서버 모델 결과). 같은 서버에 `emergencyFlag` 없는 `POST /api/center/cases` → 201, 업무 중 + 보험증 없음 → 긴급도 높음
  - 1280px `/center`: 옛 꼴 사례(`emergencyFlag: true`)를 localStorage에 넣어도 목록·상세(`/center/cases/C-99999`)가 열리고, 상세에 "응급 판정 이력" 칸이 없다
- 바뀐 화면·경로: S-06 `/emergency` 삭제. S-05 추가 질문 9 → 6개(통증 점수·나이대·성별 삭제, 업무 종류는 "예"일 때만이라 보통 5개). C-02 상세에서 "응급 판정 이력" 칸 삭제
- 결정
  - 옛 저장 사례·세션의 `emergencyFlag`·`emergency` 같은 남은 키는 따로 지우지 않는다. 읽는 코드가 없어 화면에 영향이 없다
  - 결과 화면의 응급실 지도 검색(`mapEr`)과 `Worse119`, 하단 119 독은 판정 없는 고정 안내라 남겼다(사용자 결정)
  - `useReveal`의 `enabled` 인자는 스플래시가 계속 쓰므로 남겼다
  - `design.md`에서 응급 히어로·응급 전화 버튼·통증 슬라이더 설명을 지웠다. `--radius-lg`는 센터 채팅 시트가 쓰므로 그 용도로 고쳐 적었고, `--t13`은 쓰는 곳이 없어졌다고 적었다

## 메모
- backend 26과 한 PR로 낸다(`CLAUDE.md` "백엔드·모델링과의 경계": 같은 PR로 할지는 사용자가 정한다. 이 계획에서 한 PR로 정했다). 프론트만 먼저 들어가면 `emergencyFlag` 없는 `POST /api/center/cases`가 서버에서 422가 되고, 프론트가 다시 만든 `parity.json`으로 backend CI가 깨진다
- 응급도 모델(서버 `model.acuity`)과 그 학습 자산 정리는 modeling 15다. 이 PR이 먼저 들어가야 한다
- 센터 긴급도는 응급 +3이 빠져 "높음"이 업무 중이면서 보험증도 없을 때만 나온다. 기준값은 그대로 둔다
- mock의 `emergencyFlag` 난수를 지우면 뒤 난수 순서가 밀려 mock 24건이 바뀐다. 프론트·백엔드가 같이 바뀌므로 parity로 맞춘다
