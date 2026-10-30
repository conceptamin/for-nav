# 25. 근로자·센터 상담 채팅 연결(WebSocket)

상태: 완료
의존: 03 (센터 경로 전환), backend 14 (상담 채팅 WebSocket, PR 98 — 이 브랜치는 병합 전이라 `origin/backend/chat-websocket` 위에 쌓는다)

## 목표
백엔드에 사례별 상담 채팅(`WS /api/center/cases/{id}/chat`, backend 14)이 생겼다. 근로자가 S-12에서 센터로 보낸 뒤 그 자리에서 상담원과 글을 주고받고, 센터 상담원은 C-02 사례 상세에서 같은 방에 붙는다. 단독 모드(`VITE_API_BASE` 없음)에는 서버가 없으므로 채팅을 보이지 않는다.

## 결정이 필요한 것

1. **근로자 채팅이 보이는 곳.** → **A로 결정(2026-10-30).**
   - **A. S-12 전송 완료 화면에만(권장).** 지금 전송 완료 화면은 `CenterRequestPage`의 메모리 상태라, 새로고침하거나 다른 화면에 갔다 오면 사라지고 채팅도 함께 사라진다. 새 경로가 없고 범위가 가장 작다.
   - B. A + S-13 "센터로 보낸 요청" 목록에서 이 세션에 토큰이 있는 사례는 채팅을 펼친다. 새로고침 뒤에도 이어서 쓸 수 있지만 S-13 배치(backlog 12)를 바꾼다.
   - C. 새 경로 `/center-request/:id/chat`. README 화면 구성 표와 PRD 경로에 없는 화면이라 이 항목에서는 하지 않는다.
2. **`chatToken`을 어디에 두나.** → **권장대로 결정(2026-10-30).** 세션(sessionStorage `umn.session`)의 `chatTokens: Record<사례 id, 토큰>`(권장). 토큰은 그 사례 채팅에 붙는 열쇠이므로 탭을 닫으면 사라지는 쪽에 둔다. 사례 id(`myCaseIds`)는 지금처럼 기기 저장소에 남는다. "내 정보 전체 지우기"는 토큰도 지운다.
3. **다시 연결.** → **권장대로 결정(2026-10-30).** 예상하지 못한 끊김(서버 꺼짐, 네트워크)이면 3초 뒤 다시 연결한다. 횟수 제한 없이 화면이 열려 있는 동안 계속한다. `4403`(권한)·`4404`(사례 없음)·`4000`(데모 초기화)이면 다시 연결하지 않고 멈춘 이유를 보인다. 권장: 그대로.

