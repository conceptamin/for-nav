# 16. 근로자·센터 인터넷 통화 신호와 통화 자막 번역

상태: 대기
의존: 14(상담 채팅 WebSocket)

## 목표
상담 채팅(backlog 14)이 있는 사례마다 근로자와 센터 상담원이 앱 안에서 인터넷 음성 통화를 하게 하고, 통화하는 동안 두 사람이 한 말을 실시간 자막으로 남긴다. 근로자의 말은 한국어로, 상담원의 말은 근로자 언어로 번역해 양쪽에 원문과 함께 보인다. 음성은 브라우저끼리 WebRTC로 직접 주고받고, 서버는 연결 신호를 중계하고 자막을 저장·번역한다. 음성 자체는 서버를 지나지 않고 저장하지도 않는다.

## 결정이 필요한 것

1. **말을 글자로 바꾸는 곳(STT).** → **A로 결정(2026-10-30).**
   - **A. 각 브라우저가 자기 마이크를 Web Speech API(`SpeechRecognition`)로 받아 쓰고, 글자만 서버로 보낸다(권장).** 새 의존성·키가 없고 서버가 음성을 받지 않는다. 대신 Chrome 계열에서만 되고(Chrome은 음성을 Google 서버로 보내 인식한다), 20개 언어 중 일부는 인식이 안 될 수 있으며, Android Chrome에서 통화 마이크와 동시에 쓸 때 인식이 끊길 수 있다(실기기 확인 필요). 이 경우 서버 일은 이 문서 범위 그대로다.
   - B. 서버가 음성을 받아 STT 공급자(OpenAI·Google 등)로 인식한다. 브라우저 제약이 없지만 새 공급자·키·비용이 생기고, 음성을 서버로 올리는 경로(오디오 스트리밍)와 그 보존 규칙을 따로 정해야 한다. 이 문서를 크게 고쳐야 한다.
2. **자막 번역 방식.** → **A로 결정(2026-10-30).**
   - **A. 문장이 끝날 때마다 LLM 번역 1회 + `guard` 검사(권장).** 통화 중이라 늦으면 쓸모가 없다. 리포트 `note` 번역(backlog 05)의 역번역·비교까지 하면 3회 호출로 몇 초가 더 걸린다. 원문을 항상 함께 보이고 "기계 번역" 표시를 단다.
   - B. backlog 05와 같은 번역 → 역번역 → 비교 3회. 정확하지만 문장마다 몇 초 늦게 붙는다.
3. **자막 저장.** → **A로 결정(2026-10-30).**
   - **A. 사례별로 저장해 다시 연결하거나 통화가 끝난 뒤에도 C-02에서 볼 수 있게 한다(권장).** 채팅 메시지와 같은 저장소(메모리·SQLite)에 둔다. 보존 기간·삭제는 채팅과 같이 미결이다.
   - B. 통화 중에만 메모리로 중계하고 남기지 않는다.

