# app-front 작업 규칙

울산 외국인 의료 내비게이터의 근로자 화면을 **Flutter 앱의 WebView 안에서** 돌리는 웹앱(Vite + React + TypeScript)을 만드는 폴더다. 화면·규칙·문구는 `frontend/`의 근로자 화면과 같고, 이 폴더가 더하는 것은 네이티브 호스트와의 다리(bridge)와 WebView 전용 설정이다.
무엇을 만드는지(범위, 호스트 계약, API·상태 정책, 결정 사항)는 `README.md`가 정하고, 어떻게 그리는지는 `design.md`(= `frontend/design.md` + WebView 덧붙임)가 정하고, **무엇을 언제 만드는지는 `backlog/` 문서가 정한다.** 이 문서는 그 셋을 코드로 옮길 때 지키는 규칙이다.

브랜치·커밋·PR 규칙은 루트 `CLAUDE.md`를 따른다. 브랜치 영역은 `app-front/`이다.

## 읽는 순서

1. 루트 `CLAUDE.md`
2. `app-front/README.md` — 범위, 호스트 계약(감지·메시지·외부 링크·뒤로 가기·안전 영역·호스트가 없을 때), API 연결(출처), 상태의 경계, Flutter 쪽에서 할 일, 결정이 필요한 것. 계약에 없는 메시지 `type`을 새로 보내지 않고, 호스트가 있어야만 되는 동작을 만들지 않는다.
3. `app-front/design.md` — 화면을 그릴 때. 토큰·컴포넌트는 `frontend/design.md`이고, 여기에는 WebView에서 더 지키는 것만 있다.
4. `app-front/backlog/` — 작업 항목. 사용자가 지정한 항목 하나만 구현한다.
5. 근로자 화면·규칙·API 정책을 볼 때는 `frontend/README.md`("화면 구성", "API 연결", "상태의 경계")와 `frontend/CLAUDE.md`. 이 앱은 그 정책을 다시 정하지 않고 그대로 따른다.
6. 호스트(Flutter) 쪽을 고칠 때는 `README.md` "Flutter 쪽에서 할 일"과 `../app/CLAUDE.md`. 계약이 바뀌면 코드보다 `README.md`를 먼저 고친다.

## backlog 문서로 일한다

- `backlog/` 안의 문서 하나가 작업 항목 하나다. 파일 이름은 `NN-short-name.md`(예: `01-scaffold-bridge.md`)로 쓰고, 번호가 작은 것이 먼저다.
- 사용자가 항목을 말하지 않으면 미완료 항목 중 번호가 가장 작은 것을 고르고, 시작 전에 어느 항목을 하는지 말한다. `의존:`에 적힌 항목이 완료되지 않았으면 시작하지 않고 사용자에게 알린다. 다른 폴더의 항목에 기대면 `frontend 02`, `backend 08`처럼 폴더 이름을 붙여 적는다.
- `backlog/`에 맞는 항목이 없으면 구현을 시작하지 않는다. 아래를 근거로 아래 형식의 문서를 먼저 쓰고, 사용자가 확인한 뒤 구현한다.
  - `README.md`의 "나중에 붙일 자리", "결정이 필요한 것", "확인이 필요한 값", "실서비스와 다른 점"
  - `frontend/backlog/`·`backend/backlog/`의 `## 메모`에서 앱 몫으로 넘긴 일(예: 통화 자막의 네이티브 받아쓰기, 푸시)
- 항목에 `## 결정이 필요한 것`이 있으면 권장안을 적고 사용자 확인을 받은 뒤 구현한다. 결정 결과와 날짜를 그 자리에 남긴다(`frontend/backlog/25-consult-chat.md` 형식).
- **지정된 항목의 범위만 구현한다.** 하다가 발견한 다른 일은 새 backlog 문서로 만들거나 기존 문서의 `## 메모`에 적고, 지금 작업에 섞지 않는다.
- 문서의 `## 완료 기준`을 그대로 검증한다. 기준이 모호하거나 검증할 방법이 없으면 구현 전에 사용자에게 묻는다. 호스트가 있어야만 확인되는 기준(외부 링크·뒤로 가기)은 Flutter 앱이 생기기 전까지 "브라우저에서 호스트 없음 동작 확인"과 "`/__host` 화면에서 메시지 확인"으로 대신하고, 그렇게 했다고 `## 결과`에 적는다.
- 끝나면 그 문서의 `## 결과`에 실행한 명령과 결과, 바뀐 계약(메시지 `type`·필드), 확인한 화면·기기, 내린 결정과 이유를 적고 `상태:`를 바꾼다. 결과 기록은 코드와 같은 PR에 넣는다.
- backlog 문서와 `README.md`가 어긋나면 멈추고 사용자에게 묻는다. 임의로 한쪽을 고치지 않는다.

