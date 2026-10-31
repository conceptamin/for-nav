# 백엔드 목업 서버 — 프론트 데모 기준 구현 안내

지금 프론트(`frontend/`)는 규칙·템플릿·mock 데이터를 모두 브라우저 안에서 돌린다.
이 문서는 그 로직을 **같은 입력이면 같은 결과**가 나오도록 FastAPI 서버로 옮겨, 프론트가 API를 호출하는 구조로 바꾸기 위한 구현 안내다.

목업 서버의 목표는 세 가지다.

1. 프론트가 쓸 **API 계약(경로·요청·응답 형태)을 먼저 확정**한다. 응답 필드는 프론트 TypeScript 타입과 1:1로 맞춘다.
2. 규칙 엔진(진료과·제도 경로·긴급도)과 기본 템플릿을 서버로 옮긴다. 이 템플릿은 나중에 **LLM 실패 시 대체 문장**으로 그대로 쓴다.
3. 센터 접수함을 localStorage 대신 서버 메모리에 두어, **다른 기기에서도** "근로자 전송 → 센터 접수함 도착"을 시연할 수 있게 한다.

학습 모델(`modeling/README.md`)은 `MODEL_DIR`이 있을 때 `/api/triage`에 붙고(없으면 규칙표), LLM은 `/api/extract`, 접수 도우미의 상황 줄 슬롯, 리포트 자유 입력 번역, 통화 자막 번역에 붙였다(키가 없거나 실패하면 키워드 사전·기본 템플릿·원문 표시). 나머지 자리는 응답 스키마에 비워 둔다("나중에 붙일 자리").

## 기술 스택

| 항목 | 선택 | 이유 |
|---|---|---|
| 언어·런타임 | Python 3.12+ | 모델링 코드(LightGBM·SHAP)와 같은 언어 |
| 프레임워크 | FastAPI + Pydantic v2 | PRD의 실서비스 구성과 동일, 스키마 자동 문서(`/docs`) |
| 패키지 관리 | uv | `uv run`으로 가상환경 없이 실행 |
| 저장소 | 프로세스 메모리(dict), `DB_PATH`가 있으면 SQLite 파일(표준 라이브러리 `sqlite3`) | 메모리는 재시작하면 mock 시드 상태로 돌아간다. SQLite는 live 사례와 상태 변경, 채팅 토큰·메시지가 재시작 뒤에도 남는다 |
| 상담 채팅 | FastAPI 기본 WebSocket(`uvicorn[standard]`에 든 `websockets`) | 새 의존성이 없다. 사례별 방과 재접속 뒤 이전 메시지면 충분해 socket.io는 쓰지 않는다(backlog 14). 열린 연결은 프로세스 메모리에 있으므로 `--workers 1`(기본)로만 띄운다 |
| 통화 | 브라우저끼리 WebRTC 음성, 서버는 같은 WebSocket으로 시그널링 중계와 자막 번역만 | 서버가 음성을 받지 않아 새 의존성·음성 인식 공급자가 없다. 받아쓰기는 브라우저 Web Speech API가 한다(backlog 16). TURN 서버는 없다 |
| 모델 | `../modeling` 경로 의존성(editable)의 `predict()`. `lightgbm`·`numpy`가 따라 설치된다 | 진료과 모델(backlog 06, 12). 버전은 `modeling/pyproject.toml` 한 곳에서 고정한다. `MODEL_DIR`이 없으면 import하지 않는다 |
| LLM | `anthropic` SDK, 기본 `claude-haiku-5-5` | 추출·슬롯 채우기·짧은 번역에 빠르고 싸다. JSON 스키마 출력 고정 지원. 키가 없으면 쓰지 않는다 |
| 검사 | pytest, ruff | CI `backend` 작업에서 실행 |

## 폴더 구조

