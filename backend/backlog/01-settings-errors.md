# 01. 설정값 분리, 공통 오류 형식, 접근 로그

상태: 완료
의존: 없음

## 목표
`README.md`의 "확인이 필요한 값"(센터 운영 시간, 정보 기준일, 허용 출처)을 코드 상수에서 환경 변수로 빼서 발표 전에 코드를 고치지 않고 바꿀 수 있게 한다. 뒤 항목(LLM, 모델, DB)이 같은 방식으로 설정을 받을 수 있도록 설정 모듈을 하나 두고, 오류 응답 형식과 접근 로그를 요청 본문이 남지 않는 형태로 고정한다.

## 범위
- 하는 것
  - `app/settings.py`: 환경 변수를 한 번 읽어 담는 불변 객체. 새 의존성 없이 `os.environ`으로 읽는다
    - `CENTER_HOURS`(기본 `09:00-18:00`, 평일), `INFO_DATE`(기본 현재 상수), `CORS_ORIGINS`(기본 `http://localhost:5180`, 쉼표 구분)
  - `rules/coverage.py`의 `CENTER_HOURS`, `INFO_DATE` 상수를 설정에서 읽도록 바꾼다. `/api/meta`가 설정값을 돌려준다
  - `.env.example` 커밋, `.env`는 `.gitignore`에 추가. `uv run fastapi dev`가 `.env`를 읽는지 확인하고 아니면 README에 `export` 방법을 적는다
  - 공통 오류 형식: 404·422·500이 모두 `{ "error": { "code": "...", "message": "...", "requestId": "..." } }`로 나간다. `code`는 `NOT_FOUND`, `VALIDATION`, `INTERNAL`
  - 요청마다 `X-Request-Id` 헤더를 붙인다(클라이언트가 보내면 그대로, 없으면 생성)
  - 접근 로그 한 줄: 메서드, 경로, 상태 코드, 소요 ms, request id. 쿼리 문자열·본문·헤더는 남기지 않는다. 예외 로그에도 본문을 넣지 않는다
  - `tests/test_settings.py`, `tests/test_errors.py`
- 하지 않는 것
  - LLM·모델·DB 설정값(각 항목에서 추가), 로그 수집 서비스 연결, 인증

## API·파일
- 변경: 오류 응답 본문 형식(모든 경로). 성공 응답은 바뀌지 않는다
- 추가: `app/settings.py`, `app/errors.py`(예외 핸들러·미들웨어), `.env.example`
- 수정: `app/main.py`, `app/rules/coverage.py`, `README.md`("확인이 필요한 값", "실행", 오류 형식 절 추가)

## 완료 기준
- [x] `cd backend && uv sync && uv run ruff check . && uv run ruff format --check . && uv run pytest` 통과
- [x] `CENTER_HOURS=10:00-17:00 uv run fastapi dev app/main.py` 뒤 `curl /api/meta`에 `10:00`~`17:00`이 나오고, 운영 시간 외 판정(`isAfterHours`)이 그 값을 따른다
- [x] 동기화 테스트(`test_parity.py`)가 기본 설정값에서 그대로 통과한다
- [x] 잘못된 본문으로 `POST /api/triage`를 부르면 422와 위 오류 형식, `X-Request-Id`가 돌아온다
- [x] 테스트에서 본문에 표식 문자열을 넣어 422·500을 일으켰을 때 `caplog`에 그 표식이 없다
- [x] `README.md`에 환경 변수 표와 오류 형식이 있다

## 결과

실행한 명령과 결과
- `uv sync && uv run ruff check . && uv run ruff format --check . && uv run pytest` → 통과, 901 passed(이전 881 + 20: `test_settings.py` 10, `test_errors.py` 10). `test_parity.py` 862건은 기본 설정값에서 그대로 통과
- `CENTER_HOURS=10:00-17:00 uv run fastapi dev app/main.py --port 8765` 뒤 `curl /api/meta` → `"centerHours":{"openHour":10,"closeHour":17,...}`
- `.env`에 `CENTER_HOURS=11:00-17:00`을 넣고 `uv run --env-file .env fastapi dev app/main.py` 뒤 수요일 10:56에 `POST /api/center/cases` → `afterHours: true`, `nextOpenDate`는 당일. 운영 시간 외 판정은 `test_settings.py::test_env_reaches_meta_and_after_hours`가 별도 프로세스(10:00-17:00)에서 09:30·10:00·16:59·17:00 경계로 확인
- 잘못된 본문으로 `POST /api/triage` → `422`, `x-request-id` 헤더, `{"error":{"code":"VALIDATION","message":"요청 형식이 올바르지 않다: body.bodyParts.0, ...","requestId":"<헤더와 같음>"}}`
- 서버 로그는 `GET /api/meta 200 0.3ms request_id=...` 형태 한 줄만 남고, 본문 표식·연락처·쿼리 문자열이 없음을 확인. uvicorn 기본 접근 로그는 나오지 않음

