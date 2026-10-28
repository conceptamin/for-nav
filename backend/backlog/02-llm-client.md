# 02. LLM 호출 인터페이스

상태: 완료
의존: 01

## 목표
추출·템플릿·번역 항목(03~05)이 공통으로 쓸 LLM 호출 계층을 만든다. 시간 제한과 재시도, JSON 스키마 검증, 원문 미기록을 여기서 한 번만 구현해 각 기능은 "프롬프트와 출력 스키마"만 정하면 되게 한다. 키가 없으면 LLM 없이 동작해야 한다.

## 범위
- 하는 것
  - `app/llm.py`: `LLMClient` 프로토콜(`complete(prompt) -> str`), `LLMPrompt(system, user)`, `generate(client, prompt, output_type, timeout_s, attempts)`
    - 호출마다 `asyncio.timeout`, 실패·스키마 불일치 시 재시도 1회, 그래도 실패면 `LLMUnavailableError`
    - 로그에는 시도 횟수와 예외 종류만 남긴다. 프롬프트·응답 원문은 로그·예외 메시지·`__context__`에 들어가지 않는다
  - 공급자 어댑터 하나(`app/llm_providers/<provider>.py`): 공급자 SDK 호출을 `LLMClient`로 감싼다. JSON 출력 강제 옵션이 있으면 쓴다
  - `app/settings.py`에 `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_TIMEOUT_S`(기본 10), `LLM_ATTEMPTS`(기본 2) 추가. `get_llm_client()`는 키가 비면 `None`을 돌려주고, 부르는 쪽은 `None`이면 LLM 자리를 건너뛴다
  - `tests/fakes.py`의 `FakeLLMClient`(응답 목록을 순서대로 돌려주고 받은 프롬프트를 기록, 예외·지연도 흉내냄), `tests/test_llm.py`
  - 공급자 호출을 한 번 눈으로 확인하는 명령 `scripts/llm_smoke.py`(CI에서 돌지 않음)
- 하지 않는 것
  - 실제 기능 프롬프트(03~05), 스트리밍, 비용·토큰 집계, 공급자 둘 이상 동시 지원

## API·파일
- 변경되는 API 없음
- 추가: `app/llm.py`, `app/llm_providers/__init__.py`, `app/llm_providers/<provider>.py`, `scripts/llm_smoke.py`, `tests/fakes.py`, `tests/test_llm.py`
- 수정: `app/settings.py`, `.env.example`, `pyproject.toml`(공급자 SDK 1개), `README.md`(환경 변수 표)

## 완료 기준
- [x] `uv run pytest`가 네트워크 없이, `LLM_API_KEY` 없이 통과한다
- [x] `test_llm.py`: 정상 출력 1회 호출, 스키마 불일치·JSON 아님·공급자 오류·시간 초과 각각 재시도 후 성공, 2회 모두 실패 시 `LLMUnavailableError`, 실패 로그에 응답 원문 표식이 없음
- [x] `LLM_API_KEY`가 비어 있으면 `get_llm_client()`가 `None`이고 서버가 정상 기동한다
- [x] `uv run python scripts/llm_smoke.py`를 실제 키로 한 번 돌린 결과(모델 이름, 소요 시간, 스키마 통과 여부)가 `## 결과`에 있다. 응답 원문은 적지 않는다
- [x] `README.md`에 LLM 환경 변수와 "키 없으면 템플릿으로 동작" 설명이 있다

## 결과

실행한 명령 (`backend/`, `LLM_API_KEY`·`ANTHROPIC_API_KEY` 없는 환경)

```sh
uv sync
uv run ruff check .                                   # All checks passed!
uv run ruff format --check .                          # 41 files already formatted
env -u LLM_API_KEY -u ANTHROPIC_API_KEY uv run pytest # 925 passed
uv run python scripts/llm_smoke.py                    # 키 없음 → "LLM 없이 동작한다", exit 1
LLM_API_KEY=<가짜 키> uv run python scripts/llm_smoke.py
# llm attempt=1/2 failed=LLMError/AuthenticationError
# llm attempt=2/2 failed=LLMError/AuthenticationError
# schema=fail elapsed=0.54s  (실패 경로에서도 원문 없이 예외 종류만 찍힘)
```

- 실제 키 확인(2026-10-28, 사용자가 실행): `uv run --env-file .env python scripts/llm_smoke.py` → `provider=anthropic model=claude-haiku-5-5 timeout_s=10.0 attempts=2`, `schema=ok elapsed=2.03s`, 합성 입력의 언어 판정이 기대값과 같음. 응답 원문은 적지 않는다

바뀐 API: 없음

추가·수정 파일
- 추가: `app/llm.py`, `app/llm_providers/__init__.py`, `app/llm_providers/anthropic.py`, `scripts/llm_smoke.py`, `tests/fakes.py`, `tests/test_llm.py`
- 수정: `app/settings.py`(LLM 설정 5개, `get_llm_client()`), `tests/test_settings.py`, `.env.example`, `pyproject.toml`·`uv.lock`(`anthropic>=2.3.0`), `README.md`(기술 스택, 폴더 구조, 환경 변수 표, "LLM" 절)

