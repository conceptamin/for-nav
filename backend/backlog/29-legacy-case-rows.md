# 29. 옛 계약으로 저장된 센터 사례를 읽어 접수함이 끊기지 않게 하기

상태: 완료
의존: 없음(23·26이 바꾼 사례 계약의 뒷정리)

## 목표
운영(www.for-nav.com/center)에서 직원이 로그인한 뒤 접수함이 "서버 연결 안 됨 · 마지막 갱신 없음"으로만 보였다(2026-10-31). SQLite `live_cases`에는 사례 본문이 저장할 때의 계약 그대로 남는데, backlog 23이 `requestType`을 `requestTypes` 배열로 바꾸면서 옛 본문을 읽는 처리를 두지 않았다. 옛 본문이 하나라도 있으면 `GET /api/center/cases` 전체가 `ValidationError`로 500이 되고, 프론트는 이를 연결 끊김으로 보인다. 옛 본문을 지금 계약으로 읽고, 그래도 못 읽는 본문 하나가 접수함 전체를 막지 않게 한다.

## 범위
- 하는 것
  - `app/store_sqlite.py`: 본문을 읽는 함수 하나(`_case_from_body`)로 목록(`all`)과 조회(`get`)가 같이 읽는다
    - 단수 `requestType`만 있으면 `requestTypes: [requestType]`로 읽는다
    - JSON이 아니거나 객체가 아니거나 지금 계약에 맞지 않으면 그 사례만 뺀다(`get`은 `None` → 404). 로그는 `live case skipped id=… error=<예외 이름>` 한 줄이고 본문은 남기지 않는다
  - `tests/test_store.py`: 옛 `requestType` 본문 읽기, 못 읽는 본문 3가지(깨진 JSON, 배열, 필드 빠짐)는 그 사례만 빠지고 다른 live 사례는 남음, 로그에 본문 없음
  - `README.md` 센터 저장소 설명
- 하지 않는 것
  - DB 파일의 본문을 고쳐 쓰는 이전 작업(migration). 읽을 때 바꾸므로 운영 DB를 손대지 않아도 된다
  - 메모리 저장소. 재시작하면 비므로 옛 본문이 없다
  - API 계약 변경. 응답 필드·상태 코드는 그대로다

## API·파일
- 경로 변경 없음
- 수정: `app/store_sqlite.py`, `tests/test_store.py`, `README.md`

## 완료 기준
- [x] `uv run ruff check . && uv run ruff format --check .` 통과
- [x] `uv run pytest` 통과(위 테스트 포함)
- [x] `requestType` 본문이 있는 DB로 센터 로그인 뒤 `GET /api/center/cases`가 500이 아니다

## 결과
- 재현(고치기 전, origin/main 467d45c): `CENTER_AUTH=email MAIL_PROVIDER=console DB_PATH=…`로 띄워 로그인 → `GET /api/center/cases` 200. 같은 DB에 `requestType` 본문 한 행을 넣자 500, 로그 `unhandled ValidationError … store_sqlite.py:115 _live < list_cases`
- 고친 뒤 같은 DB를 `SqliteStore`로 열면 `all()` 25건, `get("C-2001").request_types == ["interpret"]`
- `uv run ruff check . && uv run ruff format --check .` → All checks passed, 89 files already formatted
- `uv run pytest` → 2873 passed(새 테스트 4개, main 4423ec5 위에서)
- 번호: 처음 28로 썼으나 main에 채팅 읽음 표시(28)가 먼저 들어와 29로 옮겼다
- 결정: 못 읽는 본문은 500 대신 건너뛴다. 사례 하나 때문에 직원이 다른 사례를 모두 못 보는 것이 더 나쁘고, 건너뛴 사실은 id와 함께 로그에 남는다

## 메모
- 운영에서 원인 확정은 맥미니 `pm2 logs for-nav`의 `ValidationError … _live` 줄로 한다(이 작업은 로컬 재현으로 확인했다). 배포 뒤에는 같은 자리에 `live case skipped`가 찍히면 옛 계약 변환으로도 못 읽은 본문이 있다는 뜻이다
- 사례 계약을 다시 바꿀 때는 `_case_from_body`에 옛 모양 변환을 더하고 `test_store.py`에 옛 본문 테스트를 더한다
