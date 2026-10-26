# 04. 접수 도우미·리포트 템플릿 슬롯 LLM 채우기

상태: 대기
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
- [ ] `uv run pytest` 통과. LLM이 꺼진 기본 상태에서 `test_parity.py`의 템플릿 케이스가 그대로 통과한다
- [ ] 슬롯 목록이 `## 결과`에 있고, 슬롯 밖 문장은 LLM 켜짐·꺼짐에서 바이트 단위로 같다(테스트로 확인)
- [ ] 금지어 검사 테스트: 병명이 든 출력, 60자 초과, 한국어가 아닌 출력이 각각 템플릿 원문으로 대체된다
- [ ] `FakeLLMClient` 실패 시 응답이 LLM 꺼짐과 같고 `llmSlots`가 빈 배열이다
- [ ] 픽스처 자유 입력 전부로 실제 LLM 요약을 한 번 돌려 금지어에 걸린 건수/전체를 `## 결과`에 적는다

## 결과

## 메모
- 금지어 목록은 `README.md` "진단 표현 금지" 규칙의 구체화다. 목록은 코드 상수로 두고 추가할 때 테스트도 같이 둔다
- 슬롯 하나당 LLM 호출 1회면 리포트에서 호출이 여러 번 생긴다. 한 번에 모든 슬롯을 채우는 출력 스키마로 묶을지 구현하면서 정하고 결과에 적는다
