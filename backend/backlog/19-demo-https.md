# 19. 휴대폰 시연용 HTTPS 주소

상태: 대기
의존: 13(맥미니 배포), 08(같은 출처 서빙)

## 목표
휴대폰으로 시연할 수 있게 맥미니 서버를 HTTPS 주소로도 연다. 지금 맥미니는 `http://<맥미니 IP>:8000/`만 있어서 휴대폰 브라우저가 마이크(`getUserMedia`)와 음성 인식을 열지 않고, 근로자·센터 통화(frontend 26)를 휴대폰에서 쓸 수 없다. 또 센터 세션 쿠키는 기본이 `Secure`(`CENTER_COOKIE_SECURE=true`, backend 17)라 HTTP 주소에서는 센터 로그인이 유지되지 않는다. 서버 코드는 바꾸지 않고 맥미니 앞에 HTTPS를 둔다. frontend 26 결정 1-A에서 "휴대폰 HTTPS는 따로 한다"고 넘긴 일이다.

## 결정이 필요한 것

1. **HTTPS를 붙이는 방법.** 구현 전에 정한다.
   - **A. Tailscale Serve(권장).** 맥미니에서 `tailscale serve --bg --https=443 http://127.0.0.1:8000` 한 번이면 `https://<맥미니 이름>.<tailnet>.ts.net/`이 생긴다. 정식 인증서(Let's Encrypt, 자동 갱신)라 경고가 없고, 공유기 포트를 열지 않으며, 인터넷에 공개되지 않는다. WebSocket(`wss`)도 그대로 지난다. 새 의존성은 맥미니의 Tailscale 하나다(사용자가 Mac Studio 주피터 접속에 이미 쓰는 도구). 대신 **시연에 쓰는 휴대폰·PC마다 Tailscale 앱을 깔고 같은 tailnet에 로그인**해야 한다. 관객 휴대폰으로는 열 수 없다
   - B. Tailscale Funnel. A와 같은 주소를 인터넷에 공개한다. 관객 휴대폰도 앱 없이 열린다. 대신 누구나 접근하므로 센터 화면은 backend 17 로그인(`CENTER_AUTH=email`)을 반드시 켜야 하고, LLM 호출 비용이 열린 주소에 노출된다(호출 제한 없음)
   - C. Cloudflare 임시 터널(`cloudflared tunnel --url http://127.0.0.1:8000`). 계정 없이 `https://<임의>.trycloudflare.com`이 생긴다. 새 의존성(`cloudflared`), 다시 띄울 때마다 주소가 바뀌고, B처럼 공개된다
   - D. 자체 서명 인증서(Caddy `tls internal`, mkcert). 휴대폰마다 루트 인증서를 설치하거나 경고를 넘겨야 하고, 경고를 넘긴 출처에서 iOS Safari의 마이크·음성 인식이 불안정하다
2. **HTTP 주소를 남길지.** 권장: 남긴다. 같은 Wi-Fi에서 통화·센터 로그인 없이 보는 시연(backend 08)은 지금처럼 `http://<IP>:8000/`로 된다. HTTPS는 그 앞에 하나 더 있는 입구다

## 범위
- 하는 것(결정 1이 A일 때)
  - `backend/README.md` "맥미니 배포" 아래 "휴대폰 시연 HTTPS" 절
    - 준비: 맥미니에 Tailscale 설치·로그인, 관리 화면에서 MagicDNS와 HTTPS 인증서 켜기, 시연 기기에 Tailscale 앱 설치·같은 tailnet 로그인
    - 켜기·확인·끄기 명령(`tailscale serve --bg --https=443 http://127.0.0.1:8000`, `tailscale serve status`, `tailscale serve --https=443 off`), 첫 접속 때 인증서 발급에 몇 초 걸린다는 것
    - 센터 로그인: HTTPS 주소에서는 `CENTER_COOKIE_SECURE=true`(기본) 그대로 쓴다. HTTP 주소에서는 로그인이 유지되지 않으니 로그인을 켠 시연은 HTTPS 주소로 한다
    - 휴대폰 통화 시연 순서(근로자 휴대폰 S-12 ↔ PC 센터 C-02), 이어폰 권장
  - 맥미니에서 실제로 켜고 아래 완료 기준을 확인한 뒤 `## 결과`에 기기·브라우저별로 적는다
  - backend 08의 "휴대폰 확인 남음"과 backend 17의 "맥미니 실제 메일 확인 남음"을 이 주소로 함께 확인할 수 있으면 각 문서 `## 결과`에도 한 줄씩 적는다
- 하지 않는 것
  - 서버 코드·설정 기본값 변경. 같은 출처 서빙(08)이라 `CORS_ORIGINS`도 바꿀 일이 없다
  - 도메인 구매, 공유기 포트 열기, 공개 인터넷 노출(결정 1이 B·C가 아니면)
  - TURN 서버(README "나중에 붙일 자리"의 "통화 연결(TURN)", 따로 한다)
  - pm2·`deploy.sh`·배포 워크플로 변경. Tailscale Serve 설정은 맥미니에 남고(`--bg`) 배포와 관계없다
  - 프론트 Vite 개발 서버 HTTPS(frontend 26 결정 1-B)

## API·파일
- API 변경 없음
- 수정: `backend/README.md`("맥미니 배포" 아래 절, "실행"의 환경 변수 표 `CENTER_COOKIE_SECURE` 설명에 HTTPS 주소 한 줄)
- 결정 1이 A가 아니면 이 절을 다시 쓴다(새 설정 파일·의존성이 생기면 여기에 적는다)

## 완료 기준
- [ ] 맥미니에서 켠 뒤 Tailscale에 붙은 다른 기기에서 `curl -fsS https://<맥미니>.<tailnet>.ts.net/api/health`가 200이다
- [ ] Android Chrome과 iPhone Safari에서 근로자 화면 `/`가 인증서 경고 없이 열린다
- [ ] 상담 채팅과 통화 신호가 `wss://…/api/center/cases/{id}/chat`·`/call`로 붙는다(근로자 휴대폰 S-12와 PC C-02에서 서로 메시지가 오간다)
- [ ] 근로자 휴대폰(vi) ↔ PC 센터 통화: 마이크 권한 요청이 뜨고, 서로 목소리가 들리고, 받아쓰기 자막과 번역이 양쪽에 붙는다. Android Chrome에서 통화 마이크와 음성 인식을 함께 쓸 때 인식이 끊기는지 확인해 `## 결과`에 적는다(frontend 26 `## 메모`의 위험)
- [ ] `CENTER_AUTH=email`로 띄운 맥미니에서 HTTPS 주소로 센터 로그인 뒤 새로고침해도 로그인이 유지된다
- [ ] 맥미니를 다시 켠 뒤에도 `tailscale serve status`에 설정이 남아 있다
- [ ] `backend/README.md` 절이 위 순서대로 따라 할 수 있게 적혀 있다

## 결과
(구현 후 작성)

## 메모
- Tailscale에 붙은 기기끼리는 WebRTC 후보에 Tailscale 주소(100.x)도 올라와, 서로 다른 망(휴대폰 LTE ↔ PC Wi-Fi)이어도 TURN 없이 붙을 수 있다. 실제로 그런지 결과에 적으면 TURN 항목의 필요 여부를 정하는 근거가 된다
- 결정 1이 B(공개)로 바뀌면 LLM 경로에 호출 제한이 없다는 점을 먼저 다룬다(별도 항목)
- 휴대폰에서 받아쓰기가 통화와 함께 안 되면 backend 16 결정 1-B(서버 음성 인식)를 다시 검토한다. 그때는 새 항목이다
