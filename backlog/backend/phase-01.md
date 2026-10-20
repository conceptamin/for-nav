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

- [ ] Python 3.11 최신 패치·지원 종료일, uv 버전, FastAPI·Pydantic·Uvicorn·pytest·HTTPX·Ruff·mypy 버전을 공식 문서·PyPI로 확인하고 출처를 기록한다.
- [ ] SQLAlchemy·Alembic·NetworkX의 현행 버전이 Python 3.11을 지원하는지 확인하고 기록한다 (설치하지 않음).
- [ ] `backend/`에 uv 프로젝트를 만들고 `.python-version`·`requires-python`으로 Python 버전을 고정한다. 직접 의존성은 정확한 버전으로 고정하고 `uv.lock`을 생성한다.
- [ ] Ruff lint·format 설정과 실행 명령을 구성한다.
- [ ] mypy strict 설정과 실행 명령을 구성한다. 검사 대상은 `backend/app/`과 `tests/backend/`다.
- [ ] pytest 설정(`testpaths`가 `tests/backend/`를 가리킴)과 실행 명령을 구성한다.
- [ ] `backend/app/`에 app factory와 설정 모듈을 두고, `api/`에 `/api/v1` 라우터와 health handler를 둔다.
- [ ] Swagger UI·ReDoc을 비활성화한다.
- [ ] 단일 worker Uvicorn 실행 명령과 호스트·포트 환경 변수를 구성하고 기본값을 문서화한다.
- [ ] TestClient로 health 응답, 정의되지 않은 `/api/v1/...` 경로의 404, `/docs`·`/redoc` 미제공을 검증하는 테스트를 작성한다.
- [ ] health handler가 DB·파일·외부 네트워크에 접근하지 않음을 검증하는 테스트를 작성하거나 확인 근거를 기록한다.
- [ ] 실행 명령으로 실제 서버를 띄워 `curl`로 health를 확인하는 수동 절차와 결과를 기록한다.
- [ ] 백엔드를 띄운 상태에서 프론트 `npm run dev` proxy를 거친 `/api/v1/health` 응답을 확인하는 절차와 결과를 기록한다.
- [ ] `.gitignore`에 `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`를 추가한다.
- [ ] `backend/AGENTS.md`의 검증 기준 문단을 실제 등록 명령으로 갱신한다.
- [ ] 아래 완료 조건별 실행 명령·결과를 검증 결과 섹션에 기록한다.

## 의존성

- [프론트 phase-01](../frontend/phase-01.md): dev server proxy(`/api` → `YARDPILOT_API_ORIGIN`, 기본값 `http://127.0.0.1:8000`). 이 산출물은 proxy를 거친 health 확인에만 쓴다. 백엔드 앱과 검증 명령은 프론트에 의존하지 않는다.

루트 `fixtures/`와 계약 스키마 산출물은 이 phase의 선행 조건이 아니다. 계약 스키마를 만드는 이후 백엔드 phase가 이 phase를 선행 조건으로 둔다. 그 연결은 이 문서가 아니라 이후 phase 문서에 기록한다.

## 완료 조건

- [ ] `backend/`에서 `uv sync --locked`가 커밋된 `uv.lock`만으로 재현되고, 실행 전후 `uv.lock`이 바뀌지 않는다.
- [ ] Ruff lint, Ruff format 검사, mypy strict, pytest가 모두 오류 없이 종료된다.
- [ ] TestClient 테스트에서 `GET /api/v1/health`가 200과 `application/json`을 반환하고, 정의되지 않은 `/api/v1/...` 경로는 HTML이 아닌 404를 반환한다.
- [ ] `/docs`와 `/redoc`이 제공되지 않는다.
- [ ] health 응답이 DB·파일·외부 네트워크 없이 만들어지고, 토큰·경로·환경 변수 같은 내부 정보를 포함하지 않는다.
- [ ] 등록된 실행 명령으로 서버가 단일 worker로 `127.0.0.1:8000`에 기동되고, `curl`로 요청한 `/api/v1/health`가 200을 반환한다.
- [ ] 백엔드를 띄운 상태에서 프론트 dev server를 거친 `/api/v1/health`가 502가 아닌 200 JSON으로 응답한다.
- [ ] 이번 phase에서 설치한 직접 의존성이 범위 섹션에 적은 목록을 벗어나지 않는다.
- [ ] 확인한 Python·uv·패키지 버전과 출처, 미설치 패키지(SQLAlchemy·Alembic·NetworkX)의 Python 3.11 지원 확인 결과가 기록돼 있다.
- [ ] `backend/AGENTS.md`에 실제 명령이 등록돼 있다.

## 검증 결과

미실행. 구현 후 실행 환경, 버전 확인 출처, 실행 명령·결과, 완료 조건별 증거, 남은 제약을 기록한다.
