# 17. 센터 직원 로그인(이메일 코드)

상태: 진행 중(맥미니 실제 메일 확인 남음)
의존: 07 (SQLite 저장소), 14 (상담 채팅 WebSocket)

## 목표
지금 센터 경로(`/api/center/*`의 목록·상세·상태 변경·초기화·통계, 채팅·통화의 `role=center`)는 로그인 없이 열린다. 맥미니 배포(13)로 `www.for-nav.com`에 공개되면서 Cloudflare Access로 임시로 막았지만, 로그인 화면이 Cloudflare 것이라 앱과 통일되지 않고 Cloudflare 앞단만 막아 맥미니에 직접 붙는 접속은 막지 못한다. 센터 직원 이메일을 서버 DB에 두고, 이메일로 보낸 6자리 코드로 로그인하게 해서 서버가 센터 경로마다 직접 확인한다. 비밀번호는 두지 않는다.

## 결정이 필요한 것

1. **메일 발송 서비스.** → **권장대로 결정(2026-10-31).** 권장: **Resend**(HTTP API 하나, 무료 하루 100통). `for-nav.com`이 Cloudflare DNS에 있어 발신 도메인 인증(SPF·DKIM 레코드)을 바로 넣을 수 있다. SDK 없이 `httpx`로 부른다(`fastapi[standard]`에 이미 들어 있어 새 의존성이 없다). 다른 후보: AWS SES(설정이 길다), Gmail SMTP(앱 비밀번호, 발신 주소가 개인 메일).
2. **로컬 개발에서 코드를 받는 방법.** → **권장대로 결정(2026-10-31).** 권장: `MAIL_PROVIDER=console`이면 코드를 메일 대신 서버 표준 출력에 한 줄 찍는다(로거가 아니라 `print`, 접근 로그·파일 로그에는 남지 않는다). 운영에서 실수로 켜지지 않도록 `CENTER_COOKIE_SECURE=false`(로컬 http 개발)일 때만 허용하고, 아니면 서버가 뜨지 않는다. 다른 안: 로컬에서도 Resend 키로 진짜 메일을 받는다.
3. **기본값.** → **권장대로 결정(2026-10-31).** 권장: `CENTER_AUTH` 기본 `off`(지금 동작 그대로, 기존 테스트·동기화 테스트·단독 개발이 바뀌지 않는다). 맥미니 `backend/.env`에서만 `email`로 켠다.
4. **직원 등록 방법.** → **권장대로 결정(2026-10-31).** 권장: 맥미니에서 `uv run python scripts/staff.py add <이메일>`로 SQLite 표에 넣고 빼는 명령줄 도구. 관리 화면(직원 추가·삭제 UI)은 이 항목에서 만들지 않는다.
5. **세션 길이.** → **권장대로 결정(2026-10-31).** 권장: 30일 고정(`CENTER_SESSION_DAYS`). 쓸 때마다 늘리지 않는다. 로그아웃하면 바로 끝난다.

