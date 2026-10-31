# 28. 근로자 Google 로그인 연결·비회원 없애기

상태: 진행 중(실제 Google 계정 로그인 확인 남음: 사용자 클라이언트 ID 필요)
의존: backend 21 (근로자 Google 로그인 API), 10 (S-03 로그인 화면), 27 (`src/api/auth.ts`)

## 목표
S-03 로그인 화면의 Google 버튼은 지금 서버를 부르지 않고 프로필 화면으로만 간다. 누구나 "비회원으로 계속"으로 들어올 수도 있다. 사용자가 비회원을 없애고 Google 로그인을 실제로 붙이기로 했다(2026-10-31). API 모드에서 서버가 `WORKER_AUTH=google`이면 Google Identity Services로 받은 ID 토큰을 backend 21로 보내 세션을 만들고, 로그인한 근로자만 앱을 쓴다. 단독 모드와 서버가 로그인을 쓰지 않는 경우에는 지금 데모 버튼을 그대로 두고 비회원 버튼만 뺀다.

## 결정이 필요한 것

1. **로그인 방식을 고르는 기준.** → **권장대로 결정(2026-10-31).** 권장: 근로자 화면에 들어올 때 `getWorkerMe()`를 한 번 부른다.
   - 단독 모드(`VITE_API_BASE` 없음)이거나 서버가 `required: false`면 **데모 로그인**이다. 지금 G 버튼이 프로필 화면으로 가고, 계정 키는 `demo`다. 서버가 없어 토큰을 검증할 수 없고, 발표장 대비 단독 모드는 계속 돌아야 하기 때문이다.
   - `required: true`면 **실제 Google 로그인**이다.
2. **서버가 꺼졌을 때.** → **권장대로 결정(2026-10-31).** 권장: 이 기기에서 로그인한 적이 있으면(기기 저장소에 계정 키가 있으면) 서버를 기다리지 않고 그대로 쓴다. 근로자 데이터는 기기에 있고 판정·안내 경로는 브라우저 함수로 대체되기 때문이다. 처음 로그인은 서버가 있어야 하므로, 실패하면 "Google 로그인을 하지 못했습니다" 문구와 다시 시도 버튼을 보인다. 하단 119 띠는 로그인 화면에서도 그대로 보인다. 데모 로그인으로 몰래 대체하지 않는다(가짜 성공 금지). 서버가 세션이 끝났다고 알려 주면(`account: null`) 로그인 화면으로 보낸다.
3. **Google 버튼 모양.** → **권장대로 결정(2026-10-31).** 권장: 실제 로그인에서는 Google이 그려 주는 공식 버튼(`google.accounts.id.renderButton`)을 쓴다. 설정은 `theme: 'outline'`, `size: 'large'`, `shape: 'pill'`, `text: 'signin_with'`, `locale`은 앱 언어, 너비는 바닥 버튼 폭에 맞춘다. Google 브랜드 규정 때문에 직접 그린 G 버튼으로 실제 로그인을 할 수 없다. 데모 로그인은 지금 `.btn.secondary` + `.mark` G를 그대로 쓴다. One Tap 자동 팝업은 쓰지 않는다.
4. **계정마다 기기 저장소 나누기.** → **권장대로 결정(2026-10-31).** 권장: `umn.device`를 `umn.device.<계정 키>`로 나눈다. 데모 계정의 키는 `demo`이고, 지금 있는 `umn.device`는 처음 읽을 때 `umn.device.demo`로 옮긴다. 마지막 계정 키는 `umn.account`(localStorage)에 둔다. 실제 Google 계정은 빈 저장소로 시작한다.
5. **로그아웃.** → **권장대로 결정(2026-10-31).** 권장: S-13 `/my`에 "로그아웃"을 둔다. 로그아웃하면 서버 세션을 지우고(실제 로그인일 때), `umn.account`와 세션 상태(현재 입력·판정)를 비운 뒤 로그인 화면으로 간다. 계정별 프로필·리포트는 기기에 남긴다(다시 로그인하면 보인다). 지금 있는 "내 데이터 삭제"는 그 계정의 기기 저장소를 지운 뒤 로그아웃까지 한다.

