# 27. 센터 직원 로그인 화면

상태: 대기
의존: backend 17 (센터 직원 로그인 API), 03 (센터 경로 전환), 25 (상담 채팅)

## 목표
backend 17로 서버가 센터 경로마다 직원 세션을 확인하게 된다(`CENTER_AUTH=email`일 때). 센터 화면(C-01~C-03)에 앱 디자인 그대로의 로그인 화면을 두어, 직원이 이메일 → 메일로 받은 6자리 코드로 들어오게 한다. Cloudflare Access 로그인 화면을 쓰지 않아 근로자 화면과 같은 디자인을 유지한다.

## 결정이 필요한 것

1. **로그인 경로.** 권장: `/center/login`(화면 ID `C-00`). 센터 레이아웃(`CenterLayout`) 밖의 단독 화면으로 두어 헤더·접수함 폴링이 로그인 전에 돌지 않게 한다. README 화면 구성 표에 행을 더한다.
2. **로그인이 필요한지 아는 방법.** 권장: 센터 화면에 들어올 때 `GET /api/auth/me`를 한 번 부른다. `required: false`(서버가 `CENTER_AUTH=off`)면 지금처럼 바로 보여 주고, `required: true`인데 `email: null`이면 로그인 화면으로 보낸다. 단독 모드(`VITE_API_BASE` 없음)에는 서버가 없으므로 부르지 않고 로그인도 없다.
3. **세션이 중간에 끝났을 때.** 권장: 센터 경로가 401을 받으면(접수함 폴링, 상태 변경, 통계, 초기화) 하던 화면 주소를 `from`에 담아 로그인 화면으로 보낸다. 채팅이 `4401`로 닫히면 채팅 패널 안에 "로그인이 끝났습니다. 다시 로그인해 주세요" 줄과 로그인 링크를 보이고, 쓰던 입력은 남긴다.

## 범위
- 하는 것
  - `src/api/auth.ts`(새 파일): `getMe()`, `requestCode(email)`, `verifyCode(email, code)`, `logout()`. 이메일·코드를 `console`에 찍지 않는다
  - `src/api/http.ts`: `ApiErrorCode`에 `UNAUTHORIZED`·`RATE_LIMITED`. 같은 출처 요청이라 `fetch`의 기본 쿠키 동작(`same-origin`)을 그대로 쓴다(바꾸지 않는다)
  - `src/api/center.ts`: 401이면 폴링을 멈추고 `onUnauthorized` 구독자에게 알린다(화면이 로그인으로 보낸다). 401은 "서버 연결 안 됨" 띠로 보이지 않는다
  - `src/api/chat.ts`: 닫힘 코드 `4401` → `stopReason: 'unauthorized'`, 다시 연결하지 않는다
  - `src/pages/center/Login.tsx`(새 파일, `C-00 /center/login`): 두 단계 한 화면
    - 1단계: 이메일 입력(`type="email"`, `autocomplete="email"`) + "코드 받기". 보내면 "등록된 이메일이면 코드를 보냈습니다. 메일함을 확인해 주세요" (서버와 같이 등록 여부를 드러내지 않는다)
    - 2단계: 6자리 코드(`inputmode="numeric"`, `autocomplete="one-time-code"`, 숫자 6개만) + "로그인", 그 아래 "코드 다시 받기"(60초 동안 남은 초를 보이며 막는다) · "이메일 바꾸기"
    - 성공하면 `from`(센터 경로일 때만, 아니면 `/center`)으로 `replace` 이동
    - 실패 문구: 401 "코드가 맞지 않거나 만료되었습니다", 429 "요청이 너무 많습니다. 잠시 뒤 다시 시도해 주세요", 네트워크 "서버에 연결하지 못했습니다". 입력값은 남긴다(README "비동기 UX 규칙")
  - `CenterLayout`: 들어올 때 `getMe()` 결과를 기다리는 동안 "확인 중" 한 줄만 보이고 접수함 폴링을 시작하지 않는다. 로그인이 필요하면 `/center/login?from=<지금 경로>`로 `replace`. 헤더 오른쪽에 로그인한 이메일과 "로그아웃" 버튼(누르면 `logout()` 뒤 로그인 화면)
  - 문구: 센터 화면은 한국어 고정이므로 `Center.tsx`의 `TEXT`처럼 화면 파일 안 상수로 둔다. i18n 키는 더하지 않는다
  - `styles.css`: `input[type='email']`을 기존 입력 선택자에 더한다. 로그인 카드는 기존 `.card`·`.field`·`.btn`·`.notice`로 그리고 새 색·새 컴포넌트를 만들지 않는다. 필요하면 가운데 정렬 레이아웃 한 줄(`.c-login`)만 더하고 `design.md`에 적는다
  - `src/main.tsx`: 라우트 `{ path: '/center/login', element: <CenterLoginPage /> } // C-00`
  - `README.md`: 화면 구성 표(C-00), "경로별 대체 정책" 표에 `/api/auth/*` 행과 센터 경로 401 처리, 채팅 `4401`, 폴더 구조
