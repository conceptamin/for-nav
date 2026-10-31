# 외국인 근로자 다국어 의료 안내 — 모델 및 데이터 구성

## 설계 원칙

- **판단은 규칙과 학습 모델, 문장은 LLM**: 진료과 판단은 근거를 제시할 수 있는 규칙·모델이 담당하고, LLM은 정리와 번역만 맡는다.
- **응급 여부는 판정하지 않는다**: 틀린 판정이 헛된 확신을 주지 않게 응급도 분류 모델과 응급 규칙을 지웠다(사용자 결정, 2026-10-31, backlog 15). 119는 앱이 판정 없이 늘 보이는 버튼으로 안내한다.
- **진단이 아닌 안내**: 질환명은 화면에 노출하지 않고, "증상 요약 리포트"와 "의료기관 이용 안내"로 표현한다.
- **같은 버튼 피처 구조**: 진료과 모델 A·B가 동일한 입력 스키마를 사용해 한 번의 API 호출로 결과를 반환한다.

## 처리 흐름

```
버튼 입력
  → 명확 케이스 규칙 (치아 → 치과, 눈 → 안과 등)
  → 진료과 앙상블 (모델 A + 모델 B)
  → LLM 리포트 생성·번역
  → 근처 진료 가능 의원 연결 (공공 API)
```

## 모델 구성

| 구성 요소 | 방식 / 모델 | 학습 데이터 | 출력 | 평가 지표 |
|---|---|---|---|---|
| **진료과 모델 A** (증상 → 질환 → 진료과) | **LightGBM** 다중 분류 | Kaggle Disease Symptom Prediction + HIRA 질병별 진료과 통계 | 진료과 확률 분포 | Top-2 적중률 |
| **진료과 모델 B** (직접 분류) | **소형 MLP** (소프트 라벨 학습) | 직접 구축한 "버튼 조합 → 진료과 분포" 테이블 | 진료과 확률 분포 | Top-2 적중률 |
| 진료과 앙상블 | A·B 가중 평균 | 검증 데이터로 가중치 조정 | 상위 2개 진료과 | Top-2 적중률 |
| 명확 케이스 처리 | 규칙 | 없음 | 진료과 확정 | — |
| 리포트 생성·번역 | LLM API (Claude Haiku 5.5, 품질 부족 시 Sonnet 5.5) | 없음 (프롬프트 + JSON 스키마) | 사용자 언어 + 한국어 요약 | 원어민 검토 |
| 병원 연결 | 공공 API + 코드 (LLM 미사용) | 없음 | 근처 진료 가능 의원 | — |

### 진료과 모델 세부

- **모델 A**: 증상에서 질환 확률을 예측한 뒤, HIRA 통계의 질환별 진료과 비율로 합산해 진료과 확률로 변환. 질환명은 노출하지 않음. 내과 질환에 강함.
- **모델 B**: 버튼 조합마다 HIRA 통계 기반 진료과 확률 분포를 라벨로 학습. 외상·산업재해 증상을 직접 포함할 수 있음.
- **앙상블**: 두 모델의 확률 분포를 가중 평균(초기 0.5 : 0.5). 서로의 빈틈(내과 질환 / 외상·산재)을 보완.
- **폴백**: 확신도가 낮으면 가정의학과 또는 내과로 안내.

### 리포트 생성

- 입력은 JSON으로 고정, 출력도 JSON 스키마로 받아 템플릿에 채움
- 프롬프트 제약: 입력에 없는 증상·질환명 추가 금지, 진료과 결과는 그대로 옮길 것
- 구성: 위쪽 사용자 언어(상태 요약, 해야 할 일, 추천 진료과), 아래쪽 한국어 의료진용 요약(주증상, 발생 시점, 동반 증상, 사고 경위, 복용약, 알레르기)
- 하단 고정 문구: 의학적 진단이 아니라는 안내, 번역 오류 가능성 안내
- API 실패 시 한국어 요약은 템플릿으로 생성
- 저자원 언어(네팔어, 크메르어, 미얀마어 등)는 모델별 비교와 원어민 검토 필요

