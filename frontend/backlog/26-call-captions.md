# 26. 근로자·센터 인터넷 통화와 실시간 번역 자막

상태: 진행 중(실제 음성·받아쓰기는 Chrome 창 두 개로 사용자 확인 필요)
의존: 25-consult-chat(상담 채팅 연결), backend 16(통화 신호·자막 번역)

## 목표
상담 채팅이 열리는 두 자리(S-12 전송 완료 화면, C-02 사례 상세)에서 근로자와 센터 상담원이 앱 안에서 인터넷 음성 통화를 한다. 통화하는 동안 내 말과 상대의 말이 실시간 자막으로 쌓이고, 각 자막에 원문과 번역(근로자 언어 ↔ 한국어)이 함께 보인다. 음성은 브라우저끼리 WebRTC로 직접 주고받고, 자막은 각 브라우저가 자기 마이크를 Web Speech API로 받아 써서 서버(backend 16)로 보낸다.

## 결정이 필요한 것

1. **휴대폰에서 시연할 방법.** → **A로 결정(2026-10-30).** 마이크(`getUserMedia`)와 음성 인식은 안전한 출처(HTTPS 또는 `localhost`)에서만 열린다. 지금 맥미니 배포는 HTTP이고 외부 접속·HTTPS가 범위 밖이다(backend 13).
   - **A. 이 항목은 `localhost`에서 PC 브라우저 창 두 개(근로자 360px, 센터 1280px)로 확인하고, 휴대폰 시연용 HTTPS는 `chore/` 항목으로 따로 한다(권장).** 범위가 가장 작다. 대신 이 항목이 끝나도 휴대폰으로는 아직 통화할 수 없다.
   - B. 이 항목에서 Vite 개발 서버를 HTTPS로 띄운다(`@vitejs/plugin-basic-ssl`, 새 의존성, 자체 서명 인증서 경고를 휴대폰에서 한 번 넘겨야 한다).
2. **STUN 서버.** → 권장안 A로 진행(2026-10-30). 바꾸려면 구현 전에 정한다. 같은 공유기·같은 PC에서는 없어도 붙는다. 다른 망끼리는 STUN이 있어야 대부분 붙고, 일부 망은 TURN까지 필요하다(범위 밖).
   - **A. 기본값 Google 공개 STUN(`stun:stun.l.google.com:19302`), `VITE_ICE_SERVERS`(JSON)로 바꿀 수 있게 한다(권장).** 브라우저가 공인 IP 확인을 위해 Google에 접속한다.
   - B. 기본 없음(같은 망에서만), 필요하면 환경 변수로 넣는다.
3. **근로자 화면이 닫혀 있을 때.** → 권장안 A로 진행(2026-10-30). 바꾸려면 구현 전에 정한다. 웹 앱이라 화면이 닫혀 있으면 전화를 받을 수 없다(푸시 알림 없음).
   - **A. 센터 패널에 "근로자가 화면에 없음"을 보이고 걸기 버튼을 막는다(권장).** backend 16의 `presence`를 쓴다. 근로자에게 전화를 받게 하려면 채팅으로 먼저 알린다.
   - B. 걸기는 막지 않고, 근로자가 들어오면 그때 울린다(대기 중 상태가 서버에 생겨 backend 16을 고쳐야 한다).