## 범위
- 하는 것
  - 설정(`app/settings.py`): `CENTER_AUTH`(`off` | `email`, 기본 `off`), `MAIL_PROVIDER`(`resend` | `console`), `MAIL_API_KEY`(repr에서 뺀다), `MAIL_FROM`(예: `for-nav 센터 <no-reply@for-nav.com>`), `CENTER_SESSION_DAYS`(기본 30), `CENTER_COOKIE_SECURE`(기본 `true`). `email`이면 `DB_PATH`가 있어야 하고, `resend`면 `MAIL_API_KEY`·`MAIL_FROM`이 있어야 한다. 아니면 시작 시 거절한다
  - 직원 표: SQLite `center_staff`(email PRIMARY KEY, added_at). 이메일은 앞뒤 공백을 지우고 소문자로 맞춰 저장·비교한다
  - 로그인 코드: `secrets.randbelow(10**6)`로 6자리를 만들고 `sha256` 해시만 저장한다(`auth_codes`: email, code_hash, expires_at, attempts, sent_at). 10분 유효, 틀리면 `attempts`를 올리고 5번 틀리면 지운다. 새 코드를 보내면 이전 코드는 무효다
  - 세션: `secrets.token_urlsafe(32)`를 쿠키로 주고 `sha256` 해시만 저장한다(`center_sessions`: token_hash, email, created_at, expires_at). 쿠키 `fornav_center`, `HttpOnly`, `SameSite=Lax`, `Path=/`, `Max-Age`=세션 길이, `CENTER_COOKIE_SECURE`면 `Secure`
  - 보내기 제한: 같은 이메일에 60초 안에 다시 보내지 않고, 1시간에 5통까지. 서버 전체로 10분에 30통까지(메일 무료 한도 보호). 넘으면 429
  - 등록되지 않은 이메일도 `POST /api/auth/code`는 같은 202를 돌려준다(직원 이메일이 맞는지 떠보지 못하게). 메일만 보내지 않는다
  - 센터 경로 보호(`CENTER_AUTH=email`일 때만): `GET /api/center/cases`, `GET`·`PATCH /api/center/cases/{id}`, `POST /api/center/reset`, `GET /api/center/stats`는 세션이 없거나 만료되면 401. **`POST /api/center/cases`(근로자 전송)는 보호하지 않는다.** 라우터에는 의존성(`Depends(require_staff)`) 한 줄만 더한다
  - 채팅·통화 `role=center`: 핸드셰이크 쿠키로 세션을 확인하고, 없으면 accept 뒤 `4401`로 닫는다. `Origin` 헤더가 요청 호스트나 `CORS_ORIGINS`와 다르면 `4403`(다른 사이트에서 직원 쿠키로 붙는 것을 막는다). `role=worker`는 지금처럼 토큰으로 확인하고 쿠키를 보지 않는다
  - 오류 코드: `errors.py`의 `CODES`에 401 `UNAUTHORIZED`, 429 `RATE_LIMITED`를 더한다
  - 메일 본문(한국어, 텍스트): 제목 `for-nav 센터 로그인 코드`, 본문 `로그인 코드: 123456` + `10분 동안 유효합니다. 요청하지 않았다면 이 메일을 무시하세요.` 링크는 넣지 않는다
  - 직원 관리 명령줄: `scripts/staff.py add|remove|list <이메일>`. `DB_PATH`의 SQLite 파일을 연다. `remove`는 그 직원의 세션도 지운다
  - 로그: 이메일·코드·세션 토큰·쿠키 값을 남기지 않는다. 메일 발송 실패는 공급자 HTTP 상태와 request id만 남긴다
  - `reset()`(데모 초기화)은 직원·코드·세션을 지우지 않는다
  - `README.md`: API 표, 요청·응답 예시, 오류 코드, 설정 표, "맥미니 배포"의 `.env`·직원 등록·Resend DNS 안내, "나중에 붙일 자리"의 "상담 채팅 센터 인증" 행을 "붙임(backlog 17)"로 바꾼다. `.env.example`에 새 변수
- 하지 않는 것
  - 비밀번호, 소셜 로그인, 2단계 인증
  - 직원 관리 화면, 직원별 권한(관리자·상담원 구분), 담당자 지정, 채팅·상태 변경에 처리한 직원 남기기
  - 근로자 로그인(근로자 세션은 지금처럼 브라우저에 둔다)
  - 다른 출처(예: Vercel 프론트)에서 쿠키를 보내는 교차 출처 로그인. 프론트는 같은 출처(`STATIC_DIR`, Vite 프록시)에서만 붙는다
  - 프론트 코드. 로그인 화면은 `frontend/` backlog 27로 따로 한다
  - Cloudflare 설정(Access 앱 삭제, WAF 규칙). 배포 뒤 사용자가 대시보드에서 한다

## API·파일

### 경로
| 경로 | 요청 | 응답 | 비고 |
|---|---|---|---|
| `GET /api/auth/me` | — | `{ required, email }` | `required`는 `CENTER_AUTH=email`인지. 세션이 없으면 `email: null`(401이 아니다) |
| `POST /api/auth/code` | `{ email }` | `202` | 등록 여부와 관계없이 같은 응답. 제한을 넘으면 `429` |
| `POST /api/auth/verify` | `{ email, code }` | `{ required, email }` + `Set-Cookie` | 코드가 틀리거나 만료·없음이면 `401`(이유를 나누지 않는다) |
| `POST /api/auth/logout` | — | `204` + 쿠키 지우기 | 세션이 없어도 204 |

`CENTER_AUTH=off`이면 `/api/auth/me`는 `{ "required": false, "email": null }`이고, `code`·`verify`는 `404`다. 센터 경로는 지금처럼 열린다.

```jsonc
// POST /api/auth/verify
{ "email": "staff@example.org", "code": "042917" }
// 200
{ "required": true, "email": "staff@example.org" }
// 401
{ "error": { "code": "UNAUTHORIZED", "message": "코드가 맞지 않거나 만료되었다", "requestId": "…" } }
```

### 채팅·통화 닫힘 코드(더하는 것)
| 닫힘 코드 | 언제 |
|---|---|
| `4401` | `role=center`인데 센터 세션이 없거나 만료되었다 |
| `4403` | (기존) + `role=center`인데 `Origin`이 허용 밖이다 |

