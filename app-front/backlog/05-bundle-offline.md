# 05. 앱 안에 번들해 네트워크 없이 단독 모드로 열기

상태: 대기
의존: 02, 03

## 목표
빌드 결과(`dist/`)를 Flutter 앱 자산으로 넣어 **네트워크가 없어도 근로자 화면 전부(단독 모드)가 열리게** 한다. 지하·이동통신망이 끊긴 곳에서도 응급 판정과 접수 창구 화면이 떠야 한다는 `frontend/`의 원칙을 앱에서 지키는 방법이다. 원격 주소 방식(03)은 그대로 두고, 빌드 설정으로 둘 다 만들 수 있게 한다.

## 결정이 필요한 것

1. **자산을 어떻게 여나.** 권장: `webview_flutter`의 `loadFlutterAsset`(Android는 `file:///android_asset/…`, iOS는 앱 번들 `file://`). 대안: 앱 안 로컬 HTTP 서버(출처가 `http://localhost:<port>`가 되어 `file://`의 제약 — `fetch` 상대 경로, 쿠키, `history.pushState` — 를 피한다). `file://`에서 `createBrowserRouter`가 깨지면 해시 라우터로 바꾸지 않고 로컬 서버 쪽으로 간다(`frontend/`와 경로가 같아야 한다).
2. **API 주소.** 번들은 같은 출처가 없으므로 `VITE_API_BASE`를 절대 주소로 넣어 빌드한다. 서버 `CORS_ORIGINS`에 번들 출처(`file://`은 `null`, 로컬 서버는 그 주소)를 더하는 것은 backend 항목이다. 단독 모드로만 번들하면(`VITE_API_BASE` 없음) 서버 설정이 필요 없다. 권장: 1차는 단독 모드 번들 + 원격 주소 앱을 따로 두고 비교한다.

## 범위
- 하는 것
  - `vite.config.ts`: `base`를 환경 변수(`VITE_BASE`, 기본 `/`)로 — 번들은 `./`. `index.html`·`public/` 참조(`/logo.png`, `/flags/*.svg`)가 상대 경로로도 되는지 확인하고, 안 되면 `frontend/` 항목으로 넘긴다(`import.meta.env.BASE_URL` 사용)
  - 빌드 스크립트 `npm run build:bundle` → `dist-bundle/`, Flutter `pubspec.yaml`의 `assets`에 포함하는 절차(`app/README.md`)
  - 자산에서 열 때도 `/__host`·뒤로 가기·`openExternal`이 같게 동작하는지 확인
- 하지 않는 것
  - 번들과 원격의 자동 전환(네트워크 있으면 원격, 없으면 번들). 결정 뒤 별도 항목
  - 서버 `CORS_ORIGINS` 변경(backend 항목), 앱 업데이트 없이 웹만 갱신하는 구조(OTA)

## 화면·계약·파일
- 화면: 변경 없음
- 계약: 변경 없음
- 수정: `vite.config.ts`, `package.json`(스크립트), `README.md`("API 연결" 표·"나중에 붙일 자리"), `app/`(자산 등록·로딩)

## 완료 기준
- [ ] `VITE_BASE=./ npm run build:bundle` 결과를 앱 자산으로 넣고 비행기 모드에서 앱을 열면 S-01부터 접수 창구 화면까지 전부 뜬다(네트워크 요청 0건)
- [ ] 같은 자산으로 `/__host`가 "호스트: 있음", `onBack()`·`openExternal`이 03과 같게 동작한다
- [ ] 로고·국기 그림이 보인다(상대 경로 확인)
- [ ] 원격 주소 방식(03)의 빌드·동작이 바뀌지 않았다(`npm run build`의 `dist/`는 `base: /`)

## 결과

## 메모
- 번들은 앱 심사를 거쳐야 갱신된다. 발표 전 마지막 수정이 많을 때는 원격 주소 방식이 유리하다. 둘 다 유지하는 이유다
- `sessionStorage`·`localStorage`는 `file://` 출처에서도 된다(WebView). iOS는 `file://` 출처 간 격리가 느슨하므로 다른 로컬 HTML을 같은 WebView에 열지 않는다
