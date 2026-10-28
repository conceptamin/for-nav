# 02. 근로자 나머지 경로 전환(제도 경로·접수 도우미·리포트·메타)

상태: 완료
의존: 01

## 목표
01이 만든 `src/api/` 계층 위에 근로자 화면의 나머지 경로를 얹는다. 제도 경로(S-08), 접수 도우미(S-09·S-10), 의료진 리포트(S-11), 센터 요약 미리보기(S-12), 그리고 앱 시작 시 `/api/meta`다. 이 경로들은 서버 결과와 브라우저 결과가 같으므로, 실패하면 **조용히 브라우저 함수로 대체**하고 사용자에게 알리지 않는다(`README.md` "경로별 대체 정책"). 백엔드가 나중에 더하는 선택 필드(`llmSlots`, `translation`)를 받을 자리도 함께 만든다.

## 범위
- 하는 것
  - `src/api/worker.ts`에 추가. 모두 단독 모드는 브라우저 함수, API 모드는 서버를 부르고 실패·시간 초과(`TEMPLATE_TIMEOUT_MS`, 8초)면 브라우저 함수로 대체한다. 돌려주는 형태는 두 모드에서 같다
    - `routeCoverage(input)` → `POST /api/route`
    - `buildVisitHelper(intake, department, firstVisit, lang)` → `POST /api/visit-helper`. 두 모드 모두 `{ desk, call }`
    - `buildClinicianReport(...)` → `POST /api/report/clinician`
    - `buildCenterSummary(input)` → `POST /api/report/center`
  - `src/api/meta.ts`: `loadMeta()` → `GET /api/meta`(시간 제한 3초). 실패하면 `domain/coverage.ts`의 `INFO_DATE`·`CENTER_HOURS`. 단독 모드는 부르지 않는다
  - `src/state/AppState.tsx`: `meta: { infoDate, centerHours }`를 컨텍스트에 더한다(저장소에 쓰지 않는 메모리 값, 기본은 브라우저 상수). `AppStateProvider`가 시작 시 한 번 `loadMeta()`를 부른다
  - `src/domain/coverage.ts`: `isAfterHours(date, hours = CENTER_HOURS)`, `nextOpenDay(date, hours = CENTER_HOURS)`처럼 운영 시간을 인자로 받되 기본값을 두어 동작과 `parity.json`이 바뀌지 않게 한다
  - `src/domain/*.ts` 타입에 선택 필드 추가: `DeskSheet`·전화 스크립트 결과·`ClinicianReport`에 `llmSlots?: string[]`, `ClinicianReport`와 센터 요약 결과에 `translation?: { status: 'ok' | 'rejected' | 'skipped' }`. 화면은 이번 항목에서 이 필드를 보지 않는다
  - S-05 추출 대체 알림: 01이 미뤄 둔 "키워드 사전으로 채움" 한 줄을 `notice.info`로 더한다. `source`가 `keyword`일 때만, API 모드에서만 보인다. 문구 키 `extractFallback`(en·vi·ko)
  - 화면 수정: `Coverage.tsx`, `Visit.tsx`, `Report.tsx`, `CenterRequest.tsx`(미리보기와 `INFO_DATE`·운영 시간 외 판정을 `meta`로), `Intake.tsx`(알림 한 줄). 기다리는 동안 해당 버튼만 `disabled`. 결과가 오기 전 화면이 비는 것은 허용하지 않는다: 호출은 버튼을 누른 시점에 하고, 이미 보여 주던 화면은 유지한다
  - `README.md` "비동기 UX 규칙"의 시간 제한 줄에 이 항목이 정한 값을 적는다
- 하지 않는 것
  - 센터 경로(03), `llmSlots`·`translation` 값을 화면에 표시(백엔드 04·05 이후 별도 항목), 모델 결과 표시
  - 새 UI 조각. 알림은 기존 `notice.info`, 대기는 `disabled`만
  - 백엔드 코드 수정. `/api/meta` 응답 형태는 `backend/README.md` 그대로 쓴다

## 화면·파일
- 화면: S-05(`/intake` 알림 한 줄), S-08 `/coverage`, S-09 `/visit/desk`, S-10 `/visit/call`, S-11 `/report/new`·`/report/:id`, S-12 `/center-request` 미리보기. 경로·구성 변경 없음
- API: `GET /api/meta`, `POST /api/route`, `POST /api/visit-helper`, `POST /api/report/clinician`, `POST /api/report/center`
- 추가: `src/api/meta.ts`
- 수정: `src/api/worker.ts`, `src/state/AppState.tsx`, `src/domain/coverage.ts`, `src/domain/templates.ts`(선택 필드), `src/pages/worker/{Coverage,Visit,Report,CenterRequest,Intake}.tsx`, `src/i18n/{en,vi,ko}.ts`, `README.md`
- 새 문구 키: `extractFallback`

