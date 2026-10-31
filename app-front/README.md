# 울산 외국인 의료 내비게이터 — 앱 프론트(Flutter WebView 안의 근로자 화면)

근로자 화면을 **Flutter 앱의 WebView 안에서** 돌리기 위한 웹앱(Vite + React + TypeScript)이다. 화면 자체는 `../frontend/`의 근로자 화면(S-01~S-13, `/guide`)과 같은 것을 보여 주고, 이 폴더가 더하는 것은 **네이티브 앱 껍데기(호스트)와 주고받는 다리(bridge)**와 WebView에서만 필요한 설정이다. 센터 화면(C-00~C-03)은 PC용이므로 여기에 두지 않는다.

왜 따로 두는가.

- 웹 프론트(`frontend/`)는 브라우저 주소로 열리는 데모·발표용이고 센터 화면까지 한 앱이다. 앱 스토어에 올릴 근로자 앱은 WebView 한 장 안에서 돌며, 전화 걸기·외부 링크·뒤로 가기·안전 영역·권한처럼 **브라우저가 알아서 해 주던 일을 호스트가 대신 해야 한다.** 그 경계를 `frontend/` 코드에 섞지 않고 이 폴더에 모은다.
- 호스트가 없는 보통 브라우저에서 열어도 그대로 동작해야 한다(아래 "호스트가 없을 때"). 그래야 PC 브라우저로 개발·확인하고, 같은 빌드를 웹에도 둘 수 있다.

이 폴더의 문서는 역할이 나뉜다.

| 문서 | 정하는 것 |
|---|---|
| `README.md` (이 문서) | 무엇을 만드는지 — 범위, 실행, 폴더, 호스트 계약(bridge), API 연결, 상태의 경계, Flutter 쪽에서 할 일, 결정·미결 사항 |
| `design.md` | 화면을 어떻게 그리는지 — `frontend/design.md`를 그대로 따르고, WebView에서만 더 지키는 것 |
| `CLAUDE.md` | 코드로 옮길 때 지키는 규칙 |
| `backlog/` | 무엇을 언제 만드는지. 항목 하나가 PR 하나다 |

## 범위

| 포함 | 제외 |
|---|---|
| 근로자 화면 전부(S-01~S-13, `/guide`). 화면·규칙·문구는 `frontend/`와 같다(backlog 02에서 가져온다) | 센터 화면(C-00~C-03). 센터 직원은 PC 브라우저로 `frontend/`를 쓴다 |
| 호스트 계약: 감지, 메시지 형식, 외부 링크·전화, 뒤로 가기, 안전 영역, 기기 언어 | Flutter 프로젝트 자체(`../app/`, backlog 03) |
| WebView에서만 필요한 설정(뷰포트, 탭 하이라이트, 당겨서 튕김, 안전 영역 패딩) | 네이티브 UI(네이티브 탭 바·네비게이션). 화면은 모두 WebView 안이다 |
| 호스트가 없는 브라우저에서의 동일 동작 | 푸시 알림, 앱 스토어 배포 절차(미정, "나중에 붙일 자리") |

## 실행

```sh
cd app-front
npm install
npm run dev        # http://localhost:5181 — 단독 모드(브라우저 안 규칙·mock만, 네트워크 요청 없음)
npm run build      # 타입 검사 + 정적 빌드(dist/)
```

백엔드와 함께 띄우는 API 모드는 `frontend/`와 같다. Vite 프록시가 `/api`(WebSocket 포함)를 `:8000`으로 넘기므로 CORS 설정이 필요 없다.

```sh
uv run --directory ../backend fastapi dev app/main.py   # http://localhost:8000
VITE_API_BASE=/api npm run dev
```

- `/`부터 근로자 화면이 `frontend/`와 같이 뜬다(S-01 언어 선택부터). 센터 경로(`/center*`)는 없고 `/`로 돌아간다. 호스트 연결 확인 화면은 `/__host`다(메뉴에 없다).
- `frontend/src`를 공유 import하므로 **`frontend/`의 `node_modules`는 필요 없다.** 이 폴더의 `npm install`만으로 빌드된다(`tsconfig.json`의 `paths`가 react·react-dom·react-router를 이 폴더의 것으로 고정한다).
- 휴대폰 WebView에서 열려면 Flutter 앱(`../app/`, 실행은 `app/README.md`)이 이 주소를 불러온다. 개발 중에는 같은 Wi-Fi의 폰에서 `http://<맥 IP>:5181/`로 열어도 되고(`npm run dev -- --host`), PC 브라우저의 기기 모드(360px)로도 대부분 확인할 수 있다. 호스트가 있을 때만 다른 동작(외부 링크·뒤로 가기)은 실제 앱에서 확인한다.

