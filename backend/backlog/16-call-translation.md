# 16. 근로자·센터 앱 통화와 자막 번역

상태: 완료
의존: 14

## 목표
근로자 앱과 센터 앱이 사례 하나를 두고 인터넷 음성 통화를 하고, 서로의 말을 상대 언어 자막으로 본다. 가장 쉬운 방식으로 만든다. 음성은 브라우저끼리 WebRTC로 직접 주고받고, 서버는 연결 정보(시그널링)를 중계하고 받아쓴 문장만 LLM으로 번역한다. 서버는 음성을 받지 않는다.

## 방식과 고른 이유

| 방식 | 서버가 하는 일 | 판단 |
|---|---|---|
| **A. WebRTC 음성 + 서버 시그널링 중계 + 브라우저 받아쓰기 → 서버 번역** | WebSocket으로 SDP·ICE 중계, 자막 문장 번역 | **고른다.** 새 의존성 없음(14의 WebSocket과 토큰을 그대로 씀). 음성 지연은 브라우저끼리라 짧다. 서버는 짧은 글만 다룬다 |
| B. 서버가 음성을 받아 음성 인식 → 번역 → 음성 합성 | 오디오 스트림 수신, STT·TTS 공급자 연결 | 빼다. STT·TTS 공급자와 키가 더 필요하고 오디오 처리·지연·비용이 크다 |
| C. 통화 없이 음성 입력 채팅 | 채팅 번역만 | 통화가 아니다 |

- 받아쓰기는 브라우저 Web Speech API(`SpeechRecognition`)가 한다. Chrome(Android 포함)·Safari에 있고, 근로자 언어 코드로 `lang`을 맞춘다. 브라우저 일이라 이 항목의 범위가 아니다(프론트 backlog).
- 채팅 WebSocket(14)에 프레임을 더하지 않고 **경로를 따로 둔다**(`/call`). 채팅 계약·기록을 바꾸지 않고, 통화 프레임(SDP 수 KB, ICE 수십 개)이 채팅 기록에 섞이지 않는다. 검사(`_chat_denied`)·토큰·닫힘 코드·접근 로그는 14 것을 그대로 쓴다.

## 범위
- 하는 것
  - `WS /api/center/cases/{id}/call?role=worker&token=<chatToken>` / `?role=center`: 권한 검사와 닫힘 코드(`4404`, `4403`, `4000`)는 채팅과 같다. 근로자는 14의 `chatToken`을 그대로 쓴다
  - 방 하나에 역할마다 한 연결만. 같은 역할이 이미 있으면 새 연결을 `4409`로 닫는다(센터 탭 두 개가 같은 제안을 받아 연결이 꼬이는 것을 막는다)
  - 있음 알림: 연결 직후 `{ type: "joined", role, peers }`(지금 방에 있는 상대 역할 목록), 상대가 들어오고 나가면 `{ type: "peer", role, present }`. 센터 화면은 이것으로 "근로자가 통화를 기다립니다"를 띄운다
  - 시그널링 중계: `{ type: "signal", data }`를 **상대에게만** `{ type: "signal", from, data }`로 보낸다. `data`(SDP·ICE·끊기 등)는 열어 보지 않는다. 직렬화 크기 16KB 초과는 `error`
  - 자막 번역: `{ type: "caption", text }`(1~500자, 받아쓰기 확정 문장)를 받으면 번역해 양쪽에 `{ type: "caption", caption }`을 보낸다
    - 근로자 → 한국어, 센터 → 근로자 언어. 근로자 언어는 클라이언트 값이 아니라 사례의 `language`다. 사례 언어가 `ko`면 번역하지 않는다
    - `templates/translate.py`에 `translate_line(text, source, target, client)`를 더한다. LLM 1회, 05의 `generate()`·`_DATA_ONLY`·출력 스키마 방식을 그대로 쓰고 `attempts=1`이다(늦은 자막은 쓸모가 없다). 역번역 검사는 하지 않는다(호출 3회, 평균 4초라 통화에 늦다). 대신 원문을 항상 함께 보낸다
    - 키가 없거나 실패·시간 초과면 `translation: "skipped"`, `translated: null`로 원문만 보낸다. 실패가 연결을 끊지 않는다
    - 번역은 연결마다 별도 작업(`asyncio` task)으로 돌려, 번역을 기다리는 동안에도 시그널링 프레임을 계속 중계한다. 연결이 끝나면 남은 작업을 취소한다
  - `app/chat.py`의 `ChatHub`에 상대에게만 보내기(`send_others`)와 역할 확인을 더하고, 통화용 인스턴스를 `app.state.call`로 둔다. `POST /api/center/reset`은 통화 연결도 4000으로 닫는다
  - 로그: 미들웨어의 `WS <경로> <닫힘 코드> <ms>` 한 줄(14와 같음)과 `call caption translation=ok|skipped`만 남긴다. 토큰, SDP·ICE(IP 주소가 들어 있다), 자막 원문·번역은 남기지 않는다
  - `tests/test_call.py`: `TestClient.websocket_connect` + `FakeLLMClient`로 네트워크 없이
  - `README.md`: API 표, 프레임 예시, 폴더 구조 표(`test_call.py`), "나중에 붙일 자리"에 TURN·통화 기록 행
