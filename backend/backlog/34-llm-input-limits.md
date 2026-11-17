# 34. LLM 입력 크기 상한, 하루 호출 수 유지, 사례 전송 제한

상태: 완료
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
- [x] `uv run ruff check . && uv run ruff format --check .` 통과, `uv run pytest` 통과
- [x] `freeText` 500자 → `200`, 501자 → `422`(`/api/triage`, `/api/extract`, `POST /api/center/cases`)
- [x] 동기화 테스트(`test_parity.py`)가 통과한다. `parity.json`의 입력 중 500자를 넘는 것이 없는지 확인하고 결과에 적는다
- [x] 하루 상한: `DB_PATH`=임시 파일, `LLM_DAILY_LIMIT=2`로 2번 호출 → 앱을 새로 만든 뒤(재시작) 3번째 호출이 `source: "keywords"`. 다음 날(Asia/Seoul)에는 다시 `llm`
- [x] 사례 전송: `CASE_RATE_PER_MIN=2`로 같은 IP에서 3번 → 세 번째 `429`, 다른 IP는 `201`. `0`이면 제한 없음
- [x] 로그에 IP·본문이 남지 않는다(`caplog`)

## 결과
- `uv run ruff check . && uv run ruff format --check .` → All checks passed, 97 files already formatted
- `uv run pytest` → 3093 passed(새 테스트 31개, 매개변수 조합과 두 저장소 포함). `test_parity.py` 통과. `parity.json`의 `freeText`는 가장 긴 것이 58자라 500자를 넘는 입력이 없다
- 실제 서버 확인(`DB_PATH`=임시 파일, `CASE_RATE_PER_MIN=2`, `uv run uvicorn app.main:app`): `POST /api/center/cases`가 `freeText` 501자 `422` → 500자 `201` → `429` → `429`, 로그 `case limited scope=ip` 2줄, 파일에 `llm_usage` 표가 생긴다. 하루 합계 유지는 LLM 키 없이는 LLM이 꺼져 제한기가 돌지 않으므로 테스트로 확인했다(같은 파일을 새로 연 저장소와 새 제한기로 3번째 호출이 `keywords`, 다음 날 `llm`)
- 바뀐 API
  - `Intake.freeText` 500자까지. 넘으면 `Intake`를 받는 모든 경로가 `422`
  - `NewCaseRequest.contact` 100자까지, `consentedItems` 10개까지·항목마다 20자까지. 넘으면 `422`
  - `POST /api/center/cases`: IP별 최근 60초 `CASE_RATE_PER_MIN`건을 넘으면 `429 RATE_LIMITED`
- 파일: `app/schemas.py`, `app/llm_limit.py`(`IpWindow`·`CaseLimiter`·`DailyUsage`, 하루 합계 저장), `app/store.py`·`app/store_sqlite.py`(`llm_usage` 표, `llm_usage_get`·`llm_usage_add`), `app/main.py`, `app/routers/center.py`(`limit_case_rate`), `app/settings.py`(`CASE_RATE_PER_MIN`), `deploy/ecosystem.config.cjs`(`CASE_RATE_PER_MIN: '20'`), `.env.example`, `README.md`
- 결정
  - 상한 값: `contact` 100자(근로자 화면은 늘 `null`을 보낸다. 전화번호·메신저 id 자리라 넉넉히), `consentedItems` 10개·20자(`frontend/src/components/CenterSheet.tsx`가 만드는 값은 9종이고 가장 긴 것이 "경위(업무 중 여부)" 11자)
  - 하루 합계는 시작 뒤 첫 호출과 날짜가 바뀐 뒤 첫 호출에서 저장소의 그날 값을 읽는다("시작할 때 읽기"를 첫 호출로 미뤘다. 날짜가 바뀔 때도 같은 길로 읽는다). 메모리 저장소도 `llm_usage`를 구현해 제한기는 저장소를 늘 받고, `DB_PATH`가 없으면 다시 띄울 때 0이다
  - `llm_usage`는 데모 초기화(`reset`)가 지우지 않는다(사례 데이터가 아니고, 지우면 초기화로 하루 상한을 비울 수 있다)
  - IP 창은 `IpWindow`로 떼어 LLM 제한과 사례 전송 제한이 같이 쓴다. 사례 전송은 IP 헤더도 `LLM_CLIENT_IP_HEADER`를 그대로 쓴다(따로 설정을 두지 않았다)
  - 사례 전송 제한은 의존성으로 걸어 본문 검사보다 먼저 센다. 그래서 `422`가 되는 요청도 분당 수에 들어간다(막으려는 것이 반복 요청 자체라 그대로 둔다)
  - 맥미니 값 20: 발표장 와이파이처럼 여러 사람이 Cloudflare에서 IP 하나로 보일 수 있다. 근로자 한 명은 분당 한두 건을 보낸다

## 메모
- 출처: 2026-11-16 코드 리뷰
- **backlog 20의 결정을 바꾼다.** 20은 "제한 상태 저장(SQLite)"을 하지 않기로 했다. `main` 병합마다 배포되고(프론트만 바뀌어도 서버가 재시작된다) 그때마다 하루 합계가 0이 되므로, 하루 상한이 사실상 배포 사이 상한이 된다. 하루 합계만 저장하고 IP별 창은 그대로 메모리에 둔다
- 같은 리뷰에서 나온 관련 일(따로 항목으로): 채팅 WebSocket은 프레임 크기 검사 없이 `validate_json`에 넘긴다(통화는 16KB를 먼저 거른다). uvicorn 기본 최대 크기는 16MiB다. `ChatHub`에도 사례당 연결 수 상한이 없다