## 범위
- 하는 것
  - `src/api/call.ts`(새 파일): `useCall(caseId, auth)` 훅 하나. backend 16의 `WS /api/center/cases/{id}/call` 연결, 신호(`ring`·`accept`·`decline`·`hangup`·`signal`), `RTCPeerConnection`(음성만, `echoCancellation`·`noiseSuppression` 켬), 자막 목록
    - 통화 상태: `idle` → `calling`(내가 걸었음) / `ringing`(상대가 걸었음) → `connecting` → `in-call` → `ended`(이유: 상대가 끊음·거절·상대가 나감·연결 실패). 거는 쪽이 offer를 만든다
    - 응답 없음: 30초 동안 받지 않으면 거는 쪽이 `hangup`(`CALL_RING_TIMEOUT_MS`)
    - 다시 연결·멈춤 규칙은 `useChat`과 같다(3초, `4403`·`4404`·`4000`이면 멈춤). 통화 중에 신호 WebSocket이 끊겨도 이미 붙은 음성은 끊지 않는다
    - 돌려주는 값: `{ state, endReason, peer: { worker, center }, captions, interim, muted, captionSupport, start(), accept(), decline(), hangup(), toggleMute() }`
  - `src/api/speech.ts`(새 파일): 통화 중에만 `SpeechRecognition`(`continuous`, `interimResults`)을 돌린다. 앱 언어 → BCP-47 표(`vi` → `vi-VN` 등 20개)를 둔다. 인식 결과를 `caption`(`final: false/true`)으로 보낸다. 브라우저가 멈추면(`onend`) 통화가 이어지는 동안 다시 시작한다. 음소거 중에는 인식도 멈춘다
    - 지원하지 않는 브라우저·언어(`captionSupport: false`): 통화는 그대로 되고 "이 브라우저에서는 자막을 만들 수 없습니다"를 보인다. 상대 자막은 계속 받는다
  - `src/components/CallPanel.tsx`(새 파일): 걸기·받기·거절·끊기·음소거 버튼, 상태 줄, 통화 시간, 자막 목록. 자막 한 줄 = 보낸 사람 + 원문 + 번역(`pending`이면 "번역 중", `skipped`·`rejected`면 원문만, `ok`면 "기계 번역" 표시와 함께). 말하는 중(`interim`)은 목록 끝에 흐린 줄 하나. 문구는 props로 받는다(근로자 i18n, 센터 한국어 상수). 원격 음성은 숨긴 `<audio autoplay>`로 재생한다
    - 상대 화면: 근로자는 원문(자기 언어) 대신 번역을 크게, 센터는 한국어 번역을 크게 보인다. 내 말은 원문을 크게, 번역을 작게
  - S-12 전송 완료 화면: 채팅 카드 위에 "센터와 통화" 카드. C-02: 상담 채팅 패널 위에 "통화" 패널. 둘 다 채팅과 같이 토큰이 없거나 단독 모드면 보이지 않는다
  - 통화가 끝나도 자막 목록은 그 자리에 남는다(서버 `history`). C-02는 새로고침해도 이전 통화 자막을 다시 본다
  - 마이크 권한 거부: "마이크를 허용해야 통화할 수 있습니다"를 보이고 `idle`로 돌아간다
  - `styles.css` + `design.md`: 통화 패널(`.call`) 절. 끊기 버튼은 위험 색 토큰, 걸기·받기는 `--brand`. 자막은 채팅 말풍선 규칙(내 말 끝 쪽, 상대 시작 쪽, 논리 속성으로 RTL 반대편)을 따른다. 애니메이션·울림 소리 없음(`design.md` 규칙)
  - i18n: 새 키를 20개 언어 파일에 모두 넣는다(아래)
  - `README.md`: 화면 구성 S-12·C-02 설명, "경로별 대체 정책"에 통화 WS 행, "실서비스와 다른 점"(TURN 없음, 화면이 열려 있어야 받음, 음성 인식은 브라우저 공급자), "상태의 경계"(자막은 서버, 음성은 저장 안 함), 폴더 구조(`api/call`, `api/speech`, `components/CallPanel`), 환경 변수 `VITE_ICE_SERVERS`
- 하지 않는 것
  - 휴대폰 시연용 HTTPS(결정 1이 B가 아니면), TURN 서버, 영상 통화, 통화 녹음, 울림 소리·진동, 푸시 알림
  - 서버 STT(backend 16 결정 1이 B면 이 문서를 다시 쓴다)
  - 번역된 자막을 소리로 읽어 주기(TTS)
  - 채팅 메시지 번역, 센터 로그인, 새 경로
  - `backend/` 코드 수정

## 화면·파일
- 화면: S-12 `/center-request`(전송 완료 뒤), C-02 `/center/cases/:id`. 경로 변경 없음
- API: `WS /api/center/cases/{id}/call?role=worker&token=` / `?role=center`(backend 16)
- 추가: `src/api/call.ts`, `src/api/speech.ts`, `src/components/CallPanel.tsx`
- 수정: `src/api/http.ts`(필요하면 `wsUrl` 재사용만), `src/domain/centerCase.ts`(`Caption`, `CaptionTranslation` 타입), `src/pages/worker/CenterRequest.tsx`, `src/pages/center/Center.tsx`, `src/styles.css`, `src/i18n/*.ts`(20개), `design.md`, `README.md`, `src/vite-env.d.ts`(`VITE_ICE_SERVERS`)
- 새 문구 키(근로자): `callTitle`(센터와 통화), `callIntro`(통화하는 동안 두 사람의 말이 자막으로 남고 기계 번역이 붙습니다), `callStart`, `callAccept`, `callDecline`, `callHangup`, `callMute`, `callUnmute`, `callCalling`(거는 중), `callRinging`(센터에서 전화가 왔습니다), `callConnecting`, `callInCall`, `callEnded`, `callNoAnswer`, `callDeclined`, `callFailed`(연결하지 못했습니다), `callMicDenied`, `callNoCaption`, `callMe`, `callCenter`, `callTranslating`, `callMachineTranslated`

