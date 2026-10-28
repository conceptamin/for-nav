# 백엔드 목업 서버 — 프론트 데모 기준 구현 안내

지금 프론트(`frontend/`)는 규칙·템플릿·mock 데이터를 모두 브라우저 안에서 돌린다.
이 문서는 그 로직을 **같은 입력이면 같은 결과**가 나오도록 FastAPI 서버로 옮겨, 프론트가 API를 호출하는 구조로 바꾸기 위한 구현 안내다.

목업 서버의 목표는 세 가지다.

1. 프론트가 쓸 **API 계약(경로·요청·응답 형태)을 먼저 확정**한다. 응답 필드는 프론트 TypeScript 타입과 1:1로 맞춘다.
2. 규칙 엔진(응급·진료과·제도 경로·긴급도)과 기본 템플릿을 서버로 옮긴다. 이 템플릿은 나중에 **LLM 실패 시 대체 문장**으로 그대로 쓴다.
3. 센터 접수함을 localStorage 대신 서버 메모리에 두어, **다른 기기에서도** "근로자 전송 → 센터 접수함 도착"을 시연할 수 있게 한다.

학습 모델(`modeling/README.md`)은 아직 붙이지 않았고, LLM은 `/api/extract`에만 붙였다(키가 없거나 실패하면 키워드 사전). 나머지 자리는 응답 스키마에 비워 둔다("나중에 붙일 자리").

## 기술 스택

| 항목 | 선택 | 이유 |
|---|---|---|
| 언어·런타임 | Python 3.12+ | 모델링 코드(LightGBM·SHAP)와 같은 언어 |
| 프레임워크 | FastAPI + Pydantic v2 | PRD의 실서비스 구성과 동일, 스키마 자동 문서(`/docs`) |
| 패키지 관리 | uv | `uv run`으로 가상환경 없이 실행 |
| 저장소 | 프로세스 메모리(dict) | 목업이므로 재시작하면 mock 시드 상태로 돌아간다 |
| LLM | `anthropic` SDK, 기본 `claude-haiku-5-5` | 추출·슬롯 채우기·짧은 번역에 빠르고 싸다. JSON 스키마 출력 고정 지원. 키가 없으면 쓰지 않는다 |
| 검사 | pytest, ruff | CI `backend` 작업에서 실행 |

## 폴더 구조

```text
backend/
  pyproject.toml
  app/
    main.py            FastAPI 앱, CORS, 라우터 등록, /api/health, /api/meta
    settings.py        환경 변수에서 시작 시 한 번 읽는 불변 설정값(운영 시간, 정보 기준일, 허용 출처, LLM), get_llm_client()
    llm.py             LLM 호출 계층 — LLMClient 프로토콜, generate()(시간 제한·재시도·스키마 검증·원문 미기록)
    llm_providers/
      anthropic.py     Anthropic Messages API 어댑터(JSON 스키마 출력 고정)
    errors.py          공통 오류 형식, X-Request-Id, 접근 로그
    clock.py           서버 시각(Asia/Seoul), JS toISOString 형식 — 테스트에서 시각 고정용
    schemas.py         Pydantic 모델 — frontend/src/domain/*.ts 타입과 1:1
    vocab.py           ← domain/vocab.ts (부위·증상·진료과·업종·구군 어휘, josa)
    rules/
      triage.py        ← domain/triage.ts (응급 키워드, 보조 점수, 진료과 규칙표, 자유 입력 추출)
      extract_llm.py   자유 입력 LLM 추출(프롬프트, 열거값 밖 필드 버리기, 실패 시 키워드 사전)
      coverage.py      ← domain/coverage.ts (제도 경로, INFO_DATE, 센터 운영 시간)
      urgency.py       ← domain/centerCase.ts (rateUrgency)
    templates/
      common.py        pick·joinTerms 등 공통 도우미
      visit.py         ← domain/templates.ts (접수 창구 화면, 전화 스크립트)
      reports.py       ← domain/templates.ts (의료진용 리포트, 센터 요약)
    data/mock.py       ← data/mock.ts (시드 고정 mock 사례 24건, 통계 레코드 420건)
    store.py           센터 사례 메모리 저장소
    routers/
      worker.py        /api/extract, /api/triage, /api/route, /api/visit-helper, /api/report/*
      center.py        /api/center/*
  scripts/
    llm_smoke.py       실제 공급자를 한 번 불러 확인(CI에서 돌지 않음)
    extract_compare.py 픽스처 자유 입력의 LLM 추출과 키워드 추출 비교(CI에서 돌지 않음)
  tests/
    fixtures/          프론트 규칙으로 만든 기대값 JSON(parity.json)
    test_parity.py     같은 입력 → 프론트와 같은 출력인지 비교
    test_api.py        경로별 응답 형태·상태 코드
    test_llm.py        LLM 호출 계층·어댑터(가짜 LLM·가짜 전송, 네트워크 없음)
    test_extract_llm.py /api/extract의 LLM 추출·대체(가짜 LLM)
    fakes.py           FakeLLMClient
```

