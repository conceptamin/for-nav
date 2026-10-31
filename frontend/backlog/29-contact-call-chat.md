# 29. 센터 연락 방법을 앱 안 통화·채팅 둘로

상태: 완료
의존: 25 상담 채팅, 26 통화 자막

## 목표
2026-10-31 사용자 결정: 근로자가 지원센터와 연락하는 방법은 **앱 안 센터 통화**(backlog 26)와 **앱 안 채팅**(backlog 25) 둘뿐이다. S-12의 연락 방법 선택(전화·문자·카카오톡·Zalo·센터 방문)과 연락처 입력란을 없애고, 선택지를 통화·채팅 둘로 바꿔 누르면 그 패널로 가게 한다. 하단 119 버튼 오른쪽에 채팅 아이콘을 두어 어느 화면에서나 센터 채팅으로 갈 수 있게 한다.

## 범위
- 하는 것
  - S-12 입력 화면: 연락 방법 선택지를 `통화`(📞 `liveCallTitle`)·`채팅`(💬 `chatTitle`) 둘로 바꾼다. 연락처 입력란(`cenContact`·`cenContactHint`)과 동의 항목 `연락처`를 없앤다
  - S-12 전송 완료 화면: 통화·채팅을 둘 다 쌓아 보이지 않고, 같은 두 선택지로 고른 패널 하나만 보인다. 입력 화면에서 고른 것이 처음 열린다(고르지 않았으면 채팅)
  - 새 경로 `/center-chat`(S-12 연락): 이 기기에서 보낸 가장 최근 요청의 통화·채팅. `?via=call`이면 통화가 먼저 열린다. 로그인·프로필은 진입 가드가 지키고(backlog 28 이후 비회원 없음), 보낸 요청이 없으면 "먼저 요청을 보내 주세요" + S-12 버튼, 단독 모드면 "서버에 연결되어 있을 때만" 안내
  - 하단 띠: 119 버튼을 왼쪽에, 채팅 아이콘 버튼(44px 원, 유리)을 오른쪽에 둔다. 로그인하고 프로필까지 있을 때만(`app.ready`) 보인다. 응급 화면·스플래시에는 지금처럼 띠 전체가 없다
  - i18n: `contact.phone`·`contact.sms`·`contact.kakao`·`contact.zalo`·`contact.visit`·`cenContact`·`cenContactHint`를 20개 언어에서 지운다. 새 키 `talkNoCase`·`talkOffline`을 20개 언어에 넣는다
  - `app-front/src/main.tsx`에 `/center-chat` 경로를 더한다(공유 화면, 빠지면 채팅 아이콘이 `/`로 튕긴다)
  - `README.md` 화면 구성·"연락처" 문장, `design.md` 하단 띠 절
- 하지 않는 것
  - `domain/templates.ts`의 `ContactMethod`, `data/mock.ts`, 센터 화면 C-02의 "연락 희망"·"연락처" 표시, 백엔드 계약(`schemas.py`). 사용자 결정: 이번은 근로자 화면만
  - 기관 전화번호(S-08 근로복지공단·건강보험공단 `tel:`), 병원 전화 대본(S-10), 카카오맵 검색 링크(S-07), 119. 센터 연락 수단이 아니어서 그대로 둔다
  - 채팅 멈춤 문구 `chatStopped`("다른 방법으로 센터에 연락해 주세요") 수정

## 화면·파일
- 경로: `/center-request`(S-12), 새 `/center-chat`(S-12 연락), 하단 띠가 있는 모든 근로자 화면
- API: 그대로(`POST /api/center/cases`, 채팅·통화 WebSocket). 전송 본문의 `contactMethod`·`contact`는 늘 `null`이다
- 파일: `src/pages/worker/CenterRequest.tsx`, `src/components/WorkerLayout.tsx`, `src/main.tsx`, `src/styles.css`, `src/i18n/*.ts`(20개), `README.md`, `design.md`, `app-front/src/main.tsx`