## 범위
- 하는 것
  - `vite.config.ts`: 프록시를 `{ '/api': { target: 'http://localhost:8000', ws: true } }`로 바꾼다
  - `src/api/http.ts`: `wsUrl(path)` — `VITE_API_BASE`(상대 `/api` 또는 절대 주소)를 지금 페이지 기준으로 풀어 `ws:`/`wss:` 주소를 만든다
  - `src/api/chat.ts`(새 파일): `useChat(caseId, auth)` 훅 하나. `auth`는 `{ role: 'worker', token }` 또는 `{ role: 'center' }`
    - `history` 프레임은 목록을 통째로 바꾼다(재접속 때 겹치지 않는다). `message`는 끝에 붙인다(같은 `id`면 무시). `error`(`invalid`)는 "보내지 못함" 표시만 하고 연결은 그대로
    - 돌려주는 값: `{ messages, state: 'connecting' | 'open' | 'reconnecting' | 'stopped', stopReason: 'denied' | 'missing' | 'reset' | null, rejected: boolean, send(text): boolean }`
    - 보낼 때 앞뒤 공백을 지우고 1~1000자만 보낸다(`CHAT_MAX_LEN`). 연결이 열려 있지 않으면 보내지 않고 `false`. 내 메시지도 서버가 되돌려 준 것만 그린다(낙관적 표시 없음, `id`·`at`은 서버 값)
    - 단독 모드에서는 연결하지 않는다. `isChatAvailable()`(= `isApiMode()`)로 화면이 패널 자체를 숨긴다
    - 메시지 본문·토큰을 `console`에 찍지 않는다. 끊김 기록은 닫힘 코드만
  - `src/domain/centerCase.ts`: `ChatMessage`, `ChatRole` 타입과 `NewCaseResponse.chatToken?`(선택 필드)
  - `src/state/AppState.tsx`: 세션에 `chatTokens`, `addMyCase(id, chatToken?)`로 함께 저장. `clearMyData`가 지운다
  - 근로자: `src/components/ChatPanel.tsx`(새 파일) — 근로자·센터가 같이 쓰는 말풍선 목록 + 입력줄. 문구는 props로 받는다(근로자는 i18n, 센터는 한국어 상수)
  - S-12 전송 완료 화면: 운영 시간 안내 아래, 홈 버튼 위에 "센터와 대화" 카드. 토큰이 없으면(단독 모드, 서버가 토큰을 주지 않음) 보이지 않는다
  - C-02 사례 상세: 오른쪽 열 맨 위(상태 변경 위)에 "상담 채팅" 패널. mock 사례(`live: false`)에는 "근로자 토큰이 없는 예시 사례라 근로자는 들어올 수 없습니다" 한 줄을 덧붙인다
  - 상태 줄: 연결 중 / 다시 연결 중 / 멈춤(이유별 문구). 끊긴 동안 입력은 남고 보내기 버튼만 막힌다(README "비동기 UX 규칙")
  - `styles.css` + `design.md`: 채팅 패널(`.chat`) 절을 더한다. 내 말풍선은 끝 쪽 `--brand-2`, 상대 말풍선은 시작 쪽 `--card`, 목록은 높이 제한 + 스크롤, 새 메시지가 오면 맨 아래로. 애니메이션·입력 중 표시 없음. 논리 속성으로 RTL에서 반대편
  - i18n: 새 키를 20개 언어 파일에 모두 넣는다(아래)
  - `README.md`: "경로별 대체 정책" 표에 WS 행, "비동기 UX 규칙"에 다시 연결 3초, "상태의 경계" 표에 `chatTokens`, 화면 구성 S-12·C-02 설명, 폴더 구조(`api/chat`, `components/ChatPanel`)
- 하지 않는 것
  - 메시지 번역(backend 14 "하지 않는 것", README "나중에 붙일 자리")
  - 읽음 표시, 입력 중 표시, 알림, 첨부, 센터 접수함 목록의 새 메시지 배지
  - 센터 로그인, 새 경로, S-13 변경(1번이 B가 아니면)
  - 접수함 2초 폴링을 WebSocket으로 바꾸는 것
  - `backend/` 코드 수정

## 화면·파일
- 화면: S-12 `/center-request`(전송 완료 뒤), C-02 `/center/cases/:id`. 경로 변경 없음
- API: `WS /api/center/cases/{id}/chat?role=worker&token=` / `?role=center`, `POST /api/center/cases` 응답의 `chatToken`
- 추가: `src/api/chat.ts`, `src/components/ChatPanel.tsx`
- 수정: `vite.config.ts`, `src/api/http.ts`, `src/domain/centerCase.ts`, `src/state/AppState.tsx`, `src/pages/worker/CenterRequest.tsx`, `src/pages/center/Center.tsx`, `src/styles.css`, `src/i18n/*.ts`(20개), `design.md`, `README.md`
- 새 문구 키(근로자): `chatTitle`(센터와 대화), `chatIntro`(상담원이 확인하면 여기에 답합니다. 번역 없이 그대로 전달됩니다), `chatEmpty`, `chatPlaceholder`, `chatSend`, `chatMe`, `chatCenter`, `chatConnecting`, `chatReconnecting`, `chatStopped`(대화를 이어갈 수 없습니다), `chatRejected`(보내지 못했습니다. 1000자 이하로 써 주세요)

