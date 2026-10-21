# 프론트엔드 작업 규칙

루트 `CLAUDE.md`, [공통 계약](../docs/api-contract.md), [프론트 기획서](docs/proposal.md)를 먼저 읽는다. phase 문서는 `frontend/docs/phase-XX.md`에 쓴다. 지정된 phase의 범위만 구현하고 검증 결과를 같은 문서에 남긴다. 다른 영역에 의존하면 그 영역의 phase 문서 경로를 적는다. 다음 작업은 [phase-02](docs/phase-02.md)다.

## 범위와 스택

`frontend/`의 모바일 웹 화면·클라이언트·테스트를 소유한다. React, TypeScript, Vite, React Router, CSS Modules를 쓴다. 계약 수신 검증은 Zod, 계약 타입은 백엔드 OpenAPI에서 생성한다(openapi-typescript). 패키지는 npm으로 관리하고 `package-lock.json`을 고정한다. 응급 판단, 비용 경로 결정, 요약 생성은 서버 책임이며 프론트에서 다시 계산하지 않는다.

## 불변 조건

- 119 화면이 먼저다. `/triage`의 `is_emergency`가 참이면 다른 화면보다 먼저 119 안내를 띄우고, 응급이 아닌 결과에도 "증상이 심해지면 119"를 항상 보인다. 네트워크 오류로 응급 결과를 받지 못하면 "응급 아님"으로 보이지 않고 119 안내와 재시도를 함께 보인다.
- 비용 경로 결과는 판정이 아니라 "먼저 상담할 곳"으로 쓴다. 모든 결과 화면 아래에 "지원 여부는 각 기관이 최종 결정합니다"와 정보 기준일을 보인다. `verified: false` 연락처는 "상담으로 확인하세요"로 보이고 번호를 지어내지 않는다.
- 비자·체류 자격을 묻는 화면을 만들지 않는다. 이름·소속·사업장명 입력란을 만들지 않는다. 위치는 구·군 선택까지만 받는다.
- 요약 카드는 항목별 선택 화면(기본값 모두 포함)과 동의 버튼을 거친 뒤에만 요청한다. 뺀 항목은 요청 본문에 넣지 않는다.
- 외부 AI 전송 고지와 동의를 처음 쓸 때 근로자 언어로 받는다. 동의 전에는 `/triage`·`/summary`를 호출하지 않는다.
- 증상·작업 기록은 기기에만 저장한다(localStorage 또는 IndexedDB). 서버나 외부 분석 도구로 보내지 않는다. 기록 삭제 버튼을 둔다.
- 근로자에게 보이는 문구는 모두 언어 파일(`en`, `vi`)에서 가져온다. 의사용 요약 카드만 한국어로 크게 보인다. 번역이 없는 키는 빌드·테스트에서 실패시킨다.
- 360px 폭 휴대폰에서 한 손으로 쓸 수 있어야 한다. 터치 영역 44px 이상, 색상만으로 상태를 전달하지 않고, 키보드로도 조작할 수 있다.
- 외부 CDN·폰트·분석 스크립트를 불러오지 않는다(`check:dist`가 검사).

## 검증 기준

Vitest/React Testing Library로 화면 분기(응급 → 119 우선, 네트워크 오류 시 119 안내), 비용 질문의 순서와 생략, 요약 카드 항목 선택과 동의 전 미호출, 언어 파일 누락 키를 검증한다. Playwright 실제 브라우저(360px·1440px)로 첫 흐름 전체를 백엔드 mock 응답으로 끝까지 통과하는지 확인한다.

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

dev·preview 서버는 `/api`(HTTP)를 `YARDPILOT_API_ORIGIN`으로 proxy한다. phase-02에서 `FORNAV_API_ORIGIN`으로 바꾼다. 기본값은 `http://127.0.0.1:8000`이며, http(s) origin만 허용한다. `VITE_` 접두사가 없어 클라이언트 번들에는 들어가지 않는다. 백엔드가 꺼져 있어도 서버는 기동되며 `/api` 요청은 SPA `index.html`이 아닌 502로 응답한다. 휴대폰 실기기에서 마이크를 쓰려면 HTTPS 또는 localhost가 필요하다(음성 입력 phase에서 다룬다). 의존성을 추가하거나 갱신할 때는 공식 문서·레지스트리에서 호환 범위를 확인하고 phase 문서에 출처와 날짜를 남긴다.
