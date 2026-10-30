# 12. 모델링 코드를 경로 의존성으로 불러오기

상태: 완료
의존: 06, modeling 11

## 목표
06은 `PYTHONPATH=../modeling/src`로 `fornav_modeling`을 불러오고, `lightgbm`·`numpy` 버전을 서버 `pyproject.toml`에 한 번 더 적었다. 사용자가 (a) 경로 의존성으로 정했고(2026-10-30), modeling 11(conceptamin/for-nav#82)이 모델링을 설치할 수 있는 패키지로 바꿨다. 서버가 `../modeling`을 editable 경로 의존성으로 설치하게 바꿔, 실행할 때 `PYTHONPATH`가 필요 없고 모델 의존성 버전을 modeling 한 곳에서 고정하게 한다.

## 범위
- 하는 것
  - `pyproject.toml`: `lightgbm`·`numpy` 대신 `for-nav-modeling`, `[tool.uv.sources]`에 `{ path = "../modeling", editable = true }`
  - `app/model.py`: `PYTHONPATH` 안내와 `ImportError` 처리 삭제. `MODEL_DIR`이 있을 때만 import하는 것은 그대로
  - `README.md`, `.env.example`: `PYTHONPATH` 안내 삭제
- 하지 않는 것
  - 모델 판정 규칙·응답 형태(06 그대로), 실제 아티팩트로 도는 자동 테스트(테스트는 지금처럼 가짜 `predict`)

## API·파일
- API 변경 없음
- 수정: `pyproject.toml`, `uv.lock`, `app/model.py`, `README.md`, `.env.example`, `backlog/06-model-triage.md`(메모 한 줄)

## 완료 기준
- [x] `uv run ruff check . && uv run ruff format --check .`, `uv run pytest` 통과
- [x] `uv sync` 뒤 서버 환경에 `for-nav-modeling`(editable), `lightgbm==4.7.0`, `numpy==2.5.4`가 있고 pandas·scikit-learn·shap은 없다
- [x] `PYTHONPATH` 없이 `MODEL_DIR=../modeling/models`로 띄운 `/api/triage`가 06 `## 결과`와 같은 판정을 낸다

## 결과
- 실행(2026-10-30)
  - `uv lock` → 76개 패키지. 바뀐 것은 서버 의존성이 `lightgbm`·`numpy`에서 `for-nav-modeling`(editable `../modeling`)으로 바뀐 것과, 그 패키지 항목이 더해진 것뿐. `lightgbm 4.7.0`, `numpy 2.5.4`는 그대로
  - `uv run ruff check . && uv run ruff format --check .` → `All checks passed!`, `58 files already formatted`
  - `uv run pytest` → `2852 passed`
  - `uv pip list` → `for-nav-modeling 0.1.0`(editable, `../modeling`), `lightgbm 4.7.0`, `numpy 2.5.4`. pandas·scikit-learn·shap·pyarrow 없음(modeling의 `train` 그룹은 따라오지 않는다)
- `MODEL_DIR=../modeling/models uv run fastapi run app/main.py`(PYTHONPATH 없음) 뒤 `curl -XPOST /api/triage`

| 입력 | emergency | byRule | byModel | model.acuity | department |
|---|---|---|---|---|---|
| 손·베인 상처·출혈 | false | false | false | outpatient(0.87) | surgery/ortho |
| 가슴·통증 | true | true | true | emergency(0.70) | internal/family |

  06 `## 결과` 표와 같다
- 결정 사항
  - editable로만 설치한다. `predict`가 기본 아티팩트 위치를 소스 위치에서 찾기 때문이다. 서버는 `MODEL_DIR`을 `models_dir=`로 넘기므로 실제 동작은 `MODEL_DIR`이 정한다
  - `fornav_modeling` import는 `load_model` 안에 둔다. `MODEL_DIR`이 없으면 lightgbm을 불러오지 않아 시작이 빠르다

## 메모
- 경로 의존성이라 서버는 저장소 체크아웃 안에서만 설치된다. `backend/`만 따로 배포하면 `../modeling`이 없다(08 같은 출처 서빙은 체크아웃 안에서 띄우므로 해당 없음)
- modeling의 `[project] dependencies`를 바꾸면 서버 `uv.lock`도 다시 만들어야 한다(`uv lock`). CI는 `uv sync`(잠금 확인 없이)라 실패하지 않고 그 자리에서 다시 푼다
- 열린 PR #84(07)·#85(08)도 `.env.example`·`README.md`의 `MODEL_DIR` 줄 옆을 고쳐서, 이 PR 뒤에 병합하면 그 줄에서 다시 충돌할 수 있다