## 완료 기준
- [x] `npm run build` 통과, `cd app-front && npm run build` 통과
- [x] `/center-request` 입력 화면의 연락 방법 선택지가 통화·채팅 둘이고, 연락처 입력란이 없다
- [x] 전송 후(API 모드) 고른 쪽 패널이 열리고, 선택지를 눌러 통화↔채팅을 오간다. 단독 모드에서는 안내 한 줄이 보인다
- [x] 하단 띠에 119(왼쪽)·채팅 아이콘(오른쪽)이 보이고, 아이콘을 누르면 `/center-chat`으로 간다. 보낸 요청이 없으면 S-12로 가는 버튼이 보인다
- [x] 360px 폭, en·vi·ko에서 `/center-request`·`/center-chat`·`/my`의 하단 띠가 넘치지 않는다. ar(RTL)에서 띠 좌우가 뒤집힌다
- [x] 근로자 화면에 센터 연락 수단으로 통화·채팅 외의 것(문자·카카오톡·Zalo·방문·연락처 입력)이 남지 않는다

## 결과
- `cd frontend && npm run build` → 통과(청크 크기 경고만 기존과 같다), `cd app-front && npm run build` → 통과
- 브라우저 360px(dev 서버 5180)
  - 단독 모드 en: `/center-request` 연락 방법 선택지가 📞 Call the centre·💬 Chat with the centre 둘, 연락처 입력란 없음. 전송 후 "서버에 연결되어 있을 때만" 안내 한 줄
  - API 모드 en(로컬 백엔드 :8000, Windows는 `uv run --with tzdata`가 필요했다): 통화를 고르고 전송하면 통화 패널이 먼저 열리고, 선택지로 채팅으로 바뀐다. 하단 채팅 아이콘 → `/center-chat`에 같은 요청 번호의 채팅이 열린다. 보낸 요청이 없으면 "먼저 요청을 보내 주세요" + S-12 버튼
  - vi `/center-request`, ko `/center-chat`, ar·uz `/my`: 하단 띠 넘침 없음. ar은 119가 오른쪽·아이콘이 왼쪽
  - 20개 언어 `bar119` 문구를 띠에 넣어 재 보았다: 모두 높이 44px, 넘침 없음. uz·kk·ky·mn·ne·si는 두 줄로 접힌다
- 결정
  - 선택지 이름은 새 키 없이 기존 `liveCallTitle`·`chatTitle`을 쓴다. 질문 문구 `cenContactMethod`도 그대로 둔다
  - 통화·채팅은 요청을 보낸 뒤에만 붙을 수 있어(토큰이 전송 응답에 있다), 입력 화면의 선택은 전송 후 처음 열 패널을 정한다. 고르지 않으면 채팅이 열린다
  - 전송 완료 화면에 두 패널을 쌓지 않고 고른 하나만 보인다(사용자 요청 "누르면 전화, 채팅으로 갈 수 있게")
  - 119 글자는 자르지 않는다. 아이콘 자리만큼 좁아지면 두 줄로 접는다
  - 연락 희망은 domain `ContactMethod`에 `call`·`chat`이 없어 보내지 않는다(`null`). 센터 C-02에는 새 사례가 "선택 안 함"으로 보인다
- 남은 문제
  - 증상을 넣지 않고 S-12에 들어오면(API 모드) `newIntake()`가 렌더마다 새 id·시각을 만들어 요약 미리보기 키가 계속 바뀌고 `POST /api/report/center`가 끝없이 반복된다. 이번 변경 전부터 있던 문제이고 이 항목 범위 밖이다(새 항목 필요)

## 메모
- 백엔드 `ContactMethod`(`phone`·`sms`·`kakao`·`zalo`·`visit`)와 mock·C-02 표시·`parity.json`은 그대로다. 연락 희망을 센터에 다시 보내려면 `call`·`chat` 값을 `backend/` 브랜치에서 계약부터 바꾸고 `domain/templates.ts`·`data/mock.ts`를 맞춘다
- 새 키 `talkNoCase`·`talkOffline`의 vi 문구는 원어민 검수가 필요하다. en·vi를 뺀 17개 언어는 기계 번역 초안이다(backlog 16)
