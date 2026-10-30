# modeling 작업 규칙

울산 외국인 의료 내비게이터의 응급도 분류 모델, 진료과 추천 모델, 그 학습 데이터와 평가를 만드는 폴더다.
무엇을 만드는지(처리 흐름, 모델 구성, 데이터 출처)는 `README.md`가 정하고, **무엇을 언제 만드는지는 `backlog/` 문서가 정한다.** 이 문서는 그 둘을 코드로 옮길 때 지키는 규칙이다.

브랜치·커밋·PR 규칙은 루트 `CLAUDE.md`를 따른다. 브랜치 영역은 `modeling/`이다.

## 읽는 순서

1. 루트 `CLAUDE.md`
2. `modeling/README.md` — 설계 원칙, 처리 흐름, 모델 구성, 데이터 출처. 여기에 없는 모델·데이터를 새로 넣지 않는다.
3. `modeling/backlog/` — 작업 항목. 사용자가 지정한 항목 하나만 구현한다.
4. 백엔드와 맞춰야 할 때는 `backend/README.md`의 "나중에 붙일 자리", `backend/app/vocab.py`(열거값), `backend/app/schemas.py`(`Intake`, `TriageResult`)

## backlog 문서로 일한다

- `backlog/` 안의 문서 하나가 작업 항목 하나다. 파일 이름은 `NN-short-name.md`(예: `01-triage-data.md`)로 쓰고, 번호가 작은 것이 먼저다.
- 사용자가 항목을 말하지 않으면 미완료 항목 중 번호가 가장 작은 것을 고르고, 시작 전에 어느 항목을 하는지 말한다. `의존:`에 적힌 항목이 완료되지 않았으면 시작하지 않고 사용자에게 알린다.
- **지정된 항목의 범위만 구현한다.** 하다가 발견한 다른 일은 새 backlog 문서로 만들거나 기존 문서의 `## 메모`에 적고, 지금 작업에 섞지 않는다.
- 문서의 `## 완료 기준`을 그대로 검증한다. 기준이 모호하거나 검증할 방법이 없으면 구현 전에 사용자에게 묻는다.
- 끝나면 그 문서의 `## 결과`에 실행한 명령과 결과, 측정값(분자·분모 포함), 만든 파일, 내린 결정과 이유를 적고 `상태:`를 바꾼다. 결과 기록은 코드와 같은 PR에 넣는다.
- backlog 문서와 `README.md`가 어긋나면 멈추고 사용자에게 묻는다. 임의로 한쪽을 고치지 않는다.

### backlog 문서 형식

```markdown
# NN. <제목>

상태: 대기 | 진행 중 | 완료 | 보류
의존: <먼저 끝나야 하는 항목 번호, 없으면 "없음">

## 목표
무엇을 왜 만드는지 두세 문장

## 범위
- 하는 것
- 하지 않는 것

## 입력·출력
쓰는 데이터·파일, 만들어지는 파일·모델·표

## 완료 기준
- [ ] 검증할 수 있는 문장으로 쓴다 (예: `uv run pytest` 통과, 응급 클래스 재현율을 분자·분모와 함께 기록)

## 결과
(구현 후 작성) 실행 명령 → 결과, 측정값, 결정 사항, 남은 문제

## 메모
```

## 스택과 폴더

- Python 3.12 + uv(backend와 같음). LightGBM, scikit-learn, pandas, SHAP를 기준으로 하고, 버전은 `pyproject.toml`에 고정해 `uv.lock`을 커밋한다.
- 검사 도구는 backend와 같은 ruff·pytest를 쓴다. ruff 설정은 `backend/pyproject.toml`을 따른다.
- 노트북(`.ipynb`)은 탐색용이다. 재현해야 하는 것(전처리, 학습, 평가, 내보내기)은 모두 `.py` 모듈과 명령으로 옮긴다. 노트북을 커밋할 때는 출력을 지운다.
- `pyproject.toml`은 `package = true`(빌드 백엔드 `uv_build`)다. 백엔드가 `../modeling`을 editable 경로 의존성으로 설치한다(backlog 11). **`[project] dependencies`에는 `predict`가 import하는 것(`lightgbm`, `numpy`)만 두고**, 학습·평가 의존성은 `train` 의존성 그룹에 둔다. 서빙 경로에 새 import를 넣으면 `test_predict_contract.py`가 막는다. pytest는 `pythonpath = ["src"]`로 같은 `src`를 찾는다.
- 지금 `main.py`는 빈 자리표시자다. 첫 구현 항목에서 지운다.
- 폴더 구조는 아래를 따른다. 새 폴더가 필요하면 backlog 문서에 이유를 적고 여기와 `README.md`를 함께 고친다.

