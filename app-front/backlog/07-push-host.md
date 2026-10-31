# 07. 앱 푸시 알림: 호스트의 FCM 등록과 알림으로 센터 채팅 열기

상태: 대기
의존: 06(호스트의 `init.features`·요청-응답 메시지 모양), backend 28(기기 등록·FCM 발송), 08(같은 PR, 결정 1), frontend 46(센터 채팅 시트를 사례로 여는 `openCase`)

## 목표
센터 회신(2026-10-31)의 "상담 결과 안내·사후관리"를 위해, 근로자 앱이 닫혀 있어도 센터의 채팅 답·요청 상태 변경을 알린다(frontend 46 `## 메모`의 앱 몫). 웹앱만으로는 앱이 닫혀 있을 때 알릴 수 없으므로, Flutter 호스트(`app/`)가 FCM에 등록해 기기 토큰을 웹에 넘기고, 알림을 누르면 앱을 열어 그 사례의 센터 채팅 시트가 열리게 한다. 이 문서는 호스트 쪽(`app/`)과 계약이고, 웹 다리(`src/bridge/`)는 08이다.

## 결정이 필요한 것
권장안으로 적었다. 사용자 확인 뒤 결과와 날짜를 남긴다.

1. **07(호스트)·08(웹 다리)을 어떻게 나누어 올리나.** `CLAUDE.md`는 "계약 변경은 웹·호스트를 같은 PR에서 고친다"고 한다.
   - 권장: 문서는 영역별로 둘이지만 **한 브랜치(`app/push-notification`), 한 PR로 구현한다.** `README.md` "호스트 계약"을 먼저 고치고 `app/lib/`·`src/bridge/`를 함께 고친다. 근로자 화면의 등록·시트 열기(frontend 47, 가칭)는 `@fe` 안이라 그보다 먼저 `frontend/` 브랜치로 따로 한다(06과 frontend 35의 관계와 같다)
   - 대안: 07을 먼저 올리고 웹은 모르는 `type`을 무시하게 둔다. 계약 규칙을 어기므로 권장하지 않는다
2. **Firebase 설정을 앱에 어떻게 넣나.**
   - 권장: `google-services.json`·`GoogleService-Info.plist`·`firebase_options.dart`를 **커밋하지 않고**, `Firebase.initializeApp(options: FirebaseOptions(...))`에 넣을 값(`FIREBASE_API_KEY`, `FIREBASE_APP_ID_ANDROID`, `FIREBASE_APP_ID_IOS`, `FIREBASE_SENDER_ID`, `FIREBASE_PROJECT_ID`)을 `APP_URL`·Google 클라이언트 ID처럼 `--dart-define`으로 받는다. 값이 없는 빌드는 Firebase를 초기화하지 않고 `init.features`에 `push`를 넣지 않는다(googleSignIn과 같은 규칙: 설정이 없으면 기능이 없을 뿐 앱은 그대로다). Android Gradle `google-services` 플러그인도 쓰지 않는다
   - 이 값들은 비밀 키가 아니지만(앱 안에 들어간다) 프로젝트마다 달라 코드에 적지 않는다. 운영 값은 `env/prod.json`에 더할지, 클라이언트 ID처럼 빼 둘지 함께 정한다. 권장은 클라이언트 ID와 같이 **빼 둔다**
   - Firebase 프로젝트는 backend 28 결정 1(근로자 Google 로그인과 같은 Google Cloud 프로젝트)을 따른다
   - 대안: `flutterfire configure`로 만든 `firebase_options.dart`를 커밋. 설정이 간단하지만 환경마다 파일을 바꿔야 하고 지금 `--dart-define` 원칙과 어긋난다
3. **iOS(APNs).**
   - iOS 푸시는 Push Notifications capability(`aps-environment` 권한 파일), Firebase 콘솔의 APNs 인증 키(.p8)가 있어야 하고, 둘 다 **유료 Apple Developer 계정**이 필요하다. 지금 앱은 개발 서명만 있고 번들 ID(`dev.fornav.forNav`)도 임시다
   - 권장: 코드·설정은 두 플랫폼 모두 넣되 **완료 확인은 Android로 하고, iOS 실기기 확인은 Developer 계정·APNs 키가 준비되면 이 문서 `## 결과`에 덧붙인다.** iOS에서 APNs 토큰을 못 받으면 `pushToken`이 `failed`로 끝나고 앱은 그대로다
   - 대안: iOS를 이 항목에서 빼고 스토어 배포 항목으로 미룬다. 코드가 두 번 바뀐다
