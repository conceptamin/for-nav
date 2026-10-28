# 03. 센터 경로 전환(전송·접수함·상세·통계)

상태: 대기
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
- [ ] `npm run build` 통과
- [ ] 단독 모드: `/api` 요청이 없고, 근로자 전송 → 같은 브라우저 다른 탭의 `/center`에 지금처럼 나타난다. 연결 띠가 보이지 않는다
- [ ] API 모드(백엔드 켬): 다른 브라우저 프로필(또는 같은 Wi-Fi의 휴대폰, backend 08 이후)에서 전송한 사례가 PC `/center` 맨 위에 2초 안에 `live` 칩과 함께 나타나고, 상세의 요약·긴급도가 `backend/README.md`의 `POST /api/center/cases` 예시와 같은 규칙으로 계산되어 있다
- [ ] API 모드에서 전송 뒤 `localStorage`의 `umn.center.liveCases`가 비어 있다(개발자 도구로 확인)
- [ ] API 모드(백엔드 끔): 전송하면 `sendFailed` 문구와 다시 시도 버튼이 보이고 입력값이 남아 있다. 백엔드를 켜고 다시 시도하면 성공한다
- [ ] API 모드에서 센터 화면을 연 채 백엔드를 끄면 5초 안팎에 연결 띠가 뜨고 표는 마지막 목록을 유지한다. 다시 켜면 띠가 사라진다
- [ ] 상태 변경·데모 초기화가 서버에 반영되고(`curl GET /api/center/cases`로 확인), 실패 시 다시 시도 버튼이 보인다
- [ ] C-03에서 서버가 `null`로 준 칸이 `<5`로 보이고, 네트워크 탭에 원천 레코드 요청이 없다
- [ ] 센터 화면을 1280px과 900px 아래에서 보았을 때 연결 띠가 표를 가리지 않는다

## 결과

## 메모
- 센터 경로를 대체하지 않기로 한 결정은 2026-10-28 토론에서 확인했다. 센터 화면의 목적이 "다른 기기에서 온 사례가 보이는 것"이므로 localStorage 대체는 시연에서 거짓이 된다
- 폴링을 유지하는 이유: 사례 수가 적어 전체 목록을 2초마다 받아도 되고, SSE는 backend 08(같은 출처 서빙)과 프록시 설정이 얽힌다. 발표 뒤에도 필요하면 별도 항목
- 새 문구 키의 베트남어는 원어민 검수가 필요하다
- 이 항목이 끝나면 `backend/README.md` "구현 순서" 7번이 완료되고 backend 08을 시작할 수 있다
