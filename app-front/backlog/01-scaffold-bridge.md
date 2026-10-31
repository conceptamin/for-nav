# 01. 프로젝트 뼈대와 호스트 다리(bridge)

상태: 완료(실제 WebView 확인은 03에서)
의존: 없음

## 목표
Flutter WebView 안에서 돌 근로자 앱의 웹 쪽 뼈대를 만든다. Vite + React + TypeScript 프로젝트, 호스트 계약(`README.md` "호스트 계약")의 웹 쪽 구현(`src/bridge/`), 그리고 다리가 동작하는지 눈으로 보는 확인 화면 `/__host`다. 근로자 화면은 넣지 않는다(02). 이 항목이 끝나면 Flutter 쪽(03)이 붙을 계약이 코드로 있고, 보통 브라우저에서는 아무 다리 없이 같은 화면이 뜬다.

## 범위
- 하는 것
  - `package.json`(의존성 버전은 `frontend/package.json`과 같은 값), `vite.config.ts`(포트 5181, `/api` 프록시 `ws: true`), `tsconfig.json`(`frontend/`와 같음), `index.html`(`viewport-fit=cover`, 줌 허용), `.gitignore`
  - `src/bridge/host.ts`: 전송 통로 감지(`window.ForNav.postMessage` → `window.flutter_inappwebview.callHandler` 순), `send()`, `window.fornav = { receive, onBack }` 설치, `init`·`insets` 처리와 `:root --inset-*` 반영, `ready` 한 번 보내기. 메시지 본문을 `console`에 찍지 않는다
  - `src/bridge/links.ts`: 문서 수준 클릭 가로채기. `tel:`·`mailto:`·`sms:`와 앱 출처 밖 `http(s)` 링크를 호스트가 `init`을 보낸 뒤에만 `openExternal`로 넘긴다. 호스트가 없거나 `init` 전이면 손대지 않는다
  - `src/bridge/HostProvider.tsx`: React 컨텍스트와 `useHost()` — `{ present, ready, platform, appVersion, locale, insets, openExternal(url) }`. 화면은 이것만 쓴다
  - `src/pages/HostCheck.tsx`(`/__host`): 호스트 있음/없음, 통로 종류, `init` 받음 여부, platform·appVersion·locale, insets 값, `VITE_API_BASE`(모드), 최근 보낸·받은 메시지의 `type` 목록(본문은 보이지 않는다), 시험 링크 두 개(`tel:119`, 카카오맵 검색) — 눌렀을 때 호스트가 있으면 `openExternal`, 없으면 브라우저 기본 동작
  - `src/main.tsx`: `/__host` 하나, `/`와 알 수 없는 경로는 `/__host`로. 하단 119 띠는 아직 두지 않는다(근로자 화면과 함께 02에서)
  - `src/styles.css`: `design.md` "안전 영역"·"높이와 스크롤"·"터치"의 규칙과 확인 화면용 최소 스타일. 토큰 값은 `frontend/src/styles.css`의 `:root`에서 쓰는 것만 같은 값으로 가져온다
  - `.claude/launch.json`에 `app-front` 개발 서버 항목, 루트 `CLAUDE.md` 영역 표에 `app-front` 행
- 하지 않는 것
  - 근로자 화면·i18n·`domain/` 가져오기(02), Flutter 프로젝트(03), 권한·받아쓰기(04), 번들 빌드(05)
  - `frontend/`·`backend/` 코드 수정, CI 잡(`chore/` 별도)

## 화면·계약·파일
- 화면: `/__host`(확인 화면). 근로자 화면 없음
- 계약: `README.md` "호스트 계약" 전부가 이 항목에서 처음 구현된다 — 웹→호스트 `ready`·`openExternal`, 호스트→웹 `init`·`insets`, 동기 `onBack()`
- 추가: `app-front/` 전체(`README.md`, `CLAUDE.md`, `design.md`, `backlog/`, 설정 파일, `src/`)
- 수정: 루트 `CLAUDE.md`(영역 표), `.claude/launch.json`

