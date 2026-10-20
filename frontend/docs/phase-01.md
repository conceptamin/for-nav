# Frontend Phase 01 — 실행·검증 기반과 앱 셸

## 목표

`frontend/`에 React·TypeScript·Vite 프로젝트를 만들고 타입 검사·lint·단위 테스트·실제 브라우저 E2E·프로덕션 빌드 명령을 실제로 실행할 수 있게 한다. 기획서의 네 화면 경로를 빈 셸로 연결해 이후 phase가 같은 실행·검증 기반 위에서 기능을 추가할 수 있게 한다.

이 phase는 백엔드나 공유 계약 산출물 없이 완료할 수 있어야 한다. 제품 기능은 이 phase의 결과물이 아니다.

## 범위

포함:

- `frontend/`에 Vite + React + TypeScript 프로젝트 구성. npm으로 관리하고 `package-lock.json`을 커밋한다.
- Node 버전과 직접 의존성 버전을 공식 문서로 확인해 고정한다. 확인한 출처와 날짜를 검증 결과에 기록한다.
- 이번 phase에서 설치하는 의존성: React, React DOM, React Router, TypeScript, Vite, ESLint, Vitest, React Testing Library, Playwright, 그리고 이들을 쓰는 데 필요한 플러그인·타입 패키지.
- 이후 phase에서 쓸 react-konva는 설치하지 않되, 선택한 React 메이저 버전을 지원하는지 공식 문서로 확인해 기록한다.
- npm 스크립트: `typecheck`, `lint`, `test`, `test:e2e`, `build`, `dev`, `preview`.
- Vite dev server proxy: `/api` 경로와 `/api/v1/ws` WebSocket을 백엔드 origin으로 전달한다. 대상 origin은 환경 변수로 바꿀 수 있고 기본값은 로컬 loopback 주소다. 백엔드가 없어도 dev server는 기동되어야 한다.
- React Router로 `/driver/:vehicleId`, `/control`, `/demo`, `/runs/:runId`, 정의되지 않은 경로(404)를 placeholder 화면으로 연결한다.
- CSS Modules와 CSS 변수 기반 기본 스타일, 360px~1440px 기본 레이아웃.
- 각 placeholder 화면의 문서 제목, `main` landmark, `h1`, 보이는 키보드 포커스 표시.
- Vitest 스모크 테스트와 Playwright 실제 브라우저 스모크 테스트.
- `.gitignore`에 빌드 산출물·테스트 리포트 경로 추가.
- `frontend/AGENTS.md`의 "명령 없음" 문구를 실제 등록 명령으로 갱신한다.

제외:

- OpenAPI·이벤트 스키마 기반 생성 타입, Zod 수신 검증, openapi-typescript (백엔드 계약 산출물 필요).
- TanStack Query, REST 클라이언트, 세션 발급·`/me` 조회, WebSocket store와 재동기화.
- Konva 지도, 좌표 변환, 차량 보간, 안내 카드 등 제품 UI.
- placeholder 화면에 차량·실행 데이터를 표시하는 일. URL의 `vehicleId`·`runId`는 경로 일치 확인에만 쓰고 권한이나 데이터 조회 근거로 사용하지 않는다.
- FastAPI의 정적 파일 제공과 SPA fallback (백엔드 영역).
- `.github/workflows`에 프론트 CI 작업 추가 (정책 파일 변경이므로 별도 PR에서 다룬다).
- 성능 목표(5대·30FPS·반영 p95 200ms) 측정.

## 작업 체크리스트

