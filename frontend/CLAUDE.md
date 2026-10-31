# frontend 작업 규칙

울산 외국인 의료 내비게이터의 근로자 화면(모바일)과 센터 화면(PC)을 만드는 폴더다(Vite + React + TypeScript). 지금은 규칙·템플릿·mock이 모두 브라우저 안에서 도는 단독 데모이고, 백엔드 API(`backend/`)로 전환할 자리를 만들어 가는 중이다.
무엇을 보여 주는지(화면 구성, API 연결 정책, 상태의 경계, 미결 값)는 `README.md`가 정하고, 어떻게 그리는지(SEED Design 토큰·컴포넌트와 글래스모피즘)는 `design.md`가 정하고, **무엇을 언제 만드는지는 `backlog/` 문서가 정한다.** 이 문서는 그 셋을 코드로 옮길 때 지키는 규칙이다.

브랜치·커밋·PR 규칙은 루트 `CLAUDE.md`를 따른다. 브랜치 영역은 `frontend/`이다.

## 읽는 순서

1. 루트 `CLAUDE.md`
2. `frontend/README.md` — 화면 구성(PRD 8장 경로), 폴더 구조, API 연결(두 모드, 경로별 대체 정책, 비동기 UX 규칙), 상태의 경계, 나중에 붙일 자리, 확인이 필요한 값. 여기에 없는 화면·경로를 새로 넣지 않고, 대체 정책 표에 없는 실패 동작을 만들지 않는다.
3. `frontend/design.md` — 화면을 그릴 때. SEED Design의 색·타이포·간격·둥글기 토큰과 컴포넌트, Do's and Don'ts, 그리고 이 프로젝트의 글래스모피즘(세 가지 면, `--glass*` 그림자·흐림 토큰). 문서에 없는 모양을 그리기 전에 문서를 먼저 고친다.
4. `frontend/backlog/` — 작업 항목. 사용자가 지정한 항목 하나만 구현한다.
5. API를 부를 때는 `backend/README.md`의 API 목록·요청·응답 예시와 "프론트 전환 방법", `backend/app/schemas.py`(응답 형태), `backend/app/vocab.py`(열거값)
6. 규칙·템플릿·mock을 바꿀 때는 `frontend/scripts/dump-fixtures.ts`와 `backend/README.md`의 "프론트 동기화 테스트"

## backlog 문서로 일한다

- `backlog/` 안의 문서 하나가 작업 항목 하나다. 파일 이름은 `NN-short-name.md`(예: `01-api-client-switch.md`)로 쓰고, 번호가 작은 것이 먼저다.
- 사용자가 항목을 말하지 않으면 미완료 항목 중 번호가 가장 작은 것을 고르고, 시작 전에 어느 항목을 하는지 말한다. `의존:`에 적힌 항목이 완료되지 않았으면 시작하지 않고 사용자에게 알린다. 다른 폴더의 항목에 기대면 `backend 01`처럼 폴더 이름을 붙여 적는다.
- `backlog/`에 맞는 항목이 없으면 구현을 시작하지 않는다. 아래를 근거로 아래 형식의 문서를 먼저 쓰고, 사용자가 확인한 뒤 구현한다.
  - `README.md`의 "API 연결", "나중에 붙일 자리", "실서비스와 다른 점", "확인이 필요한 값"
  - `design.md`의 규칙과 `styles.css`가 어긋난 곳(문서에 없는 모양, 토큰 밖 값)
  - `backend/README.md`의 "프론트 전환 방법"과 "구현 순서"
  - `backend/backlog/`·`modeling/backlog/`의 `## 메모`에서 프론트 몫으로 넘긴 일(예: 응급도 3단계 표시, 센터 화면 SHAP 표시)
- 백엔드 문서가 "frontend 항목 7"이라고 부르는 것은 `backend/README.md` "구현 순서" 7번(`src/api/` 전환, Vite 프록시)이다. 이 일을 backlog 문서로 쓸 때 `## 메모`에 그 대응을 적어, 백엔드 문서의 참조를 따라올 수 있게 한다.
- **지정된 항목의 범위만 구현한다.** 하다가 발견한 다른 일은 새 backlog 문서로 만들거나 기존 문서의 `## 메모`에 적고, 지금 작업에 섞지 않는다.
- 문서의 `## 완료 기준`을 그대로 검증한다. 기준이 모호하거나 검증할 방법이 없으면 구현 전에 사용자에게 묻는다.
- 끝나면 그 문서의 `## 결과`에 실행한 명령과 결과, 브라우저에서 확인한 경로와 언어, 바뀐 화면·경로, 내린 결정과 이유를 적고 `상태:`를 바꾼다. 결과 기록은 코드와 같은 PR에 넣는다.
- backlog 문서와 `README.md`(또는 `backend/README.md`의 API 계약)가 어긋나면 멈추고 사용자에게 묻는다. 임의로 한쪽을 고치지 않는다.

