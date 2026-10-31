# 21. 근로자 Google 로그인(ID 토큰 검증·세션)

상태: 대기
의존: 17 (세션 쿠키·저장소 표 구조를 그대로 따른다), 07 (SQLite 저장소)

## 목표
근로자 화면의 Google 로그인은 지금 서버를 부르지 않는 데모 버튼이고, 누구나 "비회원으로 계속"으로 들어온다. 사용자가 비회원을 없애고 Google 로그인을 실제로 붙이기로 했다(2026-10-31). 프론트가 Google Identity Services로 받은 ID 토큰을 서버가 검증하고, 맞으면 근로자 세션 쿠키를 준다. 서버는 Google 계정을 가리키는 해시와 세션만 저장하고 이름·이메일·사진은 저장하지 않는다. 프론트 몫은 `frontend` 28이다.

## 결정이 필요한 것

1. **서버가 저장하는 것.** → **권장대로 결정(2026-10-31).** 권장: Google `sub`(계정 고유 번호)에서 만든 계정 키와 세션 해시만 저장한다. 이름·이메일·사진·`email_verified`는 검증에만 쓰고 저장하지 않으며 응답에도 넣지 않는다. 근로자 표(계정 목록)는 두지 않고 세션 표 하나만 둔다. 프로필·리포트는 지금처럼 기기(localStorage)에 둔다(frontend 28)
2. **계정 키.** → **권장대로 결정(2026-10-31).** 권장: `sha256("fornav-worker:" + sub)`의 앞 32자(16진수). 응답의 `account`로 프론트에 주고, 프론트는 이 값으로 기기 저장소를 계정마다 나눈다(같은 휴대폰에서 다른 계정으로 들어오면 앞 사람 프로필·리포트가 보이지 않게). `sub` 원문은 저장·응답·로그에 남기지 않는다
3. **ID 토큰 검증 라이브러리.** → **권장대로 결정(2026-10-31).** 권장: **`google-auth`**(Google 공식, `id_token.verify_oauth2_token`이 서명·`iss`·`aud`·`exp`를 함께 확인한다). 공개 키를 받는 전송 계층으로 `requests`가 함께 들어온다. 다른 안: `PyJWT[crypto]` + `PyJWKClient`(키 캐시가 있다. 대신 `iss` 두 값·`aud` 확인을 직접 짠다). 외부 호출이므로 `app/mail.py`처럼 `TokenVerifier` 프로토콜 뒤에 두고 테스트는 가짜로 바꾼다
4. **기본값.** → **권장대로 결정(2026-10-31).** 권장: `WORKER_AUTH` 기본 `off`. 지금 API·테스트·동기화 테스트가 그대로이고 프론트는 데모 로그인으로 동작한다. 맥미니 `backend/.env`에서만 `google`로 켠다
5. **세션 저장소.** → **권장대로 결정(2026-10-31).** 권장: 센터 로그인과 같이 `WORKER_AUTH=google`이면 `DB_PATH`가 있어야 한다(서버를 다시 띄워도 근로자가 다시 로그인하지 않게). 세션 길이는 `WORKER_SESSION_DAYS`(기본 30), 쓸 때마다 늘리지 않는다
6. **로그인으로 막는 경로.** → **권장대로 결정(2026-10-31).** 권장: `WORKER_AUTH=google`이면 `POST /api/center/cases`(센터 요청)만 근로자 세션을 요구한다(PRD "센터 요청은 회원만"을 서버가 확인). 증상 추출·판정·제도 경로·접수 도우미·리포트(`/api/extract`, `/api/triage`, `/api/route`, `/api/visit-helper`, `/api/report/*`)는 막지 않는다. 응급 판정이 로그인에 묶이면 안 되고, 이 경로들은 실패하면 프론트가 브라우저 함수로 대체하므로 막아도 보호 효과가 없다. LLM 비용은 backend 20의 호출 제한이 맡는다

