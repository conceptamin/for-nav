# 울산 외국인 의료 내비게이터 — 프론트엔드

울산의 외국인 근로자가 증상을 버튼으로 고르면 응급 여부·진료과·제도 경로·접수 문장을 모국어와 한국어로 보여 주는 웹앱(Vite + React + TypeScript)이다. 근로자 화면(모바일)과 센터 화면(PC)이 한 앱 안에 경로로 나뉘어 있다. 화면 목록과 경로는 `PRD_울산외국인의료내비게이터.md`(v1.0) 8장을 따른다.

규칙 엔진·템플릿·mock 데이터는 `src/domain/`과 `src/data/`에 있어 **백엔드 없이도 전부 동작한다.** 백엔드(`../backend/`, FastAPI)는 이 로직을 "같은 입력이면 같은 결과"가 나오도록 옮긴 서버이고, 프론트는 `src/api/` 계층을 통해 둘 중 하나를 쓴다. 어느 화면이 어떤 경로를 어떻게 부르고 실패하면 어떻게 하는지는 아래 "API 연결"이 정한다.

이 폴더의 문서는 역할이 나뉜다.

| 문서 | 정하는 것 |
|---|---|
| `README.md` (이 문서) | 무엇을 만드는지 — 화면, 폴더, API 연결 정책, 상태의 경계, 나중에 붙일 자리 |
| `design.md` | 화면을 어떻게 그리는지 — SEED Design 토큰·컴포넌트와 글래스모피즘 |
| `CLAUDE.md` | 코드로 옮길 때 지키는 규칙 |
| `backlog/` | 무엇을 언제 만드는지. 항목 하나가 PR 하나다 |

## 실행

```sh
npm install
npm run dev        # 단독 모드 http://localhost:5180 — 브라우저 안의 규칙·mock만 쓴다
npm run build      # 타입 검사 + 정적 빌드(dist/)
```

백엔드와 함께 띄우는 API 모드(`src/api/` 계층이 생기는 backlog 01부터):

```sh
uv run --directory ../backend fastapi dev app/main.py   # http://localhost:8000
VITE_API_BASE=/api npm run dev                          # Vite 프록시가 /api → :8000 으로 넘긴다
```

- 근로자 화면(모바일): `http://localhost:5180/`
- 센터 화면(PC): `http://localhost:5180/center` — 다른 탭이나 다른 기기에 열어 두면 근로자가 보낸 사례가 2초 안에 맨 위에 나타난다. 다른 기기 시연은 API 모드에서만 된다.
- 센터 접수함의 **접수함 초기화** 버튼으로 실제 전송 사례를 지울 수 있다.
- 발표용으로 서버 하나만 띄우는 방법(프론트 빌드를 FastAPI가 서빙)은 backend 08 이후 `backend/README.md`에 적는다.

## 배포

`main`에 병합되면 GitHub Actions(`.github/workflows/deploy-frontend.yml`)가 `frontend/`를 Vercel production에 올린다. `frontend/` 밖만 바뀐 병합은 배포하지 않는다. Actions 탭에서 "Deploy frontend"를 직접 실행할 수도 있다.

흐름: `npm ci` → `vercel pull`(프로젝트 설정·환경 변수 내려받기) → `vercel build`(`npm run build`, 타입 검사 포함) → `vercel deploy --prebuilt --prod`. 빌드가 실패하면 배포하지 않는다. Vercel 쪽 Git 연동은 쓰지 않는다(연결하면 두 번 배포된다).

처음 한 번 준비할 것:

1. Vercel 프로젝트를 만들고 이 폴더를 연결한다. 프로젝트의 Root Directory는 비워 둔다(워크플로가 `frontend/` 안에서 돈다).
   ```sh
   cd frontend
   npx vercel@latest link          # 로그인 → 새 프로젝트 생성 → .vercel/project.json 생성(커밋하지 않는다)
   cat .vercel/project.json        # orgId, projectId
   ```