### backlog 문서 형식

```markdown
# NN. <제목>

상태: 대기 | 진행 중 | 완료 | 보류
의존: <먼저 끝나야 하는 항목 번호, 없으면 "없음">

## 목표
무엇을 왜 만드는지 두세 문장

## 범위
- 하는 것
- 하지 않는 것

## 화면·파일
추가·변경되는 경로(S-xx·C-xx), 부르는 API, 만들거나 고치는 파일, 새 문구 키

## 완료 기준
- [ ] 검증할 수 있는 문장으로 쓴다 (예: `npm run build` 통과, `VITE_API_BASE` 없이 띄워 `/intake` → `/result`가 지금과 같이 동작, 백엔드를 끄고 API 모드로 응급 입력 시 `/emergency`가 바로 뜸, en·vi·ko 세 언어에서 확인)

## 결과
(구현 후 작성) 실행 명령 → 결과, 확인한 화면, 결정 사항, 남은 문제

## 메모
```

## 스택과 폴더

- Vite + React 19 + react-router + TypeScript(strict). 버전은 `package.json`에 범위 기호 없이 고정하고 `package-lock.json`을 커밋한다. 의존성을 더할 때는 backlog 문서에 이유를 적는다. 상태 관리·UI·스타일 라이브러리는 지금 쓰지 않으며, 더하려면 사용자에게 먼저 묻는다.
- 검사는 `npm run build`(타입 검사 + 빌드) 하나다. 린터·포매터·테스트 러너는 아직 없다. 들이는 것은 backlog 문서 하나로 따로 한다.
- 폴더 구조는 `README.md`의 "폴더 구조"를 따른다. 새 폴더가 필요하면 backlog 문서에 이유를 적고 `README.md`의 구조를 함께 고친다.

```text
frontend/
  CLAUDE.md  README.md  design.md  backlog/
  package.json  package-lock.json  vite.config.ts  tsconfig.json  index.html
  scripts/dump-fixtures.ts   백엔드 동기화 테스트 기대값(parity.json) 생성
  public/logo.png            팀 로고 마크. 빌드 없이 그대로 서빙된다(파비콘·로고 화면·앱 바)
  public/wordmark.png        앱 이름 `for nav` 글자 그림(스플래시·로고 화면·홈 앱 바)
  public/flags/              S-01 언어 칸의 국기 SVG 19개(flag-icons 7.6.0에서 복사, MIT, LICENSE.txt 함께). 패키지는 의존성으로 두지 않는다
  src/
    main.tsx       라우트 표. 경로 옆에 PRD 화면 ID(S-xx, C-xx) 주석
    domain/        규칙 엔진·템플릿·어휘. React·DOM·저장소를 모르는 순수 함수. 백엔드가 옮기는 원본
    data/          시드 고정 mock(mulberry32)
    i18n/          근로자 고정 문구. en이 기준, 나머지 19개 언어는 같은 키를 타입으로 강제
    state/         세션·기기 저장 상태(AppState), 센터 접수함 저장소, 저장소 래퍼
    components/    여러 화면이 쓰는 조각(WorkerLayout, 119 버튼 등)
    pages/         worker/(S-01~S-13), center/(C-01~C-03)
    api/           (전환 후) 화면이 부르는 함수. 브라우저 함수와 API 중 하나를 고른다
```

