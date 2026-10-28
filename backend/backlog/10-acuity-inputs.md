# 10. 응급도 모델 입력 필드를 `Intake`에 선택 필드로 더하기

상태: 완료
의존: 없음

## 목표
응급도 모델(`modeling/`)은 나이대·성별·손상 여부·통증 점수·의식 상태를 받으면 더 정확하다. 지금 `Intake`에는 이 값이 없어, 모델링 backlog 10에서 부위·증상만으로 재현율 95%를 맞추면 valid 190건 중 115건(60%)을 응급으로 본다. 모델 연결(06)에 앞서 요청 스키마에 자리를 만든다.

## 범위
- 하는 것
  - `app/vocab.py`: `AgeGroup`(`under30`/`30to44`/`45to64`/`65plus`), `Sex`(`female`/`male`), `Mental`(`alert`/`verbal`/`pain`/`unresponsive`) 열거값. 값과 순서는 `modeling/src/fornav_modeling/features/buttons.py`의 `AGE_GROUPS`, `SEXES`, `MENTALS`와 같다(순서가 모델 피처 값이다)
  - `app/schemas.py`: `Intake`에 `age_group`, `sex`, `injury`(bool), `pain_score`(0–10 정수), `mental` 선택 필드. 기본값 `None`, 값이 없으면 응답 JSON에 키를 넣지 않는다(`/api/extract`가 `Intake`를 돌려주므로, 프론트 타입과 동기화 테스트가 그대로 맞게)
  - `tests/test_api.py`: 새 필드를 넣은 요청이 통과, 범위 밖 값은 422, 새 필드가 없을 때 응답에 키가 없음, 있을 때 `/api/extract` 응답에 그대로 돌아옴
  - `README.md`: `Intake` 설명에 새 선택 필드
- 하지 않는 것
  - 규칙(`rules/triage.py`)이 새 필드를 쓰게 바꾸기, `TriageResult.model`과 모델 호출(06), 프론트 버튼·타입(`frontend/` 작업)

## API·파일
- 변경: 모든 `Intake` 요청(`/api/triage`, `/api/extract`, `/api/visit-helper`, `/api/report/*`, `/api/center/cases`)이 `ageGroup`, `sex`, `injury`, `painScore`, `mental`을 선택으로 받는다. 응답은 값이 있을 때만 이 키를 담는다
- 수정: `app/vocab.py`, `app/schemas.py`, `tests/test_api.py`, `README.md`

## 완료 기준
- [x] `uv run pytest` 통과. `test_parity.py` 전부 그대로 통과(`parity.json`을 다시 만들지 않는다)
- [x] 새 필드 없는 요청의 `/api/triage`·`/api/extract` 응답이 지금과 바이트까지 같다(테스트)
- [x] `painScore: 11`, `ageGroup: "child"`, `mental: "asleep"`, `sex: "x"`가 422(테스트)
- [x] `modeling/tests/test_schema.py`가 같이 통과하도록 모델링 쪽 변경이 별도 PR로 있다(conceptamin/for-nav#53, 이 PR 위에 쌓음. 모델링 `uv run pytest` → 151 passed)

## 결과
- 실행(2026-10-28)
  - `uv run ruff check . && uv run ruff format --check .` → `All checks passed!`, `46 files already formatted`
  - `uv run pytest` → `1019 passed`(기존 1007 + `test_api.py` 12). `test_parity.py`는 `parity.json`을 다시 만들지 않고 그대로 통과
- 바뀐 API: 모든 `Intake` 요청이 `ageGroup`, `sex`, `injury`, `painScore`, `mental`을 선택으로 받는다. 응답에는 값이 있을 때만 이 키가 들어간다(`/api/extract`의 `intake`). 새 키가 없는 요청의 응답은 이전과 같다(`test_acuity_inputs_are_optional_and_absent_when_unset`)
- 결정 사항
  - **값이 없으면 응답에 키를 넣지 않는다**: Pydantic `Field(exclude_if=...)`(`schemas.absent_if_none`). `null`로 넣으면 `/api/extract`가 돌려주는 `Intake`가 프론트 타입·`parity.json`과 달라진다
  - `injury`·`painScore`는 `strict`로 받는다. 느슨하면 `"yes"` → `true`, `"3"` → `3`으로 바뀌어 들어간다
  - 규칙(`rules/triage.py`)은 새 필드를 쓰지 않는다. 같은 부위·증상이면 새 필드가 있어도 `/api/triage` 응답이 같다(테스트)
- 남은 문제
  - `modeling/tests/test_schema.py`는 백엔드 `Intake` 필드 목록과 모델링 `schema.Intake`가 같은지 본다. 모델링 쪽에 같은 필드를 더하는 PR(#53)이 이 PR 다음에 병합돼야 모델링 테스트가 통과한다
  - 프론트 `Intake` 타입·버튼은 `frontend/` 작업이다

## 메모
- 열거값을 더하는 것(바꾸는 것 아님)이라 기존 프론트·모델링 값은 깨지지 않는다. 다만 `modeling/tests/test_schema.py`는 백엔드 `Intake` 필드와 모델링 `schema.Intake`가 같은지 보므로, 모델링 `schema.py`에 같은 필드를 더하는 `modeling/` PR이 함께 병합돼야 한다(사용자에게 알림, 2026-10-28)
- 프론트 `Intake` 타입·버튼에 이 값들을 더하는 것은 `frontend/` 작업이다. 그 전까지 프론트는 이 키를 보내지 않고, 서버도 없는 키를 응답에 넣지 않는다
- `Profile.sex`(리포트용, `male`/`female` 순서)는 그대로 둔다. `Sex`는 모델 피처 순서(`female` 0, `male` 1)를 따른다
