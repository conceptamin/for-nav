# 백엔드 작업 규칙

루트 `CLAUDE.md`, [공통 계약](../docs/api-contract.md), [백엔드 기획서](docs/proposal.md)를 먼저 읽는다. phase 문서는 `backend/docs/phase-XX.md`에 쓴다. 지정된 phase의 범위만 구현하고 검증 결과를 같은 문서에 남긴다. 다른 영역에 의존하면 그 영역의 phase 문서 경로를 적는다. 다음 작업은 [phase-02](docs/phase-02.md)다.

## 범위와 스택

`backend/`를 담당한다. Python 3.11, FastAPI/Pydantic, 단일 worker Uvicorn. 환경·의존성은 uv(`pyproject.toml`, `uv.lock`)로 관리한다. 테스트는 pytest·HTTPX·TestClient, 품질은 Ruff·mypy strict다. DB는 쓰지 않는다(서버 미저장).

맡는 일: API 엔드포인트, 응급 키워드 규칙, 응급 감지 모델 불러오기·추론, LLM을 통한 작업 맥락 추출과 요약 카드 생성, 비용 경로 규칙, 증상→진료과 대응 표, 산재 안내 정적 콘텐츠, 병원 데이터(mock 또는 공공 API). 모델 학습·테스트셋·평가는 `modeling/`의 책임이다.

## 불변 조건

- 응급 판단은 키워드 규칙 OR 모델이다. LLM 출력으로 응급을 판단하거나 뒤집지 않는다. LLM이 실패·시간 초과해도 `/triage`는 응급 결과를 200으로 돌려준다.
- 비용 경로와 진료과는 순수 함수 규칙으로 결정한다. LLM·네트워크·시각에 의존하지 않는다.
- 요청 본문·증상 텍스트·LLM 프롬프트와 응답을 로그나 파일에 남기지 않는다. 로그에는 경로, 상태 코드, 소요 시간, `request_id`만 남긴다.
- `/summary`는 `consent`가 참일 때만 LLM을 호출한다. `include`에 없는 필드는 LLM 입력에서 뺀다.
- LLM 호출은 하나의 인터페이스 뒤에 둔다. 테스트는 가짜 구현을 쓰고 외부 LLM을 호출하지 않는다. API 키는 환경 변수로만 받고 응답·로그·프론트 번들에 넣지 않는다.
- 확인되지 않은 연락처·제도 조건은 `verified: false` 또는 `null`로 둔다. 번호나 조건을 지어내지 않는다.
- 응급 감지 모델 파일은 `modeling/`이 내보낸 형식만 읽는다. pickle처럼 불러올 때 코드를 실행하는 형식은 쓰지 않는다. 모델 버전을 응답의 `model_version`에 넣는다.
- 비자·체류 자격, 이름·소속·사업장명 필드를 만들지 않는다.

## 검증 기준

비용 경로는 `fixtures/route-cases/`의 정답 사례 전부와 계약 4장의 결정 표 모든 줄을 테스트한다. 응급 규칙은 응급·비응급 예시 문장으로, `/triage`는 LLM 실패 시 응급 결과 유지와 `context_status`를, `/summary`는 동의 없음 422와 제외 항목이 가짜 LLM 입력·응답에 없음을 검증한다. 로그에 요청 본문이 남지 않는지도 테스트한다.

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
- `uv run python -m app`: Uvicorn 단일 worker(reload 없음)로 실행한다. 바인드는 `YARDPILOT_API_HOST`(기본 `127.0.0.1`)와 `YARDPILOT_API_PORT`(기본 `8000`)로 바꾼다. phase-02에서 `FORNAV_API_HOST`·`FORNAV_API_PORT`로 바꾼다. 기본값은 프론트 dev proxy 기본값 `http://127.0.0.1:8000`과 같다. 잘못된 값이면 기동하지 않고 종료 코드 1로 끝난다.
- Swagger UI(`/docs`)·ReDoc(`/redoc`)은 외부 CDN 자산을 쓰므로 제공하지 않는다.

의존성을 추가하거나 갱신할 때는 PyPI·공식 문서에서 Python 3.11 지원과 호환 범위를 확인하고 phase 문서에 출처와 날짜를 남긴다.