- [x] Node LTS 버전과 React·Vite·TypeScript·React Router·ESLint·Vitest·Playwright 버전을 공식 문서로 확인하고 출처를 기록한다.
- [x] react-konva가 선택한 React 메이저 버전을 지원하는지 확인하고 기록한다 (설치하지 않음).
- [x] `frontend/`에 Vite React TypeScript 프로젝트를 만들고 `package.json`의 `engines`와 Node 버전 파일로 Node 버전을 고정한다.
- [x] TypeScript strict 설정과 `typecheck` 스크립트를 구성한다.
- [x] ESLint flat config와 `lint` 스크립트를 구성한다.
- [x] Vitest + React Testing Library(jsdom)와 `test` 스크립트를 구성한다.
- [x] Playwright와 `test:e2e` 스크립트를 구성한다. Chromium을 기본으로 하고 모바일(360px)·데스크톱(1440px) viewport 프로젝트를 둔다. 브라우저 설치 명령을 문서화한다.
- [x] Vite proxy에 `/api`(HTTP)와 `/api/v1/ws`(WebSocket)를 설정하고 대상 origin 환경 변수와 기본값을 문서화한다.
- [x] `src/app/`에 라우터와 레이아웃을, `src/features/{driver,control,demo,runs}/`에 placeholder 화면을 둔다. 404 화면을 둔다.
- [x] `src/styles/`에 CSS 변수와 기본 스타일을 두고 화면별 스타일은 CSS Modules로 작성한다.
- [x] 라우트별 렌더링을 검증하는 Vitest 스모크 테스트를 작성한다.
- [x] 네 경로와 404의 렌더링, 가로 스크롤 없음, 키보드 Tab 이동 시 포커스 표시를 검증하는 Playwright 스모크 테스트를 작성한다.
- [x] dev server에서 `/api` 요청이 `index.html`로 응답되지 않고 proxy로 전달되는지 확인하는 검증을 작성하거나 수동 확인 절차를 기록한다.
- [x] 빌드 산출물이 외부 CDN·폰트·지도 타일 URL을 참조하지 않는지 확인한다.
- [x] `.gitignore`에 `frontend/dist/`, Playwright 리포트·결과 경로를 추가한다.
- [x] `frontend/AGENTS.md`의 검증 기준 문단을 실제 등록 명령으로 갱신한다.
- [x] 아래 완료 조건별 실행 명령·결과를 검증 결과 섹션에 기록한다.

## 의존성

없음. 이 phase는 백엔드 phase와 루트 `fixtures/`의 공유 계약 산출물 없이 진행한다.

참고: 생성 타입·Zod·REST·WebSocket을 다루는 이후 프론트 phase는 공유 계약 산출물을 만드는 백엔드 phase를 선행 조건으로 둔다. 그 연결은 이 문서가 아니라 이후 phase 문서에 기록한다.

## 완료 조건

- [x] `frontend/`에서 `npm ci`가 커밋된 `package-lock.json`만으로 재현된다.
- [x] `npm run typecheck`, `npm run lint`, `npm run test`, `npm run build`가 오류 없이 종료된다.
- [x] `npm run test:e2e`가 실제 브라우저(Chromium)에서 360px·1440px viewport로 실행되어 네 경로와 404의 `h1`·문서 제목을 확인하고 통과한다.
- [x] 360px viewport에서 각 화면에 가로 스크롤이 생기지 않고, Tab 이동 시 포커스 표시가 보인다는 것을 E2E로 확인한다.
- [x] 백엔드가 꺼진 상태에서 `npm run dev`가 기동되고, `/api/v1/health` 요청이 SPA `index.html`이 아닌 proxy 오류로 응답된다.
- [x] `/driver/:vehicleId`·`/runs/:runId` placeholder가 URL 파라미터로 차량·실행 데이터를 조회하거나 표시하지 않는다.
- [x] 빌드 산출물에 외부 origin(`http://`·`https://`로 시작하는 CDN·폰트·타일) 참조가 없다.
- [x] 이번 phase에서 설치한 직접 의존성이 범위 섹션에 적은 목록을 벗어나지 않는다.
- [x] 확인한 Node·패키지 버전, 출처, react-konva 호환성 확인 결과가 기록돼 있다.
- [x] `frontend/AGENTS.md`에 실제 명령이 등록돼 있다.

## 검증 결과

상태: 구현 완료. 아래 기록은 `feature/frontend/phase-01-app-shell` 커밋 기준이다.

### 실행 환경

- macOS 26.6.2 (arm64), Node v24.21.0, npm 11.19.0 (nvm, `frontend/.nvmrc`)
- Playwright 1.64.0, Chrome Headless Shell 156.0.8078.4 (chromium-headless-shell v1248)
- 실행일 2026-10-20. `rm -rf node_modules dist playwright-report test-results` 후 아래 명령을 차례로 실행했다.

### 버전 확인과 출처 (2026-10-20 확인)