4. **알림 권한을 언제 묻나.** Android 13+는 `POST_NOTIFICATIONS` 런타임 권한, iOS는 처음 한 번 시스템 창이다.
   - 권장: **앱을 처음 열 때 묻지 않는다.** 근로자가 센터 요청을 처음 보내 채팅 토큰이 생겼을 때 웹이 `pushRegister`를 보내고, 그때 호스트가 시스템 권한 창을 띄운다. 알릴 것이 생긴 순간이라 이유가 분명하다(frontend 46의 "권한 팝업이 첫 경험을 막는다" 결정과 맞다). 앱이 미리 설명하는 화면·문구는 두지 않는다(호스트가 있을 때만 보이는 문구를 만들지 않는다)
   - 거부하면 다시 묻지 않는다(OS가 기억한다). 웹은 지금처럼 앱을 다시 열 때 15초 주기로 상태를 읽는다
5. **앱이 열려 있을 때 온 알림.**
   - 권장: **시스템 알림을 띄우지 않는다**(FCM 기본: Android는 앞에 있을 때 알림 메시지를 보이지 않고, iOS도 `setForegroundNotificationPresentationOptions`를 켜지 않는다). 앱이 앞에 있으면 웹의 독 점이 15초 안에 뜬다. 서버도 근로자가 채팅에 붙어 있으면 보내지 않는다(backend 28 결정 3)
   - 대안: 앞에 있을 때 받은 알림을 웹에 넘겨(`pushReceived`) 곧바로 상태를 다시 읽기. 15초 주기로 충분해 이번에는 하지 않는다(메모)

## 범위
- 하는 것
  - **계약(`README.md` 먼저)**: 아래 메시지 넷과 `init.features`의 `push`. "다리로 보내지 않는 것"에 FCM 기기 토큰 예외, "Flutter 쪽에서 할 일"에 푸시 줄, "나중에 붙일 자리"의 푸시 줄 갱신, "실서비스와 다른 점"
  - **호스트(`app/`)**
    - 의존성 `firebase_core`, `firebase_messaging`(FlutterFire 공식). 이유: FCM 토큰·알림 탭 처리를 플랫폼마다 직접 짜지 않는다. 로컬 알림 플러그인(`flutter_local_notifications`)은 더하지 않는다(결정 5로 앞에서 알림을 띄우지 않으므로 필요 없다)
    - 시작: 결정 2의 값이 있으면 `Firebase.initializeApp`. 실패하면 `push` 없이 계속한다(로그는 종류만)
    - `pushRegister`를 받으면: `requestPermission()`(Android 13 미만·이미 허용이면 창 없음) → 허용이면 `getToken()`(iOS는 APNs 토큰을 기다린다) → `pushToken { token }`. 거부면 `pushToken { error: "denied" }`, 그 밖 실패는 `{ error: "failed" }`. `onTokenRefresh`가 오면 `pushRegister`를 한 번이라도 받은 페이지에 `pushToken { token }`을 다시 보낸다
    - `pushUnregister`를 받으면 `deleteToken()`. 그 토큰으로 온 발송은 FCM이 `UNREGISTERED`로 거절하고 서버가 지운다(backend 28). 응답 메시지는 없다
    - **알림을 누르면**: `onMessageOpenedApp`(백그라운드에서 돌아올 때)·`getInitialMessage()`(꺼져 있다가 열릴 때)의 `data.kind == "center"`이고 `data.caseId`가 사례 id 형식이면, 웹이 `ready`를 보내고 `init`을 받은 뒤에 `pushOpen { caseId }`를 한 번 보낸다. `ready` 전에 온 것은 하나만 들고 있다가 `init` 바로 뒤에 보낸다(06처럼 페이지 로드 이벤트에 기대지 않는다). 그 사이 다른 알림을 누르면 마지막 것만 남긴다
    - Android: `AndroidManifest.xml`에 `POST_NOTIFICATIONS`. 알림 채널은 FCM 기본 채널을 쓴다(채널 이름을 앱이 정하면 네이티브 문구가 생긴다). 알림 아이콘은 지금 앱 아이콘(스토어 아이콘과 함께 정한다, 메모)
    - iOS: `Runner.entitlements`의 `aps-environment`, Background Modes의 Remote notifications, Xcode의 Push Notifications capability. 메서드 스위즐링은 FlutterFire 기본값 그대로
    - `init.features`에 `push`: Firebase가 초기화됐을 때만 넣는다
    - 로그에는 `type`과 `error`만 남긴다. FCM 토큰·`caseId`·알림 본문은 찍지 않는다
    - `fvm flutter test`: `pushToken`·`pushOpen` 메시지 만들기, `data` → `caseId` 거르기(형식이 아니면 버림), `ready` 전 보관·`init` 뒤 한 번 보내기
  - 웹 다리(`src/bridge/`)는 08, 근로자 화면의 등록·시트 열기는 frontend 47(가칭)
