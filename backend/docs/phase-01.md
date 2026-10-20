# Backend Phase 01 — 실행·검증 기반과 API 셸

## 목표

`backend/`에 Python 3.11·uv 기반 FastAPI 프로젝트를 만든다. Ruff·mypy·pytest 검증 명령과 단일 worker Uvicorn 실행 명령을 실제로 실행할 수 있게 한다. 계약의 `GET /api/v1/health`에 응답하는 최소 앱 셸을 둔다. 이후 phase는 같은 실행·검증 기반 위에서, HTTP handler와 도메인 규칙을 분리한 구조로 기능을 추가한다.

이 phase는 공유 계약 산출물(루트 `fixtures/`, 생성 스키마) 없이 완료할 수 있어야 한다. 세션·지도·경로·예약 같은 제품 기능은 이 phase의 결과물이 아니다.

## 범위

포함:

- `backend/`에 uv 프로젝트(`pyproject.toml`, `uv.lock`)를 구성한다. `uv.lock`을 커밋하고 `uv sync --locked`로 재현한다.
- Python 버전을 `.python-version`과 `requires-python`으로 3.11 계열에 고정한다. Python 3.11의 지원 종료일, uv와 직접 의존성 버전을 공식 문서·PyPI로 확인하고 출처와 날짜를 검증 결과에 기록한다.
- 이번 phase에서 설치하는 의존성: FastAPI, Pydantic, Uvicorn, 그리고 개발용 pytest, HTTPX, Ruff, mypy. 이들을 쓰는 데 필요한 플러그인·타입 패키지는 허용한다.
- 이후 phase에서 쓸 SQLAlchemy·Alembic·NetworkX는 설치하지 않는다. 대신 Python 3.11을 지원하는 현행 버전이 있는지 확인해 기록한다.
- `backend/app/`에 app factory, `api/` 라우터, 설정 모듈을 둔다. 이후 phase에서 쓸 빈 패키지 디렉터리는 미리 만들지 않는다.
- `GET /api/v1/health`: DB·파일·외부 네트워크에 접근하지 않고 200 JSON으로 생존 상태를 응답한다. 응답에 토큰·파일 경로·환경 변수 같은 내부 정보를 넣지 않는다. 응답 필드의 계약 스키마는 계약 phase에서 확정한다.
- 실행 명령: Uvicorn 단일 worker로 기동하며 기본 바인드는 `127.0.0.1:8000`이다. 이 값은 프론트 dev proxy 기본값(`YARDPILOT_API_ORIGIN`=`http://127.0.0.1:8000`)과 같다. 호스트·포트는 환경 변수로 바꿀 수 있고, 변수 이름과 기본값을 문서화한다. 실행 명령은 worker 수를 늘리지 않는다.
- Swagger UI·ReDoc은 외부 CDN 자산을 불러오므로 비활성화한다.
- 백엔드 테스트는 `docs/HARNESS.md`의 구현 경로에 맞춰 `tests/backend/`에 두고, pytest 설정은 `backend/pyproject.toml`에 둔다.
- Ruff lint와 format 검사, mypy strict(앱과 `tests/backend/`)를 구성한다.
- `.gitignore`에 pytest·mypy·Ruff 캐시 경로를 추가한다.
- `backend/AGENTS.md`의 "현재 앱 코드와 실행 명령은 없다" 문구를 실제 등록 명령으로 갱신한다.

제외:

- 계약 Pydantic 스키마, 공통 오류 응답 형식(`{"error": ...}`)과 `request_id`, OpenAPI·이벤트 JSON Schema 내보내기, 루트 `fixtures/` (계약 phase).
- 세션·쿠키·역할 검사, Origin 검증과 개발 서버 origin 허용 목록, CORS (세션·권한 phase).
- SQLite·SQLAlchemy·Alembic, 단일 Coordinator, 쓰기 큐, 경로 탐색, 예약·점유 상태기계, WebSocket `/api/v1/ws`.
- 루트 `simulator/`와 차량 에이전트(`agents/`, `training/`), 모델링 레인 uv 프로젝트와의 workspace 통합.
- 프론트 빌드 산출물 정적 제공과 SPA fallback.
- `.github/workflows`에 백엔드 CI 작업 추가 (정책 파일 변경이므로 별도 PR에서 다룬다).
- 성능 목표(차량 5대 수신→안내 p95 500ms) 측정.

