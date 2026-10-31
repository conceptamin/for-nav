# 20. LLM 호출 제한(IP별 분당, 서버 전체 하루)

상태: 완료
의존: 없음

## 목표
맥미니 서버는 Cloudflare 터널 뒤에서 `https://www.for-nav.com`·`https://app.for-nav.com`으로 공개돼 있고, 근로자 경로(`/api/extract`, `/api/visit-helper`, `/api/report/*`, `POST /api/center/cases`)와 통화 자막 번역은 로그인 없이 LLM을 부른다. 누군가 이 경로를 반복해 부르면 LLM 비용이 제한 없이 늘어난다. 클라이언트 IP별 분당 호출 수와 서버 전체 하루 호출 수에 상한을 두고, 넘으면 LLM 없이 지금의 대체 동작(키워드 사전·기본 템플릿·원문)으로 응답한다. 대체 동작은 이미 있으므로 API와 프론트는 바뀌지 않는다(backlog 19 `## 메모`).

## 범위
- 하는 것
  - 세는 단위는 **공급자 호출 한 번**(`LLMClient.complete` 한 번, 재시도 포함)이다. 리포트 번역은 한 요청에 3번 부르므로 요청 수보다 실제 비용에 가깝다
  - IP별 제한: 최근 60초 안의 호출 수가 `LLM_RATE_PER_MIN`을 넘으면 그 IP의 호출을 막는다(슬라이딩 창). 막힌 호출은 세지 않는다
  - 서버 전체 하루 제한: Asia/Seoul 날짜별 호출 수가 `LLM_DAILY_LIMIT`을 넘으면 그날 남은 호출을 모두 막는다. 자정에 0으로 돌아간다
  - 두 값 모두 `0`이면 그 제한을 끈다. 기본값은 `0`(로컬 개발·테스트는 지금과 같다). 맥미니는 `deploy/ecosystem.config.cjs`의 `env`에 켠 값을 적어 `.env`를 빠뜨려도 켜진다
  - 막히면 `LLMError("limited")`로 올려 기존 실패 경로를 탄다. `generate()`는 이 종류에서 재시도하지 않는다(다시 불러도 막힌다)
  - 클라이언트 IP: 기본은 TCP 상대 주소(`request.client.host`). `LLM_CLIENT_IP_HEADER`(예: `cf-connecting-ip`)가 있으면 **TCP 상대가 루프백(127.0.0.1·::1)일 때만** 그 헤더를 믿는다. 서버가 `0.0.0.0:8000`으로 떠 있어 같은 망에서 직접 붙은 클라이언트가 헤더를 꾸밀 수 있기 때문이다
  - HTTP 경로와 통화 WebSocket(`/api/center/cases/{id}/call`의 자막 번역) 모두 같은 제한을 쓴다. 채팅은 LLM을 부르지 않는다
  - 로그: 막을 때 `llm limited scope=ip` 또는 `scope=daily` 한 줄. IP·경로 본문은 남기지 않는다
- 하지 않는 것
  - 응답에 제한 여부를 알리는 필드·`429`. 키가 없을 때와 똑같이 대체 결과를 준다(`source: "keywords"`, `translation.status: "skipped"` 등). 프론트는 바뀌지 않는다
  - 제한 상태 저장(SQLite). 프로세스 메모리에 두며 서버를 다시 띄우면(배포 포함) 0부터 센다. `--workers 1` 전제는 채팅·통화와 같다
  - 토큰 수·금액 기준 예산, 공급자 대시보드 한도 설정(사용자가 Anthropic 콘솔에서 따로 걸 수 있다)
  - LLM을 부르지 않는 경로(`/api/triage`, `/api/route`, 센터 경로)의 요청 제한. 필요하면 Cloudflare Rate limiting 규칙으로 한다

## API·파일
API 변경 없음. 제한에 걸리면 응답은 LLM 키가 없을 때와 같다.