## 폴더 구조

```text
app-front/
  CLAUDE.md  README.md  design.md  backlog/
  package.json  package-lock.json  vite.config.ts  tsconfig.json  index.html
  src/
    main.tsx          경로 표. frontend/src/main.tsx의 근로자 경로와 같은 순서·화면 ID. 화면·레이아웃·상태·스타일은 @fe(= ../frontend/src)에서 import한다
    bridge/           호스트 계약의 구현. host(감지·send·receive·onBack·안전 영역 변수), links(외부 링크·전화 가로채기), back(Android 뒤로 가기 규칙), HostProvider(useHost). 화면은 useHost()만 부른다
    pages/            이 앱만의 화면. HostCheck(/__host) 하나. 근로자 화면은 여기 두지 않는다
    styles.css        WebView 덧붙임(안전 영역 --inset-*, 터치, overscroll)과 /__host 스타일. 토큰·컴포넌트는 @fe/styles.css 그대로
    vite-env.d.ts     Vite 환경 변수 타입
```

**근로자 화면은 `frontend/src`를 공유 import한다**(backlog 02 결정, 2026-10-31). 별칭 `@fe` → `../frontend/src`(`vite.config.ts`의 `resolve.alias`와 `tsconfig.json`의 `paths`), `resolve.dedupe`로 React를 하나로 묶고, `publicDir`을 `../frontend/public`으로 두어 로고·국기가 같은 절대 경로로 나온다. 그래서 `frontend/src/domain/`이 원본인 것, 화면·문구·스타일이 `frontend/`와 한 글자도 다르지 않은 것이 구조로 보장된다. 이 폴더에 규칙·템플릿·문구·화면을 새로 쓰지 않고, 바꿔야 하면 `frontend/` 브랜치로 한다. `frontend/`가 이 파일들을 옮기면 이 앱 빌드가 깨지므로 `frontend/CLAUDE.md` "경계"에 그 사실이 적혀 있다.

## 호스트 계약(bridge)

웹(이 앱)과 호스트(Flutter) 사이의 약속이다. 구현은 `src/bridge/`, Flutter 쪽은 아래 "Flutter 쪽에서 할 일". 계약은 `protocol: 1`로 시작하고, 서로 모르는 `type`은 무시한다(앞뒤 버전이 섞여도 멈추지 않게).

### 감지

호스트가 있다는 것은 **호스트가 미리 넣어 둔 전송 통로가 `window`에 있다**는 뜻이다. 사용자 에이전트 문자열로 판단하지 않는다.

| 통로 | 조건 | 보내는 방법 |
|---|---|---|
| `webview_flutter` JavaScript 채널 | `window.ForNav.postMessage`가 함수다(채널 이름 `ForNav`) | `window.ForNav.postMessage(JSON 문자열)` |
| `flutter_inappwebview` 핸들러 | `window.flutter_inappwebview.callHandler`가 함수다 | `window.flutter_inappwebview.callHandler('ForNav', JSON 문자열)` |
| 없음 | 둘 다 없다 | 보통 브라우저. 보내지 않는다 |

채널은 문서가 만들어질 때(document start) 생기므로 첫 렌더에서 바로 안다. 늦게 생긴 통로(브라우저에서 흉내 낼 때)도 첫 메시지를 주고받는 순간 같은 길로 감지한다. 호스트(`../app/`)는 `webview_flutter`를 쓴다(backlog 03). 웹 쪽은 둘 다 받으므로 호스트가 라이브러리를 바꿔도 웹은 그대로다.

### 메시지 형식

양방향 모두 JSON 객체 하나다. `type`과 내용 필드만 있고, 요청-응답 짝은 없다(필요하면 `type`을 둘로 나눈다).

```json
{ "protocol": 1, "type": "openExternal", "url": "tel:119" }
```

**웹 → 호스트** (`src/bridge/host.ts`의 `send()`)

