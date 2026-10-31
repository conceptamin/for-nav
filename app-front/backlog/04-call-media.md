# 04. 권한과 통화 매체(마이크·카메라·파일 선택·받아쓰기)

상태: 진행 중 (코드 완료, 실기기 통화·받아쓰기 확인 남음)
의존: 02, 03, frontend 37

## 목표
근로자 화면 가운데 브라우저 권한에 기대는 것 — 통화(마이크, WebRTC), 사진 선택(S-05, `<input type=file accept=image/*>`), 통화 자막 받아쓰기(Web Speech API) — 이 WebView 안에서도 동작하게 한다. Android WebView는 앱이 권한 요청과 파일 선택기를 구현해야 하고, iOS WKWebView에는 Web Speech API가 없다. 이 항목이 끝나면 S-12 전송 완료 화면에서 센터와 통화가 되고 자막이 뜬다.

## 결정이 필요한 것

1. **iOS 받아쓰기.** 권장: **호스트 음성 인식을 다리로 잇는다.** 호스트→웹 `type: "speech"`(`{ text, final: boolean, lang }`), 웹→호스트 `type: "speechStart"`(`{ lang }`)·`"speechStop"`. 웹의 `frontend/src/api/speech.ts`가 통로를 고르는 자리가 되어야 하므로 **`frontend/` 항목이 하나 필요하다**(`isSpeechSupported()`가 호스트 통로도 보게). 대안: iOS에서는 자막 없이 통화만(지금 Firefox와 같은 "받아쓰기를 못 하는 브라우저" 안내 줄). 1차 발표가 Android뿐이면 대안으로 시작할 수 있다.
   - 결정(2026-10-31): 권장안. Android WebView에서도 Web Speech API로 받아쓸 수 없어(결과 참고) 두 플랫폼 모두 호스트 음성 인식을 쓴다. 웹→호스트 메시지는 권장안대로, 호스트→웹은 `speech`(`text`·`final`)와 `speechError`(`denied`·`unsupported`)로 정했다(`lang`은 웹이 이미 알아 `speech`에서 뺐다). `frontend/` 항목은 frontend 37(`setHostSpeech`, PR #145)
2. **사진 선택.** Android WebView의 파일 선택기는 `webview_flutter`에서 Android 전용 `setOnShowFileSelector`로 구현한다(권장). 카메라 직접 촬영은 2차.
   - 결정(2026-10-31): 권장안. 고르는 화면은 `image_picker`(Android 13+ 시스템 사진 선택기, 권한 없음)

## 범위
- 하는 것
  - Android: `WebViewPermissionRequest`(마이크·카메라) 수락 — 앱 권한(`permission_handler`)을 먼저 받고 WebView 요청을 허용. 파일 선택기 구현. `AndroidManifest`의 `RECORD_AUDIO`·`CAMERA`
  - iOS: `Info.plist`의 `NSMicrophoneUsageDescription`·`NSCameraUsageDescription`·`NSPhotoLibraryUsageDescription`(한국어·영어). WKWebView `getUserMedia`는 iOS 14.3+에서 되고 권한 창은 시스템이 띄운다
  - 결정 1이 권장안이면: 계약에 `speech*` 메시지 추가(`README.md` 먼저), 호스트 `speech_to_text` 연결, `frontend/` 항목으로 `speech.ts`에 호스트 통로 추가
  - `README.md` "호스트 계약"(새 메시지), "Flutter 쪽에서 할 일"(권한 표), "나중에 붙일 자리"
- 하지 않는 것
  - TURN 서버, 푸시(센터가 걸 때 알림), 통화 음성 녹음, 백그라운드 통화
  - 권한 거부 뒤 설정 화면으로 보내는 안내(웹의 `micDenied` 안내 그대로)

## 화면·계약·파일
- 화면: S-05 사진 선택, S-12 통화 패널. 웹 화면 변경 없음(결정 1 권장안이면 `frontend/` 쪽 `speech.ts`만)
- 계약: (결정 1) `speechStart`·`speechStop`·`speech` 추가, `protocol` 그대로(기존 메시지 의미 불변)
- 수정: `app/`(권한·파일 선택기·음성 인식), `app-front/README.md`, (결정 1) `frontend/src/api/speech.ts`와 `frontend/backlog/` 항목

## 완료 기준
- [ ] Android 실기기: S-05에서 사진 선택이 갤러리를 열고 미리보기가 뜬다. S-12 통화가 PC 센터 화면(`frontend/` 1280px)과 붙고 양쪽 자막이 번역되어 보인다
- [ ] iOS 실기기: 통화가 붙는다. 자막은 결정 1에 따라 뜨거나(권장안) 안내 줄이 보인다(대안)
- [ ] 권한을 거부하면 웹의 기존 안내(`micDenied`)가 보이고 앱이 멈추지 않는다
- [ ] 앱 로그에 받아쓴 글·SDP·자막이 없다

## 결과
2026-10-31. 브랜치 `app-front/call-media`(frontend 37 브랜치 `frontend/host-speech-slot`을 병합해 둠).

바뀐 계약(`README.md` "호스트 계약"): 웹→호스트 `speechStart`(`lang`)·`speechStop`, 호스트→웹 `speech`(`text`, `final`)·`speechError`(`error`: `denied`|`unsupported`), `init.features`에 `speech`. `protocol`은 1 그대로다.

- 웹: `src/bridge/host.ts` `listenHostSpeech`(켜 둔 받아쓰기 하나에만 `speech`를 넘기고, 확정 문장 뒤 말하는 중 글을 빈 글로 지운다), `src/main.tsx`가 `features`에 `speech`가 있을 때만 `setHostSpeech` 등록, `/__host`에 "받아쓰기 시험"(글자 수·확정 문장 수·오류 종류만 보인다)
- 호스트: `lib/speech.dart`(`speech_to_text`, 다시 켜기·오류 분류), `lib/host_page.dart`(WebView 마이크 요청, Android 파일 선택기, 원격 음성 자동 재생), `AndroidManifest.xml`(`RECORD_AUDIO`·`MODIFY_AUDIO_SETTINGS`·음성 인식 서비스 `<queries>`), `Info.plist`(마이크·음성 인식·사진·카메라 설명, 한국어·영어)
- 의존성(호스트): `speech_to_text`(받아쓰기), `permission_handler` 12.x(Android 마이크 앱 권한. 13.x는 `compileSdk 37`을 요구해 지금 SDK로 빌드되지 않는다), `image_picker`(Android 사진 선택기), `webview_flutter_android`(Android 전용 API를 부르려고 직접 의존)

실행한 명령
- `cd app-front && npm run build` → 통과. `cd app && fvm flutter analyze` → 문제 없음, `fvm flutter test` → 15개 통과(받아쓰기 오류 분류, 메시지 형식, 권한·파일 형식 판정 추가)
- `cd frontend && npm run build` → 통과(frontend 37 병합 상태)

확인한 환경: Android 에뮬레이터(`fornav_api36`, 언어 vi), iOS 시뮬레이터(iPhone 17 Pro, iOS 26.4). 웹은 이 브랜치 app-front를 API 모드로 띄우고(`adb reverse`로 `localhost`, 안전한 출처) 백엔드는 이 브랜치 `backend/`.
- 브라우저(호스트 없음) `/__host`: "받아쓰기 시험" → `speechError unsupported`(보내지 않는다)
- Android `/__host`: features에 `speech`. 받아쓰기 시험 → 시스템 마이크 권한 창 → 거부하면 `speechError denied`가 웹까지 온다. 허용하면 `듣는 중`이고, 말이 없을 때 `error_no_match` 뒤 계속 다시 켠다. 다시 누르면 `speechStop`
- iOS `/__host`: 음성 인식 권한 창(`Info.plist` 문구가 그대로 보인다) → 마이크 권한 창 → `듣는 중`, 다시 누르면 `speechStop`. **첫 권한 허용 직후 시뮬레이터에서 앱이 한 번 멈췄다**(`coreaudio` "Initialize: RPC timeout. Apparently deadlocked. Aborting now."). 다시 열면 같은 흐름이 멈추지 않았다. 시뮬레이터 오디오 쪽 문제로 보이지만 실기기에서 첫 실행을 꼭 본다
- Android WebView의 Web Speech API: `webkitSpeechRecognition`은 있지만, 앱이 `RECORD_AUDIO`를 가진 상태에서도 켜면 `start` 직후 `not-allowed`로 끝났다(DevTools로 확인). 그래서 Android도 호스트 음성 인식이 필요하다
- Android S-12(vi): 센터 요청을 보낸 뒤 통화 패널에 "받아쓰기를 못 하는 브라우저" 안내 줄이 없다(호스트 등록이 잡힘). "Gọi"를 누르면 WebView 마이크 요청 → 허용, `getUserMedia`가 살아 있는 트랙을 준다
- Android 사진 선택기: `accept=image/*` `multiple` 입력 → 시스템 사진 선택기 → 한 장 고르면 웹 `input.files`에 같은 크기(106,556바이트)의 `image/png`가 온다. 취소하면 빈 목록이고 다시 열린다

완료 기준별
- [ ] Android 실기기 — 실기기 없음. 에뮬레이터로 사진 선택(미리보기 전 단계까지 `files` 확인)과 통화 마이크 권한까지 봤다. **PC 센터와 통화를 붙여 양쪽 자막을 보는 것은 하지 못했다**: 브라우저 패널은 마이크를 막고, 가짜 마이크를 쓰는 헤드리스 Chrome은 이 환경의 샌드박스에서 뜨지 않았고, 에뮬레이터 Chrome은 처음 실행 약관 동의가 필요해 쓰지 않았다
- [ ] iOS 실기기 — 실기기 없음. 시뮬레이터로 권한 창·받아쓰기 켜고 끄기까지 봤다
- [x] 권한을 거부하면 웹의 기존 안내가 보이고 앱이 멈추지 않는다 — Android 마이크 거부 시 WebView 요청도 거부(웹 `micDenied` 경로)되고, 받아쓰기는 `speechError denied` → 안내 줄. 앱은 멈추지 않았다
- [x] 앱 로그에 받아쓴 글·SDP·자막이 없다 — `[host]` 줄은 `type`·권한 종류·사진 장 수·오류 이름뿐이다. `speech`는 type도 찍지 않는다

남은 것(실기기에서)
1. Android·iOS 실기기에서 S-12 통화가 PC 센터와 붙고, 근로자 말이 받아써져 센터에 번역 자막으로 보이는지
2. 통화 음성(WebRTC)과 받아쓰기가 마이크를 함께 쓸 때 서로 끊지 않는지. Android는 음성 인식 서비스(Google 앱)가 다른 앱으로 마이크를 잡고, iOS는 `speech_to_text`가 오디오 세션을 `playAndRecord`로 바꿨다가 끌 때 되돌린다
3. Android 음성 인식기가 다시 켤 때마다 알림음을 내는 기기가 있는지(통화 중 몇 초마다 소리가 나면 안 된다)
4. iOS 첫 권한 허용 직후 멈춤이 실기기에서도 나는지

## 메모
- `/__host` 확인 화면은 앱 안에서 표가 세로로 깨져 보인다(`.check` 클래스가 공용 스타일과 겹친다, 운영에서도 같다). 이 항목 범위 밖이라 고치지 않았다
- 통화는 HTTPS 출처에서만 된다. 개발 중에는 Android 에뮬레이터가 `http://10.0.2.2`를 안전하지 않은 출처로 보므로, 이 항목의 확인은 배포 주소(HTTPS) 또는 `adb reverse`+`localhost`로 한다
- `frontend/README.md` "실서비스와 다른 점"의 통화 줄(TURN 없음, 푸시 없음)은 앱에서도 같다