## 범위
- 하는 것
  - `src/api/auth.ts`: `getWorkerMe()`, `loginWithGoogle(credential)`, `logoutWorker()`. 시간 제한은 `AUTH_TIMEOUT_MS`를 그대로 쓴다. 토큰·계정 키를 `console`에 찍지 않는다. 단독 모드에서 `getWorkerMe()`는 요청 없이 `{ required: false, account: null }`이다.
  - `src/api/googleId.ts`(새 파일): Google Identity Services 스크립트(`https://accounts.google.com/gsi/client`)를 한 번만 불러온다. `initialize({ client_id: VITE_GOOGLE_CLIENT_ID, callback, ux_mode: 'popup', auto_select: false })`와 `renderButton`을 감싼다. 스크립트를 불러오지 못하면(오프라인·차단) 실패를 돌려준다. 화면은 이 파일과 `auth.ts`만 부른다(`fetch`·전역 `google`을 화면에서 직접 쓰지 않는다).
  - `src/vite-env.d.ts`: `VITE_GOOGLE_CLIENT_ID`. API 모드에서 서버는 `required: true`인데 이 값이 비어 있으면 로그인 화면에 "로그인 설정이 없습니다" 문구를 보인다(빌드 설정 실수가 바로 보이게).
  - `src/state/AppState.tsx`
    - `mode: 'guest' | 'member'`, `startGuest`, `guestReports`를 지운다.
    - `account: string | null`(+ `loginKind: 'demo' | 'google'`)과 `signIn(account, kind)`, `signOut()`을 둔다.
    - 프로필·리포트·내 사례 id는 계정별 기기 저장소에 둔다(결정 4).
    - `reports`는 늘 계정 저장소에서 읽는다.
  - `src/components/WorkerLayout.tsx`: 진입 순서 가드를 언어 → 동의 → 로그인(`account`) → 프로필(`profile`) → 홈으로 바꾼다. 로그인했지만 프로필이 없으면 `/signup`의 프로필 단계로 보낸다.
  - `src/pages/worker/Onboarding.tsx`(S-03)
    - "비회원으로 계속"을 지운다.
    - 실제 로그인이면 공식 버튼을 쓰고, 성공하면 `signIn` 뒤 프로필 단계로 간다(프로필이 이미 있으면 `next`로 간다).
    - 데모 로그인이면 지금 G 버튼에 `signIn('demo', 'demo')`를 붙인다.
    - 로그인을 기다리는 동안 버튼만 `disabled`로 두고, 실패하면 `notice.warn` 한 줄을 보인다.
    - `loginDemoNote`는 데모 로그인일 때만 보인다.
    - 실제 로그인일 때는 "Google 계정의 이름·이메일은 저장하지 않습니다" 각주를 보인다.
  - 회원/비회원 분기를 지운다: `CenterRequest.tsx`(S-12의 회원만 안내와 `repSavedGuest`), `Report.tsx`(S-11 저장 안내는 늘 `repSaved`), `/my`(S-13의 `modeGuest · myProfileCreate` 줄, 로그아웃 버튼 추가), `WorkerLayout` 앱 바의 `app.mode` 분기.
  - 센터 요청(`src/api/center.ts`의 근로자 전송)이 401을 받으면 로그인 화면으로 보낸다(세션 만료). 쓰던 입력은 남긴다.
  - i18n(20개 언어)
    - 지울 키: `loginGuest`, `modeGuest`, `repSavedGuest`
    - 고칠 키: `consentSensitiveBody`의 비회원 문장. "로그인 정보는 계정을 구분하는 값만 서버에 두고 이름·이메일은 저장하지 않는다"는 뜻으로 바꾼다.
    - 새 키: `loginFailed`, `loginRetry`, `loginNotConfigured`, `loginGoogleNote`, `logout`
  - 문서
    - `README.md`: 화면 구성표 S-01~S-04·S-11·S-12·S-13 줄, 진입 순서 문장, "API 연결"의 경로별 대체 정책(`/api/auth/worker/*`는 대체하지 않는다, 서버가 꺼졌을 때 결정 2), 상태의 경계(계정별 `umn.device.<키>`, `umn.account`, 근로자 세션 쿠키 `fornav_worker`, 비회원 줄 삭제), "실서비스와 다른 점"에 로그인 줄
    - `design.md`: S-03 로그인 화면에 공식 Google 버튼(iframe, 우리 토큰을 쓰지 않는 예외)과 데모 G 버튼 구분
    - `CLAUDE.md`: "근로자 정보는 브라우저에 둔다" 문단의 비회원 리포트·"센터 요청은 회원만" 문장
    - `../app-front/README.md`: 137행 "근로자 화면에는 로그인 세션이 없고" 문장과 진입 순서 가드 문장