### backlog 문서 형식

```markdown
# NN. <제목>

상태: 대기 | 진행 중 | 완료 | 보류
의존: <먼저 끝나야 하는 항목 번호, 없으면 "없음">

## 목표
무엇을 왜 만드는지 두세 문장

## 결정이 필요한 것
(있을 때만) 번호를 붙여 선택지와 권장안을 적고, 결정되면 결과와 날짜를 남긴다

## 범위
- 하는 것
- 하지 않는 것

## 화면·계약·파일
바뀌는 화면(경로), 호스트 계약(메시지 type·필드), 만들거나 고치는 파일

## 완료 기준
- [ ] 검증할 수 있는 문장으로 쓴다 (예: `npm run build` 통과, 브라우저(호스트 없음)에서 `/__host`가 "브라우저" 표시, 폰 WebView에서 `tel:119`가 전화 앱을 연다)

## 결과
(구현 후 작성) 실행 명령 → 결과, 바뀐 계약, 확인한 환경, 결정 사항, 남은 문제

## 메모
```

## 스택과 폴더

- Vite + React 19 + react-router + TypeScript(strict). **버전은 `frontend/package.json`과 같은 값으로 고정한다**(범위 기호 없이). `frontend/` 코드를 공유 import하게 되면(backlog 02) React가 둘이 되면 안 되기 때문이다. 올릴 때는 두 폴더를 같은 PR에서 올리거나, `frontend/`를 먼저 올린다. `package-lock.json`을 커밋한다. 의존성을 더할 때는 backlog 문서에 이유를 적는다. WebView 전용 라이브러리는 쓰지 않는다. 다리는 `window` API만으로 충분하다.
- 검사는 `npm run build`(타입 검사 + 빌드) 하나다. 린터·포매터·테스트 러너는 아직 없다. 들이는 것은 backlog 문서 하나로 따로 한다.
- 폴더 구조는 `README.md`의 "폴더 구조"를 따른다. 새 폴더가 필요하면 backlog 문서에 이유를 적고 `README.md`의 구조를 함께 고친다.
- **호스트와 닿는 코드는 `src/bridge/`에만 있다.** `window.ForNav`, `window.flutter_inappwebview`, `window.fornav`를 화면·상태 코드에서 직접 만지지 않는다. 화면은 `useHost()`가 주는 값(`present`, `platform`, `locale`, `insets`)과 함수만 쓴다. 다리의 감지·전송 방식이 바뀌어도 화면은 바뀌지 않아야 한다.
- 화면 코드는 `frontend/CLAUDE.md`의 규칙을 그대로 따른다. 로직은 `domain/`, 저장소는 `state/storage.ts` 래퍼, 네트워크는 `api/`, 문구는 `i18n/` 키. 이 폴더에 규칙·템플릿·문구를 새로 쓰지 않는다.
- 개발 서버 포트는 5181이다(`frontend/`가 5180). 백엔드 CORS 기본값은 5180뿐이지만 둘 다 Vite 프록시로 `/api`를 부르므로 CORS 설정이 필요 없다.

## 설계에서 바꾸지 않는 것

