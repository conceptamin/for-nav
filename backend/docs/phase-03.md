# Backend Phase 03 — 공통 실행 기반 (이름·오류·로그·LLM 인터페이스)

기준일: 2026-10-24 · 기준: [공통 기획서](../../docs/proposal.md), [백엔드 기획서](proposal.md)

## 배경

2026-10-24 기획 전환으로 [이전 phase-02](phase-02.md)는 과거 범위로 보존한다. 새 상담·인계 API는 인증·저장·보관 정책을 정한 뒤 별도 phase로 쓴다([공통 기획서](../../docs/proposal.md) 9·10장). 이 phase는 새 API 설계와 상관없이 쓰는 실행 기반만 구현한다. 이전 phase-02에서 "phase-03"으로 미룬 응급 모델·`/guide`·`/hospitals`는 이 문서의 범위가 아니다.

## 범위

포함:

- 이름 교체: `pyproject.toml`의 `name`·`description`, 환경 변수 `YARDPILOT_API_HOST`·`YARDPILOT_API_PORT` → `FORNAV_API_HOST`·`FORNAV_API_PORT`, FastAPI 제목, 관련 테스트·주석, `backend/AGENTS.md` 등록 명령 설명. `uv.lock`은 프로젝트 이름만 바뀐다.
- 공통 오류 응답: 계약 1장에 이미 있는 `{"error":{"code","message","request_id"}}` 형식. 404 `NOT_FOUND`, 405 `METHOD_NOT_ALLOWED`(Allow 헤더 유지), 422 `VALIDATION_ERROR`, 503 `LLM_UNAVAILABLE`, 500 `INTERNAL_ERROR`. `message`는 고정 개발자용 한국어이며 요청 값·예외 메시지·검증 상세를 담지 않는다.
- 요청마다 `request_id`(`req-` + 32자리 hex)를 만들어 오류 본문과 `X-Request-ID` 응답 헤더에 넣는다.
- 본문 없는 로깅: Uvicorn 접근 로그(쿼리 문자열을 남김)를 끄고 `app.access`가 경로·상태 코드·소요 시간·`request_id`만 남긴다. 처리하지 못한 예외는 미들웨어가 500으로 바꾸고 예외 종류만 남기며, 다시 올리지 않아 traceback·예외 메시지가 로그에 남지 않는다.
- LLM 인터페이스 `LLMClient`와 `generate()`: 호출마다 시간 제한(기본 10초), 실패·시간 초과·출력 스키마 불일치 시 재시도 1회, 그래도 실패하면 `LLMUnavailableError`(API에서 503). 프롬프트·응답 원문은 로그·예외에 넣지 않는다. 테스트용 `FakeLLMClient`.

제외:

- 실제 LLM 공급자 구현과 공급자·약관 확인: 무엇을 어떤 동의로 보낼지는 새 상담 API 설계에서 정한다.
- `/triage`·`/route`·`/summary`와 `fixtures/contract/`: 이전 기획의 API다. API v1 스키마는 바꾸지 않는다.
- 인증·상담 저장·인계·보험 상태 API, DB 선정.
- 프론트 proxy 변수 `YARDPILOT_API_ORIGIN` 이름 교체(`frontend/` 소관). 기본 origin이 같아 백엔드 이름 교체만으로 연결이 깨지지 않는다.
- 새 의존성, CI 변경.

## 작업 체크리스트

- [x] 이름과 환경 변수를 교체하고 기존 테스트를 새 이름으로 갱신한다.
- [x] 공통 오류 응답과 예외 처리기를 만든다.
- [x] `request_id`·접근 로그 미들웨어와 실행 명령의 로그 설정을 만든다.
- [x] LLM 인터페이스, `generate()`, 가짜 구현을 만든다.
- [x] 오류 형식·422 입력 미반환·500 상세 미노출·503을 테스트한다.
- [x] 본문·쿼리·예외 메시지·LLM 원문이 로그에 남지 않음을 테스트한다.
- [x] 재시도 1회, 3번째 호출 없음, 시간 초과, 스키마 불일치를 테스트한다.
- [x] 실제 서버를 띄워 응답 헤더·오류 본문·로그를 확인한다.

## 완료 조건

- [x] `uv sync --locked`, Ruff lint·format, mypy strict, pytest가 모두 오류 없이 끝난다.
- [x] `YARDPILOT`·`yardpilot` 문자열이 `backend/` 코드와 설정에 남지 않는다(phase-01·phase-02 기록 문서 제외).
- [x] 모든 응답에 `X-Request-ID`가 붙고, 오류 응답은 계약 1장 형식이며 그 `request_id`가 헤더와 같다.
- [x] 로그에 요청 본문·쿼리 문자열·예외 메시지가 남지 않는다.
- [x] LLM 호출이 시간 제한·재시도 1회·스키마 검증을 거치고, 실패 시 원문 없이 `LLMUnavailableError`가 된다.
- [x] 테스트가 외부 네트워크에 접속하지 않는다.
- [x] 직접 의존성이 phase-01과 같다.

## 검증 결과

상태: 구현 완료. 실행일 2026-10-24, macOS 26.6.2 (arm64), uv 0.13.1, CPython 3.11.17. `backend/.venv`를 지운 뒤 실행했다.

### 실행 명령과 결과 (`backend/`)

