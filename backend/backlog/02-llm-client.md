# 02. LLM 호출 인터페이스

상태: 대기
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
- [ ] `uv run pytest`가 네트워크 없이, `LLM_API_KEY` 없이 통과한다
- [ ] `test_llm.py`: 정상 출력 1회 호출, 스키마 불일치·JSON 아님·공급자 오류·시간 초과 각각 재시도 후 성공, 2회 모두 실패 시 `LLMUnavailableError`, 실패 로그에 응답 원문 표식이 없음
- [ ] `LLM_API_KEY`가 비어 있으면 `get_llm_client()`가 `None`이고 서버가 정상 기동한다
- [ ] `uv run python scripts/llm_smoke.py`를 실제 키로 한 번 돌린 결과(모델 이름, 소요 시간, 스키마 통과 여부)가 `## 결과`에 있다. 응답 원문은 적지 않는다
- [ ] `README.md`에 LLM 환경 변수와 "키 없으면 템플릿으로 동작" 설명이 있다

## 결과

## 메모
- **공급자와 모델은 저장소 어디에도 정해져 있지 않다.** 시작 전에 사용자에게 확인하고 결정을 여기에 적는다. SDK 의존성은 그 뒤에 추가한다
- 이전에 지운 `backend/app/llm.py`(커밋 `83d67d1`)의 설계를 그대로 다시 쓴다. 프로토콜·재시도·원문 미기록 테스트가 이미 있었다
- 프롬프트의 system 부분은 코드에 상수로 두고, 사용자 자유 입력은 user 부분에만 넣는다. 자유 입력 안의 지시문을 따르지 않도록 system에 명시한다