- **로직은 `domain/`, 화면은 `pages/`.** 화면 컴포넌트에 판정 조건·문장 조합을 넣지 않는다. `domain/`에 있어야 동기화 테스트로 백엔드와 같은지 검증할 수 있다.
- **저장소는 `state/`만 연다.** `localStorage`·`sessionStorage`는 `state/storage.ts`의 래퍼로만 읽고 쓴다(사생활 보호 모드에서 실패해도 앱이 멈추지 않게).
- **API 전환 후 화면은 `src/api/`만 부른다.** `fetch`를 화면이나 `domain/`에서 직접 부르지 않는다. 단독/API 모드 분기와 실패 시 대체 분기는 `src/api/` 안에만 있다. 화면은 두 모드에서 같은 형태의 값을 받고, 시간 제한 숫자를 갖지 않는다.
- **화면은 `design.md`의 토큰과 컴포넌트로 그린다.** 새 클래스·새 색이 필요하면 `:root` 토큰과 `design.md`를 먼저 고친다. `styles.css` 밖에 색을 쓰지 않고, 새 인라인 `style`을 더하지 않는다(지금 있는 간격용 몇 곳은 그대로 둔다). 스피너·모달·토스트·애니메이션은 만들지 않는다(예외: 스크롤 등장 효과 하나, `src/components/reveal.ts`, 사용자 결정, backlog 25. 응급 화면·119에는 걸지 않는다).
- 근로자에게 보이는 문구는 `i18n/`의 키로만 쓴다. 키를 더하면 20개 언어 파일에 모두 넣는다(타입 검사가 빠진 키를 잡는다). 어휘·접수 도우미 문장은 `domain/lang/<언어>.ts`에 있다. 센터 화면·접수 창구처럼 한국어로 고정된 문구는 `domain/`의 `*_KO` 표를 쓴다.
- 경로를 더하거나 바꾸면 `main.tsx`의 화면 ID 주석과 `README.md`의 화면 구성 표를 같은 PR에서 고친다.

## 설계에서 바꾸지 않는 것

- **단독 데모는 계속 동작한다.** `VITE_API_BASE`가 비어 있으면 지금처럼 브라우저 안의 함수를 쓰고, 값이 있을 때만 API를 부른다(발표장 네트워크 문제 대비). 어느 작업도 단독 모드를 깨뜨리지 않는다.
- **응급 판정은 늦어지면 안 된다.** API 모드에서도 브라우저 규칙을 먼저 돌려 응급이면 서버를 기다리지 않고 `/emergency`로 간다. `/api/triage`가 실패하거나 느리면 브라우저 결과를 쓴다. 119 안내와 하단 119 버튼은 네트워크·로딩 상태와 관계없이 보인다(예외: 첫 진입 1.2초 스플래시, 사용자 결정, backlog 24). 자유 입력 추출(`/api/extract`)도 실패하면 브라우저 함수로 대체한다(추출에서 멈추면 응급 판정이 늦어진다).
- **실패 시 행동은 `README.md`의 "경로별 대체 정책" 표를 따른다.** 근로자 화면의 제도 경로·접수 도우미·리포트는 실패하면 브라우저 함수로 조용히 대체하고(결과가 같다), 센터 경로(`/api/center/*`)는 **대체하지 않고** 실패를 보인다. localStorage를 서버 대신 쓰는 가짜 성공을 만들지 않는다. 표에 없는 경로를 부르게 되면 표를 먼저 고친다.
- **`domain/`이 원본이다.** 백엔드 규칙·템플릿·mock은 이 폴더를 옮긴 것이다. `domain/`·`data/mock.ts`를 바꾸면 `parity.json`을 다시 만들어 같은 PR에 넣는다("검사와 커밋"). 백엔드 출력이 달라 보여도 프론트를 서버에 맞춰 고치지 않고 사용자에게 묻는다.
- **열거값은 백엔드 `vocab.py`와 같다.** `domain/vocab.ts`의 `BodyPart`, `Symptom`, `Department`(10종) 등을 바꾸면 백엔드와 `modeling/`이 함께 깨진다. 바꿔야 하면 사용자에게 묻고, 승인되면 backlog 문서 `## 메모`에 영향 범위를 적는다.
- **API 계약은 `backend/README.md`가 정한다.** 화면이 쓰는 타입은 `domain/`의 타입 그대로이고 JSON 필드는 camelCase다. 응답에 없는 필드를 기대하거나 요청 형태를 임의로 바꾸지 않는다. 계약을 바꿔야 하면 backlog 문서 `## 메모`에 적고 사용자에게 알린다.
- **진단 표현을 넣지 않는다.** 병명·추측 문장을 화면·템플릿에 새로 넣지 않는다. 모델 결과를 보여 줄 때도 응급도와 진료과까지만 보이고 질환명은 보이지 않는다.
- **제도 안내는 기관이 최종 결정한다.** 산재·건강보험·지원 경로 화면은 "기관이 최종 결정" 문구와 정보 기준일(`INFO_DATE`)을 항상 함께 보인다. 확인되지 않은 연락처·금액을 넣지 않는다(`README.md` "확인이 필요한 값").
- **근로자 정보는 브라우저에 둔다.** 언어, 동의, 현재 입력, 비회원 리포트는 브라우저 저장소에 두고 서버로 보내지 않는다. 센터 요청은 회원만, 전송 동의를 따로 받은 뒤에만 보낸다. 입력 내용·연락처를 `console`에 찍지 않는다.
- **센터 통계는 집계만 보인다.** 5건 미만 칸은 숨긴다. API 모드에서는 서버가 준 집계를 그대로 그리고, 원천 레코드를 받아 브라우저에서 세지 않는다.
- **동의는 3개로 나눠 받는다.** 하나로 합치거나 기본 체크로 바꾸지 않는다.
- 한국어를 고르면 발음 표기·모국어 뜻 줄·리포트 언어 토글·통역 요청 문장을 숨기는 동작을 유지한다.
- 베트남어를 비롯한 외국어 문구·발음 표기를 더하거나 고치면 원어민 검수가 필요하다는 것을 backlog 문서 `## 메모`에 남긴다. en·vi를 뺀 17개 언어는 기계 번역 초안이다(backlog 16).