| 명령 | 결과 |
|---|---|
| `uv sync --locked` | exit 0. 실행 전후 `uv.lock` sha256 `95b664a0bb270d9d…` 동일. `uv lock --check` exit 0 |
| `uv run ruff check .` | exit 0, All checks passed |
| `uv run ruff format --check .` | exit 0, 24 files already formatted |
| `uv run mypy` | exit 0, strict, 20 source files |
| `uv run pytest` | exit 0, 43 passed(`filterwarnings = error`) |

`uv tree --depth 1`: 런타임 fastapi 0.143.0·pydantic 2.14.1·uvicorn 0.54.0, dev httpx·mypy·pytest·ruff. phase-01과 같다. `uv lock`의 변경은 패키지 이름(`yardpilot-backend` → `fornav-backend`)뿐이며 해석된 패키지는 30개 그대로다.

### 테스트 구성

- `tests/test_errors.py`: 200 응답의 `X-Request-ID` 형식, 5회 요청의 id가 모두 다름, 404·405(Allow 헤더 유지)·422(타입 불일치·깨진 JSON·필드 누락)·500·503이 `{"error":{"code","message","request_id"}}` 형식이고 `request_id`가 헤더와 같음. 경로·본문에 넣은 표식 문자열과 예외 종류가 응답에 없음.
- `tests/test_logging.py`: 200·500·405 요청에 쿼리와 본문으로 표식을 넣고, 접근 로그가 `path=… status=… duration_ms=… request_id=…` 한 줄뿐이며 서버 쪽 로그 전체에 표식이 없음. 422도 같음. 처리하지 못한 예외는 `unhandled=ValueError request_id=…`만 남고 `exc_info`가 없음. httpx 로그는 테스트 클라이언트가 보낸 URL이라 검사에서 뺐다.
- `tests/test_llm.py`: 정상 1회 호출, 스키마 불일치·JSON 아님·공급자 오류·시간 초과 각각 재시도 후 성공(호출 2회), 두 번 실패하면 3번째 응답을 쓰지 않고 `LLMUnavailableError`(`__context__`·`__cause__` 없음), 실패 로그는 예외 종류만 있고 원문 표식 없음.
- `tests/test_main.py`: 실행 명령이 `workers=1`, `reload=False`, `access_log=False`, `log_config=LOG_CONFIG`로 Uvicorn을 부름.
- 외부 네트워크: 새 테스트는 TestClient와 `FakeLLMClient`만 쓴다. `app/llm.py`에는 네트워크 코드가 없다.

### 검사가 문제를 잡는지 확인

아래처럼 코드를 하나씩 바꾸고 pytest를 돌린 뒤 원복했다. 원복 후 43 passed.

| 변경 | 결과 |
|---|---|
| 422 처리기 등록 제거(FastAPI 기본 본문이 입력값을 되돌림) | 3 failed |
| 접근 로그에 쿼리 문자열 추가 | 3 failed |
| LLM 시도 횟수를 3회로 | 2 failed |
| 미들웨어에서 처리하지 못한 예외를 다시 올림 | 3 failed |
| LLM 실패 로그에 예외 문자열 기록 | 1 failed |
| `except` 블록 안에서 `LLMUnavailableError`를 올림 | 2 failed |
| `X-Request-ID` 헤더 제거 | 13 failed |

### 서버 수동 확인

`uv run python -m app`(환경 변수 없음), 실행 전 8000번 리스너 없음.

- `GET /api/v1/health` → 200, `x-request-id: req-d1674db8…`, `{"status":"ok"}`.
- `GET /api/v1/nope?q=synthetic-marker-qs` → 404, `{"error":{"code":"NOT_FOUND","message":"없는 경로입니다.","request_id":"req-2f46ea60…"}}`, 헤더와 같은 id.
- `POST /api/v1/health`(본문 `{"text":"synthetic-marker-body"}`) → 405, `allow: GET`, `METHOD_NOT_ALLOWED`.
- 서버 로그는 `uvicorn.error` 기동·종료 줄과 `app.access path='/api/v1/nope' status=404 duration_ms=0.2 request_id=req-2f46ea60…` 같은 줄뿐이었다. `synthetic-marker` 검색 결과 0건. Uvicorn 접근 로그 줄은 없었다.
- `FORNAV_API_PORT=abc uv run python -m app` → `설정 오류: FORNAV_API_PORT는 1~65535 정수여야 합니다: 'abc'`, exit 1. 종료 후 8000번 리스너 없음.

### 남은 일

- 실제 LLM 공급자 구현, 공급자·약관 확인, 실제 호출 수동 확인은 새 상담 API 설계 후 phase에서 한다.
- 프론트 proxy 변수 `YARDPILOT_API_ORIGIN` → `FORNAV_API_ORIGIN`은 프론트 phase에서 바꾼다.
- 접근 로그의 `path`는 요청 경로 그대로다. 새 API에서 경로에 상담 id 같은 값이 들어가면 경로 템플릿으로 남길지 그때 정한다.
- 처리하지 못한 예외가 응답 시작 뒤에 나면 500을 보낼 수 없어 연결만 끊긴다. 지금 엔드포인트는 스트리밍 응답이 없다.
- API v1 계약(`docs/api-contract.md`)과 `fixtures/`는 바꾸지 않았다. 오류 형식은 계약 1장에 이미 있던 내용을 구현한 것이다.
