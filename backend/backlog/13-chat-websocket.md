# 13. 근로자·센터 상담 채팅(WebSocket)

상태: 완료
의존: 07

## 목표
근로자가 S-12에서 센터로 보낸 사례마다 근로자와 센터 상담자가 실시간으로 글을 주고받게 한다. 지금 서버는 프로세스 하나에 저장소 하나(메모리 또는 SQLite)이고, 발표 때도 서버 하나만 띄우므로(backlog 08) FastAPI 기본 WebSocket으로 만든다. 새 의존성은 없다. `fastapi[standard]` 안의 `uvicorn[standard]`가 이미 `websockets`를 포함한다.

## 범위
- 하는 것
  - `WS /api/center/cases/{id}/chat`: 사례 하나가 방 하나다. 연결되면 서버가 이전 메시지를 한 번 보내고, 이후 메시지를 같은 방의 모든 연결에 보낸다. 재접속하면 이전 메시지를 다시 받으므로 따로 조회 경로를 두지 않는다
  - 근로자 권한: `POST /api/center/cases` 응답에 선택 필드 `chatToken`을 더한다(`secrets.token_urlsafe(24)`). 근로자는 `?role=worker&token=<chatToken>`으로 연결한다. 토큰은 저장소에 사례별로 두고 `CenterCase`에는 넣지 않는다(센터 목록·상세 응답에 나오지 않게)
  - 센터 권한: 센터 화면에 로그인이 없으므로 데모에서는 `?role=center`만으로 연결한다(아래 "하지 않는 것"과 README "나중에 붙일 자리")
  - 메시지는 서버가 만든다. 클라이언트는 `text`만 보내고 `id`·`from`·`at`은 서버가 정한다(`from`은 연결 때 확인한 역할, `at`은 `clock`)
  - 저장: `CenterStore` 프로토콜에 `chat_token(case_id)`, `add_message(case_id, from_, text, at)`, `messages(case_id)`를 더하고 메모리·SQLite 두 구현에 넣는다. SQLite 표는 `chat_tokens`(case_id, token), `chat_messages`(id, case_id, sender, text, at). `reset()`은 두 표도 비운다
  - 연결 목록(방별 WebSocket 집합)은 저장 상태가 아니라 실행 중인 연결이므로 `app/chat.py`의 `ChatHub`에 두고 lifespan에서 `app.state.chat`으로 만든다. 경로는 `routers/center.py`에 더한다. `POST /api/center/reset`은 열린 연결을 모두 닫는다
  - 접근 로그: `RequestContextMiddleware`가 지금 `websocket` scope를 그냥 넘기므로, 연결이 끝날 때 한 줄(`WS`, 경로, 닫힘 코드, 연결 시간, request id)을 남긴다. 쿼리 문자열(토큰)과 메시지 본문은 남기지 않는다
  - `tests/test_chat.py`: `TestClient.websocket_connect`로 네트워크 없이 확인한다. 메모리·SQLite 두 구현에 돌린다(07의 `center_store` 픽스처)
  - `README.md`: API 표, 요청·응답 예시, "나중에 붙일 자리"에 센터 인증·채팅 번역 행 추가
- 하지 않는 것
  - socket.io(`python-socketio`), Redis 등 다중 프로세스·다중 서버 중계. `--workers 2` 이상이면 같은 방이 다른 프로세스로 나뉘므로 지원하지 않는다고 README에 적는다
  - 센터 상담자 로그인·상담자별 권한, 근로자 토큰 만료·재발급
  - 메시지 번역(근로자 모국어 ↔ 한국어), 첨부 파일, 읽음 표시, 입력 중 표시, 푸시 알림
  - mock 사례 24건의 근로자 쪽 채팅(토큰이 없으므로 센터만 연결된다)
  - 프론트 코드. 채팅 화면, `chatToken` 저장, Vite 프록시 `ws: true`는 `frontend/` backlog로 따로 한다
  - 센터 접수함 2초 폴링을 WebSocket으로 바꾸는 것

## API·파일

### 연결
```text
WS /api/center/cases/{id}/chat?role=worker&token=<chatToken>
WS /api/center/cases/{id}/chat?role=center
```
서버는 먼저 `accept()`한 뒤 검사하고, 실패하면 아래 코드로 닫는다. `accept()` 전에 닫으면 클라이언트가 이유 없는 1006만 보게 되기 때문이다.

| 닫힘 코드 | 언제 |
|---|---|
| `4404` | 사례가 없다 |
| `4403` | `role`이 없거나 틀렸다, 근로자 토큰이 없거나 맞지 않는다 |
| `4000` | 데모 초기화(`POST /api/center/reset`)로 방이 비었다 |

