# 08. 프론트 정적 파일을 같은 출처에서 서빙

상태: 진행 중(휴대폰 확인 남음)
의존: 01, frontend 항목 7(`src/api/` 전환)

## 목표
발표 때 서버 하나만 띄우면 근로자 화면·센터 화면·API가 같은 주소에서 동작하게 한다. `frontend/dist`를 FastAPI가 정적 파일로 서빙하고, 같은 출처이므로 CORS 설정이 필요 없어진다. 다른 기기(휴대폰)에서 접속하는 시연을 위한 것이다.

## 범위
- 하는 것
  - `app/settings.py`에 `STATIC_DIR`(기본 빈 값 = 서빙 안 함) 추가
  - `app/main.py`: `STATIC_DIR`이 있으면 `/api` 외 경로를 정적 파일로, 없는 경로는 `index.html`로 돌려준다(SPA 라우팅). `/api/*`는 정적 파일보다 먼저 매칭된다
  - `README.md` "실행"에 발표용 명령 추가: `npm --prefix frontend run build` → `STATIC_DIR=../frontend/dist uv run fastapi run app/main.py --host 0.0.0.0`
  - `tests/test_static.py`: 임시 폴더에 `index.html`을 두고 `/`, `/center`, `/없는경로`가 `index.html`을, `/api/health`가 JSON을 돌려주는지
- 하지 않는 것
  - 도커·클라우드 배포(`chore/`), HTTPS, 프론트 빌드 설정 변경, 인증

## API·파일
- 변경되는 API 없음. `/`와 프론트 경로가 새로 응답한다
- 추가: `tests/test_static.py`
- 수정: `app/main.py`, `app/settings.py`, `.env.example`, `README.md`

## 완료 기준
- [x] `uv run pytest` 통과. `STATIC_DIR`이 빈 기본 상태에서 모든 기존 테스트가 그대로 통과한다
- [ ] 프론트를 빌드해 위 명령으로 띄운 뒤, 같은 Wi-Fi의 휴대폰에서 `http://<맥 IP>:8000/`로 근로자 화면이 열리고 전송한 사례가 PC의 `/center`에 나타난다(확인 결과를 `## 결과`에)
- [x] `STATIC_DIR` 없이 띄우면 `/`가 404이고 `/api/health`는 그대로다
- [x] `README.md`에 발표용 실행 명령이 있다

## 결과

### 결정
- 서빙은 `StaticFiles` 대신 catch-all 경로 하나(`mount_frontend`, `/api` 라우터 뒤에 등록)다. `StaticFiles(html=True)`는 없는 경로를 `index.html`로 돌려주지 않아 `/center` 새로고침이 404가 된다.
- 경로 규칙: `/api`·`/api/*`는 항상 JSON 404(오류 형식 유지) → 빌드 폴더 안의 있는 파일 → 확장자가 있으면 404(없는 `/assets/x.js`에 HTML을 주면 브라우저 오류가 헷갈림) → 나머지는 `index.html`.
- `../` 경로(`/%2e%2e/secret.txt`)는 `resolve()` 뒤 빌드 폴더 안인지 확인해 막는다.
- `STATIC_DIR`은 시작 시 `index.html`이 있는지 확인한다. 빌드를 잊고 띄우면 서버가 뜨지 않는다.
- 발표 명령은 문서의 `npm --prefix frontend run build`가 아니라 `VITE_API_BASE=/api`를 붙인 API 모드 빌드다(메모의 전제). 단독 모드 빌드는 서버를 부르지 않는다.
- CORS 설정은 그대로 둔다. 같은 출처면 쓰이지 않고, 개발 서버(5180) 직접 호출에는 여전히 필요하다.

### 실행
- `uv run ruff check . && uv run ruff format --check .` → 통과
- `uv run pytest` → 2781 passed. 새 `tests/test_static.py` 12개(`/`, `/center`, `/center/cases/C-1001`, `/없는경로` → `index.html`, 있는 파일, 없는 asset 404, `/api/health`·`/api/center/cases` 우선, `/api`·`/api/nope` JSON 404, 폴더 밖 차단, `STATIC_DIR` 없을 때 `/` 404, `index.html` 없는 폴더 거절)
- 실제 빌드로 확인(`VITE_API_BASE=/api npm run build` → `STATIC_DIR=../frontend/dist uv run fastapi run app/main.py --port 8767`, curl)

| 요청 | 결과 |
|---|---|
| `/`, `/center`, `/report`, `/없는경로` | 200 `text/html`, `<title>for nav</title>` |
| `/assets/index-CxKYmdx8.js` | 200 `text/javascript`, 번들에 `/api` 있음 |
| `/assets/missing.js` | 404 |
| `/api/nope` | `{"error":{"code":"NOT_FOUND",...}}` |
| `POST /api/center/cases` → `GET /api/center/cases` | 보낸 사례 `C-67649`가 목록에 있음 |

- `STATIC_DIR` 없이: `/` 404, `/api/health` `{"ok": true}`(`test_without_static_dir_root_is_404`)

### 남은 일
- **휴대폰 확인(완료 기준 둘째 줄)은 사용자가 한다.** 같은 Wi-Fi에서 `http://<맥 IP>:8000/`로 근로자 화면을 열고 전송한 사례가 PC의 `/center`에 나타나는지 본 뒤 여기에 적고 상태를 완료로 바꾼다. 맥 방화벽이 8000 포트를 막으면 열어야 한다

### 바뀐 API
- 없음. `STATIC_DIR`이 있을 때만 `/`와 프론트 경로가 응답한다

## 메모
- 프론트가 API 모드(`VITE_API_BASE=/api`)로 빌드되어 있어야 한다. 그 전환은 frontend 항목 7이며, 이 항목은 그 뒤에 한다
- 휴대폰 시연에서 119 안내가 네트워크 실패로 늦으면 안 되므로, 프론트의 "응급 판정 실패 시 브라우저 규칙 대체"가 켜져 있는지 시연 전에 확인한다