- 하지 않는 것
  - 직원 관리 화면, 직원별 권한 표시, 담당자 표시
  - 근로자 화면 변경(근로자 로그인은 지금처럼 데모 Google 로그인/비회원)
  - 단독 모드 로그인(서버가 없다)
  - 다른 출처 API(`VITE_API_BASE`가 절대 주소)에서 쿠키를 보내는 설정(`credentials: 'include'`). backend 17 "하지 않는 것"과 같다
  - `backend/` 코드 수정

## 화면·파일
- 화면: 새 `C-00 /center/login`. C-01~C-03은 경로 변경 없음(로그인 확인과 헤더 로그아웃만 더한다)
- API: `GET /api/auth/me`, `POST /api/auth/code`, `POST /api/auth/verify`, `POST /api/auth/logout`, 센터 경로의 401, 채팅·통화 `4401`
- 추가: `src/api/auth.ts`, `src/pages/center/Login.tsx`
- 수정: `src/main.tsx`, `src/api/http.ts`, `src/api/center.ts`, `src/api/chat.ts`, `src/pages/center/Center.tsx`, `src/styles.css`, `design.md`(바뀌는 경우만), `README.md`

## 완료 기준
- [ ] `npm run build` 통과
- [ ] 단독 모드: `/center`가 지금처럼 바로 열리고 `/api/auth/me` 요청이 없다
- [ ] API 모드 + 서버 `CENTER_AUTH=off`: `/center`가 지금처럼 바로 열리고 헤더에 로그아웃이 없다
- [ ] API 모드 + 서버 `CENTER_AUTH=email`, `MAIL_PROVIDER=console`(backend 17 결정 2), `CENTER_COOKIE_SECURE=false`, 등록한 직원 1명:
  - `/center/cases/<id>`로 바로 들어가면 로그인 화면으로 가고, 서버 출력의 코드로 로그인하면 그 사례 상세로 돌아온다
  - 등록하지 않은 이메일도 같은 안내 문구를 보고, 서버 출력에 코드가 없다
  - 틀린 코드 → 실패 문구, 입력값 유지. "코드 다시 받기"가 60초 동안 막힌다
  - 로그인 뒤 C-01 폴링·C-02 상태 변경·채팅·C-03이 지금처럼 동작한다
  - 로그아웃 → 로그인 화면. 뒤로 가기로 접수함에 돌아가도 다시 로그인 화면으로 간다
  - 로그인한 채로 `scripts/staff.py remove`로 직원을 지우면 2초 안에(다음 폴링) 로그인 화면으로 가고, 열려 있던 채팅은 `4401` 문구를 보인다
- [ ] 로그인 화면을 1280px·360px에서 보고, 근로자 화면과 같은 토큰(색·둥글기·글래스)으로 그려졌는지 확인한다. 개발자 도구 콘솔에 이메일·코드가 찍히지 않는다

## 결과

## 메모
- 센터 헤더의 "근로자 화면 열기 ↗"는 `/`로 간다. 맥미니 배포에서는 `www.for-nav.com/`가 Cloudflare 리디렉션으로 `/center`에 오므로 이 링크가 근로자 화면을 열지 못한다. `https://app.for-nav.com/`을 가리키게 하는 일은 이 항목과 따로 정한다(환경 변수로 둘지, 링크를 뺄지)
- 로그인 화면은 `www.for-nav.com/center/login`에서 열린다. Cloudflare 리디렉션 규칙(`app.`·루트의 `/center*` → `www.`)과 WAF 규칙은 바꾸지 않아도 된다
