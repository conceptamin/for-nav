# for nav — 울산 외국인 의료 내비게이터

울산의 외국인 근로자가 아픈 곳과 증상을 버튼으로 고르면 **어느 진료과로 가야 하는지, 산재·건강보험·울산 지원 중 어떤 경로를 쓸 수 있는지, 접수 창구에서 무엇이라고 말하면 되는지**를 모국어와 한국어로 보여 주는 데모 서비스다. 근로자가 센터에 도움을 요청하면 센터 직원이 PC 접수함에서 받아 채팅·통화(번역 자막)로 상담한다.

- 근로자 화면(모바일): 20개 언어, 증상 확인 → 진료과 + 근처 의원 지도 → 제도 경로 → 접수·전화 도우미 → 한국어/모국어 리포트 → 센터 요청·채팅·통화
- 센터 화면(PC): 접수함, 사례 상세·상태 변경·상담 기록, 채팅·통화, 익명 통계

**진단이 아니라 안내다.** 질환명은 보여 주지 않고, 응급 여부도 판정하지 않는다. 119는 판정 없이 늘 보이는 버튼으로 둔다.

| 주소 | 무엇 |
|---|---|
| `www.for-nav.com` | 웹(근로자 + 센터 화면) |
| `app.for-nav.com` | 근로자 앱 WebView가 불러오는 웹 |

## 저장소 구성

폴더마다 따로 실행·검사하는 프로젝트이고, 자세한 내용은 각 폴더의 `README.md`가 원본이다.

| 폴더 | 무엇 | 스택 | 자세히 |
|---|---|---|---|
| [`frontend/`](frontend/) | 근로자 화면(모바일) + 센터 화면(PC) 웹. 규칙·템플릿·mock이 브라우저 안에 있어 **백엔드 없이도 전부 동작한다** | Vite + React 19 + TypeScript | [README](frontend/README.md) · [design](frontend/design.md) |
| [`app-front/`](app-front/) | `frontend/src`를 가져와 근로자 화면만 묶고, 네이티브 호스트와 주고받는 다리(bridge)를 더한 웹 | Vite + React + TypeScript | [README](app-front/README.md) |
| [`app/`](app/) | `app-front`를 WebView 한 장으로 여는 근로자 앱 껍데기. 전화·외부 링크·뒤로 가기·마이크·Google 로그인·푸시를 맡는다 | Flutter(Android · iOS) | [README](app/README.md) |
| [`backend/`](backend/) | 프론트 규칙을 "같은 입력이면 같은 결과"로 옮긴 API 서버. 센터 접수함, 채팅·통화 시그널링, 로그인, 푸시, LLM·모델 연결 | Python 3.12 · FastAPI · uv | [README](backend/README.md) |
| [`modeling/`](modeling/) | 진료과 추천 모델(LightGBM + 소형 MLP 앙상블) 학습·평가·내보내기와 `predict()` | Python 3.12 · uv | [README](modeling/README.md) |
| [`docs/architecture/`](docs/architecture/) | 전체 구조 그림(Mermaid) | — | [화면 쪽](docs/architecture/frontend-architecture.md) · [모델링·서버](docs/architecture/modeling-backend-flow.md) |

각 폴더의 `backlog/`는 무엇을 언제 만드는지 적은 문서이고, 항목 하나가 PR 하나다. `CLAUDE.md`는 그 폴더 코드를 고칠 때 지키는 규칙이다.

## 어떻게 동작하는가

```text
근로자 앱(app/, Flutter) ─ WebView ─┐
                                    ├─ 근로자 화면 ──┐
브라우저 ────────────── frontend/ ──┤               ├─ /api, WebSocket ─→ backend/ (FastAPI)
                                    └─ 센터 화면 ────┘                      ├─ 규칙표(진료과·제도 경로)
                                                                            ├─ modeling/ predict()  (MODEL_DIR 있을 때)
                                                                            ├─ LLM(Claude Haiku)   (키 있을 때)
                                                                            └─ SQLite              (DB_PATH 있을 때)
```