```text
backend/
  pyproject.toml
  app/
    main.py            FastAPI 앱, CORS, 라우터 등록, /api/health, /api/meta, STATIC_DIR 프론트 서빙(APP_HOSTS 호스트에는 APP_STATIC_DIR 앱용 웹)
    settings.py        환경 변수에서 시작 시 한 번 읽는 불변 설정값(운영 시간, 정보 기준일, 허용 출처, LLM), get_llm_client()
    model.py           진료과 모델 연결 — 시작 시 아티팩트 검증, modeling predict() 호출, 실패 시 None
    llm.py             LLM 호출 계층 — LLMClient 프로토콜, generate()(시간 제한·재시도·스키마 검증·원문 미기록)
    llm_limit.py       LLM 호출 제한 — IP별 60초·서버 전체 하루 상한, 넘으면 LLMError(limited)로 대체 동작, IP 헤더는 루프백일 때만
    llm_providers/
      anthropic.py     Anthropic Messages API 어댑터(JSON 스키마 출력 고정)
    errors.py          공통 오류 형식, X-Request-Id, 접근 로그(HTTP·WebSocket)
    chat.py            상담 채팅·통화의 열린 연결(ChatHub, CallHub) — 사례별 방, 방송·상대에게만 보내기, 데모 초기화 때 닫기
    auth.py            센터 직원 로그인 — 6자리 코드 만들기·확인, 보내기 제한, 세션 쿠키(코드·토큰은 sha256 해시만 저장). 근로자 Google 로그인 계정 키·세션
    google_id.py       근로자 Google ID 토큰 검증 — TokenVerifier 프로토콜, google-auth(서명·발급자·대상·만료), sub만 돌려준다
    mail.py            로그인 코드 메일 — Mailer 프로토콜, Resend(httpx), 로컬 개발용 console
    clock.py           서버 시각(Asia/Seoul), JS toISOString 형식 — 테스트에서 시각 고정용
    schemas.py         Pydantic 모델 — frontend/src/domain/*.ts 타입과 1:1
    vocab.py           ← domain/vocab.ts (20개 언어 Lang, 부위·증상·진료과·업종·구군 어휘, josa, 언어 묶음 PACKS 읽기)
    lang/packs.json    ← domain/lang/*.ts (근로자 모국어 19개의 어휘 표기·문장 틀). 손으로 고치지 않는다
    rules/
      triage.py        ← domain/triage.ts (진료과 규칙표, 자유 입력 추출)
      extract_llm.py   자유 입력 LLM 추출(프롬프트, 열거값 밖 필드 버리기, 실패 시 키워드 사전)
      coverage.py      ← domain/coverage.ts (제도 경로, INFO_DATE, 센터 운영 시간)
      urgency.py       ← domain/centerCase.ts (rateUrgency)
    templates/
      common.py        pick·joinTerms 등 공통 도우미
      guard.py         LLM이 쓴 한국어 문장 검사(금지어·60자·한국어 여부)
      llm_slots.py     템플릿 슬롯 LLM 채우기(자유 입력 → 상황 줄), 실패 시 기본 템플릿
      translate.py     리포트 자유 입력 번역 → 역번역 → 비교, 실패·불일치 시 원문 표시. 통화 자막 한 문장 번역(translate_line)
      visit.py         ← domain/templates.ts (접수 창구 화면, 전화 스크립트)
      reports.py       ← domain/templates.ts (의료진용 리포트, 센터 요약)
    data/mock.py       ← data/mock.ts (시드 고정 mock 사례 24건, 통계 레코드 420건)
    store.py           센터 사례 저장소 — CenterStore 프로토콜, 메모리 구현, DB_PATH로 고르기, 채팅 토큰·메시지, 통화 자막, 직원·로그인 코드·세션, 근로자 세션
    store_sqlite.py    센터 사례 SQLite 구현(live_cases, case_status, chat_tokens, chat_messages, chat_reads, call_captions, center_staff, auth_code_requests, auth_codes, center_sessions, worker_sessions 표)
    routers/
      worker.py        /api/extract, /api/triage, /api/route, /api/visit-helper, /api/report/*
      center.py        /api/center/*, WS /api/center/cases/{id}/chat, WS /api/center/cases/{id}/call
      auth.py          /api/auth/* (센터 직원 로그인), /api/auth/worker/* (근로자 Google 로그인)
  deploy/
    deploy.sh          맥미니 배포 — 프론트·앱용 웹 API 모드 빌드, uv sync, 정적 파일 교체, pm2 재시작, /api/health 확인
    ecosystem.config.cjs pm2 앱 for-nav(STATIC_DIR=deploy/static, APP_STATIC_DIR=deploy/static-app·APP_HOSTS=app.for-nav.com, MODEL_DIR=../modeling/models, .env 있으면 읽기)
  scripts/
    llm_smoke.py       실제 공급자를 한 번 불러 확인(CI에서 돌지 않음)
    extract_compare.py 픽스처 자유 입력의 LLM 추출과 키워드 추출 비교(CI에서 돌지 않음)
    slots_check.py     픽스처 자유 입력의 상황 줄 요약이 guard를 통과하는지 집계(CI에서 돌지 않음)
    translate_check.py 픽스처 자유 입력의 번역 수락·거부 건수와 소요 시간 집계(CI에서 돌지 않음)
    staff.py           센터 직원 목록 add·remove·list(DB_PATH의 SQLite, CI에서 돌지 않음)
  tests/
    fixtures/          프론트 규칙으로 만든 기대값 JSON(parity.json)
    test_parity.py     같은 입력 → 프론트와 같은 출력인지 비교
    test_store.py      센터 저장소 메모리·SQLite 같은 테스트(채팅·통화 자막 포함), SQLite 재시작 뒤 유지
    test_chat.py       상담 채팅 WebSocket(방, 토큰, 잘못된 프레임, 읽음, 데모 초기화, 로그에 토큰·본문 없음)
    test_call.py       통화 WebSocket(있음 알림, 시그널링 중계, 자막 번역·대체, 자막 history·끊긴 쪽 자막·말한 순서, 4409, 데모 초기화, 로그에 SDP·자막 없음)
    test_auth.py       센터 직원 로그인(코드 메일, 확인, 쿠키, 보내기 제한, 센터 경로·채팅·통화 보호, 로그에 이메일·코드·토큰 없음, staff.py)
    test_worker_auth.py 근로자 Google 로그인(가짜 검증기로 쿠키·세션·센터 요청 보호·센터 세션과 분리·로그, 테스트 서명 키로 GoogleVerifier)
    test_api.py        경로별 응답 형태·상태 코드
    test_static.py     STATIC_DIR 프론트 서빙(SPA 경로 → index.html, /api 우선, 폴더 밖 차단), 호스트별 앱용 웹 빌드
    test_llm.py        LLM 호출 계층·어댑터(가짜 LLM·가짜 전송, 네트워크 없음)
    test_extract_llm.py /api/extract의 LLM 추출·대체(가짜 LLM)
    test_model_triage.py 규칙표 우선·막연한 분기 진료과·고정 조합·응급도 출력 무시·예측 실패 대체(가짜 predict)
    test_template_slots.py 템플릿 슬롯 채우기·guard 대체·슬롯 밖 문장 불변(가짜 LLM)
    test_translation.py 자유 입력 번역·역번역 거부·호출 실패·금지어 거부(가짜 LLM)
    test_llm_limit.py  LLM 호출 제한(IP별·하루, 대체 동작, 재시도 없음, 루프백일 때만 IP 헤더, 통화 자막, 로그에 IP 없음)
    fakes.py           FakeLLMClient, FakeMailer
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
| 401 | `UNAUTHORIZED` | 센터 직원 세션이 없거나 끝났다(`센터 로그인이 필요하다`), 로그인 코드가 틀렸다, 근로자 세션이 없다(`근로자 로그인이 필요하다`), Google ID 토큰을 받아들이지 않았다 |
| 404 | `NOT_FOUND` | 없는 경로·사례(`사례 C-0를 찾을 수 없다`) |
| 422 | `VALIDATION` | 어긋난 필드 위치만 적는다(요청 값은 넣지 않는다). 경로 안 검사(`days`)도 이 코드 |
| 429 | `RATE_LIMITED` | 로그인 코드 요청이 보내기 제한을 넘었다 |
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
| `POST /api/visit-helper` | `buildDeskSheet`, `buildCallScript` | S-09, S-10 | `{ intake, department, firstVisit, lang }` | `{ desk: DeskSheet, call: { lines, faq }, llmSlots }` |
| `POST /api/report/clinician` | `buildClinicianReport` | S-11 | `{ intake, included, profile, meds }` | `ClinicianReport` + `llmSlots`, `translation` |
| `POST /api/report/center` | `buildCenterSummary` | S-12 미리보기 | `CenterSummaryInput` | `{ ko, native, translation }` |
| `POST /api/center/cases` | `addLiveCase` (+ `rateUrgency`, `isAfterHours`, `nextOpenDay`) | S-12 전송 | 아래 참고 | `{ case: CenterCase, nextOpenDate, chatToken }` |
| `GET /api/center/cases` | `useCenterCases` | C-01 | `?status=&since=` | `CenterCase[]` (최신순, `since`보다 뒤에 접수된 것만) |
| `GET /api/center/cases/{id}` | — | C-02 | — | `CenterCase` / 404 |
| `PATCH /api/center/cases/{id}` | `setCaseStatus` | C-02 | `{ status }` | `CenterCase` |
| `POST /api/center/reset` | `resetCenterDemo` | C-01 데모 초기화 | — | `204` (열린 채팅·통화 연결은 4000으로 닫힌다) |
| `WS /api/center/cases/{id}/chat` | — (프론트 미연결) | 근로자·센터 상담 | `?role=worker&token=` 또는 `?role=center` | 아래 참고 |
| `WS /api/center/cases/{id}/call` | — (프론트 미연결) | 근로자·센터 통화 | `?role=worker&token=` 또는 `?role=center` | 아래 참고 |
| `GET /api/center/stats` | `StatsPage`의 집계 | C-03 | `?days=30\|90\|180&district=` | 아래 참고 |
| `GET /api/auth/me` | — (프론트 미연결) | C-01~C-03 진입 | — | `{ required, email }` |
| `POST /api/auth/code` | — (프론트 미연결) | 센터 로그인 | `{ email }` | `202` (등록 여부와 관계없이 같다) / `429` |
| `POST /api/auth/verify` | — (프론트 미연결) | 센터 로그인 | `{ email, code }` | `{ required, email }` + 세션 쿠키 / `401` |
| `POST /api/auth/logout` | — (프론트 미연결) | 센터 헤더 | — | `204` + 쿠키 지우기 |
| `GET /api/auth/worker/me` | — (프론트 미연결) | 근로자 화면 진입 | — | `{ required, account }` |
| `POST /api/auth/worker/google` | — (프론트 미연결) | S-03 로그인 | `{ credential }` | `{ required, account }` + 근로자 세션 쿠키 / `401` |
| `POST /api/auth/worker/logout` | — (프론트 미연결) | S-13 로그아웃 | — | `204` + 쿠키 지우기 |

`CENTER_AUTH=email`이면 센터 읽기·쓰기(`GET /api/center/cases`, `GET`·`PATCH /api/center/cases/{id}`, `POST /api/center/reset`, `GET /api/center/stats`)와 채팅·통화의 `role=center`는 직원 세션 쿠키가 있어야 한다(없으면 401, WS는 `4401`). 근로자 전송(`POST /api/center/cases`)과 `role=worker`는 그대로 열려 있다. 기본값 `off`에서는 지금처럼 로그인 없이 열린다(backlog 17).

`WORKER_AUTH=google`이면 근로자 전송(`POST /api/center/cases`)만 근로자 세션 쿠키가 있어야 한다(없으면 401). 판정·안내 경로(`/api/extract`, `/api/triage`, `/api/route`, `/api/visit-helper`, `/api/report/*`)는 응급 판정이 로그인에 묶이지 않도록 열어 둔다. 기본값 `off`에서는 근로자 전송도 지금처럼 열려 있다(backlog 21).

### 요청·응답 예시

아래 값은 현재 프론트 규칙에 실제로 넣어 얻은 결과다. 서버도 같은 값을 돌려줘야 한다.

**`POST /api/triage`** — 손·베인 상처·출혈. 응급 여부는 판정하지 않고 진료과만 돌려준다(backlog 26)

```jsonc
// 요청
{ "id": "in-test", "language": "vi", "bodyParts": ["hand"], "symptoms": ["cut", "bleeding"],
  "freeText": "", "onset": null, "workRelated": null, "workType": null,
  "industry": null, "district": null, "createdAt": "2026-10-26T01:00:00.000Z" }
// 응답
{ "department": { "primary": "surgery", "alt": "ortho" }, "missing": [] }
```

**모델이 있을 때(`MODEL_DIR`, backlog 06)** — 같은 요청에 선택 필드 `model`이 더해진다(확률은 줄임).

```jsonc
// 손·베인 상처·출혈 — 규칙표가 정한 조합이라 진료과는 규칙표 그대로
{ "department": { "primary": "surgery", "alt": "ortho" }, "missing": [],
  "model": { "departmentProba": { "ortho": 0.292, "surgery": 0.476, "family": 0.166, "...": 0.066 } } }
```

- `department`: 규칙표가 명시적으로 정한 조합은 규칙표다. 막연한 분기(배·가슴·온몸·발열·구토·어지러움 → 내과 묶음, 그리고 기본값)만 진료과 앙상블 상위 2개(`modeling` 폴백 포함)로 바꾼다. 단 가슴 + 통증, 숨참은 막연한 분기여도 규칙표로 고정한다(모델이 가슴 통증에 정형외과를 먼저 내기도 한다, backlog 06·26).
- `model`에는 `departmentProba`만 나간다. `modeling` `predict()`는 응급도 출력을 내지 않고(modeling 15), 예전 묶음이 `acuity`·`acuityProba`·`shap`을 돌려줘도 읽지 않는다.
- 예측 중 오류가 나면 `model` 없이 규칙표 결과를 돌려준다(로그에는 예외 종류만).

**`Intake`의 손상 여부(선택)** — 모든 `Intake` 요청은 `injury`(`true` · `false`, 손상·외상 여부)를 선택으로 더 받는다(backlog 10). 규칙은 이 값을 쓰지 않고, `MODEL_DIR`이 있으면 진료과 모델 B 입력으로 넘긴다. 값이 없으면 응답(`/api/extract`의 `intake` 등)에 키를 넣지 않는다. 타입이 다른 값(`injury: "yes"`)은 422다. 예전 응급도 입력(`ageGroup`·`sex`·`painScore`·`mental`)은 backlog 26에서 지웠고, 보내도 무시한다.

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

- `"llm"`: LLM 출력을 썼다. 출력은 `vocab.py` 열거값으로 고정하고, 열거값을 벗어난 필드는 그 필드만 비운다(목록은 `[]`, 나머지는 `null`). 그 뒤 키워드 결과와 필드별로 합친다. 부위·증상은 합집합, 업무 관련은 키워드 값만, 발생 시점·작업 유형은 LLM 값이다(backlog 09).
- `"keywords"`: 키가 없거나, LLM이 `LLM_ATTEMPTS`번 모두 실패했거나, 호출 제한(backlog 20)에 걸렸거나, 자유 입력이 비어 키워드 사전을 썼다. 결과는 프론트 `extractFromText`와 같다.

어느 쪽이든 버튼으로 고른 값이 우선이고 빈 항목만 채운다.

**`POST /api/visit-helper`의 `llmSlots`** — 서버 전용 선택 필드로, LLM으로 채운 슬롯 이름 목록이다. 채운 것이 없으면 `[]`다(backlog 04).

| 슬롯 | 자리 | 값 |
|---|---|---|
| `desk.situation` | `desk.lines`의 증상 줄 바로 뒤(증상 줄이 없으면 그 자리) | `{ ko: 자유 입력의 한국어 한 문장 요약, native: 근로자 원문(한국어 사용자는 ko와 같음), pron: "" }` |
| `call.situation` | `call.lines`의 증상 줄 바로 뒤 | 같은 줄 |

- 요약 한 번(LLM 호출 1회)을 두 슬롯에 함께 쓴다. 고정 문장은 바뀌지 않는다. 상황 줄을 빼면 LLM 켜짐·꺼짐 응답이 바이트 단위로 같다.
- 요약은 `templates/guard.py` 검사(병명·추측·치료 권고 금지어, 60자 이내, 한 줄, 글자의 절반 이상 한글)를 통과해야 쓴다. 걸리거나 LLM이 없거나 실패하면 상황 줄을 넣지 않는다.
- `/api/report/clinician`의 `llmSlots`는 항상 `[]`다. `note`의 LLM 사용 여부는 아래 `translation`이 알려 준다.

**자유 입력 번역 `translation`** — `/api/report/clinician`, `/api/report/center`의 서버 전용 선택 필드다(backlog 05). 자유 입력을 한국어로 번역하고, 번역을 근로자 언어로 다시 옮긴 역번역이 원문과 같은 사실을 말하는지 LLM으로 비교한다(호출 3회).

| `status` | 뜻 | 의료진 `note`의 `valueKo` | 센터 요약 `ko` |
|---|---|---|---|
| `"ok"` | 번역을 썼다 | `프레스 기계에 손가락이 끼여서 부었습니다. (원문: Ngón tay bị kẹp vào máy dập, bị sưng.)` | 끝에 `근로자 메모(번역): "…"` 한 문장을 더한다 |
| `"rejected"` | 번역이 guard(금지어·한국어 여부)에 걸렸거나 역번역 비교가 다르다고 했다 | 지금과 같다(`원문 (원문, 번역 미연결)`) | 지금과 같다 |
| `"skipped"` | 한국어 사용자, 빈 자유 입력, 근로자가 `note`를 뺐음, LLM 없음, 호출 실패 | 지금과 같다 | 지금과 같다 |

- 원문은 항상 남는다. 의료진 `note`는 괄호 안에, 센터 사례는 `native`(`originalNative`)의 메모 줄에 그대로 있다.
- 근로자가 리포트에서 `note`를 뺐으면 자유 입력을 LLM에 보내지 않는다.
- `POST /api/center/cases`는 같은 번역을 다시 거쳐 `summaryKo`를 만든다. 미리보기와 실제 접수 요약이 같다.
- 번역은 리포트 화면이 기다리는 동안 돈다. 실측은 평균 4초 안팎이고, 최악은 `LLM_TIMEOUT_S × LLM_ATTEMPTS × 3`이다(기본 60초).

**`POST /api/route`** — 업무 관련 "모름", 보험 "없음", 울산 90일 "예"

```json
{ "infoDate": "2026-10-24", "alsoIndustrial": true, "path": "ulsanSupport",
  "institutions": [{ "id": "center", "phone": null }, { "id": "ulsan", "phone": null }],
  "docs": ["arc", "receipts"] }
```

**`POST /api/center/cases`** — 근로자 전송

요약·긴급도·운영 시간 외 여부·id·접수 시각은 **서버가 계산**한다. 클라이언트가 보낸 요약은 믿지 않고 같은 입력으로 다시 만든다. LLM이 있으면 요약에 자유 입력 번역이 더해진다(위 `translation`).

```jsonc
// 요청
{
  "intake": { /* Intake */ },
  "requestTypes": ["booking", "interpret"],   // 고른 순서, 1~5개. 빈 배열은 422
  "coverage": { /* CoverageResult 또는 null */ },
  "insurance": "no",
  "contactMethod": "zalo",
  "contact": "010-0000-0000",
  "consentedItems": ["증상", "부위", "시작 시점"]
}
// 응답 201
{ "case": { /* CenterCase, live: true, status: "new" */ }, "nextOpenDate": "2026-10-27", "chatToken": "kqr6VTRE…" }
```

`chatToken`은 서버 전용 선택 필드다(backlog 14). 근로자가 이 사례의 상담 채팅에 붙을 때 쓰고, `CenterCase`에는 들어가지 않아 센터 목록·상세에는 나오지 않는다.

긴급도는 `rateUrgency`와 같다(업무 중 발생 +2, 건강보험증 없음 +1, 3점 이상 높음·1점 이상 보통). 예: 업무 중 발생 + 보험 없음 → `{ "urgency": "high", "reasons": ["업무 중 발생", "건강보험증 없음"] }`(2 + 1 = 3점).

**`WS /api/center/cases/{id}/chat`** — 근로자·센터 상담 채팅(backlog 14)

사례 하나가 방 하나다. 근로자는 `?role=worker&token=<chatToken>`, 센터는 `?role=center`로 붙는다(`CENTER_AUTH=email`이면 직원 세션 쿠키도 있어야 한다). 서버는 먼저 연결을 받은 뒤 검사하고, 실패하면 이유 코드로 닫는다.

| 닫힘 코드 | 언제 |
|---|---|
| `4404` | 사례가 없다 |
| `4403` | `role`이 없거나 틀렸다, 근로자 토큰이 없거나 맞지 않는다(mock 사례에는 근로자 토큰이 없다), `role=center`인데 `Origin`이 다른 사이트다 |
| `4401` | `role=center`인데 직원 세션이 없거나 끝났다(`CENTER_AUTH=email`일 때만) |
| `4000` | 데모 초기화(`POST /api/center/reset`)로 방이 비었다 |

```jsonc
// 클라이언트 → 서버. text는 앞뒤 공백을 지운 뒤 1~1000자
{ "type": "message", "text": "Tay tôi vẫn còn chảy máu" }
// 클라이언트 → 서버: 이 연결의 역할이 m-5까지 읽었다(backlog 27). 이 사례에 있는 메시지 id여야 한다
{ "type": "read", "upTo": "m-5" }

