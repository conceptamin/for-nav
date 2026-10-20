# 백엔드 작업 규칙

루트 `CLAUDE.md`, [공통 계약](../docs/api-contract.md), [백엔드 기획서](docs/proposal.md)를 먼저 읽는다. phase 문서는 `backend/docs/phase-XX.md`에 쓴다. 지정된 phase의 범위만 구현하고 검증 결과를 같은 문서에 남긴다. 다른 영역에 의존하면 그 영역의 phase 문서 경로를 적는다. 실행·검증 명령은 아래 "검증 기준"에 있다([phase-01](docs/phase-01.md)).

## 범위와 스택

`backend/`(향후 `backend/simulator/` 포함)를 담당한다. Python 3.11, FastAPI/Pydantic, 단일 worker Uvicorn, NetworkX DiGraph, SQLite/SQLAlchemy/Alembic을 기준으로 한다. Python 환경·의존성은 uv(`pyproject.toml`, `uv.lock`)로 관리한다. pytest·HTTPX·TestClient·Ruff·mypy를 구현 단계에서 구성한다. 차량 모델과 온라인 학습은 `modeling/`의 책임이다.

## 불변 조건

- 단일 Coordinator와 직렬화된 DB 쓰기로 결정한다. 예약·안내·이벤트를 한 트랜잭션에 저장하고 commit 이후 방송한다. 활성 소유자는 하나다.
- OCCUPIED는 실행·차량·구간·활성 토큰이 일치하는 실제 EXIT로만 해제한다. TTL·예측·ACK는 해제 증거가 아니다. 미예약 진입·확인 불가·복구 중 상태는 UNKNOWN이다.
- 우선순위 전에 점유·대기 공간·통행 제약·신선도를 확인한다. 현재 점유를 우선순위로 뒤집지 않는다.
- epoch·seq·지도·모델 버전·유한값·시각을 검사한다. 최신 위치와 유실되면 안 되는 ENTER/EXIT 처리를 분리한다.
- 서버가 역할·차량 범위·Origin을 검사한다. 멱등 키 본문 불일치와 버전 충돌은 409다. 인증 토큰을 로그에 남기지 않는다.
- 서버 복구는 실행 PAUSED/복구 필요, 예약 UNKNOWN으로 시작한다. 확인 없이 통행을 재허용하지 않는다.
- 시뮬레이터는 단일 활성 실행·고정 seed를 유지한다. 벽시계 heartbeat와 배속되는 sim_time_s를 분리한다. 모델 오차 비교와 제어 효과 비교를 분리한다.

## 검증 기준

순수 도메인 테스트로 경로 제약·동시 예약·중복 ENTER·늦거나 위조된 EXIT·미이행·구간 내부 정지·대기 공간 불가를 검증한다. API 권한·잘못된 수치·멱등성, DB commit 실패, 스냅샷 구독 경쟁, 느린 클라이언트, 재시작을 통합 검증한다. 아래 등록 명령으로 Ruff·mypy·pytest 결과를 남긴다. 5대 수신→안내 p95 500ms는 측정 목표이며 현장 안전 성능 보장이 아니다.

### 등록 명령

Python은 `backend/.python-version`(3.11)과 `requires-python`(`>=3.11,<3.12`)으로 고정하며 uv가 필요하면 내려받는다. 직접 의존성은 `pyproject.toml`에 정확한 버전으로 고정하고 `[tool.uv] exclude-newer`보다 나중에 공개된 배포본은 해석하지 않는다. 앱은 `backend/app/`, 테스트는 `backend/tests/`에 두며 pytest·mypy·Ruff 설정은 `backend/pyproject.toml`에 있다. 모든 명령은 `backend/`에서 실행한다.

```sh
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv run python -m app
```

- `uv sync --locked`: 커밋된 `uv.lock`만으로 `.venv`를 만든다. lock과 `pyproject.toml`이 어긋나면 실패한다.
- `uv run mypy`: strict, 대상은 `app`과 `tests`다.
- `uv run pytest`: `testpaths`가 `tests`다. 파일만 돌릴 때는 `uv run pytest tests/test_app.py`. 경고는 오류로 처리한다.
- `uv run python -m app`: Uvicorn 단일 worker(reload 없음)로 실행한다. 바인드는 `YARDPILOT_API_HOST`(기본 `127.0.0.1`)와 `YARDPILOT_API_PORT`(기본 `8000`)로 바꾼다. 기본값은 프론트 dev proxy의 `YARDPILOT_API_ORIGIN` 기본값 `http://127.0.0.1:8000`과 같다. 잘못된 값이면 기동하지 않고 종료 코드 1로 끝난다. worker 수를 늘리는 실행 방식은 쓰지 않는다.
- Swagger UI(`/docs`)·ReDoc(`/redoc`)은 외부 CDN 자산을 쓰므로 제공하지 않는다.

의존성을 추가하거나 갱신할 때는 PyPI·공식 문서에서 Python 3.11 지원과 호환 범위를 확인하고 phase 문서에 출처와 날짜를 남긴다.