## 작업 체크리스트

- [x] Python 3.11 최신 패치·지원 종료일, uv 버전, FastAPI·Pydantic·Uvicorn·pytest·HTTPX·Ruff·mypy 버전을 공식 문서·PyPI로 확인하고 출처를 기록한다.
- [x] SQLAlchemy·Alembic·NetworkX의 현행 버전이 Python 3.11을 지원하는지 확인하고 기록한다 (설치하지 않음).
- [x] `backend/`에 uv 프로젝트를 만들고 `.python-version`·`requires-python`으로 Python 버전을 고정한다. 직접 의존성은 정확한 버전으로 고정하고 `uv.lock`을 생성한다.
- [x] Ruff lint·format 설정과 실행 명령을 구성한다.
- [x] mypy strict 설정과 실행 명령을 구성한다. 검사 대상은 `backend/app/`과 `tests/backend/`다.
- [x] pytest 설정(`testpaths`가 `tests/backend/`를 가리킴)과 실행 명령을 구성한다.
- [x] `backend/app/`에 app factory와 설정 모듈을 두고, `api/`에 `/api/v1` 라우터와 health handler를 둔다.
- [x] Swagger UI·ReDoc을 비활성화한다.
- [x] 단일 worker Uvicorn 실행 명령과 호스트·포트 환경 변수를 구성하고 기본값을 문서화한다.
- [x] TestClient로 health 응답, 정의되지 않은 `/api/v1/...` 경로의 404, `/docs`·`/redoc` 미제공을 검증하는 테스트를 작성한다.
- [x] health handler가 DB·파일·외부 네트워크에 접근하지 않음을 검증하는 테스트를 작성하거나 확인 근거를 기록한다.
- [x] 실행 명령으로 실제 서버를 띄워 `curl`로 health를 확인하는 수동 절차와 결과를 기록한다.
- [x] 백엔드를 띄운 상태에서 프론트 `npm run dev` proxy를 거친 `/api/v1/health` 응답을 확인하는 절차와 결과를 기록한다.
- [x] `.gitignore`에 `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`를 추가한다.
- [x] `backend/AGENTS.md`의 검증 기준 문단을 실제 등록 명령으로 갱신한다.
- [x] 아래 완료 조건별 실행 명령·결과를 검증 결과 섹션에 기록한다.

## 의존성

- [프론트 phase-01](../frontend/phase-01.md): dev server proxy(`/api` → `YARDPILOT_API_ORIGIN`, 기본값 `http://127.0.0.1:8000`). 이 산출물은 proxy를 거친 health 확인에만 쓴다. 백엔드 앱과 검증 명령은 프론트에 의존하지 않는다.

루트 `fixtures/`와 계약 스키마 산출물은 이 phase의 선행 조건이 아니다. 계약 스키마를 만드는 이후 백엔드 phase가 이 phase를 선행 조건으로 둔다. 그 연결은 이 문서가 아니라 이후 phase 문서에 기록한다.

## 완료 조건

- [x] `backend/`에서 `uv sync --locked`가 커밋된 `uv.lock`만으로 재현되고, 실행 전후 `uv.lock`이 바뀌지 않는다.
- [x] Ruff lint, Ruff format 검사, mypy strict, pytest가 모두 오류 없이 종료된다.
- [x] TestClient 테스트에서 `GET /api/v1/health`가 200과 `application/json`을 반환하고, 정의되지 않은 `/api/v1/...` 경로는 HTML이 아닌 404를 반환한다.
- [x] `/docs`와 `/redoc`이 제공되지 않는다.
- [x] health 응답이 DB·파일·외부 네트워크 없이 만들어지고, 토큰·경로·환경 변수 같은 내부 정보를 포함하지 않는다.
- [x] 등록된 실행 명령으로 서버가 단일 worker로 `127.0.0.1:8000`에 기동되고, `curl`로 요청한 `/api/v1/health`가 200을 반환한다.
- [x] 백엔드를 띄운 상태에서 프론트 dev server를 거친 `/api/v1/health`가 502가 아닌 200 JSON으로 응답한다.
- [x] 이번 phase에서 설치한 직접 의존성이 범위 섹션에 적은 목록을 벗어나지 않는다.
- [x] 확인한 Python·uv·패키지 버전과 출처, 미설치 패키지(SQLAlchemy·Alembic·NetworkX)의 Python 3.11 지원 확인 결과가 기록돼 있다.
- [x] `backend/AGENTS.md`에 실제 명령이 등록돼 있다.