## 완료 기준
- [x] `cd app-front && npm ci && npm run build` 통과
- [x] 브라우저(호스트 없음)에서 `http://localhost:5181/`이 `/__host`로 가고 "호스트: 없음(브라우저)"가 보인다. `tel:119` 링크를 누르면 브라우저 기본 동작(PC는 아무 일 없음 또는 전화 앱 선택 창)이고 `openExternal`이 기록되지 않는다
- [x] 브라우저 콘솔에서 `window.ForNav = { postMessage: (s) => console.log('host<-', JSON.parse(s).type) }`를 넣고(새로고침 없이) `window.fornav.receive({ protocol: 1, type: 'init', platform: 'android', appVersion: '0.0.1', locale: 'vi-VN', insets: { top: 24, right: 0, bottom: 48, left: 0 } })`를 부르면 "호스트: 있음(webview_flutter)"가 보이고 `ready`가 한 번 찍히며, 화면의 platform·locale·insets가 바뀌고 `document.documentElement.style`에 `--inset-bottom: 48px`가 있다
- [x] 그 상태에서 `tel:119`와 지도 링크를 누르면 콘솔에 `host<- openExternal`만 찍히고 페이지가 이동하지 않는다. `init` 전(통로만 만들고 `receive`를 부르기 전)에 누르면 가로채지 않는다
- [x] `window.fornav.onBack()`이 `/__host`에서 `false`를 돌려준다(갈 곳이 없다)
- [x] 360px 폭에서 가로 넘침 없음
- [x] `diff <(jq .dependencies ../frontend/package.json) <(jq .dependencies package.json)`과 `devDependencies` 비교가 비어 있다

## 결과
- 실행(2026-10-31)
  - `npm install`(lock 생성) 뒤 `npm ci && npm run build` → 통과(tsc + vite build, 99 modules)
  - `diff <(jq .dependencies ../frontend/package.json) <(jq .dependencies package.json)`과 `devDependencies` 비교 → 차이 없음
  - 내장 브라우저(Chromium, 375×812) `http://localhost:5181/` → `/__host`로 이동, "호스트: 없음(브라우저)". 가짜 클릭(anchor에 `dispatchEvent`) 세 종류(`tel:`, 다른 출처 https, 같은 출처) 모두 가로채지 않음, `onBack()` false, 기록 0건
  - 통로만 만든 상태(`window.ForNav`): `tel:` 가로채지 않음, 보낸 메시지 0건
  - `receive(init …)` 뒤: "있음(webview_flutter)", `ready` 1건 → `init` 수신, platform·appVersion·locale·insets 표시, `--inset-bottom: 48px`. `tel:`·지도 링크는 `openExternal`(url 포함)로 나가고 기본 동작이 막힘, 같은 출처 링크는 그대로. `onBack()` false, 경로 그대로
  - JSON이 아닌 입력·모르는 type은 무시, `insets` 메시지는 `--inset-bottom: 20px`로 반영. 콘솔 오류 0건, 가로 넘침 없음
- 결정 사항
  - 통로 감지는 `installHost()` 때 한 번이 아니라 첫 `send()`·`receive()` 때도 다시 한다(늦게 생긴 통로). 브라우저에서 새로고침 없이 호스트를 흉내 낼 수 있게 하기 위해서다. 실제 호스트는 문서 시작 때 통로를 만들므로 동작이 같다(`README.md` "감지"에 적음)
  - 뒤로 가기 기본 동작은 react-router가 `history.state.idx`에 두는 이력 번호로 판단한다. 단계가 있는 화면을 위한 `setBackHandler()`를 두었고 02에서 쓴다
  - 하단 119 띠는 이 항목에 두지 않았다(근로자 화면과 함께 02)
- 남은 문제
  - 실제 WebView(Android·iOS)에서는 아직 확인하지 않았다(03). `flutter_inappwebview` 통로는 코드만 있고 확인하지 않았다
  - CI에 이 폴더의 잡이 없다(`chore/` 별도)

## 메모
- `webview_flutter`의 JavaScript 채널은 Android·iOS 모두 `window.<채널 이름>.postMessage(문자열)`을 만든다. iOS에서는 `window.webkit.messageHandlers`를 감싼 것이라 직접 쓰지 않는다
- `flutter_inappwebview`는 `callHandler`가 Promise를 돌려주지만 계약은 응답을 쓰지 않으므로 무시한다
- 확인 화면 문구는 한국어·영어 고정이다. 개발 확인용이라 i18n 키를 만들지 않는다(`design.md` "호스트 확인 화면")
- 확인 화면 바깥 클래스는 `.host-check`다(2026-10-31). 처음 이름 `.check`가 backlog 02로 함께 불러오는 `frontend/src/styles.css`의 동의 체크박스 `.check { display: flex }`와 겹쳐 카드가 세로로 좁게 늘어섰다. 이 폴더의 확인 화면 클래스는 `frontend/` 클래스와 겹치지 않게 `host-` 접두사를 붙인다
