# 01. 설정값 분리, 공통 오류 형식, 접근 로그

상태: 대기
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
- [ ] `cd backend && uv sync && uv run ruff check . && uv run ruff format --check . && uv run pytest` 통과
- [ ] `CENTER_HOURS=10:00-17:00 uv run fastapi dev app/main.py` 뒤 `curl /api/meta`에 `10:00`~`17:00`이 나오고, 운영 시간 외 판정(`isAfterHours`)이 그 값을 따른다
- [ ] 동기화 테스트(`test_parity.py`)가 기본 설정값에서 그대로 통과한다
- [ ] 잘못된 본문으로 `POST /api/triage`를 부르면 422와 위 오류 형식, `X-Request-Id`가 돌아온다
- [ ] 테스트에서 본문에 표식 문자열을 넣어 422·500을 일으켰을 때 `caplog`에 그 표식이 없다
- [ ] `README.md`에 환경 변수 표와 오류 형식이 있다

## 결과

## 메모
- 422 형식을 바꾸면 프론트 `src/api/`(frontend 항목 7)가 이 형식을 읽어야 한다. 프론트 전환 전에 끝내는 것이 좋다
- 기관 대표번호(`KCOMWEL`, `NHIS`)는 공개 번호라 상수로 둔다. 센터·울산시 연락처는 확인 전까지 `null` 유지