### 병원 연결

| 단계 | 담당 |
|---|---|
| 진료과 → 진료과목 코드 변환, API 호출, 진료시간 필터링, 거리순 정렬 | 코드 |
| 병원 이름·주소·전화번호·진료시간 표시 | 앱 (API 데이터 그대로, 이름·주소는 한국어 원문 유지) |
| 사용자 언어 안내 문장 | LLM (리포트 생성 호출에 함께 포함) |

병원 정보를 LLM이 생성하거나 수정하지 않도록 해서 환각으로 인한 잘못된 안내를 방지한다.

## 데이터 출처

| 데이터 | 용도 | 접근성 | 비고 |
|---|---|---|---|
| Kaggle Disease Symptom Prediction | 진료과 모델 A 학습 | 바로 다운로드 | 영어권 데이터, 외상 증상 부족 |
| HIRA 보건의료빅데이터개방시스템 질병별 진료과 통계 | 질환 → 진료과 매핑, 모델 B 라벨 | 공개 | 라벨 근거로 가장 탄탄함 |
| 대학병원 증상별 진료과 안내, 국가건강정보포털 | 모델 B 테이블 구축·검증 | 공개 | 대량 수집 시 이용약관 확인 |
| HIRA 병원정보서비스, 국립중앙의료원 병·의원 찾기 | 병원 연결 | 공공데이터포털 API 신청 | 진료시간·진료과목 조회 |

## 향후 계획

- 서비스 운영 중 "버튼 입력 → 실제 방문 진료과" 로그 수집
- 로그가 쌓이면 진료과 모델을 실사용 데이터로 재학습
- 진료과 모델 A가 쓰지 않는 피처(통증 점수·의식 상태·나이대·성별·발생 시점·손상 여부)를 빼고 다시 학습해 버전을 올린다(지금은 순서를 그대로 둔다)
- 의료진 검수를 통한 규칙·매핑 테이블 신뢰도 확보
## 실행

