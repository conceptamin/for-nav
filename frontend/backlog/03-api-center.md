# 03. 센터 경로 전환(전송·접수함·상세·통계)

상태: 완료
의존: 01 (02와는 독립이지만 번호 순서대로 한다)

## 목표
센터 접수함을 localStorage 대신 서버에서 읽고 써서, **다른 기기(휴대폰)에서 보낸 사례가 PC의 센터 화면에 2초 안에 나타나는** 시연을 가능하게 한다. 센터 경로는 실패하면 대체하지 않는다. localStorage로 대체하면 도착한 것처럼 보이는 가짜 성공이 되므로, 전송 실패와 서버 끊김을 그대로 보인다(`README.md` "경로별 대체 정책").

## 범위
- 하는 것
  - `src/api/center.ts`: `sendCase(body)` → `POST /api/center/cases`, `listCases()` → `GET /api/center/cases`, `getCase(id)`, `setCaseStatus(id, status)` → `PATCH`, `resetDemo()` → `POST /api/center/reset`, `getStats(days, district)` → `GET /api/center/stats`. 단독 모드는 지금 `centerStore`·`data/mock.ts` 집계를 그대로 부른다. 시간 제한 `CENTER_TIMEOUT_MS` 5초. 실패하면 `ApiError`를 그대로 던진다(대체하지 않는다)
  - `src/state/centerStore.ts`의 `useCenterCases()`를 `src/api/center.ts`의 `useCenterCases()`로 옮긴다. API 모드: 2초 주기로 `listCases()`를 부르고, `storage`·`umn-center-change` 이벤트는 듣지 않는다. 돌려주는 값에 연결 상태를 더한다: `{ cases, connected: boolean, lastUpdated: string | null }`. 실패하면 `connected: false`로 바꾸고 `cases`는 마지막 성공 값을 유지한다. 단독 모드는 `connected: true`
  - `CenterLayout`: `connected`가 `false`면 `.c-header` 아래 가로 띠 "서버 연결 안 됨 · 마지막 갱신 HH:MM"(`design.md` "로딩과 실패를 그리는 법"). 클래스 `c-offline`(warn 배경)을 `styles.css` 센터 섹션에 더하고 `design.md` 센터 표에 한 줄 적는다
  - S-12 전송(`CenterRequest.tsx`): API 모드는 `sendCase()`의 응답 `case`·`nextOpenDate`를 보여 주고 `myCaseIds`에 넣는다. 실패하면 `notice.danger` + 바로 옆 "다시 시도"(`btn secondary`). 입력값은 유지한다. localStorage `umn.center.*`에는 쓰지 않는다. 요약·긴급도·운영 시간 외 여부는 서버가 계산한 값을 쓰고 브라우저에서 다시 계산한 값으로 덮지 않는다
  - C-02 상태 변경·C-01 데모 초기화: 실패하면 그 자리에 `notice.danger` 한 줄 + 다시 시도. 성공하면 다음 폴링을 기다리지 않고 바로 다시 읽는다
  - C-03 통계: API 모드는 `getStats()`의 집계를 그대로 그린다. `null` 칸은 지금처럼 `<5`. 원천 레코드를 받지 않는다. 기간·구군 필터는 쿼리로 보낸다
  - 문구 키: `sendFailed`, `retry`(근로자 화면, en·vi·ko). 센터 화면 띠·실패 문구는 한국어 고정이므로 `domain/`의 `*_KO` 표 또는 컴포넌트 안 한국어 상수
- 하지 않는 것
  - SSE·WebSocket(2초 폴링 유지), 오프라인 큐·재전송, 센터 화면 로그인
  - 모델 결과(`TriageResult.model`) 상세 표시, SHAP(백엔드 06 이후 별도 항목)
  - 백엔드 코드 수정. 통계 응답 형태는 `backend/README.md` 그대로 쓴다

## 화면·파일
- 화면: S-12 `/center-request`(전송 결과·실패), C-01 `/center`, C-02 `/center/cases/:id`, C-03 `/center/stats`. 경로 변경 없음, C-01~C-03 상단에 연결 띠 추가
- API: `POST /api/center/cases`, `GET /api/center/cases`, `GET /api/center/cases/{id}`, `PATCH /api/center/cases/{id}`, `POST /api/center/reset`, `GET /api/center/stats`
- 추가: `src/api/center.ts`
- 수정: `src/state/centerStore.ts`(단독 모드 구현만 남김), `src/pages/center/Center.tsx`, `src/pages/worker/CenterRequest.tsx`, `src/styles.css`(`.c-offline`), `src/i18n/{en,vi,ko}.ts`, `design.md`(센터 표 한 줄), `README.md`(시간 제한 값)
- 새 문구 키: `sendFailed`, `retry`

## 완료 기준
- [x] `npm run build` 통과
- [x] 단독 모드: `/api` 요청이 없고, 근로자 전송 → 같은 브라우저 다른 탭의 `/center`에 지금처럼 나타난다. 연결 띠가 보이지 않는다
- [x] API 모드(백엔드 켬): 다른 브라우저 프로필(또는 같은 Wi-Fi의 휴대폰, backend 08 이후)에서 전송한 사례가 PC `/center` 맨 위에 2초 안에 `live` 칩과 함께 나타나고, 상세의 요약·긴급도가 `backend/README.md`의 `POST /api/center/cases` 예시와 같은 규칙으로 계산되어 있다
- [x] API 모드에서 전송 뒤 `localStorage`의 `umn.center.liveCases`가 비어 있다(개발자 도구로 확인)
- [x] API 모드(백엔드 끔): 전송하면 `sendFailed` 문구와 다시 시도 버튼이 보이고 입력값이 남아 있다. 백엔드를 켜고 다시 시도하면 성공한다
- [x] API 모드에서 센터 화면을 연 채 백엔드를 끄면 5초 안팎에 연결 띠가 뜨고 표는 마지막 목록을 유지한다. 다시 켜면 띠가 사라진다
- [x] 상태 변경·데모 초기화가 서버에 반영되고(`curl GET /api/center/cases`로 확인), 실패 시 다시 시도 버튼이 보인다
- [x] C-03에서 서버가 `null`로 준 칸이 `<5`로 보이고, 네트워크 탭에 원천 레코드 요청이 없다
- [x] 센터 화면을 1280px과 900px 아래에서 보았을 때 연결 띠가 표를 가리지 않는다