## 공통 규칙

- **경로 접두사**: 모든 API는 `/api` 아래에 둔다. 프론트 개발 서버는 Vite 프록시로 `/api` → `http://localhost:8000`을 넘긴다.
- **JSON 필드명은 camelCase**: 프론트 타입을 그대로 쓰기 위해 Pydantic 모델에 `alias_generator=to_camel`, `populate_by_name=True`를 건다. Python 코드 안에서는 snake_case를 쓴다.
- **열거값은 프론트 문자열 그대로**: `Lang = 'en' | 'vi' | 'ko'`, `BodyPart`, `Symptom`, `Department` 등은 `Literal[...]`로 정의해 잘못된 값은 422로 거절한다.
- **결정적 규칙**: 규칙·템플릿에는 난수·LLM·현재 시각을 넣지 않는다. 시각이 필요한 곳(`createdAt`, 운영 시간 외 판정)만 서버 시각(Asia/Seoul)을 쓴다.
- **시간대**: `isAfterHours`는 브라우저 로컬 시각을 쓰고 있다. 서버에서는 반드시 `ZoneInfo("Asia/Seoul")` 기준으로 계산한다.
- **진단 표현 금지**: 템플릿을 옮길 때 문구를 바꾸지 않는다. 병명·추측 문장을 새로 넣지 않는다.
- **로그**: 요청마다 한 줄(메서드, 경로, 상태 코드, 소요 ms, request id)만 남긴다. 쿼리 문자열·본문·헤더·예외 메시지는 남기지 않는다. uvicorn 기본 접근 로그는 쿼리 문자열을 남기므로 앱에서 끈다.

### 오류 형식

404·422·500을 포함한 모든 오류 응답은 같은 형태다. 성공 응답은 바뀌지 않는다.

```json
{ "error": { "code": "VALIDATION", "message": "요청 형식이 올바르지 않다: body.bodyParts.0", "requestId": "fd083399e3094ab3a529d73199beaafe" } }
```

| 상태 | `code` | `message` |
|---|---|---|
| 404 | `NOT_FOUND` | 없는 경로·사례(`사례 C-0를 찾을 수 없다`) |
| 422 | `VALIDATION` | 어긋난 필드 위치만 적는다(요청 값은 넣지 않는다). 경로 안 검사(`days`)도 이 코드 |
| 500 | `INTERNAL` | `서버 오류가 발생했다` |
| 그 밖 4xx | `BAD_REQUEST` | 예: 405 |

- 모든 응답에 `X-Request-Id` 헤더가 붙고, 오류 본문의 `requestId`와 같다. 클라이언트가 보내면 그대로 쓰고(영문·숫자·`._-` 128자 이내), 없거나 그 밖이면 서버가 만든다. CORS `expose_headers`에 넣어 브라우저에서 읽을 수 있다.
- 오류는 이 id로 서버 로그에서 찾는다. 500 로그에는 예외 타입과 코드 위치만 남는다.

## API 목록

프론트 코드 주석에 이미 적힌 경로(`POST /triage`, `POST /route`, `POST /visit-helper` 등)를 따른다.

