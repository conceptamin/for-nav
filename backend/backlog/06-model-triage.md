# 06. 응급도·진료과 모델 연결

상태: 완료
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
- [x] `uv run pytest` 통과. `MODEL_DIR`이 빈 기본 상태에서 `test_parity.py`의 `triage` 케이스가 그대로 통과한다
- [x] `grep -rn "pickle\|joblib" app/`이 비어 있다
- [x] 실제 아티팩트(`modeling/models/*/v1/`)로 띄워 README의 예시 입력 2건(손·베인 상처·출혈, 가슴·통증)을 넣은 응답이 `## 결과`에 있다. 가슴·통증은 모델 결과와 관계없이 `emergency: true`, `byRule: true`다
- [x] 모델 포함 `/api/triage` 응답 시간(10회 평균)이 `## 결과`에 있다
- [x] `README.md`의 `TriageResult` 예시에 `model`이 있고, "나중에 붙일 자리" 표의 모델 두 행이 완료로 바뀐다

## 결과

### 정한 것
- 모델링 코드 부르기: (b) `PYTHONPATH`에 `modeling/src`(사용자와 정함). `modeling/`은 고치지 않았다. 서버 의존성에 `lightgbm==4.7.0`, `numpy==2.5.4`를 modeling과 같은 버전으로 더했다(`predict.py`가 이 둘만 import한다). `MODEL_DIR`이 비면 `fornav_modeling`을 import하지 않아 CI·기본 실행은 그대로다.
- 버전: 문서는 `v1`이라 했지만 `predict.py`가 `VERSION = "v2"`로 고정하고 그 폴더만 읽는다(modeling backlog 10, 결측 학습). 서버는 버전을 다시 적지 않으므로 v2로 확인했다.
- `MODEL_DIR`은 `modeling/models` 폴더(`predict(models_dir=)`)다. 없는 폴더면 설정 단계에서, 아티팩트가 깨졌거나 import가 안 되면 lifespan에서 서버가 뜨지 않는다.
- 응급이면 진료과는 규칙표다(사용자와 정함). 실제 아티팩트로 처음 띄웠을 때 가슴·통증(규칙 응급)이 내과 묶음 분기라 모델 값 ortho/internal이 됐다. 모델 앙상블이 가슴 통증에서 정형외과(0.35)를 내과(0.25)보다 높게 보기 때문이다. 응급(규칙·모델 어느 쪽이든)이면 분기와 관계없이 규칙표를 쓰도록 바꿨다.
- 진료과 기본값 분기: `rules/triage.py`의 마지막 `family/internal`은 **부위가 하나라도 있으면 닿지 않는다**(13개 부위가 모두 앞 분기에 있고, 진료과는 부위·증상이 모두 있을 때만 계산한다). 문서대로면 모델 진료과가 한 번도 쓰이지 않으므로, 사용자와 정해 **내과 묶음 분기**(배·가슴·온몸 부위 또는 발열·구토·어지러움 → internal/family)**와 기본값**을 막연한 분기로 보고 그때만 모델 앙상블 상위 2개(`departmentTop2`, 모델 쪽 폴백 포함)를 쓴다. `rule_department()`가 `(결과, 막연한지)`를 돌려준다.
- `byModel`: 모델이 있으면 `model.acuity == "emergency"`, 없으면 지금 보조 점수. 모델만 응급이면 `reasons`는 기존 열거값 `riskScore`(위험 신호 점수 높음)를 쓴다. 새 열거값을 만들지 않았다.
- `vocab.py`에 `Acuity = Literal["emergency", "today", "outpatient"]`. `predict.py`의 `ACUITIES`와 같다.
- `TriageResult.model`은 `acuity`, `acuityProba`, `departmentProba`, `shap`만 내보낸다. `departmentTop2`·`departmentFallback`은 서버 안에서만 쓴다(`exclude`).
- 예측 중 예외는 잡아서 규칙·보조 점수 결과로 돌아간다. 응급 판정 경로가 모델 오류로 500이 되지 않게 했다. 로그에는 예외 종류만 남는다.
- 모델은 lifespan에서 한 번 읽어 `app.state.model`에 둔다(모듈 수준 상태 없음, LLM 클라이언트와 같은 방식).