## 결과

2026-10-29. `frontend/api-center` 브랜치. 02(PR 60) 위에 쌓았다(S-12 화면을 둘 다 고친다).

| 확인 | 결과 |
|---|---|
| `npm run build` | 통과 |
| 동기화 기대값 재생성 | 생성 시각 외 차이 없음(`domain/centerCase.ts`에는 타입·상수만 더했다) |
| 백엔드 `uv run pytest` | 1019 passed |
| 단독: `/api` 요청 | 0건(전송·접수함·통계 모두) |
| 단독: 같은 브라우저 다른 탭 도착 | 바로(이벤트), 맨 위 + `실제 전송` 칩, 띠 없음 |
| API 켬: 저장소가 분리된 다른 브라우저 컨텍스트에서 전송 → PC `/center` 도착 | 1.7초, 맨 위 + `실제 전송` 칩 |
| API 켬: 상세 긴급도 | 응급 이력 없음 + 업무 중 + 보험 없음 → `▲▲ 높음`, 근거 "업무 중 발생, 건강보험증 없음". 요약은 서버 `summaryKo`와 같다 |
| API 켬: 전송 뒤 `localStorage` | `umn.center.liveCases`·`statusOverrides` 없음(근로자·센터 둘 다). `myCaseIds`에 서버 id |
| API 켬: 상태 변경·데모 초기화 | 서버 `GET`으로 `progress`, 초기화 뒤 24건·live 0건. 화면은 0.1초 안에 다시 읽음 |
| API 켬: C-03 | 30일·울주군에서 서버 `null` 칸이 화면 `<5`. 요청은 `GET /api/center/stats?days=&district=`만 |
| API 끔: S-12 전송 | `sendFailed` + 다시 시도, 연락처·요청 종류·동의 유지, `localStorage` 비어 있음. 백엔드를 켜고 다시 시도하면 성공 |
| API 끔: 센터 화면 연 채 끄기 | 띠 1.5~2.0초, 표 행 수 유지. 켜면 2초 안에 띠 사라짐(1280px·880px) |
| API 끔: 초기화·상태 변경·통계 | 각자 `notice.danger` + 다시 시도. 켠 뒤 통계 다시 시도 성공 |
| 응답 없는 서버 | 띠 6.8초(주기 2초 + 시간 제한 5초) |
| 띠 위치 | 1280px·880px 모두 헤더 바로 아래, 표 위. 표를 덮지 않는다 |

정한 것
- 접수함은 모듈 하나가 구독자를 세어 폴링한다(`useSyncExternalStore`). 헤더의 띠와 목록·상세가 요청 하나를 나눠 쓰고, 센터 화면을 떠나면 멈춘다. 요청이 끝난 뒤 2초를 기다리므로 겹치지 않고, 늦게 온 응답이 새 응답을 덮지 않는다.
- 상세(C-02)는 `GET /api/center/cases/{id}` 대신 폴링 목록에서 찾는다. 다른 PC의 상태 변경이 같은 주기로 보이고 요청이 늘지 않는다. 그래서 `getCase`는 만들지 않았다.
- 통계는 두 모드 모두 서버 응답 형태(`CenterStats`)로 그린다. 단독 모드는 브라우저 mock 원천으로 같은 집계·가림을 한다(`getStatsLocal`). 화면은 칸이 `null`인지만 본다.
- 실패 문구와 다시 시도는 `.notice.danger.with-retry` 하나로 근로자·센터가 같이 쓴다.
- 다음 운영일은 서버의 `YYYY-MM-DD`를 한국 시각 정오로 읽어 요일을 그린다. 브라우저 시간대가 달라도 날짜가 밀리지 않는다.
- `requestJson`이 204(데모 초기화)를 본문 없이 받도록 했다.

남은 것
- 응답 없는 서버에서 띠는 7초까지 걸린다. 서버가 꺼진 경우(시연에서 흔한 경우)는 2초 안이다.
- 휴대폰 실기기로는 확인하지 않았다(backend 08 이후). 다른 기기는 저장소가 분리된 브라우저 컨텍스트로 대신했다.
- `backend/README.md` 경로 표의 "프론트 함수" 칸은 옛 이름(`addLiveCase`, `useCenterCases`, `resetCenterDemo`)이다. 백엔드 문서라 이 항목에서 고치지 않았다.

## 메모
- 센터 경로를 대체하지 않기로 한 결정은 2026-10-28 토론에서 확인했다. 센터 화면의 목적이 "다른 기기에서 온 사례가 보이는 것"이므로 localStorage 대체는 시연에서 거짓이 된다
- 폴링을 유지하는 이유: 사례 수가 적어 전체 목록을 2초마다 받아도 되고, SSE는 backend 08(같은 출처 서빙)과 프록시 설정이 얽힌다. 발표 뒤에도 필요하면 별도 항목
- 새 문구 키의 베트남어는 원어민 검수가 필요하다
- 이 항목이 끝나면 `backend/README.md` "구현 순서" 7번이 완료되고 backend 08을 시작할 수 있다
