# 01. API 호출 계층과 증상 입력(추출·응급 판정) 전환

상태: 완료
의존: 없음(backend 구현 순서 1~6, backend 01 오류 형식 완료)

## 목표
`VITE_API_BASE`가 있으면 API를, 없으면 지금 브라우저 함수를 쓰는 `src/api/` 계층을 만들고, 증상 입력 화면(S-05)의 자유 입력 추출과 응급 판정을 그 계층으로 옮긴다. 응급 판정은 네트워크 때문에 119 안내가 늦어지지 않는 것을 가장 먼저 지킨다. 이후 화면 전환(02, 03)은 이 항목이 만든 계층 위에 얹는다.

## 범위
- 하는 것
  - `vite.config.ts`: `server.proxy: { '/api': 'http://localhost:8000' }`. 맨 위 "백엔드 없이" 주석을 두 모드에 맞게 고친다
  - `src/vite-env.d.ts`: `ImportMetaEnv`에 `VITE_API_BASE?: string`
  - `src/api/http.ts`: `VITE_API_BASE`를 읽는 `isApiMode()`, JSON 요청 함수(시간 제한은 `AbortController`). 실패하면 `ApiError`(`code`, `requestId`, 상태 코드)를 던진다. 오류 본문은 `backend/README.md` "오류 형식"을 읽고, 요청 본문·응답 원문은 `console`에 찍지 않는다
  - `src/api/worker.ts`
    - `checkTriage(intake)`: 브라우저 `triage()`를 먼저 돌려 **응급이면 API를 기다리지 않고 바로 돌려준다.** 응급이 아니고 API 모드면 `POST /api/triage`를 부르고, 실패하거나 시간 제한(`TRIAGE_TIMEOUT_MS`, 3초)을 넘기면 브라우저 결과를 돌려준다. API 결과가 응급이면 응급이다
    - `extract(intake)`: 단독 모드는 브라우저 함수, API 모드는 `POST /api/extract`(`EXTRACT_TIMEOUT_MS`, 8초). 실패하면 브라우저 함수로 대체한다(메모 참고). 돌려주는 형태는 두 모드 모두 `{ extraction, intake, filled }`
  - `src/domain/triage.ts`: `Intake.tsx` 안의 `filled` 판단을 `extractIntake(intake)`(→ `{ extraction, intake, filled }`)로 옮긴다. 기존 함수의 동작은 바꾸지 않는다
  - `src/pages/worker/Intake.tsx`: `triage`·`extractFromText`·`mergeExtraction` 직접 호출을 `src/api/worker.ts`로 바꾼다. `goNext`를 비동기로 바꾸고, 기다리는 동안 다음 버튼을 막아 두 번 눌리지 않게 한다
  - `README.md` "실행"에 API 모드 실행 명령을 더한다
- 하지 않는 것
  - 제도 경로·접수 도우미·리포트·`/api/meta` 전환(02), 센터 화면 전환(03)
  - 새 문구 키 추가(대기 중 표시는 버튼 비활성만 쓴다), 모델 결과(`TriageResult.model`) 표시
  - CI `frontend` 작업(`chore/`), 백엔드 코드 수정

## 화면·파일
- 화면: S-05 `/intake` → S-06 `/emergency` / S-07 `/result`. 경로·화면 구성 변경 없음
- API: `POST /api/triage`, `POST /api/extract` (요청·응답은 `backend/README.md` 예시 그대로)
- 추가: `src/api/http.ts`, `src/api/worker.ts`, `src/vite-env.d.ts`
- 수정: `vite.config.ts`, `src/domain/triage.ts`, `src/pages/worker/Intake.tsx`, `README.md`

