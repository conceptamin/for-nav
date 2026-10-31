# for nav — 근로자 앱 호스트(Flutter)

근로자 화면(`../app-front/`)을 **WebView 한 장으로 불러오는 Flutter 앱**이다. 화면은 모두 웹이고, 이 앱은 웹이 브라우저에 기대던 일(전화·외부 링크·뒤로 가기·안전 영역·기기 언어)을 대신하는 껍데기다. 웹과 주고받는 약속은 `../app-front/README.md` "호스트 계약"이 원본이고, 이 앱은 그 호스트 쪽 구현이다.

- 플랫폼: Android·iOS. 세로 고정
- WebView: `webview_flutter`(공식). 마이크 권한·Android 파일 선택기는 직접 붙였다(app-front backlog 04)
- 통화 매체(app-front backlog 04): `permission_handler`(Android 마이크 앱 권한), `image_picker`(Android 사진 선택기), `speech_to_text`(통화 자막 받아쓰기). `permission_handler`는 12.x로 둔다(13.x의 Android 쪽이 `compileSdk 37`을 요구하는데 SDK에 `android-37` 이름의 플랫폼이 없어 빌드가 깨진다)
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

### 운영 주소

운영 웹 주소는 `env/prod.json`에 둔다(`APP_URL=https://app.for-nav.com`). 맥미니가 이 호스트에 앱용 웹(`app-front`) 빌드를 준다(backend backlog 22).

```sh
fvm flutter run -d <기기> --dart-define-from-file=env/prod.json
fvm flutter build apk --dart-define-from-file=env/prod.json
```

- `--dart-define`을 함께 주면 그 값이 파일보다 앞선다. 확인 화면은 `--dart-define=APP_URL=https://app.for-nav.com/__host`, Google 클라이언트 ID는 아래 "Google 로그인"처럼 덧붙인다. 클라이언트 ID는 이 파일에 넣지 않는다(Google Cloud 프로젝트마다 다르다).
- 앱이 불러온 웹이 다리를 쓰는지는 `/__host`의 "호스트: 있음"·"init 받음: 예"로 본다. 다리 없는 `frontend/` 빌드가 오면 상태 표시줄과 겹치고 뒤로 가기가 앱을 닫는다.

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

## 푸시 알림

센터가 채팅에 답하거나 요청 상태를 바꾸면 앱이 닫혀 있어도 알림 한 줄이 뜨고, 누르면 센터 채팅 시트가 그 사례로 열린다(`app-front/README.md` "호스트 계약" `pushRegister`·`pushToken`·`pushOpen`, app-front backlog 07·08, 서버 backend 28). Firebase 값을 넘기지 않은 빌드는 `init.features`에 `push`를 넣지 않고 지금처럼 동작한다(권한 창도 없다).

준비(한 번). 근로자 Google 로그인 클라이언트가 있는 **같은 Google Cloud 프로젝트**에 Firebase를 붙인다(backend 28 결정 1).

1. Firebase 콘솔 → 프로젝트 추가 → 기존 Google Cloud 프로젝트 선택
2. Android 앱 등록: 패키지 `dev.fornav.for_nav`. `google-services.json`은 내려받지 않아도 된다(아래 값만 쓴다. Gradle `google-services` 플러그인을 쓰지 않는다)
3. iOS 앱 등록: 번들 ID `dev.fornav.forNav`. `GoogleService-Info.plist`도 넣지 않는다
4. 프로젝트 설정 → 일반에서 값을 옮겨 둔다: 웹 API 키, Android·iOS 앱 ID(`1:…:android:…`, `1:…:ios:…`), 프로젝트 번호(= 발신자 ID), 프로젝트 ID
5. iOS만: 유료 Apple Developer 계정에서 APNs 인증 키(.p8)를 만들어 Firebase 콘솔 → 클라우드 메시징 → Apple 앱 구성에 올리고, Xcode의 Runner 타깃 → Signing & Capabilities에서 **Push Notifications**를 켠다(`ios/Runner/Runner.entitlements`가 연결된다. 개인 팀 서명으로는 이 capability를 켤 수 없어 아직 연결하지 않았다). Background Modes의 Remote notifications는 `Info.plist`에 이미 있다

실행 때 값을 넘긴다. 비밀 키가 아니지만(앱 안에 들어간다) 프로젝트마다 달라 코드·`env/prod.json`에 적지 않는다.

```sh
fvm flutter run -d <기기> --dart-define=APP_URL=… \
  --dart-define=FIREBASE_API_KEY=AIza… \
  --dart-define=FIREBASE_APP_ID_ANDROID=1:123:android:abc \
  --dart-define=FIREBASE_APP_ID_IOS=1:123:ios:def \
  --dart-define=FIREBASE_SENDER_ID=123 \
  --dart-define=FIREBASE_PROJECT_ID=for-nav-demo
```