2. https://vercel.com/account/tokens 에서 토큰을 만든다.
3. 저장소 secrets에 넣는다.
   ```sh
   gh secret set VERCEL_TOKEN
   gh secret set VERCEL_ORG_ID
   gh secret set VERCEL_PROJECT_ID
   ```
4. 환경 변수는 Vercel 프로젝트 설정(Settings → Environment Variables, Production)에 둔다. 아무것도 넣지 않으면 단독 모드로 배포된다. 백엔드가 공개 주소를 갖게 되면 `VITE_API_BASE`를 그 주소로 넣는다(아래 "API 연결").

`vercel.json`은 `react-router`의 주소(`/center` 등)를 새로고침해도 `index.html`이 나오도록 모든 경로를 `index.html`로 되돌린다.

## 화면 구성

PRD 8장 경로 그대로다. 경로 표는 `src/main.tsx` 한 곳에 있다.

| ID | 경로 | 내용 |
|---|---|---|
| S-01~S-04 | `/`, `/consent`, `/signup`, `/home` | 언어 20개(한국어·네팔어·러시아어·몽골어·미얀마어·베트남어·싱할라어·아랍어·영어·우즈베크어·일본어·중국어 간체/번체·카자흐어·크메르어·키르기스어·태국어·프랑스어·필리핀어·인도네시아어, 첫 진입 때 로고 스플래시(세션당 한 번, 1.2초), 벤토 그리드: 폰 언어로 묻고 폰 언어를 큰 타일·가까운 언어를 중간 타일로 추천, 나머지는 작은 타일, 아랍어는 RTL), 3개 분리 동의(전체 동의 줄 + 항목별 전문 펼치기), 로그인(데모 Google 로그인 → 간단 프로필: 생년월일·성별만 / 비회원으로 계속), 홈(심토미 배치: 나 줄 → 아파요/다쳤어요 시작 카드 → 기능 목록 → 최근 메모) + 하단 119 고정 |
| S-05~S-07 | `/intake`, `/emergency`, `/result` | 부위·증상 칩 묶음 → 사진(브라우저 메모리만) + 자유 입력 추출 → 추가 질문(화면 하나에 질문 하나) → 분석 중 화면 → 응급 시 119 우선, 진료과 + 카카오맵 |
| S-08 | `/coverage` | 산재 / 건강보험 / 울산 지원 / 센터 상담 경로 + 기관 최종 결정 문구·기준일 |
| S-09·S-10 | `/visit/desk`, `/visit/call` | 접수 창구용 큰 한국어 화면, 전화 스크립트(발음 표기) + 예상 질문 답변 버튼 |
| S-11 | `/report/new` → `/report/:id` | 항목 선택(기본 전체) → 한국어·모국어 토글 리포트 |
| S-12·S-13 | `/center-request`, `/my` | 센터 요청(회원만, 전송 동의 별도, 운영 시간 외 안내, API 모드면 전송 완료 화면에 센터와 대화 채팅), 내 정보(프로필·언어 설정·내 메모·센터 요청 id·전체 삭제. 프로필 수정은 `/signup?next=/my`) |
| — | `/guide` | 병원 이용 안내 5개 항목(고정 문구) |
| C-01~C-03 | `/center`, `/center/cases/:id`, `/center/stats` | 접수함(mock 24건 + 실제 전송), 상세·상태 변경·상담 채팅(API 모드), 익명 통계(5건 미만 칸은 `<5`) |

근로자 화면의 진입 순서(언어 → 동의 → 로그인/비회원)는 `WorkerLayout`이 지킨다. 앞 단계를 건너뛰고 들어오면 그 단계로 되돌린다.

## 폴더 구조

