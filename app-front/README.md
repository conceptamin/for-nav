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
| 호스트 계약: 감지, 메시지 형식, 외부 링크·전화, 뒤로 가기, 안전 영역, 기기 언어 | Flutter 프로젝트 자체(어디에 둘지는 backlog 03의 결정 사항) |
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

- 지금(backlog 01)은 호스트 연결 확인 화면 `/__host` 하나만 있다. `/`는 거기로 보낸다. 근로자 화면은 backlog 02부터다.
- 휴대폰 WebView에서 열려면 Flutter 앱(backlog 03)이 이 주소를 불러온다. 개발 중에는 같은 Wi-Fi의 폰에서 `http://<맥 IP>:5181/`로 열어도 되고(`npm run dev -- --host`), PC 브라우저의 기기 모드(360px)로도 대부분 확인할 수 있다. 호스트가 있을 때만 다른 동작(외부 링크·뒤로 가기)은 실제 앱에서 확인한다.

## 폴더 구조

```text
app-front/
  CLAUDE.md  README.md  design.md  backlog/
  package.json  package-lock.json  vite.config.ts  tsconfig.json  index.html
  src/
    main.tsx          경로 표. 경로 옆에 화면 ID 주석(frontend와 같은 S-xx)
    bridge/           호스트 계약의 구현. 호스트 감지·메시지 보내기·받기·뒤로 가기·외부 링크 가로채기·안전 영역. 화면은 useHost()만 부른다
    pages/            화면. 지금은 HostCheck(/__host) 하나. 근로자 화면은 backlog 02에서
    styles.css        스타일. 토큰·컴포넌트는 frontend/design.md를 따른다(backlog 02에서 frontend 스타일을 가져오면 WebView용 덧붙임만 남긴다)
    vite-env.d.ts     Vite 환경 변수 타입
```

`frontend/src/domain/`이 규칙·템플릿·어휘의 원본인 것은 여기서도 같다. 이 폴더에 규칙·템플릿·문구를 새로 쓰지 않는다. 가져오는 방법(공유 import인지 복사인지)은 backlog 02의 결정 사항이다.

## 호스트 계약(bridge)

웹(이 앱)과 호스트(Flutter) 사이의 약속이다. 구현은 `src/bridge/`, Flutter 쪽은 아래 "Flutter 쪽에서 할 일". 계약은 `protocol: 1`로 시작하고, 서로 모르는 `type`은 무시한다(앞뒤 버전이 섞여도 멈추지 않게).

### 감지

호스트가 있다는 것은 **호스트가 미리 넣어 둔 전송 통로가 `window`에 있다**는 뜻이다. 사용자 에이전트 문자열로 판단하지 않는다.

| 통로 | 조건 | 보내는 방법 |
|---|---|---|
| `webview_flutter` JavaScript 채널 | `window.ForNav.postMessage`가 함수다(채널 이름 `ForNav`) | `window.ForNav.postMessage(JSON 문자열)` |
| `flutter_inappwebview` 핸들러 | `window.flutter_inappwebview.callHandler`가 함수다 | `window.flutter_inappwebview.callHandler('ForNav', JSON 문자열)` |
| 없음 | 둘 다 없다 | 보통 브라우저. 보내지 않는다 |

채널은 문서가 만들어질 때(document start) 생기므로 첫 렌더에서 바로 안다. 늦게 생긴 통로(브라우저에서 흉내 낼 때)도 첫 메시지를 주고받는 순간 같은 길로 감지한다. 어느 라이브러리를 쓸지는 backlog 03에서 정하되, 웹 쪽은 둘 다 받는다.

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

**호스트 → 웹** (`window.fornav.receive(message)`를 부른다. `message`는 객체 또는 JSON 문자열)

| `type` | 필드 | 언제 | 웹이 할 일 |
|---|---|---|---|
| `init` | `platform`(`android`·`ios`), `appVersion`, `locale`(BCP-47), `insets`(아래) | `ready`를 받은 뒤 한 번 | `useHost()`의 값이 채워진다. `locale`은 S-01의 "폰 언어" 제안에 쓴다(없으면 `navigator.language`) |
| `insets` | `insets: { top, right, bottom, left }`(CSS px) | 안전 영역이 바뀔 때(회전, 키보드는 제외) | `:root`의 `--inset-*` 변수를 바꾼다 |

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

- Android: 호스트가 `onBack()`을 부른다. 웹은 라우터 이력이 있으면 `history.back()`하고 `true`, 첫 화면(`/`, `/home`)이거나 이력이 없으면 `false`.
- iOS: 가장자리 스와이프는 WebView 설정(`allowsBackForwardNavigationGestures`)으로 켜고 웹은 관여하지 않는다. 앱 바의 ←는 지금처럼 웹이 그린다.
- 근로자 화면의 진입 순서 가드(언어 → 동의 → 로그인/비회원)는 `frontend/`와 같다. 뒤로 가기로 가드 앞 단계로 가면 가드가 되돌린다.

