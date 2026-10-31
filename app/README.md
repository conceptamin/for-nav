# for nav — 근로자 앱 호스트(Flutter)

근로자 화면(`../app-front/`)을 **WebView 한 장으로 불러오는 Flutter 앱**이다. 화면은 모두 웹이고, 이 앱은 웹이 브라우저에 기대던 일(전화·외부 링크·뒤로 가기·안전 영역·기기 언어)을 대신하는 껍데기다. 웹과 주고받는 약속은 `../app-front/README.md` "호스트 계약"이 원본이고, 이 앱은 그 호스트 쪽 구현이다.

- 플랫폼: Android·iOS. 세로 고정
- WebView: `webview_flutter`(공식). 파일 선택기·권한은 app-front backlog 04에서 직접 붙인다
- Flutter: fvm으로 `3.44.7` 고정(`.fvmrc`)
- 최소 OS: Android `flutter.minSdkVersion`(기본값), iOS 15.0

## 실행

불러올 주소는 코드에 적지 않고 `--dart-define=APP_URL=`로 넘긴다. 이 주소의 **출처**(scheme·host·port)가 "앱 안"이고, 그 밖은 모두 외부 앱으로 연다.

```sh
# 다른 터미널: 웹 개발 서버(http://localhost:5181)
cd app-front && npm run dev

cd app
fvm install          # 처음 한 번
fvm flutter pub get

# iOS 시뮬레이터: 맥의 localhost가 그대로 보인다
fvm flutter run -d <시뮬레이터> --dart-define=APP_URL=http://localhost:5181

# Android 에뮬레이터: 호스트 PC는 10.0.2.2다(localhost는 에뮬레이터 자신)
fvm flutter run -d <에뮬레이터> --dart-define=APP_URL=http://10.0.2.2:5181
```

- 확인 화면을 바로 열려면 `APP_URL=http://localhost:5181/__host`처럼 경로를 붙인다. 출처는 같으므로 동작은 같다.
- 같은 Wi-Fi의 실기기는 웹을 `npm run dev -- --host`로 띄우고 `APP_URL=http://<맥 IP>:5181`.
- `APP_URL`을 빠뜨리면 앱이 안내 문구 한 장만 보인다.
- **http는 개발 빌드에서만 열린다.** Android는 `src/debug/AndroidManifest.xml`에서만 `usesCleartextTraffic`을 켠다. iOS는 `NSAllowsLocalNetworking`(localhost·사설 IP)만 연다. 배포 빌드는 HTTPS 주소를 넘긴다(마이크·WebRTC도 안전한 출처에서만 열린다).
- Xcode 27.1에서 `fvm flutter build ios --simulator`는 `lipo -verify_arch`에 아키텍처 두 개를 넘기는 단계에서 실패한다(Flutter 3.44.7 도구 쪽 문제). 활성 아키텍처 하나만 빌드하는 `fvm flutter run`은 된다.

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
| 메시지 형식·스크립트 | `lib/bridge.dart` |

- `locale`은 `PlatformDispatcher.instance.locale.toLanguageTag()`(기기 첫 번째 언어, BCP-47)다. `Platform.localeName`은 iOS에서 앱 번들이 지원하는 언어로 좁혀져 기기 언어가 그대로 오지 않는다.
- 앱 주소를 못 불러오면(메인 프레임 실패) WebView 오류 화면 대신 `lib/offline_view.dart` 한 장(다시 시도, 119 전화)을 보인다. 번들(app-front backlog 05) 전까지의 임시 동작이다.
- 로그(`flutter run` 출력)에는 `[host] ← ready`처럼 메시지 `type`만 남긴다. 주소·메시지 본문은 찍지 않는다. 배포 빌드에서는 찍지 않는다.

## 확인 방법

1. 위 "실행"으로 `APP_URL=…/__host`를 연다. "호스트: 있음 (webview_flutter)", "init 받음: 예", platform·appVersion·locale·insets가 기기 값인지 본다.
2. "119" → 전화 앱(Android 에뮬레이터는 다이얼러. iOS 시뮬레이터에는 전화 앱이 없어 열리지 않고 로그에 `openExternal 실패`가 남는다).
3. "카카오맵" → 외부 브라우저. WebView 안에 카카오맵이 뜨면 실패다.
4. Android 뒤로 가기: 웹 이력이 있으면 한 화면 뒤로, 첫 화면에서는 앱이 뒤로 간다.
5. 웹 개발 서버를 끄고(또는 비행기 모드로) 앱을 열면 오프라인 안내가 뜨고, 서버를 켠 뒤 "다시 시도"로 돌아온다.

## 하지 않는 것(다른 항목)

권한(마이크·카메라·파일 선택기)·받아쓰기(app-front backlog 04), 번들(05), 푸시, 스토어 배포 설정(서명·아이콘·앱 ID). 번들 ID `dev.fornav.forNav`·Android `dev.fornav.for_nav`는 임시다(`app-front/README.md` "확인이 필요한 값").