| 메서드·경로 | 프론트 대응 함수 | 호출 화면 | 요청 | 응답 |
|---|---|---|---|---|
| `GET /api/health` | — | — | — | `{ "ok": true }` |
| `GET /api/meta` | `INFO_DATE`, `CENTER_HOURS` | S-08, S-12 | — | `{ infoDate, centerHours }` |
| `POST /api/extract` | `extractFromText` + `mergeExtraction` | S-05 3단계 | `{ intake }` | `{ extraction, intake, filled, source }` |
| `POST /api/triage` | `triage` | S-05 | `Intake` | `TriageResult` |
| `POST /api/route` | `routeCoverage` | S-08 | `CoverageInput` | `CoverageResult` |
| `POST /api/visit-helper` | `buildDeskSheet`, `buildCallScript` | S-09, S-10 | `{ intake, department, firstVisit, lang }` | `{ desk: DeskSheet, call: { lines, faq } }` |
| `POST /api/report/clinician` | `buildClinicianReport` | S-11 | `{ intake, included, profile, meds }` | `ClinicianReport` |
| `POST /api/report/center` | `buildCenterSummary` | S-12 미리보기 | `CenterSummaryInput` | `{ ko, native }` |
| `POST /api/center/cases` | `addLiveCase` (+ `rateUrgency`, `isAfterHours`, `nextOpenDay`) | S-12 전송 | 아래 참고 | `{ case: CenterCase, nextOpenDate }` |
| `GET /api/center/cases` | `useCenterCases` | C-01 | `?status=&since=` | `CenterCase[]` (최신순, `since`보다 뒤에 접수된 것만) |
| `GET /api/center/cases/{id}` | — | C-02 | — | `CenterCase` / 404 |
| `PATCH /api/center/cases/{id}` | `setCaseStatus` | C-02 | `{ status }` | `CenterCase` |
| `POST /api/center/reset` | `resetCenterDemo` | C-01 데모 초기화 | — | `204` |
| `GET /api/center/stats` | `StatsPage`의 집계 | C-03 | `?days=30\|90\|180&district=` | 아래 참고 |

### 요청·응답 예시

아래 값은 현재 프론트 규칙에 실제로 넣어 얻은 결과다. 서버도 같은 값을 돌려줘야 한다.

**`POST /api/triage`** — 손·베인 상처·출혈(비응급, 보조 점수 2)

```jsonc
// 요청
{ "id": "in-test", "language": "vi", "bodyParts": ["hand"], "symptoms": ["cut", "bleeding"],
  "freeText": "", "onset": null, "workRelated": null, "workType": null,
  "industry": null, "district": null, "createdAt": "2026-10-26T01:00:00.000Z" }
// 응답
{ "emergency": false, "reasons": [], "byRule": false, "byModel": false, "modelScore": 2,
  "department": { "primary": "surgery", "alt": "ortho" }, "missing": [] }
```

가슴 + 통증이면 버튼 조합 규칙으로 바로 응급이다.

```json
{ "emergency": true, "reasons": ["chest"], "byRule": true, "byModel": false, "modelScore": 0,
  "department": { "primary": "internal", "alt": "family" }, "missing": [] }
```

**`POST /api/extract`** — 자유 입력 `"Ngón tay bị kẹp vào máy dập, bị sưng."`

```json
{
  "extraction": { "bodyParts": ["hand"], "symptoms": ["swelling"], "onset": null, "workRelated": "yes", "workType": "machine" },
  "intake": { "...": "버튼 입력을 우선하고 빈 항목만 위 추출값으로 채운 Intake" },
  "filled": true,
  "source": "keywords"
}
```

`filled`는 프론트 `Intake.tsx`의 "추출로 채운 값이 있는지" 판단과 같다. 부위·증상이 여전히 비면 프론트가 해당 버튼 질문으로 되돌아간다.

`source`는 서버 전용 선택 필드로, 추출에 무엇을 썼는지 알려 준다. 위 예시는 LLM이 꺼진 기본 상태(키 없음)의 결과다.

