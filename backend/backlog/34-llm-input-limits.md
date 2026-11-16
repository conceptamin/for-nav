# 34. LLM 입력 크기 상한, 하루 호출 수 유지, 사례 전송 제한

상태: 대기
의존: 20

## 목표
backlog 20은 LLM 호출 **횟수**에 상한을 두었지만 입력 크기에는 상한이 없다. `Intake.free_text`(`app/schemas.py`)에 `max_length`가 없어 큰 본문 하나가 호출 한 번의 비용을 키우고, 리포트 번역(`translate_note`)은 한 요청에 3번 부르며 그중 2번에 원문 전체를 넣는다. 하루 상한은 메모리에 있어 배포(`pm2 delete` 후 재시작)마다 0으로 돌아간다. 입력 길이를 프론트와 같은 값으로 막고, 하루 호출 수를 SQLite에 남기며, 로그인 없이 열린 사례 전송 경로에 요청 수 상한을 둔다.

## 범위
- 하는 것
  - **입력 길이**: `Intake.free_text`에 `max_length=500`. 근로자 입력란이 이미 `maxLength={500}`(`frontend/src/pages/worker/Intake.tsx`)이라 화면에서 보낸 요청은 바뀌지 않는다. 넘으면 `422`이고, 프론트는 지금처럼 브라우저 규칙·키워드 추출로 대체한다
  - `NewCaseRequest.contact`, `consented_items`(개수와 항목 길이)에도 상한을 둔다. 값은 프론트 입력란과 `consented_items`의 실제 값 목록을 보고 정해 `## 결과`에 적는다
  - **하루 호출 수 유지**: `LLMLimiter`의 Asia/Seoul 날짜별 합계를 저장소에 둔다(`llm_usage(day TEXT PRIMARY KEY, count INTEGER)`). 시작할 때 오늘 값을 읽고, 호출을 셀 때마다 올린다. `DB_PATH`가 없으면 지금처럼 메모리에만 둔다. IP별 60초 창은 지금처럼 메모리다
  - **사례 전송 제한**: `POST /api/center/cases`에 IP별 분당 상한(`CASE_RATE_PER_MIN`, 기본 `0`=끔, 맥미니는 `ecosystem.config.cjs`에서 켠다). 넘으면 `429 RATE_LIMITED`. IP는 backlog 20의 `client_key`를 그대로 쓴다
- 하지 않는 것
  - 문자 수·토큰 수 기준 예산. 입력이 500자로 막히고 출력은 `MAX_TOKENS`(`app/llm_providers/anthropic.py`)로 막혀 있으므로 호출 한 번의 비용에 상한이 생긴다. 호출 수 기준을 유지한다
  - 요청 본문 전체 크기 미들웨어, 채팅 WebSocket 프레임 크기 검사(따로 항목으로. 아래 메모)
  - 프론트 변경

## API·파일
- `POST /api/triage`, `/api/extract` 등 `Intake`를 받는 경로: `freeText`가 500자를 넘으면 `422`
- `POST /api/center/cases`: 위 길이 제한, 그리고 IP별 분당 상한을 넘으면 `429 RATE_LIMITED`
- `app/schemas.py`: `Intake.free_text`, `NewCaseRequest`
- `app/llm_limit.py`: 하루 합계를 저장소에서 읽고 쓰기(시작 시 한 번 읽고, `take`에서 올린다)
- `app/store.py`·`app/store_sqlite.py`: `llm_usage` 표와 `llm_usage_get(day)`, `llm_usage_add(day)`
- `app/routers/center.py`: 사례 전송 IP 제한
- `app/settings.py`: `CASE_RATE_PER_MIN`
- `deploy/ecosystem.config.cjs`: `CASE_RATE_PER_MIN` 값
- `.env.example`, `README.md`(요청 필드 표의 길이, 오류 코드 표, "실행 → LLM")
- 테스트: `tests/test_api.py`, `tests/test_llm_limit.py`, `tests/test_settings.py`

## 완료 기준
- [ ] `uv run ruff check . && uv run ruff format --check .` 통과, `uv run pytest` 통과
- [ ] `freeText` 500자 → `200`, 501자 → `422`(`/api/triage`, `/api/extract`, `POST /api/center/cases`)
- [ ] 동기화 테스트(`test_parity.py`)가 통과한다. `parity.json`의 입력 중 500자를 넘는 것이 없는지 확인하고 결과에 적는다
- [ ] 하루 상한: `DB_PATH`=임시 파일, `LLM_DAILY_LIMIT=2`로 2번 호출 → 앱을 새로 만든 뒤(재시작) 3번째 호출이 `source: "keywords"`. 다음 날(Asia/Seoul)에는 다시 `llm`
- [ ] 사례 전송: `CASE_RATE_PER_MIN=2`로 같은 IP에서 3번 → 세 번째 `429`, 다른 IP는 `201`. `0`이면 제한 없음
- [ ] 로그에 IP·본문이 남지 않는다(`caplog`)

## 결과
(구현 후 작성)

## 메모
- 출처: 2026-11-16 코드 리뷰
- **backlog 20의 결정을 바꾼다.** 20은 "제한 상태 저장(SQLite)"을 하지 않기로 했다. `main` 병합마다 배포되고(프론트만 바뀌어도 서버가 재시작된다) 그때마다 하루 합계가 0이 되므로, 하루 상한이 사실상 배포 사이 상한이 된다. 하루 합계만 저장하고 IP별 창은 그대로 메모리에 둔다
- 같은 리뷰에서 나온 관련 일(따로 항목으로): 채팅 WebSocket은 프레임 크기 검사 없이 `validate_json`에 넘긴다(통화는 16KB를 먼저 거른다). uvicorn 기본 최대 크기는 16MiB다. `ChatHub`에도 사례당 연결 수 상한이 없다
