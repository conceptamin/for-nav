# 35. 앱 네이티브 Google 로그인 자리

상태: 완료
의존: 28 (근로자 Google 로그인), app-front 03 (Flutter 셸)

## 목표
Google은 임베디드 WebView 안의 웹 OAuth를 막는다(`403 disallowed_useragent`). 그래서 Flutter 앱 안에서는 S-03의 GIS 공식 버튼으로 로그인할 수 없다. app-front 06이 호스트의 네이티브 로그인으로 ID 토큰을 받아 오는데, S-03은 `@fe` 안의 화면이라 app-front에서 고칠 수 없다. 이 항목은 앱이 네이티브 로그인을 등록할 자리를 `googleId.ts`에 두고, 등록되면 S-03이 GIS 대신 앱 로그인 버튼을 그리게 한다.

## 결정이 필요한 것
1. **등록 자리의 모양.** app-front 06 `## 범위`의 권장안을 따른다: `setNativeGoogleSignIn(fn)`. 호스트의 `init`은 렌더 뒤 비동기로 오므로, 화면이 등록을 따라 다시 그리도록 `useNativeGoogleSignIn()`(useSyncExternalStore)도 둔다.
   - 결정(2026-10-31): 권장안. 사용자가 "06까지 하고 켜기"로 06 진행을 승인했다.
2. **취소와 실패를 어떻게 구분하나.** 등록 함수는 `Promise<string | null>`이다. `null`은 사용자가 계정 선택을 닫은 것(문구 없음), 예외는 실패(`loginFailed`). 화면이 다리의 오류 종류를 몰라도 된다.
   - 결정(2026-10-31): 권장안.

## 범위
- 하는 것
  - `src/api/googleId.ts`: `NativeGoogleSignIn` 타입, `setNativeGoogleSignIn`, `useNativeGoogleSignIn`
  - `src/pages/worker/Onboarding.tsx` S-03: 등록이 있으면 앱 로그인 버튼(Google 브랜드 규정 모양). 받은 토큰을 지금 그대로 `loginWithGoogle`로 보낸다. 이때 `VITE_GOOGLE_CLIENT_ID`가 없어도 `loginNotConfigured`를 보이지 않는다
  - `src/styles.css` `.btn.google`, `design.md` "근로자 로그인" 표 한 줄, `README.md`·`CLAUDE.md`의 해당 줄
- 하지 않는 것
  - 다리·호스트 코드(app-front 06). 이 폴더는 다리를 모른다
  - 서버·로그인 흐름(로그인 → 프로필 → `next`) 변경

## 화면·계약·파일
- 화면: S-03 `/signup` 로그인 단계. 브라우저(등록 없음)에서는 backlog 28과 같다
- 파일: `src/api/googleId.ts`, `src/pages/worker/Onboarding.tsx`, `src/styles.css`, `design.md`, `README.md`, `CLAUDE.md`

## 완료 기준
- [x] `cd frontend && npm run build` 통과, `cd app-front && npm run build` 통과
- [x] 브라우저(등록 없음): S-03이 backlog 28과 같다(단독 모드 데모 버튼)
- [x] 등록이 있으면 앱 로그인 버튼이 보이고, 누르면 등록 함수를 부른다. `null`이면 문구 없이 버튼으로, 예외면 `loginFailed` 한 줄

## 결과
- 앱 쪽 연결과 실기기 확인은 app-front 06의 `## 결과`에 적는다.

## 메모
- app-front 06 `## 범위` "웹(`frontend/`, 별도 항목)"이 이 항목이다.