- `"llm"`: LLM 출력을 썼다. 출력은 `vocab.py` 열거값으로 고정하고, 열거값을 벗어난 필드는 그 필드만 비운다(목록은 `[]`, 나머지는 `null`).
- `"keywords"`: 키가 없거나, LLM이 `LLM_ATTEMPTS`번 모두 실패했거나, 자유 입력이 비어 키워드 사전을 썼다. 결과는 프론트 `extractFromText`와 같다.

어느 쪽이든 버튼으로 고른 값이 우선이고 빈 항목만 채운다. 응급 판정(`/api/triage`)은 LLM과 관계없이 자유 입력에 키워드 규칙으로 돈다.

**`POST /api/route`** — 업무 관련 "모름", 보험 "없음", 울산 90일 "예"

```json
{ "infoDate": "2026-10-24", "alsoIndustrial": true, "path": "ulsanSupport",
  "institutions": [{ "id": "center", "phone": null }, { "id": "ulsan", "phone": null }],
  "docs": ["arc", "receipts"] }
```

**`POST /api/center/cases`** — 근로자 전송

요약·긴급도·운영 시간 외 여부·id·접수 시각은 **서버가 계산**한다. 클라이언트가 보낸 요약은 믿지 않고 같은 입력으로 다시 만든다.

```jsonc
// 요청
{
  "intake": { /* Intake */ },
  "emergencyFlag": true,            // 세션 중 응급 판정 이력(AppState.emergencySeen)
  "requestType": "booking",
  "coverage": { /* CoverageResult 또는 null */ },
  "insurance": "no",
  "contactMethod": "zalo",
  "contact": "010-0000-0000",
  "consentedItems": ["증상", "부위", "시작 시점"]
}
// 응답 201
{ "case": { /* CenterCase, live: true, status: "new" */ }, "nextOpenDate": "2026-10-27" }
```

긴급도는 `rateUrgency`와 같다. 예: 응급 이력 없음 + 업무 중 발생 + 보험 없음 → `{ "urgency": "high", "reasons": ["업무 중 발생", "건강보험증 없음"] }`(2 + 1 = 3점).

**`GET /api/center/stats`** — 익명 집계

프론트는 지금 원천 레코드 420건을 받아 브라우저에서 센다. 서버는 **집계 결과만** 돌려주고, 5건 미만 칸은 서버에서 가린다(개인 단위 기록을 내보내지 않기 위해).

```jsonc
{
  "total": 212,                       // 5건 미만이면 null
  "afterHoursRate": 0.41,             // total이 null이면 null
  "workRelatedRate": 0.47,
  "noInsuranceRate": 0.44,            // 보험 "없음" + "모름"
  "byIndustry": [{ "key": "autoparts", "n": 68 }, { "key": "chemical", "n": null }],  // n < 5 → null
  "byLanguage": [ ... ],
  "byInsurance": [ ... ],
  "byAfterHours": [{ "key": "after", "n": 89 }, { "key": "within", "n": 138 }]  // 운영 시간 외 도넛용
}
```

(숫자는 형태 예시다. 실제 값은 mock 시드와 기간 필터로 정해진다.)

## mock 데이터

- `data/mock.ts`의 시드 고정 난수 **mulberry32를 그대로 옮긴다**. 그래야 프론트 단독 데모와 같은 사례 24건(`C-1001`~`C-1024`), 같은 통계가 나온다.
  - `Math.imul`, `>>>`, `|0`은 32비트 정수 연산이다. Python에서는 매 연산 뒤 `& 0xFFFFFFFF`로 자르고, 부호가 필요한 곳(`|0`)은 부호 있는 32비트로 바꿔 계산한다. 첫 10개 난수값을 프론트와 비교하는 테스트를 둔다.
