# 03. Flutter 셸(호스트) 프로젝트

상태: 진행 중
의존: 01 (02와 독립이지만 02 뒤에 하면 실제 화면으로 확인할 수 있다)

## 목표
이 웹앱을 불러오는 Flutter 앱을 만든다. WebView 한 장, `README.md` "호스트 계약"의 호스트 쪽 구현(채널·`init`·`openExternal`·뒤로 가기·안전 영역), 앱 출처 밖 이동 차단이다. 이 항목이 끝나면 Android 에뮬레이터·iOS 시뮬레이터에서 앱을 열어 `/__host`가 "호스트: 있음"을 보이고, 119 링크가 전화 앱을 연다.

## 결정이 필요한 것

1. **프로젝트 위치.** → **권장대로 `app/`으로 결정(2026-10-31).** 권장: 이 저장소의 `app/`(새 영역, 루트 `CLAUDE.md` 표에 `app` 행). 계약 변경을 웹·호스트 한 PR에서 할 수 있다. 대안: 별도 저장소(스토어 배포 파이프라인을 따로 두고 싶을 때).
2. **WebView 라이브러리.** → **권장대로 `webview_flutter`로 결정(2026-10-31).** 권장: `webview_flutter`(공식). 파일 선택기·권한은 04에서 직접 구현한다. 대안: `flutter_inappwebview`(파일 선택기·`onPermissionRequest` 내장, 의존성 큼). 웹 쪽은 둘 다 감지하므로 바꿔도 웹은 그대로다.
3. **불러올 주소.** → **권장대로 환경별 `--dart-define=APP_URL=`로 결정(2026-10-31).** 코드에 주소가 없다. 배포 출처(README 결정 2)는 배포 주소가 생길 때 정하고, 앱 코드는 바뀌지 않는다. 개발: `http://10.0.2.2:5181`(Android 에뮬레이터) / `http://localhost:5181`(iOS 시뮬레이터) — `--dart-define=APP_URL=`로 넘긴다. 배포: `README.md` "결정이 필요한 것" 2(배포 출처)와 함께 정한다. 권장은 환경별 `--dart-define`이고 코드에 주소를 적지 않는다.
4. **Flutter 버전.** 로컬에 fvm `3.24.3`이 있다. 권장: fvm으로 고정하고 `.fvmrc`를 커밋한다. → **fvm 고정은 권장대로, 버전은 `3.44.7`로 결정(2026-10-31).** 이 맥의 Xcode 27.1은 iOS 배포 대상을 15.0 이상만 받고, `3.24.3`(2024-09)보다 최신 Xcode·Android SDK에 맞는 안정판이 로컬에 이미 있다(다른 로컬 프로젝트도 `3.44.7`). `3.24.3`으로 빌드해 보지는 않았다.

## 범위
- 하는 것
  - `flutter create`(Android·iOS만), `WebViewController` 설정: JavaScript 허용, 채널 `ForNav`, `NavigationDelegate`(앱 출처 밖 → `url_launcher` 외부 열기, `tel:`·`mailto:`·`sms:` 포함), `onPageFinished`에서는 아무것도 하지 않는다(`init`은 `ready`를 받은 뒤에만 보낸다)
  - `init`: `platform`, `appVersion`(`package_info_plus`), `locale`(`Platform.localeName`), `insets`(`MediaQuery.paddingOf`를 CSS px로 — 논리 픽셀이 그대로 CSS px다). 회전·크기 변경 때 `insets` 다시 보내기
  - Android 뒤로 가기: `PopScope`에서 `window.fornav?.onBack?.()`을 동기로 부르고 `false`면 앱 종료(홈으로 보내기)
  - iOS: `allowsBackForwardNavigationGestures` 켬. 상태 표시줄 영역은 WebView가 가리고 웹이 `env()`로 처리하므로 네이티브 패딩을 두지 않는다
  - 세로 고정, 상태 표시줄 글자색은 밝은 배경 기준(어두운 글자), 네이티브 스플래시는 Flutter 기본(로고는 미정)
  - 로그에 `openExternal.url`·메시지 본문을 찍지 않는다. `type`만
  - `app/README.md`: 실행(`fvm flutter run --dart-define=APP_URL=…`), 계약 구현 위치, 확인 방법. `app/CLAUDE.md`는 이 폴더(`app-front/CLAUDE.md`)의 규칙 중 호스트에 해당하는 것(계약은 `app-front/README.md`가 먼저, 본문 로그 금지, 호스트 없이도 웹이 동작해야 하므로 웹에 호스트 전용 기능을 요구하지 않음)
