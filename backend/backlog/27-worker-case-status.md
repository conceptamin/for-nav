# 27. 근로자가 자기 센터 요청의 상태와 센터 메시지 수를 읽는 경로

상태: 완료
의존: 없음(frontend 46이 이 경로를 부른다)

## 목표
센터 회신(2026-10-31)의 지원 절차 마지막 단계(결과 안내·사후관리)를 앱에서 하려면, 근로자가 앱을 다시 열었을 때 자기 요청의 처리 상태와 읽지 않은 센터 메시지를 알아야 한다(frontend 46). 지금 근로자는 사례를 읽는 경로가 없고(센터 경로는 직원 전용), 채팅 WebSocket을 열어야만 메시지를 본다. 근로자가 가진 채팅 토큰으로 자기 사례의 요약 상태만 읽는 경로를 둔다.

## 범위
- 하는 것
  - `POST /api/center/my-cases`
    - 요청: `{ "cases": [{ "id": "C-…", "token": "…" }] }`. 1~20개. 토큰을 URL에 싣지 않으려고 `GET`이 아니라 본문으로 받는다
    - 응답: `[{ "id", "status", "centerMessages", "lastCenterAt" }]`. `centerMessages`는 그 사례에서 센터가 보낸 메시지 수, `lastCenterAt`은 마지막 센터 메시지 시각(ISO, 없으면 `null`)
    - 토큰이 맞지 않거나 사례가 없으면(데모 초기화 포함) **그 항목만 빠진다.** 사례 존재 여부를 드러내지 않으려고 403·404를 내지 않는다. 토큰 비교는 `secrets.compare_digest`(채팅과 같다)
    - 근로자 세션: 서버가 `WORKER_AUTH=google`이면 `require_worker`(사례 전송과 같다), `off`면 토큰만 본다
    - 21개 이상·빈 목록·형식 오류는 422
  - `app/schemas.py`: `MyCaseRef`, `MyCasesRequest`, `MyCaseView`
  - `app/store.py`·`app/store_sqlite.py`: 센터 메시지 수·마지막 시각을 내는 함수(`messages()`를 세어도 되지만 SQLite는 `COUNT`·`MAX` 한 번으로)
  - `tests/test_api.py`: 맞는 토큰 → 상태·수, 틀린 토큰·없는 사례 → 빠짐, 직원 쿠키만으로는 아무것도 못 읽음, `WORKER_AUTH=google`에서 세션 없으면 401, 422 경계
  - `README.md` API 목록·요청·응답 예시
- 하지 않는 것
  - 사례 본문(요약·원문·긴급도) 돌려주기. 근로자 기기에 이미 있다
  - 푸시 발송(FCM). frontend 46 메모의 후속
  - 상태 변경 시각 저장

## API·파일
- 새 경로: `POST /api/center/my-cases`
- 수정: `app/routers/center.py`, `app/schemas.py`, `app/store.py`, `app/store_sqlite.py`, `tests/test_api.py`, `README.md`

## 완료 기준
- [x] `uv run ruff check . && uv run ruff format --check .` 통과
- [x] `uv run pytest` 통과(위 테스트 포함)
- [x] 센터가 채팅에 글 둘을 쓰면 그 사례의 `centerMessages`가 2, 근로자 글은 세지 않는다
- [x] 데모 초기화 뒤 같은 요청은 빈 목록을 돌려준다

## 결과
- `uv run ruff check . && uv run ruff format --check .` → All checks passed, 86 files already formatted
- `uv run pytest` → 3136 passed(Windows에서는 `PYTHONUTF8=1 uv run --with tzdata pytest`로 돌렸다. 시간대 자료·파일 인코딩이 OS 기본값이라 생기는 차이이고 CI(Linux)와 무관하다)
- 새 테스트(메모리·SQLite 두 저장소): `tests/test_chat.py`의 `test_my_cases_*` 5개(센터 글만 세기·상태 반영, 틀린 토큰·없는 사례·mock 사례 빠짐, 데모 초기화 뒤 빈 목록, 422 경계 5가지, 로그에 토큰 없음), `tests/test_worker_auth.py`의 `test_my_cases_needs_worker_session`(세션 없으면 401, 센터 직원 쿠키로도 401)
- 번호: 처음 26으로 썼으나 main에 응급 판정 삭제(26)가 먼저 들어와 27로 옮겼다. main 병합 뒤 `uv run pytest` → 2856 passed(main이 응급 테스트를 지워 수가 줄었다), ruff 통과
- 바뀐 API: 새 경로 `POST /api/center/my-cases`. 요청 `{ cases: [{ id, token }] }`(1~20개), 응답 `[{ id, status, centerMessages, lastCenterAt }]`. 기존 경로는 그대로다
- 저장소: `CenterStore.center_message_summary(case_id)`. 메모리는 메시지를 세고, SQLite는 `COUNT(*)`·`MAX(at)` 한 번으로 읽는다(`at`이 `iso_utc` 문자열이라 문자열 최댓값이 마지막 시각이다)
- 결정: 토큰 비교는 채팅과 같이 `secrets.compare_digest`. 사례 존재 여부를 드러내지 않으려고 틀린 항목은 오류 없이 뺀다

## 메모
- 토큰이 곧 그 사례의 열쇠다. 프론트가 토큰을 기기 저장소로 옮기므로(frontend 46) 응답에는 사례 내용을 넣지 않고 상태·수만 둔다