## 범위
- 하는 것
  - 설정(`app/settings.py`): `WORKER_AUTH`(`off` | `google`, 기본 `off`), `GOOGLE_CLIENT_ID`(웹 클라이언트 ID, 토큰의 `aud`와 비교), `WORKER_SESSION_DAYS`(기본 30). 쿠키 `Secure`는 센터와 같은 `CENTER_COOKIE_SECURE`를 쓴다(로컬 http 개발에서 둘을 따로 끄는 일이 없게). `google`인데 `DB_PATH`·`GOOGLE_CLIENT_ID`가 없으면 시작 시 거절한다
  - 검증(`app/google_id.py`, 새 모듈): `TokenVerifier` 프로토콜과 `GoogleVerifier`. 서명, `iss`(`accounts.google.com` 또는 `https://accounts.google.com`), `aud == GOOGLE_CLIENT_ID`, `exp`를 확인하고 `sub`만 돌려준다. 실패 이유는 나누지 않고 하나의 예외로 올린다
  - 세션(`app/auth.py`에 근로자 함수 추가): `secrets.token_urlsafe(32)` 쿠키, `sha256` 해시만 저장. 표 `worker_sessions`(token_hash, account, created_at, expires_at). 쿠키 `fornav_worker`, `HttpOnly`, `SameSite=Lax`, `Path=/`, `Max-Age`=세션 길이, `CENTER_COOKIE_SECURE`면 `Secure`
  - 경로(`app/routers/auth.py`에 `/auth/worker/*` 추가)와 `require_worker` 의존성. `POST /api/center/cases`에 의존성 한 줄
  - `reset()`(데모 초기화)은 근로자 세션을 지우지 않는다
  - 로그: ID 토큰·`sub`·계정 키·세션 토큰·쿠키 값을 남기지 않는다. 검증 실패는 `request_id`만 남긴다
  - `README.md`: API 표, 요청·응답 예시, 설정 표, `.env.example`, "맥미니 배포"에 Google 클라이언트 ID 안내. `CLAUDE.md`·`README.md`의 "서버는 회원 정보를 저장하지 않는다"를 "근로자는 로그인 계정 키와 세션만 저장한다(이름·이메일·프로필·리포트는 저장하지 않는다)"로 고친다
- 하지 않는 것
  - 근로자 프로필·리포트를 서버에 저장하기, 기기 사이 동기화
  - 센터 사례에 계정 키를 남기기(누가 보냈는지 센터가 아는 것). 필요하면 따로 항목으로 쓴다
  - 근로자 채팅·통화(`role=worker`) 확인 방식 변경. 지금처럼 사례별 토큰이다
  - Google 외 로그인(Apple·카카오), Google 액세스 토큰·스코프(ID 토큰만 쓴다)
  - Flutter 앱 네이티브 로그인. 앱은 다른 `aud`(Android·iOS 클라이언트 ID)의 토큰을 보낼 수 있으므로 `GOOGLE_CLIENT_ID`를 여러 값으로 받는 일은 app-front 쪽 항목에서 함께 정한다
  - 다른 출처 프론트에서 쿠키 보내기(17과 같다)

## API·파일

### 경로
| 경로 | 요청 | 응답 | 비고 |
|---|---|---|---|
| `GET /api/auth/worker/me` | — | `{ required, account }` | `required`는 `WORKER_AUTH=google`인지. 세션이 없으면 `account: null`(401이 아니다) |
| `POST /api/auth/worker/google` | `{ credential }` | `{ required, account }` + `Set-Cookie` | `credential`은 Google Identity Services 콜백의 ID 토큰(JWT). 검증 실패는 `401` |
| `POST /api/auth/worker/logout` | — | `204` + 쿠키 지우기 | 세션이 없어도 204 |

`WORKER_AUTH=off`이면 `/api/auth/worker/me`는 `{ "required": false, "account": null }`이고 `google`은 `404`다. `POST /api/center/cases`는 지금처럼 쿠키 없이 201이다.

`WORKER_AUTH=google`이면 `POST /api/center/cases`는 근로자 세션이 없을 때 `401 UNAUTHORIZED`다.

```jsonc
// POST /api/auth/worker/google
{ "credential": "eyJhbGciOiJSUzI1NiIs…" }
// 200
{ "required": true, "account": "3f9c0a…(32자)" }
// 401
{ "error": { "code": "UNAUTHORIZED", "message": "Google 로그인을 확인하지 못했다", "requestId": "…" } }
```

### 파일
- 추가: `app/google_id.py`(`TokenVerifier`, `GoogleVerifier`), `tests/test_worker_auth.py`
  - 새 모듈을 두는 이유: Google 공개 키를 받는 외부 호출이라 `mail.py`처럼 가짜로 바꿔 끼울 자리가 필요하다. 테스트는 `tests/fakes.py`의 `FakeVerifier`(정해 둔 토큰 → `sub`)를 쓴다
- 수정: `app/settings.py`, `app/auth.py`, `app/store.py`·`app/store_sqlite.py`(`worker_sessions`), `app/routers/auth.py`, `app/routers/center.py`(`create_case`에 `require_worker`), `app/main.py`(검증기), `app/schemas.py`(`WorkerGoogleIn`, `WorkerMe`), `tests/fakes.py`, `tests/test_settings.py`, `tests/test_store.py`, `pyproject.toml`·`uv.lock`(`google-auth`, `requests`), `.env.example`, `README.md`, `CLAUDE.md`

