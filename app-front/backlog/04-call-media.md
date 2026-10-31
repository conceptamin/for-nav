# 04. 권한과 통화 매체(마이크·카메라·파일 선택·받아쓰기)

상태: 대기
의존: 02, 03

## 목표
근로자 화면 가운데 브라우저 권한에 기대는 것 — 통화(마이크, WebRTC), 사진 선택(S-05, `<input type=file accept=image/*>`), 통화 자막 받아쓰기(Web Speech API) — 이 WebView 안에서도 동작하게 한다. Android WebView는 앱이 권한 요청과 파일 선택기를 구현해야 하고, iOS WKWebView에는 Web Speech API가 없다. 이 항목이 끝나면 S-12 전송 완료 화면에서 센터와 통화가 되고 자막이 뜬다.

## 결정이 필요한 것

1. **iOS 받아쓰기.** 권장: **호스트 음성 인식을 다리로 잇는다.** 호스트→웹 `type: "speech"`(`{ text, final: boolean, lang }`), 웹→호스트 `type: "speechStart"`(`{ lang }`)·`"speechStop"`. 웹의 `frontend/src/api/speech.ts`가 통로를 고르는 자리가 되어야 하므로 **`frontend/` 항목이 하나 필요하다**(`isSpeechSupported()`가 호스트 통로도 보게). 대안: iOS에서는 자막 없이 통화만(지금 Firefox와 같은 "받아쓰기를 못 하는 브라우저" 안내 줄). 1차 발표가 Android뿐이면 대안으로 시작할 수 있다.
2. **사진 선택.** Android WebView의 파일 선택기는 `webview_flutter`에서 Android 전용 `setOnShowFileSelector`로 구현한다(권장). 카메라 직접 촬영은 2차.

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

## 메모
- 통화는 HTTPS 출처에서만 된다. 개발 중에는 Android 에뮬레이터가 `http://10.0.2.2`를 안전하지 않은 출처로 보므로, 이 항목의 확인은 배포 주소(HTTPS) 또는 `adb reverse`+`localhost`로 한다
- `frontend/README.md` "실서비스와 다른 점"의 통화 줄(TURN 없음, 푸시 없음)은 앱에서도 같다
