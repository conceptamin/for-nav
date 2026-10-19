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

- [ ] Node LTS 버전과 React·Vite·TypeScript·React Router·ESLint·Vitest·Playwright 버전을 공식 문서로 확인하고 출처를 기록한다.
- [ ] react-konva가 선택한 React 메이저 버전을 지원하는지 확인하고 기록한다 (설치하지 않음).
- [ ] `frontend/`에 Vite React TypeScript 프로젝트를 만들고 `package.json`의 `engines`와 Node 버전 파일로 Node 버전을 고정한다.
- [ ] TypeScript strict 설정과 `typecheck` 스크립트를 구성한다.
- [ ] ESLint flat config와 `lint` 스크립트를 구성한다.
- [ ] Vitest + React Testing Library(jsdom)와 `test` 스크립트를 구성한다.
- [ ] Playwright와 `test:e2e` 스크립트를 구성한다. Chromium을 기본으로 하고 모바일(360px)·데스크톱(1440px) viewport 프로젝트를 둔다. 브라우저 설치 명령을 문서화한다.
- [ ] Vite proxy에 `/api`(HTTP)와 `/api/v1/ws`(WebSocket)를 설정하고 대상 origin 환경 변수와 기본값을 문서화한다.
- [ ] `src/app/`에 라우터와 레이아웃을, `src/features/{driver,control,demo,runs}/`에 placeholder 화면을 둔다. 404 화면을 둔다.
- [ ] `src/styles/`에 CSS 변수와 기본 스타일을 두고 화면별 스타일은 CSS Modules로 작성한다.
- [ ] 라우트별 렌더링을 검증하는 Vitest 스모크 테스트를 작성한다.
- [ ] 네 경로와 404의 렌더링, 가로 스크롤 없음, 키보드 Tab 이동 시 포커스 표시를 검증하는 Playwright 스모크 테스트를 작성한다.
- [ ] dev server에서 `/api` 요청이 `index.html`로 응답되지 않고 proxy로 전달되는지 확인하는 검증을 작성하거나 수동 확인 절차를 기록한다.
- [ ] 빌드 산출물이 외부 CDN·폰트·지도 타일 URL을 참조하지 않는지 확인한다.
- [ ] `.gitignore`에 `frontend/dist/`, Playwright 리포트·결과 경로를 추가한다.
- [ ] `frontend/AGENTS.md`의 검증 기준 문단을 실제 등록 명령으로 갱신한다.
- [ ] 아래 완료 조건별 실행 명령·결과를 검증 결과 섹션에 기록한다.

## 의존성

없음. 이 phase는 백엔드 phase와 루트 `fixtures/`의 공유 계약 산출물 없이 진행한다.

참고: 생성 타입·Zod·REST·WebSocket을 다루는 이후 프론트 phase는 공유 계약 산출물을 만드는 백엔드 phase를 선행 조건으로 둔다. 그 연결은 이 문서가 아니라 이후 phase 문서에 기록한다.

## 완료 조건

- [ ] `frontend/`에서 `npm ci`가 커밋된 `package-lock.json`만으로 재현된다.
- [ ] `npm run typecheck`, `npm run lint`, `npm run test`, `npm run build`가 오류 없이 종료된다.
- [ ] `npm run test:e2e`가 실제 브라우저(Chromium)에서 360px·1440px viewport로 실행되어 네 경로와 404의 `h1`·문서 제목을 확인하고 통과한다.
- [ ] 360px viewport에서 각 화면에 가로 스크롤이 생기지 않고, Tab 이동 시 포커스 표시가 보인다는 것을 E2E로 확인한다.
- [ ] 백엔드가 꺼진 상태에서 `npm run dev`가 기동되고, `/api/v1/health` 요청이 SPA `index.html`이 아닌 proxy 오류로 응답된다.
- [ ] `/driver/:vehicleId`·`/runs/:runId` placeholder가 URL 파라미터로 차량·실행 데이터를 조회하거나 표시하지 않는다.
- [ ] 빌드 산출물에 외부 origin(`http://`·`https://`로 시작하는 CDN·폰트·타일) 참조가 없다.
- [ ] 이번 phase에서 설치한 직접 의존성이 범위 섹션에 적은 목록을 벗어나지 않는다.
- [ ] 확인한 Node·패키지 버전, 출처, react-konva 호환성 확인 결과가 기록돼 있다.
- [ ] `frontend/AGENTS.md`에 실제 명령이 등록돼 있다.

## 검증 결과

미실행. 구현 후 실행 환경(OS·Node·npm·브라우저 버전), 실행 명령, 결과, 완료 조건별 증거, 남은 제약을 기록한다.