// 서버 → 클라이언트: 연결 직후 한 번(재접속하면 다시 받는다). read는 역할별 마지막으로 읽은 메시지 id, 없으면 null
{ "type": "history", "messages": [ /* ChatMessage, 보낸 순서 */ ], "read": { "worker": "m-3", "center": null } }
// 서버 → 클라이언트: 새 메시지. 보낸 사람 자신에게도 간다
{ "type": "message", "message": { "id": "m-1", "caseId": "C-47625", "from": "worker", "text": "Tay tôi vẫn còn chảy máu", "at": "2026-10-30T11:50:47.646Z" } }
// 서버 → 클라이언트: 읽은 자리가 앞으로 옮겨졌다. 보낸 쪽을 포함해 방의 모든 연결에 간다
{ "type": "read", "role": "center", "upTo": "m-5" }
// 서버 → 클라이언트: 잘못된 프레임(빈 글, 1000자 초과, JSON 아님, 다른 type, 바이너리, 없는 메시지의 읽음). 연결은 끊지 않는다
{ "type": "error", "code": "invalid" }
```

읽은 자리는 역할마다 하나이고 앞으로만 옮겨진다. 저장된 값보다 앞이거나 같은 `read`는 저장도 방송도 하지 않는다. 데모 초기화가 함께 지운다.

`id`·`from`·`at`은 **서버가 정한다**. `id`는 사례 안에서 `m-1`, `m-2`…로 늘어나고, `from`은 연결 때 확인한 역할이다. 접근 로그에는 `WS <경로> <닫힘 코드> <ms> request_id=`만 남고 쿼리 문자열(토큰)과 메시지 본문은 남지 않는다. uvicorn이 따로 남기는 `"WebSocket <경로?쿼리>" [accepted]` 줄은 앱에서 버린다.

**`WS /api/center/cases/{id}/call`** — 근로자·센터 통화와 자막 번역(backlog 16), 자막 다시 보기(backlog 18)

음성은 브라우저끼리 WebRTC로 직접 오가고 서버는 받지 않는다. 서버는 연결 정보(SDP·ICE)를 상대에게 중계하고, 브라우저가 받아쓴 문장을 번역해 양쪽에 보낸다. 권한(`role`, 근로자 `chatToken`)과 닫힘 코드 `4404`·`4403`·`4000`은 채팅과 같고, 방마다 역할 하나에 연결 하나다(같은 역할 두 번째 연결은 `4409`).

```jsonc
// 클라이언트 → 서버. 프레임 하나는 16KB 이하
{ "type": "signal", "data": { "sdp": { "type": "offer", "sdp": "v=0…" } } }   // data는 열어 보지 않고 상대에게 그대로
{ "type": "caption", "text": "Tay tôi vẫn còn chảy máu" }                    // 받아쓰기 확정 문장, 앞뒤 공백을 지운 뒤 1~500자