테스트 (`test_llm.py` 14개, `test_settings.py` +17개)
- `generate()`: 정상 출력 1회 호출·스키마 전달, 스키마 불일치·JSON 아님·공급자 오류·시간 초과 각각 재시도 후 성공, 2회 실패 시 `LLMUnavailableError`(3번째 호출 없음, `__context__`·`__cause__` 없음), 실패 로그에 원문 표식 없음, 로그 형식 `failed=LLMError/RateLimitError`
- 어댑터(가짜 전송 `httpx2.MockTransport`): 요청에 system·user·`output_config.format`(json_schema, `additionalProperties: false`)이 들어감, 429·500·refusal·max_tokens·연결 오류가 원문 없는 `LLMError`가 되고 SDK는 한 번만 부름
- 설정: 기본값, 환경 변수 읽기, 잘못된 값 거절(공급자·모델·시간 제한·시도 횟수), `repr`에 키 없음, 키가 비면 `get_llm_client()`가 `None`, `LLM_*`·`ANTHROPIC_*`를 지운 프로세스에서 서버 기동·`/api/health` 200

결정 사항
- **공급자·모델: Anthropic, `claude-haiku-5-5`**(사용자 확인). 추출·슬롯 채우기·짧은 번역이라 빠르고 싼 쪽을 기본으로 두고 `LLM_MODEL`로 바꾼다. SDK는 `anthropic` 하나.
- **`complete(prompt, *, output_schema)`**: 범위의 `complete(prompt)`에 출력 스키마 키워드 인자를 더했다. JSON 출력 강제(`output_config.format`)를 쓰려면 어댑터가 스키마를 알아야 하기 때문이다. `generate()`가 `output_type.model_json_schema()`를 넘기고, 어댑터가 SDK의 `transform_schema`로 공급자 형식에 맞춘다. 받은 출력은 `generate()`가 같은 Pydantic 모델로 다시 검증한다. `LLMPrompt(system, user)`는 그대로다.
- **SDK 재시도 끔(`max_retries=0`)**: 켜 두면 한 번의 시간 제한 안에서 SDK가 몰래 다시 불러 시도 횟수가 `LLM_ATTEMPTS`와 달라진다. 재시도는 `generate()` 한 곳에서만 한다.
- **`LLMError(kind)`**: SDK 예외는 메시지를 버리고 예외 이름(`RateLimitError` 등)만 `kind`에 담아 `from None`으로 올린다. 로그의 "예외 종류"를 `LLMError/<kind>`로 남겨 발표장에서 키 오류·속도 제한·시간 초과를 구분할 수 있게 했다. `stop_reason`이 `end_turn`이 아니면(refusal, max_tokens) `LLMError`다.
- **effort `low`, `max_tokens` 4096**: 짧고 형식이 정해진 작업이라 지연을 줄인다. Haiku 5.5는 사고(thinking)가 기본으로 켜져 있고 그 토큰도 `max_tokens`에 들어가므로 넉넉히 둔다. 응답의 첫 text 블록만 읽는다.
- **`LLMClient.aclose()`**: 서버가 연결을 닫을 수 있도록 프로토콜에 더했다. `get_llm_client()`는 부를 때마다 새 클라이언트를 만든다(모듈 수준 캐시를 두지 않는 규칙). 서버에서 한 번 만들어 두는 것은 03에서 붙일 때 정한다(메모 참고).
- `Settings.llm_api_key`는 `repr=False`로 둬 설정 객체가 로그·오류에 찍혀도 키가 나오지 않는다. 키가 비면 `ANTHROPIC_API_KEY`·로그인 프로필이 있어도 클라이언트를 만들지 않는다(SDK 기본 자격 증명 탐색을 타지 않음).

남은 문제
- 없음. 서버에서 클라이언트를 한 번 만들어 두는 일은 03에서 한다(메모)

## 메모
- 03에서 LLM을 처음 붙일 때 `get_llm_client()`를 FastAPI lifespan에서 한 번 불러 `app.state`에 두고 종료 시 `aclose()`한다. 요청마다 만들면 연결이 쌓인다.
- **공급자와 모델은 저장소 어디에도 정해져 있지 않다.** 시작 전에 사용자에게 확인하고 결정을 여기에 적는다. SDK 의존성은 그 뒤에 추가한다
- 이전에 지운 `backend/app/llm.py`(커밋 `83d67d1`)의 설계를 그대로 다시 쓴다. 프로토콜·재시도·원문 미기록 테스트가 이미 있었다
- 프롬프트의 system 부분은 코드에 상수로 두고, 사용자 자유 입력은 user 부분에만 넣는다. 자유 입력 안의 지시문을 따르지 않도록 system에 명시한다