Python 3.12와 [uv](https://docs.astral.sh/uv/)가 필요하다. 의존성 버전은 `pyproject.toml`에 고정하고 `uv.lock`을 커밋한다.

```sh
cd modeling
uv sync                                              # .venv 생성, 고정된 의존성 설치
uv run ruff check . && uv run ruff format --check .  # 린트·포맷 검사
uv run pytest                                        # 테스트
```

노트북(`notebooks/`)은 이 프로젝트 `.venv`를 커널로 연다. `uv sync`가 `notebook` 그룹(ipykernel·matplotlib)까지 설치한다. 커널 등록은 한 번만 한다: `.venv/bin/python -m ipykernel install --user --name for-nav-modeling --display-name "for-nav modeling (.venv)"`

데이터 내려받기·학습·평가 명령은 `scripts/`에 하나씩 추가한다. 무엇을 언제 만드는지는 `backlog/` 문서를 따른다.

## 학습·평가·내보내기 순서

```sh
uv run python scripts/download_data.py                   # 원본(data/raw)
uv run python scripts/make_splits.py                     # 질환·증상 분할(진료과 모델 A)
uv run python scripts/build_tables.py                    # 진료과 표·검증셋 id
uv run python scripts/train_dept_a.py                    # models/dept_a/v0
uv run python scripts/train_dept_b.py                    # models/dept_b/v0
uv run python scripts/tune_ensemble.py                   # models/ensemble/v1/ensemble.json
uv run python scripts/evaluate.py --model <dept_a|dept_b|ensemble> --round <v0|v1>   # test 1회, "최종"
uv run python scripts/export_models.py                   # models/{dept_a,dept_b,ensemble}/v2/
```

## 아티팩트와 `predict`

서빙은 `models/*/v2/`만 읽는다(08의 `v1` 묶음은 기록으로 남겨 둔다). 불러올 때 코드를 실행하는 형식(pickle·joblib)은 쓰지 않는다. 폴더마다 `metadata.json`이 있고, 그 `files`에 적힌 sha256과 파일이 다르면 `predict`가 `ArtifactError`로 멈춘다.

| 폴더 | 파일 | 내용 |
|---|---|---|
| `dept_a/v2/` | `model.txt`, `departments.json` | LightGBM 텍스트(질환 번호 예측) + 질환 번호별 진료과 비율 행렬. 질환명은 없다 |
| `dept_b/v2/` | `weights.json` | MLP 가중치(`W1`, `b1`, `W2`, `b2`), 입력 피처·라벨 순서 |
| `ensemble/v2/` | `ensemble.json` | 모델 A 가중치, 폴백 기준값, 폴백 진료과(가정의학과, 내과) |

`metadata.json`에는 모델 버전, 원본 라운드, 학습 데이터 sha256, seed, 가중치·폴백 기준, 피처·라벨 순서, 검증·최종(test) 측정값, 생성 시각이 있다.

```python
from fornav_modeling.predict import predict  # uv sync가 이 패키지를 editable로 설치한다

predict(
    {
        "id": "r1",
        "language": "vi",
        "body_parts": ["hand"],
        "symptoms": ["cut", "bleeding"],
        "injury": True,
        "created_at": "2026-10-28T09:00:00Z",
    }
)
# {"departmentProba": {"ortho": …, …, "occ": …},      # Department 10종, 합 1
#  "departmentTop2": ["surgery", "ortho"],              # 폴백이면 ["family", "internal"]
#  "departmentFallback": false}
```

- 입력은 백엔드 `Intake` 필드 이름(snake_case)이다. 손상 여부(`injury`)는 진료과 모델 B가 쓴다. 피처 자리가 남아 있는 `pain_score`·`mental`·`age_group`·`sex`는 백엔드가 보내지 않아 결측이고, 모델 A는 이 값을 쓰지 않는다(`features/buttons.py`)
- 명확 케이스 규칙(진료과 규칙표)은 백엔드가 `predict` 앞에서 실행한다. `predict`에는 규칙이 없다
- `predict`는 학습 코드(`fornav_modeling.models`)를 import하지 않는다(`tests/test_predict_contract.py`)
- 백엔드는 이 폴더를 editable 경로 의존성으로 설치한다: `for-nav-modeling = { path = "../modeling", editable = true }`(`[tool.uv.sources]`). 설치되는 것은 `[project] dependencies`(`lightgbm`, `numpy`)뿐이고 학습 의존성은 `train` 그룹이라 따라가지 않는다(backlog 11). 아티팩트 위치는 `predict(..., models_dir=)`로 넘길 수 있다

## 폴더 구조

```text
modeling/
  pyproject.toml  uv.lock  .gitignore
  backlog/                 작업 항목. 문서 하나 = 항목 하나
  src/fornav_modeling/     로직은 전부 여기(테스트 대상)
    schema.py              입력 필드·열거값. backend/app/vocab.py와 같은 값
    data/                  내려받기·원본 → 표준 테이블·train/valid/test 분리. I/O는 이 폴더만 한다
    features/              버튼 입력 → 피처 벡터. 학습과 서빙이 같은 함수를 쓴다
    labels/                질환·버튼 조합 → 진료과
    models/                진료과 모델 A·B, 앙상블
  scripts/                 명령 하나 = 일 하나. 패키지 함수를 부르기만 한다
  data/
    raw/  processed/  test/   git 제외(폴더만 .gitkeep)
    splits/                train/valid/test id 목록 + 해시(git 포함)
    tables/                사람이 검토하는 CSV, 행마다 출처 열(git 포함)
  models/                  내보낸 아티팩트. 버전 폴더마다 metadata.json
  notebooks/               탐색용. 커밋 시 출력 제거
  reports/                 평가 결과
  tests/                   test_schema.py: 열거값·Intake 필드가 백엔드와 같은지
```

파일 단위 계획과 작업 규칙은 `CLAUDE.md`에 있다.