```text
src/
  main.tsx          경로 표. PRD 화면 ID를 주석으로 단다
  pages/            worker/ (S-01~S-13, /guide), center/ (C-01~C-03)
                    화면은 api/·state/·i18n/·components/만 부른다. domain/을 직접 부르지 않는다(아래 "API 연결")
  components/       WorkerLayout(앱 바 ←·화면 이름·언어 변경·하단 119 띠·진입 순서 가드, useScreenBar), common(Chip·Steps·YesNoSeg·SingleSelect·PainRange·PhotoPicker·Worse119·PolicyDisclaimer), ChatPanel(근로자·센터 상담 채팅)
  api/              호출 계층. http(요청·오류·WebSocket 주소), worker(근로자 경로·조용한 대체), center(센터 경로·대체 없음·접수함 구독), chat(상담 채팅 WebSocket·다시 연결), meta
                    단독/API 모드 선택과 경로별 대체 정책은 여기에만 있다
  domain/           규칙 엔진(triage·coverage·centerCase)과 템플릿(templates), 어휘(vocab) — 타입·규칙·문장의 원본
    lang/           근로자 모국어별 내용 묶음(어휘 표기·접수 도우미 문장 틀·응급 키워드). 한국어를 뺀 19개 언어가 파일 하나씩, 형태는 types.ts의 LangPack
  i18n/             근로자 고정 문구. en이 키의 기준이고 나머지 19개 언어는 같은 키를 타입으로 강제한다
    suggest.ts      S-01 언어 추천(폰 언어 → 지원 언어, 가까운 언어 표)
  state/            AppState(세션·기기 상태), centerStore(단독 모드의 센터 접수함), splash(이 세션에서 스플래시를 봤는지), storage(실패해도 멈추지 않는 저장소 래퍼)
  data/             mock 사례 24건·통계 레코드 420건(시드 고정 합성 데이터)
  styles.css        스타일 한 파일. 그리는 규칙은 design.md
scripts/
  dump-fixtures.ts  백엔드 동기화 테스트 입력. 프론트 규칙·템플릿 출력을 backend/tests/fixtures/parity.json으로 내보낸다
public/             빌드 없이 그대로 서빙되는 정적 파일(Vite 기본 publicDir). logo.png = 팀 로고 마크(파비콘·로고 화면·앱 바)
backlog/            작업 항목(NN-short-name.md)
```

`src/domain/*.ts`가 원본이다. 백엔드(`backend/app/rules/`, `templates/`, `vocab.py`)와 모델링의 열거값은 이것을 옮긴 것이고, 동기화 테스트가 같음을 확인한다. 그래서 `domain/`은 API 모드에서도 지우지 않는다. 실패 시 대체 경로이자 백엔드가 맞춰야 할 기준이다.

## API 연결

### 두 모드

| 모드 | 조건 | 동작 |
|---|---|---|
| 단독 | `VITE_API_BASE`가 비어 있다 | 지금처럼 `domain/` 함수와 `centerStore`(localStorage)를 쓴다. 네트워크 요청이 없다 |
| API | `VITE_API_BASE`가 있다(개발은 `/api`, 배포는 같은 출처의 `/api`) | 아래 경로별 정책대로 서버를 부르고, 실패하면 정책대로 대체한다 |

화면 컴포넌트는 모드를 모른다. `src/api/` 함수만 부르고, 두 모드에서 같은 형태의 값을 받는다. 모드 분기와 대체 분기는 `src/api/` 밖에 두지 않는다.

### 경로별 대체 정책

실패 시 행동은 경로마다 다르고, 세 등급으로 나뉜다. **응급은 브라우저가 먼저**, 근로자 화면의 나머지는 **조용한 대체**, 센터 쪽은 **대체 없이 정직한 실패 표시**다.

