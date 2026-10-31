# 49. 상담 채팅 말풍선에 번역 보이기

상태: 완료
의존: backend 30(채팅 메시지 번역). 새 필드가 없으면 지금처럼 원문만 보이므로 backend 30보다 먼저 병합돼도 깨지지 않는다

## 목표
backend 30이 채팅 메시지마다 상대 언어 번역(`lang`·`translated`·`translatedLang`·`translation`)을 붙여 보낸다. 근로자와 상담자가 각자 자기 언어로 읽도록 말풍선에 번역을 보이고, "번역 없이 그대로 전달된다"는 안내를 고친다. 통화 자막(`CallPanel`)이 원문·번역을 보이는 규칙을 그대로 따른다.

## 범위
- 하는 것
  - `domain/centerCase.ts`: `ChatMessage`에 선택 필드 넷(`lang?`, `translated?`, `translatedLang?`, `translation?`, 없거나 null이면 번역 없음)
  - `ChatPanel` 말풍선(근로자 시트, 센터 C-02 둘 다)
    - 상대 글: `translation === 'ok'`이면 번역이 본문, 원문은 그 아래 작은 줄(`.chat-sub`). 내 글: 원문이 본문, 번역이 작은 줄. 번역이 없으면 원문 하나만(지금과 같다)
    - 번역이 붙은 말풍선의 작은 줄 앞에 "기계 번역" 표시. 문구는 통화의 `liveCallMachineTranslated`(근로자)·`기계 번역`(센터)을 다시 쓴다
    - 각 줄에 `lang`을 붙인다(화면 읽기 프로그램·글꼴)
  - 보낸 글이 번역을 거쳐 되돌아올 때까지(1~2초) 내 쪽 끝에 "번역 중…" 흐린 말풍선(`.chat-msg.pending`)을 보인다. `useChat`이 보낸 글을 `pending`으로 들고, 서버가 되돌려 준 내 메시지(같은 글)가 오면 하나씩 지운다. 다시 연결·`history`·멈춤 때 비운다. 문구는 통화의 `liveCallTranslating`·`번역 중…`을 다시 쓴다
  - 문구 고치기
    - 근로자 `chatIntro`(20개 언어): "메시지는 번역 없이 그대로 전달됩니다" → "메시지는 상대 언어로 기계 번역되고 원문도 함께 보입니다"
    - 센터 C-02 `chatNote`: "근로자가 쓴 글은 번역 없이 원문 그대로 보입니다" → "근로자가 쓴 글은 한국어로, 센터가 쓴 글은 근로자 언어로 기계 번역되어 원문과 함께 보입니다"
  - `design.md` "상담 채팅" 표에 작은 줄·번역 전 말풍선, `README.md` "확인이 필요한 값"의 `ChatMessage.textKo` 행을 지금 필드로
- 하지 않는 것
  - 원문 보기 토글, 번역 다시 요청
  - 새 문구 키(통화 키를 다시 쓴다). `chatIntro`만 20개 언어 문구가 바뀐다

## 화면·파일
- S-12 센터 채팅 시트, C-02 상담 채팅. 부르는 API는 그대로(`WS /api/center/cases/{id}/chat`)
- 수정: `src/domain/centerCase.ts`, `src/api/chat.ts`, `src/components/ChatPanel.tsx`, `src/components/CenterSheet.tsx`(`workerChatLabels`), `src/pages/center/Center.tsx`(`CHAT_LABELS`, `chatNote`), `src/i18n/*.ts`(`chatIntro`), `src/styles.css`, `design.md`, `README.md`

