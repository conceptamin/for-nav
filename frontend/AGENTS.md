# 프론트엔드 작업 규칙

루트 `CLAUDE.md`, `docs/HARNESS.md`, `shipyard-api-contract.md`, `shipyard-frontend-proposal.md`를 먼저 읽는다. 작업 원장은 `backlog/frontend/` 아래 사용자가 작성·지정한 phase Markdown 문서다. 다른 영역의 작업은 해당 영역 백로그에서 관리하고 의존 문서 경로로 연결한다. `backlog/frontend.json`은 참고 초안이며 JSON 상태 갱신·CLI 실행은 필수가 아니다. 의존 작업이 완료된 항목부터 수행하고 검증 증거 없이 완료 처리하지 않는다. 실행·검증 명령은 아래 "검증 기준"에 등록돼 있다([frontend phase-01](../backlog/frontend/phase-01.md)).

## 범위와 스택

`frontend/`의 화면·클라이언트·지도·테스트를 소유한다. React, TypeScript, Vite, React Router, CSS Modules, TanStack Query, WebSocket store와 useSyncExternalStore, Zod, openapi-typescript, Konva/react-konva를 제안 기준으로 삼는다. 패키지는 npm으로 관리하며 버전 호환성을 확인하고 설치 작업에서 `package-lock.json`을 고정한다. 모델 학습과 예약 결정은 서버·차량 에이전트 책임이다.

## 불변 조건

- 서버가 통행 상태의 원본이다. TTL·예상 이탈·안내 확인으로 통과를 허용하지 않는다. UNKNOWN과 알 수 없는 시간 null을 숨기지 않는다.
- 계약 타입·이벤트 스키마·공통 fixture를 공유한다. 임의 필드·단위 변경은 계약 작업으로 먼저 반영한다.
- connection_id·run_id·seq·객체 버전을 검사한다. 누락은 재동기화하고 새 스냅샷 전 안내를 제한한다. 네트워크 TTL은 벽시계, 운행은 시뮬레이션 시계다.
- 관측 사이 geometry 보간만 허용한다. 외삽·서버 좌표 변경·화면 위치의 관제 입력 사용은 금지한다. 단절·STALE·일시정지 시 애니메이션과 카운트다운을 중지한다.
- 지도만 Canvas로 렌더링한다. 키보드로 조작할 수 있는 DOM 목록·버튼·안내를 제공하고 색상만으로 상태를 전달하지 않는다.
- URL 차량 ID와 클라이언트 역할을 권한 근거로 사용하지 않는다. 통제는 서버 확정 이후 반영한다.

## 검증 기준

Vitest/React Testing Library로 좌표·버전·복구·시계 규칙을 검증하고 Playwright 실제 브라우저로 Canvas hit 영역·터치·접근성·연결 단절·두 화면 결정 버전을 확인한다. 고정 프레임 스크린샷과 반복 진입 정리 검증을 포함한다. 5대·30FPS·반영 p95 200ms는 측정 목표이며 완료 실적으로 미리 적지 않는다.

### 등록 명령

Node는 `frontend/.nvmrc`(24.21.0, `engines` `>=24.21.0 <25`)를 쓴다. `.npmrc`의 `engine-strict`로 맞지 않는 Node에서는 설치가 실패한다. 의존성은 `save-exact`로 정확한 버전을 고정한다. 모든 명령은 `frontend/`에서 실행한다.

```sh
nvm use                          # .nvmrc의 Node 24.21.0
npm ci                           # package-lock.json만으로 설치
npx playwright install chromium  # E2E 브라우저(최초 1회·Playwright 버전 변경 시)
npm run typecheck                # tsc strict: tsconfig.app.json(src), tsconfig.node.json(vite 설정·scripts·tests), tsconfig.e2e.json(Playwright, DOM 포함)
npm run lint                     # ESLint flat config
npm run test                     # Vitest: src/**/*.test.tsx(jsdom), tests/**/*.test.ts(node, dev proxy 통합)
npm run build                    # vite build → dist/
npm run check:dist               # dist의 외부 origin(CDN·폰트·타일) 참조 검사, build 후 실행
npm run test:e2e                 # Playwright: build 후 vite preview, Chromium 360px·1440px
npm run dev                      # 개발 서버(기본 http://localhost:5173)
npm run preview                  # 빌드 결과 미리보기
```

dev·preview 서버는 `/api/v1/ws`(WebSocket)와 `/api`(HTTP)를 `YARDPILOT_API_ORIGIN`으로 proxy한다. 기본값은 `http://127.0.0.1:8000`이며, http(s) origin만 허용한다. `VITE_` 접두사가 없어 클라이언트 번들에는 들어가지 않는다. 백엔드가 꺼져 있어도 서버는 기동되며 `/api` 요청은 SPA `index.html`이 아닌 502로 응답한다. 백엔드의 Origin 허용 목록에는 개발 서버 origin을 넣어야 한다. 의존성을 추가하거나 갱신할 때는 공식 문서·레지스트리에서 호환 범위를 확인하고 phase 문서에 출처와 날짜를 남긴다.