### 안전 영역

- `index.html`의 뷰포트에 `viewport-fit=cover`를 둔다. iOS는 `env(safe-area-inset-*)`가 채워진다.
- Android는 호스트가 `init`·`insets`로 값을 주고, 웹은 `:root { --inset-top … }`에 넣는다. 스타일은 `max(env(safe-area-inset-bottom), var(--inset-bottom))`처럼 둘 중 큰 값을 쓴다(`design.md`).
- 하단 119 띠는 안전 영역 **위에** 뜬다(홈 인디케이터와 겹치지 않게).

### 호스트가 없을 때

- 보통 브라우저(PC 개발, 웹 배포)에서는 감지가 실패하고 `useHost().present`가 `false`다. 링크·전화·뒤로 가기는 브라우저 기본 동작, 안전 영역은 `env()`만, 언어는 `navigator.language`다.
- 호스트가 있어야만 보이는 화면·문구를 만들지 않는다. 호스트 전용 기능(`openExternal` 등)은 "없으면 브라우저가 한다"로 설계한다.

### 다리로 보내지 않는 것

- 증상 입력·자유 입력·연락처·리포트 본문. 다리는 열고 닫는 신호만 나른다. 호스트 로그(Flutter `print`)와 웹 `console`에 메시지 본문을 찍지 않는다(`url`은 `tel:`·지도 검색어가 들어 있으므로 호스트도 찍지 않는다).
- 인증 토큰. 근로자 화면에는 로그인 세션이 없고(데모 Google 로그인은 브라우저 안 상태), 센터 직원 로그인은 이 앱 범위 밖이다.

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

- `sessionStorage`는 WebView가 살아 있는 동안 남고, 앱을 완전히 끄면 사라진다. 비회원 입력이 사라지는 시점이 "탭을 닫을 때"에서 "앱을 끌 때"로 바뀌는 것뿐이고 설계는 같다.
- `localStorage`는 앱 데이터에 남는다. iOS는 저장 공간이 부족하면 지울 수 있다. `storage.ts` 래퍼가 실패해도 멈추지 않는 것은 같다.
- 호스트는 웹 저장소를 읽거나 쓰지 않는다. 필요한 값은 다리로 주고받는다.

## Flutter 쪽에서 할 일

Flutter 프로젝트는 이 폴더 밖이다(backlog 03). 이 절은 웹이 기대하는 것을 호스트 쪽 말로 적은 것이고, 아래 예시는 `webview_flutter` 4.x 기준이다. 실제 구현은 backlog 03에서 하고, 계약이 바뀌면 이 문서를 먼저 고친다.

```dart
final appOrigin = Uri.parse(appUrl).origin;
late final WebViewController controller;
controller = WebViewController()
  ..setJavaScriptMode(JavaScriptMode.unrestricted)
  // 웹 → 호스트. 채널 이름 ForNav가 감지 기준이다
  ..addJavaScriptChannel('ForNav', onMessageReceived: (m) {
    final msg = jsonDecode(m.message) as Map<String, dynamic>;
    switch (msg['type']) {
      case 'ready':
        controller.runJavaScript('window.fornav?.receive(${jsonEncode({
          'protocol': 1, 'type': 'init',
          'platform': Platform.isIOS ? 'ios' : 'android',
          'appVersion': packageInfo.version,
          'locale': Platform.localeName.replaceAll('_', '-'),
          'insets': {'top': padding.top, 'right': padding.right, 'bottom': padding.bottom, 'left': padding.left},
        })})');
      case 'openExternal':
        launchUrl(Uri.parse(msg['url'] as String), mode: LaunchMode.externalApplication);
    }
  })
  ..setNavigationDelegate(NavigationDelegate(
    // 앱 출처 밖은 WebView 안에서 열지 않는다(두 번째 겹)
    onNavigationRequest: (req) {
      if (Uri.parse(req.url).origin == appOrigin) return NavigationDecision.navigate;
      launchUrl(Uri.parse(req.url), mode: LaunchMode.externalApplication);
      return NavigationDecision.prevent;
    },
  ))
  ..loadRequest(Uri.parse(appUrl));

// Android 뒤로 가기: 웹이 처리했는지 동기로 묻는다
Future<bool> handleBack() async {
  final r = await controller.runJavaScriptReturningResult('window.fornav?.onBack?.() ?? false');
  return r == true || r == 'true';
}
```

호스트가 더 챙겨야 하는 것(웹은 관여하지 않는다):