- mock 사례의 `createdAt`은 "서버 시작 시각 기준 몇 시간 전"으로 만든다. 서버 시작 시 한 번만 만든다.
- 근로자가 실제로 보낸 사례는 `live: true`로 같은 저장소에 넣는다. `POST /api/center/reset`은 live 사례와 상태 변경만 지우고 mock은 처음 상태로 되돌린다.
- 사례 id: mock은 `C-1001`~`C-1024`, live는 `C-` + 접수 시각 밀리초 끝 5자리(프론트와 같음). 겹치면 뒤에 `-2`를 붙인다.

## 프론트 동기화 테스트

규칙을 옮길 때 가장 흔한 실수는 키워드 하나, 조건 순서 하나가 달라지는 것이다. 사람이 기대값을 적지 않고 **프론트 코드로 기대값을 만든다.**

1. `frontend/scripts/dump-fixtures.ts`에서 입력 목록을 프론트 도메인 함수(`triage`, `extractFromText`, `routeCoverage`, `rateUrgency`, `buildDeskSheet`, `buildClinicianReport`, `buildCenterSummary`)에 넣고 `{ input, output }`을 JSON으로 저장한다.
2. 프론트에 이미 있는 rolldown으로 묶어 node로 실행한다(추가 의존성 없음).
   ```sh
   cd frontend
   npx rolldown scripts/dump-fixtures.ts --file /tmp/dump.mjs --format esm && TZ=Asia/Seoul node /tmp/dump.mjs > ../backend/tests/fixtures/parity.json
   ```
   운영 시간·mock 시각은 로컬 시각으로 계산되므로 `TZ=Asia/Seoul`을 반드시 붙인다(빠지면 스크립트가 멈춘다).
   프론트 규칙·템플릿·mock을 바꾸면 이 명령으로 `parity.json`을 다시 만들어 함께 커밋한다.
3. `tests/test_parity.py`가 같은 입력을 서버 함수에 넣어 출력이 완전히 같은지 비교한다.
4. 입력 목록에는 최소한 다음을 넣는다.
   - 응급 키워드 13종 각각(한국어·영어·베트남어 1개씩)
   - 머리 부상 + 구토 / 머리 부상만(응급 아님)
   - 보조 점수 경계값(2점, 3점)
   - 진료과 규칙표의 모든 분기
   - 오탐 방지 사례: `"ở nhà máy"`(공장에서 → 업무 중), 영어 `painting`(통증으로 잡히면 안 됨)
   - 제도 경로 4가지 + `alsoIndustrial`
   - 템플릿은 언어 3종 × 첫 방문 여부 × 업무 관련 여부

`createdAt`, 리포트 `id`처럼 시각에 따라 바뀌는 값은 비교에서 뺀다. 의료진 리포트의 나이는 픽스처를 만든 시각(`generatedAt`)으로 고정해 비교한다.

## 프론트 전환 방법

목업 서버가 생겨도 **프론트 단독 데모는 계속 동작해야 한다**(발표장 네트워크 문제 대비).

- `VITE_API_BASE`가 비어 있으면 지금처럼 브라우저 안의 함수를 쓰고, 값이 있으면 API를 호출한다. 화면 컴포넌트는 `src/api/` 아래 함수만 부르게 하고, 그 안에서 둘 중 하나를 고른다.
- `vite.config.ts`에 `server.proxy: { '/api': 'http://localhost:8000' }`를 추가한다. 배포 시에는 같은 도메인 아래에 두어 CORS를 피한다. 개발 중 직접 호출에 대비해 서버 CORS는 `http://localhost:5180`만 허용한다.
- **응급 판정은 API 실패 시 브라우저 규칙으로 즉시 대체한다.** 네트워크 오류 때문에 119 안내가 늦어지면 안 된다. 자유 입력 추출(`/api/extract`)도 실패하면 브라우저 키워드 추출로 대체한다. 추출에서 입력이 멈추면 그 뒤의 응급 판정까지 늦어지기 때문이다. 나머지(리포트·접수 도우미)는 실패 시 오류 문구를 보이고 다시 시도하게 한다.
- 센터 접수함은 지금처럼 2초 주기로 `GET /api/center/cases`를 다시 부른다. 사례 수가 적어 전체 목록을 받아도 된다. 기존 `storage` 이벤트 갱신은 API 모드에서 끈다.
- 근로자 세션 상태(언어, 동의, 현재 입력, 비회원 리포트)는 계속 브라우저에 둔다. 서버는 로그인·회원 정보를 저장하지 않는다.

