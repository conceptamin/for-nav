# 03. Flutter 셸(호스트) 프로젝트

상태: 대기
의존: 01 (02와 독립이지만 02 뒤에 하면 실제 화면으로 확인할 수 있다)

## 목표
이 웹앱을 불러오는 Flutter 앱을 만든다. WebView 한 장, `README.md` "호스트 계약"의 호스트 쪽 구현(채널·`init`·`openExternal`·뒤로 가기·안전 영역), 앱 출처 밖 이동 차단이다. 이 항목이 끝나면 Android 에뮬레이터·iOS 시뮬레이터에서 앱을 열어 `/__host`가 "호스트: 있음"을 보이고, 119 링크가 전화 앱을 연다.

## 결정이 필요한 것

1. **프로젝트 위치.** 권장: 이 저장소의 `app/`(새 영역, 루트 `CLAUDE.md` 표에 `app` 행). 계약 변경을 웹·호스트 한 PR에서 할 수 있다. 대안: 별도 저장소(스토어 배포 파이프라인을 따로 두고 싶을 때).
2. **WebView 라이브러리.** 권장: `webview_flutter`(공식). 파일 선택기·권한은 04에서 직접 구현한다. 대안: `flutter_inappwebview`(파일 선택기·`onPermissionRequest` 내장, 의존성 큼). 웹 쪽은 둘 다 감지하므로 바꿔도 웹은 그대로다.
3. **불러올 주소.** 개발: `http://10.0.2.2:5181`(Android 에뮬레이터) / `http://localhost:5181`(iOS 시뮬레이터) — `--dart-define=APP_URL=`로 넘긴다. 배포: `README.md` "결정이 필요한 것" 2(배포 출처)와 함께 정한다. 권장은 환경별 `--dart-define`이고 코드에 주소를 적지 않는다.
4. **Flutter 버전.** 로컬에 fvm `3.24.3`이 있다. 권장: fvm으로 고정하고 `.fvmrc`를 커밋한다.

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

## 메모
- Android 에뮬레이터에서 호스트 PC는 `10.0.2.2`다. `localhost`는 에뮬레이터 자신이다
- Android는 `http://` 주소를 기본으로 막는다(cleartext). 개발 빌드에만 `usesCleartextTraffic`을 켜고 배포 빌드는 HTTPS만 쓴다
- `MediaQuery.padding`은 논리 픽셀이고 WebView 안 CSS px와 같은 단위다. 변환하지 않는다
- 계약의 `insets`는 키보드를 포함하지 않는다(`viewInsets`가 아니라 `padding`)
