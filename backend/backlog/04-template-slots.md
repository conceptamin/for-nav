# 04. 접수 도우미·리포트 템플릿 슬롯 LLM 채우기

상태: 완료
의존: 02

## 목표
접수 창구 화면, 전화 스크립트, 의료진 리포트의 고정 문장은 그대로 두고, 자유 입력을 한국어 한 문장으로 요약하는 **슬롯만** LLM이 채운다. 금지어(병명·진단 표현) 검사와 길이 제한을 통과하지 못하면 지금 템플릿 문장을 그대로 쓴다.

## 범위
- 하는 것
  - 슬롯 정의: `templates/`에서 자유 입력(`freeText`)을 그대로 끼우는 자리를 찾아 목록으로 만든다(접수 창구 "상황" 줄, 전화 스크립트 상황 설명, 의료진 리포트 `note` 행). 그 외 문장은 건드리지 않는다
  - `templates/llm_slots.py`: 프롬프트(system: "증상을 사실대로 한국어 한 문장, 병명·원인 추측·치료 권고 금지, 60자 이내"), 출력 스키마 `{ "ko": str }`
  - 검사 `templates/guard.py`: 금지어 목록(병명·"~로 보임"·"~일 가능성" 같은 추측 표현), 길이, 한국어 여부. 하나라도 걸리면 템플릿 원문 사용
  - `/api/visit-helper`, `/api/report/clinician` 응답에 선택 필드 `llmSlots: ["desk.situation", ...]`(LLM으로 채운 슬롯 이름 목록, 없으면 빈 배열)
  - `tests/test_template_slots.py`: `FakeLLMClient`로 채움·금지어 차단·실패 대체, 고정 문장이 바뀌지 않음
- 하지 않는 것
  - 고정 문장 생성·재작성, 센터 요약(05에서 번역과 함께), 베트남어·영어 문장 생성(모국어 줄은 기존 템플릿 유지)

## API·파일
- 변경: `POST /api/visit-helper`, `POST /api/report/clinician` 응답에 `llmSlots` 선택 필드 추가
- 추가: `app/templates/llm_slots.py`, `app/templates/guard.py`, `tests/test_template_slots.py`
- 수정: `app/routers/worker.py`, `app/schemas.py`, `README.md`

## 완료 기준
- [x] `uv run pytest` 통과. LLM이 꺼진 기본 상태에서 `test_parity.py`의 템플릿 케이스가 그대로 통과한다
- [x] 슬롯 목록이 `## 결과`에 있고, 슬롯 밖 문장은 LLM 켜짐·꺼짐에서 바이트 단위로 같다(테스트로 확인)
- [x] 금지어 검사 테스트: 병명이 든 출력, 60자 초과, 한국어가 아닌 출력이 각각 템플릿 원문으로 대체된다
- [x] `FakeLLMClient` 실패 시 응답이 LLM 꺼짐과 같고 `llmSlots`가 빈 배열이다
- [x] 픽스처 자유 입력 전부로 실제 LLM 요약을 한 번 돌려 금지어에 걸린 건수/전체를 `## 결과`에 적는다

## 결과

### 슬롯 목록(문서 범위에서 바꾼 점)
범위에 적힌 세 자리 중 지금 템플릿이 `freeText`를 끼우는 곳은 의료진 리포트 `note` 하나뿐이었다(프론트·서버 모두). 접수 창구·전화 스크립트에는 "상황" 줄이 없고, 증상 줄은 부위·증상 버튼 값으로만 만든다. 사용자와 정해 아래처럼 바꿨다.

| 슬롯 | 자리 | 값 |
|---|---|---|
| `desk.situation` | `desk.lines` 증상 줄 바로 뒤 | `ko`: LLM 한국어 요약, `native`: 근로자 원문(한국어 사용자는 `ko`와 같음), `pron`: `""` |
| `call.situation` | `call.lines` 증상 줄 바로 뒤 | 같은 줄 |

- 의료진 리포트 `note`는 04에서 채우지 않는다. 비한국어 원문을 한국어로 요약하는 것은 번역과 같아서, 역번역 검사(05) 없이 의료진에게 가면 안 되기 때문이다. `/api/report/clinician`의 `llmSlots`는 계약만 만들고 지금은 항상 `[]`다.
- 상황 줄은 LLM이 성공하고 guard를 통과했을 때만 **새로 끼운다.** 기존 줄은 그대로라 LLM 꺼짐 상태 출력은 프론트 템플릿과 같다.

