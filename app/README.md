# for nav — 근로자 앱 호스트(Flutter)

근로자 화면(`../app-front/`)을 **WebView 한 장으로 불러오는 Flutter 앱**이다. 화면은 모두 웹이고, 이 앱은 웹이 브라우저에 기대던 일(전화·외부 링크·뒤로 가기·안전 영역·기기 언어)을 대신하는 껍데기다. 웹과 주고받는 약속은 `../app-front/README.md` "호스트 계약"이 원본이고, 이 앱은 그 호스트 쪽 구현이다.

- 플랫폼: Android·iOS. 세로 고정
- WebView: `webview_flutter`(공식). 파일 선택기·권한은 app-front backlog 04에서 직접 붙인다
- 근로자 Google 로그인: `google_sign_in` 7.x(네이티브, app-front backlog 06). WebView 안에서는 Google이 웹 로그인을 막는다(`403 disallowed_useragent`)
- Flutter: fvm으로 `3.44.7` 고정(`.fvmrc`)
- 최소 OS: Android `flutter.minSdkVersion`(기본값), iOS 15.0

## 실행

불러올 주소는 코드에 적지 않고 `--dart-define=APP_URL=`로 넘긴다. 이 주소의 **출처**(scheme·host·port)가 "앱 안"이고, 그 밖은 모두 외부 앱으로 연다.

```sh
# 다른 터미널: 웹 개발 서버. Android 에뮬레이터는 IPv4로 붙으므로 127.0.0.1에 연다
cd app-front && npm run dev -- --host 127.0.0.1

cd app
fvm install          # 처음 한 번
fvm flutter pub get

# iOS 시뮬레이터: 맥의 localhost가 그대로 보인다
fvm flutter run -d <시뮬레이터> --dart-define=APP_URL=http://localhost:5181

# Android 에뮬레이터: 호스트 PC는 10.0.2.2다(localhost는 에뮬레이터 자신)
fvm flutter run -d <에뮬레이터> --dart-define=APP_URL=http://10.0.2.2:5181
```

- Vite는 기본으로 `localhost`를 IPv6 `[::1]`에만 열 수 있다. 그러면 iOS 시뮬레이터는 되지만 Android 에뮬레이터는 `10.0.2.2`(호스트의 127.0.0.1)로 닿지 않아 오프라인 안내가 뜬다. 위처럼 `--host 127.0.0.1`로 띄우면 둘 다 된다.
- 확인 화면을 바로 열려면 `APP_URL=http://localhost:5181/__host`처럼 경로를 붙인다. 출처는 같으므로 동작은 같다.
- 같은 Wi-Fi의 실기기는 웹을 `npm run dev -- --host`로 띄우고 `APP_URL=http://<맥 IP>:5181`.
- `APP_URL`을 빠뜨리면 앱이 안내 문구 한 장만 보인다.
- **http는 개발 빌드에서만 열린다.** Android는 `src/debug/AndroidManifest.xml`에서만 `usesCleartextTraffic`을 켠다. iOS는 `NSAllowsLocalNetworking`(localhost·사설 IP)만 연다. 배포 빌드는 HTTPS 주소를 넘긴다(마이크·WebRTC도 안전한 출처에서만 열린다).
- Xcode 27.1에서 `fvm flutter build ios --simulator`는 `lipo -verify_arch`에 아키텍처 두 개를 넘기는 단계에서 실패한다(Flutter 3.44.7 도구 쪽 문제). 활성 아키텍처 하나만 빌드하는 `fvm flutter run`은 된다.

## Google 로그인

서버가 `WORKER_AUTH=google`이면 근로자는 로그인해야 센터 요청을 보낸다. 앱 안에서는 웹 GIS 버튼이 막히므로, 앱이 네이티브 계정 선택으로 ID 토큰을 받아 웹에 넘긴다(`app-front/README.md` "호스트 계약" `googleSignIn`). 클라이언트 ID를 넘기지 않은 빌드는 `init.features`에 `googleSignIn`을 넣지 않고 지금처럼 동작한다(앱 안 GIS는 실패한다).

준비(한 번). 서버 `GOOGLE_CLIENT_ID`의 웹 클라이언트가 있는 **같은 Google Cloud 프로젝트**에 클라이언트 둘을 더 만든다. 클라이언트 보안 비밀번호는 쓰지 않는다.

1. **Android** OAuth 클라이언트: 패키지 `dev.fornav.for_nav`, SHA-1은 디버그 키(`keytool -list -v -keystore ~/.android/debug.keystore -alias androiddebugkey -storepass android`). 코드에는 넣지 않는다. 배포 키 SHA-1은 배포 때 더한다.
2. **iOS** OAuth 클라이언트: 번들 ID `dev.fornav.forNav`. 만들면 보이는 "iOS URL 스킴"(역방향 클라이언트 ID, `com.googleusercontent.apps.…`)을 `ios/Flutter/GoogleSignIn.xcconfig`에 적는다(커밋하지 않는다, `.gitignore`).
   ```text
   GOOGLE_REVERSED_CLIENT_ID = com.googleusercontent.apps.123-abc
   ```
   GoogleSignIn-iOS는 이 URL 스킴이 등록되지 않은 채 로그인을 시작하면 앱을 멈춘다. iOS 클라이언트 ID를 넘길 때는 이 파일도 꼭 둔다.

실행 때 두 ID를 넘긴다. 웹 클라이언트 ID는 서버 `GOOGLE_CLIENT_ID`와 같은 값이다(`serverClientId`로 줘서 ID 토큰의 `aud`가 이 값이 된다).