- 하지 않는 것
  - 음성을 서버로 받기, 녹음·저장. 자막도 저장하지 않는다(재접속해도 이전 자막은 없다. 채팅 기록에도 넣지 않는다)
  - 서버 음성 인식·음성 합성(방식 B)
  - TURN 서버. 같은 와이파이·대부분의 가정·회사망은 STUN만으로 붙지만, 이동통신망끼리(대칭 NAT)는 실패할 수 있다. 발표장에서 문제가 되면 따로 항목을 만든다
  - 그룹 통화, 영상, 통화 대기열·벨소리·푸시, 통화 시간 기록
  - 프론트 코드(통화 버튼, `RTCPeerConnection`, `SpeechRecognition`, 자막 화면)는 `frontend/` backlog로 따로 한다
  - 채팅 메시지 번역(README "나중에 붙일 자리"의 "상담 채팅 번역"). `translate_line`을 나중에 다시 쓸 수 있다

## API·파일

### 연결
```text
WS /api/center/cases/{id}/call?role=worker&token=<chatToken>
WS /api/center/cases/{id}/call?role=center
```

| 닫힘 코드 | 언제 |
|---|---|
| `4404` | 사례가 없다 |
| `4403` | `role`이 없거나 틀렸다, 근로자 토큰이 없거나 맞지 않는다 |
| `4409` | 같은 역할이 이미 이 사례의 통화에 붙어 있다 |
| `4000` | 데모 초기화(`POST /api/center/reset`) |

### 프레임(JSON, camelCase)
```jsonc
// 클라이언트 → 서버
{ "type": "signal", "data": { "sdp": { "type": "offer", "sdp": "v=0…" } } }   // data는 그대로 중계, 16KB 이하
{ "type": "caption", "text": "Tay tôi vẫn còn chảy máu" }                    // 1~500자

// 서버 → 클라이언트
{ "type": "joined", "role": "worker", "peers": ["center"] }    // 연결 직후 한 번
{ "type": "peer", "role": "center", "present": true }          // 상대가 들어오거나(true) 나감(false)
{ "type": "signal", "from": "worker", "data": { … } }          // 상대에게만
{ "type": "caption", "caption": {                              // 양쪽 모두
    "id": "c-1", "from": "worker", "text": "Tay tôi vẫn còn chảy máu", "lang": "vi",
    "translated": "손에서 아직 피가 납니다", "translatedLang": "ko", "translation": "ok",
    "at": "2026-10-30T05:12:00.000Z" } }
{ "type": "error", "code": "invalid" }                         // 잘못된 프레임. 연결은 유지
```
- `id`는 연결이 아니라 방(사례) 안에서 `c-1`, `c-2`…로 늘어난다. 저장하지 않으므로 서버를 다시 띄우면 처음부터다
- `translation`은 05의 `TranslationStatus`다. `ok`가 아니면 `translated`는 `null`이다(`rejected`는 아래 `## 결과`의 "문서에서 바꾼 점"). 사례 언어가 `ko`면 `lang`·`translatedLang`이 모두 `ko`이고 `skipped`다

