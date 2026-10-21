# Frontend Phase 02 — 첫 흐름 화면

목표일: 2026-10-23

## 목표

휴대폰 브라우저에서 언어 선택 → 고지·동의 → 상황 말하기 → (응급이면 119) → 비용 경로 → 요약 카드까지 한 번 이어지게 한다. YardPilot 화면 자리와 이름을 for-nav로 바꾼다.

## 범위

포함:

- 이름 교체: `package.json`의 `name`, proxy 환경 변수 `YARDPILOT_API_ORIGIN` → `FORNAV_API_ORIGIN`, 관련 테스트·주석, `frontend/AGENTS.md`의 설명. 기본값 `http://127.0.0.1:8000`은 유지한다. 쓰지 않는 WebSocket proxy(`/api/v1/ws`)는 지운다.
- YardPilot 화면 자리(`/driver/:vehicleId`, `/control`, `/demo`, `/runs/:runId`)와 해당 `features/` 폴더를 지우고, [기획서 2장](proposal.md)의 `/`, `/consent`, `/describe`, `/emergency`, `/route`, `/card`를 만든다. 404는 유지한다.
- 언어 파일 `en`·`vi`와 누락 키 검사 테스트.
- 계약 3·4·5장 응답의 Zod 스키마(이번 phase는 손으로 작성, 생성 연결은 phase-03). 스키마는 `fixtures/contract/` 예시로 테스트한다.
- `/triage`, `/route`, `/summary` 호출 클라이언트.
- 화면 분기: 응급 → 119 우선, 네트워크 오류 → 119 안내 + 재시도, 빈 항목 되묻기, Q1~Q3 순서와 건너뛰기, 카드 항목 선택과 동의.
- 모든 화면의 "증상이 심해지면 119" 고정 표시, 결과 화면의 기관 최종 결정 문구와 정보 기준일.
- Playwright E2E: 백엔드 응답을 가로채(mock) 데모 흐름을 360px·1440px에서 끝까지 통과.

제외:

- 음성 입력, `/nearby`, `/guide`, `/records` (phase-03·04).
- 기기 저장(언어·동의 기억은 포함, 기록 저장은 phase-03).
- openapi-typescript 생성 타입 연결.
- 디자인 다듬기, 아이콘·일러스트.

## 작업 체크리스트

- [ ] 이름과 proxy 환경 변수를 교체하고 기존 테스트(`tests/dev-proxy.test.ts`, `src/app/routes.test.tsx`, `e2e/smoke.spec.ts`)를 갱신한다.
- [ ] YardPilot 화면을 지우고 새 경로를 연결한다.
- [ ] 언어 파일과 누락 키 검사를 만든다.
- [ ] Zod 스키마와 `fixtures/contract/` 검증 테스트를 작성한다.
- [ ] API 클라이언트를 만든다. 응답 검증 실패를 오류로 처리한다.
- [ ] 고지·동의 화면을 만들고 동의 전 `/triage`·`/summary` 미호출을 테스트한다.
- [ ] 응급 분기와 네트워크 오류 시 119 안내를 테스트한다.
- [ ] 비용 질문 순서·건너뛰기와 결과 화면 문구를 테스트한다.
- [ ] 요약 카드 항목 선택(기본 모두 포함), 뺀 항목이 요청 본문에 없음, 동의 전 미호출을 테스트한다.
- [ ] E2E로 데모 흐름 전체를 확인한다.
- [ ] 아래 완료 조건별 실행 명령·결과를 검증 결과에 기록한다.

## 의존성

- [공통 계약](../../docs/api-contract.md) 3·4·5장, `fixtures/contract/` (백엔드가 만든다: [백엔드 phase-02](../../backend/docs/phase-02.md)). 백엔드 예시 파일이 아직 없으면 계약 문서의 예시로 임시 fixture를 만들고, 백엔드 파일이 생기면 그 파일로 바꾼다.
- 실제 백엔드 연결 확인은 백엔드 phase-02 완료 후 수동 확인으로 기록한다.

## 완료 조건

- [ ] typecheck, lint, test, build, check:dist, test:e2e가 모두 통과한다.
- [ ] `frontend/` 코드와 설정에 `YARDPILOT`·`yardpilot`·`vehicle`·`driver`·`control` 같은 이전 프로젝트 이름이 남지 않는다(phase-01 기록 문서 제외).
- [ ] 응급 응답과 네트워크 오류 모두에서 119 안내가 다른 화면보다 먼저 보인다.
- [ ] 동의 전에는 `/triage`·`/summary` 요청이 나가지 않는다.
- [ ] 요약 카드 요청에 뺀 항목이 들어가지 않는다.
- [ ] 비자·체류 자격, 이름·소속·사업장명 입력란이 없다.
- [ ] 360px에서 데모 흐름 E2E가 통과한다.

## 검증 결과

아직 구현 전.