## 완료 기준
- [x] `npm run build` 통과
- [x] 단독 모드: S-12·C-02에 통화가 보이지 않고 WebSocket·마이크 요청이 없다(코드 확인: `isCallAvailable()`이 거짓이면 패널과 `useCall`을 그리지 않는다. 브라우저로는 보지 않았다)
- [ ] API 모드(`VITE_API_BASE=/api npm run dev` + 백엔드, `ANTHROPIC_API_KEY` 있음), `localhost` Chrome 창 두 개(근로자 vi 360px, 센터 1280px): 센터가 걸고 근로자가 받아 서로 목소리가 들린다. 반대로 근로자가 걸어도 된다
- [x] 통화 중 근로자가 베트남어로 말하면 근로자 화면에 원문, 센터 화면에 한국어 번역이 몇 초 안에 붙는다. 센터가 한국어로 말하면 반대로 붙는다. 말하는 중에는 상대 화면에 흐린 줄이 먼저 보인다
- [ ] 끊기·거절·30초 무응답·상대 창 닫기에서 양쪽이 각각의 끝난 이유를 보이고 마이크가 꺼진다(탭의 마이크 표시가 사라진다)
- [ ] 백엔드 키 없이 띄우면 자막은 원문만 쌓이고 통화는 그대로 된다
- [x] 근로자 화면이 없을 때 센터 걸기 버튼이 막히고 이유가 보인다(결정 3이 A일 때)
- [x] ~~통화 뒤 C-02를 새로고침하면 자막이 번역과 함께 다시 보인다~~ → 통화가 끝나도 자막은 화면을 떠나기 전까지 그 자리에 남는다(사용자 결정 2026-10-31, 아래 "문서에서 바꾼 점")
- [ ] 마이크 권한을 막으면 `callMicDenied`가 보이고 화면이 멈추지 않는다. Firefox(음성 인식 없음)에서 통화는 되고 `callNoCaption`이 보인다
- [ ] 근로자 통화 패널을 en·vi·ko·ar(RTL)에서, 센터 패널을 1280px·900px 아래에서 본다
- [x] 콘솔에 자막 본문·SDP·토큰이 찍히지 않는다

## 결과

### 문서에서 바꾼 점
- **자막 기록(사용자 결정 2026-10-31):** 이 문서는 서버 `history`로 C-02 새로고침 뒤에도 자막을 다시 보인다고 했지만, 이미 병합된 backend 16은 자막을 저장하지 않고 `history` 프레임도 없다("하지 않는 것"). backend 16 계약대로 자막은 화면 메모리에만 두고, 통화가 끝나도 화면을 떠나기 전까지 남긴다. 새로고침하면 사라진다. C-02 안내 문구에 그렇게 적었고, README "나중에 붙일 자리"에 통화 자막 기록 행을 더했다
- **문구 키 이름:** `callTitle`·`callHint` 등 `call*` 키는 S-10 전화 스크립트가 이미 쓰고 있어, 새 키는 `liveCall*`로 썼다(`liveCallTitle` … `liveCallMachineTranslated`). 문서의 키 목록에 두 개를 더했다: `liveCallCenterAway`(센터가 화면에 없어 걸 수 없음, 결정 3의 근로자 쪽), `liveCallUnsupported`(HTTP 주소 등 WebRTC·마이크가 없는 브라우저). `callIntro`에는 이어폰 권장 한 줄을 넣었다(메모)
- **신호 형태:** backend 16의 `signal.data`는 서버가 열어 보지 않으므로, 걸기·받기·거절·끊기(`{ call }`), SDP(`{ sdp }`), ICE(`{ ice }`), 말하는 중 글과 확정 문장(`{ speech: { text, final } }`)을 모두 그 안에 담았다. 서버 계약은 바뀌지 않는다. 말하는 중 흐린 줄과 번역 전 "번역 중" 줄은 이 `speech`로 상대에게도 보인다
- **번역 상태 `pending`:** 서버 자막에는 `pending`이 없다(번역이 끝난 뒤 한 번 온다). 확정 문장을 보낸 순간부터 같은 쪽 자막이 올 때까지를 화면에서 "번역 중" 줄(`PendingLine`)로 보인다
- **거는 쪽 offer:** backend 16 메모는 "근로자가 offer"였지만 이 문서대로 거는 쪽이 만든다. 둘이 동시에 걸면 센터 걸기를 살리고 근로자가 받는 쪽이 된다
- **4409(같은 역할이 이미 있음):** 문서에 없던 닫힘 코드다. 멈추지 않고 이유를 보인 채 3초마다 다시 붙는다. 개발 모드 이중 마운트·새로고침에서 옛 연결이 아직 안 끊긴 경우가 있고, 다른 탭을 닫으면 저절로 이어지게 하려고
- **언어 바꾸기:** 통화 중에 앱 언어를 바꿔도 다시 붙지 않는다(받아쓰기 언어만 다음부터 바뀐다). 번역 대상 언어는 서버가 사례 언어로 정하므로 바뀌지 않는다