## 실행

```sh
cd backend
uv sync
uv run fastapi dev app/main.py        # http://localhost:8000, 문서: /docs (설정은 기본값)
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

설정값을 바꿀 때는 `.env`를 만들어 `--env-file`로 넘기거나 환경 변수를 직접 준다. `fastapi dev`는 `.env`를 스스로 읽지 않고, `uv run --env-file .env`는 파일이 없으면 실패한다. `.env`는 커밋하지 않는다.

```sh
cp .env.example .env                  # 값 수정
uv run --env-file .env fastapi dev app/main.py
# 또는
CENTER_HOURS=10:00-17:00 uv run fastapi dev app/main.py
```

| 환경 변수 | 기본값 | 형식 | 쓰는 곳 |
|---|---|---|---|
| `CENTER_HOURS` | `09:00-18:00` | `HH:00-HH:00`(평일, 시 단위) | `/api/meta`, 운영 시간 외 판정(`afterHours`), 다음 운영일, mock 사례·통계 |
| `INFO_DATE` | `2026-10-24` | `YYYY-MM-DD` | `/api/meta`, `/api/route`의 `infoDate` |
| `CORS_ORIGINS` | `http://localhost:5180` | 쉼표 구분 출처 목록 | CORS 허용 출처 |
| `LLM_PROVIDER` | `anthropic` | `anthropic`만 지원 | LLM 어댑터 선택 |
| `LLM_MODEL` | `claude-haiku-5-5` | 공급자 모델 이름 | LLM 호출 |
| `LLM_API_KEY` | (없음) | 공급자 API 키 | 비어 있으면 LLM을 쓰지 않는다 |
| `LLM_TIMEOUT_S` | `10` | 0보다 큰 초 | LLM 호출 한 번의 시간 제한 |
| `LLM_ATTEMPTS` | `2` | 1 이상 정수 | 첫 호출 + 재시도 횟수 |

값이 형식에 맞지 않으면 서버가 시작하지 않는다. 동기화 테스트(`parity.json`)는 기본값으로 만들었으므로 `uv run pytest`는 이 변수들이 없는 상태에서 돌린다.

### LLM

**키가 없으면 템플릿으로 동작한다.** `LLM_API_KEY`가 비어 있으면 `get_llm_client()`가 `None`을 돌려주고, LLM 자리(추출·템플릿 슬롯·번역)는 지금 규칙·템플릿을 그대로 쓴다. 키가 있어도 호출이 시간 제한을 넘기거나 출력이 스키마에 맞지 않으면 `LLM_ATTEMPTS`번까지 시도한 뒤 같은 기본값으로 돌아간다. LLM 실패는 API 실패가 되지 않는다(발표장 네트워크 대비).

- 출력은 Pydantic 모델의 JSON 스키마로 고정한다(Anthropic `output_config.format`). 받은 뒤에도 같은 모델로 다시 검증한다.
- 로그에는 시도 횟수와 실패 종류(`llm attempt=1/2 failed=LLMError/RateLimitError`)만 남는다. 프롬프트·응답 원문은 로그·예외에 들어가지 않는다.
- SDK 자체 재시도는 끄고 재시도는 `generate()` 한 곳에서만 한다.
- 서버는 시작 시(lifespan) 클라이언트를 한 번 만들어 `app.state.llm`에 두고 종료 시 닫는다.
- 테스트는 가짜 LLM으로 돌고 키·네트워크가 필요 없다. 실제 공급자 확인은 손으로 한 번 돌린다.

```sh
uv run --env-file .env python scripts/llm_smoke.py   # 모델 이름, 소요 시간, 스키마 통과 여부만 찍는다
uv run --env-file .env python scripts/extract_compare.py   # 픽스처 자유 입력의 LLM·키워드 추출 비교(번호와 열거값만 찍는다)
```

