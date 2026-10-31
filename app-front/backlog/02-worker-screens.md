# 02. 근로자 화면 가져오기(S-01~S-13, /guide)

상태: 완료(실제 WebView 확인은 03에서)
의존: 01

## 목표
`frontend/`의 근로자 화면 전부를 이 앱에서 그대로 띄운다. 화면·규칙·문구·스타일은 `frontend/`와 한 글자도 다르지 않아야 하고, 다른 것은 센터 화면이 없다는 것과 다리(01)가 끼어 있다는 것뿐이다. 이 항목이 끝나면 PC 브라우저에서 `http://localhost:5181/`이 `frontend/`의 근로자 화면과 같게 보이고, 호스트가 있으면 전화·지도 링크가 `openExternal`로 나간다.

## 결정이 필요한 것

1. **가져오는 방법.** → **A로 결정(2026-10-31).** 권장: **A. 공유 import.**
   - **A. 공유 import(권장).** `vite.config.ts`에 별칭 `@fe` → `../frontend/src`, `resolve.dedupe: ['react', 'react-dom', 'react-router']`, `server.fs.allow`에 저장소 루트, `publicDir: '../frontend/public'`(로고·국기). `src/main.tsx`가 `@fe/pages/worker/*`, `@fe/components/WorkerLayout`, `@fe/state/AppState`, `@fe/styles.css`를 import하고 근로자 경로만 등록한다. 원본이 하나로 남고 `frontend/` 수정이 바로 반영된다. 대신 `frontend/node_modules`가 있어야 타입 검사가 되고(`npm ci`를 두 곳에서), `frontend/`의 파일 이동이 이 앱 빌드를 깨뜨릴 수 있다(`frontend/CLAUDE.md` "경계"에 한 줄 더한다, 이 앱 CI 잡은 `chore/` 별도).
   - B. 복사. `frontend/src`의 `domain/`·`data/`·`i18n/`·`api/`·`state/`·`components/`·`pages/worker/`·`styles.css`를 이 폴더로 복사하고 센터 관련 코드를 지운다. 폴더가 독립적이지만 같은 코드가 둘이 되어 `frontend/` 수정 때마다 다시 복사해야 하고, "`domain/`이 원본" 규칙을 사람이 지켜야 한다.
   - C. npm 워크스페이스로 `frontend/src`를 패키지로 뽑기. 가장 깨끗하지만 `frontend/`의 설치·CI·Vercel·맥미니 배포 명령이 모두 바뀐다. 이 항목 범위 밖.
2. **진입 가드와 스플래시.** → **권장대로 결정(2026-10-31, 그대로 둔다).** `WorkerLayout`의 스플래시(세션당 한 번 1.2초)는 네이티브 스플래시와 겹친다. 권장: 그대로 둔다(호스트 없을 때와 같은 동작, 바꾸려면 `frontend/` 항목). 호스트가 있을 때 웹 스플래시를 건너뛰는 것은 "호스트가 있을 때만 다른 화면"이라 `CLAUDE.md`에 어긋난다.

## 범위
- 하는 것
  - 결정 1에 따라 `vite.config.ts`·`tsconfig.json`(`paths`) 설정 또는 복사
  - `src/main.tsx`: 근로자 경로 S-01~S-13·`/guide`를 `frontend/src/main.tsx`와 같은 순서·같은 화면 ID 주석으로. `/__host`는 유지. `/center*`는 없고 알 수 없는 경로는 `/`
  - `HostProvider`를 `AppStateProvider` 바깥에 둔다(`useHost()`가 상태에 의존하지 않게)
  - 하단 119 띠·앱 바는 `WorkerLayout`이 그리므로 이 앱이 다시 그리지 않는다. 안전 영역 패딩은 `src/styles.css`에 `.w-shell`·`.bar-119` 덧붙임(`design.md`)으로 더한다
  - `locale`: `useHost().locale`이 있으면 S-01의 폰 언어 제안(`frontend/src/i18n/suggest.ts`)에 `navigator.language` 대신 넘긴다. 이것이 유일하게 호스트 값이 화면에 닿는 곳이고, 방법은 결정 1에 따라 다르다(A면 `suggest`가 인자를 받는지 확인하고, 안 받으면 `frontend/` 항목으로 넘긴다)
  - `README.md` "폴더 구조"·"나중에 붙일 자리"·"실서비스와 다른 점" 갱신, A면 `frontend/CLAUDE.md` "경계"에 한 줄
- 하지 않는 것
  - 화면·문구·스타일 변경(필요하면 `frontend/` 항목), 센터 화면, 통화·받아쓰기의 네이티브 연결(04)
  - 호스트가 있을 때만 다른 화면·동작

## 화면·계약·파일
- 화면: S-01~S-13, `/guide` 전부. `/__host` 유지
- 계약: 변경 없음. `init.locale`이 처음으로 쓰인다
- 추가·수정: `vite.config.ts`, `tsconfig.json`, `src/main.tsx`, `src/styles.css`, `README.md`, (A) `frontend/CLAUDE.md` 한 줄 / (B) 복사한 폴더들