| `type` | 필드 | 언제 | 호스트가 할 일 |
|---|---|---|---|
| `ready` | `path` | 다리가 준비됐을 때 한 번(첫 렌더 직후) | 이 뒤에 `init`을 보낸다. 스플래시(네이티브)가 있다면 여기서 걷는다 |
| `openExternal` | `url` | `tel:`·`mailto:`·`sms:` 링크, 그리고 앱 출처 밖의 `http(s)` 링크(카카오맵 등)를 눌렀을 때 | 기본 전화 앱·브라우저로 연다. WebView 안에서 열지 않는다 |
| `googleSignIn` | 없음 | S-03에서 앱 로그인 버튼을 눌렀을 때. `init.features`에 `googleSignIn`이 있을 때만 보낸다(backlog 06) | `signOut()` 뒤 `authenticate()`로 네이티브 계정 선택을 띄우고, 끝나면 `googleSignInResult`를 한 번 보낸다. 앞 요청이 끝나기 전에 또 오면 앞 요청을 `failed`로 끝낸다 |
| `speechStart` | `lang`(받아쓰기 언어 BCP-47, `frontend/src/api/speech.ts`의 `SPEECH_LANGS` 값) | 통화가 붙어 자막을 켤 때(음소거를 풀 때 포함). `init.features`에 `speech`가 있을 때만 보낸다(backlog 04) | 네이티브 음성 인식을 켜고, `speechStop`이 올 때까지 플랫폼이 스스로 멈추면 다시 켠다. 받아쓴 글은 `speech`로 보낸다. 이미 켜져 있으면 앞 것을 버리고 새 `lang`으로 켠다. 처음 켤 때 마이크·음성 인식 권한을 묻는다 |
| `speechStop` | 없음 | 통화가 끝나거나 음소거할 때 | 음성 인식을 끄고 듣던 말은 버린다. 이 뒤에는 `speech`를 보내지 않는다 |
| `pushRegister` | 없음 | 이 계정에 채팅 토큰이 있는 센터 요청이 있을 때(API 모드). 페이지마다 처음 한 번, 그 뒤에는 토큰이 필요할 때(로그아웃 뒤 다시 로그인 등). `init.features`에 `push`가 있을 때만 보낸다(backlog 07·08, frontend 48) | 알림 권한을 묻고(OS가 처음 한 번만 창을 띄운다), FCM 토큰을 받아 `pushToken`을 한 번 보낸다. 이 뒤 토큰이 바뀌면 `pushToken`을 다시 보낸다 |
| `pushUnregister` | 없음 | 로그아웃·계정 바꾸기·"내 데이터 지우기". 웹이 서버에서 기기를 뺀 뒤 보낸다 | FCM 토큰을 지운다(`deleteToken()`). 응답 없음. 다음 `pushRegister`는 새 토큰을 받는다 |

**호스트 → 웹** (`window.fornav.receive(message)`를 부른다. `message`는 객체 또는 JSON 문자열)

| `type` | 필드 | 언제 | 웹이 할 일 |
|---|---|---|---|
| `init` | `platform`(`android`·`ios`), `appVersion`, `locale`(BCP-47), `insets`(아래), `features`(문자열 배열, 예: `["googleSignIn"]`. 없으면 빈 배열로 본다) | `ready`를 받은 뒤 한 번 | `useHost()`의 값이 채워진다. `locale`은 확인 화면에 보이기만 한다. S-01의 "폰 언어" 제안은 `frontend/`와 같이 `navigator.languages`를 쓰는데, WebView의 `navigator.languages`가 기기 언어를 그대로 주므로 따로 넘길 필요가 없다 |
| `insets` | `insets: { top, right, bottom, left }`(CSS px) | 안전 영역이 바뀔 때(회전, 키보드는 제외) | `:root`의 `--inset-*` 변수를 바꾼다 |
| `googleSignInResult` | 성공: `idToken`(Google ID 토큰 JWT). 실패: `error`(`canceled` \| `failed`) | `googleSignIn`의 응답으로 한 번 | 기다리던 `requestGoogleIdToken()`을 끝낸다. 기다리는 요청이 없으면 무시한다. 토큰을 저장하거나 로그에 찍지 않는다 |
| `speech` | `text`(받아쓴 글), `final`(`true`면 확정 문장, `false`면 말하는 중) | `speechStart`와 `speechStop` 사이, 인식 결과가 올 때마다 | 통화 자막으로 넘긴다(`setHostSpeech`, frontend 37). 확정 문장 뒤에는 말하는 중 글을 빈 글로 지운다. 켜 둔 받아쓰기가 없으면 무시한다. 글을 저장하거나 로그에 찍지 않는다 |
| `speechError` | `error`(`denied`: 마이크·음성 인식 권한 거부 \| `unsupported`: 이 기기·언어로 인식할 수 없음) | 받아쓰기를 계속할 수 없을 때 한 번. 호스트는 이 뒤 음성 인식을 끈다 | 이 통화에서는 다시 켜지 않고 "받아쓰기를 못 하는 브라우저" 안내 줄을 보인다(통화는 그대로다) |
| `pushToken` | 성공: `token`(FCM 등록 토큰). 실패: `error`(`denied`: 알림 권한 거부 \| `failed`: 그 밖) | `pushRegister`의 응답으로 한 번, 그리고 그 뒤 토큰이 바뀔 때(`token`만) | 기다리던 `requestPushToken()`을 끝내고, 요청 없이 온 것은 토큰 갱신으로 넘긴다. 웹은 이 토큰으로 서버에 기기를 등록한다(`POST /api/center/push-devices`, backend 28). 저장하거나 로그에 찍지 않는다 |
| `pushOpen` | `caseId`(사례 id) | 근로자가 센터 알림을 눌러 앱이 열렸을 때, `init` 뒤 한 번 | 이 계정의 사례면 센터 채팅 시트를 그 사례로 연다(frontend 48). 아니면 무시한다. 근로자 화면이 아직 받을 준비가 안 됐으면 다리가 마지막 하나를 30초 동안 들고 있다 |