### 파일
- 추가: `app/auth.py`(코드·세션 만들기와 확인, 쿠키 도우미, `require_staff` 의존성, WS 확인), `app/mail.py`(`Mailer` 프로토콜, `ResendMailer`, `ConsoleMailer`), `app/routers/auth.py`, `scripts/staff.py`, `tests/test_auth.py`
  - `app/mail.py`를 새 모듈로 두는 이유: 외부 호출이라 `llm.py`처럼 가짜로 바꿔 끼울 자리가 필요하다. 테스트는 `tests/fakes.py`의 `FakeMailer`로 보낸 메일을 모은다
  - 직원·코드·세션은 `CenterStore` 프로토콜에 더한다(상태는 저장소 하나라는 규칙). 메모리 구현은 테스트용이다(`CENTER_AUTH=email`은 `DB_PATH`가 있어야 켜진다)
- 수정: `app/settings.py`, `app/store.py`, `app/store_sqlite.py`(표 3개), `app/errors.py`, `app/routers/center.py`(의존성, `_chat_denied`에 세션·Origin 확인), `app/main.py`(라우터·메일러), `app/schemas.py`(`AuthCodeIn`, `AuthVerifyIn`, `AuthMe`), `tests/fakes.py`, `tests/test_api.py`, `tests/test_chat.py`, `tests/test_call.py`, `tests/test_store.py`, `.env.example`, `README.md`

## 완료 기준
- [x] `uv run ruff check . && uv run ruff format --check .` 통과, `uv run pytest` 통과. `CENTER_AUTH`를 주지 않은 기존 테스트는 그대로 통과한다
- [x] `test_auth.py`가 메모리·SQLite 두 구현에서 다음을 확인한다(`FakeMailer`, `clock` 고정)
  - 등록되지 않은 이메일 → 202, 메일 0통. 등록된 이메일(대소문자·공백이 달라도) → 202, 6자리 코드 메일 1통
  - 맞는 코드 → 200, 쿠키에 `HttpOnly`·`SameSite=Lax`·`Max-Age`가 있고 `CENTER_COOKIE_SECURE`면 `Secure`. `/api/auth/me` → 그 이메일
  - 틀린 코드 5번 → 맞는 코드도 401. 10분 지난 코드 → 401. 새 코드를 보내면 이전 코드 → 401
  - 60초 안에 다시 요청, 1시간 6번째, 서버 전체 10분 31번째 → 429
  - 로그아웃 → 204, 같은 쿠키로 `/api/auth/me` → `email: null`. 30일 지난 세션 → 센터 경로 401
  - `scripts/staff.py remove` 뒤 그 직원의 쿠키 → 401
- [x] `CENTER_AUTH=email`: 쿠키 없이 센터 읽기·쓰기 5개 경로 → 401, 쿠키가 있으면 지금과 같은 응답. `POST /api/center/cases`는 쿠키 없이 201
- [x] 채팅·통화: `role=center` 쿠키 없음 → `4401`, 쿠키 있음 → 연결, 다른 `Origin` → `4403`. `role=worker`는 토큰으로만 확인한다(지금 테스트 그대로)
- [x] `CENTER_AUTH=off`: `/api/auth/me` → `{ required: false }`, `code`·`verify` → 404, 센터 경로는 쿠키 없이 지금처럼 응답한다
- [x] 설정: `email`인데 `DB_PATH` 없음, `resend`인데 키 없음, `console`인데 `CENTER_COOKIE_SECURE=true`면 서버가 뜨지 않는다(`test_settings`)
- [x] 접근 로그·앱 로그에 이메일·코드·토큰이 없다(`caplog`)
- [ ] 맥미니: Resend 도메인 인증 후 `CENTER_AUTH=email`로 배포하고, 등록한 직원 메일로 코드를 받아 `https://www.for-nav.com`(프론트 27 이후)이나 `curl`로 로그인한 결과를 `## 결과`에 적는다

## 결과

```sh
cd backend
uv run ruff check . && uv run ruff format --check .   # All checks passed, 74 files already formatted
uv run pytest                                          # 3015 passed (이전 2923, 새 테스트 92)
```