## 완료 기준
- [x] `npm run build` 통과
- [x] 단독 모드: S-12 전송 완료 화면과 C-02에 채팅이 보이지 않고, WebSocket 연결이 없다(개발자 도구 네트워크 WS 탭)
- [x] API 모드(`VITE_API_BASE=/api npm run dev` + `cd backend && uv run fastapi dev app/main.py`): 브라우저 둘(근로자 360px, 센터 1280px)에서 근로자가 S-12로 보낸 사례의 C-02를 열고, 양쪽이 서로의 메시지를 받는다. 각 말풍선의 보낸 사람·시각이 서버 값이다
- [x] 센터 화면을 새로고침하면 이전 메시지가 순서대로 다시 보인다(`history`)
- [x] 백엔드를 껐다 켜면 양쪽이 "다시 연결 중"을 보이다가 저절로 다시 붙는다(메모리 저장소면 서버 재시작으로 사례가 사라지므로 `4404` 멈춤 문구를 보이는 것까지 확인. `DB_PATH`를 주면 이어진다)
- [x] C-01 데모 초기화 → 열린 채팅이 `4000`으로 멈추고 다시 연결하지 않는다(C-01 버튼이 부르는 `POST /api/center/reset`을 직접 불러 확인)
- [x] mock 사례 C-02에서 센터 채팅이 열리고 예시 사례 안내 줄이 보인다
- [x] 1001자 이상은 보내기 버튼이 막히거나 `chatRejected`가 보인다. 입력값은 남는다
- [x] 근로자 채팅을 en·vi·ko와 ar(RTL)에서 보고 말풍선 방향이 맞다. 센터 패널을 1280px·900px 아래에서 본다
- [x] 콘솔에 메시지 본문·토큰이 찍히지 않는다

## 결과

2026-10-30. `frontend/consult-chat` 브랜치. backend 14(PR 98)가 아직 main에 없어 `origin/backend/chat-websocket` 위에 쌓았다.

브라우저 확인은 Playwright(로컬에 받아 둔 1.61.1, Chromium 1228) 헤드리스로 했다. Claude in Chrome이 연결되지 않아서다. 근로자(360×780)와 센터(1280×900, 880×900)를 저장소가 분리된 브라우저 컨텍스트 두 개로 띄웠다. 근로자의 언어·동의·회원 상태는 세션·기기 저장소에 미리 넣었고, S-12 요청 종류·동의 체크·보내기는 화면에서 눌렀다.

| 확인 | 결과 |
|---|---|
| `npm run build` | 통과 |
| 동기화 기대값 재생성 | 생성 시각 외 차이 없음(`domain/centerCase.ts`에는 타입·상수만 더했다). `parity.json`은 바꾸지 않았다 |
| Vite 프록시 `ws: true` | Node `WebSocket`으로 `:5180/api/…/chat`에 근로자·센터를 붙여 `history` → `m-1`(worker)·`m-2`(center)를 양쪽이 받음, 틀린 토큰은 4403 |
| API 모드, 두 브라우저 | 근로자 S-12 전송 → 전송 완료 화면에 채팅 카드, 세션 `chatTokens`에 사례 id 키 하나. 센터 C-02에서 근로자 글(vi)과 센터 글(ko)을 양쪽이 서버 `id`·`from`·`at`으로 받음. 내 말풍선은 끝 쪽, 상대는 시작 쪽 |
| 센터 새로고침 | `history`로 두 글이 순서대로 다시 보임 |
| 백엔드 재시작(`DB_PATH`) | 끈 뒤 0.2초 안에 양쪽 "다시 연결 중", 보내기 버튼 막힘, 입력 유지. 다시 켜면 저절로 붙고 history 유지, 남은 입력을 보내 센터가 받음 |
| 백엔드 재시작(메모리) | 다시 켜면 사례가 없어 근로자는 `chatStopped`(4404)로 멈춤, 센터는 목록 폴링으로 "사례를 찾을 수 없습니다" |
| 데모 초기화(`POST /api/center/reset`) | 양쪽 4000으로 멈춤(근로자 `chatStopped`, 센터 "데모 초기화로 채팅이 끝났습니다."), 입력줄 사라짐, 4초 동안 다시 연결 시도 0회 |
| mock 사례 C-02 | 센터 채팅이 열리고 예시 사례 안내 줄이 보임 |
| 길이 제한 | 입력란 `maxLength` 1000이라 1001자는 쓸 수 없다. 비었으면 보내기 버튼이 막힌다. 서버 `error` 프레임(`chatRejected`) 표시 경로는 화면에서 만들 방법이 없어(서버 검사 = 브라우저 검사) 코드로만 있다 |
| 단독 모드 | S-12 전송 완료·C-02에 채팅 없음, WebSocket 연결 0(Vite HMR 제외), `/api` 요청 0 |
| 언어 | 근로자 vi·ko·en·ar·my·ru. ar은 내 말풍선이 왼쪽. 센터 1280px은 오른쪽 열 맨 위, 880px은 한 열에서 원문 아래·상태 변경 위 |
| 콘솔 | `[chat] 닫힘 4000 → 멈춤` 같은 닫힘 코드 줄만. 메시지 본문·토큰 없음 |