### 파일
- 추가: `tests/test_call.py`
- 수정: `app/chat.py`(`send_others`, `roles`), `app/routers/center.py`(WS `/call`, reset 때 닫기), `app/main.py`(`app.state.call`), `app/schemas.py`(`CallIn`, `Caption`), `app/templates/translate.py`(`translate_line`), `tests/test_translation.py`(`translate_line`), `README.md`
- 새 모듈·의존성은 없다. 통화 경로는 채팅 경로와 검사·토큰을 함께 쓰므로 `routers/center.py`에 둔다

## 완료 기준
- [x] `uv run ruff check . && uv run ruff format --check .` 통과, `uv run pytest` 통과(네트워크 없이). 기존 테스트는 그대로 통과한다
- [x] `test_call.py`가 확인한다
  - 근로자·센터가 붙으면 `joined`의 `peers`가 맞고, 먼저 붙은 쪽이 `peer present: true`를, 한쪽이 나가면 남은 쪽이 `present: false`를 받는다
  - `signal`은 상대만 받고 보낸 쪽은 받지 않는다. `data`가 그대로다. 16KB 초과·JSON 아님·다른 `type` → `error`, 연결 유지
  - 근로자 자막(사례 `vi`) → 양쪽이 `translated`(가짜 LLM 값)·`translatedLang: "ko"`·`translation: "ok"`를 받는다. 센터 자막 → 대상 언어가 `vi`이고 프롬프트에 베트남어가 들어 있다
  - LLM 없음·LLM 오류·시간 초과 → `skipped`, `translated: null`, 원문 그대로. 사례 언어 `ko` → LLM을 부르지 않는다
  - 번역이 멈춘 동안(가짜 LLM이 기다림)에도 같은 연결의 `signal`이 상대에게 간다
  - 없는 사례 4404, 토큰 틀림·`role` 틀림 4403, 같은 역할 두 번째 연결 4409, `POST /api/center/reset` → 4000
  - 로그(`caplog`)에 토큰, `sdp` 내용, 자막 원문·번역이 없다
- [x] 실제 서버(`uv run fastapi run app/main.py`, LLM 키 있음)에 Python `websockets` 클라이언트 두 개로 붙어 사례 생성 → 근로자·센터 연결 → 가짜 SDP 중계 → 근로자 베트남어 자막·센터 한국어 자막의 실제 번역 → reset 4000을 확인하고, 자막 번역 소요 시간과 서버 로그 줄을 `## 결과`에 적는다. 키 없이도 한 번 돌려 `skipped`를 확인한다
- [x] `README.md` API 표·프레임 예시·"나중에 붙일 자리"가 바뀐다

## 결과

### 문서에서 바꾼 점
- `translation`에 `rejected`를 더했다. 문서는 `ok`·`skipped`만 쓴다고 했지만 backend `CLAUDE.md`의 "LLM이 쓴 문장은 진단·병명 검사 뒤 내보낸다"에 따라 한국어로 옮긴 자막은 05와 같은 `check_ko_text`(금지어·한국어 여부)를 거친다. 걸리면 `rejected`, `translated: null`이고 원문은 그대로 간다. 근로자 언어로 옮긴 자막은 한국어 금지어 검사를 할 수 없어 빈 값만 거른다
- `ChatHub`에 메서드를 더하지 않고 같은 `app/chat.py`에 `CallHub`를 따로 두었다. 통화는 방마다 역할 하나에 연결 하나라 저장 형태(`dict[역할, 연결]`)가 채팅(연결 집합)과 다르고, 자막 번호도 여기 둔다. 채팅 코드는 그대로다
- 로그 줄은 `call caption translation=<상태>`(라우터)와 guard에 걸렸을 때의 `line translation rejected=<사유>`(번역 모듈)다

### 결정
- LLM 클라이언트는 `Depends(llm_client)`가 아니라 `ws.app.state.llm`에서 읽는다. `llm_client`는 `Request`를 받아 WebSocket 경로에서 쓸 수 없다. 테스트는 기존 방식대로 `app.main.get_llm_client`를 가짜로 바꿔 lifespan에서 넣는다
- 자막 번호·시각은 번역 전에 받은 순서대로 정한다. 번역은 연결마다 `asyncio` task로 돌려 번역이 끝나는 순서가 달라도 `id`는 말한 순서다. 연결이 끊기면 남은 번역 task를 취소한다
- 프레임 크기(16KB)는 파싱 전에 원문 바이트로 본다. `signal.data`는 JSON 객체만 받는다(문자열·없음은 `error`)
- 데모 초기화로 방이 비면 끊긴 쪽이 `peer present: false`를 보내지 않는다(`leave`가 False). 둘 다 4000으로 닫히기 때문이다
- 번역 시간 제한은 `LLM_TIMEOUT_S`를 그대로 쓰고 시도는 1회다