- 하지 않는 것
  - 권한(마이크·카메라·파일), 받아쓰기 연결(04). 번들(05). 푸시. 스토어 배포 설정(서명·아이콘·스크린샷)
  - 네이티브 UI. 네이티브 화면은 WebView 하나와 (필요하면) 오프라인 안내 한 장뿐이다

## 화면·계약·파일
- 화면: 웹 화면 변경 없음. 네이티브는 WebView 한 장
- 계약: 변경 없음(처음으로 호스트 쪽이 구현된다). `insets` 다시 보내기의 시점(회전)이 여기서 정해진다
- 추가: `app/` 전체(결정 1이 권장안일 때), 루트 `CLAUDE.md` 영역 표 `app` 행
- 수정: `app-front/README.md` "Flutter 쪽에서 할 일"(예시 코드를 실제 구현 위치로 바꾸거나 줄인다), "결정이 필요한 것" 2~4

## 완료 기준
- [ ] `fvm flutter analyze` 통과, Android 에뮬레이터와 iOS 시뮬레이터에서 앱이 뜬다
- [ ] `/__host`가 "호스트: 있음(webview_flutter)", platform·appVersion·locale·insets가 기기 값으로 보인다. Android 에뮬레이터에서 insets.top이 상태 표시줄 높이와 같다
- [ ] `tel:119` 링크 → 전화 앱(에뮬레이터는 다이얼러), 지도 링크 → 외부 브라우저. WebView 안에서 다른 사이트가 열리는 경우가 없다(주소창 없는 WebView에서 카카오맵이 열리면 실패)
- [ ] Android 뒤로 가기: 웹 이력이 있으면 한 화면 뒤로, 첫 화면에서는 앱이 뒤로 간다(02가 끝났으면 `/intake` → `/home` → 종료 순으로 확인)
- [ ] 기기 언어를 베트남어로 바꾸고 앱을 다시 열면 `locale`이 `vi-VN`이다(02가 끝났으면 S-01이 베트남어를 맨 앞에 제안한다)
- [ ] 앱 로그(`flutter run` 출력)에 `tel:`·지도 주소·메시지 본문이 없다
- [ ] 비행기 모드에서 앱을 열면(원격 주소라) WebView 오류 화면 대신 앱의 오프라인 안내 한 장이 뜨고 "다시 시도"가 된다. 번들(05) 전까지의 임시 동작이다

## 결과

2026-10-31. 브랜치 `app/flutter-shell`. **Android 에뮬레이터 확인이 남아 상태는 "진행 중"이다**(이 맥에 AVD·시스템 이미지가 없다).

실행한 명령
- `cd app && fvm flutter analyze` → No issues found
- `fvm flutter test` → 6개 통과(이동 분류: 앱 출처·외부·하위 프레임 / 메시지: 형식 오류 무시, `init` 필드, `onBack` 결과)
- `fvm flutter build apk --debug --dart-define=APP_URL=http://10.0.2.2:5181` → 빌드됨
- `fvm flutter run -d "iPhone 17 Pro"(iOS 26.4 시뮬레이터) --dart-define=APP_URL=http://localhost:5181/__host` → 실행됨
- `fvm flutter build ios --simulator`는 Xcode 27.1의 `lipo -verify_arch`가 아키텍처 두 개를 받지 않아 실패한다(Flutter 도구 쪽). `flutter run`은 활성 아키텍처 하나만 빌드해 된다. `app/README.md`에 적었다