- **판단은 규칙과 모델, 문장은 LLM.** 진료과는 명확한 경우 규칙(치아 → 치과 등), 나머지는 모델 앙상블이 정한다. LLM은 자유 입력 추출, 접수 문장 다듬기, 번역만 맡는다.
- **모든 바깥 의존은 꺼져도 돈다.** 모델이 없으면 규칙표, LLM 키가 없거나 실패하면 키워드 사전·기본 템플릿·원문 표시, DB가 없으면 메모리로 동작한다. 발표장 네트워크가 끊겨도 시연이 멈추지 않게 하기 위해서다.
- **두 가지 모드.** 프론트는 단독 모드(브라우저 안 규칙·mock만)와 API 모드(`VITE_API_BASE`가 있으면 서버 호출) 중 하나로 뜬다. 다른 기기 간 시연(근로자 전송 → 센터 접수함 도착)과 채팅·통화는 API 모드에서만 된다.

## 빠르게 실행하기

필요한 것: Node.js 24, Python 3.12 + [uv](https://docs.astral.sh/uv/). 앱(`app/`)까지 띄우려면 fvm으로 Flutter `3.44.7`.

### 1. 웹만 띄우기(단독 모드)

```sh
cd frontend
npm install
npm run dev        # http://localhost:5180
```

- 근로자 화면: `http://localhost:5180/`
- 센터 화면: `http://localhost:5180/center`

### 2. 서버와 함께 띄우기(API 모드)

터미널 두 개를 쓴다.

```sh
cd backend
uv sync
uv run fastapi dev app/main.py     # http://localhost:8000, API 문서: /docs
```

```sh
cd frontend
VITE_API_BASE=/api npm run dev     # Vite 프록시가 /api → :8000 으로 넘긴다
```

기본값만으로 뜬다(모델·LLM·DB·로그인·푸시 모두 꺼짐). 켜는 방법과 환경 변수 전체 목록은 [`backend/README.md`](backend/README.md) "실행"에 있다.

### 3. 근로자 앱 띄우기

`app-front`(포트 5181)를 띄우고 Flutter 앱이 그 주소를 불러오게 한다. 시뮬레이터·에뮬레이터·실기기별 주소는 [`app/README.md`](app/README.md) "실행"에 있다.

```sh
cd app-front && npm install && npm run dev -- --host 127.0.0.1
```

```sh
cd app && fvm flutter pub get && fvm flutter run --dart-define=APP_URL=http://localhost:5181
```

### 검사

| 폴더 | 명령 |
|---|---|
| `frontend/`, `app-front/` | `npm run build` (타입 검사 + 빌드) |
| `backend/`, `modeling/` | `uv run ruff check . && uv run ruff format --check . && uv run pytest` |

## CI · 배포

| 워크플로 | 언제 | 하는 일 |
|---|---|---|
| [`ci.yml`](.github/workflows/ci.yml) | 모든 PR, `main` push | `frontend` 빌드, `backend` 린트·테스트 |
| [`deploy-backend.yml`](.github/workflows/deploy-backend.yml) | `main` 병합 중 `backend`·`frontend`·`app-front`·`modeling` 코드 변경 | 맥미니에 SSH로 들어가 `git pull` → `backend/deploy/deploy.sh`(웹·앱용 웹 빌드, `uv sync`) → pm2 재시작 → `/api/health` 확인. Cloudflare 터널로 `www`·`app.for-nav.com`에 나간다 |
| [`deploy-frontend.yml`](.github/workflows/deploy-frontend.yml) | `main` 병합 중 `frontend` 변경 | `frontend`를 Vercel production에 배포 |

맥미니 준비와 secrets는 [`backend/README.md`](backend/README.md), Vercel 준비는 [`frontend/README.md`](frontend/README.md) "배포"에 있다.

## 기여 규칙

자세한 규칙은 [`CLAUDE.md`](CLAUDE.md)에 있다. 사람과 AI 모두 같은 규칙을 따른다.

- 새 작업은 최신 `main`에서 새 브랜치로 시작한다. 이름은 `<영역>/<짧은-설명>`(영역: `frontend`·`backend`·`modeling`·`docs`·`chore`).
- `main`에 직접 커밋·push하지 않고, PR(`gh pr create --base main`)로 병합한다.
- 커밋 메시지는 한국어 평서형 한 줄 + 바꾼 파일 목록 + `테스트:` 줄.
