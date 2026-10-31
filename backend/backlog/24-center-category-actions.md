# 24. 센터 사례의 상담 분야·조치 기록을 받고 돌려주기

상태: 대기
의존: frontend 41(`category`·`actions`·`referredTo`와 `defaultCategory`, `parity.json` 재생성)

## 목표
센터 회신(2026-10-31)에 맞춰 프론트가 센터 사례에 상담 분야(의료·보건 / 건강보험·공공의료 / 의료비 지원)와 조치 기록(정보 제공 / 통역 지원 / 관계기관 연계 / 후속 상담 필요, 연계 기관)을 더했다(frontend 41). 프론트가 원본이므로 서버의 센터 사례도 같은 필드를 저장·수정·응답하고, 접수 때 기본 분야를 프론트와 같은 규칙으로 채운다. 그전까지 API 모드에서는 분야·조치가 서버에 남지 않고 `backend` CI의 동기화 테스트가 실패한다.

## 범위
- 하는 것
  - `app/vocab.py`: `CaseCategory`(`medical`/`insurance`/`cost`), `CaseAction`(`info`/`interpret`/`referral`/`followUp`), `ReferralTarget`(`nhis`/`kcomwel`/`hospital`/`ulsan`/`other`). 값과 순서는 `frontend/src/domain/centerCase.ts`와 같다
  - `app/rules/urgency.py`(또는 새 `rules/category.py`): `default_category(coverage_path, request_types)` ← 프론트 `defaultCategory`. `ulsanSupport` → `cost`, 그 밖에 `nhis`이거나 요청 종류가 `["policy"]`뿐이면 `insurance`, 나머지 `medical`
  - `app/schemas.py`: `CenterCase`에 `category`, `actions: list[CaseAction]`, `referred_to: list[ReferralTarget]`. `PATCH /api/center/cases/{id}` 본문을 `{ status }`에서 `{ status?, category?, actions?, referred_to? }`로. 적어도 하나는 있어야 하고(빈 본문 422), 겹치는 값은 422
  - `app/routers/center.py`: 접수 때 `category`를 규칙으로 채우고 `actions`·`referred_to`는 `[]`. `PATCH`는 보낸 필드만 바꾼다. `referral`이 없는데 `referred_to`가 비어 있지 않으면 422
  - `app/data/mock.py`: mock 24건의 `category`를 같은 규칙으로 계산(새 난수 없음)
  - `app/store.py`·`app/store_sqlite.py`: 사례 저장소에 세 필드 추가. 기존 SQLite 파일을 열 때 열이 없으면 더하고 기본값으로 채운다
  - `tests/test_parity.py`에 `defaultCategory` 비교, `tests/test_api.py`에 PATCH 조합·422·접수 기본값
  - `README.md`: `PATCH` 본문, `CenterCase` 필드, "구현 순서"
- 하지 않는 것
  - 통계 집계(25), 상태 열거값 변경, 프론트 코드

## API·파일
- `PATCH /api/center/cases/{id}` 요청: `{ "status": "progress" }` → `{ "status"?: ..., "category"?: "insurance", "actions"?: ["info", "referral"], "referredTo"?: ["nhis"] }`
- `GET /api/center/cases`, `GET /api/center/cases/{id}`, `POST /api/center/cases` 응답의 `CenterCase`: `category`, `actions`, `referredTo` 추가
- 수정: `app/vocab.py`, `app/rules/`, `app/schemas.py`, `app/routers/center.py`, `app/data/mock.py`, `app/store.py`, `tests/`, `README.md`

## 완료 기준
- [ ] `uv run ruff check . && uv run ruff format --check .` 통과
- [ ] frontend 41이 만든 `parity.json`으로 `uv run pytest` 통과(`defaultCategory` 비교 포함)
- [ ] `{ "status": "progress" }`만 보내는 기존 요청이 그대로 200이다
- [ ] 빈 본문, 모르는 분야, `referral` 없이 `referredTo`가 있는 요청이 422다
- [ ] 세 열이 없는 옛 SQLite 파일로 서버를 띄워도 사례 목록이 열린다

## 결과

## 메모
- 분야 기본값 규칙은 프론트 `domain/centerCase.ts`가 원본이고 서버는 그것을 옮긴다. 증상 내용으로 분야를 가르지 않는다
- 열거값을 더하는 것이다. `modeling/tests/test_schema.py`가 보는 `Intake`·`Lang`은 바뀌지 않아 모델링 쪽 변경은 없다
