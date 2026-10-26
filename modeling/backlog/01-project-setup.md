# 01. 프로젝트 골격과 검사 도구

상태: 대기
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
- [ ] `cd modeling && uv sync && uv run ruff check . && uv run ruff format --check . && uv run pytest` 통과
- [ ] `tests/test_schema.py`가 `Department` 10종, `BodyPart` 13종, `Symptom` 전체가 백엔드와 같은지 확인하고 통과
- [ ] `git status`에 `data/raw/` 등 제외 폴더가 나타나지 않음(빈 폴더는 `.gitkeep`으로 유지)
- [ ] `main.py`가 없고 `README.md`에 폴더 구조·실행 명령이 있음

## 결과

## 메모
- 백엔드가 열거값을 바꾸면 `test_schema.py`가 깨진다. 그때 백엔드 파일을 고치지 말고 `schema.py`를 맞춘다