```text
modeling/
  CLAUDE.md  README.md  backlog/
  pyproject.toml  uv.lock  .gitignore

  src/fornav_modeling/          로직은 전부 여기. 테스트 대상
    schema.py                   입력 필드·열거값 (backend vocab과 같은 값, 모델링 안의 단일 출처)
    data/                       I/O는 이 폴더만 한다
      download.py               출처별 내려받기 + sha256 검증
      kaggle_triage.py          응급도 원본 → 표준 테이블
      kaggle_symptom.py         질환·증상 원본 → 표준 테이블
      hira.py                   질환 → 진료과 통계 적재
      split.py                  train/valid/test 분리 (id 목록으로 고정)
    features/
      buttons.py                버튼 입력 → 피처 벡터. 학습과 서빙(predict.py)이 같은 함수를 쓴다
      vitals.py                 발표용 비교 실험 전용. 서빙 모델에는 넣지 않는다
    labels/
      ktas.py                   KTAS 1~5 → 3단계
      department.py             질환 → 진료과 매핑, 버튼 조합 → 분포 표 적재
    models/
      acuity.py                 LightGBM 응급도 (학습·예측·임계값)
      dept_a.py                 LightGBM 질환 확률 → 진료과 확률 변환
      dept_b.py                 소형 MLP, 소프트 라벨
      ensemble.py               가중 평균 + 저확신 폴백
    explain.py                  SHAP
    evaluate.py                 지표 계산. 분자·분모, 출처별 분리
    export.py                   아티팩트 + metadata.json 쓰기
    predict.py                  입력 dict → TriageResult.model dict. 백엔드가 부를 순수 함수
    experiment_vitals.py        발표용 활력징후 비교 실험(backlog 09). 서빙과 무관, 모델을 내보내지 않는다
    pipeline.py                 백엔드 규칙 + 응급도 모델을 합친 응급 판정 평가(backlog 12). 규칙은 backend 환경에서 부른다

  scripts/                      명령 하나 = 일 하나. 인자를 받아 패키지 함수를 부르기만 하는 얇은 파일
    download_data.py  build_tables.py  make_splits.py
    train_acuity.py  train_dept_a.py  train_dept_b.py  tune_ensemble.py
    evaluate.py  export_models.py  experiment_vitals.py

  data/
    README.md                   파일별 출처 URL·라이선스·확인 날짜·sha256
    raw/                        git 제외. 원본 그대로
    processed/                  git 제외. 만드는 스크립트만 커밋
    splits/                     git 포함. train/valid/test id 목록 + 재생성한 파일의 해시
    tables/                     git 포함. 사람이 검토하는 CSV, 행마다 출처 열
      button_department.csv     버튼 조합 → 진료과 분포 (모델 B 라벨)
      disease_department.csv    질환 → 진료과 비율 (HIRA)
    test/                       git 제외. splits로 재생성. 평가 명령만 읽는다

  models/                       내보낸 아티팩트. 버전 폴더마다 metadata.json
    acuity/v1/   dept_a/v1/   dept_b/v1/   ensemble/v1/

  notebooks/                    탐색용. 커밋 시 출력 제거
  reports/                      평가 결과 JSON·표, 발표용 그림
  tests/
    test_features.py            버튼 → 피처가 결정적인지
    test_labels.py              KTAS·진료과 매핑
    test_determinism.py         같은 seed 두 번 → 같은 해시
    test_split_isolation.py     학습 명령이 data/test를 열지 않는지
    test_predict_contract.py    출력이 TriageResult.model 형태이고 Department 10종만 나오는지
```

- **피처 정의는 `features/buttons.py` 한 곳**이다. 학습과 `predict.py`가 같은 함수를 써서 학습 시점과 서빙 시점의 피처가 어긋나지 않게 한다.
- **로직은 패키지, 명령은 `scripts/`.** 스크립트에 로직을 넣으면 테스트할 수 없다. 스크립트는 10~20줄로 유지한다.

## 설계에서 바꾸지 않는 것

- **규칙이 모델보다 먼저다.** 레드플래그 규칙과 명확 케이스 규칙은 모델 앞에서 실행되고, 규칙이 응급이면 모델 결과와 관계없이 응급이다. 모델이 규칙을 덮어쓰는 구조를 만들지 않는다.
- **피처는 버튼으로 받을 수 있는 것만 쓴다.** 주증상 카테고리, 통증 점수(0–10), 의식 상태, 나이대, 성별, 발생 시점, 손상 여부. 활력징후처럼 버튼에 없는 피처는 발표용 비교 실험에만 쓰고 서빙할 모델에는 넣지 않는다.
- **열거값은 백엔드 `vocab.py`의 값을 그대로 쓴다.** `BodyPart`, `Symptom`, `Department`(10종)의 문자열을 모델 입력·출력 라벨로 쓴다. 진료과를 더해야 하면 모델링 쪽에서 추가하지 않고 사용자에게 묻는다.
- **응급도는 3단계다.** KTAS 1–2 → 즉시 응급, 3 → 오늘 병원, 4–5 → 외래·약국. 임계값은 응급을 놓치는 쪽을 줄이는 방향으로 정한다.
- **질환명은 노출하지 않는다.** 모델 A의 질환 확률은 중간 산출물까지만 쓰고, 내보낸 아티팩트의 출력과 메타데이터, 리포트에 질환명이 들어가지 않게 한다.
- **확신도가 낮으면 가정의학과 또는 내과로 폴백한다.** 폴백 기준값은 검증셋으로 정하고 메타데이터에 적는다.