- 새 파일 `app/llm_limit.py`: `LLMLimiter`(IP별 60초 창, 날짜별 합계, `clock.now()` 기준), `LimitedLLMClient`(`complete` 전에 `take(key)`, 막히면 `LLMError("limited")`), `client_key(conn, header)`(루프백일 때만 헤더 사용)
- `app/llm.py`: `generate()`가 `LLMError.kind == "limited"`면 재시도 없이 `LLMUnavailableError`
- `app/settings.py`: `LLM_RATE_PER_MIN`, `LLM_DAILY_LIMIT`(0 이상 정수), `LLM_CLIENT_IP_HEADER`(소문자 헤더 이름, 빈 값 허용)
- `app/main.py`: `app.state.llm_limiter`(ChatHub처럼 lifespan 밖에서 만든다)
- `app/routers/worker.py`의 `llm_client` 의존성, `app/routers/center.py`의 통화 자막: 원래 클라이언트를 요청 IP로 감싼 `LimitedLLMClient`를 넘긴다. 제한이 모두 꺼져 있으면 감싸지 않는다
- `deploy/ecosystem.config.cjs`: `LLM_RATE_PER_MIN=60`, `LLM_DAILY_LIMIT=3000`, `LLM_CLIENT_IP_HEADER=cf-connecting-ip`
- `.env.example`, `README.md`(폴더 구조 표, "실행 → LLM", "나중에 붙일 자리"에 한 줄)
- 테스트: `tests/test_llm_limit.py`(새 파일), `tests/test_settings.py`

기본 값을 고른 근거: 근로자 한 명이 증상 입력부터 센터 전송까지 가면 약 11번(추출 1, 접수 도우미 1, 리포트 번역 3, 센터 미리보기 3, 전송 3), 통화 자막은 문장마다 1번이다. 시연 영상을 한 PC의 창 두 개로 찍으면 근로자·센터가 같은 IP라 분당 60이면 넉넉하다. 하루 3000번은 Haiku 기준 비용이 작고, 넘어도 서비스는 대체 동작으로 계속된다.

## 완료 기준
- [x] `uv run ruff check . && uv run ruff format --check .` 통과, `uv run pytest` 통과. 제한 설정을 주지 않은 기존 테스트는 그대로 통과한다
- [x] `test_llm_limit.py`(가짜 LLM, `clock` 고정)
  - IP별: 분당 3으로 두고 같은 IP에서 `/api/extract` 4번 → 앞 3번 `source: "llm"`, 4번째 `source: "keywords"`이고 가짜 LLM은 3번만 불린다. 다른 IP는 그대로 `llm`. 61초 뒤에는 다시 `llm`
  - 하루: 하루 2로 두고 IP 셋에서 한 번씩 → 세 번째는 `keywords`. 다음 날(Asia/Seoul 자정 지나서) 다시 `llm`
  - 리포트 번역이 중간(역번역)에서 막히면 `translation.status: "skipped"`이고 500이 아니다
  - 통화 자막: 제한을 넘은 자막은 `translation: "skipped"`로 원문만 양쪽에 간다
  - 막힌 호출은 재시도하지 않는다(가짜 LLM 호출 수와 `llm attempt=` 로그 줄 수로 확인)
  - IP 헤더: 루프백 상대 + `cf-connecting-ip` → 헤더 값으로 센다. 루프백이 아닌 상대가 보낸 헤더는 무시한다. 헤더 설정이 비면 언제나 상대 주소다
  - 두 값이 0이면 제한 없이 지금과 같다
  - 로그에 `llm limited scope=…`만 있고 IP가 없다(`caplog`)
- [x] `test_settings.py`: 음수·정수가 아닌 값이면 서버가 뜨지 않는다. 기본값은 0, 0, 빈 헤더
- [x] 로컬 실제 서버(`LLM_RATE_PER_MIN=2`, 키 있음)에서 `curl`로 `/api/extract` 3번 → 세 번째 `source: "keywords"`, 서버 로그에 `llm limited scope=ip` (키가 없으면 이 항목은 건너뛰고 결과에 적는다)

## 결과

```sh
cd backend
uv run ruff check . && uv run ruff format --check .   # All checks passed, 78 files already formatted
uv run pytest                                          # 3045 passed (시작점 3028, 새 테스트 17)
```

