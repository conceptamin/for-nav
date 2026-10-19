# 백엔드 작업 규칙

루트 `CLAUDE.md`, `docs/HARNESS.md`, `shipyard-api-contract.md`, `shipyard-backend-proposal.md`를 먼저 읽는다. 작업 원장은 `backlog/backend/` 아래 사용자가 작성·지정한 phase Markdown 문서다. 다른 영역의 작업은 해당 영역 백로그에서 관리하고 의존 문서 경로로 연결한다. `backlog/backend.json`은 참고 초안이며 JSON 상태 갱신·CLI 실행은 필수가 아니다. 의존 작업 완료 후 착수하고 검증 증거를 남긴다. 현재 앱 코드와 실행 명령은 없다. 해당 영역의 환경 구성 phase에서 실제 검증 명령을 구성한다.

## 범위와 스택

`backend/`와 향후 루트 `simulator/`를 담당한다. `simulator/` 작업 시 루트 규칙이 이 문서를 필수 읽기 자료로 지정한다. Python 3.11, FastAPI/Pydantic, 단일 worker Uvicorn, NetworkX DiGraph, SQLite/SQLAlchemy/Alembic을 기준으로 한다. Python 환경·의존성은 uv(`pyproject.toml`, `uv.lock`)로 관리한다. pytest·HTTPX·TestClient·Ruff·mypy를 구현 단계에서 구성한다. 차량 모델과 온라인 학습은 모델링 레인 `agents/`, `training/`의 책임이다.

## 불변 조건

- 단일 Coordinator와 직렬화된 DB 쓰기로 결정한다. 예약·안내·이벤트를 한 트랜잭션에 저장하고 commit 이후 방송한다. 활성 소유자는 하나다.
- OCCUPIED는 실행·차량·구간·활성 토큰이 일치하는 실제 EXIT로만 해제한다. TTL·예측·ACK는 해제 증거가 아니다. 미예약 진입·확인 불가·복구 중 상태는 UNKNOWN이다.
- 우선순위 전에 점유·대기 공간·통행 제약·신선도를 확인한다. 현재 점유를 우선순위로 뒤집지 않는다.
- epoch·seq·지도·모델 버전·유한값·시각을 검사한다. 최신 위치와 유실되면 안 되는 ENTER/EXIT 처리를 분리한다.
- 서버가 역할·차량 범위·Origin을 검사한다. 멱등 키 본문 불일치와 버전 충돌은 409다. 인증 토큰을 로그에 남기지 않는다.
- 서버 복구는 실행 PAUSED/복구 필요, 예약 UNKNOWN으로 시작한다. 확인 없이 통행을 재허용하지 않는다.
- 시뮬레이터는 단일 활성 실행·고정 seed를 유지한다. 벽시계 heartbeat와 배속되는 sim_time_s를 분리한다. 모델 오차 비교와 제어 효과 비교를 분리한다.

## 검증 기준

순수 도메인 테스트로 경로 제약·동시 예약·중복 ENTER·늦거나 위조된 EXIT·미이행·구간 내부 정지·대기 공간 불가를 검증한다. API 권한·잘못된 수치·멱등성, DB commit 실패, 스냅샷 구독 경쟁, 느린 클라이언트, 재시작을 통합 검증한다. 실제 명령 구성 후 Ruff·mypy·pytest 결과를 남긴다. 5대 수신→안내 p95 500ms는 측정 목표이며 현장 안전 성능 보장이 아니다.