## 범위
- 하는 것
  - `WS /api/center/cases/{id}/call`: 사례 하나가 통화방 하나다. 권한 검사와 닫힘 코드는 채팅과 같다(`?role=worker&token=<chatToken>` / `?role=center`, 4404·4403·4000)
  - 통화 신호 중계: `ring`·`accept`·`decline`·`hangup`과 WebRTC `signal`(SDP offer/answer, ICE 후보)을 같은 방의 **다른 역할** 연결에만 보낸다. `signal.data`는 열어 보지 않고 크기(16KB)만 검사한다
  - 상대 접속 여부: 연결·끊김마다 `presence` 프레임(`{ worker: bool, center: bool }`)을 방 전체에 보낸다. 근로자 화면이 닫혀 있으면 센터가 "근로자가 화면에 없음"을 알 수 있게 한다
  - 통화 상태는 서버가 갖지 않는다. 누가 걸었는지·통화 중인지는 두 브라우저가 프레임으로 맞춘다(서버 재시작·다시 연결 때 상태가 어긋나지 않게). 한쪽 연결이 끊기면 서버가 남은 쪽에 `hangup`(`reason: "left"`)을 보낸다
  - 자막: 클라이언트는 자기 말만 보낸다. `{ type: "caption", text, final }`
    - `final: false`(말하는 중): 저장·번역하지 않고 상대에게 `interim`으로 그대로 보낸다
    - `final: true`(문장 끝): 저장하고 방 전체에 `caption`(번역 `pending`)을 보낸 뒤, 번역이 끝나면 같은 `id`로 `caption`을 한 번 더 보낸다(번역 `ok`·`skipped`·`rejected`)
    - 언어는 서버가 정한다. 근로자 = 사례의 `language`, 센터 = `ko`. 번역 방향은 근로자 언어 → 한국어, 한국어 → 근로자 언어. 근로자가 한국어를 골랐으면 번역하지 않는다(`skipped`)
  - 번역: `app/templates/call.py`(새 파일)에 `translate_caption(text, src, dst, client)`. 결정 2를 따른다. 키가 없거나 실패·시간 초과(`CALL_TRANSLATE_TIMEOUT_S`, 기본 4초, 재시도 없음)면 `skipped`. 한국어 출력은 `guard.check_ko_text`로 검사해 걸리면 `rejected`. 번역은 백그라운드 작업으로 돌려 WebSocket 수신을 막지 않는다
  - 저장: `CenterStore`에 `add_caption(case_id, from_, lang, text, at)`, `set_caption_translation(case_id, caption_id, translation)`, `captions(case_id)`. SQLite 표 `call_captions`(id, case_id, sender, lang, text, at, tr_status, tr_lang, tr_text). `reset()`이 비운다. 연결 직후 `history`(자막 목록)를 한 번 보낸다
  - 연결 목록은 `app/chat.py`의 `ChatHub`를 그대로 한 번 더 만들어 `app.state.call`에 둔다(방 키 = 사례 id). 같은 역할 연결이 둘이면 둘 다 받는다(탭 두 개)
  - 접근 로그: 채팅과 같은 한 줄(`WS`, 경로, 닫힘 코드, 연결 시간, request id). 자막 본문·SDP·토큰을 남기지 않는다. 번역 실패는 `templates/translate.py`처럼 종류만 남긴다
  - `tests/test_call.py`: 메모리·SQLite 두 구현, 가짜 LLM. `README.md`: API 표, 프레임 예시, "나중에 붙일 자리"(TURN 서버, 센터 인증), 환경 변수 표
- 하지 않는 것
  - 음성 중계·녹음·저장(SFU, 녹음 파일). 음성은 브라우저끼리 직접 간다
  - TURN 서버. STUN만으로 연결되지 않는 망(일부 이동통신망·회사망)에서는 통화가 붙지 않을 수 있다. "나중에 붙일 자리"에 적는다
  - 서버 STT(결정 1이 B면 이 문서를 다시 쓴다), 영상 통화, 세 명 이상 통화, 통화 대기열·상담원 배정
  - 채팅 메시지 번역(README "나중에 붙일 자리"의 별도 행 그대로)
  - 프론트 코드(frontend 26)

## API·파일

### 연결
```text
WS /api/center/cases/{id}/call?role=worker&token=<chatToken>
WS /api/center/cases/{id}/call?role=center
```

