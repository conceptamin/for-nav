# Backend Phase 02 — 첫 흐름 API

목표일: 2026-10-23

## 목표

프론트가 텍스트 입력 → 응급 확인 → 비용 경로 → 요약 카드를 한 번 이어서 호출할 수 있도록 `/triage`, `/route`, `/summary`를 계약대로 구현한다. 응급은 이 phase에서 키워드 규칙만으로 판단하고, 모델은 phase-03에서 붙인다. YardPilot 이름을 for-nav로 바꾼다.

## 범위

포함:

- 이름 교체: `pyproject.toml`의 `name`·`description`, 환경 변수 `YARDPILOT_API_HOST`·`YARDPILOT_API_PORT` → `FORNAV_API_HOST`·`FORNAV_API_PORT`, 관련 테스트와 주석, `backend/AGENTS.md`의 등록 명령 설명. 프론트 proxy 변수 이름은 [프론트 phase-02](../../frontend/docs/phase-02.md)와 맞춘다.
- 계약 1·3·4·5장의 요청·응답 Pydantic 모델과 공통 오류 형식(`request_id` 포함).
- `fixtures/contract/`에 `/triage`·`/route`·`/summary` 요청·응답 예시 JSON. 테스트가 이 파일로 스키마 일치를 확인한다.
- `POST /route`: 계약 4장 결정 표를 순수 함수로 구현. `en`·`vi` 안내 문구, 연결 기관(`verified` 포함), `disclaimer`, `info_as_of`.
- `POST /triage`: 응급 키워드 규칙(`en`·`vi`, 공통 응급 신호: 의식 저하, 호흡곤란, 대량 출혈, 추락, 끼임, 화학물질·밀폐공간 작업 중 어지럼 등) + LLM 맥락 추출 + 진료과 대응 표. `by_model`·`model_score`·`model_version`은 `null`.
- `POST /summary`: 동의 검사, `include` 필터, LLM 요약.
- LLM 인터페이스와 가짜 구현. 실제 구현은 하나의 공급자로 두고 API 키는 환경 변수로 받는다. 공급자와 무료 등급 약관 확인 결과를 검증 결과에 기록한다.
- 요청 본문을 남기지 않는 로깅 설정.

제외:

- 응급 감지 모델 불러오기·추론 (phase-03, [모델링 phase-01](../../modeling/docs/phase-01.md) 산출물 필요).
- `/guide`, `/hospitals` (phase-03).
- 음성 인식, `/transcribe`.
- 로컬 LLM 실행 (공급자 인터페이스만 맞춰 두고 시험은 phase-03).
- CI 변경.

## 작업 체크리스트

- [ ] 이름과 환경 변수를 교체하고 기존 테스트를 새 이름으로 갱신한다.
- [ ] 계약 스키마를 Pydantic 모델로 만들고 공통 오류 응답을 구성한다.
- [ ] `fixtures/contract/` 예시 JSON을 만들고 스키마 검증 테스트를 작성한다.
- [ ] 비용 경로 결정 함수와 표의 모든 줄·필요 없는 답·빠진 답(422) 테스트를 작성한다.
- [ ] `fixtures/route-cases/`가 있으면 전체 사례를 테스트에 연결한다. 아직 없으면 연결 코드만 두고 검증 결과에 "사례 미제공"으로 적는다.
- [ ] 응급 키워드 규칙과 응급·비응급 예시 문장 테스트를 작성한다.
- [ ] 진료과 대응 표와 테스트를 작성한다.
- [ ] LLM 인터페이스, 가짜 구현, 실제 구현 1개를 만든다. 출력 스키마 검증·재시도 1회·시간 제한을 둔다.
- [ ] `/triage`에서 LLM 실패 시 응급 결과 유지와 `context_status: LLM_UNAVAILABLE`을 테스트한다.
- [ ] `/summary`에서 동의 없음 422, LLM 미호출, `include` 밖 필드가 가짜 LLM 입력과 응답에 없음을 테스트한다.
- [ ] 증상 텍스트를 담은 요청 후 캡처한 로그에 그 텍스트가 없음을 테스트한다.
- [ ] 아래 완료 조건별 실행 명령·결과를 검증 결과에 기록한다.

## 의존성

- [공통 계약](../../docs/api-contract.md) 1·3·4·5장. 10-22 고정 전 바뀌면 이 문서의 범위를 다시 맞춘다.
- `fixtures/route-cases/`: 콘텐츠 담당이 작성한다. 이 phase의 완료 조건이 아니다.
- [프론트 phase-02](../../frontend/docs/phase-02.md): proxy 환경 변수 이름.

## 완료 조건

- [ ] `uv sync --locked`, Ruff lint·format, mypy strict, pytest가 모두 오류 없이 끝난다.
- [ ] 저장소에서 `YARDPILOT`·`yardpilot` 문자열이 `backend/` 코드와 설정에 남지 않는다(phase-01 기록 문서 제외).
- [ ] 비용 경로 결정 표의 모든 줄이 테스트로 덮인다.
- [ ] LLM 실패 시에도 `/triage`가 200과 응급 결과를 돌려준다.
- [ ] `/summary`가 동의 없이 LLM을 호출하지 않고, 뺀 항목이 LLM 입력·응답에 없다.
- [ ] 테스트가 외부 네트워크에 접속하지 않는다.
- [ ] 로그에 요청 본문이 남지 않는다.
- [ ] 실제 LLM 공급자로 합성 문장 1개를 `/triage`·`/summary`에 보내 본 수동 확인 결과가 기록돼 있다.

## 검증 결과

아직 구현 전.
