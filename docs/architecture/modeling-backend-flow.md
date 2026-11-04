# 모델링 · 서버 흐름과 실험

for nav의 진료과 추천 모델이 어떻게 만들어지고, 서버가 요청을 어떤 순서로 처리하며, 지금까지 어떤 실험을 했는지 그림으로 정리한다. 기준은 `main`(b33d8ea, 2026-11-04)이다.

- 모델링 상세: [`modeling/README.md`](../../modeling/README.md), [`modeling/backlog/`](../../modeling/backlog/)
- 서버 상세: [`backend/README.md`](../../backend/README.md), [`backend/backlog/`](../../backend/backlog/)
- 화면 쪽 그림: [`frontend-architecture.md`](frontend-architecture.md)
- 그림 소스는 [`diagrams/`](diagrams/)의 `.mmd` 파일이다. 본문 그림을 고치면 같은 이름의 `.mmd`도 함께 고친다.

## 목차

1. [모델링](#1-모델링)
   - [1.1 학습 파이프라인](#11-학습-파이프라인)
   - [1.2 서빙 시 예측 흐름](#12-서빙-시-예측-흐름)
2. [실험](#2-실험)
3. [서버](#3-서버)
   - [3.1 구성 요소](#31-구성-요소)
   - [3.2 상담 요청 흐름](#32-상담-요청-흐름)
   - [3.3 진료과 결정: 규칙표와 모델](#33-진료과-결정-규칙표와-모델)
   - [3.4 LLM 호출과 대체 경로](#34-llm-호출과-대체-경로)
   - [3.5 실시간 채팅 · 통화](#35-실시간-채팅--통화)
   - [3.6 배포](#36-배포)

## 1. 모델링

### 1.1 학습 파이프라인

공개 데이터 두 가지(Kaggle 증상-질환, HIRA 진료과 × 질환 집계)와 수기 매핑 표로 진료과 모델 두 개를 학습하고, 두 모델을 섞는 앙상블 값을 정한다. test 셋은 `evaluate.py`만 읽고, 라운드마다 한 번만 평가한다.

```mermaid
flowchart TD
    subgraph SRC["📥 데이터 출처"]
        K[("Kaggle 증상-질환<br/>4,920행 · 41질환")]
        H[("HIRA 2025<br/>진료과 × 질환 집계")]
        G[("병원 안내 페이지<br/>SNUH 28 + 원주세브란스 1")]
        M[/"수기 매핑 표<br/>symptom_map · disease_kcd<br/>button_kcd · department_guide"/]
    end

    DL["⚙️ download_data.py<br/>내려받기 + sha256 검증"]
    SP["⚙️ make_splits.py<br/>중복 제거 → 292행 · 40질환<br/>층화 분할 seed 20261027"]
    TB["⚙️ build_tables.py<br/>질환→진료과 168행<br/>버튼→진료과 566행"]
    FE["🧩 featurize()<br/>버튼 입력 → 34개 특성"]

    A["🌲 train_dept_a.py<br/>LightGBM 40질환 분류<br/>3-fold CV → 954 rounds"]
    B["🧠 train_dept_b.py<br/>numpy MLP 29→32→10<br/>5-fold CV → L2 1e-3 · 125 epochs"]
    EN["⚖️ tune_ensemble.py<br/>weight × threshold 격자 탐색<br/>튜닝셋 73건"]
    EV{{"🔒 evaluate.py<br/>test 해시 확인 · 라운드당 1회"}}
    EX["📦 export_models.py<br/>v0/v1 → v2 복사 + sha256"]
    OUT[("💾 modeling/models/*/v2<br/>서빙 번들")]

    K --> DL
    H --> DL
    DL --> SP
    M --> SP
    DL --> TB
    M --> TB
    G --> TB
    SP -->|"train 189 · valid 44"| FE
    TB -->|"disease_department.csv"| A
    TB -->|"button_department.csv"| B
    FE --> A
    FE --> B
    A --> EN
    B --> EN
    TB -->|"가이드 29조합"| EN
    SP -.->|"test 59 (봉인)"| EV
    EN --> EV
    EV --> EX
    EX --> OUT

    classDef src fill:#E6E6FA,stroke:#333,stroke-width:2px,color:#1a1a4a
    classDef step fill:#87CEEB,stroke:#333,stroke-width:2px,color:#0a2a4a
    classDef model fill:#90EE90,stroke:#333,stroke-width:2px,color:#0a3a0a
    classDef gate fill:#FFD700,stroke:#333,stroke-width:2px,color:#000
    classDef store fill:#FFE4B5,stroke:#333,stroke-width:2px,color:#000
    class K,H,G,M src
    class DL,SP,TB,FE,EX step
    class A,B,EN model
    class EV gate
    class OUT store
```

소스: [`diagrams/m1_training_pipeline.mmd`](diagrams/m1_training_pipeline.mmd)

| 단계 | 스크립트 | 산출물 |
|---|---|---|
| 내려받기 | `scripts/download_data.py` | `data/raw/{kaggle_symptom,hira}/` |
| 분할 | `scripts/make_splits.py` | `data/processed/symptom.parquet`, `data/test/`, `data/splits/*.txt`, `reports/symptom_splits.json` |
| 표 | `scripts/build_tables.py` | `data/tables/disease_department.csv`, `button_department.csv`, `data/splits/dept_valid.txt` |
| Model A | `scripts/train_dept_a.py` | `models/dept_a/v0/` |
| Model B | `scripts/train_dept_b.py` | `models/dept_b/v0/` |
| 앙상블 | `scripts/tune_ensemble.py` | `models/ensemble/v1/` |
| 평가 | `scripts/evaluate.py --round` | `reports/*_test.{json,md}` |
| 내보내기 | `scripts/export_models.py` | `models/*/v2/` (서빙 번들) |

`train_dept_a.py`는 `build_tables.py`가 만든 `disease_department.csv`를 읽는다. 그래서 `build_tables.py`를 먼저 돌려야 한다.

**버전.** v2는 서빙 번들이다. 모델 파일은 v0·v1과 바이트 단위로 같다(A `model.txt` 8fa60486…, B `weights.json` fd6930ea…). v1은 지표를 넣은 내보내기본이고, v2는 응급도 모델 재학습 때 묶음 버전을 올린 것이다. 앙상블에는 v0가 없고, v1에서 튜닝한 값(0.5 · 0.5 · 임계 0.25)을 v2에 그대로 복사했다.

### 1.2 서빙 시 예측 흐름

서버는 `fornav_modeling.predict.predict()`를 editable path 의존성으로 불러 쓴다. 런타임 의존성은 `lightgbm`, `numpy`뿐이다.

```mermaid
flowchart TD
    IN(["📋 Intake<br/>body_parts · symptoms · onset · injury ..."])
    LOAD["📦 v2 번들 로드<br/>sha256 확인 · lru_cache"]
    FE["🧩 featurize() → 34개 특성"]

    subgraph MA["Model A"]
        A1["🌲 LightGBM<br/>40질환 확률"]
        A2["✖️ 질환→진료과 행렬<br/>departments.json"]
        A1 --> A2
    end

    subgraph MB["Model B"]
        B0{"injury 모름?"}
        B1["🧠 MLP 29특성 → 10진료과"]
        B2["➗ 외상 예/아니오 두 번 돌려 평균"]
        B0 -->|"아니오"| B1
        B0 -->|"예"| B2
    end

    MIX["⚖️ 0.5·A + 0.5·B<br/>10개 진료과 확률"]
    TH{"최대 확률 < 0.25?"}
    FB["🏥 family · internal<br/>departmentFallback = true"]
    TOP["🎯 상위 2개 진료과<br/>동점은 목록 앞쪽"]
    OUT(["📤 departmentProba · departmentTop2<br/>departmentFallback"])

    IN --> LOAD --> FE
    FE --> A1
    FE --> B0
    A2 --> MIX
    B1 --> MIX
    B2 --> MIX
    MIX --> TH
    TH -->|"예"| FB
    TH -->|"아니오"| TOP
    FB --> OUT
    TOP --> OUT

    classDef io fill:#E6E6FA,stroke:#333,stroke-width:2px,color:#1a1a4a
    classDef step fill:#87CEEB,stroke:#333,stroke-width:2px,color:#0a2a4a
    classDef model fill:#90EE90,stroke:#333,stroke-width:2px,color:#0a3a0a
    classDef gate fill:#FFD700,stroke:#333,stroke-width:2px,color:#000
    classDef warn fill:#FFB6C1,stroke:#DC143C,stroke-width:2px,color:#000
    class IN,OUT io
    class LOAD,FE,MIX,TOP step
    class A1,A2,B1,B2 model
    class TH,B0 gate
    class FB warn
```

소스: [`diagrams/m2_predict_inference.mmd`](diagrams/m2_predict_inference.mmd)

- **입력**: 34개 특성. 부위 13개와 증상 15개는 multi-hot이고, 나머지는 `pain_score`, `mental`, `age_group`, `onset`, `sex_male`, `injury`다. 학습과 서빙이 같은 `featurize()`를 쓴다.
- **빈 슬롯**: 응급도 모델을 지운 뒤에도 `pain_score`, `mental`, `age_group`, `sex` 네 칸은 늘 NaN으로 남긴다. Model A가 그 순서로 학습되었기 때문이다.
- **출력 진료과(10개)**: `ortho, surgery, internal, ophth, ent, derm, dental, neuro, family, occ`
- **응답**: `departmentProba`(10개 진료과, 합 1), `departmentTop2`, `departmentFallback`

## 2. 실험

진료과 추천은 서빙 중이고, 응급도 예측은 실험 끝에 삭제했다.

```mermaid
flowchart TD
    subgraph DEPT["🏥 진료과 추천 (서빙 중)"]
        D6["✅ 06 Model A<br/>LightGBM<br/>test Top-1 56/59 · Top-2 58/59<br/>가이드셋 Top-2 10/29"]
        D7["✅ 07 Model B<br/>표 기반 MLP<br/>test Top-1 27/59 · Top-2 45/59<br/>가이드셋 Top-2 23/29"]
        D8["✅ 08 앙상블 v1<br/>0.5 · 0.5 · 임계 0.25<br/>test Top-1 52/59 · Top-2 58/59<br/>튜닝셋 Top-2 65/73"]
        D13["⏳ 13 Model B 개선<br/>표 자체 상한 = 현재 B<br/>평가셋 확장 → v3 계획"]
        D14["⏳ 14 센터 상담 데이터<br/>어휘 커버리지 점검만"]
        D6 --> D8
        D7 --> D8
        D8 -.-> D13
        D13 -.-> D14
    end

    subgraph ACU["🚑 응급도 예측 (삭제됨)"]
        A4["✅ 04 Acuity 모델<br/>목표 응급 재현율 ≥ 95%<br/>test 재현율 42/49 = 85.7%"]
        A9["✅ 09 활력징후 추가<br/>재현율 동일 36/37<br/>응급 판정만 99 → 124 증가"]
        A10["✅ 10 모르는 입력 학습<br/>valid 응급 판정 153 → 115<br/>test 재현율 40/49"]
        A12["✅ 12 파이프라인 재현율<br/>규칙만 17/49<br/>규칙+모델 40/49"]
        A15["🗑️ 15 Acuity 제거<br/>앱은 응급 판단 안 함<br/>119 버튼 상시 노출"]
        A4 --> A9
        A9 -->|"효과 없음 → 채택 안 함"| A10
        A10 --> A12
        A12 -->|"2026-10-31 사용자 결정"| A15
    end

    classDef done fill:#90EE90,stroke:#333,stroke-width:2px,color:#0a3a0a
    classDef pending fill:#FFD700,stroke:#333,stroke-width:2px,color:#000
    classDef removed fill:#FFB6C1,stroke:#DC143C,stroke-width:2px,color:#000
    classDef past fill:#D3D3D3,stroke:#333,stroke-width:2px,color:#000
    class D6,D7,D8 done
    class D13,D14 pending
    class A4,A9,A10,A12 past
    class A15 removed
```

소스: [`diagrams/e1_experiment_history.mmd`](diagrams/e1_experiment_history.mmd)

### 진료과 모델 결과

| 모델 | test Top-1 (59건) | test Top-2 (59건) | 가이드셋 Top-2 (29조합) | 비고 |
|---|---|---|---|---|
| Model A (LightGBM) | 56 (94.9%) | 58 (98.3%) | 10 (34.5%) | 내과 질환에 강하다 |
| Model B (MLP) | 27 (45.8%) | 45 (76.3%) | 23 (79.3%) | 외상 · 병원 안내 조합에 강하다 |
| 앙상블 0.5 · 0.5 | 52 (88.1%) | 58 (98.3%) | 22 (75.9%) | 튜닝셋 Top-2 65/73, test 폴백 0/59 |

- A는 Kaggle 질환 데이터에 강하고 B는 병원 안내 조합에 강하다. 그래서 앙상블은 두 평가셋에서 모두 Top-2를 높게 유지한다.
- Top-3는 재지 않는다. 화면에 진료과를 2개만 보여 주기 때문이다.

### 응급도 실험 (backlog 04 → 15)

| 실험 | 가설 · 시도 | 결과 | 결론 |
|---|---|---|---|
| 04 Acuity 모델 | 버튼만으로 3단계 응급도를 예측해 응급 재현율 95% 이상 | test 재현율 42/49 (85.7%), 정밀도 42/129 | 목표에 못 미침 |
| 09 활력징후 | 활력징후를 더하면 나아진다 | valid 재현율 36/37로 같고, 응급 판정만 99 → 124/190으로 늘어남 | 채택 안 함 |
| 10 모르는 입력 | 마스킹한 복사본으로 모르는 입력을 학습한다 | valid 응급 판정 153 → 115/190, test 재현율 40/49 (백엔드 입력) | 과잉 판정 줄어듦 |
| 12 파이프라인 재현율 | 규칙과 모델을 합친 전체 재현율 | 규칙만 17/49, 규칙+모델 40/49. 모델이 놓친 응급을 규칙이 더 잡지 못함 | 측정 완료 |
| 15 Acuity 제거 | 2026-10-31 사용자 결정 | 서빙 출력 588건이 삭제 전후 동일 | 앱은 응급을 판단하지 않고 119 버튼을 늘 보여 준다 |

### 진행 전 (대기)

- **13 Model B 개선**: B의 가이드셋 점수(18/29, 23/29)가 표 자체의 상한과 같다. 그래서 모델 구조만 바꿔서는 오르지 않는다. 계획은 평가셋 확장 → 반복 CV → 외상 라벨 보정 → 빈 조합 채우기 → 다중 선택 합성 → 기준선 → v3와 앙상블 재튜닝이다.
- **14 센터 상담 데이터**: 비공개 상담 329건으로 어휘 커버리지만 점검한다. 학습에는 쓰지 않는다.

## 3. 서버

### 3.1 구성 요소

FastAPI 앱 하나가 API와 두 프론트엔드 정적 파일을 함께 서빙한다. 채팅 · 통화 · LLM 제한 · 푸시 상태가 메모리에 있어서 반드시 단일 프로세스로 돌린다.

```mermaid
flowchart TD
    subgraph CL["👤 클라이언트"]
        WEB["🌐 frontend<br/>www.for-nav.com"]
        APP["📱 app-front · Flutter<br/>app.for-nav.com"]
    end

    CF["☁️ Cloudflare 터널<br/>Host 헤더 그대로 전달"]

    subgraph SRV["⚙️ FastAPI · pm2 단일 프로세스 :8000"]
        MW["🛡️ RequestContext · CORS<br/>request id · access log"]
        WR["📋 worker.router /api<br/>extract · triage · route<br/>visit-helper · report"]
        CR["🏢 center.router /api/center<br/>cases · stats · chat · call"]
        AR["🔐 auth.router /api/auth<br/>이메일 코드 · Google 로그인"]
        ST["📄 정적 파일 catch-all<br/>Host로 static / static-app 선택"]
        CORE["🧩 rules · templates · model<br/>llm + LLMLimiter"]
        HUB["⚡ ChatHub · CallHub · PushNotifier<br/>메모리 상태"]
    end

    subgraph EXT["🔌 외부 · 로컬 자원"]
        LLM["🤖 Anthropic API<br/>claude-haiku-5-5"]
        MOD[("📦 modeling/models v2<br/>editable path 의존성")]
        DB[("💾 SQLite<br/>DB_PATH 없으면 메모리")]
        GID["🎫 Google ID 토큰 검증"]
        FCM["📢 FCM HTTP v1"]
        MAIL["📨 Resend 메일"]
    end

    WEB --> CF
    APP --> CF
    CF --> MW
    MW --> WR
    MW --> CR
    MW --> AR
    MW --> ST
    WR --> CORE
    CR --> CORE
    CR --> HUB
    CORE --> LLM
    CORE --> MOD
    CR --> DB
    AR --> DB
    AR --> GID
    AR --> MAIL
    HUB --> FCM

    classDef client fill:#E6E6FA,stroke:#333,stroke-width:2px,color:#1a1a4a
    classDef edge fill:#FFE4B5,stroke:#333,stroke-width:2px,color:#000
    classDef app fill:#87CEEB,stroke:#333,stroke-width:2px,color:#0a2a4a
    classDef core fill:#90EE90,stroke:#333,stroke-width:2px,color:#0a3a0a
    classDef ext fill:#D3D3D3,stroke:#333,stroke-width:2px,color:#000
    class WEB,APP client
    class CF,MW edge
    class WR,CR,AR,ST app
    class CORE,HUB core
    class LLM,MOD,DB,GID,FCM,MAIL ext
```

소스: [`diagrams/s1_backend_components.mmd`](diagrams/s1_backend_components.mmd)

### 3.2 상담 요청 흐름

엔드포인트 하나가 전부 처리하지 않는다. 프론트엔드가 단계마다 아래 순서로 호출한다.

```mermaid
sequenceDiagram
    autonumber
    actor W as 👤 이주노동자 화면
    participant API as ⚙️ FastAPI
    participant R as 🧩 규칙 엔진
    participant M as 📦 진료과 모델
    participant L as 🤖 LLM
    participant S as 💾 Store

    W->>API: POST /api/extract (자유 서술)
    API->>R: extract_from_text (키워드)
    opt LLM 사용 가능
        API->>L: LLMExtraction 스키마로 추출
        L-->>API: 부위 · 증상 · onset · work_type
    end
    API-->>W: 합친 추출 결과 (빈 칸만 채움)

    W->>API: POST /api/triage (Intake)
    API->>M: predict(intake) → departmentTop2
    API->>R: department_for (규칙표 우선)
    API-->>W: 추천 진료과 2개 · missing

    W->>API: POST /api/route
    API->>R: route_coverage (산재 → 건강보험 → 울산지원 → 센터)
    API-->>W: 경로 · 기관 · 준비 서류

    W->>API: POST /api/visit-helper
    API->>L: 한 문장 상황 요약
    L-->>API: 요약 → guard 검사
    API-->>W: 접수 시트 · 전화 대본 (실패 시 기본 템플릿)

    W->>API: POST /api/report/clinician · /center
    API->>L: 번역 → 검사 → 역번역 → 비교
    API-->>W: 보고서 + translation.status (ok · rejected · skipped)

    W->>API: POST /api/center/cases
    API->>R: rate_urgency · default_category
    API->>S: add_live(case) + chat token
    API-->>W: case · nextOpenDate · chatToken
```

소스: [`diagrams/s2_intake_sequence.mmd`](diagrams/s2_intake_sequence.mmd)

- **`/extract`**: 키워드 결과를 먼저 만들고, LLM 결과와 필드별로 합친다. 부위 · 증상은 합집합, `work_related`는 키워드, `onset` · `work_type`은 LLM 값을 쓴다. 이미 채운 칸은 덮어쓰지 않는다.
- **`/route`**: 결정적 규칙이다. 순서는 산재(`work_related=yes`) → 건강보험 → 울산 지원 → 센터다.
- **긴급도**: `rate_urgency`는 진료 판단이 아니라 센터 사례의 처리 우선순위다. 업무 관련이면 +2, 무보험이면 +1이다. 사례를 만들 때만 계산한다.

### 3.3 진료과 결정: 규칙표와 모델

규칙표가 명확히 정하는 조합(치아 → 치과, 눈 → 안과 등)은 규칙표를 따른다. 모델 앙상블은 막연한 분기(내과 묶음 · 기본값)에서만 쓴다.

```mermaid
flowchart TD
    IN(["📋 POST /api/triage<br/>Intake"])
    MS{"부위나 증상이<br/>비어 있나?"}
    MISS(["❌ department = None<br/>missing 반환"])
    RUN["📦 run_model()<br/>실패 · 모델 없음 → None"]
    RULE["🧩 rule_department()<br/>화학물질 → 직업환경 · 눈 → 안과<br/>치아 → 치과 · 화상/출혈 → 외과 ..."]
    GEN{"막연한 분기인가?<br/>내과 묶음 · 기본값"}
    FIX{"rule_fixed?<br/>숨참 · 가슴+통증"}
    HAS{"모델 예측 있음?"}
    RT(["✅ 규칙표 진료과 2개"])
    MT(["✅ 모델 앙상블 Top-2"])

    IN --> MS
    MS -->|"예"| MISS
    MS -->|"아니오"| RUN --> RULE --> GEN
    GEN -->|"아니오 · 명시 규칙"| RT
    GEN -->|"예"| FIX
    FIX -->|"예"| RT
    FIX -->|"아니오"| HAS
    HAS -->|"아니오"| RT
    HAS -->|"예"| MT

    classDef io fill:#E6E6FA,stroke:#333,stroke-width:2px,color:#1a1a4a
    classDef step fill:#87CEEB,stroke:#333,stroke-width:2px,color:#0a2a4a
    classDef gate fill:#FFD700,stroke:#333,stroke-width:2px,color:#000
    classDef ok fill:#90EE90,stroke:#333,stroke-width:2px,color:#0a3a0a
    classDef bad fill:#FFB6C1,stroke:#DC143C,stroke-width:2px,color:#000
    class IN io
    class RUN,RULE step
    class MS,GEN,FIX,HAS gate
    class RT,MT ok
    class MISS bad
```

소스: [`diagrams/s3_triage_decision.mmd`](diagrams/s3_triage_decision.mmd)

숨참, 가슴+통증은 막연한 분기에 들어가도 규칙표로 고정한다. 모델이 가슴 통증에 정형외과를 먼저 내는 경우가 있었기 때문이다(backlog 06, 26).

### 3.4 LLM 호출과 대체 경로

LLM은 추출 · 상황 요약 · 번역에만 쓴다. 어떤 실패에도 결정적 대체 경로가 있어서, LLM이 없어도 서비스가 멈추지 않는다.

```mermaid
flowchart TD
    CALL(["🤖 LLM이 필요한 요청<br/>extract · visit-helper · report · chat"])
    KEY{"LLM_API_KEY 있음?"}
    LIM{"LLMLimiter.take()<br/>IP별 분당 · 하루 상한"}
    GEN["⚙️ generate()<br/>asyncio.timeout · JSON 스키마 강제"]
    ERR{"타임아웃 · 오류 ·<br/>스키마 불일치?"}
    RETRY{"시도 < LLM_ATTEMPTS (2)?"}
    GUARD{"guard 검사<br/>한국어 · 길이 · 진단/추측 금지어<br/>번역은 역번역 비교"}
    OK(["✅ LLM 결과 사용<br/>llmSlots · translation ok"])
    FB(["↩️ 결정적 대체<br/>키워드 추출 · 기본 템플릿<br/>translation skipped"])
    REJ(["⛔ translation rejected<br/>원문만 전달"])

    CALL --> KEY
    KEY -->|"아니오"| FB
    KEY -->|"예"| LIM
    LIM -->|"초과 → limited, 재시도 없음"| FB
    LIM -->|"통과"| GEN --> ERR
    ERR -->|"예"| RETRY
    RETRY -->|"예"| GEN
    RETRY -->|"아니오 → LLMUnavailableError"| FB
    ERR -->|"아니오"| GUARD
    GUARD -->|"통과"| OK
    GUARD -->|"요약 실패"| FB
    GUARD -->|"번역 불일치"| REJ

    classDef io fill:#E6E6FA,stroke:#333,stroke-width:2px,color:#1a1a4a
    classDef step fill:#87CEEB,stroke:#333,stroke-width:2px,color:#0a2a4a
    classDef gate fill:#FFD700,stroke:#333,stroke-width:2px,color:#000
    classDef ok fill:#90EE90,stroke:#333,stroke-width:2px,color:#0a3a0a
    classDef warn fill:#FFE4B5,stroke:#333,stroke-width:2px,color:#000
    classDef bad fill:#FFB6C1,stroke:#DC143C,stroke-width:2px,color:#000
    class CALL io
    class GEN step
    class KEY,LIM,ERR,RETRY,GUARD gate
    class OK ok
    class FB warn
    class REJ bad
```

소스: [`diagrams/s4_llm_fallback.mmd`](diagrams/s4_llm_fallback.mmd)

| 설정 | 기본값 | 뜻 |
|---|---|---|
| `LLM_API_KEY` | 없음 | 비면 LLM 없이 동작한다 |
| `LLM_MODEL` | `claude-haiku-5-5` | Anthropic Messages API, JSON 스키마 강제 |
| `LLM_TIMEOUT_S` / `LLM_ATTEMPTS` | 10 / 2 | 시도마다 타임아웃, 재시도 횟수 |
| `LLM_RATE_PER_MIN` / `LLM_DAILY_LIMIT` | 운영 60 / 3000 | IP별 분당 · 하루 상한. 초과하면 재시도 없이 대체 |
| `LLM_CLIENT_IP_HEADER` | 운영 `cf-connecting-ip` | 피어가 loopback(터널)일 때만 신뢰 |

### 3.5 실시간 채팅 · 통화

채팅은 서버가 번역해서 방 전체에 중계한다. 통화 음성은 브라우저끼리 WebRTC로 주고받고, 서버는 시그널과 자막만 중계한다.

```mermaid
sequenceDiagram
    autonumber
    actor WK as 📱 이주노동자
    participant SV as ⚙️ 서버 Hub
    participant DB as 💾 Store
    participant LL as 🤖 LLM
    actor CT as 🏢 센터 직원
    participant FCM as 📢 FCM

    rect rgb(230, 240, 255)
    note over WK,CT: 채팅 WS /api/center/cases/{id}/chat
    WK->>SV: 연결 (role=worker, token)
    CT->>SV: 연결 (role=center, 세션 쿠키)
    SV-->>WK: history · read
    CT->>SV: 메시지 (한국어)
    SV->>LL: translate_message (ko → 사례 언어, 1회)
    SV->>DB: add_message
    SV-->>WK: message (원문 + 번역)
    SV-->>CT: message
    opt 노동자가 채팅을 보고 있지 않고 60초 안에 보낸 푸시가 없음
        SV->>FCM: notify(kind, caseId)
    end
    end

    rect rgb(235, 255, 235)
    note over WK,CT: 통화 WS /api/center/cases/{id}/call (역할당 1소켓)
    WK->>SV: join → joined · history(captions)
    SV-->>CT: peer present:true
    WK->>SV: signal (SDP · ICE)
    SV-->>CT: signal 중계만 (음성은 WebRTC P2P)
    WK->>SV: caption (음성 인식 문장)
    SV->>DB: add_caption
    SV->>LL: translate_line (백그라운드)
    SV-->>WK: caption + 번역
    SV-->>CT: caption + 번역
    WK--xSV: 연결 끊김
    SV-->>CT: 남은 자막 skipped · peer present:false
    end
```

소스: [`diagrams/s5_realtime_chat_call.mmd`](diagrams/s5_realtime_chat_call.mmd)

- **연결 거부 코드**: 4404(사례 없음), 4403(토큰 불일치 · 교차 사이트), 4401(직원 세션 없음), 4409(통화 역할 중복)
- **푸시**: 노동자가 채팅을 보고 있지 않고, 60초 안에 보낸 푸시가 없을 때만 보낸다. FCM이 `UNREGISTERED`를 돌려주면 그 기기를 지운다.

### 3.6 배포

```mermaid
flowchart LR
    GH["🐙 GitHub main push<br/>deploy-backend.yml"]
    subgraph MAC["🖥️ Mac mini ~/srv/for-nav"]
        PULL["🔄 git pull --ff-only"]
        SH["⚙️ deploy.sh<br/>frontend · app-front 빌드<br/>uv sync --frozen"]
        SWAP["📂 static · static-app 교체"]
        PM2["🚀 pm2 for-nav<br/>fastapi run :8000"]
        HC{"/api/health<br/>30초 안에 200?"}
        CFD["☁️ cloudflared 터널"]
        MODELS[("📦 ../modeling/models")]
        SQL[("💾 SQLite")]
    end
    USERS["👤 www · app.for-nav.com"]

    GH -->|"SSH :2222"| PULL --> SH --> SWAP --> PM2 --> HC
    MODELS --> PM2
    SQL --- PM2
    USERS --> CFD --> PM2

    classDef ci fill:#E6E6FA,stroke:#333,stroke-width:2px,color:#1a1a4a
    classDef step fill:#87CEEB,stroke:#333,stroke-width:2px,color:#0a2a4a
    classDef run fill:#90EE90,stroke:#333,stroke-width:2px,color:#0a3a0a
    classDef gate fill:#FFD700,stroke:#333,stroke-width:2px,color:#000
    classDef store fill:#FFE4B5,stroke:#333,stroke-width:2px,color:#000
    class GH,USERS ci
    class PULL,SH,SWAP step
    class PM2,CFD run
    class HC gate
    class MODELS,SQL store
```

소스: [`diagrams/s6_deployment.mmd`](diagrams/s6_deployment.mmd)

- **pm2 환경**: `STATIC_DIR`, `APP_STATIC_DIR`, `APP_HOSTS=app.for-nav.com`, `MODEL_DIR=../modeling/models`, LLM 상한 값을 설정한다.
- **경로 의존**: 서버가 모델을 `../modeling` 경로로 읽는다. 그래서 `backend/`만 따로 배포하면 모델을 못 찾는다(modeling backlog 11의 남은 과제).