## 검증 결과

상태: 구현 완료. 아래 기록은 `feature/backend/phase-01-api-shell` 커밋 기준이다.

> 2026-10-20 작업 방식 간소화로 테스트를 `tests/backend/`에서 `backend/tests/`로 옮겼다. 아래 기록의 `tests/backend/`·`../tests/backend`는 지금의 `backend/tests/`·`tests`에 해당한다.

### 실행 환경

- macOS 26.6.2 (arm64), uv 0.13.1 (Homebrew), CPython 3.11.17 (uv 관리 배포본, `uv sync`가 내려받음)
- 프론트 proxy 확인: Node v24.21.0 (`frontend/.nvmrc`), Vite 8.3.4
- 실행일 2026-10-20. `backend/.venv`와 pytest·mypy·Ruff 캐시, `__pycache__`를 지운 뒤 아래 명령을 차례로 실행했다.

### 버전 확인과 출처 (2026-10-20 확인)

- Python 3.11: [PEP 릴리스 주기](https://peps.python.org/api/release-cycle.json) 기준 status `security`, 지원 종료 2027-10이다(PEP 664). [python.org 릴리스 API](https://www.python.org/api/v2/downloads/release/?is_published=true) 기준 최신 패치는 3.11.17(2026-10-01)이다. `.python-version`은 `3.11`, `requires-python`은 `>=3.11,<3.12`이고 lock에는 `==3.11.*`로 기록된다. 지원 종료까지 약 1년 남았으므로 이후 버전 상향은 별도 phase에서 결정해야 한다.
- uv: 로컬 0.13.1(Homebrew 2026-10-14)이다. [PyPI uv](https://pypi.org/project/uv/) 최신은 0.13.3(2026-10-20 공개)이다. `[tool.uv] required-version = ">=0.13.1"`로 하한을 둔다.
- 패키지 버전·공개일·`requires_python`은 PyPI JSON API(`https://pypi.org/pypi/<pkg>/json`)로 확인했다. 각 프로젝트의 문서 사이트를 하나씩 읽지는 않았다.
- 프론트 phase-01과 같은 기준을 따랐다. 2026-10-13 이전(7일 이상 경과)에 공개된 최신 안정판만 골랐다. 이 기준을 `[tool.uv] exclude-newer = "2026-10-13T00:00:00Z"`로 lock에 고정했다.
- 선택한 직접 의존성은 모두 Python 3.11을 지원한다(괄호 안은 공개일).
  - 런타임: fastapi 0.143.0(10-08, `>=3.10`), pydantic 2.14.1(10-11, `>=3.10`), uvicorn 0.54.0(09-25, `>=3.10`)
  - 개발: pytest 9.1.1(06-19, `>=3.10`), httpx 0.28.1(2024-12-06, `>=3.8`), ruff 0.17.0(10-09), mypy 2.4.0(10-01, `>=3.10`)
  - 기준일 이후 최신은 fastapi 0.150.0(10-19)과 ruff 0.17.1(10-15)이며 제외했다.
- uv가 해석한 주요 전이 의존성은 starlette 1.7.0, pydantic-core 2.50.1, opentelemetry-api 1.45.1(fastapi 0.143.0의 필수 의존성), anyio, h11 등이다. lock의 패키지는 프로젝트를 포함해 30개다.
- 설치하지 않은 패키지의 Python 3.11 지원:
  - SQLAlchemy 2.1.5(10-16): `requires_python >=3.11`, classifier에 3.11~3.15가 있어 지원한다.
  - Alembic 1.20.0(09-11): `>=3.10`, classifier에 3.10~3.15가 있어 지원한다.
  - **NetworkX 최신 3.7(09-21)은 `>=3.12`(3.14.1 제외)를 요구해 Python 3.11을 지원하지 않는다.** 3.11을 지원하는 마지막 버전은 3.6.1(2025-12-08, `>=3.11`)이다. 경로 탐색 phase에서는 3.6.x 고정과 Python 상향 중 하나를 골라야 한다. 이 phase에서는 결정하지 않는다.

### 실행 명령과 결과 (`backend/`)

| 명령 | 결과 |
|---|---|
| `uv sync --locked` | exit 0, CPython 3.11.17로 `.venv` 생성. 실행 전후 `uv.lock` sha256(ba71b23763c32f58…) 동일. `uv lock --check`도 exit 0 |
| `uv run ruff check . ../tests/backend` | exit 0, All checks passed |
| `uv run ruff format --check . ../tests/backend` | exit 0, 13 files already formatted |
| `uv run mypy` | exit 0, strict, 12 source files(`app`, `../tests/backend`), pydantic.mypy 플러그인 |
| `uv run pytest` | exit 0, 22 passed(`filterwarnings = error`) |

서버 수동 확인 1(`uv run python -m app`, 환경 변수 없음): 실행 전 8000번 포트에 리스너가 없었다(`lsof`).
- 로그는 `Started server process`와 `Uvicorn running on http://127.0.0.1:8000`이었다. 다중 worker일 때 나오는 `Started parent process`는 없었다.
- `lsof`로 본 리스너는 `127.0.0.1:8000` 하나다. 서버 프로세스에 자식 프로세스가 없었다(`pgrep -P`).
- `curl -i /api/v1/health`는 `200 OK`, `content-type: application/json`, 본문 `{"status":"ok"}`였다.
- `/api/v1/nope`는 `404`, `application/json`, `{"detail":"Not Found"}`였다. `/docs`와 `/redoc`은 모두 404였다.

서버 수동 확인 2(프론트 dev proxy): 위 백엔드를 띄운 채 `frontend/`에서 `npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`를 실행했다.
- `curl -i http://127.0.0.1:5173/api/v1/health`는 `200 OK`, `server: uvicorn`, `content-type: application/json`, `{"status":"ok"}`였다. 백엔드 access log에도 해당 요청이 남았다.
- proxy를 거친 `/api/v1/nope`는 JSON 404였다.

서버 수동 확인 3(환경 변수): `YARDPILOT_API_PORT=8011 uv run python -m app`은 `127.0.0.1:8011`에서 기동했고 health가 200이었다. `YARDPILOT_API_PORT=abc`는 `설정 오류: YARDPILOT_API_PORT는 1~65535 정수여야 합니다: 'abc'`를 출력하고 exit 1로 끝났다. 확인 후 모든 서버를 종료했고 8000·8011·5173 리스너가 없음을 확인했다.

검사 자체가 문제를 잡아내는지도 확인했다. 변경은 모두 원복했고, 바이트코드 캐시를 지운 상태로 실행했다.
- health 응답에 `os.environ`의 호스트 값을 넣으면 health·격리 테스트 3개가 실패한다.
- health handler에서 파일을 열면 격리 테스트 2개가 실패한다.
- `docs_url=None`을 제거하면 `/docs`·`/docs/oauth2-redirect` 테스트가 실패한다.
- `workers=1`을 `workers=2`로 바꾸면 실행 명령 테스트가 실패한다.

### 완료 조건별 증거

- `uv sync --locked` 재현: `.venv`를 지운 뒤 exit 0이었고 `uv.lock` 해시가 바뀌지 않았다. 위 표에 있다.
- Ruff lint·format, mypy strict, pytest: 위 표와 같이 모두 exit 0이다.
- health·404 (`tests/backend/test_app.py`):
  - `GET /api/v1/health`는 200, `content-type` `application/json`, `{"status": "ok"}`를 반환한다.
  - `/api/v1/unknown`, `/api/v1/health/extra`, `/api/v1/`은 JSON 404이고 본문에 `<html`이 없다.
  - `POST /api/v1/health`는 405다.
- `/docs`·`/redoc` 미제공: 같은 파일에서 `/docs`, `/redoc`, `/docs/oauth2-redirect`가 404이고 본문에 swagger·redoc 문자열이 없음을 확인한다. 실제 서버에서도 404였다.
- health의 I/O 격리와 내부 정보 비노출 (`tests/backend/test_health_isolation.py`):
  - `builtins.open`, `os.open`, `socket.socket.connect`, `socket.create_connection`, `socket.getaddrinfo`, `os.getenv`, `os.environ`을 모두 예외를 내도록 바꾼다.
  - 그 상태에서 handler 코루틴을 이벤트 루프 없이 한 번에 실행해 결과를 확인한다. 대기 지점이 없다는 뜻이다.
  - HTTP 요청도 같은 차단 상태에서 200을 받는다. 단, Pydantic이 첫 요청에서 응답 직렬화기를 만들며 `PYDANTIC_DISABLE_PLUGINS`를 한 번 읽으므로 예열 요청 1회 뒤에 막는다. 이는 handler가 아닌 프레임워크의 지연 초기화다.
  - 호스트·포트·토큰·DB URL 환경 변수에 표식 값을 넣어도 응답 본문은 `{"status":"ok"}`뿐이다. 표식 값과 작업 디렉터리 경로가 본문에 없다.
  - 코드상으로도 `app/api/health.py`는 `fastapi.APIRouter` 외에 아무것도 import하지 않는다. DB 코드는 아직 존재하지 않는다.
- 단일 worker·`127.0.0.1:8000`·curl 200:
  - `tests/backend/test_main.py`가 실행 명령이 `uvicorn.run(..., host="127.0.0.1", port=8000, workers=1, reload=False)`을 호출하는지, 잘못된 설정이면 `SystemExit`으로 끝나는지 확인한다.
  - `tests/backend/test_settings.py`가 기본값, 환경 변수 적용, 잘못된 포트(빈 값·0·65536·음수·소수·문자·지수 표기)와 빈 호스트 거부를 확인한다.
  - 실제 기동 결과는 서버 수동 확인 1에 있다.
- 프론트 proxy 200 JSON: 서버 수동 확인 2에 있다.
- 직접 의존성 범위: `uv tree --depth 1` 결과는 런타임 fastapi·pydantic·uvicorn, dev 그룹 httpx·mypy·pytest·ruff다. 범위 목록과 같다. mypy 플러그인은 pydantic에 포함된 `pydantic.mypy`를 써서 추가 패키지가 없다. SQLAlchemy·Alembic·NetworkX·pydantic-settings는 설치하지 않았다.
- 버전·출처·미설치 패키지 확인: 위 "버전 확인과 출처" 절에 있다.
- `backend/AGENTS.md`: "등록 명령" 절에 실제 명령, Python 고정, 호스트·포트 환경 변수와 기본값, docs 비활성화를 등록했다. "현재 앱 코드와 실행 명령은 없다" 문구를 지웠다.

### 구성 메모

- `backend/app/`: `main.py`(app factory `create_app`), `settings.py`(`YARDPILOT_API_HOST`·`YARDPILOT_API_PORT` 해석), `__main__.py`(실행 명령), `api/router.py`(`/api/v1` 라우터), `api/health.py`(health handler).
- uv 프로젝트는 `package = false`(빌드하지 않는 앱)다. pytest는 `pythonpath = ["."]`로 `app`을 찾고, mypy는 `files`의 `app` 위치로 찾는다.
- `.gitignore`에 `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`를 추가했다. 실행 후 `git status --ignored`에서 `backend/` 아래 세 캐시가 무시됨을 확인했다.

### 남은 제약

- Starlette 1.7.0의 `TestClient`는 `httpx` 대신 후속 패키지 `httpx2`(PyPI 별도 패키지, HTTPX 작성자)를 권장하며 import 때 `StarletteDeprecationWarning`을 낸다. 승인 범위의 의존성이 HTTPX이므로 `httpx2`는 설치하지 않았다. pytest `filterwarnings`에서 이 메시지 하나만 무시하고 나머지 경고는 오류로 둔다. `httpx2` 전환은 범위 변경이므로 이후 phase에서 결정해야 한다.
- 테스트 파일을 직접 지정하면 pytest가 `backend/pyproject.toml`을 찾지 못한다(테스트가 `backend/` 밖에 있음). 이때는 `-c pyproject.toml`을 붙여야 하며 `backend/AGENTS.md`에 적었다.
- NetworkX 최신판이 Python 3.11을 지원하지 않는다(위 기록). 경로 탐색 phase의 선행 결정 사항이다.
- 백엔드 CI 작업은 범위에서 제외했으므로 위 결과는 로컬 실행 증거다. Linux·Windows에서는 실행하지 않았다.
- health 응답 필드(`status`)는 임시이며 계약 phase에서 스키마로 확정한다. 공통 오류 형식이 정해지지 않았으므로 404 본문은 FastAPI 기본값(`{"detail": ...}`)이다.
- `openapi.json`은 기본 경로(`/openapi.json`)로 제공된다. 외부 자산을 부르지 않으므로 이 phase에서 막지 않았다. 노출 여부와 내보내기는 계약 phase에서 다룬다.
