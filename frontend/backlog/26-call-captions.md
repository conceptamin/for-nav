# 26. 근로자·센터 인터넷 통화와 실시간 번역 자막

상태: 대기
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
- [ ] `npm run build` 통과
- [ ] 단독 모드: S-12·C-02에 통화가 보이지 않고 WebSocket·마이크 요청이 없다
- [ ] API 모드(`VITE_API_BASE=/api npm run dev` + 백엔드, `ANTHROPIC_API_KEY` 있음), `localhost` Chrome 창 두 개(근로자 vi 360px, 센터 1280px): 센터가 걸고 근로자가 받아 서로 목소리가 들린다. 반대로 근로자가 걸어도 된다
- [ ] 통화 중 근로자가 베트남어로 말하면 근로자 화면에 원문, 센터 화면에 한국어 번역이 몇 초 안에 붙는다. 센터가 한국어로 말하면 반대로 붙는다. 말하는 중에는 상대 화면에 흐린 줄이 먼저 보인다
- [ ] 끊기·거절·30초 무응답·상대 창 닫기에서 양쪽이 각각의 끝난 이유를 보이고 마이크가 꺼진다(탭의 마이크 표시가 사라진다)
- [ ] 백엔드 키 없이 띄우면 자막은 원문만 쌓이고 통화는 그대로 된다
- [ ] 근로자 화면이 없을 때 센터 걸기 버튼이 막히고 이유가 보인다(결정 3이 A일 때)
- [ ] 통화 뒤 C-02를 새로고침하면 자막이 번역과 함께 다시 보인다
- [ ] 마이크 권한을 막으면 `callMicDenied`가 보이고 화면이 멈추지 않는다. Firefox(음성 인식 없음)에서 통화는 되고 `callNoCaption`이 보인다
- [ ] 근로자 통화 패널을 en·vi·ko·ar(RTL)에서, 센터 패널을 1280px·900px 아래에서 본다
- [ ] 콘솔에 자막 본문·SDP·토큰이 찍히지 않는다

## 결과
(구현 후 작성)

## 메모
- 휴대폰 시연용 HTTPS는 결정 1대로 `chore/` 항목으로 따로 쓴다
- 위험: Android Chrome에서 통화 마이크(`getUserMedia`)와 `SpeechRecognition`을 동시에 쓰면 인식이 끊기거나 통화 음성이 작아지는 경우가 알려져 있다. 결정 1 A대로면 이 항목에서는 PC로만 확인하고, 휴대폰 HTTPS 항목에서 실기기로 확인한다. 안 되면 backend 16 결정 1 B(서버 STT)를 다시 검토한다
- 스피커로 통화하면 상대 목소리가 내 음성 인식에 다시 들어가 내 자막으로 찍힐 수 있다. 이어폰을 권장하는 한 줄을 `callIntro`에 넣을지 구현 때 본다
- Web Speech API의 언어 지원은 브라우저마다 다르다. 20개 언어 중 인식되지 않는 언어는 구현 때 Chrome에서 확인해 `## 결과`에 적는다
- 새 문구 키의 베트남어는 원어민 검수가 필요하다. en·vi를 뺀 17개 언어는 기계 번역 초안이다(backlog 16)
- 새 의존성 없음(WebRTC·Web Speech는 브라우저 내장). 결정 1이 B면 `@vitejs/plugin-basic-ssl`을 더하고 이유를 여기에 적는다