- 하지 않는 것
  - Flutter WebView 안의 로그인. Google이 WebView 안 웹 로그인을 막으므로(`disallowed_useragent`) 네이티브 로그인 → 다리로 ID 토큰 전달은 app-front 항목으로 따로 한다. 그 전까지 앱 안에서는 실제 로그인이 안 되고, 서버가 `required: false`인 빌드(데모 로그인)로만 앱을 확인한다.
  - 프로필·리포트를 서버에 저장하기, 기기 사이 동기화, Google 이름·이메일·사진 표시
  - One Tap, 자동 로그인, Google 외 로그인
  - 센터 화면 변경(센터 로그인은 27 그대로)
  - `backend/` 코드 수정
  - 새 npm 의존성. GIS는 스크립트 태그로 불러오고 타입은 쓰는 부분만 `googleId.ts`에 직접 적는다(`@types/google.accounts`를 들이지 않는다).

## 화면·파일
- 화면: S-03 `/signup`(로그인 → 프로필), S-04 `/home`, S-11 `/report/:id`, S-12 `/center-request`, S-13 `/my`. 경로 추가·변경 없음
- API: `GET /api/auth/worker/me`, `POST /api/auth/worker/google`, `POST /api/auth/worker/logout`, `POST /api/center/cases`의 401
- 추가: `src/api/googleId.ts`
- 수정: `src/api/auth.ts`, `src/api/center.ts`, `src/vite-env.d.ts`, `src/state/AppState.tsx`, `src/state/storage.ts`(필요하면 키 옮기기 도우미), `src/components/WorkerLayout.tsx`, `src/pages/worker/Onboarding.tsx`, `src/pages/worker/CenterRequest.tsx`, `src/pages/worker/Report.tsx`, `src/i18n/*.ts`(20개), `README.md`, `design.md`, `CLAUDE.md`, `../app-front/README.md`

## 완료 기준
- [x] `npm run build` 통과. `app-front`도 `npm run build`가 통과한다(근로자 화면을 공유 import하므로).
- [x] 단독 모드: `/signup`에 비회원 버튼이 없고, G 버튼(데모) → 프로필 → `/home`이 된다. `/api/*` 요청이 없다. 새로고침해도 로그인이 유지된다. 지금 `umn.device`에 있던 프로필·리포트가 `umn.device.demo`로 옮겨져 그대로 보인다.
- [x] API 모드 + 서버 `WORKER_AUTH=off`: 단독 모드와 같다. `/api/auth/worker/me`는 한 번만 부른다.
- [x] API 모드 + 서버 `WORKER_AUTH=google`(`CENTER_COOKIE_SECURE=false`, 사용자가 만든 클라이언트 ID), `VITE_GOOGLE_CLIENT_ID` 같은 값:
  - [ ] `/signup`에 공식 Google 버튼만 있다. 실제 Google 계정으로 로그인하면 `fornav_worker` 쿠키가 생기고 프로필 단계 → `/home`으로 간다.
  - [x] 로그인 전에 `/intake`·`/home`으로 바로 들어가면 `/signup`으로 간다. 하단 119 띠는 `/signup`에서도 보인다.
  - [x] 다른 Google 계정으로 다시 로그인하면 앞 계정의 프로필·리포트가 보이지 않는다. 원래 계정으로 돌아오면 다시 보인다.
  - [x] `/my` 로그아웃 → 서버 `/me`가 `account: null`이 되고 로그인 화면으로 간다.
  - [x] S-12 센터 요청이 201이다. 서버 세션을 지우고(`/logout`을 직접 부름) 보내면 로그인 화면으로 가고, 다시 로그인하면 쓰던 입력이 남아 있다.
  - [x] 로그인한 뒤 서버를 끄면 앱을 계속 쓸 수 있다(증상 입력 → 결과는 브라우저 함수로 대체). 로그인한 적 없는 새 시크릿 창에서는 로그인 실패 문구 + 다시 시도 + 119 띠가 보인다.
  - [x] Google 스크립트를 막으면(개발자 도구 요청 차단) 로그인 실패 문구가 보이고 화면이 멈추지 않는다.
