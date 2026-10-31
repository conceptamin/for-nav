# 06. 앱 안 근로자 Google 로그인(네이티브 로그인 → 다리로 ID 토큰)

상태: 대기
의존: 03 (Flutter 셸), frontend 28 (근로자 Google 로그인 화면), backend 21 (`POST /api/auth/worker/google`)

## 목표
frontend 28의 S-03은 Google Identity Services(GIS) 공식 버튼으로 ID 토큰을 받는다. 그런데 Google은 임베디드 WebView 안의 웹 OAuth를 막는다(`403 disallowed_useragent`). 그래서 Flutter 앱 안에서는 이 버튼으로 로그인할 수 없고, 지금 앱은 서버 `WORKER_AUTH=off`(데모 로그인)로만 확인한다. 이 항목은 호스트가 네이티브 Google 로그인(`google_sign_in`)으로 ID 토큰을 받아 다리로 웹에 넘기는 일이다. 웹은 그 토큰을 지금처럼 `loginWithGoogle`로 서버에 보낸다. 이 항목이 끝나면 `WORKER_AUTH=google` 서버를 불러온 Android·iOS 앱에서 실제 Google 계정으로 로그인하고, `fornav_worker` 쿠키로 센터 요청이 201이 된다.

## 결정이 필요한 것

1. **ID 토큰의 `aud`를 어떻게 맞추나.** backend 21은 `aud`를 `GOOGLE_CLIENT_ID`(웹 클라이언트 ID) 하나와만 비교한다.
   - 확인한 것(2026-10-31)
     - Android: `google_sign_in` 7.x는 Credential Manager를 쓴다. `serverClientId`가 꼭 있어야 하고, 여기에 웹 클라이언트 ID를 주면 ID 토큰의 `aud`가 그 웹 ID다. Android OAuth 클라이언트(패키지 이름 + SHA-1)는 같은 Google Cloud 프로젝트에 등록만 하고 코드에는 넣지 않는다.
     - iOS: iOS 클라이언트 ID는 `clientId`(또는 `Info.plist`의 `GIDClientID`)로 준다. `serverClientId`(`GIDServerClientID`)를 주면 GoogleSignIn-iOS가 인가·토큰 요청에 `audience=<serverClientID>` 파라미터를 붙인다(`GIDSignIn.m`의 `kAudienceParameter`). 그래서 `aud`는 웹 ID, `azp`는 iOS ID가 될 것으로 본다. 다만 이것은 소스에서 추론한 것이고 문서가 직접 말하지는 않는다. `serverClientId`를 주지 않으면 `aud`는 iOS 클라이언트 ID다.
   - 권장: **두 플랫폼 모두 `serverClientId`에 웹 클라이언트 ID를 준다.** 그러면 backend 21을 바꾸지 않는다. iOS는 아래 완료 기준(서버가 웹 ID 하나로 받아 주는지)으로 실기기에서 확인한다.
   - 대안(iOS 확인이 실패하면): 서버가 `GOOGLE_CLIENT_ID`를 여러 값(웹·iOS)으로 받는다. backend 항목이 따로 필요하다(`## 메모`).
2. **다리 메시지 이름과 모양.** 지금 계약에는 요청-응답 짝이 없고 "필요하면 `type`을 둘로 나눈다"고 되어 있다.
   - 권장: 웹 → 호스트 `googleSignIn`, 호스트 → 웹 `googleSignInResult`. 응답은 성공이면 `idToken`, 실패면 `error`(`canceled` | `failed`) 하나다.
   - 대안: 이름을 `authGoogle`/`authGoogleResult`처럼 묶음으로 짓기. 다른 로그인을 붙일 계획이 없으므로 권장안이 더 바로 읽힌다.
   - 함께 정할 것
     - **호스트가 이 기능을 아는지 웹이 어떻게 아나.** 권장: `init`에 `features: ["googleSignIn"]`을 더한다. 필드를 더하는 것이라 기존 메시지의 의미가 바뀌지 않고 `protocol`은 1 그대로다. 03 빌드처럼 `features`가 없는 호스트에는 웹이 `googleSignIn`을 보내지 않는다. 응답을 영영 기다리는 일이 없다.
     - **"인증 토큰은 다리를 타지 않는다" 규칙의 예외.** `README.md` "다리로 보내지 않는 것"에 이 메시지 하나만 예외로 적는다. 호스트·웹 모두 `idToken`을 저장하거나 로그에 찍지 않는다. 웹은 받은 토큰을 서버에 한 번 보내고 버린다.
