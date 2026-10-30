# 11. 백엔드가 경로 의존성으로 설치할 수 있는 서빙 패키지

상태: 완료
의존: 08, 10

## 목표
백엔드 backlog 06(모델 연결)이 `predict`를 부르려면 모델링 코드를 불러오는 방법이 있어야 한다. 사용자와 (a) `[tool.uv.sources]` 경로 의존성으로 정했다(2026-10-30). 모델링을 설치할 수 있는 패키지로 바꾸고, 백엔드가 받는 의존성을 `predict`가 쓰는 것으로 줄인다.

## 범위
- 하는 것
  - `pyproject.toml`: `package = true`, `uv_build` 빌드 백엔드(`module-name = "fornav_modeling"`). `[project] dependencies`는 `predict`가 import하는 `lightgbm`·`numpy`만 두고, 학습·평가 의존성(openpyxl, pandas, pyarrow, scikit-learn, shap)은 `train` 의존성 그룹으로 옮긴다. 이 폴더의 `uv sync`는 `train`도 기본으로 설치한다
  - `tests/test_predict_contract.py`: `predict`가 따라 들어가는 모듈의 외부 import가 `[project] dependencies` 안에 있는지
  - `README.md`, `CLAUDE.md`: 설치 방식과 백엔드에서 쓰는 법
- 하지 않는 것
  - 백엔드 `pyproject.toml`·`app/model.py`(백엔드 06), 모델·아티팩트 변경, 스크립트의 `sys.path` 줄 삭제(주석만 고친다)

## 입력·출력
- 수정: `pyproject.toml`, `uv.lock`, `tests/test_predict_contract.py`, `README.md`, `CLAUDE.md`, `scripts/*.py`(주석 한 줄)

## 완료 기준
- [x] `uv run ruff check . && uv run ruff format --check .` 통과, `uv run pytest` 통과
- [x] `uv.lock`에서 패키지 버전이 바뀌지 않는다(의존성 위치만 바뀐다)
- [x] 빈 프로젝트에 `for-nav-modeling = { path = "…/modeling", editable = true }`로 설치하면 pandas·scikit-learn·shap 없이 설치되고, `predict` 결과가 backlog 10의 예시와 같다

## 결과
- 실행(2026-10-30)
  - `uv lock` → 81개 패키지, 버전 변경 없음. 바뀐 것은 이 프로젝트의 `source`(`virtual` → `editable`)와 의존성이 `train` 그룹으로 옮겨진 것뿐
  - `uv run ruff check . && uv run ruff format --check .` → `All checks passed!`, `70 files already formatted`
  - `uv run pytest` → `181 passed`(기존 180 + `test_serving_imports_only_declared_dependencies` 1)
- 경로 의존성 확인: 빈 프로젝트(`package = false`, `dependencies = ["for-nav-modeling"]`, 위 경로 의존성)에서 `uv sync` → 설치 5개(`for-nav-modeling`, `lightgbm==4.7.0`, `numpy==2.5.4`, `scipy==1.18.1`, `narwhals==2.28.0`. scipy·narwhals는 lightgbm 의존성). pandas·scikit-learn·shap·pyarrow·openpyxl은 설치되지 않음
  - 그 환경에서 `predict({"body_parts": ["hand"], "symptoms": ["cut", "bleeding"], "injury": True, …})` → `acuity: outpatient`, `acuityProba` 0.016 / 0.105 / 0.878, `departmentTop2: ["surgery", "ortho"]`. backlog 10 결과 표와 같다
  - 첫 호출(프로세스 시작·아티팩트 읽기 포함) 3.1초. 백엔드는 시작 때 한 번 읽으면 된다(`load_artifacts`가 `lru_cache`)
- 결정 사항
  - **editable로만 쓴다.** `predict.MODELS_DIR`은 `src/fornav_modeling/predict.py` 위치에서 `modeling/models/`를 찾는다. editable이 아니면 wheel에 `models/`가 없어 기본 경로가 깨진다. 백엔드는 06에서 정한 `MODEL_DIR`을 `predict(..., models_dir=)`로 넘기면 설치 방식과 관계없이 동작한다
  - 학습 의존성은 extra가 아니라 의존성 그룹(`train`)에 둔다. 의존성 그룹은 다른 프로젝트가 설치할 때 따라가지 않는다
  - pytest `pythonpath = ["src"]`와 스크립트의 `sys.path` 줄은 그대로 둔다. 설치된 패키지와 같은 `src`를 가리켜 해가 없고, `uv run` 없이 실행할 때도 동작한다

## 메모
- 백엔드 06 문서에 맞출 것(백엔드 브랜치에서): 완료 기준의 `modeling/models/*/v1/` → 서빙 묶음은 `v2`. `predict` 출력에는 `departmentTop2`·`departmentFallback`도 있다
- 백엔드를 `backend/` 폴더만 따로 배포하면 `../modeling` 경로가 없다. 배포 방식(backend 08)과 함께 확인한다