- Node: [nodejs.org/dist/index.json](https://nodejs.org/dist/index.json)과 [nodejs/Release schedule.json](https://github.com/nodejs/Release/blob/main/schedule.json) 기준이다. 오늘 Active LTS는 24 "Krypton"이다(2026-10-20 maintenance 진입, 2028-04-30 종료). 26은 2026-10-28에 LTS가 된다. 24.21.0(2026-09-07)을 고정했다. `.nvmrc`는 `24.21.0`, `engines.node`는 `>=24.21.0 <25`, `.npmrc`는 `engine-strict=true`다.
- 패키지 버전·peerDependencies·engines는 npm 레지스트리 메타데이터(`npm view <pkg> time|peerDependencies|engines`)로 확인했다. 각 프로젝트의 문서 사이트를 하나씩 읽지는 않았다.
- 공급망 위험을 줄이기 위해 2026-10-13 이전(7일 이상 경과)에 공개된 최신 안정판만 골랐다. `npm install --before=2026-10-13`으로 설치했고 `save-exact`로 고정했다.
- 선택한 버전은 react·react-dom 19.3.0, react-router 8.4.0, typescript 6.0.3, vite 8.3.4, @vitejs/plugin-react 6.1.2, eslint 10.12.0, @eslint/js 10.0.1, typescript-eslint 8.71.2, eslint-plugin-react-hooks 7.1.1, eslint-plugin-react-refresh 0.5.7, globals 17.13.0, vitest 5.0.4, jsdom 30.1.2, @testing-library/react 16.3.3, @testing-library/dom 10.4.2, @testing-library/jest-dom 7.0.1, @playwright/test 1.64.0, @types/react·@types/react-dom 19.3.0, @types/node 24.19.2(Node 24에 맞춤)이다.
- 호환성 판단 근거:
  - TypeScript 7.0.2는 제외했다. typescript-eslint 8.71.2의 peer가 `typescript >=4.8.4 <6.1.0`이라 6.0.3을 선택했다.
  - jsdom 30.1.2는 Node `^24.15.0`을 요구한다. 그래서 로컬에 있던 24.14.1 대신 24.21.0을 쓴다.
  - react-router 8.4.0은 react `>=19.2.7`과 Node `>=22.22.0`을 요구한다.
  - vitest 5.0.4는 vite `^8.0.0`을 지원하고, @vitejs/plugin-react 6.1.2는 vite `^8.0.0`을 요구한다.
- react-konva(설치하지 않음): [README](https://github.com/konvajs/react-konva)에 "React Konva 19.3 requires React and React DOM `^19.3.0`"이라고 적혀 있다. 레지스트리의 react-konva 19.3.0 peer도 react·react-dom `^19.3.0`, konva `^10.0.0` 등이다. 선택한 React 19.3.0과 호환된다.

### 실행 명령과 결과 (`frontend/`)

| 명령 | 결과 |
|---|---|
| `npm ci` | exit 0, 239개 설치, 0 vulnerabilities. 실행 전후 `package-lock.json` sha256(b2c2e6de72255aae…) 동일 |
| `npm run typecheck` | exit 0 (app·node·e2e tsconfig 3개, strict) |
| `npm run lint` | exit 0 |
| `npm run test` | exit 0, 2 files, 14 tests passed |
| `npm run build` | exit 0, index.html 0.39 kB, CSS 1.88 kB, JS 314.21 kB(gzip 99.49 kB) |
| `npm run check:dist` | exit 0, 3개 파일, 외부 origin 리소스 참조 없음 |
| `npm run test:e2e` | exit 0, 10 passed(5개 경로 × mobile-360·desktop-1440) |

`npm run dev` 수동 확인: 8000번 포트에 리스너가 없는 상태(`lsof` 확인)에서 `npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`가 69 ms 만에 ready가 됐다. `curl -i /api/v1/health`는 `502 Bad Gateway`, `Content-Type: text/plain`으로 응답했고 dev 로그에 `http proxy error … ECONNREFUSED 127.0.0.1:8000`이 남았다. 대조군 `/control`은 `200 text/html`과 `<div id="root">`로 응답했다.

검사 자체가 문제를 잡아내는지도 확인했다(변경은 모두 원복함):
- `:focus-visible { outline: none }`을 추가하면 E2E가 "포커스 표시"에서 실패한다.
- `h1 { width: 500px }`를 추가하면 E2E가 "가로 스크롤 없음"에서 실패한다.
- vite proxy 설정을 제거하면 proxy 테스트 3개가 실패한다.
- dist에 Google Fonts `<link>`를 넣으면 `check:dist`가 exit 1로 끝난다.

### 완료 조건별 증거

- `npm ci` 재현: node_modules를 삭제한 뒤 `npm ci` exit 0, lockfile hash가 바뀌지 않았다.
- typecheck·lint·test·build: 위 표와 같이 모두 exit 0이다.
- E2E 360px·1440px: `frontend/e2e/smoke.spec.ts`가 Chromium에서 다섯 경로(`/driver/:vehicleId`, `/control`, `/demo`, `/runs/:runId`, 404)의 단일 `h1`, `<제목> · YardPilot` 문서 제목, `main` 포함 여부를 확인한다.
- 가로 스크롤·포커스: 같은 E2E에서 `scrollWidth - clientWidth <= 0`을 확인한다. Tab을 누르면 "본문 바로가기" 링크에 포커스가 가고, 링크가 viewport 안에 완전히 보이며 outline이 2px 이상인지 확인한다. Enter를 누르면 `main`으로 포커스가 이동하는지도 본다.
- 백엔드 없는 dev 기동과 proxy 오류: `frontend/tests/dev-proxy.test.ts`가 실제 `vite.config.ts`로 dev server를 띄워 확인한다.
  - 백엔드가 켜져 있으면 `/api` HTTP 200과 `/api/v1/ws` upgrade가 백엔드에 도달한다.
  - 닫힌 포트로 설정하면 `/api/v1/health`가 502를 반환하고, HTML도 `#root`도 아니다.
  - 기본값 `http://127.0.0.1:8000`, 환경 변수 정규화, http(s)가 아닌 값 거부도 검증한다.
  - 위 `npm run dev` 수동 확인 결과와 일치한다.
- URL 파라미터 미사용: `src/app/routes.test.tsx`에서 fetch·WebSocket을 stub하고 렌더링했다. 호출은 0회였고, 본문과 제목에 파라미터 값이 나타나지 않았다. E2E에서도 본문과 제목에 `vehicle-secret-7`·`run-secret-42`가 없다. 화면 코드는 `useParams`를 사용하지 않는다.
- 외부 origin 참조: `npm run check:dist`는 HTML·CSS의 http(s) URL을 모두 거부한다. JS에서는 요청하지 않는 문자열만 허용한다(XML 네임스페이스, React·React Router 오류 메시지의 문서 링크, React Router의 URL 파싱 기준값 `http://localhost`). E2E에서도 페이지마다 다른 origin으로 가는 요청이 0건이었다.
- 직접 의존성 범위: `npm ls --depth=0` 결과는 dependencies 3개(react, react-dom, react-router)와 devDependencies 18개다. 모두 범위에 적힌 패키지이거나 그것을 쓰는 데 필요한 플러그인·타입 패키지다. TanStack Query·Zod·Konva는 설치하지 않았다.
- 버전·출처·react-konva 기록: 위 "버전 확인과 출처" 절에 있다.
- `frontend/AGENTS.md`: "등록 명령" 절에 실제 명령, Node 고정, proxy 환경 변수와 기본값, 브라우저 설치 명령을 등록했다.

### 남은 제약

- `npm ci`가 `fsevents@2.3.3`(vite의 macOS 선택 의존성)의 install script를 npm `allowScripts` 정책에 따라 실행하지 않았다는 경고를 낸다. 실행을 승인하지 않았고, dev·build·test는 영향 없이 동작했다.
- 프론트 CI 작업은 범위에서 제외했으므로 위 결과는 로컬 실행 증거다.
- Linux·Windows, Firefox·WebKit, 실제 모바일 기기에서는 실행하지 않았다. 360px은 Chromium 모바일 에뮬레이션(isMobile, hasTouch, DPR 2)이다.
- 백엔드 Origin 허용 목록에 개발 서버 origin을 넣는 일은 백엔드 phase에서 다룬다.