- **권한**: 마이크(통화), 카메라·사진(S-05 사진 선택), 파일 선택기. Android WebView는 앱이 권한 요청과 파일 선택기를 구현해야 동작한다. 계약에는 없고 backlog 04에서 다룬다.
- **받아쓰기**: 통화 자막은 브라우저 Web Speech API를 쓰는데 iOS WKWebView에는 없다. 네이티브 음성 인식을 다리로 잇는 것은 backlog 04의 결정 사항이다.
- **HTTPS**: 마이크·WebRTC는 안전한 출처에서만 열린다. 앱이 불러오는 주소는 HTTPS여야 한다(`localhost` 개발 제외).
- 상태 표시줄 색, 화면 방향(세로 고정), 텍스트 크기 배율은 앱 설정이다.

## 나중에 붙일 자리

| 자리 | 지금 | 나중 |
|---|---|---|
| 근로자 화면 | `/__host` 확인 화면만 | backlog 02에서 S-01~S-13 |
| 번들 배포 | 원격 주소를 불러온다 | 앱 안에 빌드를 넣어 네트워크 없이 단독 모드(backlog 05). `base`를 상대 경로로 빌드할 수 있게 해 둔다 |
| 받아쓰기 | 브라우저 Web Speech API(Android WebView는 됨, iOS는 없음) | 호스트 음성 인식 → `type: "speech"` 메시지(backlog 04) |
| 푸시 | 없음. 통화는 S-12 화면을 열어 두어야 받는다 | 센터가 걸 때 알림. 호스트·백엔드 양쪽 항목이 필요하다(미정) |
| 앱 스토어 | 없음 | 심사용 개인정보 처리방침·권한 설명 문구(미정) |

## 결정이 필요한 것

1. **근로자 화면을 어떻게 가져오나(backlog 02).** `frontend/src`의 `pages/`·`components/`·`state/`·`api/`·`domain/`·`i18n/`·`styles.css`를 경로 별칭으로 **공유 import**할지, 이 폴더로 **복사**할지. 권장은 공유 import다. 화면과 규칙의 원본이 하나로 남고, `frontend/`의 수정이 그대로 앱에 반영된다. 대신 두 폴더에 `node_modules`가 둘 다 있어야 하고 React를 하나로 묶는 설정(`resolve.dedupe`)이 필요하며, `frontend/` 쪽 파일 이동이 이 앱 빌드를 깨뜨릴 수 있다(CI가 잡는다).
2. **배포 출처.** 같은 출처(`/app/` 경로로 백엔드가 서빙, backend 항목 필요) / 다른 출처(Vercel 등 + `CORS_ORIGINS`) / 앱 안 번들. 1차 권장은 다른 출처(지금 `frontend/`와 같은 방식, 서버 코드 변경 없음)이고, 발표가 맥미니 한 대라면 같은 출처가 낫다. backlog 03에서 Flutter가 불러올 주소를 정할 때 함께 정한다.
3. **Flutter 프로젝트 위치.** 이 저장소의 `app/`(권장: 계약 문서와 같은 PR에서 고칠 수 있다) / 별도 저장소. backlog 03.
4. **WebView 라이브러리.** `webview_flutter`(공식, 가벼움, 파일 선택기·권한은 직접) / `flutter_inappwebview`(파일 선택기·권한·`onPermissionRequest` 내장, 의존성 큼). 웹은 둘 다 감지하므로 backlog 03에서 정한다.

## 확인이 필요한 값

- `frontend/README.md`의 "확인이 필요한 값"이 그대로 적용된다(센터 운영 시간, 카카오맵 링크, 기관 번호, 정보 기준일, 번역 검수).
- 앱 이름·번들 ID·스토어 계정(미정). 앱 이름은 `frontend` backlog 18의 "for nav"를 따른다.
- 최소 지원 OS. 권장은 Android 8(WebView 자동 갱신 대상) / iOS 15(`env()`·`dvh`·WebRTC 음성이 모두 되는 선). 더 낮추면 `design.md`의 단위를 다시 본다.

## 실서비스와 다른 점

| 항목 | 지금 | 실서비스 |
|---|---|---|
| 호스트 | 없음(브라우저로 확인). Flutter 앱은 backlog 03 | Android·iOS 앱 |
| 화면 | `/__host` 확인 화면 | 근로자 화면 전부 |
| 받아쓰기 | 브라우저 공급자 | 호스트 음성 인식 또는 서버 음성 인식(미정) |
| 테스트 | `npm run build`(타입 검사)뿐. 다리는 `/__host` 화면에서 눈으로 확인 | — |
| CI | `.github/workflows/ci.yml`에 이 폴더 잡이 아직 없다(`chore/` 영역 별도 작업) | PR마다 `npm run build` |