- **호스트가 없어도 똑같이 동작한다.** 보통 브라우저에서 열면 링크·전화·뒤로 가기·언어는 브라우저 기본 동작이고, 화면·문구는 호스트가 있을 때와 같다. 호스트 감지는 `window`의 전송 통로 유무로만 하고 사용자 에이전트로 하지 않는다. 호스트가 있을 때만 보이는 화면·문구를 만들지 않는다.
- **응급은 다리도 네트워크도 기다리지 않는다.** 하단 119 띠와 응급 화면의 전화 버튼은 호스트 초기화·API 응답과 관계없이 보인다. `tel:` 가로채기는 호스트가 `init`을 보낸 뒤에만 한다. 그 전에는 WebView의 기본 `tel:` 처리에 맡긴다.
- **계약은 `README.md`가 먼저다.** 메시지 `type`·필드를 더하거나 바꾸려면 `README.md` "호스트 계약"을 같은 PR에서 먼저 고치고, 모르는 `type`은 양쪽 모두 무시한다. `protocol` 번호는 기존 메시지의 의미가 바뀔 때만 올린다.
- **다리로 개인정보를 보내지 않는다.** 증상·자유 입력·연락처·리포트·토큰은 다리를 타지 않는다. 다리 메시지 본문(특히 `openExternal.url`)을 `console`에 찍지 않는다. 오류 기록은 `type`만 남긴다.
- **`frontend/`의 정책을 다시 정하지 않는다.** API 두 모드, 경로별 대체 정책, 시간 제한, 상태의 경계, 진입 순서 가드, 진단 표현 금지, 제도 안내 문구, 동의 3개 분리, 센터 통계 집계만 — 모두 `frontend/README.md`·`frontend/CLAUDE.md` 그대로다. 앱이라서 달라야 할 것이 생기면 이 문서가 아니라 사용자에게 묻는다.
- **`frontend/src/domain/`이 원본이다.** 규칙·템플릿·어휘·열거값을 이 폴더에 새로 쓰거나 고치지 않는다. 공유 import라면 그대로 쓰고, 복사라면 `frontend/`를 고친 뒤 다시 복사한다(backlog 02가 방법을 정한다). 백엔드 동기화 테스트(`parity.json`)의 입력은 `frontend/`에서만 만든다.
- **센터 화면을 넣지 않는다.** `/center*` 경로·센터 API 폴링·센터 로그인은 이 앱에 없다. 알 수 없는 경로는 `/`로 보낸다.
- **같은 빌드가 어디서나 돈다.** 호스트 유무, 출처(개발 서버·같은 출처·다른 출처·번들)에 따라 코드를 나누지 않는다. 다른 것은 환경 변수(`VITE_API_BASE`, 번들용 `base`)뿐이다.
- 줌을 막지 않는다(`user-scalable=no`를 쓰지 않는다). 글을 크게 보아야 하는 근로자가 있다. 두 번 탭 지연은 `touch-action: manipulation`으로 없앤다.

## frontend·backend·Flutter와의 경계

- `frontend/` 코드는 이 폴더의 작업에서 고치지 않는다. 화면·규칙을 바꿔야 하면 `frontend/` 브랜치로 따로 한다. 예외는 backlog 02가 공유 import를 택했을 때 `frontend/CLAUDE.md` "경계" 절에 "app-front가 이 경로들을 import한다"는 한 줄을 더하는 것이다(그 뒤로 `frontend/` 작업이 파일을 옮길 때 이 앱 빌드를 함께 돌리게 하기 위해서).
- `backend/` 코드는 고치지 않는다. 같은 출처 서빙 경로(`/app/`)나 `CORS_ORIGINS` 기본값처럼 서버 쪽이 필요하면 backlog 문서 `## 메모`에 적고 사용자에게 알린다.
- Flutter 프로젝트는 이 폴더 밖의 `../app/`이다(backlog 03). 이 폴더는 호스트가 지켜야 할 계약(`README.md`)만 둔다. 계약 변경은 웹(`src/bridge/`)·호스트(`app/lib/`)를 같은 PR에서 고친다.
- `.github/workflows/ci.yml`에 이 폴더의 잡을 더하는 것은 `chore/` 영역의 별도 작업이다. 그 전까지는 PR 본문에 `npm run build` 결과를 적는다.

## 검사와 커밋

```sh
cd app-front
npm ci
npm run build
```

브라우저에서 바뀐 경로를 직접 확인한다. 휴대폰 폭(360px)으로 보고, 호스트 없음 동작(링크·전화가 브라우저 기본대로 열리는지, `/__host`가 "브라우저"로 보이는지)을 확인한다. 호스트가 있어야 하는 동작은 Flutter 앱(`../app/`, 실행은 `app/README.md`)에서 확인한다. 근로자 화면이 생기면(backlog 02) `frontend/CLAUDE.md`의 확인 방법(언어 여러 개, 베트남어로 넘침 확인)을 그대로 따른다.

```sh
npm run dev                                   # 단독 모드, http://localhost:5181
VITE_API_BASE=/api npm run dev                # API 모드 (다른 터미널: cd backend && uv run fastapi dev app/main.py)
```

- 커밋 메시지의 `테스트:` 줄에 `npm run build` 결과와 브라우저에서 확인한 경로·환경(호스트 없음 / Android WebView / iOS WebView)을 적는다. 문서만 바꿨으면 그렇게 적는다.
- `frontend/`와 같은 버전의 의존성을 쓰는지 올릴 때마다 확인한다(`diff <(jq .dependencies frontend/package.json) <(jq .dependencies app-front/package.json)`).