`init.features`의 모르는 값은 무시한다. 호스트는 빌드에 Google 클라이언트 ID가 없으면 `googleSignIn`을 넣지 않는다(그러면 웹은 GIS 버튼을 그리고, 앱 안에서는 `disallowed_useragent`로 실패해 설정 실수가 바로 보인다). `speech`는 호스트가 음성 인식을 이을 수 있으면 늘 넣는다. 기기에 인식기가 없거나 권한이 거부된 것은 켜 봐야 알므로 `speechError`로 알린다. WebView에서는 Web Speech API로 받아쓸 수 없어서(iOS WKWebView에는 없고, Android WebView에는 `webkitSpeechRecognition`이 있지만 앱이 마이크 권한을 가져도 켜자마자 `not-allowed`로 끝난다, backlog 04 결과) 앱 안 통화 자막은 이 메시지로만 된다. `push`는 빌드에 Firebase 값(`--dart-define`, `app/README.md` "푸시 알림")이 있고 Firebase가 초기화됐을 때만 넣는다. 없으면 웹은 `pushRegister`를 보내지 않고 지금처럼 앱을 다시 열 때 15초 주기로 상태를 읽는다.

```json
{ "protocol": 1, "type": "googleSignIn" }
{ "protocol": 1, "type": "googleSignInResult", "idToken": "eyJhbGciOiJSUzI1NiIs…" }
{ "protocol": 1, "type": "googleSignInResult", "error": "canceled" }
{ "protocol": 1, "type": "speechStart", "lang": "vi-VN" }
{ "protocol": 1, "type": "speech", "text": "tôi bị đau", "final": false }
{ "protocol": 1, "type": "speechError", "error": "denied" }
{ "protocol": 1, "type": "pushRegister" }
{ "protocol": 1, "type": "pushToken", "token": "dXf3…:APA91b…" }
{ "protocol": 1, "type": "pushToken", "error": "denied" }
{ "protocol": 1, "type": "pushOpen", "caseId": "C-251031-001" }
```

**호스트 → 웹, 동기 호출**

| 함수 | 돌려주는 값 | 언제 |
|---|---|---|
| `window.fornav.onBack()` | `true`면 웹이 처리했다(한 화면 뒤로 갔다). `false`면 더 갈 곳이 없다 | Android 뒤로 가기 버튼. `false`면 호스트가 앱을 뒤로 보내거나 종료한다 |

`window.fornav`는 웹이 만든다. 호스트가 있든 없든 항상 있으므로, 호스트는 `window.fornav?.receive`처럼 있는지 확인만 하고 부르면 된다.

### 외부 링크와 전화

- 화면은 지금처럼 `<a href="tel:119">`, `<a href="https://map.kakao.com/...">`을 쓴다. 다리가 문서 수준에서 클릭을 가로채(`src/bridge/links.ts`) 호스트가 있으면 `openExternal`로 넘기고 기본 동작을 막는다. 호스트가 없으면 아무것도 하지 않아 브라우저가 평소대로 연다.
- 같은 출처의 `http(s)` 링크와 라우터 링크는 가로채지 않는다.
- Flutter 쪽도 `NavigationDelegate`에서 앱 출처 밖 주소를 막고 외부로 연다(아래). 두 겹으로 두는 이유는, 가로채기 전에 일어나는 이동(새로고침 직후 등)이나 `window.location`으로 바꾸는 코드가 WebView 안에서 다른 사이트를 열지 않게 하기 위해서다.
- **119는 어느 경우에도 한 번 누르면 걸려야 한다.** 호스트가 `openExternal`을 아직 처리하지 못하는 상태(초기화 전)라도, 웹은 `tel:` 기본 동작을 막기 전에 호스트가 `init`을 보냈는지 본다. 보내지 않았으면 가로채지 않는다(WebView의 기본 `tel:` 처리에 맡긴다).