3. **실패·취소 UX.**
   - 권장
     - 취소(`canceled`)면 아무 문구 없이 로그인 버튼으로 돌아간다. 사용자가 스스로 닫은 것이다.
     - 실패(`failed`: 네트워크·설정 오류·Google Play 서비스 없음)는 frontend 28과 같은 `loginFailed` 한 줄을 보인다. 버튼을 다시 누르면 다시 시도한다.
     - 서버가 토큰을 거절하면(`loginWithGoogle` 401)도 같은 `loginFailed`다.
     - 응답을 기다리는 시간 제한은 두지 않는다. 계정 선택 창은 사용자가 오래 들고 있을 수 있다. 대신 기다리는 동안 버튼만 `disabled`로 둔다. 앱이 백그라운드에서 돌아왔는데 응답이 없으면 호스트가 `failed`를 보낸다.
     - 데모 로그인으로 몰래 대체하지 않는다(frontend 28 결정 2). 하단 119 띠는 로그인 화면에서도 그대로 보인다.
   - 호스트 유무에 따라 버튼이 달라진다: `app-front/CLAUDE.md`는 "호스트가 있을 때만 보이는 화면·문구를 만들지 않는다"고 한다. 문구는 같은 `loginGoogle`이고 흐름도 같다. 하지만 버튼을 그리는 방식이 호스트에 따라 달라지는 첫 예외다. 권장은 "브라우저는 GIS, 앱은 네이티브"를 `README.md` "호스트가 없을 때"에 예외로 적는 것이다. 웹 OAuth가 앱 안에서 막혀 다른 길이 없기 때문이다.
   - 계정 바꾸기: 웹이 로그아웃해도 호스트에는 Google 로그인 상태가 남는다. 권장은 호스트가 `googleSignIn`을 받을 때마다 먼저 `signOut()`을 부르고 `authenticate()`하는 것이다. 늘 계정 선택이 뜨고, 로그아웃용 메시지를 따로 두지 않는다.