### 프레임(JSON, camelCase)
```jsonc
// 클라이언트 → 서버
{ "type": "message", "text": "Tay tôi vẫn còn chảy máu" }

// 서버 → 클라이언트: 연결 직후 한 번
{ "type": "history", "messages": [ChatMessage, ...] }
// 서버 → 클라이언트: 새 메시지(보낸 사람 자신에게도 간다)
{ "type": "message", "message": ChatMessage }
// 서버 → 클라이언트: 잘못된 프레임. 연결은 끊지 않는다
{ "type": "error", "code": "invalid" }

// ChatMessage
{ "id": "m-1", "caseId": "C-48213", "from": "worker", "text": "...", "at": "2026-10-30T05:12:00.000Z" }
```
- `text`는 앞뒤 공백을 지운 뒤 1자 이상 1000자 이하다. 벗어나거나 JSON이 아니거나 `type`이 다르면 `error`를 보낸다
- `id`는 사례 안에서 `m-1`, `m-2`…로 늘어난다. `at`은 다른 시각 필드와 같은 형식(`clock.iso_utc`)이다

### 바뀌는 응답
- `POST /api/center/cases` → `{ case, nextOpenDate, chatToken }`. `chatToken`은 선택 필드로 더한다. 기존 필드는 그대로다

### 파일
- 추가: `app/chat.py`(`ChatHub`), `tests/test_chat.py`
  - `app/chat.py`를 새 모듈로 두는 이유: 방별 연결 목록과 방송은 저장 상태도 규칙도 아니어서 `store.py`·`rules/`에 맞지 않고, 라우터를 얇게 두려면 라우터 밖에 있어야 한다. 모듈 변수가 아니라 lifespan에서 만든 인스턴스(`app.state.chat`)로 둔다
- 수정: `app/schemas.py`(`ChatMessage`, `ChatIn`, `NewCaseResponse.chat_token`), `app/vocab.py`(`ChatRole = Literal["worker", "center"]`), `app/store.py`, `app/store_sqlite.py`, `app/routers/center.py`(WS 경로, 토큰 발급, reset 때 연결 닫기), `app/main.py`(lifespan), `app/errors.py`(WS 접근 로그), `tests/test_store.py`, `tests/test_api.py`, `README.md`(API 표, 요청·응답 예시, 폴더 구조 표, "나중에 붙일 자리", 발표용 실행의 단일 프로세스 안내)

## 완료 기준
- [x] `uv run ruff check . && uv run ruff format --check .` 통과, `uv run pytest` 통과. 기존 테스트는 그대로 통과한다
- [x] `test_chat.py`가 다음을 메모리·SQLite 두 구현에서 확인한다
  - 근로자·센터 두 연결이 한 방에 붙어 한쪽이 보낸 메시지를 양쪽이 받는다. `from`·`at`·`id`는 서버 값이다
  - 다시 연결하면 `history`에 이전 메시지가 순서대로 있다
  - 없는 사례 → 4404, 토큰 없음·틀림·`role` 틀림 → 4403
  - 빈 문자열, 1001자, JSON 아님 → `error` 프레임을 받고 연결은 유지된다
  - `POST /api/center/reset` → 열린 연결이 4000으로 닫히고, 다시 연결하면 `history`가 비어 있다
  - SQLite: 저장소를 두 번 만들어도(재시작 흉내) 메시지와 토큰이 남는다
- [x] `test_api.py`: `POST /api/center/cases` 응답에 `chatToken`이 있고, `GET /api/center/cases`·`/cases/{id}` 응답에는 없다
- [x] 접근 로그에 WS 연결이 한 줄씩 남고, 그 줄에 토큰·메시지 본문이 없다(테스트에서 `caplog`로 확인)
- [x] `uv run fastapi dev app/main.py`로 띄워 브라우저 콘솔 두 개(근로자·센터)에서 `new WebSocket(...)`으로 주고받은 결과를 `## 결과`에 적는다

## 결과

### 결정
- `ChatRole`은 `vocab.py`가 아니라 `schemas.py`의 `CaseStatus` 옆에 두었다. 센터 사례의 다른 열거값(`CaseStatus`, `Urgency`)이 거기에 있고, 프론트·모델링과 나누는 어휘가 아니기 때문이다
- `ChatHub`는 lifespan이 아니라 앱을 만든 직후 `app.state.chat`에 둔다. 닫을 자원이 없고, 테스트 대부분이 `TestClient(app)`를 `with` 없이 써서 lifespan이 돌지 않기 때문이다. 모듈 변수는 아니다
- 경로는 `routers/center.py`에 더했다. 검사(`_chat_denied`)와 프레임 처리만 두고 방 관리는 `app/chat.py`, 저장은 `store`에 있다
- `hub.join()`과 `store.messages()` 사이에 await가 없게 해, 연결 직후 들어온 메시지를 놓치거나 `history`와 `message`로 두 번 받지 않게 했다
- 저장소 호출은 비동기 경로 안에서 동기로 부른다. 메모리·SQLite 모두 한 번에 1ms 안쪽이라 스레드 풀로 넘기지 않았다
- 근로자 토큰 비교는 `secrets.compare_digest`다. `POST /api/center/cases` 응답의 `chatToken`은 `absent_if_none` 선택 필드다
- 수동 확인 중 uvicorn이 WebSocket 연결마다 `uvicorn.error`에 `"WebSocket <경로?쿼리>" [accepted]`(클라이언트 주소, 토큰 포함)를 남기는 것을 찾았다. `errors.py`에서 이 줄을 버리는 필터를 달고 테스트를 더했다(`test_uvicorn_websocket_line_is_dropped`)