- [x] `VITE_GOOGLE_CLIENT_ID`를 비우고 `WORKER_AUTH=google` 서버에 붙이면 "로그인 설정이 없습니다"가 보인다.
- [x] 360px에서 en·vi·ko·ar(RTL)로 `/signup`·`/my`를 보고 가로 스크롤이 없다. 공식 버튼 문구가 앱 언어로 나온다.
- [x] 저장소와 콘솔에 ID 토큰이 없다(`sessionStorage`·`localStorage`·콘솔 검색). 화면 코드가 전역 `google`과 `fetch`를 직접 쓰지 않는다(`grep`).
- [x] i18n 20개 파일에서 `loginGuest`·`modeGuest`·`repSavedGuest`가 사라지고 새 키가 모두 있다(타입 검사).

## 결과

```sh
cd frontend && npm ci && npm run build      # tsc --noEmit + vite build 통과(기존 500kB 청크 경고만)
cd app-front && npm ci && npm run build     # 통과(공유 import)
```

브라우저 확인. Chrome 확장이 연결되지 않아 Playwright(`playwright-core` + 캐시된 Chromium headless shell)로 360px 화면을 돌렸다. 확인 스크립트는 저장소 밖(작업용 폴더)에 두고 커밋하지 않았다.
- 단독 모드: `npx vite --port 5195`
- API 모드: backend 21 브랜치 서버를 `STATIC_DIR`로 프론트 빌드(`VITE_API_BASE=/api VITE_GOOGLE_CLIENT_ID=test-client…`)와 같은 출처로 띄웠다(8767). 설정은 `WORKER_AUTH=google CENTER_COOKIE_SECURE=false DB_PATH=<임시 파일>`이다.
- 실제 Google 팝업은 쓸 수 없어서 두 가지를 바꿔 끼웠다. 서버의 ID 토큰 검증기만 가짜(`dev-token-a`·`dev-token-b` → 서로 다른 sub)로 바꿨고, 브라우저에서는 `window.google.accounts.id`를 미리 넣어 공식 버튼 자리에 "Google A/B/틀린 토큰" 버튼을 그리게 했다. 그 밖의 코드 경로(`googleId.ts` → `loginWithGoogle` → `/api/auth/worker/google` → 쿠키 → `AppState`)는 실제와 같다.