- 다섯 값 중 그 플랫폼에 필요한 넷(API 키·그 플랫폼 앱 ID·발신자 ID·프로젝트 ID)이 다 있어야 켜진다. `Firebase.initializeApp`이 실패해도 `push` 없이 계속한다
- 알림 권한은 앱을 처음 열 때 묻지 않는다. 근로자가 센터 요청을 처음 보내 웹이 `pushRegister`를 보낼 때 묻는다(Android 13+ `POST_NOTIFICATIONS`, iOS 시스템 창). 거부하면 다시 묻지 않고, 웹은 앱을 다시 열 때 15초 주기로 상태를 읽는다
- 앱이 앞에 있을 때 온 알림은 띄우지 않는다. Android 에뮬레이터는 **Google Play** 시스템 이미지여야 FCM 토큰이 나온다
- 서버는 `PUSH=fcm`과 FCM 발송 권한 서비스 계정 키가 있어야 실제로 보낸다(`backend/README.md`). `PUSH=off` 서버로도 등록 흐름(`/__host` "푸시 시험", `POST /api/center/push-devices`)은 확인된다
- 로그에는 `pushRegister`·`pushToken`·`pushOpen`과 실패 종류(`denied`, Firebase 오류 코드)만 남는다. FCM 토큰·`caseId`·알림 본문은 찍지 않는다

## 검사

```sh
cd app
fvm flutter analyze
fvm flutter test        # 이동 분류·메시지 형식·푸시 caseId 거르기·보관 단위 테스트
```

`analysis_options.yaml`은 `build/**`를 보지 않는다. Flutter가 iOS Swift 패키지를 `build/ios/SourcePackages`에 풀어 두는데, firebase_messaging은 그 안에 자기 테스트 mock까지 있어 분석에 걸린다.

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
| `speechStart`·`speechStop` → `speech`·`speechError`, `init.features`의 `speech` | `lib/speech.dart` `NativeSpeech`. `speech_to_text`를 `dictation`·말하는 중 결과 켬·3초 쉬면 확정·55초 한도로 켜고, `done`이면 300ms 뒤 다시 켠다. 권한 거부·언어 미지원은 바로 `speechError`, 말 없음(`error_no_match` 등)은 세지 않고, 그 밖 오류가 결과 없이 3번 이어지면 `unsupported`. 페이지가 다시 `ready`하면 끈다 |
| WebView 마이크 요청 | `_onPermissionRequest`: 마이크만 요청이면 Android는 `RECORD_AUDIO`를 받고 허용, 거부면 WebView 요청도 거부(웹 `micDenied`). iOS는 시스템 권한 창. 카메라 등은 거부 |
| Android 파일 선택기 | `_onShowFileSelector` → `image_picker`(시스템 사진 선택기, 권한 없음). `accept`가 사진이 아니면 빈 목록 |
| 통화 상대 음성 자동 재생 | iOS `mediaTypesRequiringUserAction: {}`·`allowsInlineMediaPlayback`, Android `setMediaPlaybackRequiresUserGesture(false)` |
| `pushRegister` → `pushToken`, `pushUnregister`, `init.features`의 `push` | `lib/push.dart` `NativePush`. 시작 때 `--dart-define` Firebase 값으로 `Firebase.initializeApp`, 성공하면 `push`. `pushRegister`: `requestPermission()` → (iOS는 APNs 토큰을 10초까지 기다림) → `getToken()` → `pushToken`. 거부는 `denied`, 그 밖은 `failed`. 이 페이지가 `pushRegister`를 보낸 뒤에만 `onTokenRefresh`를 `pushToken`으로 다시 보낸다. `pushUnregister`: `deleteToken()` |
| 알림 탭 → `pushOpen` | `onMessageOpenedApp`(백그라운드에서 돌아옴)·`getInitialMessage()`(꺼져 있다가 열림)의 `data.kind == "center"`이고 `data.caseId`가 사례 id 모양일 때만(`pushCaseIdOf`). `PushOpenGate`가 `init` 전에 누른 것 중 마지막 하나를 들고 있다가 `init` 바로 뒤에 한 번 보낸다. 페이지가 다시 `ready`하면 다음 `init`까지 다시 들고 있는다 |
| 메시지 형식·스크립트 | `lib/bridge.dart` |

