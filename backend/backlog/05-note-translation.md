# 05. 리포트 자유 입력 번역과 역번역 검사

상태: 대기
의존: 02, 04

## 목표
의료진 리포트와 센터 요약에서 지금 "원문 + (원문, 번역 미연결)"로 표시되는 자유 입력을 LLM으로 한국어로 번역하고, 역번역이 원문과 다르면 번역을 버리고 지금 표시로 돌아간다. 뜻이 바뀐 번역이 의료진에게 가지 않게 하는 것이 목적이다.

## 범위
- 하는 것
  - `templates/translate.py`: 번역 프롬프트(출력 `{ "ko": str }`)와 역번역 프롬프트(출력 `{ "back": str }`), 검사 프롬프트(원문·역번역 두 문장을 주고 `{ "same": bool, "diff": str }`)
    - 검사가 `same: false`이거나 세 호출 중 하나라도 실패하면 번역을 쓰지 않는다
    - 04의 금지어 검사를 번역 결과에도 적용한다
  - 적용 자리: `ClinicianReport`의 `note` 행, `CenterSummary`의 자유 입력 줄. 원문은 항상 함께 남긴다(번역만 보여주지 않는다)
  - `/api/report/clinician`, `/api/report/center` 응답에 선택 필드 `translation: { "status": "ok" | "rejected" | "skipped" }` 추가
  - `tests/test_translation.py`: `FakeLLMClient`로 성공, 역번역 불일치 거부, 호출 실패, 금지어 거부
- 하지 않는 것
  - 고정 문구 번역(이미 i18n), 근로자 화면 모국어 표시 변경, 번역 품질 사람 검수(발표 전 별도)

## API·파일
- 변경: `POST /api/report/clinician`, `POST /api/report/center` 응답에 `translation` 선택 필드 추가, `note` 값이 번역 성공 시 "번역 (원문)" 형태로 바뀜
- 추가: `app/templates/translate.py`, `tests/test_translation.py`
- 수정: `app/templates/reports.py`, `app/routers/worker.py`, `app/schemas.py`, `README.md`

## 완료 기준
- [ ] `uv run pytest` 통과. LLM이 꺼진 기본 상태에서 `test_parity.py`의 리포트·센터 요약 케이스가 그대로 통과한다
- [ ] 역번역 검사가 `same: false`를 주면 `note`가 지금 표시와 같고 `translation.status`가 `rejected`다
- [ ] 번역 성공 시에도 원문이 `note`에 남아 있다
- [ ] 픽스처 자유 입력 전부를 실제 LLM으로 돌려 수락/거부 건수와 거부 사유 종류별 건수를 `## 결과`에 적는다
- [ ] `README.md` "나중에 붙일 자리" 표의 "리포트 `note` 번역" 행이 완료로 바뀐다

## 결과

## 메모
- 호출이 세 번이라 느리다. 리포트 생성은 사용자가 기다리는 화면이므로 `LLM_TIMEOUT_S`와 합쳐 몇 초가 되는지 결과에 적고, 길면 번역·역번역을 한 호출로 합칠지 사용자와 정한다
- 베트남어 원어민 검수(frontend README)는 이 항목의 범위가 아니다. 검수 결과가 오면 거부 기준을 조정한다