| 점검 | 결과 |
|---|---|
| 단독 모드 | `/intake`로 바로 가면 `/signup?next=/intake`로 간다. 비회원 버튼이 없다. 데모 G 버튼 + 데모 각주 + 119 띠. G → 프로필 → `/home`. `umn.account`={key:demo,kind:demo}, `umn.device.demo`에 프로필. 새로고침해도 `/home`. `/api/*` 요청 0 |
| 옛 기기 저장소 | `umn.device`(1985년생 프로필, 사례 id 하나)를 넣고 데모 로그인 → `umn.device`가 없어지고 `umn.device.demo`로 옮겨졌다. 홈 나 줄에 1985 |
| 서버 `WORKER_AUTH=off` | 단독과 같은 데모 로그인 → `/home`. `/api/auth/worker/me`는 페이지를 열 때마다 한 번 |
| `google`: 로그인 | 데모 G 없이 `.gsi-button`만. 틀린 토큰 → "Could not sign in", 화면 그대로. 계정 A → `fornav_worker`(HttpOnly), `umn.account`={32자 키, google} → 프로필 → `/home` |
| `google`: 계정 바꾸기 | A 로그아웃 → 서버 `/me` `account: null` → `/signup`(next 없음). B 로그인 → 빈 프로필 단계(A의 생년월일 없음). B 저장 → 홈에 B 프로필. 다시 A → 프로필 단계 없이 `/home`에 A 프로필. 계정별 저장소 2개 |
| `google`: 센터 요청 | 201 전송 완료. 화면에 머문 채 서버 세션만 지우고 보내기 → `/signup?next=/center-request?type=interpret`. 다시 로그인 → S-12로 돌아오고 "통역"이 골라져 있다 |
| 서버 꺼짐 | 로그인한 기기는 `/api/*`를 모두 막아도 `/home`·`/intake`가 열린다. 처음 기기는 "Could not sign in" + 다시 시도 + 119 띠. 서버를 되살리고 다시 시도 → Google 버튼 |
| Google 스크립트 막힘 | `accounts.google.com` 차단 → 10초 안에 실패 문구 + 다시 시도 |
| 클라이언트 ID 없는 빌드 | "Sign-in is not set up for this app yet." Google 스크립트 요청 0 |
| 실제 Google 스크립트 | 가짜 없이 테스트 클라이언트 ID로 열면 Google이 공식 버튼을 그린다(ko에서 "Google 계정으로 로그인", 알약 모양, 폭 328px). 로그인 자체는 실제 클라이언트 ID가 있어야 해서 하지 않았다 |
| 언어·폭 | 360px에서 en·vi·ko·ar·my·ru로 `/signup`(단독·API)과 `/my`를 열었고 가로 스크롤이 없다. 공식 버튼 locale은 앱 언어(en-GB, vi-VN, ko-KR, ar-AE, my-MM, ru-RU) |
| 토큰 노출 | `localStorage`·`sessionStorage`에 `dev-token` 문자열이 없다. 화면(`pages/`·`components/`)에 `window.google`·`fetch(`가 없다(grep) |

- 바뀐 화면·경로: S-03 `/signup`(비회원 없음, 실제·데모 로그인, 실패·설정 없음 안내), S-04 나 줄(비회원 줄 없음), S-11 저장 안내(늘 저장됨), S-12(회원만 안내 카드 없음, 세션 끝 401 → 로그인), S-13(로그아웃 버튼, 비회원 안내 없음). 진입 가드가 로그인 → 프로필까지 본다. 경로 추가 없음