### 실행
- `uv run ruff check . && uv run ruff format --check .` → 통과
- `uv run pytest` → 2829 passed(main의 04·05 병합 후, 새 테스트 `tests/test_model_triage.py` 60개, 그중 44개는 `MODEL_DIR` 없는 `/api/triage`가 parity 픽스처와 같은지). `test_parity.py`의 triage 케이스 그대로 통과
- `grep -rn "pickle\|joblib" app/` → 출력 없음
- `PYTHONPATH=../modeling/src MODEL_DIR=../modeling/models uv run fastapi run app/main.py` 뒤 `curl -XPOST /api/triage`

| 입력 | emergency | byRule | byModel | model.acuity | department | 비고 |
|---|---|---|---|---|---|---|
| 손·베인 상처·출혈 | false | false | false | outpatient(0.87) | surgery/ortho | 규칙표 그대로(명시적 분기) |
| 가슴·통증 | **true** | **true** | true | emergency(0.70) | internal/family | 규칙 응급이라 진료과도 규칙표(바꾸기 전에는 모델 값 ortho/internal) |
| 배·통증·구토 | false | false | false | outpatient(0.57) | internal/family | 모델 상위 2개가 규칙표와 같음 |

  응답 전문(손·베인 상처·출혈): `{"emergency":false,"reasons":[],"byRule":false,"byModel":false,"modelScore":2,"department":{"primary":"surgery","alt":"ortho"},"missing":[],"model":{"acuity":"outpatient","acuityProba":{"emergency":0.0166,"today":0.1145,"outpatient":0.8689},"departmentProba":{"ortho":0.2924,"surgery":0.4758,"internal":0.0531,"ophth":0.0002,"ent":0.0009,"derm":0.0110,"dental":0.0010,"neuro":0.0001,"family":0.1655,"occ":0.0000},"shap":[{"feature":"symptom_cut","value":1.0,"contribution":1.1125},{"feature":"body_hand","value":1.0,"contribution":1.0225},{"feature":"body_chest","value":0.0,"contribution":0.2988}]}}`(확률은 소수 넷째 자리로 줄임)
- 응답 시간: 모델 포함 `/api/triage` 10회 평균 2.1ms, 최대 2.3ms(로컬, curl `time_total`)

### 바뀐 API
- `POST /api/triage` 응답에 선택 필드 `model: { acuity, acuityProba, departmentProba, shap }`(모델이 없으면 키 없음)
- 모델이 있으면 `byModel`·`emergency`·`reasons`(`riskScore`)·`department`(비응급의 내과 묶음·기본값 분기만) 값이 달라질 수 있다

### 남은 문제
- 진료과 앙상블이 가슴 통증에서 정형외과를 먼저 내는 것은 모델 쪽 문제로 남는다. 실제 아티팩트에서 가슴·통증, 가슴·저림은 모두 응급(규칙 또는 모델)이라 규칙표 internal/family가 나온다. 응급이 아닌 내과 묶음 조합에서는 여전히 모델 값을 쓴다. modeling 쪽에 알린다
- 프론트 화면은 응급/비응급 둘뿐이라 `today`/`outpatient`와 SHAP 표시는 frontend 항목이다

## 메모
- 모델링 코드를 부르는 방법은 시작 전에 사용자와 정한다. 후보는 (a) `[tool.uv.sources]`로 `../modeling` 경로 의존성(모델링의 `package = false`를 바꿔야 함), (b) `PYTHONPATH`에 `modeling/src` 추가. 피처 코드를 서버에 복사하는 방법은 쓰지 않는다
- `acuity` 값(`emergency`/`today`/`outpatient`)은 modeling 08 메모에 있듯 백엔드에 아직 정의되지 않았다. 이 항목에서 `vocab.py`에 `Acuity`로 정의하고 모델링 `schema.py`와 같은지 확인한다
- 모델이 `today`/`outpatient`를 내도 프론트 화면은 응급/비응급 둘뿐이다. 3단계 표시는 frontend 항목이다