- 하지 않는 것
  - 앱이 앞에 있을 때의 알림 표시, 앱 아이콘 숫자 배지
  - 통화 착신 알림(전체 화면 알림·CallKit). backend 28 `## 메모`
  - 알림 문구 정하기. 문구는 웹이 정해 서버에 등록한다(backend 28 결정 2). 앱에는 알림 문구가 없다
  - 네이티브 알림 설정 화면·안내 화면
  - 스토어 배포 설정(서명·번들 ID 확정·스토어 아이콘), Apple Developer 계정 만들기
  - 단독 웹앱의 웹 푸시(08 결정 4)

## 화면·계약·파일
- 화면: 바뀌는 웹 화면 없음(근로자 화면 변화는 frontend 47). 네이티브로는 시스템 권한 창과 시스템 알림만 보인다
- 계약 초안(`README.md` "메시지 형식" 표에 더한다)

  **웹 → 호스트**

  | `type` | 필드 | 언제 | 호스트가 할 일 |
  |---|---|---|---|
  | `pushRegister` | 없음 | 이 계정에 채팅 토큰이 있는 센터 요청이 생겼을 때(API 모드). 페이지마다 처음 한 번, 그 뒤에는 토큰이 필요할 때. `init.features`에 `push`가 있을 때만 보낸다 | 알림 권한을 묻고(처음 한 번), FCM 토큰을 받아 `pushToken`을 한 번 보낸다. 이 뒤 토큰이 바뀌면 `pushToken`을 다시 보낸다 |
  | `pushUnregister` | 없음 | 로그아웃·계정 바꾸기·"내 데이터 지우기" | `deleteToken()`. 응답 없음. 다음 `pushRegister`는 새 토큰을 받는다 |

  **호스트 → 웹**

  | `type` | 필드 | 언제 | 웹이 할 일 |
  |---|---|---|---|
  | `init`(값 추가) | `features`에 `"push"` | Firebase가 초기화된 빌드 | `pushRegister`를 보낼 수 있다 |
  | `pushToken` | 성공: `token`(FCM 등록 토큰). 실패: `error`(`denied` \| `failed`) | `pushRegister`의 응답, 그리고 토큰이 바뀔 때 | 서버에 기기를 등록한다(08, frontend 47). 토큰을 저장하거나 로그에 찍지 않는다 |
  | `pushOpen` | `caseId` | 근로자가 센터 알림을 눌러 앱이 열렸을 때, `init` 뒤 한 번 | 이 계정의 사례면 센터 채팅 시트를 그 사례로 연다(frontend 46 `openCase`). 아니면 무시한다 |

  ```json
  { "protocol": 1, "type": "pushRegister" }
  { "protocol": 1, "type": "pushToken", "token": "dXf3…:APA91b…" }
  { "protocol": 1, "type": "pushToken", "error": "denied" }
  { "protocol": 1, "type": "pushOpen", "caseId": "C-251031-001" }
  ```

  - 필드를 더하는 것이라 기존 메시지의 의미는 그대로고 `protocol`은 1이다
  - "다리로 보내지 않는 것"의 예외: `pushToken.token`은 인증 토큰이 아니라 이 기기로 알림을 보낼 주소다. 웹은 받은 토큰을 서버(`POST /api/center/push-devices`)에 보내고 메모리에만 둔다(`localStorage`·`sessionStorage`에 쓰지 않는다). `pushOpen.caseId`는 사례 번호일 뿐 내용이 아니다. 둘 다 로그에 찍지 않는다