### 뒤로 가기

- Android: 호스트가 `onBack()`을 부른다. 규칙은 `src/bridge/back.ts`다. 첫 화면(`/` 언어 선택, `/home`)이면 `false`(호스트가 앱을 뒤로 보낸다). 앱 바에 ←가 있으면 그것을 누른 것과 같게 하고 `true`(S-05처럼 화면이 등록한 단계 되돌리기가 그대로 돈다). 그 밖(앱 바를 숨긴 화면)은 라우터 이력이 있으면 `history.back()`하고 `true`, 없으면 `false`.
- iOS: 가장자리 스와이프는 WebView 설정(`allowsBackForwardNavigationGestures`)으로 켜고 웹은 관여하지 않는다. 앱 바의 ←는 지금처럼 웹이 그린다.
- 근로자 화면의 진입 순서 가드(언어 → 동의 → 로그인 → 프로필)는 `frontend/`와 같다. 뒤로 가기로 가드 앞 단계로 가면 가드가 되돌린다.

### 안전 영역

- `index.html`의 뷰포트에 `viewport-fit=cover`를 둔다. iOS는 `env(safe-area-inset-*)`가 채워진다.
- Android는 호스트가 `init`·`insets`로 값을 주고, 웹은 `:root { --inset-top … }`에 넣는다. 스타일은 `max(env(safe-area-inset-bottom), var(--inset-bottom))`처럼 둘 중 큰 값을 쓴다(`design.md`).
- 하단 119 띠는 안전 영역 **위에** 뜬다(홈 인디케이터와 겹치지 않게).

### 호스트가 없을 때

- 보통 브라우저(PC 개발, 웹 배포)에서는 감지가 실패하고 `useHost().present`가 `false`다. 링크·전화·뒤로 가기는 브라우저 기본 동작, 안전 영역은 `env()`만, 언어는 `navigator.language`다.
- 호스트가 있어야만 보이는 화면·문구를 만들지 않는다. 호스트 전용 기능(`openExternal` 등)은 "없으면 브라우저가 한다"로 설계한다.
- 예외 하나: S-03 로그인 버튼을 그리는 방식. 브라우저는 GIS 공식 버튼, 앱(`features`에 `googleSignIn`)은 네이티브 로그인 버튼이다(backlog 06, frontend 35). Google이 WebView 안 웹 OAuth를 막아 다른 길이 없다. 문구(`loginGoogle`)와 흐름(로그인 → 프로필 → `next`)은 같다.

### 다리로 보내지 않는 것

- 증상 입력·자유 입력·연락처·리포트 본문. 다리는 열고 닫는 신호만 나른다. 예외는 통화 자막의 `speech.text`다(backlog 04): 근로자가 통화에서 소리 내 말한 것을 받아쓴 글로, 브라우저에서도 Web Speech API 공급자를 거쳐 서버(`caption`)로 가는 글이다. 양쪽 모두 저장하거나 로그에 찍지 않는다. 호스트 로그(Flutter `print`)와 웹 `console`에 메시지 본문을 찍지 않는다(`url`은 `tel:`·지도 검색어가 들어 있으므로 호스트도 찍지 않는다).
- 인증 토큰. 근로자 Google 로그인(frontend 28)은 서버 HttpOnly 쿠키(`fornav_worker`)라 세션 토큰은 다리를 타지 않는다. **예외는 `googleSignInResult.idToken` 하나다**(backlog 06): Google이 WebView 안 웹 로그인을 막아(`disallowed_useragent`) 네이티브 로그인으로 받은 ID 토큰을 웹에 한 번 넘긴다. 호스트·웹 모두 저장하거나 로그에 찍지 않고, 웹은 받은 토큰을 서버(`POST /api/auth/worker/google`)에 한 번 보내고 버린다. 센터 직원 로그인은 이 앱 범위 밖이다.
- FCM 기기 토큰(`pushToken.token`)은 인증 토큰이 아니라 이 기기로 알림을 보낼 주소다(backlog 07). 웹은 받은 토큰을 서버(`POST /api/center/push-devices`)에 보내고 메모리에만 둔다(`localStorage`·`sessionStorage`에 쓰지 않는다). `pushOpen.caseId`는 사례 번호일 뿐 내용이 아니다. 둘 다 호스트·웹 로그에 찍지 않는다. 알림 본문은 웹이 정해 서버에 등록한 한 문장이고(backend 28 결정 2), 메시지 내용·상태·이름은 알림에도 다리에도 실리지 않는다.

## API 연결

