# 31. 통화 TURN 자격 증명

상태: 완료 (코드·테스트 완료, 운영 TURN 키 설정과 이동통신망 실기기 통화 확인 남음)
의존: 16(통화 시그널링)

## 목표
운영에서 통화가 "연결 중…"에서 멈춘 뒤 "연결 실패"로 끝난다(2026-10-31 사용자 보고). 신호 연결(WebSocket)은 붙지만 음성(WebRTC)은 Google 공개 STUN 하나로만 길을 찾아서, 이동통신망(대칭 NAT)이나 회사 방화벽 뒤에서는 두 기기가 서로 닿지 못한다. README "나중에 붙일 자리"의 "통화 연결(TURN)"을 붙여, 직접 닿지 못하면 Cloudflare TURN이 음성을 중계하게 한다.

## 결정 (2026-10-31 사용자)
1. TURN은 Cloudflare TURN(관리형)을 쓴다. 맥미니 coturn(공유기 UDP 포트 포워딩 필요, Cloudflare 터널은 UDP를 지나지 않음)과 고정 자격 증명을 프론트 빌드에 넣는 방식은 쓰지 않는다
2. TURN 키는 서버에만 두고, 서버가 짧게 유효한 자격 증명을 만들어 그 사례의 근로자·센터에게만 준다

## 범위
- 하는 것
  - `GET /api/center/cases/{id}/call/ice-servers?role=&token=`: 통화 WebSocket과 같은 검사(`_chat_denied`) 뒤 `{ iceServers }`. 거절은 HTTP `404`·`403`·`401`
  - `app/turn.py`: `TurnIssuer` 프로토콜, `CloudflareTurn`(`POST https://rtc.live.cloudflare.com/v1/turn/keys/{키 ID}/credentials/generate-ice-servers`, `Authorization: Bearer`, `{ "ttl": TURN_TTL_S }`, 시간 제한 3초, 재시도 없음), 응답 거르기(53번 포트 주소, `urls`·`username`·`credential` 밖의 필드)
  - 실패해도 통화를 막지 않는다: TURN 꺼짐·설정 모자람·발급 실패는 `{ "iceServers": [] }`(프론트가 STUN 기본값으로 건다)
  - 설정 `TURN`(`off`|`cloudflare`), `TURN_KEY_ID`, `TURN_API_TOKEN`(repr에서 뺀다), `TURN_TTL_S`(기본 14400초)
  - 응답 `Cache-Control: no-store`. 로그는 `turn off: …`(시작), `turn issue failed: <종류>`만
  - `README.md`(기술 스택 통화 줄, 폴더 구조, API 표와 설명, 환경 변수 표, 맥미니 배포 "통화 TURN 켜기", 나중에 붙일 자리), `.env.example`
- 하지 않는 것
  - 프론트 코드(`useCall`이 이 경로를 부르는 것). frontend 56으로 따로 한다(backend `CLAUDE.md` "프론트·모델링과의 경계")
  - 통화 중 자격 증명 갱신(`setConfiguration`), 통화가 끝난 뒤 자격 증명 철회(`…/credentials/{username}/revoke`). 유효 시간(4시간)이 통화 한 번보다 길어 지금은 필요 없다
  - 서버 캐시. 통화를 걸고 받을 때만 부르므로 부를 때마다 새로 받는다
  - Cloudflare TURN 키 만들기(사용자가 대시보드에서 한다)

## API·파일
- 새 경로: `GET /api/center/cases/{id}/call/ice-servers` (README 예시)
- 새 파일: `app/turn.py`, `tests/test_turn.py`, 이 문서
- 수정: `app/settings.py`, `app/schemas.py`(`IceServer`, `IceServersResponse`), `app/routers/center.py`(경로, `_same_site`·`_chat_denied`가 `HTTPConnection`을 받게), `app/main.py`(`app.state.turn`), `tests/fakes.py`(`FakeTurnIssuer`), `README.md`, `.env.example`
- 새 의존성 없음(`httpx`는 이미 있다)

## 완료 기준
- [x] `uv run ruff check . && uv run ruff format --check .` 통과
- [x] `uv run pytest` 통과(네트워크 없이, Cloudflare는 `httpx.MockTransport`)
- [x] 근로자(토큰 맞음)·센터(`CENTER_AUTH=off`)는 목록을 받고, 없는 사례 404·틀린 토큰 403·직원 세션 없음 401이며 거절된 요청으로는 발급하지 않는다
- [x] TURN 꺼짐·발급 실패는 `{"iceServers": []}`이고 로그에 종류만 남는다
- [x] Cloudflare 요청 주소·헤더·본문이 문서와 같고, 53번 포트 주소와 모르는 필드를 뺀다
- [x] 설정 repr·로그·예외에 API 토큰이 없다
- [ ] 운영 `.env`에 TURN 키를 넣은 뒤 근로자 휴대폰(LTE·5G)과 센터 PC가 통화로 붙는다 — 사용자 키 발급 후

## 결과
- `uv run ruff check . && uv run ruff format --check .` → 통과
- `uv run pytest` → 3000개 통과(이 항목 `tests/test_turn.py` 14개 포함)
- 바뀐 API: `GET /api/center/cases/{id}/call/ice-servers` 추가. 기존 경로·프레임은 그대로다
- 결정: 빈 목록을 "서버에 TURN 없음"의 뜻으로 쓴다(프론트 `VITE_ICE_SERVERS=[]`의 "STUN 없음"과 다르다. 프론트는 서버가 준 빈 목록을 자기 기본값으로 바꾼다). 응답을 막지 않게 3초 시간 제한·재시도 없음

## 메모
- Cloudflare 문서(2026-10-31 확인): 응답은 `201`, `iceServers`는 STUN 항목 하나와 TURN 항목 하나(`turn:…:3478/443?transport=udp`, `…:3478/80?transport=tcp`, `turns:…:5349/443?transport=tcp`). SFU 없이 TURN만 쓰면 Cloudflare에서 나가는 트래픽 1GB당 $0.05
- 근로자 앱(Flutter WebView)도 같은 웹 코드라 frontend 56만 들어가면 함께 바뀐다