### 결정
- 받아쓰기 언어 표 `SPEECH_LANGS`는 날짜용 `LOCALES`에서 우즈베크어(`uz-UZ`)·아랍어(`ar-SA`)만 바꿨다
- 음성 인식 서버가 없는 Chromium(Electron·Brave 등)은 `network` 오류를 끝없이 낸다. 결과 없이 3번 이어지면 받아쓰기를 끄고 `liveCallNoCaption`을 보인다(`SPEECH_MAX_NETWORK_ERRORS`)
- 음성이 붙은 뒤 상대가 나가면(`peer present: false`) 바로 끊지 않고 `RTCPeerConnection`이 `disconnected`가 될 때 끝낸다(신호만 잠깐 끊긴 경우 음성 유지). 음성이 붙기 전이면 바로 `peer-left`
- `VITE_ICE_SERVERS`가 JSON 배열이 아니면 경고 한 줄(내용 없이)과 함께 기본 STUN을 쓴다. `[]`이면 STUN 없음(결정 2-B)
- 센터 문구는 끝난 이유를 여섯 가지로 나눠 보이고, 근로자 문구는 끊음·상대 나감을 `liveCallEnded` 하나로 묶었다

### 실행
- `npm run build` → 통과(타입 검사 + 빌드. 500kB 청크 경고는 전부터 있던 것)
- 브라우저: Claude 앱 내장 브라우저, 이 브랜치 백엔드(`fastapi run --port 8001`, LLM 키 있음) + Vite(`VITE_API_BASE=/api`, 5181, 프록시 → 8001)
  - 내장 브라우저는 마이크를 막고, 같은 페이지 안 `RTCPeerConnection` 두 개끼리도 ICE가 `new`에서 움직이지 않는다(환경 제한). 그래서 **진짜 마이크** 대신 확인용으로 페이지에서 `getUserMedia`를 발진기 음성으로, `SpeechRecognition`을 정해 둔 문장을 내는 가짜로 바꾸고, 연결 상태 `connected`를 흉내 내어 통화 중 화면을 확인했다. 앱 코드는 그대로다
  - 마이크 거부(가짜 없이): 센터 걸기 → "마이크를 허용해야…" `notice.warn`, `idle`로 돌아가고 다시 걸 수 있다
  - 센터 → 근로자(vi, 360px): 센터 "거는 중…", 근로자 "Trung tâm đang gọi cho bạn." + 받기·거절 → 받기 → offer·answer·원격 트랙 도착 → ICE가 붙지 않아 약 30초 뒤 양쪽 "통화를 연결하지 못했습니다"(실패 경로)
  - 근로자 → 센터(연결 흉내): 통화 중 + 통화 시간. 근로자 "Tay tôi vẫn còn chảy máu" → 센터 화면에 흐린 줄 "Tay tôi vẫn"이 먼저, 이어 "제 손이 아직도 피가 나고 있어요."(크게) + 원문(작게) · 기계 번역. 센터 "지금 다친 손을 움직일 수 있나요?" → 근로자 화면에 "Bây giờ bạn có thể cử động bàn tay bị thương không?"(크게). 받아쓰기 언어 근로자 `vi-VN`, 센터 `ko-KR`. 서버 로그 `call caption translation=ok` 2줄
  - 음소거(`aria-pressed`, 글이 음소거 해제로) → 센터 끊기: 센터 "통화를 끊었습니다.", 근로자 "Cuộc gọi đã kết thúc.", 자막은 남는다
  - 센터 걸기 → 근로자 거절: 센터 "근로자가 전화를 거절했습니다."
  - 근로자 ar(RTL) 새 사례: 받아쓰기 `ar-SA`, 내 자막이 왼쪽(끝 쪽)·상대가 오른쪽. "يدي ما زالت تنزف" → "손이 아직도 피가 나고 있어요.", 센터 "병원 예약을 도와드릴게요." → 아랍어. 통화 중 en으로 바꿔도 통화·자막이 그대로다
  - 센터가 거는 중에 근로자 탭 닫기 → 센터 "근로자 화면이 닫혀 통화가 끝났습니다." + 걸기 버튼 막힘과 이유
  - 같은 사례 센터 탭 두 개 → 두 번째 탭 4409 안내, 첫 탭을 닫자 3초 안에 이어짐
  - 센터 1280px·880px(한 열, 가로 넘침 없음)
  - 콘솔: `[call]` 줄은 닫힘 코드만. 자막·SDP·토큰 없음. 서버 로그도 `WS … 닫힘 코드 ms`와 `translation=ok`뿐