| 경로 | 화면 | 서버 성공 시 | 서버 실패·시간 초과·단독 모드 | 사용자에게 보이는 것 |
|---|---|---|---|---|
| `POST /api/triage` | S-05 | 브라우저 `triage()`를 **먼저 즉시** 돌린다. 응급이면 서버를 기다리지 않고 `/emergency`로 간다. 비응급일 때만 서버를 부르고, 응답의 `model` 등 보강 필드만 덧붙인다. 서버가 응급이면 응급이다 | 브라우저 결과 그대로 | 없음. 응급 판정은 네트워크를 기다리지 않는다 |
| `POST /api/extract` | S-05 자유 입력 | 서버 결과(LLM 또는 키워드)로 빈 항목을 채운다. 버튼으로 고른 값이 우선이다 | 브라우저 키워드 사전 | `source`에 따라 "키워드 사전으로 채움" 한 줄(`notice.info`) |
| `POST /api/route` | S-08 | 서버 결과 | 브라우저 `routeCoverage()` | 없음(결과가 같다) |
| `POST /api/visit-helper` | S-09·S-10 | 서버 템플릿. `llmSlots`가 있으면 그 슬롯만 LLM 문장이다 | 브라우저 템플릿 | 없음. LLM 슬롯이 빠진 것은 표시하지 않는다(기본 템플릿도 완성된 문장이다) |
| `POST /api/report/clinician`, `POST /api/report/center` | S-11, S-12 미리보기 | 서버 템플릿. `translation.status`가 `ok`면 번역이 붙는다 | 브라우저 템플릿 | 번역이 없으면 지금처럼 "(원문, 번역 미연결)" |
| `GET /api/meta` | 앱 시작 | `infoDate`, `centerHours`를 서버 값으로 바꾼다 | 브라우저 상수(`INFO_DATE`, `CENTER_HOURS`) | 없음 |
| `POST /api/center/cases` | S-12 전송 | 서버가 저장하고 돌려준 `case`·`nextOpenDate`를 보여 준다 | **대체하지 않는다.** 전송 실패 문구와 다시 시도 버튼. localStorage에 넣지 않는다 | 명시적 실패(`notice.danger`) |
| `GET /api/center/cases`, `GET /api/center/cases/{id}`, `PATCH`, `POST /api/center/reset`, `GET /api/center/stats` | C-01~C-03 | 2초 주기 폴링. `storage` 이벤트 갱신은 끈다. 통계는 집계 결과만 받아 그린다 | **대체하지 않는다.** 마지막으로 받은 목록을 그대로 두고 상단에 "서버 연결 안 됨" 띠를 띄운다. 상태 변경·초기화는 실패 문구 | 명시적 실패(상단 띠) |
| `WS /api/center/cases/{id}/chat` | S-12 전송 완료, C-02 | 연결 직후 `history`로 목록을 통째로 받고, 이후 `message`를 덧붙인다. 내 글도 서버가 되돌려 준 것만 그린다 | **대체하지 않는다.** 단독 모드는 채팅을 숨긴다. 끊기면 3초 뒤 다시 연결하고, `4403`·`4404`·`4000`(데모 초기화)이면 멈춘다. 보내지 못한 입력은 남는다 | 채팅 안 상태 줄("다시 연결 중", 멈춤은 `notice.warn`), 서버가 거절한 글은 `notice.danger` |

센터 경로를 대체하지 않는 이유: 센터 화면의 목적이 "다른 기기에서 보낸 사례가 도착하는 것"이라, localStorage로 대체하면 도착한 것처럼 보이는 가짜 성공이 된다.

### 비동기 UX 규칙

지금 화면은 전부 동기 함수를 부르므로 로딩 상태가 없다. API 모드가 되면 아래를 지킨다.