### 결정
- 호출 수: 요약 한 번(LLM 1회)을 두 슬롯에 함께 쓴다. 두 줄이 같은 내용이라 따로 부를 이유가 없다.
- 템플릿 빌더는 결정적으로 둔다. `build_desk_sheet`·`build_call_script`는 선택 인자 `situation: Line | None`만 받고, LLM 호출은 `templates/llm_slots.py`의 `build_visit_helper`가 한다.
- `llmSlots`는 `absent_if_none` 선택 필드다. 빌더는 비워 두어 `test_parity.py`가 프론트 결과와 그대로 비교하고, 라우터가 목록(없으면 `[]`)을 넣는다.
- guard(`templates/guard.py`)는 이유만 돌려준다(`empty`·`multiline`·`too_long`·`not_korean`·`forbidden`). 로그에는 이유만 남고 문장은 남지 않는다. 05 번역 결과에도 쓴다.
- 금지어는 병명(골절·염좌·염증 등), 추측(`로 보임`·`것 같`·`가능성`·`의심` 등), 치료 권고(`치료`·`처방`·`하세요` 등) 세 묶음이다. 증상 어휘 15개 × 부위 13개 사실 문장이 걸리지 않는지 테스트한다.
- 요약 줄의 발음 표기(`pron`)는 만들지 않는다. 한국어 사용자가 아니면 전화 스크립트에서 소리 내어 읽기 어렵다. 필요하면 별도 항목으로 정한다.

### 실행
- `uv run ruff check . && uv run ruff format --check .` → 통과
- `uv run pytest` → 2753 passed. 새 테스트 `tests/test_template_slots.py` 187개, LLM 꺼짐 상태의 `test_parity.py` 템플릿 케이스(desk·call·clinician 1200개) 그대로 통과
- 슬롯 밖 바이트 동일: `test_outside_slot_is_byte_identical`(API), `test_outside_slot_is_byte_identical_for_fixtures`(parity desk 100건, 20개 언어)
- guard 대체: 병명·추측·권고·60자 초과·베트남어·영어·빈 문자열·두 줄 출력이 각각 LLM 꺼짐 응답과 같고 `llmSlots == []`
- 실패 대체: 공급자 오류 + 형식 오류 2회 → LLM 꺼짐 응답과 같고 `llmSlots == []`
- 실제 LLM: `uv run --env-file .env python scripts/slots_check.py` (`claude-haiku-5-5`) → 픽스처 자유 입력 28건 중 **guard 거부 0/28**, 호출 실패 0, 요약 길이 8~34자
  - 눈으로 10건 확인: 사실만 옮겼고, 원문의 원인 추측("có thể do sơn", 페인트 때문일 수도)은 요약에서 빠졌다. "đang mài"(연마 중)를 "작업 중 연마하다가"로 옮긴 것처럼 원문보다 조금 더 단정하는 경우가 있다

### 바뀐 API
- `POST /api/visit-helper` 응답에 `llmSlots: string[]` 추가. LLM이 채우면 `desk.lines`·`call.lines`에 상황 줄 하나씩 더해진다
- `POST /api/report/clinician` 응답에 `llmSlots: []` 추가

### 남은 문제
- guard는 금지어·형식만 본다. 요약이 원문에 없는 사실을 더하는지는 검사하지 않는다(05의 역번역 검사 방식을 요약에도 쓸지는 05 결과를 보고 정한다)
- 프론트 화면에 상황 줄이 `pron` 없이 보일 때의 표시는 프론트 API 모드에서 확인해야 한다

## 메모
- 금지어 목록은 `README.md` "진단 표현 금지" 규칙의 구체화다. 목록은 코드 상수로 두고 추가할 때 테스트도 같이 둔다
- 슬롯 하나당 LLM 호출 1회면 리포트에서 호출이 여러 번 생긴다. 한 번에 모든 슬롯을 채우는 출력 스키마로 묶을지 구현하면서 정하고 결과에 적는다
