# 15. uvicorn 접근 로그 끄기 바로잡기

상태: 완료
의존: 없음

## 목표
`uv run fastapi run app/main.py`(맥미니 pm2 `ecosystem.config.cjs`도 같은 명령)로 띄우면 uvicorn 기본 접근 로그가 그대로 찍힌다. 이 줄에는 클라이언트 주소와 쿼리 문자열이 들어가므로 `README.md` "공통 규칙 → 로그"(메서드·경로·상태 코드·ms·request id만)에 어긋난다. 어떤 방법으로 띄우든 uvicorn 접근 줄이 나오지 않게 한다.

```text
INFO:     127.0.0.1:51324 - "GET /api/center/cases?since=MARKERQ HTTP/1.1" 422 Unprocessable Entity
2026-10-30 20:57:40,454 INFO app.access GET /api/center/cases 422 3.2ms request_id=782c...
```

원인: `errors.py`의 `_setup_logging()`은 앱을 불러올 때 `uvicorn.access` 로거를 `disabled = True`로 끈다. 그 뒤 uvicorn이 서버 시작 때 로그 설정(`logging.config.dictConfig`)을 적용하면서 설정에 이름이 있는 로거를 `disabled = False`로 되돌린다(Python 3.12 `logging/config.py` `configure_logger`). 로거에 단 필터는 이때 지워지지 않는다.

## 범위
- 하는 것
  - `uvicorn.access` 로거에 모든 레코드를 버리는 필터를 달고, 되돌려지는 `disabled = True`는 뺀다
  - 테스트: 앱을 불러온 뒤 uvicorn 로그 설정을 실제로 적용해도 `uvicorn.access` 줄이 핸들러에 닿지 않는지 확인
- 하지 않는 것
  - 실행 명령에 `--no-access-log`를 붙이는 방식. `fastapi dev`·`fastapi run`·`uvicorn`·pm2 명령마다 붙여야 하고, 하나라도 빠지면 다시 샌다. 필터는 앱 안에 있어 실행 방법과 관계없이 막고 테스트로 지킬 수 있다
  - `app.access` 한 줄의 형식 변경, uvicorn 시작·종료 줄(`uvicorn.error`) 정리

## API·파일
API 변경 없음.
- `app/errors.py`: `uvicorn.access` 필터, `_setup_logging()`
- `tests/test_errors.py`: uvicorn 로그 설정 적용 후 접근 줄이 버려지는지 테스트

## 완료 기준
- [x] `uv run ruff check . && uv run ruff format --check .` 통과
- [x] `uv run pytest` 통과(새 테스트 포함)
- [x] `uv run fastapi run app/main.py`로 띄우고 `curl "/api/center/cases?since=MARKERQ"`, `curl /api/health` → 출력에 `app.access` 줄만 있고 `HTTP/1.1"`(uvicorn 접근 줄)·`MARKERQ`·`127.0.0.1:`이 없다

## 결과
- `uv run ruff check . && uv run ruff format --check .` → `All checks passed!`, `63 files already formatted`
- `uv run pytest` → 2865 passed. 새 테스트 `test_uvicorn_access_log_dropped_after_server_log_config`는 고치기 전 `errors.py`로 돌리면 실패한다
- 고치기 전 `uv run fastapi run app/main.py --port 8793` → 요청마다 `INFO:     127.0.0.1:51324 - "GET /api/center/cases?since=MARKERQ HTTP/1.1" 422 …`가 `app.access` 줄과 함께 찍혔다
- 고친 뒤 같은 명령 → `app.access GET /api/center/cases 422 3.4ms request_id=…` 같은 줄만 남고, 출력에서 `HTTP/1.1"`·`MARKERQ`·`127.0.0.1:` 0건
- API 변경 없음
- 결정: `uvicorn.access`에 모든 레코드를 버리는 `_DropAccessLines` 필터를 단다. 테스트는 fastapi-cli가 넘기는 uvicorn 로그 설정(`get_uvicorn_log_config()`)을 실제로 `dictConfig`로 적용한 뒤 접근 줄을 남겨 핸들러에 닿지 않는지 본다. 적용 뒤 `disabled`가 `False`로 돌아온 것도 확인해, 필터가 실제로 막는 장치임을 테스트가 보여 준다. uvicorn 로거 상태는 테스트 끝에 되돌린다

## 메모
- 같은 원인으로 `uvicorn.error`의 WebSocket `[accepted]` 줄은 backlog 14(PR 98)에서 `_DropWebSocketLines` 필터로 막았다. 두 PR이 `_setup_logging()`의 같은 자리를 고치므로 나중에 병합하는 쪽에서 충돌을 푼다
