# 56. 통화 ICE 서버를 서버에서 받기(TURN)

상태: 완료 (운영 TURN 키 설정과 이동통신망 실기기 통화 확인 남음)
의존: 26(통화), backend 31(`GET …/call/ice-servers`)

## 목표
운영에서 통화가 "연결 중…"에서 멈춘 뒤 "연결 실패"로 끝난다(2026-10-31 사용자 보고). 음성 연결이 빌드에 박힌 Google 공개 STUN 하나뿐이라 이동통신망·회사 방화벽 뒤에서는 두 기기가 서로 닿지 못한다. 걸거나 받을 때마다 서버(backend 31)가 주는 Cloudflare TURN 자격 증명을 받아 음성 연결에 넣는다.

## 결정 (2026-10-31 사용자)
1. TURN은 Cloudflare TURN을 쓰고, 키는 서버에만 둔다. 프론트는 짧게 유효한 자격 증명을 서버에서 받는다(빌드에 자격 증명을 넣지 않는다)

## 범위
- 하는 것
  - `useCall`: 걸기(`start`)·받기(`accept`) 때 마이크 요청과 함께 `GET /api/center/cases/{id}/call/ice-servers?role=&token=`을 부르고, 음성 연결(`RTCPeerConnection`)을 만들 때 그 결과를 기다려 쓴다
  - 빈 목록(서버에 TURN 없음)·실패·4초 초과면 지금 값(`VITE_ICE_SERVERS` 또는 Google STUN)으로 건다. 통화가 이 경로 때문에 막히지 않는다
  - 기다리는 사이 통화가 끝나거나 화면을 떠나면 음성 연결을 만들지 않는다
  - 로그: 실패하면 `[api] /center/cases/{id}/call/ice-servers <code> → 브라우저 함수로 대체` 한 줄(주소의 토큰·자격 증명은 찍지 않는다)
  - `README.md`: 통화 확인 문단, "실서비스와 다른 점" 통화 행
- 하지 않는 것
  - 서버(`backend/`) 코드. backend 31로 따로 한다
  - 통화 중 자격 증명 갱신, 화면 문구·통화 상태 규칙 변경. 새 문구 키 없음

## 화면·파일
- S-12·센터 채팅 시트 통화, C-02 통화(화면 변화 없음)
- `src/api/call.ts`, `README.md`

## 완료 기준
- [x] `npm run build`, `cd ../app-front && npm run build` 통과
- [x] API 모드에서 근로자(360px)·센터(1280px)가 통화로 붙고, 양쪽 모두 걸기·받기 때 ice-servers를 한 번 부른다
- [x] 서버가 목록을 주면 음성 연결이 그 목록을 쓰고, 빈 목록·요청 실패면 STUN 기본값으로 붙는다
- [x] 콘솔에 채팅 토큰이 찍히지 않는다
- [ ] 운영에서 TURN을 켠 뒤 근로자 휴대폰(LTE·5G)과 센터 PC가 통화로 붙는다 — 사용자 키 발급 후

## 결과
- `npm run build` → 통과, `cd ../app-front && npm run build` → 통과
- 브라우저(Playwright 헤드리스 Chromium, 가짜 마이크): backend 31 브랜치 `backend`(TURN 꺼짐)를 8767에, `VITE_API_BASE=/api` Vite를 5193에 띄우고 `POST /api/center/cases`로 사례를 만든 뒤 근로자(360px, en, `/my`에서 그 요청을 눌러 시트 채팅 보기)와 센터 C-02(1280px)를 열었다. `RTCPeerConnection`을 감싸 받은 설정을 기록했다
  1. 서버 TURN 꺼짐(빈 목록): 센터 `전화 걸기` → 근로자 `Answer` → 센터 `통화 중`·근로자 `On a call`. 양쪽 ice-servers 한 번씩(`role=center`, `role=worker&token=…`), 설정은 `stun:stun.l.google.com:19302`
  2. ice-servers 응답을 `[{ urls: ['stun:127.0.0.1:3999'] }]`로 바꿈: 같은 흐름으로 붙고 양쪽 설정이 그 목록이다
  3. ice-servers 요청을 끊음: 같은 흐름으로 붙고 설정은 Google STUN, 콘솔에 위 대체 한 줄(토큰 없음)
- backend 31 브랜치 서버를 `TURN=cloudflare`와 틀린 키로 띄워 부르면 Cloudflare가 404를 주고 응답은 `200 {"iceServers":[]}`(`no-store`), 서버 로그는 `turn issue failed: http_404` 한 줄이다
- 결정: 서버가 준 빈 목록은 "서버에 TURN 없음"이라 프론트 기본값으로 바꾼다(`VITE_ICE_SERVERS=[]`의 "STUN 없음"과 다르다). 기다리는 시간은 서버의 Cloudflare 제한(3초)보다 조금 긴 4초

## 메모
- backend 31이 먼저 배포되지 않아도 깨지지 않는다(404 → STUN 기본값)
- 근로자 앱(app-front)은 같은 `useCall`을 쓰므로 함께 바뀐다
