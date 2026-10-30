# 19. 휴대폰 시연용 HTTPS 주소

상태: 대기
의존: 13(맥미니 배포), 08(같은 출처 서빙), 17(센터 직원 로그인)

## 목표
휴대폰으로 시연할 수 있게 맥미니 서버를 공개 HTTPS 주소로도 연다. 지금 맥미니는 `http://<맥미니 IP>:8000/`만 있어서 휴대폰 브라우저가 마이크(`getUserMedia`)와 음성 인식을 열지 않고, 근로자·센터 통화(frontend 26)를 휴대폰에서 쓸 수 없다. 또 센터 세션 쿠키는 기본이 `Secure`(`CENTER_COOKIE_SECURE=true`, backend 17)라 HTTP 주소에서는 센터 로그인이 유지되지 않는다. 서버 코드는 바꾸지 않고 맥미니 앞에 Tailscale Funnel을 둔다. frontend 26 결정 1-A에서 "휴대폰 HTTPS는 따로 한다"고 넘긴 일이다.

## 결정이 필요한 것

1. **HTTPS를 붙이는 방법.** → **B로 결정(2026-10-31).**
   - A. Tailscale Serve. tailnet 안에서만 열린다. 시연 기기마다 Tailscale 앱이 있어야 해 관객 휴대폰으로는 열 수 없다
   - **B. Tailscale Funnel.** 맥미니에서 `tailscale funnel --bg --https=443 http://127.0.0.1:8000`이면 `https://<맥미니 이름>.<tailnet>.ts.net/`이 **인터넷에 공개**된다. 정식 인증서(Let's Encrypt, 자동 갱신), 공유기 포트를 열지 않음, WebSocket(`wss`) 그대로. 관객 휴대폰도 앱 없이 연다. 대신 누구나 접근하므로 아래 "공개 주소 규칙"을 지킨다
   - C. Cloudflare 임시 터널(`cloudflared`). 새 의존성, 다시 띄울 때마다 주소가 바뀐다
   - D. 자체 서명 인증서. 휴대폰마다 경고·루트 인증서 설치, iOS Safari 마이크가 불안정하다
2. **HTTP 주소를 남길지.** 권장: 남긴다. 같은 Wi-Fi의 `http://<IP>:8000/`(backend 08)은 그대로 둔다. Funnel은 그 앞에 하나 더 있는 입구다
3. **공개 시간.** 권장: **리허설·발표 때만 켜고 끝나면 끈다**(`tailscale funnel --https=443 off`). LLM 경로에 호출 제한이 없어 상시 공개하면 비용·남용 위험이 있다(아래 "공개 주소 규칙"). 상시 공개가 필요하면 호출 제한 항목을 먼저 한다

## 공개 주소 규칙
Funnel 주소를 켜기 전에 확인한다. README 절에 그대로 옮긴다.

| 무엇 | 왜 | 어떻게 |
|---|---|---|
| **센터 로그인 켜기** | `CENTER_AUTH=off`(기본)이면 센터 경로(`/api/center/cases` 목록·상세·상태 변경, `/reset`, `/stats`)와 센터 채팅·통화 연결이 로그인 없이 열린다. 공개 주소에서는 누구나 실제 전송 사례 요약을 읽고 데모를 초기화할 수 있다 | 맥미니 `backend/.env`에 `CENTER_AUTH=email`, `MAIL_PROVIDER=resend`와 키, 직원 이메일 등록(backend 17 README). `CENTER_COOKIE_SECURE=true`(기본) 그대로 |
| 공개 시간 줄이기 | 근로자 경로(`/api/extract`, `/api/report/*`, `/api/visit-helper`)와 통화 자막 번역은 로그인 없이 LLM을 부른다(설계상 근로자는 비회원도 쓴다). 호출 제한이 없다 | 결정 3. 켠 시간과 끈 시간을 `## 결과`에 적는다. LLM 공급자 콘솔에 사용 한도(예산 알림)를 건다 |
| 로그 확인 | 공개 중 이상한 호출이 몰리는지 본다 | `pm2 logs for-nav`의 `app.access` 줄(경로·상태·ms만 있고 본문은 없다) |
| 시연 데이터만 | 실제 근로자 정보를 넣지 않는다 | 발표 전에 접수함 초기화(`POST /api/center/reset`, 로그인 뒤 C-01 버튼) |

## 범위
- 하는 것
  - `backend/README.md` "맥미니 배포" 아래 "휴대폰 시연 HTTPS(공개)" 절
    - 준비: 맥미니에 Tailscale 설치·로그인, 관리 화면에서 MagicDNS와 HTTPS 인증서 켜기, tailnet 정책에 이 기기의 Funnel 허용(`nodeAttrs`의 `funnel`)
    - 위 "공개 주소 규칙" 표
    - 켜기·확인·끄기: `tailscale funnel --bg --https=443 http://127.0.0.1:8000`, `tailscale funnel status`, `tailscale funnel --https=443 off`. 첫 접속 때 인증서 발급에 몇 초 걸리고, 공개 DNS가 퍼지기까지 몇 분 걸릴 수 있다는 것
    - 휴대폰 통화 시연 순서(근로자 휴대폰 S-12 ↔ PC 센터 C-02 로그인 상태), 이어폰 권장
  - `backend/README.md` "실행"의 환경 변수 표: `CENTER_AUTH`에 "공개 주소(Funnel)에서는 `email` 필수" 한 줄
  - 맥미니에서 실제로 켜고 아래 완료 기준을 확인한 뒤 `## 결과`에 기기·브라우저별로 적는다
  - backend 08의 "휴대폰 확인 남음"과 backend 17의 "맥미니 실제 메일 확인 남음"을 이 주소로 함께 확인하면 각 문서 `## 결과`에도 한 줄씩 적는다
- 하지 않는 것
  - 서버 코드·설정 기본값 변경. `CENTER_AUTH` 기본값(`off`)도 그대로다(로컬 개발·같은 Wi-Fi 시연용). 같은 출처 서빙(08)이라 `CORS_ORIGINS`도 바꿀 일이 없다
  - LLM 경로 호출 제한(IP별 횟수 등). 상시 공개가 필요해지면 새 항목으로 한다(`## 메모`)
  - 도메인 구매, 공유기 포트 열기
  - TURN 서버(README "나중에 붙일 자리"의 "통화 연결(TURN)", 따로 한다)
  - pm2·`deploy.sh`·배포 워크플로 변경. Funnel 설정은 맥미니에 남고(`--bg`) 배포와 관계없다
  - 프론트 Vite 개발 서버 HTTPS(frontend 26 결정 1-B)

## API·파일
- API 변경 없음
- 수정: `backend/README.md`("맥미니 배포" 아래 절, 환경 변수 표 `CENTER_AUTH` 설명), 맥미니의 `backend/.env`(커밋하지 않는다)

## 완료 기준
- [ ] Funnel을 켠 뒤 Tailscale에 붙지 않은 기기(휴대폰 LTE)에서 `https://<맥미니>.<tailnet>.ts.net/api/health`가 200이다
- [ ] 같은 주소에서 로그인 없이 `GET /api/center/cases`가 401이고, `/center`를 열면 C-00 로그인으로 간다(`CENTER_AUTH=email` 확인)
- [ ] Android Chrome과 iPhone Safari에서 근로자 화면 `/`가 인증서 경고 없이 열린다
- [ ] 센터 로그인(실제 메일 코드) 뒤 새로고침해도 로그인이 유지된다
- [ ] 상담 채팅과 통화 신호가 `wss://…/api/center/cases/{id}/chat`·`/call`로 붙는다(근로자 휴대폰 S-12와 PC C-02에서 서로 메시지가 오간다)
- [ ] 근로자 휴대폰(vi, LTE) ↔ PC 센터(Wi-Fi) 통화: 마이크 권한 요청이 뜨고, 서로 목소리가 들리고, 받아쓰기 자막과 번역이 양쪽에 붙는다. 다른 망끼리 STUN만으로 붙는지, Android Chrome에서 통화 마이크와 음성 인식을 함께 쓸 때 인식이 끊기는지 `## 결과`에 적는다(frontend 26 `## 메모`의 위험)
- [ ] `tailscale funnel --https=443 off` 뒤 같은 주소가 더 이상 열리지 않는다
- [ ] `backend/README.md` 절이 위 순서대로 따라 할 수 있게 적혀 있다

## 결과
(구현 후 작성)

## 메모
- 이동통신망끼리(휴대폰 LTE ↔ 휴대폰 LTE)는 STUN만으로 통화가 안 붙을 수 있다. 공개 주소라 관객 휴대폰끼리 통화할 일이 생기면 TURN 항목을 먼저 한다. 완료 기준의 LTE ↔ Wi-Fi 결과가 그 판단 근거다
- LLM 호출 제한(상시 공개가 필요해질 때의 새 항목): 근로자 경로·자막 번역에 IP별 분당 횟수 제한과 하루 총량, 넘으면 LLM 없이 기본 템플릿·원문으로 대체(지금 실패 동작과 같아 프론트는 바뀌지 않는다)
- 휴대폰에서 받아쓰기가 통화와 함께 안 되면 backend 16 결정 1-B(서버 음성 인식)를 다시 검토한다. 그때는 새 항목이다
