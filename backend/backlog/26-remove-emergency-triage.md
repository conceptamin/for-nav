# 26. 서버가 응급 여부를 판정하지 않게 하기

상태: 대기
의존: frontend 43(`TriageResult`·`Intake`·`CenterCase` 변경, `parity.json`·`lang/packs.json` 재생성). 한 PR로 낸다

## 목표
앱이 응급 여부를 판정하지 않기로 했다(frontend 43, 사용자와 정함 2026-10-31). 프론트가 원본이므로 `POST /api/triage`도 응급 규칙·보조 점수·응급도 모델 판정을 빼고 진료과 추천만 돌려준다. 센터 사례의 응급 판정 이력과 긴급도 +3도 뺀다. 응급도 모델 결과(`model.acuity`)를 더는 읽지 않게 해서, 모델링 쪽이 응급도 모델을 지울 수 있게 한다(modeling 15).

## 범위
- 하는 것
  - `app/rules/triage.py`
    - `EMERGENCY_KEYWORDS*`, `HEAD_INJURY*`, `VOMIT*`, `SEVERITY*`, `rule_reasons`, `model_score`, `MODEL_THRESHOLD`, `REASON_KO`를 뺀다
    - `triage()`는 `{ department, missing, model }`만 채운다
    - `department_for`의 `emergency` 인자를 뺀다. 응급이면 규칙표를 쓰던 예외는 "진료과를 규칙표로 고정하는 조합"(가슴+통증, 숨참)으로 남긴다. 모델이 가슴 통증에 정형외과를 먼저 내는 문제(backlog 06 결과)가 그대로 있기 때문이다
  - `app/schemas.py`
    - `EmergencyReason`을 뺀다
    - `TriageResult`의 `emergency`·`reasons`·`by_rule`·`by_model`·`model_score`를 뺀다
    - `Intake`의 `age_group`·`sex`·`pain_score`·`mental`을 뺀다. `injury`는 진료과 모델 B 입력이라 남긴다
    - `ModelPrediction`의 `acuity`·`acuity_proba`·`shap`과 `ShapItem`을 뺀다
    - 센터 요청·`CenterCase`의 `emergency_flag`를 뺀다
  - `app/vocab.py`: `Acuity`·`AgeGroup`·`Mental`, 언어 묶음의 `emergency` 설명. `Sex`는 프로필(`schemas.py` 208행)이 쓰는지 보고 남긴다
  - `app/lang/packs.json`: frontend 43이 다시 만든 파일
  - `app/model.py`: 주석의 "응급도"와 "응급 판정은 규칙·보조 점수로 돌아간다"
  - `app/rules/urgency.py`: `rate_urgency`에서 `emergency_flag`와 +3을 뺀다(프론트 `rateUrgency`와 1:1)
  - `app/routers/center.py`, `app/routers/worker.py` 독스트링, `app/templates/reports.py`의 "응급 판정 이력" 줄, `app/data/mock.py`
  - `app/store.py`·`app/store_sqlite.py`: 기존 SQLite 파일에 `emergency_flag`가 있어도 열린다(읽을 때 버린다)
  - `tests/`: `test_api.py`(`ACUITY_INPUTS`, 422 조합), `test_model_triage.py`(모델 응급도 → 진료과·고정 조합만), `test_parity.py`, 응급 판정을 쓰던 `test_auth`·`test_chat`·`test_call`·`test_translation`의 입력
  - `README.md`: `/api/triage` 예시·필드 설명, `Intake` 선택 입력 절, `MODEL_DIR` 설명("응급도·진료과" → "진료과"), 프론트 대응 표
  - `CLAUDE.md`: "규칙이 모델보다 먼저다"(레드플래그 규칙)를 "진료과는 규칙표가 먼저고 막연한 분기만 모델"로 바꾸고, "응급 판정 경로(`/api/triage`)"를 "진료과 추천 경로"로 고친다
- 하지 않는 것
  - `modeling/` 코드·아티팩트(modeling 15). 이 항목 뒤에도 `predict()`는 `acuity`를 돌려주지만 `ModelPrediction`이 읽지 않고 버린다(pydantic 기본 `extra="ignore"`)
  - 진료과 규칙표·앙상블 변경

## API·파일
- `POST /api/triage` 응답: `{ emergency, reasons, byRule, byModel, modelScore, department, missing, model? }` → `{ department, missing, model? }`. `model`은 `{ departmentProba }`
- `Intake`(모든 요청): `ageGroup`·`sex`·`painScore`·`mental` 제거. 옛 프론트가 보내도 무시한다
- `POST /api/center/cases` 요청과 `CenterCase` 응답: `emergencyFlag` 제거
- 수정: 위 목록

## 완료 기준
- [ ] `uv run ruff check . && uv run ruff format --check .` 통과
- [ ] frontend 43이 만든 `parity.json`으로 `uv run pytest` 통과
- [ ] `MODEL_DIR=../modeling/models`로 띄워 "가슴이 아파요"를 보내면 진료과가 규칙표(내과·가정의학과)로 나오고, 응답에 `emergency`·`model.acuity`가 없다
- [ ] `emergencyFlag`·`painScore`를 함께 보내는 옛 요청도 200이다
- [ ] `emergency_flag` 열이 있는 옛 SQLite 파일로 서버를 띄워도 사례 목록이 열린다

## 결과

## 메모
- 이 항목이 modeling 15보다 먼저 들어가야 한다. 거꾸로면 `ModelPrediction` 검증이 실패해 `run_model`이 `None`을 돌려주고, 운영 서버(Mac mini, `MODEL_DIR` 있음)가 오류 없이 진료과 모델 없이 동작한다
- `modeling/tests/test_schema.py`는 백엔드 `Intake`·열거값과 모델링 `schema.py`를 비교하므로, modeling 15가 들어갈 때까지 로컬 modeling 테스트가 실패한다. CI는 modeling을 돌리지 않는다