```sh
fvm flutter run -d <기기> --dart-define=APP_URL=… \
  --dart-define=GOOGLE_WEB_CLIENT_ID=123-web.apps.googleusercontent.com \
  --dart-define=GOOGLE_IOS_CLIENT_ID=123-ios.apps.googleusercontent.com
```

- Android는 웹 클라이언트 ID만 있어도 켜진다. iOS는 둘 다 있어야 켜진다.
- Android 에뮬레이터는 **Google Play** 시스템 이미지여야 한다(Credential Manager). Google 계정을 기기에 먼저 넣어 둔다.
- 로그인 세션은 같은 출처 HttpOnly 쿠키라, 앱이 불러오는 웹 주소와 API가 같은 출처여야 한다(개발 서버 프록시, 운영 `https://app.for-nav.com`).
- 로그에는 `googleSignIn`·`googleSignInResult`와 실패 종류(`canceled` 등)만 남는다. ID 토큰·이메일·이름은 찍지 않는다.

## 검사

```sh
cd app
fvm flutter analyze
fvm flutter test        # 이동 분류·메시지 형식 단위 테스트
```

## 계약 구현 위치

| 계약(`app-front/README.md`) | 구현 |
|---|---|
| 감지: 채널 `ForNav` | `lib/host_page.dart` `addJavaScriptChannel(channelName)` |
| `ready` → `init`(`platform`·`appVersion`·`locale`·`insets`) | `_onMessage` → `_sendInit`. `ready`를 받은 뒤에만 보낸다. `onPageFinished`에서는 아무것도 하지 않는다 |
| `insets` 다시 보내기 | `didChangeDependencies`에서 `MediaQuery.paddingOf`가 바뀌면(회전·창 크기). 키보드(`viewInsets`)는 넣지 않는다 |
| `openExternal` | `_openExternal` → `url_launcher`(`LaunchMode.externalApplication`) |
| 앱 출처 밖 이동 차단(두 번째 겹) | `lib/navigation.dart` `classifyNavigation` + `NavigationDelegate.onNavigationRequest` |
| Android 뒤로 가기 → `window.fornav.onBack()` | `PopScope` → `_onBack`. `false`면 `SystemNavigator.pop()` |
| iOS 뒤로 가기 | `setAllowsBackForwardNavigationGestures(true)`. 웹은 관여하지 않는다 |
| 안전 영역 | WebView가 상태 표시줄까지 덮고 네이티브 패딩을 두지 않는다. 웹이 `env()`·`--inset-*`로 비킨다 |
| `googleSignIn` → `googleSignInResult`, `init.features` | `_googleSignIn`: `signOut()` → `authenticate()` → `authentication.idToken`. 취소(`GoogleSignInExceptionCode.canceled`)만 `canceled`, 그 밖과 빈 토큰은 `failed`. 새 요청·페이지 `ready`가 오면 앞 결과는 버린다 |
| 메시지 형식·스크립트 | `lib/bridge.dart` |

- `locale`은 `PlatformDispatcher.instance.locale.toLanguageTag()`(기기 첫 번째 언어, BCP-47)다. `Platform.localeName`은 iOS에서 앱 번들이 지원하는 언어로 좁혀져 기기 언어가 그대로 오지 않는다.
- 앱 주소를 못 불러오면(메인 프레임 실패) WebView 오류 화면 대신 `lib/offline_view.dart` 한 장(다시 시도, 119 전화)을 보인다. 번들(app-front backlog 05) 전까지의 임시 동작이다.
- 로그(`flutter run` 출력)에는 `[host] ← ready`처럼 메시지 `type`만 남긴다. 주소·메시지 본문은 찍지 않는다. 배포 빌드에서는 찍지 않는다.

## 확인 방법

1. 위 "실행"으로 `APP_URL=…/__host`를 연다. "호스트: 있음 (webview_flutter)", "init 받음: 예", platform·appVersion·locale·insets가 기기 값인지 본다. insets.top은 상태 표시줄과 화면 카메라 구멍 중 큰 쪽이다(Pixel 7 에뮬레이터는 51.8).
2. "119" → 전화 앱(Android 에뮬레이터는 다이얼러. iOS 시뮬레이터에는 전화 앱이 없어 열리지 않고 로그에 `openExternal 실패`가 남는다).
3. "카카오맵" → 외부 브라우저. WebView 안에 카카오맵이 뜨면 실패다.
4. Android 뒤로 가기: 웹 이력이 있으면 한 화면 뒤로, 첫 화면에서는 앱이 뒤로 간다.
5. Google 로그인(위 "Google 로그인"으로 실행, 서버 `WORKER_AUTH=google`): `/__host`의 features가 `googleSignIn`이고 "Google 로그인 시험"이 `성공`이다. S-03 앱 로그인 버튼 → 계정 선택 → 프로필 → `/home`, S-12 센터 요청이 보내진다.
6. 비행기 모드로(iOS 시뮬레이터는 웹 개발 서버를 끄고) 앱을 열면 오프라인 안내가 뜨고, 서버를 켠 뒤 "다시 시도"로 돌아온다.

## 하지 않는 것(다른 항목)

권한(마이크·카메라·파일 선택기)·받아쓰기(app-front backlog 04), 번들(05), 푸시, 스토어 배포 설정(서명·아이콘·앱 ID). 번들 ID `dev.fornav.forNav`·Android `dev.fornav.for_nav`는 임시다(`app-front/README.md` "확인이 필요한 값").
