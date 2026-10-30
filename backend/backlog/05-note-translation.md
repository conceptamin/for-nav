# 05. 리포트 자유 입력 번역과 역번역 검사

상태: 완료
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
- [x] `uv run pytest` 통과. LLM이 꺼진 기본 상태에서 `test_parity.py`의 리포트·센터 요약 케이스가 그대로 통과한다
- [x] 역번역 검사가 `same: false`를 주면 `note`가 지금 표시와 같고 `translation.status`가 `rejected`다
- [x] 번역 성공 시에도 원문이 `note`에 남아 있다
- [x] 픽스처 자유 입력 전부를 실제 LLM으로 돌려 수락/거부 건수와 거부 사유 종류별 건수를 `## 결과`에 적는다
- [x] `README.md` "나중에 붙일 자리" 표의 "리포트 `note` 번역" 행이 완료로 바뀐다

## 결과

### 적용 자리(문서 범위에서 바꾼 점)
- 의료진 리포트 `note` 행: 성공 시 `valueKo`가 `번역 (원문: 원문)`이다. `valueNative`는 원문 그대로다.
- 센터 요약: 자유 입력은 지금 `native`의 메모 줄에만 있고 `ko`에는 없다. 사용자와 정해 성공 시 `ko` 끝에 `근로자 메모(번역): "…"` 한 문장을 더하고, 원문은 `native`에 그대로 둔다.
- 센터 미리보기(`/api/report/center`)만 바꾸면 센터 접수함에는 번역이 가지 않는다. 사용자와 정해 `POST /api/center/cases`도 같은 함수로 번역해 `summaryKo`를 만든다. 문서에 없던 경로 변경이다(응답 형태는 그대로).

### 결정
- 호출 순서: 번역 → guard(`check_ko_text`: 빈 값·한국어 여부·금지어, 길이·줄 수는 원문을 따르므로 보지 않음) → 역번역 → 비교. guard에 걸리면 뒤 두 호출을 하지 않는다.
- 상태: 번역을 만들었지만 guard·비교에 걸리면 `rejected`, 번역할 필요가 없거나(한국어 사용자, 빈 입력, `note` 제외) LLM이 없거나 호출이 끝내 실패하면 `skipped`다. 호출 실패는 품질 판단이 아니라서 `rejected`와 나눴다.
- 근로자가 `note`를 리포트에서 뺐으면 LLM에 보내지 않는다(`build_clinician_report`의 "제외한 항목은 계산하지 않는다" 원칙).
- 역번역 언어는 근로자 UI 언어(`intake.language`)다. 원문이 다른 언어여도 비교는 사실 단위라 영향이 없다(픽스처 n=24는 언어 vi, 원문 영어).
- 비교 출력은 `{ diff, same }` 순서다. 처음 `{ same, diff }`로 돌렸을 때 n=0이 diff에 "wording only … treated as same"이라 쓰고도 `same: false`를 냈다. diff를 먼저 쓰게 하고 "같은 것을 가리키는 다른 낱말은 차이가 아니다"를 더한 뒤 사라졌다.
- `diff`는 원문 사실을 담을 수 있어 로그에 남기지 않는다. 로그에는 `translation rejected=<사유>`만 남는다.
- `/api/report/clinician`의 `llmSlots`는 계속 `[]`이고, `note`의 LLM 사용 여부는 `translation`으로 알린다.
- 빌더(`build_clinician_report`, `build_center_summary`)는 선택 인자 `note_translation`만 받는다. 없으면 프론트 템플릿과 같아 `test_parity.py`가 그대로 통과한다.

### 실행
- `uv run ruff check . && uv run ruff format --check .` → 통과
- `uv run pytest` → 2769 passed(새 테스트 `tests/test_translation.py` 16개). LLM 꺼짐 상태의 parity 리포트·센터 요약 케이스(clinician 300, center 400) 그대로 통과
- 실제 LLM: `uv run --env-file .env python scripts/translate_check.py` (`claude-haiku-5-5`), 픽스처 자유 입력 28건(한국어 9건은 `skipped`)

| 결과 | 건수(비한국어 19건) |
|---|---|
| `ok` | 17 |
| `rejected` — 역번역 불일치 | 2 |
| `rejected` — guard(금지어·한국어 아님·빈 값) | 0 |
| `skipped` — 호출 실패 | 0 |

  - 거부 2건은 모두 타당했다. n=24 "Rash after painting the ship": "배"가 선박·복부 둘 다라 역번역이 "배(복부)에 페인트칠한 뒤"가 됐다. n=32 "…and it bleeds": 번역이 "지금도 피가 납니다"로 원문에 없는 "지금도"를 더했다
- 소요 시간(비한국어 19건, 호출 3회): 평균 3.9초, 최대 5.7초. 최악은 `LLM_TIMEOUT_S(10) × LLM_ATTEMPTS(2) × 3 = 60초`다

### 바뀐 API
- `POST /api/report/clinician`: 선택 필드 `translation: { status }` 추가, `ok`면 `note`의 `valueKo`가 `번역 (원문: 원문)`
- `POST /api/report/center`: 선택 필드 `translation: { status }` 추가, `ok`면 `ko` 끝에 번역 메모 한 문장
- `POST /api/center/cases`: 응답 형태는 같고, LLM이 있으면 `case.summaryKo`에 번역 메모가 더해진다

### 남은 문제
- 최악 지연(60초)은 리포트 화면에 길다. 평균 4초라 번역·역번역을 한 호출로 합치지는 않았다. 전체 시간 제한(예: 번역 전체 8초)을 둘지는 프론트 API 모드에서 체감을 보고 정한다
- 센터 사례에는 `translation.status`가 저장되지 않는다. 센터 화면에서 번역 여부를 보여 줄지는 frontend 항목이다

## 메모
- 호출이 세 번이라 느리다. 리포트 생성은 사용자가 기다리는 화면이므로 `LLM_TIMEOUT_S`와 합쳐 몇 초가 되는지 결과에 적고, 길면 번역·역번역을 한 호출로 합칠지 사용자와 정한다
- 베트남어 원어민 검수(frontend README)는 이 항목의 범위가 아니다. 검수 결과가 오면 거부 기준을 조정한다