iOS 시뮬레이터에서 확인한 것(웹은 이 브랜치의 `app-front`, `npm run dev`)
- `/__host`: 호스트 "있음 (webview_flutter)", init 받음 "예", platform `ios`, appVersion `1.0.0`, locale `ko-KR`(시뮬레이터 언어), insets top 62 · bottom 34(iPhone 17 Pro 안전 영역), 출처 `http://localhost:5181`
- 로그: `[host] ← ready` → `[host] → init` 순서. `onPageFinished`에서는 보내지 않는다
- 카카오맵 링크 → `openExternal` → Safari가 열린다(WebView 안에서 열리지 않음). 로그는 `← openExternal`뿐
- 119 → `openExternal`. 시뮬레이터에는 전화 앱이 없어 열리지 않고 로그에 `openExternal 실패`(type만)
- 개발 서버를 끄고 열면 WebView 오류 화면 대신 오프라인 안내(다시 시도 · 119 전화)가 뜨고, 서버를 켜고 "다시 시도"하면 `ready` → `init`으로 돌아온다
- backlog 02 브랜치(PR #117)의 웹으로 열어 S-01 언어 선택이 상태 표시줄·홈 인디케이터를 비켜 그려지는 것도 봤다

완료 기준별
- `tel:119` → 다이얼러, Android 뒤로 가기, insets.top = 상태 표시줄 높이: **Android 에뮬레이터 미확인**
- 베트남어 `vi-VN`: 기기 언어를 바꿔 보지 않았다. `locale`은 `PlatformDispatcher.instance.locale.toLanguageTag()`로 보낸다(아래 결정)
- 로그에 `tel:`·지도 주소·본문 없음: iOS `flutter run` 출력에서 확인. `[host]` 줄은 type과 고정 문구뿐이고 배포 빌드에서는 찍지 않는다(`kDebugMode`)
- 비행기 모드: 시뮬레이터에는 없어서 개발 서버를 끈 상태(연결 거부 -1004)로 대신했다

계약: 변경 없음. `insets` 다시 보내기 시점은 `MediaQuery.paddingOf`가 바뀔 때(`didChangeDependencies`)로 정했다(회전·창 크기, 키보드 제외).

이 항목에서 정한 것과 이유
- `locale`은 범위에 적힌 `Platform.localeName` 대신 `PlatformDispatcher.instance.locale`을 쓴다. iOS의 `Platform.localeName`(`NSLocale.currentLocale`)은 앱 번들이 지원하는 언어로 좁혀져, 앱에 베트남어 지역화가 없으면 기기가 베트남어여도 `vi`가 오지 않는다. `PlatformDispatcher`는 기기 선호 언어 첫 번째를 BCP-47로 준다
- 오프라인 안내에 119 전화 버튼을 둔다. "응급은 다리도 네트워크도 기다리지 않는다"(`app-front/CLAUDE.md`)를 네이티브 화면에서도 지키기 위해서다. 웹 화면이 없으므로 문구는 한국어·영어를 함께 쓴다
- 하위 프레임의 앱 출처 밖 이동은 외부로 열지 않고 막기만 한다(사용자가 누른 이동이 아니다)
- iOS에서 막은 이동이 실패(-999 취소, 102 정책으로 중단)로 오므로 오프라인 판정에서 뺀다. 앱 출처 밖 주소의 실패도 뺀다
- iOS 배포 대상 13.0 → 15.0(Xcode 27.1 하한, `README.md` "확인이 필요한 값"의 권장 최소 OS와 같다)
- 의존성: `webview_flutter`(결정 2), `webview_flutter_wkwebview`(iOS 스와이프 뒤로 가기·디버그 빌드 Web Inspector), `url_launcher`(외부 열기), `package_info_plus`(`appVersion`). 템플릿의 `cupertino_icons`는 뺐다
- Android: `INTERNET` 권한을 main 매니페스트에(배포 빌드에도 필요), http는 debug 매니페스트에서만. `<queries>`에 전화·문자·메일·https를 더했다. 세로 고정은 매니페스트·`Info.plist`·`SystemChrome` 세 곳
- 번들 ID `dev.fornav.forNav`·Android `dev.fornav.for_nav`, 앱 표시 이름 `for nav`는 임시다(스토어 설정은 범위 밖)

남은 문제
- Android 에뮬레이터 확인(위 미확인 항목). AVD를 만들려면 시스템 이미지를 받아야 한다
- iOS에서 `target="_blank"`·`window.open`은 WebView가 새 창을 만들지 않아 아무 일도 일어나지 않는다. 웹은 `init` 뒤에 외부 링크를 `openExternal`로 넘기므로 지금 화면에는 문제가 없다
- 키보드가 올라올 때 WebView 크기(`Scaffold` 기본 `resizeToAvoidBottomInset`)는 입력 화면(S-03·S-05)이 들어오면 실기기에서 본다

## 메모
- Android 에뮬레이터에서 호스트 PC는 `10.0.2.2`다. `localhost`는 에뮬레이터 자신이다
- Android는 `http://` 주소를 기본으로 막는다(cleartext). 개발 빌드에만 `usesCleartextTraffic`을 켜고 배포 빌드는 HTTPS만 쓴다
- `MediaQuery.padding`은 논리 픽셀이고 WebView 안 CSS px와 같은 단위다. 변환하지 않는다
- 계약의 `insets`는 키보드를 포함하지 않는다(`viewInsets`가 아니라 `padding`)