### 프레임(JSON, camelCase)
```jsonc
// 클라이언트 → 서버
{ "type": "ring" }                         // 전화 걸기
{ "type": "accept" } | { "type": "decline" } | { "type": "hangup" }
{ "type": "signal", "data": { "sdp": {...} } | { "candidate": {...} } }
{ "type": "caption", "text": "손에서 피가 계속 나요", "final": true }

// 서버 → 클라이언트
{ "type": "history", "captions": [Caption, ...] }            // 연결 직후 한 번
{ "type": "presence", "worker": true, "center": false }
{ "type": "ring" | "accept" | "decline", "from": "center" }  // 상대에게만
{ "type": "hangup", "from": "worker", "reason": "hangup" | "left" }
{ "type": "signal", "from": "worker", "data": {...} }        // 상대에게만
{ "type": "interim", "from": "worker", "text": "Tay tôi vẫn" } // 상대에게만, 저장 안 함
{ "type": "caption", "caption": Caption }                    // 방 전체. 같은 id가 번역과 함께 한 번 더 온다
{ "type": "error", "code": "invalid" }

// Caption
{ "id": "t-1", "caseId": "C-48213", "from": "worker", "lang": "vi", "text": "Tay tôi vẫn còn chảy máu",
  "at": "2026-10-30T05:12:00.000Z",
  "translation": { "status": "pending" | "ok" | "skipped" | "rejected", "lang": "ko", "text": "손에서 아직 피가 나요" } }
```
- `caption.text`는 앞뒤 공백을 지운 뒤 1~500자, `interim`은 0~500자. 벗어나면 `error`
- `translation.text`는 `status`가 `ok`일 때만 있다

### 파일
- 추가: `app/templates/call.py`, `tests/test_call.py`
- 수정: `app/schemas.py`(`Caption`, `CaptionTranslation`, 프레임 입력 모델), `app/store.py`, `app/store_sqlite.py`, `app/routers/center.py`(WS 경로, reset 때 통화 연결도 닫기), `app/main.py`(`app.state.call`), `app/settings.py`(`CALL_TRANSLATE_TIMEOUT_S`), `tests/test_store.py`, `README.md`

## 완료 기준
- [ ] `uv run ruff check . && uv run ruff format --check .` 통과, `uv run pytest` 통과. 기존 테스트는 그대로 통과한다
- [ ] `test_call.py`가 메모리·SQLite 두 구현에서 확인한다
  - 근로자·센터가 붙으면 양쪽이 `presence`를 받고, 한쪽이 끊기면 남은 쪽이 `presence`와 `hangup`(`left`)을 받는다
  - `ring`·`accept`·`signal`이 상대 역할에게만 가고 보낸 쪽에는 돌아오지 않는다. 16KB를 넘는 `signal`은 `error`
  - `interim`은 상대에게만 가고 `history`에 남지 않는다
  - `caption`(final) → 방 전체가 `pending`을 받고, 가짜 LLM 번역 뒤 같은 `id`의 `ok`를 받는다. 근로자 vi → `lang: "ko"`, 센터 → `lang: "vi"`
  - LLM 없음·시간 초과 → `skipped`, `guard` 탈락 → `rejected`, 근로자 언어가 ko → `skipped`이고 LLM을 부르지 않는다
  - 다시 연결하면 `history`에 자막이 번역과 함께 순서대로 있다. `POST /api/center/reset` → 4000으로 닫히고 다시 연결하면 비어 있다
  - 없는 사례 → 4404, 토큰 틀림 → 4403
- [ ] 접근 로그에 WS 한 줄씩, 자막 본문·SDP·토큰이 없다(`caplog`)
- [ ] 실제 서버를 띄워 Python `websockets` 클라이언트 둘로 신호 중계·자막 번역(키가 있을 때 실제 LLM)을 확인하고 `## 결과`에 적는다

## 결과
(구현 후 작성)

## 메모
- WebRTC 신호를 채팅 WebSocket에 섞지 않고 경로를 나눈 이유: 채팅은 저장되는 메시지만 오가는 계약(backlog 14)이고, 통화 신호는 저장하지 않는 일회성 프레임이다. 섞으면 채팅 `history`·`error` 계약과 프론트 `useChat`이 함께 바뀐다
- STUN 서버 주소는 프론트가 정한다(frontend 26). 서버는 ICE 후보를 열어 보지 않는다
- 자막은 자유 발화라 개인 정보가 들어간다. 채팅 메시지와 같이 보존 기간·자동 삭제·암호화는 미결로 둔다. 음성은 저장하지 않는다
- 번역 프롬프트는 `templates/translate.py`의 규칙(사실만, 진단·병명 추가 금지, 사용자 메시지는 데이터로만)을 따른다. 대화체 짧은 문장이라 "의사에게 보내는 메모" 대신 "통화 자막"으로 바꾼다