프론트와 함께 띄울 때:

```sh
uv run --directory backend fastapi dev app/main.py
VITE_API_BASE=/api npm --prefix frontend run dev
```

## CI

`.github/workflows/ci.yml`의 `backend` 작업은 다음 단계를 실행한다.

```yaml
backend:
  runs-on: ubuntu-latest
  defaults:
    run:
      working-directory: backend
  steps:
    - uses: actions/checkout@v4
    - uses: astral-sh/setup-uv@v6
    - run: uv sync
    - run: uv run ruff check .
    - run: uv run ruff format --check .
    - run: uv run pytest
```

## 구현 순서

| 단계 | 할 일 | 완료 기준 | 상태 |
|---|---|---|---|
| 1 | `pyproject.toml`, `app/main.py`, `/api/health`, CORS | `curl /api/health` → `{"ok": true}` | 완료 |
| 2 | `schemas.py`, `vocab.py` | 프론트 타입의 모든 필드·열거값이 들어감 | 완료 |
| 3 | `rules/` 3개 + `/api/triage`, `/api/extract`, `/api/route` | 규칙 동기화 테스트 통과 | 완료 |
| 4 | `templates/` + `/api/visit-helper`, `/api/report/*` | 템플릿 동기화 테스트 통과(언어 3종) | 완료 |
| 5 | `data/mock.py`, `store.py`, `/api/center/*` | mock 24건 id·요약이 프론트와 같음, 상태 변경 반영 | 완료 |
| 6 | `/api/center/stats` | 5건 미만 칸이 `null` | 완료 |
| 7 | 프론트 `src/api/` 전환, Vite 프록시 | `VITE_API_BASE` 유무 두 모드 모두 시연 가능 | 남음(`frontend/` 브랜치로 따로) |
| 8 | CI `backend` 작업 교체 | PR에서 ruff·pytest 통과 | 완료 |

## 나중에 붙일 자리

목업 단계에서는 비워 두지만, 응답 스키마에 자리를 미리 만들어 프론트가 다시 바뀌지 않게 한다.

| 자리 | 목업 동작 | 실서비스 |
|---|---|---|
| `TriageResult.modelScore`, `byModel` | 위험 신호 가산 점수(임계값 3) | 응급도 분류 모델(LightGBM, 3단계) — `modeling/README.md` |
| `TriageResult.department` | 결정적 규칙표 | 명확 케이스 규칙 → 진료과 앙상블(모델 A + B) 상위 2개 |
| `POST /api/extract` | 키가 있으면 LLM(JSON 스키마 고정), 없거나 실패하면 다국어 키워드 사전 — 붙임(backlog 03) | 같음. 부위·증상이 비면 버튼 질문 |
| 템플릿 문장 | 기본 템플릿 | LLM 슬롯 채우기, 실패 시 지금 템플릿 |
| 리포트 `note` 번역 | 원문 + "(원문, 번역 미연결)" | LLM 번역 + 역번역 검사 |
| 센터 저장소 | 프로세스 메모리 | 서버 DB |

모델 결과를 추가할 때는 기존 필드를 바꾸지 말고 `TriageResult.model`(예: `{ acuity, acuityProba, departmentProba, shap }`) 같은 선택 필드로 더한다. 레드플래그 규칙은 모델보다 먼저 실행하고, 규칙이 응급이면 모델 결과와 관계없이 응급이다.

## 확인이 필요한 값

프론트 `README.md`의 미결 사항을 그대로 따른다. 코드를 고치지 않고 바꿀 수 있도록 환경 변수로 빼 두었다("실행"의 환경 변수 표).

- 센터 운영 시간(평일 09:00~18:00 가정) → `CENTER_HOURS`
- 정보 기준일 → `INFO_DATE`. 발표 전 재확인
- 기관 대표번호(`KCOMWEL`, `NHIS`)는 공개 번호라 `app/rules/coverage.py` 상수로 둔다. 발표 전 재확인
- 센터·울산시 지원 연락처는 미확인이므로 `phone: null` 유지