4. **03·04와의 순서.**
   - 03(Flutter 셸, PR conceptamin/for-nav#119)이 병합된 뒤 시작한다. `app/lib/host_page.dart`의 채널 처리에 메시지 하나를 더하는 일이기 때문이다.
   - 04(권한·통화 매체)와는 서로 기대지 않는다. 다만 둘 다 `app/lib/host_page.dart`와 `README.md` "호스트 계약"을 고친다. 권장은 동시에 하지 않고 먼저 시작한 쪽이 병합된 뒤 다음을 하는 것이다. 로그인이 막혀야 앱에서 센터 요청(04의 통화 확인 전제)까지 갈 수 있으므로, `WORKER_AUTH=google`로 앱을 확인하려면 이 항목을 04보다 먼저 하는 것을 권장한다.
   - frontend 28·backend 21(PR conceptamin/for-nav#122·#120)이 병합된 뒤 시작한다.

## 범위
- 하는 것
  - **계약(`README.md` 먼저)**: `googleSignIn`·`googleSignInResult`, `init.features`. "다리로 보내지 않는 것"의 토큰 예외. "Flutter 쪽에서 할 일"에 Google 로그인 설정 줄
  - **호스트(`app/`)**
    - `google_sign_in`(7.x) 의존성. `GoogleSignIn.instance.initialize(clientId: <iOS 클라이언트 ID>, serverClientId: <웹 클라이언트 ID>)`. 두 값은 `APP_URL`처럼 `--dart-define`(`GOOGLE_IOS_CLIENT_ID`, `GOOGLE_WEB_CLIENT_ID`)로 넘기고 코드에 적지 않는다
    - `googleSignIn`을 받으면 `signOut()` → `authenticate()` → `authentication.idToken`을 `googleSignInResult`로 보낸다
    - `GoogleSignInException.code`가 `canceled`면 `error: "canceled"`, 그 밖과 `idToken`이 비었을 때는 `"failed"`
    - iOS `Info.plist`: 역방향 iOS 클라이언트 ID URL 스킴(`CFBundleURLTypes`)
    - 로그에는 `type`과 `error`만 남긴다. `idToken`·이메일·이름은 찍지 않는다
    - `init`에 `features: ["googleSignIn"]`. 두 클라이언트 ID가 빌드에 없으면 넣지 않는다. 그러면 웹은 지금처럼 GIS 버튼을 그리고, 앱 안에서는 실패한다(설정 실수가 바로 보인다)
  - **웹(`app-front/src/bridge/`)**
    - `useHost()`에 `features`를 더한다
    - `requestGoogleIdToken(): Promise<string>`을 둔다. 내부에서 `googleSignIn`을 보내고 `googleSignInResult` 하나를 기다린다. 취소·실패는 종류를 담은 예외로 던진다
    - 토큰은 이 함수의 반환값으로만 지나가고 저장하지 않는다
  - **웹(`frontend/`, 별도 항목)**: S-03은 `@fe` 안의 화면이라 이 폴더에서 고칠 수 없다(`CLAUDE.md` "`@fe` 안의 파일을 수정하지 않는다"). frontend 쪽에 "네이티브 로그인 자리"를 두는 항목이 하나 필요하다.
    - 권장: `frontend/src/api/googleId.ts`에 `setNativeGoogleSignIn(fn: () => Promise<string>)`을 둔다. 앱은 `src/main.tsx`에서 `useHost().present && features.includes('googleSignIn')`일 때 `requestGoogleIdToken`을 등록한다.
    - S-03은 등록된 함수가 있으면 GIS 공식 버튼 대신 앱 로그인 버튼을 그린다. 누르면 받은 토큰을 지금 그대로 `loginWithGoogle`(`frontend/src/api/auth.ts`)로 보낸다. 이때는 `VITE_GOOGLE_CLIENT_ID`가 없어도 "로그인 설정이 없습니다"를 보이지 않는다.
    - 화면은 다리를 모르고, 호스트가 없는 브라우저에서는 등록이 없으므로 frontend 28과 같다.
    - 이 일은 backlog 04의 `speech.ts` 호스트 통로와 같은 모양이다.
- 하지 않는 것
  - `backend/` 코드 수정. 결정 1이 대안으로 가면 backend 항목을 따로 쓴다
  - Apple 로그인. iOS 앱 심사는 제3자 로그인만 있으면 "Sign in with Apple"을 요구할 수 있다(`## 메모`). 스토어 배포 항목에서 정한다
  - One Tap·자동 로그인(앱을 열 때 조용히 로그인). 로그인 상태는 서버 쿠키가 지킨다(frontend 28)
  - 스토어 배포용 서명 키의 SHA-1 등록(배포 항목). 이 항목은 디버그 키로 확인한다
  - 프로필·리포트 서버 저장, 기기 사이 동기화(frontend 28과 같음)

## 화면·계약·파일
- 화면: S-03 `/signup` 로그인 단계. 호스트가 있고 `features`에 `googleSignIn`이 있을 때만 GIS 버튼 대신 앱 로그인 버튼이 보인다. 문구·흐름(로그인 → 프로필 → `next`)은 frontend 28 그대로다. 버튼 모양은 Google 브랜드 규정(흰 바탕, 공식 G 로고, "Google 계정으로 로그인")을 따른다. 데모 버튼의 글자 G를 그대로 쓰지 않는다. 클래스·자산은 frontend 항목에서 `design.md`와 함께 정한다
- 계약 초안(`README.md` "메시지 형식" 표에 더한다)

  **웹 → 호스트**

  | `type` | 필드 | 언제 | 호스트가 할 일 |
  |---|---|---|---|
  | `googleSignIn` | 없음 | S-03에서 앱 로그인 버튼을 눌렀을 때. `init.features`에 `googleSignIn`이 있을 때만 보낸다 | `signOut()` 뒤 `authenticate()`로 네이티브 계정 선택을 띄우고, 끝나면 `googleSignInResult`를 한 번 보낸다. 앞 요청이 끝나기 전에 또 오면 앞 요청을 `failed`로 끝낸다 |

  **호스트 → 웹**

  | `type` | 필드 | 언제 | 웹이 할 일 |
  |---|---|---|---|
  | `init`(필드 추가) | `features`: 문자열 배열(예: `["googleSignIn"]`). 없으면 빈 배열로 본다 | 지금과 같이 `ready` 뒤 한 번 | `useHost().features`가 채워진다. 모르는 값은 무시한다 |
  | `googleSignInResult` | 성공: `idToken`(Google ID 토큰 JWT). 실패: `error`(`canceled` \| `failed`) | `googleSignIn`의 응답으로 한 번 | 기다리던 `requestGoogleIdToken()`을 끝낸다. 기다리는 요청이 없으면 무시한다. 토큰을 저장하거나 로그에 찍지 않는다 |

  ```json
  { "protocol": 1, "type": "googleSignIn" }
  { "protocol": 1, "type": "googleSignInResult", "idToken": "eyJhbGciOiJSUzI1NiIs…" }
  { "protocol": 1, "type": "googleSignInResult", "error": "canceled" }
  ```
- 수정
  - `app-front/README.md`: "호스트 계약"의 메시지 표, "다리로 보내지 않는 것", "Flutter 쪽에서 할 일", "실서비스와 다른 점"
  - `app-front/src/bridge/host.ts`·`HostProvider.tsx`: `features`, `requestGoogleIdToken`
  - `app-front/src/main.tsx`: 네이티브 로그인 등록
  - `app-front/src/pages/HostCheck.tsx`: `features`를 보이고, 개발용 "Google 로그인 시험" 버튼을 둔다. 성공·실패 종류만 보이고 토큰은 보이지 않는다
  - `app/pubspec.yaml`·`pubspec.lock`(`google_sign_in`), `app/lib/host_page.dart`·`bridge.dart`, `app/ios/Runner/Info.plist`, `app/README.md`(Google Cloud 설정, `--dart-define`)
  - frontend 항목 몫: `frontend/src/api/googleId.ts`, `frontend/src/pages/worker/Onboarding.tsx`, `frontend/design.md`

## 완료 기준
- [ ] `cd app-front && npm run build` 통과, `cd app && fvm flutter analyze` 통과, `fvm flutter test` 통과(`googleSignInResult` 메시지 만들기 단위 테스트 포함)
- [ ] 브라우저(호스트 없음): S-03이 frontend 28과 같이 GIS 공식 버튼을 그린다. `/__host`의 `features`가 빈 배열이다
- [ ] 클라이언트 ID 없이 빌드한 앱: `init`에 `features`가 없고 S-03이 지금과 같다(앱 안 GIS는 `disallowed_useragent`로 실패한다)
- [ ] Android 에뮬레이터(Google Play 이미지)·실기기: 서버는 `WORKER_AUTH=google GOOGLE_CLIENT_ID=<웹 클라이언트 ID>`다. 앱 로그인 버튼 → 네이티브 계정 선택 → 프로필 단계 → `/home`. `fornav_worker` 쿠키가 생기고 S-12 센터 요청이 201이다
- [ ] iOS 시뮬레이터·실기기: 같은 서버 설정(웹 클라이언트 ID 하나)으로 위와 같이 로그인된다. 이 줄이 결정 1의 iOS `aud` 확인이다. 401이면 결정 1의 대안으로 가고 backend 항목을 쓴다
- [ ] 계정 선택 창을 닫으면 문구 없이 버튼으로 돌아온다. 비행기 모드에서 누르면 `loginFailed` 한 줄이 보이고 앱이 멈추지 않는다
- [ ] 로그아웃 뒤 다시 누르면 계정 선택이 다시 뜨고, 다른 계정으로 들어가면 앞 계정의 프로필이 보이지 않는다(frontend 28 결정 4)
- [ ] 앱 로그(`flutter run` 출력)·웹 `console`에 ID 토큰·이메일·이름이 없다. `localStorage`·`sessionStorage`에 `eyJ`로 시작하는 값이 없다

## 결과

## 메모
- **사용자 준비(구현 전)**: backend 21 `## 메모`의 웹 클라이언트가 있는 같은 Google Cloud 프로젝트에 클라이언트 두 개를 더 만든다.
  - **Android** OAuth 클라이언트: 패키지 `dev.fornav.for_nav`, 디버그 키 SHA-1. `keytool -list -v -keystore ~/.android/debug.keystore -alias androiddebugkey -storepass android`로 구한다. 배포 키 SHA-1은 배포 때 더한다
  - **iOS** OAuth 클라이언트: 번들 ID `dev.fornav.forNav`
  - 웹 클라이언트 ID는 비밀이 아니다. 클라이언트 비밀번호는 쓰지 않는다
  - 패키지·번들 ID는 PR conceptamin/for-nav#119(03)의 값이다. 바뀌면 클라이언트도 다시 만든다
- **backend 항목이 필요해지는 경우**: 결정 1의 iOS 확인에서 `aud`가 iOS 클라이언트 ID로 오면, `GOOGLE_CLIENT_ID`를 쉼표로 여러 값 받게 하는 backend 항목을 따로 쓴다. `google-auth`의 `verify_oauth2_token`은 `audience`에 목록도 받으므로 검증 코드는 작다. 웹 ID를 늘 허용하고 iOS ID를 더하는 방식이다. 이 항목에서 `backend/`를 고치지 않는다
- **쿠키 출처**: 로그인 세션은 같은 출처 HttpOnly 쿠키다(backend 21 "다른 출처 프론트에서 쿠키 보내기"는 하지 않음). 그래서 앱이 불러오는 웹 주소와 API가 같은 출처여야 실제 로그인이 된다. 개발 서버 프록시나 맥미니 같은 출처 서빙이 그렇다. 다른 출처에 배포하면(`README.md` 결정 2) WKWebView가 제3자 쿠키를 막아 로그인이 유지되지 않는다. 번들(05)도 같은 문제가 있다
- `google_sign_in` 7.x는 6.x와 API가 다르다(`GoogleSignIn.instance.initialize`·`authenticate`). 예전 예제의 `GoogleSignIn(scopes:).signIn()`을 따라 쓰지 않는다. 스코프는 요청하지 않는다(ID 토큰만 쓴다)
- iOS 앱 심사 지침 4.8은 제3자 로그인을 쓰는 앱에 Apple 로그인 같은 대안을 요구할 수 있다. 스토어 배포 항목에서 확인한다
- nonce는 쓰지 않는다. 웹 GIS 흐름(frontend 28)도 쓰지 않고, 서버는 `exp`와 서명만 본다. 재생 방지를 강화하려면 서버 nonce 발급이 필요하고, 그것은 backend·frontend·app 세 곳의 일이다
- 확인 자료: GoogleSignIn-iOS `GoogleSignIn/Sources/GIDSignIn.m`(`kAudienceParameter`, `serverClientID`가 있으면 인가·토큰 요청에 `audience`를 붙인다). Google "Authenticate with a backend server"(iOS) 문서의 "`aud`는 앱의 클라이언트 ID 중 하나와 같아야 한다", 백엔드 예시의 `WEB_CLIENT_ID`