바뀐 API
- 모든 오류 응답 본문이 `{ "error": { "code", "message", "requestId" } }`로 바뀌었다(이전에는 FastAPI 기본 `{ "detail": ... }`). 성공 응답은 그대로
- 모든 응답에 `X-Request-Id` 헤더를 붙이고 CORS `expose_headers`에 넣었다
- `/api/meta`는 같은 형태로 설정값을 돌려준다

추가·수정한 파일
- 추가: `app/settings.py`, `app/errors.py`, `.env.example`, `tests/test_settings.py`, `tests/test_errors.py`
- 수정: `app/main.py`(설정·오류 처리 연결, CORS 출처를 설정에서), `app/rules/coverage.py`(`CENTER_HOURS`·`INFO_DATE`를 설정에서), `.gitignore`(`.env`), `README.md`(폴더 구조, 로그·오류 형식 절, 실행의 환경 변수 표, 확인이 필요한 값)

결정과 이유
- 설정은 시작 시 한 번 읽는 불변 객체(`settings`) 하나로 둔다. 바뀌지 않는 값이므로 `store.py`만 상태를 갖는다는 규칙과 부딪히지 않는다고 봤다. 테스트용으로 `load_settings(env)`를 따로 둔다
- `CENTER_HOURS`는 분이 `00`인 값만 받는다. 프론트 `CenterHours`가 시 단위(`openHour`, `closeHour`)라서, 분을 받으려면 API 계약을 바꿔야 한다. 운영일은 평일로 고정했다(범위가 "평일")
- 설정값이 형식에 맞지 않으면 서버가 시작하지 않는다. 잘못된 운영 시간으로 조용히 뜨는 것보다 낫다고 봤다
- 422 `message`에는 어긋난 필드 위치만 넣는다. Pydantic 오류의 `input`·`msg`에 요청 값이 들어갈 수 있어서다. 경로 안에서 던진 422(`/api/center/stats`의 `days`)도 `VALIDATION`이다
- 범위에 적힌 세 코드 밖의 상태(예: 405)는 `BAD_REQUEST`, 그 밖 5xx는 `INTERNAL`로 둔다. 형식을 모든 오류에 똑같이 맞추려고 더했다
- 클라이언트가 보낸 `X-Request-Id`는 영문·숫자·`._-` 128자 이내일 때만 그대로 쓴다. 이 값은 로그에 그대로 남으므로, 헤더 내용이 로그에 들어가지 않게 하려고 제한했다
- 500은 예외 처리기가 아니라 미들웨어에서 잡아 다시 던지지 않는다. Starlette는 `Exception` 처리기를 쓴 뒤에도 예외를 다시 던지고, 그러면 uvicorn이 예외 메시지(요청 값이 들어갈 수 있음)까지 로그에 남긴다. 우리 로그에는 예외 타입과 코드 위치(파일:줄 함수)만 남긴다
- uvicorn 접근 로그(`uvicorn.access`)는 앱에서 끈다. 쿼리 문자열과 클라이언트 주소를 남기고, `fastapi dev`에는 끄는 옵션이 없다
- 미들웨어를 CORS 안쪽에 두어 오류 응답에도 CORS 헤더가 붙게 했다. 대신 CORS 사전 요청(OPTIONS)은 CORS가 바로 답하므로 접근 로그와 request id가 없다
- `fastapi dev`는 `.env`를 읽지 않는다. `uv run --env-file .env`를 README에 적었고, 이 옵션은 파일이 없으면 실패하므로 `.env`가 없을 때는 기존 명령을 그대로 쓴다

남은 문제
- 프론트 `src/api/`(frontend 항목 7)가 새 오류 형식(`error.code`, `error.requestId`)을 읽어야 한다

## 메모
- 422 형식을 바꾸면 프론트 `src/api/`(frontend 항목 7)가 이 형식을 읽어야 한다. 프론트 전환 전에 끝내는 것이 좋다
- 기관 대표번호(`KCOMWEL`, `NHIS`)는 공개 번호라 상수로 둔다. 센터·울산시 연락처는 확인 전까지 `null` 유지