- **기다리는 동안 다음 버튼을 막는다.** 스피너를 새로 만들지 않는다. 버튼 비활성(`disabled`)만 쓴다. 두 번 눌리는 것을 막는 것이 목적이다.
- **시간 제한은 `src/api/` 상수다.** 응급 판정 3초, 추출 8초(backlog 01), 제도 경로·접수 도우미·리포트·센터 요약 8초, `/api/meta` 3초(backlog 02), 센터 경로 5초와 접수함 다시 읽기 2초(backlog 03), 상담 채팅 다시 연결 3초(backlog 25). 화면 코드에 숫자를 쓰지 않는다.
- **버튼 없이 바로 뜨는 결과는 브라우저 결과를 먼저 그린다.** 제도 경로(S-08), 접수 창구(S-09), 전화 스크립트(S-10), 센터 요약 미리보기(S-12)는 브라우저 함수 결과를 곧바로 보여 주고, 서버 결과가 오면 그것으로 바꾼다(`src/api/useServerResult.ts`). 서버가 실패하거나 느리면 브라우저 결과가 그대로 남는다. 버튼을 눌러 만드는 의료진 리포트(S-11)만 서버를 기다린다.
- **조용한 대체는 작은 줄로만 알린다.** 대체했다는 사실은 결과 아래 `notice.info` 한 줄이고, 결과 자체를 바꾸거나 가리지 않는다. 결과가 같은 경로(제도 경로·템플릿)는 알리지 않는다.
- **명시적 실패는 다시 시도할 수 있어야 한다.** 센터 전송 실패와 센터 상태 변경 실패는 실패 문구 옆에 다시 시도 버튼을 둔다. 입력한 값은 지우지 않는다.
- **응급 화면은 네트워크와 무관하게 뜬다.** `/emergency`로 가는 경로에 비동기 호출을 두지 않는다.
- 요청 본문·자유 입력·응답 원문을 `console`에 찍지 않는다. 오류는 `requestId`와 `code`만 남긴다.

### 타입과 검증

- 요청·응답 타입은 `src/domain/*.ts`의 타입을 그대로 쓴다. 백엔드가 Pydantic으로 1:1을 보장하고 동기화 테스트가 같음을 확인하므로, 프론트는 런타임 스키마 검증 라이브러리를 넣지 않는다.
- 응답은 `as` 단언으로 받되, 없으면 안 되는 필드(`emergency`, `department`, `case.id`)가 비면 실패로 보고 대체 정책을 탄다.
- API 모드 시작 시 `/api/meta`를 한 번 부른다. 실패하면 브라우저 상수를 쓴다.
- 센터 화면의 "서버 연결 안 됨" 띠는 접수함 다시 읽기(`GET /api/center/cases`)의 성공·실패만 본다. 서버가 꺼져 있으면 다음 주기(2초 안)에, 응답이 없으면 시간 제한까지 더해 7초 안에 뜬다. 다시 성공하면 바로 사라진다.
- 백엔드가 응답에 더하는 선택 필드(`source`, `llmSlots`, `translation`, `model`)는 `domain/`의 타입에 선택 필드로 더한다. 기존 필드의 이름·타입·의미는 바꾸지 않는다.

## 상태의 경계

서버는 회원 정보를 저장하지 않는다. 근로자 상태는 전부 브라우저에 있고, 센터 사례만 서버에 있다.

| 어디 | 무엇 | 키 |
|---|---|---|
| sessionStorage | 언어, 동의, 이용 방식, 현재 증상 입력·판정, 응급 이력, 제도 경로 결과, 비회원 리포트, 상담 채팅 토큰(사례 id별, API 모드) | `umn.session` |
| localStorage | 회원 프로필(생년월일·성별), 회원 리포트, 내가 보낸 센터 사례 id | `umn.device` |
| localStorage(단독 모드만) | 센터 접수함의 실제 전송 사례와 상태 변경 | `umn.center.*` |
| 서버(API 모드) | 센터 사례와 상담 채팅 메시지. 요약·긴급도·운영 시간 외 여부·id·접수 시각, 메시지의 id·보낸 쪽·시각은 서버가 정한다 | — |