## 완료 기준
- [x] `npm run build` 통과
- [x] 단독 모드: 네트워크 탭에 `/api` 요청이 없고, S-08~S-12가 지금과 같이 동작한다. S-05 알림 줄이 보이지 않는다
- [x] API 모드(백엔드 켬): `backend/README.md`의 `/api/route` 예시 입력(업무 관련 모름, 보험 없음, 울산 90일 예)에서 S-08 화면이 단독 모드와 같다. S-09·S-10·S-11의 한국어 문장이 단독 모드와 글자 단위로 같다(세 언어)
- [x] API 모드(백엔드 끔): 같은 입력에서 같은 화면이 뜨고 오류 문구가 없다
- [x] API 모드(응답하지 않는 서버, `nc -lk 8000`): S-08·S-09가 8초 안팎에 브라우저 결과로 뜨고, 기다리는 동안 버튼이 눌리지 않는다
- [x] 백엔드를 `CENTER_HOURS=10:00-17:00 INFO_DATE=2026-11-01`로 띄우면 S-08의 기준일과 S-12의 운영 시간 외 안내가 그 값을 따른다. 백엔드를 끄면 브라우저 상수로 돌아간다
- [x] API 모드에서 자유 입력 추출이 서버 키워드 사전으로 채워졌을 때(`LLM_API_KEY` 없이 띄움) S-05에 `extractFallback` 한 줄이 보이고, LLM이 채웠을 때는 보이지 않는다
- [x] `domain/coverage.ts`를 고친 뒤 `parity.json`을 다시 만들면 diff가 없고, `backend`에서 `uv run pytest`가 통과한다
- [x] 위 확인을 en·vi·ko에서 한 번씩 했다

## 결과
2026-10-29, 브랜치 `frontend/api-worker-rest`.

실행 명령 → 결과

- `cd frontend && npm run build` → 통과(tsc + vite build)
- `npx rolldown scripts/dump-fixtures.ts … > ../backend/tests/fixtures/parity.json` → `generatedAt`만 바뀌고 내용 diff 없음. `routeCoverage`·`isAfterHours`·`nextOpenDay`의 새 인자는 기본값이 지금 상수라 기대값이 바뀌지 않는다. 시각만 다른 파일은 커밋하지 않았다
- `cd backend && uv run pytest` → 1019 passed

브라우저 확인(Playwright headless Chromium, 360×640, `Asia/Seoul`, en·vi·ko 각각). Claude in Chrome 확장 없이 스크립트로 확인했다. 언어·동의·회원 프로필·증상 입력(손 + 베인 상처 + 출혈, 오늘, 업무 중, 자유 입력 있음)을 저장소에 넣고 시작했다. 단독 모드는 5191, API 모드는 5190 포트로 띄웠다(5180은 다른 프로세스가 쓰고 있었다).

| 상황 | S-08~S-12 화면 글자(단독과 비교) | `/api` 요청 | 그 밖 |
|---|---|---|---|
| 단독 | 기준 | 없음 | S-05 대체 줄 없음 |
| API, 백엔드 켬 | S-08 결과, S-09 초진·재진, S-10, S-11 리포트 행, S-12 미리보기 6개 모두 같음(세 언어) | `/meta`·`/route`·`/visit-helper`·`/report/clinician`·`/report/center` 모두 200 | 오류 문구 없음 |
| API, 백엔드 끔 | 6개 모두 같음 | 전부 502(Vite 프록시) | 오류 문구 없음. 콘솔에는 `[api] /route INTERNAL 502 → 브라우저 함수로 대체`처럼 경로·code만 |
| API, 응답 없는 서버 | 6개 모두 같음 | 시간 제한으로 끊김 | S-08 결과가 클릭 후 약 50ms에 보인다. S-11 리포트는 8.05초 뒤 브라우저 리포트로 넘어가고, 기다리는 동안 만들기 버튼이 `disabled`다 |

- 서버 결과가 실제로 화면에 쓰이는지: 서버 응답에 표시를 붙여(Playwright `route`) S-08 기준일, S-09·S-10 첫 줄, S-11 첫 행, S-12 미리보기가 서버 값으로 바뀌는 것을 확인했다. S-08은 브라우저 결과가 먼저 보이고 서버 결과가 오면 바뀐다
- `/api/meta`: 백엔드를 `CENTER_HOURS=10:00-17:00 INFO_DATE=2026-11-01`로 띄우고 브라우저 시각을 목요일 09:30(KST)으로 고정했다. S-08과 S-12 미리보기의 기준일이 2026-11-01, S-12 전송 뒤 안내가 "운영 시간 외, 다음 운영일 10월 29일 목요일"이다. 단독 모드와 백엔드를 끈 API 모드에서는 2026-10-24, "지금 운영 중"이다
- S-05 대체 줄: API 모드에서 서버가 키워드 사전으로 채우면(`LLM_API_KEY` 없이 띄움, `source: "keywords"`) 보이고, 백엔드를 꺼 브라우저 사전으로 대체해도 보인다. 단독 모드에서는 보이지 않는다. 360px 베트남어에서 안내 상자 안 한 줄로 넘침 없이 들어간다