## 완료 기준
- [x] `npm run build` 통과, `cd app-front && npm run build` 통과
- [x] API 모드 + backend 30 서버(LLM 키 있음)에서 근로자(vi) 시트와 센터 C-02를 함께 열어, 근로자 글이 센터에 한국어 번역 본문 + 베트남어 원문 작은 줄로, 센터 글이 근로자에게 베트남어 번역 본문 + 한국어 원문 작은 줄로 보인다
- [x] 보낸 직후 내 쪽에 "번역 중…" 말풍선이 보이고, 되돌아오면 사라지고 실제 말풍선 하나만 남는다
- [x] LLM 키 없이 띄우면 지금처럼 원문 하나만 보이고 "기계 번역" 표시가 없다
- [x] 360px 시트(vi·ar)에서 가로 넘침이 없다

## 결과

### 문서에서 바꾼 점
- "번역 중" 줄은 `useChat`이 `pending`(보낸 순서의 `{ key, text }`)으로 든다. 되돌아온 내 메시지와 글이 같은 것을 하나 지우고, 같은 것이 없으면 가장 오래된 것을 지운다. `error` 프레임(서버가 받지 않음)도 가장 오래된 것을 지운다. `history`·끊김·사례 바뀜에서 비운다
- LLM이 없으면 서버가 바로 되돌려 줘 "번역 중" 줄은 거의 보이지 않는다(그대로 둔다)

### 실행
- `npm run build` → 통과, `cd app-front && npm run build` → 통과
- 브라우저(Playwright 헤드리스 Chromium). backend 30 브랜치 서버를 `--port 8767`(LLM `claude-haiku-5-5`, 임시 `DB_PATH`)로, Vite를 `VITE_API_BASE=/api` + 프록시 대상만 8767로 바꾼 임시 설정으로 띄웠다. 근로자는 저장소를 채워 데모 계정·프로필·보낸 요청(`chatToken`)이 있는 상태로 `/home` → 하단 채팅 아이콘 → 시트(360px), 센터는 `/center/cases/<id>`(1280px)
  - vi: 근로자 "Tay tôi vẫn còn chảy máu từ sáng nay" 보낸 직후 시트에 흐린 말풍선 + "Đang dịch…" 1개, 되돌아온 뒤 0개·실제 말풍선 1개. 센터 C-02에 본문 "오늘 아침부터 손이 아직도 피가 나고 있어요." + "기계 번역" 작은 줄에 베트남어 원문. 센터 "언제부터 피가 났나요? 사진을 보내 주세요." → 근로자 시트에 본문 "Bạn bị chảy máu từ khi nào? Vui lòng gửi cho tôi một tấm ảnh."(`lang="vi"`) + "Dịch máy" 작은 줄에 한국어 원문. 내 말풍선은 원문 본문 + 번역 작은 줄. 시트 첫 안내가 새 `chatIntro`. 가로 넘침 없음
  - ar(RTL): 같은 흐름, "جارٍ الترجمة…"·"ترجمة آلية", 말풍선 좌우가 뒤집히고 가로 넘침 없음
  - LLM 키 없이 다시 띄운 서버: 양쪽 모두 `.chat-sub` 0개, 원문 하나만(지금과 같다). 서버 로그 `chat translation=skipped` 2줄
- 사용자 백엔드 자리(8000)는 건드리지 않았고, 확인 뒤 8767·5199를 닫았다

### 결정
- "기계 번역"·"번역 중" 문구는 통화 키(`liveCallMachineTranslated`·`liveCallTranslating`)를 다시 쓴다. 새 문구 키는 없고 20개 언어 `chatIntro`만 바뀐다
- 번역 작은 줄은 말풍선 안에 둔다(말풍선 밖에 두면 묶음·읽음 표시 자리와 겹친다)

### 남은 문제
- 바뀐 `chatIntro`(en·vi 포함 20개 언어)는 원어민 검수 전이다(아래 메모)

## 메모
- backend README "나중에 붙일 자리"는 `textKo`를 적었지만 backend 30이 `Caption`과 같은 필드로 바꿨다(사용자 확인 2026-10-31)
- `chatIntro`의 바뀐 문구는 원어민 검수가 필요하다(README "확인이 필요한 값")
