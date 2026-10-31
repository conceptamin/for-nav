# app 작업 규칙

근로자 화면(`app-front/`)을 WebView 한 장으로 불러오는 Flutter 호스트 앱이다. 실행·구현 위치·확인 방법은 `README.md`에 있다.

브랜치·커밋·PR 규칙은 루트 `CLAUDE.md`를 따른다. 브랜치 영역은 `app`이다. 작업 항목은 `app-front/backlog/`에 있다(호스트 몫은 03·04·05).

## 읽는 순서

1. 루트 `CLAUDE.md`
2. `app-front/README.md` "호스트 계약"과 "Flutter 쪽에서 할 일" — 이 앱이 지키는 약속의 원본
3. `app-front/CLAUDE.md` — 웹 쪽 규칙. 아래 규칙은 거기서 호스트에 해당하는 것을 옮긴 것이다
4. 이 폴더의 `README.md`

## 지키는 것

- **계약은 `app-front/README.md`가 먼저다.** 메시지 `type`·필드를 더하거나 바꾸려면 그 문서 "호스트 계약"을 같은 PR에서 먼저 고치고, 웹(`app-front/src/bridge/`)과 이 앱을 함께 고친다. 모르는 `type`은 무시한다. `protocol` 번호는 기존 메시지의 의미가 바뀔 때만 올린다.
- **웹은 호스트 없이도 똑같이 동작해야 한다.** 그러니 웹에 호스트 전용 기능을 요구하지 않는다. 호스트가 해야 하는 일은 "없으면 브라우저가 한다"로 설계된 것(전화·외부 링크·뒤로 가기·안전 영역)뿐이다.
- **`init`은 웹이 `ready`를 보낸 뒤에만 보낸다.** 페이지 로드 이벤트에 기대지 않는다.
- **응급은 기다리지 않는다.** 웹은 `init` 전에는 `tel:`을 가로채지 않으므로, WebView 기본 처리(`NavigationDelegate` → 외부 앱)로도 119가 걸려야 한다. 오프라인 안내에도 119 전화를 둔다.
- **로그에 본문을 찍지 않는다.** `openExternal.url`(전화번호·지도 검색어), 이동 주소, 메시지 본문은 `debugPrint`에도 남기지 않는다. 기록은 `type`만. 개인정보(증상·연락처·리포트·토큰)는 다리를 타지 않는다.
- **앱 출처 밖은 WebView 안에서 열지 않는다.** 앱 출처는 `APP_URL`의 출처 하나다. 주소는 코드에 적지 않고 `--dart-define`으로 받는다(운영 주소는 `env/prod.json`).
- **네이티브 UI를 만들지 않는다.** 네이티브 화면은 WebView 하나와 오프라인 안내 한 장뿐이다. 화면·문구는 웹(`frontend/`)이 정한다.
- 의존성을 더할 때는 backlog 문서에 이유를 적는다. Flutter 버전은 `.fvmrc` 하나로 고정하고 `fvm flutter …`로만 실행한다.

## 검사와 커밋

```sh
cd app
fvm flutter analyze
fvm flutter test
```

- 커밋 메시지의 `테스트:` 줄에 위 결과와 확인한 기기(Android 에뮬레이터 / iOS 시뮬레이터 / 실기기)·경로를 적는다.
- 계약을 바꿨으면 `app-front`의 `npm run build` 결과도 적는다.