## 완료 기준
- [ ] `uv run ruff check . && uv run ruff format --check .` 통과, `uv run pytest` 통과. `WORKER_AUTH`를 주지 않은 기존 테스트는 그대로 통과한다
- [ ] `test_worker_auth.py`가 메모리·SQLite 두 저장소에서 다음을 확인한다(`FakeVerifier`, `clock` 고정)
  - 맞는 토큰 → 200, `account`는 32자 16진수이고 같은 `sub`이면 늘 같은 값, 다른 `sub`이면 다른 값. 쿠키 `fornav_worker`에 `HttpOnly`·`SameSite=Lax`·`Max-Age`가 있고 `CENTER_COOKIE_SECURE`면 `Secure`
  - 검증 실패 토큰 → 401, 쿠키 없음
  - `/api/auth/worker/me` → 쿠키가 있으면 그 `account`, 없거나 30일 지났으면 `null`
  - 로그아웃 → 204, 같은 쿠키로 `/me` → `account: null`
  - `WORKER_AUTH=google`: 쿠키 없이 `POST /api/center/cases` → 401, 쿠키가 있으면 201. `/api/extract`·`/api/triage`·`/api/route`·`/api/visit-helper`·`/api/report/*`는 쿠키 없이 지금과 같은 응답
  - 센터 쿠키(`fornav_center`)로는 근로자 경로가 열리지 않고, 근로자 쿠키로는 센터 경로가 열리지 않는다
- [ ] `GoogleVerifier`가 `aud`가 다른 토큰, `iss`가 다른 토큰, 만료된 토큰을 거절한다(서명 키를 테스트에서 만들어 넣는 단위 테스트, 네트워크 없음)
- [ ] `WORKER_AUTH=off`: `/me` → `{ required: false, account: null }`, `google` → 404, 센터 요청은 쿠키 없이 201
- [ ] 설정: `google`인데 `DB_PATH` 없음, `GOOGLE_CLIENT_ID` 없음이면 서버가 뜨지 않는다
- [ ] 접근 로그·앱 로그에 ID 토큰·`sub`·계정 키·세션 토큰이 없다(`caplog`)
- [ ] 로컬 실제 확인: 사용자가 만든 웹 클라이언트 ID로 `WORKER_AUTH=google CENTER_COOKIE_SECURE=false DB_PATH=<임시 파일>` 서버를 띄우고, frontend 28 화면에서 실제 Google 계정으로 로그인해 쿠키가 생기고 센터 요청이 201인 것을 `## 결과`에 적는다

## 결과
(구현 후 작성)

## 메모
- 사용자 준비(구현 전): Google Cloud 콘솔에서 OAuth 동의 화면(외부, 테스트 중이면 테스트 사용자 등록)과 **웹 애플리케이션** OAuth 클라이언트 ID를 만든다. 승인된 JavaScript 원본에 `http://localhost`, `http://localhost:5180`, 배포 출처(`https://app.for-nav.com`, `https://www.for-nav.com`, Funnel 주소를 쓰면 그 주소)를 넣는다. 리디렉션 URI는 쓰지 않는다(팝업·콜백 방식). 클라이언트 ID는 비밀이 아니고 클라이언트 비밀번호는 쓰지 않는다
- 같은 클라이언트 ID를 프론트 빌드(`VITE_GOOGLE_CLIENT_ID`)와 서버(`GOOGLE_CLIENT_ID`)에 넣는다
- `GoogleVerifier`는 요청마다 Google 공개 키를 받을 수 있다. 로그인 한 번에 한 번이라 지금은 그대로 두고, 느리면 키 캐시를 따로 한다
- `GET /api/auth/me`(센터)와 응답을 합치지 않고 경로를 나눈 이유: 센터 화면(frontend 27)의 `AuthMe` 검사와 쿠키가 서로 섞이지 않게 하기 위해서다
- Flutter WebView 안에서는 Google이 웹 로그인을 막는다(`disallowed_useragent`). 앱은 네이티브 로그인으로 받은 ID 토큰을 같은 `POST /api/auth/worker/google`로 보내게 될 것이고, 그때 `aud`가 Android·iOS 클라이언트 ID일 수 있다(위 "하지 않는 것")
- 공개 주소(backend 19 "공개 주소 규칙")에서 "근로자는 비회원도 쓴다"는 문장은 이 항목 뒤에 "근로자 판정·안내 경로는 로그인 없이 열린다(응급 판정 때문)"로 읽는다
