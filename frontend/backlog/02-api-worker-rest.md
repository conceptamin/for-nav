# 02. 근로자 나머지 경로 전환(제도 경로·접수 도우미·리포트·메타)

상태: 대기
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
- [ ] `npm run build` 통과
- [ ] 단독 모드: 네트워크 탭에 `/api` 요청이 없고, S-08~S-12가 지금과 같이 동작한다. S-05 알림 줄이 보이지 않는다
- [ ] API 모드(백엔드 켬): `backend/README.md`의 `/api/route` 예시 입력(업무 관련 모름, 보험 없음, 울산 90일 예)에서 S-08 화면이 단독 모드와 같다. S-09·S-10·S-11의 한국어 문장이 단독 모드와 글자 단위로 같다(세 언어)
- [ ] API 모드(백엔드 끔): 같은 입력에서 같은 화면이 뜨고 오류 문구가 없다
- [ ] API 모드(응답하지 않는 서버, `nc -lk 8000`): S-08·S-09가 8초 안팎에 브라우저 결과로 뜨고, 기다리는 동안 버튼이 눌리지 않는다
- [ ] 백엔드를 `CENTER_HOURS=10:00-17:00 INFO_DATE=2026-11-01`로 띄우면 S-08의 기준일과 S-12의 운영 시간 외 안내가 그 값을 따른다. 백엔드를 끄면 브라우저 상수로 돌아간다
- [ ] API 모드에서 자유 입력 추출이 서버 키워드 사전으로 채워졌을 때(`LLM_API_KEY` 없이 띄움) S-05에 `extractFallback` 한 줄이 보이고, LLM이 채웠을 때는 보이지 않는다
- [ ] `domain/coverage.ts`를 고친 뒤 `parity.json`을 다시 만들면 diff가 없고, `backend`에서 `uv run pytest`가 통과한다
- [ ] 위 확인을 en·vi·ko에서 한 번씩 했다

## 결과

## 메모
- 01의 `## 메모`에 적혀 있던 "실패 시 오류 문구 + 다시 시도"는 2026-10-28 토론에서 **조용한 대체**로 바꿨다. 서버 템플릿과 브라우저 템플릿이 같은 문장을 내므로 실패를 알릴 이유가 없고, 알림이 늘면 근로자 화면이 복잡해진다. 백엔드 04·05가 붙어 서버 문장이 더 좋아진 뒤에도, 대체는 "LLM 보강이 빠진 기본 문장"이지 틀린 문장이 아니다
- 새 문구 키 `extractFallback`의 베트남어는 원어민 검수가 필요하다
- 01~03을 합친 것이 `backend/README.md` "구현 순서" 7번이다
