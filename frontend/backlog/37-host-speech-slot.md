# 37. 앱 호스트 음성 인식 자리

상태: 완료(실제 앱 자막은 app-front 04에서 확인)
의존: 26 (통화 자막), app-front 03 (Flutter 셸)

## 목표
통화 자막(backlog 26)은 브라우저 Web Speech API로 받아쓴다. Flutter 앱의 WebView에서는 이것으로 받아쓸 수 없다(iOS WKWebView에는 없고, Android WebView에는 `webkitSpeechRecognition`이 있지만 켜자마자 `not-allowed`로 끝난다. app-front 04 결과). app-front 04가 호스트의 네이티브 음성 인식을 다리로 이어 오는데, 받아쓰기를 고르는 `src/api/speech.ts`는 `@fe` 안의 파일이라 app-front에서 고칠 수 없다. 이 항목은 앱이 호스트 음성 인식을 등록할 자리를 `speech.ts`에 둔다.

## 결정이 필요한 것
1. **등록 자리의 모양.** backlog 35(`setNativeGoogleSignIn`)와 같게 `setHostSpeech(fn)`. `fn(lang, handlers)`는 `startSpeech`와 같은 모양으로 끄는 함수를 돌려주고, 다시 켜기·오류 처리는 등록한 쪽이 맡는다. `isSpeechSupported()`는 등록이 있으면 참이다.
   - 결정(2026-10-31): 권장안. 사용자가 app-front 04 결정 1에서 "호스트 음성 인식"을 골랐다.
   - 통화 화면은 통화를 시작할 때 `isSpeechSupported()`를 한 번 읽는다. 호스트의 `init`은 첫 화면이 그려진 직후에 오고 S-12는 그보다 한참 뒤에 열리므로 구독(`useSyncExternalStore`)은 두지 않는다.

## 범위
- 하는 것
  - `src/api/speech.ts`: `HostSpeech` 타입, `setHostSpeech`, `isSpeechSupported`·`startSpeech`가 등록을 먼저 본다. 받아쓰기 언어는 지금처럼 `SPEECH_LANGS`(BCP-47)로 넘긴다
  - `README.md` 폴더 구조의 `api/` 줄, `CLAUDE.md` "백엔드·모델링과의 경계"의 공유 import 목록
- 하지 않는 것
  - 다리·호스트 코드(app-front 04). 이 폴더는 다리를 모른다
  - `src/api/call.ts`와 통화 화면 변경. 자막을 보내고 그리는 흐름은 같다

## 화면·파일
- 화면: S-12 통화 패널, C-02 통화. 브라우저(등록 없음)에서는 지금과 같다
- 파일: `src/api/speech.ts`, `README.md`, `CLAUDE.md`

## 완료 기준
- [x] `cd frontend && npm run build` 통과, `cd app-front && npm run build` 통과
- [x] 등록이 없으면 `isSpeechSupported()`·`startSpeech()`가 지금과 같다(Web Speech API를 쓴다)
- [x] 등록이 있으면 `startSpeech`가 등록 함수를 `SPEECH_LANGS` 값으로 부르고, 그 함수가 돌려준 끄기 함수를 그대로 돌려준다
- [ ] 실제 앱 통화 자막은 app-front 04 `## 결과`에서 확인한다

## 결과
- `cd frontend && npm run build` → 통과, `cd app-front && npm run build` → 통과
- `speech.ts`를 rolldown으로 묶어 Node에서 `window`를 비워 두고 확인했다(테스트 러너가 없어 임시 스크립트, 커밋하지 않음): 등록 없음 → `isSpeechSupported()` 거짓, `startSpeech('vi')`가 바로 `onUnsupported`. 등록 있음 → 참, `startSpeech('uz')`가 등록 함수를 `uz-UZ`로 부르고 그 끄기 함수를 그대로 돌려준다. `setHostSpeech(null)` 뒤 다시 거짓
- 화면 코드는 바뀌지 않아 브라우저 확인은 하지 않았다(등록이 없으면 지나는 길이 지금과 같다)

## 메모
