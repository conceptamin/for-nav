# 03. `/api/extract` LLM 추출

상태: 대기
의존: 02

## 목표
자유 입력(영어·베트남어·한국어)에서 부위·증상·발생 시점·업무 관련·작업 유형을 뽑는 자리를 키워드 사전에서 LLM으로 바꾼다. 출력은 `vocab.py` 열거값으로 고정하고, LLM이 없거나 실패하면 지금 키워드 사전으로 그대로 동작한다.

## 범위
- 하는 것
  - `rules/extract_llm.py`: 프롬프트(system에 열거값 목록과 "열거값 밖의 값·병명·추측 금지"), 출력 스키마 `Extraction`(이미 `Literal`로 검증됨)
    - 필드 하나가 열거값을 벗어나면 그 필드만 `null`로 버린다. 전체가 JSON이 아니면 `generate`가 재시도한다
  - `routers/worker.py`의 `/api/extract`: `get_llm_client()`가 `None`이거나 `LLMUnavailableError`면 `extract_from_text`로 대체. 이후 `merge_extraction`은 그대로
  - `ExtractResponse`에 선택 필드 `source: "llm" | "keywords"` 추가(기존 필드 변경 없음)
  - `tests/test_extract_llm.py`: `FakeLLMClient`로 정상·열거값 밖·실패 대체 경우, 프론트 버튼 입력이 LLM 추출값보다 우선하는지
  - 픽스처의 자유 입력 전부를 실제 LLM에 한 번 넣어 키워드 결과와 비교한 표를 `## 결과`에 적는다(일치 건수/전체, 어긋난 사례와 어느 쪽이 맞는지)
- 하지 않는 것
  - 응급 키워드 판정 변경(`/api/triage`의 규칙은 그대로 자유 입력에 키워드로 돈다), 프론트 화면 변경, 프롬프트 다국어 분기

## API·파일
- 변경: `POST /api/extract` 응답에 `source` 선택 필드 추가
- 추가: `app/rules/extract_llm.py`, `tests/test_extract_llm.py`
- 수정: `app/routers/worker.py`, `app/schemas.py`, `README.md`(API 표·예시·"나중에 붙일 자리" 표)

## 완료 기준
- [ ] `uv run pytest` 통과. LLM이 꺼진 기본 상태에서 `test_parity.py`의 `extract` 케이스가 그대로 통과한다
- [ ] `FakeLLMClient`가 열거값 밖의 값(`"bodyParts": ["finger"]`)을 주면 그 필드만 비고 나머지는 반영된다
- [ ] `FakeLLMClient`가 두 번 실패하면 응답 `source`가 `keywords`이고 결과가 키워드 사전과 같다
- [ ] 버튼으로 고른 부위·증상이 있으면 LLM 값으로 덮이지 않는다
- [ ] 픽스처 자유 입력 비교표가 `## 결과`에 있다. 오탐 방지 사례(`"ở nhà máy"`, 영어 `painting`)의 LLM 결과가 적혀 있다
- [ ] `README.md`의 `/api/extract` 예시에 `source`가 있다

## 결과

## 메모
- LLM이 키워드보다 나쁘게 나온 사례가 있으면 숨기지 않고 적는다. 그 경우 키워드 결과와 합집합을 쓸지는 사용자가 정한다
- 자유 입력은 로그에 남지 않는다(01). 비교표에도 픽스처 번호만 적고 원문은 옮기지 않는다
