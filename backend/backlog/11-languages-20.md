# 11. 근로자 언어 20개 받기

상태: 완료
의존: 없음 (프론트 `frontend/backlog/16-languages-20.md`와 같은 PR)

## 목표
프론트가 근로자 언어를 en·vi·ko에서 20개로 넓혔다(frontend 16). 서버가 새 언어를 422로 거절하지 않고, 접수 도우미·리포트·응급 키워드를 프론트와 같은 출력으로 내도록 옮긴다.

## 범위
- 하는 것
  - `vocab.py`: `Lang`·`LANGS`·`LANGUAGE_NAMES_KO`를 20개로, 어휘(`Term`)는 한국어·발음 표기 표에 언어 묶음의 표기를 합친다
  - 언어 묶음 `app/lang/packs.json`: 프론트 `src/domain/lang/*.ts`에서 `frontend/scripts/dump-lang-packs.ts`로 만든다
  - `templates/`: 모국어 문장을 언어 묶음의 문장 틀(`fill`)로 만든다. 전화 스크립트 FAQ 질문 `q`를 `{ko, native}`로
  - `rules/triage.py`: 응급 키워드를 한국어 표 + 언어 묶음으로 합친다
  - `rules/extract_llm.py`: 프롬프트의 입력 언어 문장을 "어떤 언어든"으로
- 하지 않는 것
  - 자유 입력 키워드 추출 사전(부위·증상·시점)에 새 언어 넣기. 프론트도 넣지 않았다
  - mock·센터 통계의 언어 분포(vi·en 그대로)
  - `modeling/src/fornav_modeling/schema.py`의 `Lang`(아래 메모)

## API·파일
- 요청의 `language`·`lang`: `en vi ko ne ru mn my si ar uz ja zh-CN zh-TW kk km ky th fr tl id`. 그 밖은 422
- **응답 변경**: `POST /api/visit-helper`의 `call.faq[].q`가 `{ ko, en, vi }`에서 `{ ko, native }`로 바뀐다. 프론트가 같은 PR에서 함께 바뀐다
- 파일: `app/vocab.py`, `app/lang/packs.json`(새로 만듦), `app/schemas.py`(`Tri` 삭제, `Faq.q: KoNative`), `app/templates/common.py`, `app/templates/visit.py`, `app/templates/reports.py`, `app/rules/triage.py`, `app/rules/extract_llm.py`, `tests/test_api.py`, `tests/fixtures/parity.json`, `README.md`

## 완료 기준
- [x] `parity.json`(20개 언어) 재생성 후 `uv run pytest` 통과
- [x] `uv run ruff check .`, `uv run ruff format --check .` 통과

## 결과
- `uv run pytest` → 2566 통과(20개 언어 동기화 사례 포함). `uv run ruff check .`·`uv run ruff format --check .` 통과
- `test_api.py`의 "없는 언어는 422" 예시가 `fr`이었는데 이제 지원 언어라 `de`로 바꿨다
- 결정
  1. 번역 원본은 프론트 하나다. 19개 언어 문구를 파이썬으로 다시 적지 않고 JSON으로 내보내 읽는다. 동기화 테스트가 출력이 같은지 확인한다
  2. 언어 묶음은 `vocab.py`가 표준 라이브러리(`json`)로 읽는다. modeling 테스트가 `vocab.py`를 파일로 직접 읽기 때문에 `app` 패키지를 import하지 않는다
  3. 문장 틀 자리표시 `{이름}`·`{이름:lower}`는 프론트 `fill`과 같은 규칙이다(이름은 ASCII)

## 메모
- `modeling/tests/test_schema.py`가 백엔드 `Lang`과 `schema.py`의 `Lang`(en·vi·ko)이 다르다고 3건 실패한다. `language`는 모델 피처가 아니라 `schema.py`의 `Lang` 한 줄만 맞추면 된다. modeling 폴더라 이 항목에서는 고치지 않았다
- 새 17개 언어 문구는 기계 번역 초안이다(frontend 16 메모)