`frontend/README.md`의 "API 연결"을 그대로 따른다. 두 모드(단독·API), 경로별 대체 정책, 비동기 UX 규칙, 시간 제한 상수가 모두 같다. **응급 판정은 브라우저 규칙이 먼저**이고 서버가 느리거나 없어도 119 안내가 늦어지지 않는다. 이것은 WebView 안에서 더 중요하다(이동통신망, 지하).

WebView라서 다른 것은 **출처**뿐이다.

| 불러오는 곳 | `VITE_API_BASE` | 서버 쪽 설정 |
|---|---|---|
| 개발 서버(`npm run dev`) | `/api`(프록시) | 없음 |
| 백엔드가 같은 출처에서 서빙(맥미니 `STATIC_DIR` 방식, `backend/README.md` "발표용 실행") | `/api` | `STATIC_DIR` 하나로는 `frontend/`와 이 앱을 같이 서빙할 수 없다. 경로(`/app/`)로 나누려면 backend 쪽 항목이 필요하다(아래 "결정이 필요한 것" 2) |
| 다른 출처에 배포(Vercel 등) | 백엔드 절대 주소(`https://…`) | `CORS_ORIGINS`에 이 앱의 출처를 더한다. WebSocket(채팅·통화)은 CORS 대상이 아니라 그대로 붙는다 |
| 앱 안에 번들(backlog 05) | 백엔드 절대 주소 | WebView 안 `file://`·앱 전용 출처라 `CORS_ORIGINS`에 그 출처(또는 `null`)를 더해야 한다. 단독 모드는 네트워크 없이 전부 동작한다 |

## 상태의 경계

`frontend/README.md`의 "상태의 경계"와 같다. 세션 상태는 `sessionStorage`, 기기 상태는 `localStorage`, 서버에는 센터 사례만 있다.

WebView에서 다른 점:

- `sessionStorage`는 WebView가 살아 있는 동안 남고, 앱을 완전히 끄면 사라진다. 현재 입력이 사라지는 시점이 "탭을 닫을 때"에서 "앱을 끌 때"로 바뀌는 것뿐이고 설계는 같다. 로그인한 계정과 프로필·리포트는 localStorage라 앱을 꺼도 남는다.
- `localStorage`는 앱 데이터에 남는다. iOS는 저장 공간이 부족하면 지울 수 있다. `storage.ts` 래퍼가 실패해도 멈추지 않는 것은 같다.
- 호스트는 웹 저장소를 읽거나 쓰지 않는다. 필요한 값은 다리로 주고받는다.
- FCM 기기 토큰은 웹 메모리(`frontend/src/api/push.ts`)에만 있다. 앱을 열 때마다 호스트에서 다시 받아 서버에 등록한다(backlog 08).

## Flutter 쪽에서 할 일

Flutter 프로젝트는 저장소의 `../app/`이다(`webview_flutter`, backlog 03). 실행·확인 방법과 계약 항목별 구현 위치는 `app/README.md` "계약 구현 위치"에 있다. 이 절은 웹이 호스트에 기대하는 것을 호스트 쪽 말로 적은 것이고, 계약이 바뀌면 이 문서를 먼저 고친 뒤 `src/bridge/`와 `app/lib/`를 같은 PR에서 고친다.