- `locale`은 `PlatformDispatcher.instance.locale.toLanguageTag()`(기기 첫 번째 언어, BCP-47)다. `Platform.localeName`은 iOS에서 앱 번들이 지원하는 언어로 좁혀져 기기 언어가 그대로 오지 않는다.
- 앱 주소를 못 불러오면(메인 프레임 실패) WebView 오류 화면 대신 `lib/offline_view.dart` 한 장(다시 시도, 119 전화)을 보인다. 번들(app-front backlog 05) 전까지의 임시 동작이다.
- 로그(`flutter run` 출력)에는 `[host] ← ready`처럼 메시지 `type`만 남긴다. 주소·메시지 본문·받아쓴 글은 찍지 않는다(`speech`는 말하는 동안 계속 오므로 type도 찍지 않는다). 배포 빌드에서는 찍지 않는다.
- 권한 문구: iOS `Info.plist`의 마이크·음성 인식·사진 보관함·카메라 설명은 한국어·영어 한 줄이다. Android는 `RECORD_AUDIO`·`MODIFY_AUDIO_SETTINGS`·`POST_NOTIFICATIONS`와 음성 인식 서비스 `<queries>`를 둔다. 알림 채널은 FCM 기본 채널이고 이름을 앱이 정하지 않는다.

## 확인 방법

1. 위 "실행"으로 `APP_URL=…/__host`를 연다. "호스트: 있음 (webview_flutter)", "init 받음: 예", platform·appVersion·locale·insets가 기기 값인지 본다. insets.top은 상태 표시줄과 화면 카메라 구멍 중 큰 쪽이다(Pixel 7 에뮬레이터는 51.8).
2. "119" → 전화 앱(Android 에뮬레이터는 다이얼러. iOS 시뮬레이터에는 전화 앱이 없어 열리지 않고 로그에 `openExternal 실패`가 남는다).
3. "카카오맵" → 외부 브라우저. WebView 안에 카카오맵이 뜨면 실패다.
4. Android 뒤로 가기: 웹 이력이 있으면 한 화면 뒤로, 첫 화면에서는 앱이 뒤로 간다.
5. Google 로그인(위 "Google 로그인"으로 실행, 서버 `WORKER_AUTH=google`): `/__host`의 features가 `googleSignIn`이고 "Google 로그인 시험"이 `성공`이다. S-03 앱 로그인 버튼 → 계정 선택 → 프로필 → `/home`, S-12 센터 요청이 보내진다.
6. 받아쓰기: `/__host`의 features에 `speech`가 있고, "받아쓰기 시험"을 누르면 처음에 권한 창(Android 마이크, iOS 음성 인식·마이크)이 뜬다. 거부하면 `speechError denied`, 허용하면 `듣는 중`이고 말하면 확정 문장 수가 오른다. 다시 누르면 끈다(`speechStop`). 에뮬레이터·시뮬레이터 마이크에는 소리가 들어오지 않을 수 있어 받아쓴 글은 실기기에서 본다.
7. 사진(Android): S-05 "사진 추가" → 시스템 사진 선택기 → 미리보기. 취소하면 아무 일 없이 돌아온다.
8. 통화: S-12에서 "통화" → 마이크 권한 → PC 센터 화면(`frontend/` C-02)이 받으면 양쪽 자막이 번역되어 보인다. 통화는 HTTPS 또는 `localhost`(Android는 `adb reverse`)에서만 된다.
9. 푸시(위 "푸시 알림"으로 실행, Android Google Play 이미지): 앱을 처음 열 때 권한 창이 뜨지 않는다. `/__host`의 features에 `push`가 있고 "푸시 시험"이 처음에 권한 창을 띄운 뒤 `token 받음`이다(토큰 값은 보이지 않는다). S-12로 센터 요청을 보낸 뒤 앱을 백그라운드로 보내고 PC 센터 화면 C-02에서 채팅에 쓰면 "for nav" + 근로자 언어 한 줄이 뜨고, 누르면 시트가 그 사례로 열린다. 앱을 최근 앱에서 지운 뒤 상태를 바꿔도 같다
10. 비행기 모드로(iOS 시뮬레이터는 웹 개발 서버를 끄고) 앱을 열면 오프라인 안내가 뜨고, 서버를 켠 뒤 "다시 시도"로 돌아온다.

## 하지 않는 것(다른 항목)

Android 파일 선택기의 카메라 촬영(2차), 번들(app-front backlog 05), 통화 착신 알림(센터가 걸 때, 전체 화면 알림·CallKit), 앱이 앞에 있을 때의 알림 표시, 스토어 배포 설정(서명·아이콘·앱 ID). 번들 ID `dev.fornav.forNav`·Android `dev.fornav.for_nav`는 임시다(`app-front/README.md` "확인이 필요한 값").
