# 06. 응급도·진료과 모델 연결

상태: 대기
의존: 01, modeling 08(아티팩트와 `predict` 함수)

## 목표
`modeling/`이 내보낸 응급도·진료과 모델을 `/api/triage`에 붙인다. 레드플래그·버튼 조합 규칙은 지금처럼 모델 앞에서 돌고, 규칙이 응급이면 모델과 관계없이 응급이다. 모델은 보조 점수 자리(`byModel`)를 대신하고, 결과 전체는 `TriageResult.model` 선택 필드로 더한다. 아티팩트가 없으면 지금 동작 그대로다.

## 범위
- 하는 것
  - `app/settings.py`에 `MODEL_DIR`(기본 빈 값 = 모델 없음) 추가
  - `app/model.py`: 시작 시 `MODEL_DIR` 아래 `metadata.json`과 아티팩트를 한 번 읽고 `modeling`의 `predict(intake_dict)`를 부르는 얇은 모듈. 모델이 없으면 `None`. 피처 계산·임계값은 모델링 쪽 것을 그대로 쓰고 서버에 다시 적지 않는다
  - `rules/triage.py`의 `triage()`: 규칙 판정 → 모델이 있으면 `by_model = model.acuity == "emergency"`, `emergency = by_rule or by_model`, 모델이 없으면 지금 보조 점수 그대로
  - 진료과: 규칙표가 명시적으로 정한 조합은 규칙표 결과를 유지한다. 규칙표가 기본값(폴백 분기)으로 떨어지는 조합에서만 `departmentProba` 상위 2개를 `primary`/`alt`로 쓴다. 어느 분기가 기본값인지 `rules/triage.py`를 보고 `## 결과`에 적는다
  - `TriageResult.model: { acuity, acuityProba, departmentProba, shap } | None` 추가. `modelScore`는 의미를 바꾸지 않는다
  - `tests/test_model_triage.py`: `predict`를 가짜 함수로 바꿔 규칙 응급 + 모델 비응급 → 응급, 규칙 비응급 + 모델 응급 → 응급, 모델 없음 → 지금과 같음, 기본값 분기에서만 모델 진료과 사용
- 하지 않는 것
  - 모델 학습·평가·아티팩트 생성(`modeling/`), 센터 화면에 SHAP 표시(frontend), 모델 결과 로그 수집

## API·파일
- 변경: `POST /api/triage` 응답에 `model` 선택 필드 추가. 모델이 있을 때 `byModel`·`emergency`·`department`(기본값 분기만) 값이 달라질 수 있다
- 추가: `app/model.py`, `tests/test_model_triage.py`
- 수정: `app/settings.py`, `app/rules/triage.py`, `app/schemas.py`, `pyproject.toml`(모델링 패키지 의존), `README.md`(API 표·예시·"나중에 붙일 자리" 표)

## 완료 기준
- [ ] `uv run pytest` 통과. `MODEL_DIR`이 빈 기본 상태에서 `test_parity.py`의 `triage` 케이스가 그대로 통과한다
- [ ] `grep -rn "pickle\|joblib" app/`이 비어 있다
- [ ] 실제 아티팩트(`modeling/models/*/v1/`)로 띄워 README의 예시 입력 2건(손·베인 상처·출혈, 가슴·통증)을 넣은 응답이 `## 결과`에 있다. 가슴·통증은 모델 결과와 관계없이 `emergency: true`, `byRule: true`다
- [ ] 모델 포함 `/api/triage` 응답 시간(10회 평균)이 `## 결과`에 있다
- [ ] `README.md`의 `TriageResult` 예시에 `model`이 있고, "나중에 붙일 자리" 표의 모델 두 행이 완료로 바뀐다

## 결과

## 메모
- 모델링 코드를 부르는 방법은 시작 전에 사용자와 정한다. 후보는 (a) `[tool.uv.sources]`로 `../modeling` 경로 의존성(모델링의 `package = false`를 바꿔야 함), (b) `PYTHONPATH`에 `modeling/src` 추가. 피처 코드를 서버에 복사하는 방법은 쓰지 않는다
- `acuity` 값(`emergency`/`today`/`outpatient`)은 modeling 08 메모에 있듯 백엔드에 아직 정의되지 않았다. 이 항목에서 `vocab.py`에 `Acuity`로 정의하고 모델링 `schema.py`와 같은지 확인한다
- 모델이 `today`/`outpatient`를 내도 프론트 화면은 응급/비응급 둘뿐이다. 3단계 표시는 frontend 항목이다