### 확인하지 못한 것(사용자 확인 필요)
- **실제 음성:** `localhost` Chrome 창 두 개로 서로 목소리가 들리는지, 진짜 받아쓰기로 자막이 쌓이는지(완료 기준 3·4의 음성 부분)
- 끊기·거절·무응답·창 닫기 뒤 탭의 마이크 표시가 사라지는지(코드는 모든 끝에서 트랙을 `stop()`한다). 30초 무응답은 기다려 보지 않았다
- 백엔드 키 없이 원문만 쌓이는지(`skipped`면 원문만 크게 그리는 코드는 있다)
- Firefox에서 `liveCallNoCaption`, 20개 언어 중 Chrome이 인식하지 못하는 언어
- 근로자 ko 화면(번역 없이 원문만)

### 바뀐 화면·파일
- S-12 전송 완료: 채팅 카드 위에 "센터와 통화" 카드. C-02: 상담 채팅 패널 위에 "통화" 패널. 경로 변경 없음
- 추가: `src/api/call.ts`, `src/api/speech.ts`, `src/components/CallPanel.tsx`
- 수정: `src/domain/centerCase.ts`(`Caption`, `CaptionTranslation`, `CAPTION_MAX_LEN`), `src/pages/worker/CenterRequest.tsx`, `src/pages/center/Center.tsx`, `src/styles.css`(`.call*`), `src/i18n/*.ts` 20개(`liveCall*` 24키), `src/vite-env.d.ts`(`VITE_ICE_SERVERS`), `vite.config.ts`(주석), `design.md`("통화"), `README.md`

## 메모
- 휴대폰 시연용 HTTPS는 결정 1대로 `chore/` 항목으로 따로 쓴다
- 위험: Android Chrome에서 통화 마이크(`getUserMedia`)와 `SpeechRecognition`을 동시에 쓰면 인식이 끊기거나 통화 음성이 작아지는 경우가 알려져 있다. 결정 1 A대로면 이 항목에서는 PC로만 확인하고, 휴대폰 HTTPS 항목에서 실기기로 확인한다. 안 되면 backend 16 결정 1 B(서버 STT)를 다시 검토한다
- 스피커로 통화하면 상대 목소리가 내 음성 인식에 다시 들어가 내 자막으로 찍힐 수 있다. 이어폰을 권장하는 한 줄을 `callIntro`에 넣을지 구현 때 본다
- Web Speech API의 언어 지원은 브라우저마다 다르다. 20개 언어 중 인식되지 않는 언어는 구현 때 Chrome에서 확인해 `## 결과`에 적는다
- 새 문구 키의 베트남어는 원어민 검수가 필요하다. en·vi를 뺀 17개 언어는 기계 번역 초안이다(backlog 16)
- 새 문구 24키의 베트남어는 원어민 검수가 필요하다. en·vi·ko를 뺀 17개 언어는 기계 번역 초안이다
- 새 의존성 없음(WebRTC·Web Speech는 브라우저 내장). 결정 1이 B면 `@vitejs/plugin-basic-ssl`을 더하고 이유를 여기에 적는다
