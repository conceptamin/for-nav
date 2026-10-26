# 01. 프로젝트 골격과 검사 도구

상태: 완료
의존: 없음

## 목표
`CLAUDE.md`의 폴더 구조대로 빈 패키지와 검사 도구를 만들어, 이후 항목이 코드를 넣을 자리와 `uv run pytest`가 도는 상태를 확보한다. 백엔드 열거값을 모델링 안에서 쓸 단일 출처(`schema.py`)도 여기서 만든다.

## 범위
- 하는 것
  - `pyproject.toml`(Python 3.12, uv `package = false`, ruff 설정은 `backend/pyproject.toml`과 동일, pytest `pythonpath = ["src"]`), `uv.lock`
  - 의존성 고정: lightgbm, scikit-learn, pandas, numpy, shap, pytest, ruff. 버전은 PyPI에서 확인해 적는다
  - `src/fornav_modeling/` 패키지 골격(하위 폴더와 빈 `__init__.py`), `scripts/`, `data/{raw,processed,splits,tables,test}/`, `models/`, `notebooks/`, `reports/`, `tests/`
  - `.gitignore`: `data/raw/`, `data/processed/`, `data/test/`, `.venv`, `__pycache__`, `.pytest_cache`, `.ruff_cache`
  - `schema.py`: `BodyPart`, `Symptom`, `Department`, `Lang` 열거값과 `Intake` 입력 필드(snake_case). 값은 `backend/app/vocab.py`, `backend/app/schemas.py`에서 그대로 복사하고, 두 파일이 같은지 비교하는 테스트를 둔다
  - `main.py` 삭제
  - `README.md`에 폴더 구조와 실행 명령 반영
- 하지 않는 것
  - 데이터 내려받기, 모델 코드, CI 작업 추가(`chore/` 별도)

## 입력·출력
- 입력: `backend/app/vocab.py`, `backend/app/schemas.py`, `backend/pyproject.toml`
- 출력: 위 파일·폴더, `tests/test_schema.py`(백엔드 열거값과 일치 확인)

## 완료 기준
- [x] `cd modeling && uv sync && uv run ruff check . && uv run ruff format --check . && uv run pytest` 통과
- [x] `tests/test_schema.py`가 `Department` 10종, `BodyPart` 13종, `Symptom` 전체가 백엔드와 같은지 확인하고 통과
- [x] `git status`에 `data/raw/` 등 제외 폴더가 나타나지 않음(빈 폴더는 `.gitkeep`으로 유지)
- [x] `main.py`가 없고 `README.md`에 폴더 구조·실행 명령이 있음

## 결과
- 실행: `cd modeling && uv sync && uv run ruff check . && uv run ruff format --check . && uv run pytest` → `All checks passed!`, `18 files already formatted`, `12 passed`
- 고정한 버전(2026-10-27 PyPI 최신, `uv add`로 해석 후 `==`로 고정): lightgbm 4.7.0, scikit-learn 1.9.1, pandas 3.1.0, numpy 2.5.4, shap 0.54.1 / dev: pytest 9.1.1, ruff 0.17.2. Python 3.12.15에서 다섯 패키지 import 확인
- `tests/test_schema.py`(12개): `Lang`·`BodyPart`·`Symptom`·`Department`와 `Intake` 필드 타입에 쓰는 `Onset`·`Industry`·`WorkType`·`District`·`YesNoUnknown` 9종의 값과 순서, 개수(`Department` 10, `BodyPart` 13, `Symptom` 15), `Intake` 필드 이름·순서·타입·필수 여부(11개 중 필수 3개: `id`, `language`, `created_at`)를 백엔드와 비교
  - 깨지는지 확인: `Department` 순서 바꾸기, `created_at`을 선택으로 바꾸기, `district`에서 `None` 빼기 → 각각 실패, 되돌린 뒤 12개 통과
- 제외 폴더: `data/raw/`, `data/processed/`, `data/test/`에 임시 파일을 넣고 `git add -n modeling/data` → `.gitkeep` 5개만 잡힘
- 만든 파일: `pyproject.toml`, `uv.lock`, `.gitignore`, `src/fornav_modeling/{__init__,schema}.py`, `src/fornav_modeling/{data,features,labels,models}/__init__.py`, `tests/test_schema.py`, 빈 폴더 `.gitkeep`(`scripts/`, `data/*`, `models/`, `notebooks/`, `reports/`). `main.py` 삭제, `README.md`에 실행·폴더 구조 추가
- 결정
  - 백엔드는 pydantic·fastapi에 의존하므로 테스트에서 import하지 않는다. `vocab.py`는 `typing`만 써서 파일 경로로 직접 읽고, `schemas.py`는 AST로 `Intake` 정의만 꺼내 타입 문자열을 백엔드 열거값으로 평가한다. 모델링 의존성에 pydantic을 넣지 않기 위해서다
  - `Intake`는 `TypedDict`로 둔다(03·08이 "Intake 형태 dict"를 입력으로 받는다). 백엔드에서 기본값이 있는 필드는 `NotRequired`
  - `Literal`끼리 `==`는 순서를 무시하므로 `get_args` 튜플로 비교한다. 이 순서를 라벨·원-핫 순서로 쓰도록 `LANGS`, `BODY_PARTS`, `SYMPTOMS`, `DEPARTMENTS`, `ONSETS` 튜플을 둔다
  - 다국어 표기(`Term`)는 모델에 필요 없어 옮기지 않았다
  - 제외 폴더도 구조를 남기려고 `data/raw/*` + `!data/raw/.gitkeep` 형태로 무시한다
- 남은 문제: 없음. `uv run`을 쓸 때 셸에 다른 프로젝트의 `VIRTUAL_ENV`가 잡혀 있으면 uv가 경고를 내고 무시한다(동작에는 영향 없음)

## 메모
- 백엔드가 열거값을 바꾸면 `test_schema.py`가 깨진다. 그때 백엔드 파일을 고치지 말고 `schema.py`를 맞춘다