### 실행
- `uv run ruff check . && uv run ruff format --check .` → All checks passed
- `uv run pytest` → 2900 passed(전 2864, +36). `tests/test_chat.py` 29개(14개 × 메모리·SQLite + uvicorn 로그 필터 1개), `tests/test_store.py` +7(채팅 3개 × 두 구현 + SQLite 재시작 1개), `tests/test_api.py`의 기존 전송 테스트에 `chatToken` 검사 추가
- 실제 서버 확인(완료 기준의 "브라우저 콘솔 두 개" 대신, 같은 프로토콜인 Python `websockets` 클라이언트 두 개로 했다): `DB_PATH=<임시>/chat.db uv run fastapi run app/main.py --port 8766`
  - 근로자·센터 연결 → 둘 다 `{"type":"history","messages":[]}` → 근로자가 보낸 메시지를 양쪽이 `m-1`로, 센터가 보낸 메시지를 근로자가 `m-2`로 받음 → `"oops"` → `{"type":"error","code":"invalid"}`
  - 틀린 토큰 → 4403, `C-0` → 4404, 재접속 → history 2건, `POST /api/center/reset` → 4000
  - 서버 로그: `app.access WS /api/center/cases/C-47625/chat 1000 1.4ms request_id=…` 등 5줄, `WebSocket`·`token=`이 든 줄 0개(필터 전에는 5줄이 토큰과 함께 남았다)
  - 메시지를 보낸 뒤 서버를 껐다 같은 `DB_PATH`로 다시 띄움 → 같은 토큰으로 붙고 history에 `["재시작 전"]`

### 바뀐 API
- 추가: `WS /api/center/cases/{id}/chat`(프레임·닫힘 코드는 README)
- 변경: `POST /api/center/cases` 응답에 선택 필드 `chatToken`. `POST /api/center/reset`이 열린 채팅 연결을 4000으로 닫는다

### 남은 문제
- 프론트 연결(아래 메모의 프론트 작업)
- 센터 인증·번역·다중 프로세스 중계는 README "나중에 붙일 자리"에 적었다

## 메모
- socket.io를 쓰지 않는 이유: 서버가 Python이라 `python-socketio`를 더해야 하고, 클라이언트도 `socket.io-client`로 묶인다. 이 데모에서 필요한 것(사례별 방, 재접속 후 이전 메시지)은 기본 WebSocket과 연결 직후 `history` 프레임으로 충분하다. 다중 프로세스·다중 서버로 늘릴 때(Redis 중계가 필요할 때) 다시 검토한다
- 번역: 근로자는 모국어로, 상담자는 한국어로 쓸 가능성이 높다. backlog 05(리포트 `note` 번역)의 LLM 번역 + 역번역 검사를 메시지에 붙이는 것은 별도 항목으로 둔다. 붙이면 `ChatMessage`에 선택 필드(`textKo`, `translation`)로 더한다
- 센터 인증이 없으므로 사례 id만 알면 누구나 `role=center`로 붙을 수 있다. 데모 한정이고 README "나중에 붙일 자리"에 적는다
- 프론트 작업(별도 `frontend/` backlog): `vite.config.ts` 프록시를 `{ '/api': { target: 'http://localhost:8000', ws: true } }`로 바꾸기, `chatToken`을 근로자 세션 상태(브라우저 저장)에 두기, 끊기면 몇 초 뒤 다시 연결하기, 단독 모드(`VITE_API_BASE` 없음)에서는 채팅을 숨기기
- 보존 기간: 메시지는 자유 입력이라 개인 정보가 들어갈 수 있다. 07과 같이 보존 기간·자동 삭제·암호화는 미결로 둔다
- 이 작업 밖에서 찾은 것: `fastapi run`으로 띄우면 uvicorn HTTP 접근 로그(`INFO: 127.0.0.1:50854 - "POST /api/center/cases HTTP/1.1" 201`)가 여전히 찍힌다. `_setup_logging()`의 `uvicorn.access` 끄기가 서버 시작 때 다시 켜지는 것으로 보인다. 클라이언트 주소와, `GET /api/center/cases?since=`처럼 쿼리가 있으면 쿼리 문자열까지 남으므로 README "공통 규칙"의 로그 규칙과 어긋난다. 별도 항목으로 고친다
