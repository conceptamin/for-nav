# 23. 센터 요청 종류를 여러 개 받기(requestTypes)

상태: 완료
의존: frontend 37(PR #138, `requestType` → `requestTypes`와 `parity.json` 재생성)

## 목표
2026-10-31 사용자 요청으로 근로자 S-12 "무엇이 필요하세요?"가 여러 개 고르기가 되었다(frontend 37). 프론트가 원본이므로 서버의 센터 요약 입력과 센터 사례도 요청 종류를 배열로 받고 돌려준다. 그전까지 API 모드 전송은 422로 거절되고 `backend` CI의 동기화 테스트가 실패한다.

## 범위
- 하는 것
  - `CenterSummaryInput.request_type` → `request_types: list[RequestType]`(1~5개, 빈 배열은 422), `CenterCase.request_type` → `request_types`
  - 센터 요약의 요청 줄을 고른 순서대로 쉼표로 잇는다(`templates/reports.py`, 프론트 `buildCenterSummary`와 같다)
  - mock 사례는 하나씩 뽑아 배열에 담는다(프론트 `data/mock.ts`와 같은 시드 순서)
  - `routers/center.py`가 받은 배열을 그대로 사례에 담는다
  - `README.md`의 `POST /api/center/cases` 요청 예시, 기존 테스트의 요청 본문
- 하지 않는 것
  - 통계 원천(`StatRecord.request_type`). 집계에 쓰지 않는 익명 레코드라 프론트와 같이 그대로 둔다
  - 열거값(`RequestType`) 변경

## API·파일
- `POST /api/report/center`, `POST /api/center/cases` 요청: `"requestType": "booking"` → `"requestTypes": ["booking", "interpret"]`
- `GET /api/center/cases`, `GET /api/center/cases/{id}`, `POST /api/center/cases` 응답의 `CenterCase`: `requestType` → `requestTypes`
- 파일: `app/schemas.py`, `app/templates/reports.py`, `app/data/mock.py`, `app/routers/center.py`, `README.md`, `tests/test_api.py`·`test_auth.py`·`test_call.py`·`test_chat.py`·`test_translation.py`

## 완료 기준
- [x] `uv run ruff check . && uv run ruff format --check .` 통과
- [x] frontend 37가 만든 `parity.json`으로 `uv run pytest` 통과
- [x] 두 종류를 보내면 요약이 `요청 유형: 예약 지원, 통번역.`이고, 빈 배열은 422

## 결과
- `uv run --python 3.12 ruff check .` → 통과, `ruff format --check .` → 82개 파일 통과
- `PYTHONUTF8=1 uv run --python 3.12 --with tzdata pytest -q` → 3118 passed
  - 이 Windows PC에서만 붙인 옵션이다. 기본 Python(3.15)은 `pyyaml` 휠이 없어 설치가 실패하고, Windows에는 시간대 DB가 없고(`tzdata`), 기본 인코딩이 cp949라 fixture를 못 읽는다. CI(Linux)는 그대로 `uv run pytest`를 돈다. 의존성은 바꾸지 않았다
- 더한 테스트: `test_center_summary_lists_every_request_type`(두 종류 → ko·vi 요청 줄), `test_center_summary_needs_a_request_type`(빈 배열 → 422)
- 결정
  - 개수 위아래를 서버에서도 막았다(1~5). 프론트는 하나도 안 고르면 보내기를 끄지만, 서버는 클라이언트를 믿지 않는다. 위는 종류 수(5)다. 같은 값이 겹치는 것은 막지 않았다(프론트 `toggleIn`이 겹치지 않게 한다)
  - "기존 응답 필드의 이름·타입·의미를 바꾸지 않는다" 규칙의 예외다. 사용자가 프론트 전체를 배열로 바꾸기로 정했고(frontend 37), 프론트가 원본이므로 서버를 맞춘다

## 메모
- 이 PR은 `frontend/center-multi-select`(PR #138)를 기준으로 쌓았다. 이 PR을 #138에 먼저 병합하면 #138의 `backend` CI가 통과한다
- Windows에서 테스트를 돌리는 방법(위 옵션)을 README "검사"에 적을지는 따로 정한다