// 서버 → 클라이언트
{ "type": "joined", "role": "worker", "peers": ["center"] }   // 연결 직후 한 번, 지금 방에 있는 상대
{ "type": "history", "captions": [Caption, ...] }            // joined 바로 다음 한 번, 번역이 끝난 이전 자막(말한 순서). 다시 붙을 때마다 전체
{ "type": "peer", "role": "center", "present": true }         // 상대가 들어옴(true)·나감(false)
{ "type": "signal", "from": "worker", "data": { … } }         // 상대에게만
{ "type": "caption", "caption": { "id": "c-1", "from": "worker", "text": "Tay tôi bị kẹp vào máy, vẫn còn chảy máu", "lang": "vi",
    "translated": "손이 기계에 끼였고, 아직도 피가 나고 있어요.", "translatedLang": "ko", "translation": "ok", "at": "2026-10-30T12:43:31.707Z" } }  // 양쪽 모두
{ "type": "error", "code": "invalid" }                        // 잘못된 프레임(JSON 아님, 다른 type, 16KB 초과, 빈 자막·500자 초과). 연결은 유지
```

- 근로자 말은 한국어로, 센터 말은 근로자 언어로 옮긴다. 근로자 언어는 클라이언트 값이 아니라 사례의 `language`다. LLM은 한 번만 부르고(재시도·역번역 없음) 원문을 항상 함께 보낸다. 실측 평균 3~4초다.
- `translation`: `ok` 번역을 썼다 / `rejected` 한국어 번역이 `templates/guard.py`(금지어·한국어 여부)에 걸렸거나 번역이 비었다 / `skipped` 같은 언어(사례 언어 `ko`), LLM 없음, 호출 실패·시간 초과. `ok`가 아니면 `translated`는 `null`이다.
- 자막은 사례별로 저장한다(채팅 메시지와 같은 저장소, 채팅 기록에는 넣지 않는다). 받자마자 번호·시각을 정해 번역 전 상태로 넣고, 번역이 끝나면 채워 양쪽에 `caption`으로 보낸다. 번역 전 자막은 `history`에 없다(끝나면 `caption`으로 한 번 받는다). `id`는 사례마다 `c-1`, `c-2`…이고 서버를 다시 띄워도 이어지며(`DB_PATH`가 있을 때) 데모 초기화 때 처음부터다. `history`는 번역이 끝난 순서가 아니라 말한 순서다.
- 말한 쪽이 번역 중에 끊기면 그 자막은 `translation: "skipped"`, `translated: null`로 남고(원문은 남는다) 방에 남은 쪽이 `caption`으로 받는다.
- 음성은 저장하지 않는다. `signal.data`(말하는 중 글 등)도 열어 보거나 저장하지 않는다.
- 로그에는 `WS <경로> <닫힘 코드> <ms> request_id=`와 `call caption translation=<상태>`만 남는다. 토큰, SDP·ICE(IP 주소가 들어 있다), 자막 원문·번역은 남지 않는다.

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

**`/api/auth/*`** — 센터 직원 로그인(backlog 17, `CENTER_AUTH=email`일 때)

직원 이메일은 `scripts/staff.py`로 SQLite(`center_staff`)에 넣는다. 비밀번호는 없다. 이메일을 보내면 등록된 직원에게만 6자리 코드 메일이 가고(10분 유효, 5번 틀리면 무효, 새 코드를 받으면 이전 코드 무효), 맞는 코드를 보내면 세션 쿠키를 받는다.

```jsonc
// GET /api/auth/me — 센터 화면이 들어올 때. 세션이 없어도 401이 아니다
{ "required": true, "email": null }          // CENTER_AUTH=off이면 { "required": false, "email": null }

// POST /api/auth/code → 202 (본문 없음). 등록되지 않은 이메일도 같은 202다(메일만 보내지 않는다)
{ "email": "staff@example.org" }

// POST /api/auth/verify → 200 + Set-Cookie: fornav_center=…; HttpOnly; SameSite=lax; Path=/; Max-Age=2592000; Secure
{ "email": "staff@example.org", "code": "042917" }
{ "required": true, "email": "staff@example.org" }
// 틀림·만료·없음은 이유를 나누지 않고 401
{ "error": { "code": "UNAUTHORIZED", "message": "코드가 맞지 않거나 만료되었다", "requestId": "…" } }
```

- 이메일은 앞뒤 공백을 지우고 소문자로 맞춘다. 형식이 아니면 422다.
- 보내기 제한(넘으면 429 `RATE_LIMITED`): 같은 이메일은 60초에 한 번, 1시간에 5번(등록 여부와 관계없이 똑같이 건다). 서버 전체로 10분에 실제 발송 30통.
- 메일 발송이 실패해도 202다(실패를 알리면 등록 여부가 드러난다). 서버 로그에 `로그인 코드 메일 실패 <종류> request_id=`만 남는다.
- 코드·세션 토큰은 sha256 해시만 저장하고, 이메일·코드·토큰·쿠키 값은 로그에 남기지 않는다. 세션은 `CENTER_SESSION_DAYS`(기본 30일) 뒤 끝나고 늘어나지 않는다. `scripts/staff.py remove`는 그 직원의 세션도 지운다.
- 데모 초기화(`POST /api/center/reset`)는 직원·코드·세션을 지우지 않는다.
- 쿠키는 같은 출처에서만 쓴다(`STATIC_DIR` 서빙, Vite 프록시). 다른 출처 프론트(예: Vercel)에서 쿠키를 보내는 설정은 하지 않았다.

**`/api/auth/worker/*`** — 근로자 Google 로그인(backlog 21, `WORKER_AUTH=google`일 때)

프론트가 Google Identity Services로 받은 ID 토큰(`credential`)을 보내면 서버가 서명·발급자(`accounts.google.com`)·대상(`aud == GOOGLE_CLIENT_ID`)·만료를 확인하고 근로자 세션 쿠키를 준다. 서버는 Google 계정 고유 번호(`sub`)에서 만든 **계정 키**와 세션 해시만 저장한다. 이름·이메일·사진은 저장하지도 돌려주지도 않는다.

```jsonc
// GET /api/auth/worker/me — 근로자 화면이 들어올 때. 세션이 없어도 401이 아니다
{ "required": true, "account": null }        // WORKER_AUTH=off이면 { "required": false, "account": null }

// POST /api/auth/worker/google → 200 + Set-Cookie: fornav_worker=…; HttpOnly; SameSite=lax; Path=/; Max-Age=2592000; Secure
{ "credential": "eyJhbGciOiJSUzI1NiIs…" }
{ "required": true, "account": "3f9c0a5e…(32자 16진수)" }
// 서명·발급자·대상·만료·형식이 틀리거나 Google 공개 키를 받지 못하면 이유를 나누지 않고 401
{ "error": { "code": "UNAUTHORIZED", "message": "Google 로그인을 확인하지 못했다", "requestId": "…" } }

// POST /api/auth/worker/logout → 204 + 쿠키 지우기(세션이 없어도 204)
```

- 계정 키는 `sha256("fornav-worker:" + sub)`의 앞 32자다. 같은 Google 계정이면 늘 같고 `sub`로 되돌릴 수 없다. 프론트는 이 값으로 기기 저장소를 계정마다 나눈다.
- `WORKER_AUTH=off`(기본)이면 `/worker/me`만 응답하고 `/worker/google`은 404다. 프론트는 데모 로그인으로 동작한다.
- ID 토큰·`sub`·계정 키·세션 토큰은 로그에 남기지 않는다. 확인 실패는 `Google 로그인 확인 실패 <종류> request_id=`만 남는다.
- 세션은 `WORKER_SESSION_DAYS`(기본 30일) 뒤 끝나고 늘어나지 않는다. 데모 초기화는 근로자 세션을 지우지 않는다. 쿠키 `Secure`는 센터와 같은 `CENTER_COOKIE_SECURE`를 따른다.
- 센터 세션 쿠키(`fornav_center`)와 근로자 세션 쿠키(`fornav_worker`)는 서로의 경로를 열지 않는다.

## mock 데이터

- `data/mock.ts`의 시드 고정 난수 **mulberry32를 그대로 옮긴다**. 그래야 프론트 단독 데모와 같은 사례 24건(`C-1001`~`C-1024`), 같은 통계가 나온다.
  - `Math.imul`, `>>>`, `|0`은 32비트 정수 연산이다. Python에서는 매 연산 뒤 `& 0xFFFFFFFF`로 자르고, 부호가 필요한 곳(`|0`)은 부호 있는 32비트로 바꿔 계산한다. 첫 10개 난수값을 프론트와 비교하는 테스트를 둔다.
- mock 사례의 `createdAt`은 "서버 시작 시각 기준 몇 시간 전"으로 만든다. 서버 시작 시 한 번만 만든다.
- 근로자가 실제로 보낸 사례는 `live: true`로 같은 저장소에 넣는다. `POST /api/center/reset`은 live 사례와 상태 변경만 지우고 mock은 처음 상태로 되돌린다.
- `DB_PATH`가 있으면 live 사례(`live_cases`: id, 접수 시각, 본문 JSON)와 상태 변경(`case_status`: id, 상태)만 SQLite 파일에 둔다. mock 사례·통계 레코드는 지금처럼 시작 시 메모리에서 만든다(시드 고정이라 재시작해도 id가 같다). `reset`은 두 표를 비우고 파일은 지우지 않는다.
- SQLite 파일에는 연락처·자유 입력(채팅 메시지·통화 자막 포함)이 **평문으로** 남는다. 데모 범위에서만 쓰고, 보존 기간·삭제 규칙은 PRD 미결이다. `*.db`는 `.gitignore`에 있다.
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
   언어 묶음(`frontend/src/domain/lang/*.ts`)을 바꿨으면 서버가 읽는 `app/lang/packs.json`도 다시 만든다.
   ```sh
   npx rolldown scripts/dump-lang-packs.ts --file /tmp/packs.mjs --format esm && node /tmp/packs.mjs > ../backend/app/lang/packs.json
   ```
3. `tests/test_parity.py`가 같은 입력을 서버 함수에 넣어 출력이 완전히 같은지 비교한다.
4. 입력 목록에는 최소한 다음을 넣는다.
   - 진료과 규칙표의 모든 분기
   - 오탐 방지 사례: `"ở nhà máy"`(공장에서 → 업무 중), 영어 `painting`(통증으로 잡히면 안 됨)
   - 제도 경로 4가지 + `alsoIndustrial`
   - 템플릿은 언어 3종 × 첫 방문 여부 × 업무 관련 여부

`createdAt`, 리포트 `id`처럼 시각에 따라 바뀌는 값은 비교에서 뺀다. 의료진 리포트의 나이는 픽스처를 만든 시각(`generatedAt`)으로 고정해 비교한다.

## 프론트 전환 방법

목업 서버가 생겨도 **프론트 단독 데모는 계속 동작해야 한다**(발표장 네트워크 문제 대비).

- `VITE_API_BASE`가 비어 있으면 지금처럼 브라우저 안의 함수를 쓰고, 값이 있으면 API를 호출한다. 화면 컴포넌트는 `src/api/` 아래 함수만 부르게 하고, 그 안에서 둘 중 하나를 고른다.
- `vite.config.ts`에 `server.proxy: { '/api': 'http://localhost:8000' }`를 추가한다. 배포·발표 때는 서버가 프론트 빌드를 같은 출처에서 서빙해 CORS를 피한다(`STATIC_DIR`, 아래 "발표용 실행"). 개발 중 직접 호출에 대비해 서버 CORS는 `http://localhost:5180`만 허용한다.
- **진료과 추천(`/api/triage`)은 API 실패 시 브라우저 규칙표로 즉시 대체한다.** 자유 입력 추출(`/api/extract`)도 실패하면 브라우저 키워드 추출로 대체한다. 추출에서 입력이 멈추면 문진 전체가 늦어지기 때문이다. 하단 119 버튼은 네트워크와 관계없이 늘 보인다. 나머지(리포트·접수 도우미)는 실패 시 오류 문구를 보이고 다시 시도하게 한다.
- 센터 접수함은 지금처럼 2초 주기로 `GET /api/center/cases`를 다시 부른다. 사례 수가 적어 전체 목록을 받아도 된다. 기존 `storage` 이벤트 갱신은 API 모드에서 끈다.
- 근로자 상태(언어, 동의, 현재 입력, 프로필, 리포트)는 계속 브라우저에 둔다. 근로자 Google 로그인(backlog 21)을 켜면 서버는 계정 키와 세션 해시만 저장하고 이름·이메일·프로필·리포트는 저장하지 않는다.

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
| `CENTER_HOURS` | `09:00-18:00` | `HH:00-HH:00`(일~목 고정, 시 단위) | `/api/meta`, 운영 시간 외 판정(`afterHours`), 다음 운영일, mock 사례·통계 |
| `INFO_DATE` | `2026-10-24` | `YYYY-MM-DD` | `/api/meta`, `/api/route`의 `infoDate` |
| `CORS_ORIGINS` | `http://localhost:5180` | 쉼표 구분 출처 목록 | CORS 허용 출처 |
| `LLM_PROVIDER` | `anthropic` | `anthropic`만 지원 | LLM 어댑터 선택 |
| `LLM_MODEL` | `claude-haiku-5-5` | 공급자 모델 이름 | LLM 호출 |
| `LLM_API_KEY` | (없음) | 공급자 API 키 | 비어 있으면 LLM을 쓰지 않는다 |
| `LLM_TIMEOUT_S` | `10` | 0보다 큰 초 | LLM 호출 한 번의 시간 제한 |
| `LLM_ATTEMPTS` | `2` | 1 이상 정수 | 첫 호출 + 재시도 횟수 |
| `LLM_RATE_PER_MIN` | `0`(끔) | 0 이상 정수 | 클라이언트 IP별 최근 60초 LLM 호출 수 상한(backlog 20) |
| `LLM_DAILY_LIMIT` | `0`(끔) | 0 이상 정수 | 서버 전체 하루(Asia/Seoul) LLM 호출 수 상한(backlog 20) |
| `LLM_CLIENT_IP_HEADER` | (없음) | 소문자 헤더 이름, 예: `cf-connecting-ip` | TCP 상대가 루프백일 때만 이 헤더를 클라이언트 IP로 쓴다 |
| `DB_PATH` | (없음) | 파일 경로(폴더는 있어야 함), 예: `./center.db` | 센터 사례 저장소. 비어 있으면 메모리, 있으면 SQLite 파일 |
| `STATIC_DIR` | (없음) | `index.html`이 있는 폴더, 예: `../frontend/dist` | 프론트 빌드 서빙. 비어 있으면 API만 띄우고 `/`는 404다 |
| `APP_STATIC_DIR` | (없음) | `index.html`이 있는 폴더, 예: `../app-front/dist` | 앱용 웹 빌드(backlog 22). `APP_HOSTS`의 호스트로 온 요청에는 `STATIC_DIR` 대신 이것을 준다. `APP_HOSTS`·`STATIC_DIR`과 함께 있어야 한다 |
| `APP_HOSTS` | (없음) | 쉼표 구분 호스트 이름(포트 없이), 예: `app.for-nav.com` | 요청의 `Host`가 여기 있으면 앱용 웹 빌드를 준다. 대소문자·포트는 보지 않는다 |
| `MODEL_DIR` | (없음) | 있는 폴더(`../modeling/models`) | 진료과 모델. 비어 있으면 모델 없이 규칙표로 동작한다 |
| `CENTER_AUTH` | `off` | `off` \| `email` | 센터 직원 로그인(backlog 17). `email`이면 `DB_PATH`가 있어야 한다 |
| `MAIL_PROVIDER` | `resend` | `resend` \| `console` | 로그인 코드 메일. `console`은 코드를 서버 표준 출력에 찍는다(로컬 개발 전용, `CENTER_COOKIE_SECURE=false`일 때만 허용) |
| `MAIL_API_KEY` | (없음) | Resend API 키 | `resend`이면 있어야 한다 |
| `MAIL_FROM` | (없음) | 예: `for-nav 센터 <no-reply@for-nav.com>` | 보내는 사람. `resend`이면 있어야 한다(Resend에서 인증한 도메인) |
| `CENTER_SESSION_DAYS` | `30` | 1 이상 정수 | 직원 세션 길이(일) |
| `CENTER_COOKIE_SECURE` | `true` | `true` \| `false` | 세션 쿠키의 `Secure`(센터·근로자 둘 다). 로컬 http 개발에서만 `false` |
| `WORKER_AUTH` | `off` | `off` \| `google` | 근로자 Google 로그인(backlog 21). `google`이면 `DB_PATH`·`GOOGLE_CLIENT_ID`가 있어야 한다 |
| `GOOGLE_CLIENT_ID` | (없음) | `….apps.googleusercontent.com` | Google OAuth 웹 클라이언트 ID. ID 토큰의 `aud`와 비교한다. 프론트 `VITE_GOOGLE_CLIENT_ID`와 같은 값(비밀값이 아니다) |
| `WORKER_SESSION_DAYS` | `30` | 1 이상 정수 | 근로자 세션 길이(일) |

값이 형식에 맞지 않으면 서버가 시작하지 않는다. 동기화 테스트(`parity.json`)는 기본값으로 만들었으므로 `uv run pytest`는 이 변수들이 없는 상태에서 돌린다.

### LLM

**키가 없으면 템플릿으로 동작한다.** `LLM_API_KEY`가 비어 있으면 `get_llm_client()`가 `None`을 돌려주고, LLM 자리(추출·템플릿 슬롯·번역)는 지금 규칙·템플릿을 그대로 쓴다. LLM이 쓴 한국어 문장은 `templates/guard.py` 검사를 통과해야 내보낸다. 키가 있어도 호출이 시간 제한을 넘기거나 출력이 스키마에 맞지 않으면 `LLM_ATTEMPTS`번까지 시도한 뒤 같은 기본값으로 돌아간다. LLM 실패는 API 실패가 되지 않는다(발표장 네트워크 대비).

- 출력은 Pydantic 모델의 JSON 스키마로 고정한다(Anthropic `output_config.format`). 받은 뒤에도 같은 모델로 다시 검증한다.
- 로그에는 시도 횟수와 실패 종류(`llm attempt=1/2 failed=LLMError/RateLimitError`)만 남는다. 프롬프트·응답 원문은 로그·예외에 들어가지 않는다.
- SDK 자체 재시도는 끄고 재시도는 `generate()` 한 곳에서만 한다.
- 서버는 시작 시(lifespan) 클라이언트를 한 번 만들어 `app.state.llm`에 두고 종료 시 닫는다.
- **호출 제한(backlog 20).** 공급자 호출 한 번(재시도 포함)을 하나로 세고, 클라이언트 IP별 최근 60초 `LLM_RATE_PER_MIN`번, 서버 전체 하루(Asia/Seoul) `LLM_DAILY_LIMIT`번까지 부른다. 넘으면 그 호출은 `LLMError(limited)`로 실패하고 재시도 없이 키가 없을 때와 같은 대체 결과(키워드·기본 템플릿·원문, `skipped`)로 응답한다. API와 상태 코드는 바뀌지 않는다. 근로자 경로와 통화 자막 번역이 같은 제한을 쓴다. 기본값 0은 제한 없음이고, 맥미니는 `deploy/ecosystem.config.cjs`가 60·3000을 켠다. 제한 상태는 프로세스 메모리라 다시 띄우면 0부터 센다. 막힐 때 로그는 `llm limited scope=ip|daily` 한 줄이고 IP는 남기지 않는다.
- 클라이언트 IP는 TCP 상대 주소다. `LLM_CLIENT_IP_HEADER`(맥미니 `cf-connecting-ip`)를 주면 상대가 `127.0.0.1`·`::1`(같은 기기의 Cloudflare 터널)일 때만 그 헤더 값을 쓴다. 서버가 `0.0.0.0`으로 떠 있어 같은 망에서 직접 붙은 클라이언트는 헤더를 꾸밀 수 있기 때문이다.
- 테스트는 가짜 LLM으로 돌고 키·네트워크가 필요 없다. 실제 공급자 확인은 손으로 한 번 돌린다.

```sh
uv run --env-file .env python scripts/llm_smoke.py   # 모델 이름, 소요 시간, 스키마 통과 여부만 찍는다
uv run --env-file .env python scripts/extract_compare.py   # 픽스처 자유 입력의 LLM·키워드 추출 비교(번호와 열거값만 찍는다)
uv run --env-file .env python scripts/slots_check.py       # 픽스처 자유 입력의 상황 줄 요약 guard 통과 건수(번호·글자 수·검사 결과만 찍는다)
uv run --env-file .env python scripts/translate_check.py   # 픽스처 자유 입력의 번역 수락·거부 건수와 소요 시간(번호·언어·결과·초만 찍는다)
```

### 모델

`MODEL_DIR`이 있으면 시작 시 `modeling/models`의 아티팩트(LightGBM 텍스트·JSON, `metadata.json`의 sha256 확인)를 한 번 읽어 `app.state.model`에 둔다. 아티팩트가 없거나 깨졌으면 서버가 뜨지 않는다. `fornav_modeling`은 `uv sync`가 `../modeling`에서 editable로 설치한다(`[tool.uv.sources]`, backlog 12). 모델 버전·피처·임계값은 `modeling/src/fornav_modeling/predict.py`와 `metadata.json`이 정하고 서버에 다시 적지 않는다.

```sh
MODEL_DIR=../modeling/models uv run fastapi dev app/main.py
```

테스트는 가짜 `predict`로 돌고 `modeling` 코드를 import하지 않는다.

프론트와 함께 띄울 때:

```sh
uv run --directory backend fastapi dev app/main.py
VITE_API_BASE=/api npm --prefix frontend run dev
```

### 발표용 실행(서버 하나, 같은 출처)

근로자 화면·센터 화면·API를 한 주소에서 띄운다. 같은 Wi-Fi의 휴대폰에서 `http://<맥 IP>:8000/`로 근로자 화면을 열고, PC에서 `/center`로 접수함을 본다.

```sh
VITE_API_BASE=/api npm --prefix ../frontend run build   # 프론트를 API 모드로 빌드(frontend/dist)
STATIC_DIR=../frontend/dist uv run fastapi run app/main.py --host 0.0.0.0
ipconfig getifaddr en0                                   # 맥 IP(Wi-Fi)
```

- `/api/*`가 먼저 매칭되고, 나머지 경로는 빌드 폴더의 파일, 없으면 `index.html`이다(프론트 라우팅 `/center` 등). 확장자가 있는 없는 파일(`/assets/x.js`)은 404다.
- 프론트를 API 모드(`VITE_API_BASE=/api`)로 빌드해야 같은 출처의 `/api`를 부른다. 단독 모드로 빌드하면 서버가 떠 있어도 브라우저 안 mock만 쓴다.
- 시연 전에 휴대폰에서 진료과 추천 실패 시 브라우저 규칙 대체가 동작하는지(서버를 잠깐 끄고 증상 입력) 확인한다.
- 필요하면 `DB_PATH`, `MODEL_DIR`, `LLM_API_KEY`를 같은 명령에 더한다.
- 상담 채팅의 열린 연결은 프로세스 메모리에 있으므로 `--workers`를 더하지 않는다(2 이상이면 같은 사례의 근로자·센터가 다른 프로세스에 붙어 서로 받지 못한다).

### 맥미니 배포

`main`에 병합되면 GitHub Actions(`.github/workflows/deploy-backend.yml`)가 맥미니에 SSH(포트 2222)로 접속해 `~/srv/for-nav`(없으면 클론)에서 `git pull --ff-only origin main` 뒤 `backend/deploy/deploy.sh`를 돌린다. `backend/`·`frontend/`·`app-front/`·모델링 코드와 모델이 바뀐 병합만 배포하고, 문서(`*.md`)만 바뀐 병합은 배포하지 않는다. Actions 탭에서 "Deploy backend (Mac mini)"를 직접 실행할 수도 있다.

`deploy.sh` 흐름: `backend/.env`의 `GOOGLE_CLIENT_ID`를 읽어 두 빌드에 `VITE_GOOGLE_CLIENT_ID`로 넘긴다(없으면 빈 값) → 프론트를 API 모드로 `backend/deploy/static.next`에, 앱용 웹(`app-front`)을 `backend/deploy/static-app.next`에 빌드 → `uv sync --frozen --no-dev` → 둘을 `static`·`static-app`으로 함께 바꿔 끼우기 → pm2 앱 `for-nav` 다시 띄우기 → `/api/health` 확인(30초). 빌드나 의존성 설치가 하나라도 실패하면 떠 있는 서버와 `static`·`static-app`은 그대로 두고 멈춘다. 서버는 `http://<맥미니>:8000/`(근로자 화면), `/center`(센터 화면), `/api/*`를 한 주소에서 서빙하고, 모델(`modeling/models`)을 붙여 띄운다.

호스트별 빌드(backlog 22): `Host`가 `app.for-nav.com`인 요청에는 앱용 웹 빌드(`static-app`, Flutter 앱이 불러오는 화면. 브라우저에서도 같은 근로자 화면이다)를, 나머지(`www.for-nav.com` 등)에는 `frontend` 빌드(`static`)를 준다. `/api/*`는 호스트와 관계없이 같다. Cloudflare 터널은 공개 주소의 `Host`를 그대로 넘긴다(터널 설정에 `httpHostHeader`를 두지 않는다).

처음 한 번 준비할 것:

1. 맥미니에 도구를 둔다: Homebrew `uv`·`libomp`(LightGBM 모델을 불러올 때 필요하다. 없으면 서버가 `Library not loaded: @rpath/libomp.dylib`로 뜨지 못한다), nvm Node 22 이상(`nvm install 22`), `npm i -g pm2`(nvm Node 22에 설치), 재부팅 뒤 자동 시작이 필요하면 `pm2 startup`.
2. 클론(`~/srv/for-nav`)은 없으면 워크플로가 첫 배포 때 만든다. 미리 받아 두려면 아래처럼 한다. 이 폴더에서는 파일을 손으로 고치지 않는다(`git pull --ff-only`가 실패한다).
   ```sh
   mkdir -p ~/srv && git clone https://github.com/conceptamin/for-nav.git ~/srv/for-nav
   ```
3. 필요하면 `~/srv/for-nav/backend/.env`를 만든다(`.env.example` 참고). 없으면 기본값(LLM 없음, 메모리 저장소)으로 뜬다. 첫 배포 뒤에 만들었으면 4번처럼 한 번 다시 돌린다. `STATIC_DIR`·`APP_STATIC_DIR`·`APP_HOSTS`·`MODEL_DIR`은 pm2 설정이 정하므로 넣지 않는다. `DB_PATH`를 넣으면 연락처·자유 입력이 평문 파일로 남는다.
4. 클론을 미리 받았으면 맥미니에서 한 번 직접 돌려 본다: `bash ~/srv/for-nav/backend/deploy/deploy.sh` → `배포 완료`
5. GitHub 저장소 Settings → Secrets and variables → Actions에 secrets 3개를 넣는다.

| secret | 값 |
|---|---|
| `MAC_MINI_IP` | 맥미니의 외부 IP 또는 도메인(SSH 포트 2222로 열려 있는 주소) |
| `MAC_MINI_USERNAME` | 맥미니 로그인 사용자 |
| `MAC_MINI_SSH_KEY` | 맥미니 `~/.ssh/authorized_keys`에 공개키가 등록된 개인키 전체 |

- 포트를 바꾸려면 `PORT=8080 bash backend/deploy/deploy.sh`처럼 넘긴다. 워크플로는 8000을 쓴다.
- 서버 로그는 `pm2 logs for-nav`, 상태는 `pm2 status`로 본다. 배포가 실패하면 Actions 로그 끝에 pm2 로그 40줄이 찍힌다.

센터 직원 로그인 켜기(backlog 17):

1. Resend에 가입하고 Domains에 `for-nav.com`을 더한 뒤, 안내하는 DNS 레코드(SPF·DKIM 등)를 Cloudflare DNS에 그대로 넣는다(프록시 끔). 인증되면 API Keys에서 보내기 전용 키를 만든다.
2. `~/srv/for-nav/backend/.env`에 넣는다(커밋하지 않는다).
   ```sh
   CENTER_AUTH=email
   DB_PATH=/Users/<사용자>/srv/for-nav-data/center.db
   MAIL_PROVIDER=resend
   MAIL_API_KEY=re_...
   MAIL_FROM="for-nav 센터 <no-reply@for-nav.com>"
   ```
   `DB_PATH`는 클론 밖 폴더에 둔다(폴더는 미리 만든다). 연락처·자유 입력·채팅·통화 자막도 이 파일에 평문으로 남는다.
3. 직원을 등록한다: `cd ~/srv/for-nav/backend && uv run --env-file .env python scripts/staff.py add staff@example.org` (`list`, `remove`도 같다). 서버를 다시 띄울 필요는 없다.
4. `bash ~/srv/for-nav/backend/deploy/deploy.sh`로 한 번 다시 띄운다(`.env`를 새로 읽는다).

근로자 Google 로그인 켜기(backlog 21):

1. Google Cloud 콘솔 → API 및 서비스 → OAuth 동의 화면을 만든다(외부. 게시 전에는 테스트 사용자로 등록한 계정만 로그인된다).
2. 사용자 인증 정보 → OAuth 클라이언트 ID → **웹 애플리케이션**. 승인된 JavaScript 원본에 `http://localhost`, `http://localhost:5180`, 배포 출처(`https://app.for-nav.com`, `https://www.for-nav.com`, Funnel 주소를 쓰면 그 주소)를 넣는다. 리디렉션 URI와 클라이언트 보안 비밀번호는 쓰지 않는다.
3. `~/srv/for-nav/backend/.env`에 넣고(센터 로그인과 같은 `DB_PATH`를 쓴다) 4번처럼 다시 띄운다.
   ```sh
   WORKER_AUTH=google
   GOOGLE_CLIENT_ID=123-abc.apps.googleusercontent.com
   ```
4. 프론트·앱용 웹 빌드에는 `deploy.sh`가 같은 값을 `VITE_GOOGLE_CLIENT_ID`로 넣는다(frontend 28). 따로 할 일은 없다. 배포 로그의 `▶ Google 클라이언트 ID: 있음`으로 확인한다.
- 휴대폰 등 외부에서 접속하려면 맥미니 공유기에서 8000 포트를 열거나 앞에 프록시를 둔다. 이 설정은 배포 워크플로 밖이다.

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
| `TriageResult.department` | 규칙표, `MODEL_DIR`이 있으면 막연한 분기(고정 조합 제외)만 진료과 앙상블(모델 A + B) 상위 2개 — 붙임(backlog 06) | 같음 |
| `POST /api/extract` | 키가 있으면 LLM(JSON 스키마 고정), 없거나 실패하면 다국어 키워드 사전 — 붙임(backlog 03) | 같음. 부위·증상이 비면 버튼 질문 |
| 템플릿 문장 | 키가 있으면 자유 입력 요약으로 상황 줄 슬롯을 채우고, 없거나 실패·검사 탈락이면 기본 템플릿 — 붙임(backlog 04) | 같음 |
| 리포트 `note` 번역 | 키가 있으면 LLM 번역 + 역번역 검사, 없거나 실패·불일치면 원문 + "(원문, 번역 미연결)" — 붙임(backlog 05) | 같음 |
| 센터 저장소 | 프로세스 메모리, `DB_PATH`가 있으면 SQLite 파일 — 붙임(backlog 07) | 서버 DB(보존 기간·암호화는 미결) |
| 상담 채팅 센터 인증 | `CENTER_AUTH=email`이면 직원 이메일 코드 로그인 세션이 있어야 `role=center`로 붙는다 — 붙임(backlog 17). `off`(기본)이면 역할만으로 붙는다 | 상담자별 권한, 담당자 지정, 처리 직원 기록 |
| 상담 채팅 번역 | 원문 그대로 주고받는다(backlog 14) | 리포트 `note` 번역(backlog 05)과 같은 LLM 번역 + 역번역 검사. `ChatMessage`에 선택 필드(`textKo`, `translation`)로 더한다 |
| 통화 연결(TURN) | STUN만 쓴다(주소는 프론트가 정한다). 같은 와이파이·대부분의 망에서 붙지만 이동통신망끼리는 실패할 수 있다(backlog 16) | TURN 서버와 짧게 유효한 자격 증명을 내주는 경로 |
| 통화 기록 | 자막을 사례별로 저장, 음성은 저장하지 않음 — 붙임(backlog 18). 연결 직후 `history`로 다시 준다 | 자막 기록 동의, 보존 기간·자동 삭제·암호화(채팅 메시지와 함께 정한다) |
| 상담 채팅 중계 | 프로세스 하나의 메모리(`ChatHub`) — 붙임(backlog 14) | 다중 프로세스·서버면 Redis pub/sub 등 중계(그때 socket.io 재검토) |
| LLM 호출 제한 | IP별 60초·서버 전체 하루 호출 수, 프로세스 메모리, 넘으면 대체 동작 — 붙임(backlog 20) | 공유 저장소(Redis 등)의 제한, 사용자·기관별 할당, 토큰·금액 기준 예산 |

모델 결과는 선택 필드 `TriageResult.model`(`{ departmentProba }`)로 더했다. 규칙표가 먼저고, 모델은 막연한 분기만 바꾼다. 응급 여부 판정(응급 키워드·보조 점수·응급도 모델)은 backlog 26에서 지웠다.

## 확인이 필요한 값

프론트 `README.md`의 미결 사항을 그대로 따른다. 코드를 고치지 않고 바꿀 수 있도록 환경 변수로 빼 두었다("실행"의 환경 변수 표).

- 센터 운영 시간: 일~목 09:00~18:00(센터 확인 2026-10-31). 시간은 `CENTER_HOURS`, 요일은 `app/settings.py`의 `WORKDAYS`
- 정보 기준일 → `INFO_DATE`. 발표 전 재확인
- 기관 대표번호(`KCOMWEL`, `NHIS`)는 공개 번호라 `app/rules/coverage.py` 상수로 둔다. 발표 전 재확인
- 센터·울산시 지원 연락처는 미확인이므로 `phone: null` 유지