- 채널 `ForNav`(JavaScript 채널)를 문서 시작 때 넣는다. 웹은 이것으로 호스트를 감지한다.
- `ready`를 받은 뒤에만 `init`을 보낸다(`window.fornav?.receive({...})`). 페이지 로드 이벤트에는 기대지 않는다.
- `locale`은 기기 첫 번째 언어의 BCP-47 태그다(`PlatformDispatcher.instance.locale.toLanguageTag()`. `Platform.localeName`은 iOS에서 앱 번들 언어로 좁혀진다).
- `insets`는 `MediaQuery.padding`(논리 픽셀 = CSS px, 키보드 제외)이고, 바뀔 때(회전·창 크기) `insets` 메시지로 다시 보낸다.
- `openExternal`과, `NavigationDelegate`에 걸린 앱 출처 밖 이동(`tel:`·`mailto:`·`sms:` 포함)은 막고 외부 앱으로 연다. 앱 출처는 `--dart-define=APP_URL`의 출처 하나다.
- Android 뒤로 가기는 `window.fornav?.onBack?.() ?? false`를 동기로 묻고, `false`면 앱을 뒤로 보낸다. iOS는 WebView의 가장자리 스와이프를 켠다.
- `googleSignIn`은 `google_sign_in`(7.x)으로 받는다. `initialize(clientId: <iOS 클라이언트 ID>, serverClientId: <웹 클라이언트 ID>)`로 ID 토큰의 `aud`가 웹 클라이언트 ID(서버 `GOOGLE_CLIENT_ID`)가 되게 한다. 두 값은 `--dart-define`(`GOOGLE_WEB_CLIENT_ID`, `GOOGLE_IOS_CLIENT_ID`)이고, 있을 때만 `init.features`에 `googleSignIn`을 넣는다. iOS는 역방향 클라이언트 ID URL 스킴도 등록한다(`app/README.md` "Google 로그인").
- `speechStart`·`speechStop`은 `speech_to_text`로 받는다(backlog 04). 플랫폼 인식기는 말이 끊기면 스스로 멈추므로(Android는 몇 초, iOS는 약 1분) `speechStop` 전까지 다시 켠다. 권한 거부·인식기 없음은 `speechError` 한 번으로 알리고 끈다.
- `pushRegister`·`pushUnregister`는 `firebase_messaging`으로 받는다(backlog 07). Firebase 값은 `--dart-define`(`FIREBASE_*`)이고 커밋하지 않는다. 값이 있고 `Firebase.initializeApp`이 성공했을 때만 `init.features`에 `push`를 넣는다. 권한은 `pushRegister`를 받았을 때 묻는다(앱을 처음 열 때 묻지 않는다). 알림을 누르면(`onMessageOpenedApp`·`getInitialMessage()`) `data.kind == "center"`이고 `data.caseId`가 사례 id 형식일 때만 `init` 뒤에 `pushOpen`을 한 번 보낸다. `ready` 전에 누른 것은 마지막 하나만 들고 있다. 앱이 앞에 있을 때 온 알림은 띄우지 않는다.
- 로그에는 메시지 `type`만 남긴다.

호스트가 더 챙겨야 하는 것(웹은 관여하지 않는다):

- **권한**: 계약에는 없다(backlog 04).

  | 무엇 | Android | iOS |
  |---|---|---|
  | 마이크(통화 `getUserMedia`) | `RECORD_AUDIO`. WebView의 권한 요청(`onPermissionRequest`)이 오면 앱 권한을 먼저 받고 허용한다. 거부하면 WebView 요청도 거부해 웹이 `micDenied` 안내를 보인다 | `NSMicrophoneUsageDescription`. 시스템이 권한 창을 띄운다. WebView 요청은 앱 출처일 때만 허용한다 |
  | 음성 인식(받아쓰기) | `RECORD_AUDIO`와 같은 권한. 기기의 음성 인식 서비스(Google 앱)를 쓴다 | `NSSpeechRecognitionUsageDescription` |
  | 알림(푸시, backlog 07) | Android 13+ `POST_NOTIFICATIONS`. `pushRegister`를 받았을 때 묻는다 | Push Notifications capability(`aps-environment`), Background Modes의 Remote notifications. `pushRegister`를 받았을 때 시스템 창이 뜬다 |
  | 사진 선택(S-05 `<input type=file accept=image/*>`) | 앱이 파일 선택기를 구현한다(`setOnShowFileSelector` → 시스템 사진 선택기). 권한이 필요 없다 | WKWebView가 스스로 띄운다. `NSPhotoLibraryUsageDescription`, "사진 찍기"를 고르면 `NSCameraUsageDescription` |
- **HTTPS**: 마이크·WebRTC는 안전한 출처에서만 열린다. 앱이 불러오는 주소는 HTTPS여야 한다(`localhost` 개발 제외).
- 상태 표시줄 색, 화면 방향(세로 고정), 텍스트 크기 배율은 앱 설정이다.

## 나중에 붙일 자리

| 자리 | 지금 | 나중 |
|---|---|---|
| 하단 119 띠의 안전 영역 | `frontend/`의 `env()` 위에 호스트 `--inset-bottom`을 더한다(`src/styles.css`) | Android 실기기에서 값 확인(backlog 03) |
| 번들 배포 | 원격 주소를 불러온다 | 앱 안에 빌드를 넣어 네트워크 없이 단독 모드(backlog 05). `base`를 상대 경로로 빌드할 수 있게 해 둔다 |
| 사진 선택의 카메라 촬영 | Android는 사진 선택기만(iOS는 WKWebView가 "사진 찍기"도 준다) | Android 파일 선택기에 카메라 촬영 더하기(2차) |
| 푸시 | 센터 채팅 답·요청 상태 변경 알림(backlog 07·08, backend 28). 통화는 S-12 화면을 열어 두어야 받는다 | 센터가 걸 때 알림(FCM 데이터 메시지 + 전체 화면 알림·CallKit). 호스트·백엔드 양쪽 항목이 필요하다(미정) |
| 앱 스토어 | 없음 | 심사용 개인정보 처리방침·권한 설명 문구(미정) |