- 수정
  - `app-front/README.md`: "호스트 계약"(메시지 표·예시·`features`), "다리로 보내지 않는 것", "Flutter 쪽에서 할 일"(Firebase 값, 권한 시점, 알림 탭), "나중에 붙일 자리", "실서비스와 다른 점"
  - `app/pubspec.yaml`·`pubspec.lock`(`firebase_core`, `firebase_messaging`), iOS는 SPM/CocoaPods 잠금 파일
  - `app/lib/push.dart`(새: 초기화·권한·토큰·탭 처리), `app/lib/host_page.dart`(메시지 연결, `ready` 전 `pushOpen` 보관), `app/lib/bridge.dart`(메시지 형식)
  - `app/android/app/src/main/AndroidManifest.xml`(`POST_NOTIFICATIONS`), `app/ios/Runner/Runner.entitlements`(새), `app/ios/Runner/Info.plist`(`UIBackgroundModes` `remote-notification`), Xcode 프로젝트의 capability
  - `app/test/`: 메시지·`caseId` 거르기·보관 단위 테스트
  - `app/README.md`: Firebase 준비(콘솔에서 Android·iOS 앱 등록, APNs 키), `--dart-define` 값, 확인 방법, "계약 구현 위치" 표, "하지 않는 것"에서 푸시를 뺀다

## 완료 기준
- [ ] `cd app && fvm flutter analyze` 통과, `fvm flutter test` 통과(위 단위 테스트 포함). `cd app-front && npm run build` 통과(08과 같은 PR)
- [ ] Firebase 값 없이 빌드한 앱: `/__host`의 features에 `push`가 없고, 지금 앱과 똑같이 동작한다(권한 창 없음)
- [ ] Android 에뮬레이터(Google Play 이미지, API 33 이상)·실기기, Firebase 값과 `PUSH=fcm` 서버(backend 28): 앱을 처음 열 때 권한 창이 뜨지 않는다. 센터 요청을 보내면 권한 창이 뜨고, 허용하면 서버에 기기가 등록된다(`/__host`의 "푸시 시험"이 `token 받음`, 토큰 값은 보이지 않는다)
- [ ] 앱을 백그라운드로 보내고 센터가 C-02에서 채팅에 쓰면 근로자 언어의 알림 한 줄("for nav" + 등록한 문구)이 뜬다. 메시지 본문·상태·사례 번호가 알림에 없다
- [ ] 그 알림을 누르면 앱이 앞으로 오고 센터 채팅 시트가 그 사례로 열려 센터 글이 보인다
- [ ] 앱을 완전히 끈 뒤(최근 앱에서 지움) 상태를 진행으로 바꾸면 알림이 오고, 누르면 앱이 처음부터 열린 뒤 시트가 그 사례로 열린다(`ready`·`init` 뒤 `pushOpen` 한 번)
- [ ] 권한을 거부하면 알림이 오지 않고, 앱을 다시 열면 15초 안에 독 점이 뜬다(frontend 46 그대로)
- [ ] 로그아웃 뒤 같은 사례에 센터가 쓰면 알림이 오지 않는다(`pushUnregister` → `deleteToken`). 다른 계정으로 로그인해도 앞 계정 사례의 알림이 오지 않는다
- [ ] `flutter run` 로그에 FCM 토큰·`caseId`·알림 본문이 없다
- [ ] iOS: 결정 3대로 Developer 계정·APNs 키가 있으면 실기기에서 위 넷을 확인하고, 없으면 시뮬레이터에서 빌드·실행과 `pushToken`이 `failed`로 끝나 앱이 멈추지 않는 것만 확인했다고 `## 결과`에 적는다

## 결과
(구현 후 작성)

## 메모
- frontend 46 `## 메모`의 앱 몫(FCM 등록, 알림을 누르면 시트를 연 채 앱 열기)이다. 서버 몫은 backend 28
- 앞에 있을 때 받은 알림을 웹에 넘겨 곧바로 다시 읽는 `pushReceived`는 결정 5로 하지 않았다. 15초 주기가 느리다는 말이 나오면 이 계약에 메시지 하나를 더하는 후속으로 한다
- Android 알림 작은 아이콘은 흰색 단색이어야 제대로 보인다. 지금은 앱 아이콘이 회색 사각형으로 보일 수 있다. 스토어 아이콘을 정할 때 `default_notification_icon` 메타데이터와 함께 넣는다
- 통화 착신 알림(센터가 걸 때)은 FCM 데이터 메시지 + 전체 화면 알림·CallKit이라 이 항목보다 크다. backend 28과 함께 따로 쓴다