## 완료 기준
- [x] `npm run build` 통과
- [x] 단독 모드(`npm run dev`): 개발자 도구 네트워크 탭에 `/api` 요청이 없고, 손 + 베인 상처 + 출혈 → `/result`에 외과·정형외과, 가슴 + 통증 → `/emergency`로 지금과 같이 동작한다
- [x] API 모드(백엔드 켬, `VITE_API_BASE=/api npm run dev`): 위 두 입력에서 비응급 입력은 `/api/triage`가 불리고 결과가 같다. 가슴 + 통증은 `/api/triage` 응답을 기다리지 않고 `/emergency`로 간다. 자유 입력 `"Ngón tay bị kẹp vào máy dập, bị sưng."`이 `/api/extract`를 거쳐 손·부음·업무 중으로 채워진다
- [x] API 모드(백엔드 끔): 같은 입력이 단독 모드와 같은 화면으로 간다
- [x] API 모드(응답하지 않는 서버, `nc -lk 8000`): 비응급 입력이 3초 안팎에 브라우저 결과로 `/result`에 가고, 가슴 + 통증은 기다림 없이 `/emergency`로 간다. 기다리는 동안 다음 버튼이 눌리지 않는다
- [x] 위 확인을 en·vi·ko에서 한 번씩 했다
- [x] `domain/triage.ts`를 고친 뒤 `parity.json`을 다시 만들면 diff가 없고, `backend`에서 `uv run pytest`가 통과한다

## 결과
2026-10-28, 브랜치 `frontend/api-client-intake`.

실행 명령 → 결과

- `cd frontend && npm run build` → 통과(tsc + vite build)
- `npx rolldown scripts/dump-fixtures.ts … > ../backend/tests/fixtures/parity.json` → `generatedAt` 시각만 바뀌고 내용 diff 없음. `extractIntake`는 기존 `extractFromText`·`mergeExtraction`을 그대로 부르므로 기대값이 바뀌지 않는다. 시각만 다른 파일은 커밋하지 않았다
- `cd backend && uv run pytest` → 1008 passed

브라우저 확인(Playwright headless Chromium, 360×640, en·vi·ko 각 언어에서 아래 표를 한 번씩). Claude in Chrome 확장이 연결되지 않아 스크립트로 확인했고, 사람 눈으로 본 스크린샷은 없다. 언어·동의·이용 방식은 `sessionStorage`에 넣고 `/intake`부터 시작했다.

| 상황 | 손 + 베인 상처 + 출혈 | 가슴 + 통증 | 자유 입력 `"Ngón tay bị kẹp vào máy dập, bị sưng."` |
|---|---|---|---|
| 단독(`npm run dev`) | `/result` 외과·정형외과, `/api` 요청 없음 | 2단계(증상)에서 바로 `/emergency`, 요청 없음 | 서버 없이 손·부음·업무 중·기계(`machine`) 채움, 추출 안내 줄 표시 |
| API, 백엔드 켬 | `POST /api/triage` 200 한 번, 결과 같음 | `/emergency`, `/api/triage`를 부르지 않음 | `POST /api/extract` 200 → 같은 값(`source: keywords`) |
| API, 백엔드 끔 | `/api/triage` 502(Vite 프록시) → 즉시 브라우저 결과로 `/result` | 같음 | `/api/extract` 502 → 브라우저 사전, 같은 값 |
| API, 응답 없음(`nc -lk 8000`) | 3.04초 뒤 `TIMEOUT` → 브라우저 결과로 `/result`. 기다리는 동안 다음·이전 버튼 `disabled` | 기다림 없이 `/emergency` | 8.5초 뒤 `TIMEOUT` → 브라우저 사전, 같은 값 |

콘솔에는 대체했을 때 `[api] /triage TIMEOUT → 브라우저 함수로 대체` 한 줄만 남고 요청·응답 본문은 없다. 하단 119 띠와 `/emergency`의 전화 버튼은 네 경우 모두 그대로다.

결정 사항