- 비회원 입력은 브라우저 세션이 끝나면 사라진다. 이름·연락처·체류 자격은 받지 않는다.
- 센터 요청(S-12)의 연락처는 전송 본문에만 들어가고 브라우저에 남기지 않는다.
- `storage.ts`의 읽기·쓰기는 실패해도 예외를 내지 않는다(사생활 보호 모드 대비).

## 나중에 붙일 자리

백엔드가 선택 필드로 더하는 것을 화면이 보여 줄 자리다. 필드가 없으면 지금 화면 그대로다.

| 필드 | 백엔드 항목 | 화면 | 보여 주는 방법 |
|---|---|---|---|
| `extract.source` | backend 03·09(완료) | S-05 | 키워드 사전으로 채웠을 때만 `notice.info` 한 줄 |
| `TriageResult.model` | backend 06 | C-02 | 센터 상세에 모델 응급 확률·진료과 확률·SHAP 상위 요인. 근로자 화면에는 보이지 않는다 |
| `llmSlots` | backend 04 | S-09·S-10·S-11 | 표시 없음. 문장이 그대로 바뀐다 |
| `translation.status` | backend 05 | S-11, S-12 미리보기 | `ok`면 "번역 (원문)", 아니면 지금처럼 "(원문, 번역 미연결)" |
| 같은 출처 서빙 | backend 08 | 전체 | 빌드 설정은 바뀌지 않는다. `VITE_API_BASE=/api`로 빌드하면 된다 |
| `ChatMessage.textKo`·`translation` | backend 14 메모(미정) | S-12 채팅, C-02 채팅 | 지금은 원문만 오간다. 번역이 붙으면 말풍선 원문 아래에 번역 줄을 더한다 |

## 실서비스와 다른 점

| 항목 | 지금 | 실서비스(PRD) |
|---|---|---|
| 응급 감지 | 키워드 규칙 OR 보조 점수(`modelScore`, 모델 자리 표시) | 키워드 규칙 OR 학습 모델(backend 06) |
| 증상 추출 | 단독 모드 키워드 사전 / API 모드 LLM(실패 시 키워드 사전) | LLM(JSON 스키마 고정), 실패 시 버튼 질문 |
| 접수 문장·리포트 | 기본 템플릿 | LLM 슬롯 채우기 + 기본 템플릿 대체 |
| 자유 입력 번역 | "(원문, 번역 미연결)" | LLM 번역 + 역번역 검사 |
| 센터 DB | 단독 모드 localStorage / API 모드 서버 메모리 | 서버 DB(backend 07) |
| 테스트 | 타입 검사(`npm run build`)와 백엔드 동기화 테스트만. 프론트 단위 테스트는 없다 | — |
| CI | PR마다 `.github/workflows/ci.yml`의 `frontend` 잡이 같은 `npm run build`를 돌려 타입 오류를 잡는다 | — |

## 확인이 필요한 값(PRD 16장 미결 사항)

- 센터 운영 시간: 평일 09:00~18:00으로 **가정**(`src/domain/coverage.ts`의 `CENTER_HOURS`, API 모드에서는 `/api/meta`) — Q1
- 카카오맵 검색 링크 `https://map.kakao.com/link/search/{검색어}` 형식·사용 조건 — Q4
- 센터·울산시 의료비 지원 연락처는 넣지 않고 "센터 상담으로 확인하세요"로 표시 — Q6
- 기관 대표번호(근로복지공단 1588-0075, 국민건강보험공단 1577-1000)와 정보 기준일 `INFO_DATE`는 발표 전 재확인 필요
- 베트남어 문구·발음 표기는 원어민 검수와 역번역 검사가 필요하다(PRD 11-3). 새 문구 키를 더하는 항목은 backlog에 검수 필요를 적는다.
- 한국어를 고르면 발음 표기·모국어 뜻 줄·리포트 언어 토글·통역 요청 문장을 숨긴다(한국어를 읽을 수 있는 근로자용).