## 완료 기준
- [x] `npm run build` 통과(A면 `frontend/`와 `app-front/` 둘 다 `npm ci` 뒤)
- [x] 단독 모드: `/`부터 S-01 → 동의 → 비회원 → 홈 → 증상 입력 → 결과 → 접수 도우미까지 `frontend/`(5180)와 같은 화면이 뜨고 네트워크 탭에 `/api` 요청이 없다. 한국어·베트남어·아랍어(RTL)로 한 번씩
- [x] API 모드(백엔드 켬): `/api/triage`·`/api/extract`가 200이고 결과가 단독 모드와 같다. 백엔드 끔: 같은 화면, 오류 문구 없음
- [x] `/center`로 들어가면 `/`로 간다
- [x] 호스트 없음: 하단 119 띠·결과 화면 지도 링크가 브라우저 기본대로 열린다. 콘솔에서 가짜 호스트(01의 방법)를 넣고 `init`을 보내면 같은 링크가 `openExternal`로 나가고 페이지는 그대로다
- [x] 가짜 `init`에 `insets.bottom: 48`을 주면 119 띠가 48px 위로 올라가고 본문 아래 여백이 같이 늘어난다
- [x] `window.fornav.onBack()`이 `/intake`에서 `true`(한 단계 뒤로), `/home`에서 `false`
- [x] 결정 1이 A면: `frontend/src`의 임의 파일을 고치고 저장했을 때 5181에서 HMR로 반영된다

## 결과
- 실행(2026-10-31)
  - `npm ci && npm run build` → 통과(tsc + vite build). `frontend/node_modules` 없이 빌드된다 — `tsconfig.json`의 `paths`가 react·react-dom·react-router(및 `react-router/dom`)를 이 폴더의 `node_modules`로 고정하고, Vite는 `resolve.dedupe`로 같은 일을 한다
  - 단독 모드(내장 브라우저 375×812): `/center` → `/`. S-01(국기 20개, 로고 `/logo.png` 표시) → 한국어 → 동의(전체 동의) → 홈 → 증상 입력(손·부기, 자유 입력 건너뛰기, 추가 질문 9개) → `/result`(정형외과·가정의학과) → `/visit/desk`. `/api` 요청 0건, 콘솔 오류 0건, 가로 넘침 없음. 베트남어·아랍어(RTL `dir=rtl`)로 바꿔 `/result`·`/visit/desk` 확인
  - 호스트 없음: 하단 119 띠(`tel:119`)와 결과 화면 지도 링크가 가로채이지 않는다. 가짜 통로 + `init(insets.bottom 48, top 24)` 뒤: 같은 링크가 `openExternal`(url 포함)로 나가고 페이지는 그대로. `.bar-119` padding-bottom 10→58px, `.w-main` padding-bottom 80→128px, `.w-header` padding-top 10→34px. `insets` 0으로 돌리면 원래 값
  - 뒤로 가기: `/home` false, `/intake` 2단계에서 true + 1단계로(앱 바 ←와 같음, 경로 그대로), `/visit/desk` true + `/home`
  - API 모드(`VITE_API_BASE=/api`, 프록시): `/api/meta`·`/api/extract`·`/api/triage` 200. 자유 입력 "기계에 손이 끼었어요"로 `workType: machine`이 채워지고 결과는 단독 모드와 같다(정형외과·가정의학과). 포트 8000에는 다른 세션의 center-login-demo 백엔드가 떠 있어 프록시가 그것을 썼다(같은 계약)
  - 백엔드 꺼짐: 그 서버를 끌 수 없어 `VITE_API_BASE=http://localhost:8599`(아무것도 없는 포트)로 대신했다. 연결 거부 즉시(`extract` 0.3초) 브라우저 함수로 대체, 콘솔에 `[api] /extract NETWORK → 브라우저 함수로 대체`·`/triage NETWORK` 두 줄, 결과 화면 같음, 오류 문구 없음(추출 알림 "키워드 사전으로 찾은 답입니다"는 정책대로)
  - HMR: `frontend/src/pages/worker/Visit.tsx`에 주석 한 줄을 붙였다 떼자 5181 개발 서버 로그에 `hmr update /@fs/…/frontend/src/pages/worker/Visit.tsx`가 찍혔다(파일은 되돌렸다)
- 결정 사항
  - 결정 1 = A(공유 import), 결정 2 = 스플래시 그대로(2026-10-31 사용자 확인)
  - `init.locale`은 S-01 제안에 쓰지 않는다. `Onboarding.tsx`가 `navigator.languages`를 직접 읽는데, WebView의 `navigator.languages`가 기기 언어를 그대로 주므로 `frontend/` 항목이 필요 없다. 호스트 값은 `/__host` 표시용으로만 남긴다(`README.md` "메시지 형식")
  - Android 뒤로 가기는 앱 바 ←(`.w-header button.back`)를 누르는 것과 같게 했다(`src/bridge/back.ts`). 화면이 `useScreenBar`로 등록한 동작(S-05 단계 되돌리기)을 `frontend/`를 고치지 않고 그대로 쓰기 위해서다. 선택자 의존은 `frontend/CLAUDE.md` "경계"에 적었다
  - 안전 영역은 `frontend/src/styles.css`의 `env()` 값 위에 `--inset-*`을 더하는 덧붙임 규칙 6개(`.w-header`, `.w-corner-logo`, `.w-shell`, `.w-main`, `.w-footer`, `.bar-119`)로 했다. 원래 숫자(10px, 16px, `--bar-119`)를 다시 적으므로 `frontend/`가 바꾸면 함께 바꿔야 한다
- 남은 문제
  - 실제 WebView(Android·iOS) 확인은 03에서. 번들 크기 경고(927kB, `frontend/`와 같은 구성)는 그대로 둔다
  - CI에 이 폴더의 잡이 없다(`chore/` 별도)

## 메모
- 백엔드 동기화 테스트(`parity.json`)는 `frontend/`에서만 만든다. 이 항목은 `domain/`을 바꾸지 않으므로 다시 만들 일이 없다
- 의존성 버전이 `frontend/`와 다르면 A에서 React가 둘이 되어 훅 오류가 난다. `CLAUDE.md` "스택과 폴더"의 버전 규칙이 이것 때문이다