## 데이터

- 원본 데이터는 git에 올리지 않는다. 내려받는 방법을 스크립트나 문서로 남기고, 출처 URL, 라이선스, 확인 날짜, 파일의 sha256을 backlog 문서 `## 결과`에 적는다.
- 라이선스가 학습·평가 사용을 허락하지 않거나 라이선스 표시가 없는 데이터는 쓰지 않는다. 비상업 조건이면 그 조건을 메타데이터에 적는다.
- 이름·연락처·사업장명 같은 식별 정보가 있으면 지운 뒤 넣는다.
- 우리 서비스 사용자의 입력은 어떤 경우에도 학습·평가에 넣지 않는다.
- **테스트셋은 id 목록으로 고정한다.** 원본은 git에 못 올리므로 `data/splits/`에 test id 목록과 재생성한 파일의 sha256을 커밋하고, `data/test/`는 로컬에서 재생성한다. 해시가 다르면 평가 명령이 멈춘다. 분리한 뒤에는 학습, 임계값 조정, 앙상블 가중치 조정, 오류 분석에 쓰지 않고 파일을 열어 보지도 않는다. 이 폴더를 읽는 코드는 평가 명령 하나뿐이다. 바꿔야 하면 사용자에게 묻고 이유를 backlog 문서에 남긴다.
- 임계값과 앙상블 가중치는 검증셋으로만 정한다.
- `data/tables/`의 표는 CSV로 두고 행마다 출처 열을 둔다. LLM으로 만든 행은 출처에 그렇게 적는다.

## 평가와 기록

- 수치는 항상 분자·분모와 함께 적는다(예: 응급 120건 중 113건 재현). 지표는 `README.md` 표의 것을 쓴다: 응급 클래스 재현율, 진료과 Top-2 적중률, 레드플래그 누락 0건.
- 데이터 출처별, 개선 라운드별(v0 → 1라운드 → 최종)로 나눠 적는다.
- 측정 전에 성능을 적지 않고, 나쁜 결과도 숨기지 않는다. 비교 모델(로지스틱 회귀, LLM 제로샷 등)이 더 좋게 나오면 그대로 적는다.
- 같은 seed로 두 번 학습하면 같은 아티팩트가 나와야 한다. seed는 코드에 고정하고 테스트로 확인한다.
- 학습·평가 명령은 로컬에서 몇 분 안에 끝나야 한다. 데이터가 작으므로 GPU나 외부 서비스를 전제하지 않는다.

## 모델 내보내기와 백엔드 연결

- **불러올 때 코드를 실행하지 않는 형식으로 내보낸다.** LightGBM 텍스트 모델, 어휘·가중치를 담은 JSON 등. pickle·joblib은 쓰지 않는다.
- 아티팩트 옆에 메타데이터 JSON을 둔다: 모델 버전, 학습 데이터 해시, seed, 임계값, 피처 순서, 라벨 순서, 측정값.
- 서빙은 백엔드 책임이다. 모델링은 아티팩트와 "입력 dict → 출력 dict" 순수 함수를 제공한다. 입력은 백엔드 `Intake` 필드 이름(snake_case)을 쓰고, 출력은 `backend/README.md`가 정한 `TriageResult.model` 형태(`acuity`, `acuityProba`, `departmentProba`, `shap`)에 맞춘다.
- `backend/` 코드는 이 폴더의 작업에서 고치지 않는다. 연결 작업은 `backend/` 브랜치로 따로 한다. 백엔드 스키마를 바꿔야 하면 backlog 문서 `## 메모`에 적고 사용자에게 알린다.

## 검사와 커밋

```sh
cd modeling
uv sync
uv run ruff check . && uv run ruff format --check .
uv run pytest
```

- 커밋 메시지의 `테스트:` 줄에 위 명령 결과를 적는다. 문서만 바꿨으면 그렇게 적는다.
- CI에 `modeling` 작업을 추가하는 것은 `chore/` 영역의 별도 작업이다.
- 데이터 파일과 모델 아티팩트의 git 포함 여부는 위 폴더 표를 따르고, `.gitignore`에 그대로 적는다.