- 새 테스트: `test_llm_limit.py` 12개(IP별 창과 61초 뒤 회복, 하루 제한과 Asia/Seoul 자정, 리포트 번역 중간 막힘 → `skipped`·재시도 없음, 터널 뒤 IP 헤더·꾸민 헤더 무시, `client_key` 5경우, 기본값 꺼짐, 로그에 IP 없음, 통화 자막 → `skipped` 원문), `test_settings.py` 5개(기본값·읽기 1개, 잘못된 값 4개).
- 로컬 실제 서버(`LLM_RATE_PER_MIN=2 LLM_CLIENT_IP_HEADER=cf-connecting-ip`, 실제 LLM 키, `uv run fastapi run app/main.py --port 8796`)에서 `curl -H 'cf-connecting-ip: …' POST /api/extract`:

| 보낸 IP 헤더 | `source` | 소요 |
|---|---|---|
| 203.0.113.7 | `llm` | 2152ms |
| 203.0.113.7 | `llm` | 2157ms |
| 203.0.113.7 | `keywords` | 0.8ms |
| 203.0.113.8 | `llm` | 957ms |

  세 번째 요청 때 서버 로그는 `llm limited scope=ip`, `llm attempt=1/2 failed=LLMError/limited` 두 줄이고(두 번째 시도 없음), 로그 전체에 `203.0.113` 0건

- 바뀐 API: 없음. 제한에 걸린 응답은 LLM 키가 없을 때와 같다(`source: "keywords"`, `translation.status: "skipped"`, 자막 `translation: "skipped"`, 상황 줄 슬롯 없음)
- 결정
  - 실패 종류 이름은 초안의 `rate_limited` 대신 `limited`(`app.llm.LIMITED`)로 했다. 공급자의 `RateLimitError`(로그 `LLMError/RateLimitError`, 재시도한다)와 로그에서 헷갈리지 않게 하기 위해서다
  - 제한은 `LLMClient`를 감싸는 방식이다(`LLMLimiter.wrap`). 추출·슬롯·번역 코드는 바꾸지 않고, 감싼 클라이언트가 `complete` 전에 센다. 제한이 모두 꺼져 있으면 감싸지 않아 지금과 같은 객체가 간다
  - 하루 제한을 IP별 제한보다 먼저 본다. 하루 제한에 걸린 호출은 IP 창에도 세지 않는다
  - 다시 오지 않는 IP의 창은 1분에 한 번 지운다. 공개 주소에서 IP가 계속 쌓여 메모리가 늘지 않게 하기 위해서다
  - 제한 객체는 `ChatHub`처럼 `app.state.llm_limiter`에 둔다(프로세스 메모리, 모듈 전역 변수 없음)
- 남은 문제
  - 맥미니 배포 뒤 확인(사용자): `pm2 env`로 세 값이 들어갔는지, 공개 주소에서 근로자 흐름이 그대로 되는지. 터널이 루프백으로 붙지 않으면 모두 한 IP로 세어진다(아래 메모). 이때도 하루 제한은 그대로 막는다
  - 서버를 다시 띄우면(배포 포함) 하루 수가 0이 된다. 배포가 잦은 날은 하루 3000을 넘게 부를 수 있다. 문제가 되면 Anthropic 콘솔의 월 사용 한도를 함께 건다

## 메모
- Cloudflare 대시보드의 Rate limiting 규칙만으로 막지 않는 이유: 넘으면 요청이 차단(429·차단 화면)돼 근로자 화면이 실패하는데, 앱 안에서 막으면 LLM 없이 응답이 계속된다. 응급 판정(`/api/triage`)은 LLM을 쓰지 않으므로 이 제한과 관계없다
- Cloudflare 터널(cloudflared)이 맥미니 안에서 `localhost:8000`으로 붙는다고 가정한다(backlog 17 메모: 터널 뒤에서 클라이언트 IP가 모두 `127.0.0.1`로 보인다). 아니면 헤더를 믿지 않아 모든 사용자가 한 IP로 세어지고, 하루 제한은 그대로 동작한다. 터널을 다른 기기로 옮기면 그 주소를 믿을 목록에 더하는 새 항목이 필요하다