- **서버는 마지막 단계에서 한 번만 부른다.** 2단계(증상 고른 뒤)와 3단계(추출 뒤)의 응급 선별은 `screenEmergency()`(브라우저 규칙만)이고, 4단계 "결과 보기"에서만 `checkTriage()`가 서버를 부른다. 단계마다 서버를 부르면 응답 없는 서버에서 3초가 세 번 쌓이고, 응급 화면으로 가는 길에 비동기 호출이 생기기 때문이다(README "비동기 UX 규칙")
- 자유 입력이 비어 있으면 `extract()`가 서버를 부르지 않고 브라우저 함수를 쓴다. "건너뛰기"가 응답 없는 서버에서 8초를 기다리지 않게 하기 위해서다
- 기다리는 동안 다음 버튼과 함께 **이전 버튼도** `disabled`로 둔다. 기다리는 중에 단계를 바꾸면 늦게 온 응답이 다른 단계에 적용되기 때문이다. 스피너·문구는 없다
- 서버 `/api/triage` 결과는 `{ ...브라우저 결과, ...서버 결과 }`로 합쳐 서버가 더하는 선택 필드(`model` 등)가 그대로 `AppState`에 실린다. `emergency`가 boolean이 아니거나 `department` 키가 없으면 `BAD_RESPONSE`로 보고 브라우저 결과를 쓴다. `/api/extract`는 `extraction`·`intake`·`filled`가 없으면 같은 처리다
- `domain/triage.ts`에 `ExtractResult`(`{ extraction, intake, filled, source? }`)와 `extractIntake()`를 더했다. `source`는 서버 전용 선택 필드로 타입에만 두고 화면에는 쓰지 않는다(새 문구 키 없음). `TriageResult.model` 타입은 backend 06이 형태를 정하지 않아 더하지 않았다
- `README.md`는 PR #50(`docs/frontend-design`)의 내용을 그대로 가져왔다. "실행" 절의 API 모드 명령이 거기에 이미 있다. 이 문서의 `## 메모`도 PR #50과 같아 두 PR을 어느 순서로 병합해도 충돌하지 않는다

02·03에 넘기는 것

- `http.ts`: `isApiMode()`, `requestJson<T>(path, { method?, body?, timeoutMs })`(GET은 `body` 없이), `ApiError(code, status, requestId)`, `logFallback(path, e)`. 센터 경로처럼 대체하지 않는 곳은 `requestJson`의 `ApiError`를 그대로 화면에 전달하면 된다. 쓰기 어렵게 만든 점은 없다

남은 문제

- `nc -lk 8000`을 터미널이 아닌 곳(stdin이 닫힌 백그라운드)에서 띄우면 연결을 바로 끊어 502가 나고 시간 제한을 확인할 수 없다. 터미널에서 직접 띄우거나 `tail -f /dev/null | nc -lk 8000`으로 띄운다

## 메모
- 01~03을 합친 것이 `backend/README.md` "구현 순서" 7번(`src/api/` 전환, Vite 프록시)이다. 백엔드 문서가 "frontend 항목 7"이라고 부르는 것이 이것이며, backend 08(같은 출처 서빙)은 03까지 끝난 뒤에 할 수 있다
- 뒤이을 항목은 `02-api-worker-rest.md`(근로자 나머지 경로, 조용한 대체)와 `03-api-center.md`(센터 경로, 대체 없음)에 적었다(2026-10-28). 경로별 실패 동작은 `README.md` "경로별 대체 정책" 표가 기준이다
- 이 항목이 만든 `http.ts`의 `ApiError`·시간 제한 방식은 02·03이 그대로 쓴다. 02·03에서 쓰기 어렵게 만들었다면 이 항목의 `## 결과`에 적는다
- 추출 실패 시 브라우저 함수로 대체하는 것은 사용자 확인을 받았다(2026-10-28). 추출이 실패해 증상 입력이 멈추면 그 뒤의 응급 판정까지 늦어지기 때문이다. `backend/README.md` "프론트 전환 방법"도 같이 고쳤다
- 시간 제한 값(3초, 8초)은 `src/api/worker.ts` 상수로 둔다. backend 03(추출 LLM)이 붙으면 서버 쪽 LLM 시간 제한(10초 × 2회)보다 짧아 프론트가 먼저 포기하게 된다. 그때 추출 시간 제한을 다시 정한다
- 서버가 돌려준 `TriageResult.model`(backend 06)은 이 항목에서 그대로 `AppState`에 넣기만 하고 화면에 보이지 않는다