## 결정이 필요한 것

1. **근로자 화면을 어떻게 가져오나(backlog 02).** → **공유 import로 결정(2026-10-31).** `frontend/src`를 별칭 `@fe`로 import한다("폴더 구조"). `tsconfig.json`의 `paths`가 react·react-dom·react-router를 이 폴더의 `node_modules`로 고정하므로 `frontend/node_modules` 없이 빌드된다. `frontend/` 쪽 파일 이동이 이 앱 빌드를 깨뜨릴 수 있는 것은 `frontend/CLAUDE.md` "경계"에 적었고, CI 잡은 `chore/` 별도다.
2. **배포 출처.** 같은 출처(`/app/` 경로로 백엔드가 서빙, backend 항목 필요) / 다른 출처(Vercel 등 + `CORS_ORIGINS`) / 앱 안 번들. 1차 권장은 다른 출처(지금 `frontend/`와 같은 방식, 서버 코드 변경 없음)이고, 발표가 맥미니 한 대라면 같은 출처가 낫다. Flutter 앱은 주소를 `--dart-define=APP_URL=`로 받으므로(backlog 03, 2026-10-31) 어느 쪽을 골라도 앱 코드는 바뀌지 않는다. → **같은 출처, 하위 경로 대신 호스트로 결정(2026-10-31, backend 22).** 맥미니가 `app.for-nav.com`으로 온 요청에 이 앱의 빌드를, `www.for-nav.com`에는 `frontend/` 빌드를 준다. `/api`는 같은 출처다. Flutter 앱의 운영 주소는 `app/env/prod.json`이다.
3. **Flutter 프로젝트 위치.** → **이 저장소의 `app/`으로 결정(2026-10-31, backlog 03).** 계약 문서와 웹·호스트를 같은 PR에서 고칠 수 있다.
4. **WebView 라이브러리.** → **`webview_flutter`로 결정(2026-10-31, backlog 03).** 공식이고 가볍다. 파일 선택기·권한은 backlog 04에서 직접 붙인다. 웹은 `flutter_inappwebview`도 감지하므로 바꿔도 웹은 그대로다.

## 확인이 필요한 값

- `frontend/README.md`의 "확인이 필요한 값"이 그대로 적용된다(센터 운영 시간, 카카오맵 링크, 기관 번호, 정보 기준일, 번역 검수).
- 앱 이름·번들 ID·스토어 계정(미정). 앱 이름은 `frontend` backlog 18의 "for nav"를 따른다.
- 최소 지원 OS. 권장은 Android 8(WebView 자동 갱신 대상) / iOS 15(`env()`·`dvh`·WebRTC 음성이 모두 되는 선). 더 낮추면 `design.md`의 단위를 다시 본다.

## 실서비스와 다른 점

| 항목 | 지금 | 실서비스 |
|---|---|---|
| 호스트 | `../app/`(개발 주소를 `--dart-define`으로 불러온다. 번들·서명·스토어 설정 없음) | Android·iOS 앱 |
| 화면 | 근로자 화면 전부(`frontend/` 공유 import) + `/__host` | 같음. 네이티브 화면은 없다 |
| 알림 | 앱에서만(FCM, backlog 07·08). 단독 웹앱(`www.for-nav.com`)·브라우저에는 웹 푸시가 없고 다시 열 때 15초 주기로 읽는다. iOS는 Apple Developer 계정·APNs 키가 있어야 받는다 | 같음, iOS 배포 키 준비 |
| 근로자 로그인 | 앱 안에서는 네이티브 Google 로그인(backlog 06). Android 디버그 키 SHA-1만 등록했다. 스토어 배포 키 SHA-1·Apple 로그인(심사 지침 4.8)은 없다 | 배포 키 등록, Apple 로그인 여부는 스토어 배포 항목에서 정한다 |
| 받아쓰기 | 호스트 음성 인식(`speech_to_text`: Android는 기기의 음성 인식 서비스, iOS는 Apple 음성 인식). 지원 언어는 기기마다 다르다 | 같음 또는 서버 음성 인식(미정) |
| 테스트 | `npm run build`(타입 검사)뿐. 다리는 `/__host` 화면에서 눈으로 확인. 근로자 화면의 규칙은 `frontend/`의 백엔드 동기화 테스트가 지킨다 | — |
| CI | `.github/workflows/ci.yml`에 이 폴더 잡이 아직 없다(`chore/` 영역 별도 작업) | PR마다 `npm run build` |