### 실행
- `uv run ruff check . && uv run ruff format --check .` → All checks passed
- `uv run pytest` → 2923 passed(새 테스트 22개: `tests/test_call.py` 19개, `tests/test_translation.py` +3 — `translate_line`의 같은 언어 호출 없음, 1회 호출 후 대체, 근로자 언어 쪽 guard 없음·빈 값 거부)
- 실제 서버(완료 기준대로 Python `websockets` 클라이언트 두 개, 스크립트는 저장소 밖에 두었다)
  - LLM 있음: `uv run --env-file <backend/.env> fastapi run app/main.py --port 8767` (`claude-haiku-5-5`)
    - 사례 생성 → 근로자 `joined peers=[]` → 센터 `joined peers=["worker"]`, 근로자 `peer center present=true` → 가짜 offer·answer가 상대에게만 감
    - 근로자 "Tay tôi bị kẹp vào máy, vẫn còn chảy máu" → "손이 기계에 끼였고, 아직도 피가 나고 있어요." `ok`, 3.21초
    - 센터 "지금 다친 손을 움직일 수 있나요?" → "Bây giờ anh/chị có thể cử động bàn tay bị thương không?" `ok`, 4.09초
    - 두 번째 센터 연결 → 4409, `POST /api/center/reset` → 두 연결 4000
    - 서버 로그: `app.access WS /api/center/cases/C-11685/call 4000 7311.2ms request_id=…`, `call caption translation=ok` 2줄 등. `token=`·`WebSocket`·`sdp`·자막 원문이 든 줄 0개
  - LLM 없음: `env -u LLM_API_KEY uv run fastapi run app/main.py --port 8768` → 두 자막 모두 `translated: null`, `translation: "skipped"`, 바로 도착. 나머지는 같다

### 바뀐 API
- 추가: `WS /api/center/cases/{id}/call`(프레임·닫힘 코드는 README)
- 변경: `POST /api/center/reset`이 열린 통화 연결도 4000으로 닫는다

### 남은 문제
- 실제 음성은 브라우저 두 개로 확인해야 한다(프론트 항목). 서버 확인은 시그널링 중계와 자막 번역까지다
- 자막 번역이 3~4초 걸린다. 말하고 나서 상대가 번역을 보기까지 그만큼 늦다. 더 줄이려면 스트리밍 응답이나 더 빠른 모델을 따로 검토한다
- TURN 서버가 없다. 이동통신망끼리는 통화가 안 붙을 수 있다(README "나중에 붙일 자리")

## 메모
- 실제 음성은 브라우저 두 개가 있어야 확인된다. 서버 확인은 시그널링이 그대로 오가는지까지다. 브라우저 통화 확인은 프론트 항목의 완료 기준으로 둔다
- 프론트 작업(별도 `frontend/` backlog): 센터 사례 상세(C-02)를 열면 `/call`에 붙어 근로자 있음을 보이기, 통화 버튼 → `getUserMedia` + `RTCPeerConnection`(STUN `stun:stun.l.google.com:19302`), 근로자가 offer를 만들기(누가 먼저 만들지 정해 두면 충돌이 없다), `SpeechRecognition.lang`을 근로자 언어로, 확정 문장만 `caption`으로 보내기, Vite 프록시 `ws: true`(14에서 이미 함)
- 위험: Android Chrome은 WebRTC가 마이크를 쓰는 동안 `SpeechRecognition`이 같이 돌지 않을 수 있다. 그러면 "누르고 말하기"(말하는 동안 받아쓰기, 통화 음성은 계속)로 바꾼다. 서버 계약은 같다
- 의료 대화라 번역 오류 위험이 있다. 그래서 자막은 원문과 번역을 함께 보낸다. 역번역 검사를 붙일지는 실제 소요 시간을 보고 정한다
- 14와 같이 다중 프로세스는 지원하지 않는다(`--workers 1`)