결정 사항

- **버튼 없이 바로 뜨는 화면은 브라우저 결과를 먼저 그리고 서버 결과로 바꾼다.** S-08·S-09·S-10·S-12 미리보기는 `src/api/useServerResult.ts`가 같은 입력(key)에서 브라우저 결과를 한 번 계산해 곧바로 그리고, 서버 결과가 오면 바꾼다. 늦게 온 응답이 바뀐 입력을 덮지 않게 key가 같을 때만 쓴다. 이 문서의 범위에 적힌 "결과가 오기 전 화면이 비는 것은 허용하지 않는다"를 지키는 가장 단순한 방법이고, 서버가 멈춰도 기다리는 순간이 없다. 그래서 완료 기준의 "8초 안팎에 브라우저 결과로 뜬다"는 "곧바로 브라우저 결과가 뜬다"로 더 강하게 충족된다. `README.md` "비동기 UX 규칙"에 이 규칙을 적었다
- **버튼을 누르는 S-11 리포트만 서버를 기다린다.** 리포트 id·작성 시각이 저장되므로 결과를 바꿔 끼울 수 없다. 기다리는 동안 만들기 버튼만 막는다
- 운영 시간·기준일은 `AppState`의 `meta`(메모리, 저장하지 않음)에 두고, `domain/coverage.ts` 함수는 인자로 받되 기본값을 지금 상수로 둬 동작과 `parity.json`을 바꾸지 않았다. API 모드에서 S-08 브라우저 결과에도 `meta.infoDate`를 넣어, 서버 결과로 바뀔 때 기준일이 튀지 않게 했다
- S-05 대체 줄은 "API 모드 + 자유 입력 있음 + `source`가 `llm`이 아님"일 때 보인다. 서버 키워드 사전(`keywords`)과 서버 실패 뒤 브라우저 사전(`source` 없음)이 모두 해당한다. design.md의 "안내 상자를 두 개 연달아 쌓지 않는다"에 따라 새 상자를 만들지 않고 기존 추출 안내 상자 안에 `.small` 한 줄로 넣었다
- S-12 미리보기는 회원이 요청 종류를 고른 뒤에만 서버에 보낸다. 비회원 화면에서는 아무것도 보내지 않고, 연락처는 요약 입력에 없어 미리보기 요청에 들어가지 않는다. 전송은 아직 브라우저 저장소이고 운영 시간 판정만 `meta`를 쓴다(서버 전송은 03)
- S-09·S-10은 훅을 조건 없이 부르기 위해 화면을 "진입 확인(리다이렉트)"과 "본문" 두 컴포넌트로 나눴다. 화면 모양은 같다
- `domain/templates.ts`에 서버 전용 선택 필드 타입(`VisitHelper.llmSlots`, `ClinicianReport.llmSlots`·`translation`, `CenterSummary.translation`)과 `CallScript`·`VisitHelper`·`CenterSummary` 타입을 더했다. 화면은 이 필드를 아직 보지 않는다

남은 문제

- 개발 서버(`npm run dev`)에서는 React StrictMode가 effect를 두 번 돌려 화면을 처음 열 때 같은 요청이 두 번 나간다(`/meta`, `/visit-helper`, `/report/center`). 먼저 나간 응답은 버린다. 빌드한 앱에서는 한 번이다
- `nc -lk 8000`은 연결을 하나씩만 받아, `/meta`가 시간 제한으로 끊길 때 함께 기다리던 다른 요청이 502로 끝난다. 응답 없는 서버는 연결을 모두 받고 응답하지 않는 `node -e "require('net').createServer(()=>{}).listen(8000)"`로 확인했다
- "LLM이 채웠을 때 줄이 보이지 않는다"는 실제 LLM 대신 서버 응답의 `source`를 `llm`으로 바꿔(Playwright `route`) 확인했다. 실제 키로는 돌리지 않았다
- backend 04가 붙으면 S-09·S-10 문장이 서버 응답이 올 때 LLM 문장으로 바뀐다(최대 8초 뒤). 기본 템플릿도 완성된 문장이라 틀린 것이 보이는 시간은 없다


## 메모
- 새 문구 키 `extractFallback`(en·vi·ko)을 더했다. 베트남어 "Các câu trả lời này được khớp theo danh sách từ khóa."는 원어민 검수가 필요하다
- 01의 `## 메모`에 적혀 있던 "실패 시 오류 문구 + 다시 시도"는 2026-10-28 토론에서 **조용한 대체**로 바꿨다. 서버 템플릿과 브라우저 템플릿이 같은 문장을 내므로 실패를 알릴 이유가 없고, 알림이 늘면 근로자 화면이 복잡해진다. 백엔드 04·05가 붙어 서버 문장이 더 좋아진 뒤에도, 대체는 "LLM 보강이 빠진 기본 문장"이지 틀린 문장이 아니다
- 01~03을 합친 것이 `backend/README.md` "구현 순서" 7번이다