## 백엔드·모델링과의 경계

- `backend/`·`modeling/` 코드는 이 폴더의 작업에서 고치지 않는다. 서버 쪽이 필요하면 backlog 문서 `## 메모`에 적고 사용자에게 알린다.
- 예외는 `backend/tests/fixtures/parity.json`이다. 프론트 `domain/`·`data/mock.ts`를 바꿨다면 이 파일은 프론트 코드의 출력이므로 다시 만들어 같은 PR에 넣는다. 손으로 고치지 않는다.
- 재생성 후 `backend`에서 `uv run pytest`가 실패하면(서버 규칙이 아직 옛것) 멈추고 사용자에게 묻는다. 서버 수정을 같은 PR에 넣을지 `backend/` 브랜치로 따로 할지는 사용자가 정한다. CI `backend` 작업이 모든 PR에서 돌므로 실패한 채로 올리지 않는다.
- 모델 결과(`TriageResult.model`)는 선택 필드다. 없을 때도 화면이 지금처럼 동작해야 한다.
- `app-front/`(Flutter WebView용 근로자 앱)가 이 폴더의 `src/pages/worker/*`, `src/components/WorkerLayout`, `src/state/AppState`, `src/styles.css`, `public/`을 경로 별칭 `@fe`로 **공유 import**한다(app-front backlog 02). 이 파일들을 옮기거나 이름을 바꾸거나 `.w-header button.back`(앱 바 ←, app-front의 Android 뒤로 가기가 누른다) 선택자를 바꾸면 `cd app-front && npm run build`도 함께 돌려 확인하고, 깨지면 같은 PR에서 `app-front/src/main.tsx`·`src/bridge/back.ts`를 고친다. `app-front/` 작업은 이 폴더를 고치지 않는다.

## 검사와 커밋

```sh
cd frontend
npm ci
npm run build
```

브라우저에서 바뀐 경로를 직접 확인한다. 근로자 화면은 휴대폰 폭(360px)으로, 센터 화면은 1280px과 900px 아래에서, 언어는 en·vi·ko 세 가지로 본다(베트남어가 가장 길어 넘침이 먼저 보인다). 근로자 화면 배치를 바꿨으면 ar(RTL)·my·ru도 본다.

```sh
npm run dev                                   # 단독 모드, http://localhost:5180
VITE_API_BASE=/api npm run dev                # API 모드 (다른 터미널: cd backend && uv run fastapi dev app/main.py)
```

`domain/`·`data/mock.ts`를 바꿨으면 기대값을 다시 만들고 백엔드 테스트를 돌린다.

```sh
cd frontend
npx rolldown scripts/dump-fixtures.ts --file /tmp/dump.mjs --format esm && TZ=Asia/Seoul node /tmp/dump.mjs > ../backend/tests/fixtures/parity.json
cd ../backend && uv run pytest
```

- 커밋 메시지의 `테스트:` 줄에 `npm run build` 결과와 브라우저에서 확인한 경로를 적는다. 문서만 바꿨으면 그렇게 적는다.
- CI의 `frontend` 작업(`.github/workflows/ci.yml`)은 아직 이름만 있는 자리표시자다. 실제 검사 단계로 바꾸는 것은 `chore/` 영역의 별도 작업이다.