정한 것
- 토큰은 세션(`umn.session.chatTokens`)에 사례 id별로 두고, S-12 전송 완료 화면은 거기서 읽는다. `clearMyData`는 세션을 비우므로 토큰도 사라진다
- 다시 연결은 3초(`CHAT_RECONNECT_MS`), 횟수 제한 없음. 끊김 기록은 열려 있던 연결이 끊길 때 한 번만 남긴다(서버가 꺼져 있는 동안 3초마다 쌓이지 않게)
- 연결 중인 소켓을 화면을 떠나며 바로 닫으면 Chrome이 "closed before the connection is established" 경고에 **토큰이 든 주소**를 남긴다(개발 모드 StrictMode에서 매번 생긴다). 그래서 연결 중이면 열린 뒤에 닫는다
- 내 글도 서버가 되돌려 준 것만 그린다(낙관적 표시 없음). `history`는 목록을 통째로 바꾸고 `message`는 같은 `id`를 무시한다
- Enter로 보내고 Shift+Enter는 줄바꿈, 조합 중(한글 IME) Enter는 보내지 않는다
- 시각은 24시간제(`hour12: false`)다. 센터 화면의 다른 시각 표기와 맞춘다
- 근로자 쪽 멈춤 이유(권한·사례 없음·초기화)는 한 문구(`chatStopped`)로 묶었다. 근로자가 할 수 있는 일이 같다(다른 방법으로 연락). 센터는 이유별 한국어 문구

남은 것
- 새로고침하면 S-12 전송 완료 화면이 사라져 근로자 채팅도 사라진다(결정 1 A). 토큰은 세션에 남아 있으므로 S-13에서 다시 여는 것은 별도 항목으로 할 수 있다
- 휴대폰 실기기, 실제 Chrome 창으로는 확인하지 않았다
- 한국어 낱말 중간 줄바꿈(`overflow-wrap: anywhere`)이 긴 한국어 문장에서 어절 중간에 생긴다. 말풍선 언어가 섞여 `word-break: keep-all`을 일괄로 걸지 않았다

## 메모
- backend 14 `## 메모`의 "프론트 작업"(프록시 `ws: true`, `chatToken` 세션 저장, 끊기면 몇 초 뒤 다시 연결, 단독 모드에서 숨김)을 이 항목이 맡는다
- 채팅 메시지는 번역되지 않는다. 근로자는 모국어로, 상담원은 한국어로 쓸 가능성이 높아 `chatIntro`로 알린다. 번역은 backend 14 메모대로 별도 항목
- 새 문구 키의 베트남어는 원어민 검수가 필요하다. en·vi를 뺀 17개 언어는 기계 번역 초안이다(backlog 16)
- 센터 인증이 없으므로 사례 id만 알면 누구나 `role=center`로 붙는다(backend README "나중에 붙일 자리"). 데모 한정