- 새 테스트: `test_auth.py` 70개(메모리·SQLite 두 저장소에 같은 경우를 돌린다), `test_store.py` 11개, `test_settings.py` 10개, `test_api.py` 1개. `CENTER_AUTH`를 주지 않은 기존 테스트(동기화 테스트 포함)는 그대로 통과한다
- 로컬 실제 서버 확인(`CENTER_AUTH=email MAIL_PROVIDER=console CENTER_COOKIE_SECURE=false DB_PATH=<임시 파일> uv run fastapi run app/main.py --port 8765`, `scripts/staff.py add demo@example.org`로 등록):
  - `GET /api/auth/me` → `{"required":true,"email":null}`, 쿠키 없이 `GET /api/center/cases` → 401
  - `POST /api/auth/code` → 202, 서버 표준 출력에 `[console mail]`과 6자리 코드. 60초 안에 다시 → 429
  - `POST /api/auth/verify` → `{"required":true,"email":"demo@example.org"}`, 쿠키 `fornav_center`(HttpOnly, Secure 꺼짐)
  - 쿠키로 `GET /api/center/cases` → 200, 쿠키 없이 근로자 `POST /api/center/cases` → 201
  - `POST /api/auth/logout` → 204, 같은 쿠키로 센터 목록 → 401
  - 서버 로그(`app.access` 등)에 이메일·코드가 0번 나온다
- 바뀐 API: `GET /api/auth/me`, `POST /api/auth/code`(202·429), `POST /api/auth/verify`(200·401), `POST /api/auth/logout`(204). `CENTER_AUTH=email`일 때 센터 읽기·쓰기 5개 경로가 401, 채팅·통화 `role=center`가 `4401`(세션 없음)·`4403`(다른 사이트 `Origin`). 오류 코드 `UNAUTHORIZED`(401), `RATE_LIMITED`(429). 기본값 `off`에서는 API가 지금과 같다(`/api/auth/me`만 더해지고 `code`·`verify`는 404)
- 결정
  - `verify` 응답을 문서 초안의 `{ email }` 대신 `/me`와 같은 `{ required, email }`로 했다. 프론트가 한 타입(`AuthMe`)으로 받는다
  - 이메일별 보내기 제한(60초, 1시간 5번)은 등록되지 않은 이메일에도 똑같이 건다. 등록된 이메일만 429가 나면 등록 여부가 드러난다. 서버 전체 제한(10분 30통)은 실제 발송만 센다. 모든 요청을 세면 등록되지 않은 이메일 요청만으로 직원 로그인을 막을 수 있다
  - 메일 발송이 실패해도 202를 준다(실패를 알리면 등록 여부가 드러난다). 로그에는 실패 종류(`HTTP 500` 등)와 request id만 남긴다
  - 코드 요청 기록(`auth_code_requests`)은 제한이 보는 가장 긴 구간(1시간)만큼만 남기고 다음 요청 때 지운다
  - 맞는 코드를 확인했어도 그 사이 직원 목록에서 빠졌으면 세션을 주지 않는다
  - `Origin` 확인은 요청 `Host`와 같거나 `CORS_ORIGINS`에 있으면 통과다. `Origin`이 없으면(브라우저가 아님) 쿠키 확인에만 맡긴다
  - 새 의존성은 없다. Resend는 `fastapi[standard]`에 든 `httpx`로 부른다
- 남은 것: 맥미니에서 Resend 도메인 인증·`.env` 설정·직원 등록 뒤 실제 메일로 로그인(위 완료 기준 마지막 줄). Cloudflare 터널 뒤에서 `Host`가 `www.for-nav.com`으로 들어와 채팅 `Origin` 확인을 통과하는지도 그때 본다

## 메모
- "서버는 회원 정보를 저장하지 않는다"(`CLAUDE.md`)는 근로자 이야기다. 이 항목이 저장하는 것은 센터 직원 이메일과 세션 해시뿐이고, 근로자 정보는 지금처럼 브라우저에 둔다
- 배포 뒤 할 일(사용자): Cloudflare Access 애플리케이션은 이 항목 전에 지웠다(실제 데이터가 없어서). WAF 규칙(`app.`·루트에서 센터 경로 차단)은 이중 장치로 남겨 둔다. `app.`의 `/api/auth/*`는 막지 않아도 된다(로그인은 `www.`에서 한다)
- 맥미니 `backend/.env`에 `CENTER_AUTH=email`, `DB_PATH`, `MAIL_PROVIDER=resend`, `MAIL_API_KEY`, `MAIL_FROM`을 넣는다. `.env`는 커밋하지 않는다
- Cloudflare 터널 뒤에서는 클라이언트 IP가 모두 `127.0.0.1`로 보여 IP별 제한을 두지 않았다. 필요하면 Cloudflare 대시보드의 Rate limiting 규칙으로 `/api/auth/code`를 막는다
- 담당자 지정·처리 직원 기록·직원 관리 화면은 이 항목 뒤에 새 항목으로 쓴다
