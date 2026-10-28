# 01. API 호출 계층과 증상 입력(추출·응급 판정) 전환

상태: 대기
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
- [ ] `npm run build` 통과
- [ ] 단독 모드(`npm run dev`): 개발자 도구 네트워크 탭에 `/api` 요청이 없고, 손 + 베인 상처 + 출혈 → `/result`에 외과·정형외과, 가슴 + 통증 → `/emergency`로 지금과 같이 동작한다
- [ ] API 모드(백엔드 켬, `VITE_API_BASE=/api npm run dev`): 위 두 입력에서 비응급 입력은 `/api/triage`가 불리고 결과가 같다. 가슴 + 통증은 `/api/triage` 응답을 기다리지 않고 `/emergency`로 간다. 자유 입력 `"Ngón tay bị kẹp vào máy dập, bị sưng."`이 `/api/extract`를 거쳐 손·부음·업무 중으로 채워진다
- [ ] API 모드(백엔드 끔): 같은 입력이 단독 모드와 같은 화면으로 간다
- [ ] API 모드(응답하지 않는 서버, `nc -lk 8000`): 비응급 입력이 3초 안팎에 브라우저 결과로 `/result`에 가고, 가슴 + 통증은 기다림 없이 `/emergency`로 간다. 기다리는 동안 다음 버튼이 눌리지 않는다
- [ ] 위 확인을 en·vi·ko에서 한 번씩 했다
- [ ] `domain/triage.ts`를 고친 뒤 `parity.json`을 다시 만들면 diff가 없고, `backend`에서 `uv run pytest`가 통과한다

## 결과

## 메모
- 01~03을 합친 것이 `backend/README.md` "구현 순서" 7번(`src/api/` 전환, Vite 프록시)이다. 백엔드 문서가 "frontend 항목 7"이라고 부르는 것이 이것이며, backend 08(같은 출처 서빙)은 03까지 끝난 뒤에 할 수 있다
- 뒤이을 항목(이 항목이 끝나면 문서로 쓴다)
  - 02 근로자 나머지 경로: `/api/route`(S-08), `/api/visit-helper`(S-09·S-10), `/api/report/clinician`(S-11), `/api/report/center`(S-12 미리보기), `/api/meta`. 실패 시 오류 문구 + 다시 시도. 새 문구 키가 생기므로 베트남어 원어민 검수 필요
  - 03 센터 경로: `POST /api/center/cases`(S-12 전송), `GET`(2초 주기)·`PATCH /api/center/cases`, `POST /api/center/reset`, `GET /api/center/stats`(집계만 그림). API 모드에서 `storage` 이벤트 갱신을 끈다
- 추출 실패 시 브라우저 함수로 대체하는 것은 사용자 확인을 받았다(2026-10-28). 추출이 실패해 증상 입력이 멈추면 그 뒤의 응급 판정까지 늦어지기 때문이다. `backend/README.md` "프론트 전환 방법"도 같이 고쳤다
- 시간 제한 값(3초, 8초)은 `src/api/worker.ts` 상수로 둔다. backend 03(추출 LLM)이 붙으면 서버 쪽 LLM 시간 제한(10초 × 2회)보다 짧아 프론트가 먼저 포기하게 된다. 그때 추출 시간 제한을 다시 정한다
- 서버가 돌려준 `TriageResult.model`(backend 06)은 이 항목에서 그대로 `AppState`에 넣기만 하고 화면에 보이지 않는다
