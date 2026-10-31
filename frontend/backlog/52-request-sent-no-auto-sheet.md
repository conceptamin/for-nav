# 52. 센터 요청을 보내도 채팅 시트를 저절로 열지 않기

상태: 완료
의존: 44 센터 요청을 보내면 채팅 시트가 열리게

## 목표
2026-10-31 사용자 결정: "지원센터에 문의"(S-12)에서 보내기를 눌러도 채팅 시트를 바로 열지 않는다. 전송 완료 화면을 먼저 보이고, 거기서 `💬 센터와 대화`를 눌러야 채팅 시트가 열린다. backlog 44의 "보낸 직후 시트를 연다"만 거둔다.

## 범위
- 하는 것
  - S-12 전송 완료 화면의 `CenterTalk`에서 보낸 직후 시트를 여는 효과를 지운다. `💬 센터와 대화` 버튼(시트 열기)은 그대로 둔다
  - 주석과 `README.md` S-12 설명을 고친다
- 하지 않는 것
  - 시트 모양·동작(backlog 39·44의 `chatCallHint`, 최근 요청 고르기), 하단 채팅 아이콘
  - 하단 채팅 아이콘이 연 시트 안에서 보내는 흐름(그 시트는 이미 열려 있어 그대로 채팅으로 이어진다)
  - 단독 모드(`talkOffline` 한 줄 그대로), 문구 키, API

## 화면·파일
- 경로: 그대로(S-12 `/center-request`)
- 파일: `src/pages/worker/CenterRequest.tsx`, `src/components/CenterSheet.tsx`·`src/components/WorkerLayout.tsx`(주석), `README.md`
- 새 문구 키: 없음

## 완료 기준
- [x] `npm run build` 통과, `cd app-front && npm run build` 통과
- [x] API 모드 360px en·vi·ko `/center-request?type=policy`에서 보내기 → 전송 완료 화면이 보이고 채팅 시트는 닫혀 있다(하단 채팅 아이콘 `aria-expanded=false`)
- [x] 전송 완료 화면의 `💬 센터와 대화`를 누르면 시트가 방금 보낸 요청의 채팅으로 열린다
- [x] 단독 모드 en에서 보내면 시트 없이 `talkOffline` 한 줄이다

## 결과
- `npm run build` → 통과. `cd app-front && npm run build` → 통과
- API 모드(백엔드 8767, 근로자 인증 꺼짐) Playwright 360px `/center-request?type=policy`에서 동의 → 보내기
  - en·vi·ko 모두 전송 완료 화면(✅, 요청 번호, 운영 시간 안내)이 보이고 시트는 닫혀 있다(`.sheet` 숨김, `.bar-chat` `aria-expanded=false`)
  - `💬 Chat with the centre` / `💬 Trò chuyện với trung tâm` / `💬 센터와 대화`를 누르면 시트가 열리고(`aria-expanded=true`) 머리의 요청 번호가 방금 보낸 번호와 같으며 채팅 입력줄과 📞 안내가 보인다. 콘솔 오류 없음
- 단독 모드 en: 보내면 시트 없이 `talkOffline` 한 줄, 💬 버튼 없음
- 결정: `useOpenCenterSheet`는 버튼이 계속 쓰므로 남긴다

## 메모