정한 것
- **진입 가드가 가던 주소를 `next`에 담는다.** 처음에는 S-12가 401을 받으면 직접 `/signup?next=…`로 보냈다. 그런데 계정을 비우는 상태 변경이 라우터 이동보다 먼저 그려져서, 가드가 `next` 없이 한 번 더 보냈다. 그래서 가드가 `pathname + search`를 `next`로 붙이게 했다. S-12는 고른 요청 종류를 주소(`?type=`)에도 두고, 401이면 `endSession`만 부른다. 직접 주소로 들어온 사람(`/intake`)도 로그인 뒤 그리로 간다
- **로그아웃·지우기는 먼저 로그인 화면으로 옮기고(`navigate(…, { flushSync: true })`) 계정을 비운다.** 순서가 바뀌면 가드가 `/my`를 `next`로 달아, 다시 로그인한 사람이 `/my`로 간다
- **프로필 단계 판단**: 로그인하고 프로필까지 있는 채로 `/signup`에 들어오면 수정 단계다(`/my`의 프로필 수정). 이 판단은 들어올 때 하고, 계정이 비면 푼다. 계정이 바뀌면 입력칸을 그 계정의 프로필(없으면 빈 값)로 다시 채워 앞 계정 값이 남지 않게 한다
- **센터 요청 401은 센터 직원 세션 처리(`center.ts`의 `call`)를 거치지 않는다.** `sendCase`가 `requestJson`을 직접 부르고 401을 그대로 던진다. 근로자 세션 끝이 센터 접수함 목록을 비우지 않게 하기 위해서다
- **세션이 끝나 로그인하고 돌아와도 연락처는 다시 적는다.** README "상태의 경계"(연락처는 브라우저에 남기지 않는다) 때문이다. 증상 입력은 세션에, 요청 종류는 주소에 남는다
- 서버 로그인 상태는 `api/auth.ts`의 작은 저장소(`useWorkerAuth`, `useSyncExternalStore`)에 둔다. `WorkerLayout`이 이 상태를 기기 계정과 맞춘다. 서버 세션이 없으면 `endSession`, 계정이 다르거나 데모 계정이면 서버 계정으로 바꾼다. 서버를 확인하지 못하면 아무것도 바꾸지 않는다
- 공식 버튼은 iframe이라 서버로 보내는 동안 막을 수 없다. 그동안은 버튼 대신 막힌 `.btn.secondary.block.big`을 보인다
- 새 키 `loginRetry`는 만들지 않고 기존 `retry`("다시 시도")를 쓴다
- 비회원 흐름이 없어져 쓰이지 않게 된 키도 지웠다: `cenNeedMember`, `cenMakeProfile`, `myProfileGuestHint`, `myProfileCreate`, `myDeleted`. 지운 뒤에는 로그인 화면으로 가므로 "지웠습니다" 안내가 보일 자리가 없다
- 새 클래스는 `.gsi-button`(가운데 정렬, 높이 44px 이상) 하나다. `design.md`에 "근로자 로그인" 절을 더했다
- `/my`에 "로그아웃"(`.btn.secondary`)을 두고, "내 데이터 지우기"는 `.btn.ghost`로 낮췄다. 지우기는 그 계정의 기기 저장소를 지우고 로그아웃한다

남은 것
- 사용자가 만든 웹 클라이언트 ID로 실제 Google 계정 로그인(위 완료 기준에서 열려 있는 줄). backend 21의 남은 확인과 같은 일이다

## 메모
- 백엔드 문서가 말하는 근로자 로그인 API는 backend 21이다. 이 항목은 21이 병합된 뒤 시작한다.
- 사용자 준비(구현 전): backend 21 `## 메모`의 Google Cloud 설정. 클라이언트 ID는 프론트 빌드 `VITE_GOOGLE_CLIENT_ID`와 서버 `GOOGLE_CLIENT_ID`에 같은 값을 넣는다. 맥미니 배포 빌드(`deploy`의 프론트 빌드 단계)에도 이 변수를 넣어야 한다.
- 새 문구 5개와 고친 `consentSensitiveBody`는 20개 언어 모두 원어민 검수가 필요하다. 특히 베트남어.
- 비회원을 없애면 처음 쓰는 사람은 Google 로그인(네트워크)이 되어야 증상 확인까지 간다. 119 띠는 늘 보이지만 판정 화면은 로그인 뒤에 있다. 사용자가 알고 고른 것이다(2026-10-31).
- 앱(Flutter) 네이티브 로그인: app-front 다리에 `type: "googleSignIn"` 요청 → 호스트가 `google_sign_in`으로 받은 ID 토큰을 돌려주고, 웹이 같은 `loginWithGoogle`을 부르는 방식이 유력하다. 이때 서버 `aud`에 Android·iOS 클라이언트 ID를 더해야 한다(backend 21 "하지 않는 것"). app-front backlog로 따로 쓴다.
- Content-Security-Policy를 두게 되면 `accounts.google.com`의 스크립트·프레임·연결을 허용해야 한다(지금은 CSP가 없다).
