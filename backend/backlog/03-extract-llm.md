# 03. `/api/extract` LLM 추출

상태: 완료
의존: 02

## 목표
자유 입력(영어·베트남어·한국어)에서 부위·증상·발생 시점·업무 관련·작업 유형을 뽑는 자리를 키워드 사전에서 LLM으로 바꾼다. 출력은 `vocab.py` 열거값으로 고정하고, LLM이 없거나 실패하면 지금 키워드 사전으로 그대로 동작한다.

## 범위
- 하는 것
  - `rules/extract_llm.py`: 프롬프트(system에 열거값 목록과 "열거값 밖의 값·병명·추측 금지"), 출력 스키마 `Extraction`(이미 `Literal`로 검증됨)
    - 필드 하나가 열거값을 벗어나면 그 필드만 `null`로 버린다. 전체가 JSON이 아니면 `generate`가 재시도한다
  - `routers/worker.py`의 `/api/extract`: `get_llm_client()`가 `None`이거나 `LLMUnavailableError`면 `extract_from_text`로 대체. 이후 `merge_extraction`은 그대로
  - `ExtractResponse`에 선택 필드 `source: "llm" | "keywords"` 추가(기존 필드 변경 없음)
  - `tests/test_extract_llm.py`: `FakeLLMClient`로 정상·열거값 밖·실패 대체 경우, 프론트 버튼 입력이 LLM 추출값보다 우선하는지
  - 픽스처의 자유 입력 전부를 실제 LLM에 한 번 넣어 키워드 결과와 비교한 표를 `## 결과`에 적는다(일치 건수/전체, 어긋난 사례와 어느 쪽이 맞는지)
- 하지 않는 것
  - 응급 키워드 판정 변경(`/api/triage`의 규칙은 그대로 자유 입력에 키워드로 돈다), 프론트 화면 변경, 프롬프트 다국어 분기

## API·파일
- 변경: `POST /api/extract` 응답에 `source` 선택 필드 추가
- 추가: `app/rules/extract_llm.py`, `tests/test_extract_llm.py`
- 수정: `app/routers/worker.py`, `app/schemas.py`, `README.md`(API 표·예시·"나중에 붙일 자리" 표)

## 완료 기준
- [x] `uv run pytest` 통과. LLM이 꺼진 기본 상태에서 `test_parity.py`의 `extract` 케이스가 그대로 통과한다
- [x] `FakeLLMClient`가 열거값 밖의 값(`"bodyParts": ["finger"]`)을 주면 그 필드만 비고 나머지는 반영된다
- [x] `FakeLLMClient`가 두 번 실패하면 응답 `source`가 `keywords`이고 결과가 키워드 사전과 같다
- [x] 버튼으로 고른 부위·증상이 있으면 LLM 값으로 덮이지 않는다
- [x] 픽스처 자유 입력 비교표가 `## 결과`에 있다. 오탐 방지 사례(`"ở nhà máy"`, 영어 `painting`)의 LLM 결과가 적혀 있다
- [x] `README.md`의 `/api/extract` 예시에 `source`가 있다

## 결과

실행한 명령 (`backend/`)

```sh
uv run ruff check . && uv run ruff format --check .   # 통과
env -u LLM_API_KEY -u ANTHROPIC_API_KEY uv run pytest  # 998 passed (test_extract_llm.py 73)
uv run --env-file .env python scripts/extract_compare.py  # 실제 LLM(claude-haiku-5-5), 아래 표
```

바뀐 API
- `POST /api/extract` 응답에 선택 필드 `source: "llm" | "keywords"`를 더했다. 기존 필드(`extraction`, `intake`, `filled`)는 그대로다
- 키가 없는 기본 상태에서는 `source: "keywords"`이고, 나머지 응답은 프론트 키워드 추출과 같다(`parity.json`의 extract 58건을 경로로도 비교)

추가·수정 파일
- 추가: `app/rules/extract_llm.py`, `tests/test_extract_llm.py`, `scripts/extract_compare.py`(비교표용, CI 밖)
- 수정: `app/routers/worker.py`(`/api/extract`를 async로, LLM 클라이언트 의존성), `app/main.py`(lifespan에서 클라이언트 생성·종료), `app/schemas.py`(`source`), `README.md`(API 표·예시·"나중에 붙일 자리"·폴더 구조·LLM 절)

테스트 (`test_extract_llm.py` 73개, 가짜 LLM)
- 정상 추출 → `source: "llm"`, 목록 순서는 vocab 순서
- 자유 입력은 user 부분에만 들어가고 system은 상수, system에 열거값·지시 무시·진단 금지가 있음
- `"bodyParts": ["finger"]` → `bodyParts`만 `[]`, 나머지 필드 반영. 단일 값 필드(onset·workRelated·workType)·목록 원소·목록 아닌 값도 각각 그 필드만 비움
- 두 번 실패 → `source: "keywords"`, 결과가 `extract_from_text`와 같음
- 버튼으로 고른 부위·증상·작업 유형은 LLM 값으로 덮이지 않고 빈 항목만 채움
- 빈 자유 입력은 LLM을 부르지 않음
- 키 없는 기본 상태에서 경로 응답이 `parity.json` extract 58건과 같음
- lifespan이 클라이언트를 한 번 만들고 종료 시 닫음, 키가 없으면 `app.state.llm`이 `None`

### 픽스처 자유 입력 비교 (실제 LLM)

`parity.json` extract 58건 중 자유 입력이 비지 않은 서로 다른 문장 28개를 넣었다. 번호는 그 문장이 처음 나오는 extract 순번이다(같은 문장의 버튼 입력 변형은 묶었다). 원문은 옮기지 않는다. LLM 대체(`source: "keywords"`)는 매 회차 0건이었다.

| 회차 | 프롬프트 | 전체 일치 | bodyParts | symptoms | onset | workRelated | workType |
|---|---|---|---|---|---|---|---|
| 1 | 첫 판 | 17/28 | 24/28 | 27/28 | 28/28 | 21/28 | 26/28 |
| 2 | 추측 금지 강화(최종) | 18/28 | 25/28 | 26/28 | 28/28 | 24/28 | 26/28 |
| 3 | 2와 같음(재실행) | 19/28 | 25/28 | 26/28 | 28/28 | 24/28 | 26/28 |

1회차에서 LLM은 작업 이름(연마·도장·용접·들기·프레스)만 보고 `workRelated: yes`를 7건(6·8·22·24·30·40·44) 채웠다. 52번은 증상(어지러움)으로 부위 `head`를 추측했다. 그래서 일반 규칙("한 필드로 다른 필드를 채우지 않는다", "작업 이름만으로는 yes가 아니다", "burn은 화상 손상")을 더했다. 2·3회차 표는 최종 프롬프트 기준이다.

최종 프롬프트(2·3회차)에서 키워드와 어긋난 사례

| # | 필드 | 키워드 | LLM | 맞는 쪽 |
|---|---|---|---|---|
| 0 | workRelated | `yes` | `null` | 판단 필요. 문장에는 "기계에 끼었다"만 있다. 키워드는 `máy`(기계)를 업무 신호로 보고(프론트 설계), LLM은 비워 두어 프론트가 업무 관련을 다시 묻는다 |
| 2 | workType | `machine` | `null` | **LLM.** 오탐 방지 사례 `"ở nhà máy"`(공장에서). 키워드는 `máy`로 `machine`을 잘못 잡는다. `workRelated`는 둘 다 `yes`(키워드도 `ở nhà`를 "집"으로 잡지 않음) |
| 8 | bodyParts | `[]` | `["hand"]` | **LLM.** 손이 적혀 있다 |
| 8 | workRelated | `null` | `yes` | **키워드.** 작업 이름(용접)만 있다. 프롬프트 규칙 위반 |
| 12 | bodyParts | `[]` | `["hand"]` | **LLM.** 손이 적혀 있다 |
| 18 | symptoms | `chemical` | `burn, chemical` | **키워드 쪽.** 화학물질 접촉 뒤 따끔거림이라 화상이라고 할 근거가 약하다(화학 화상일 수도 있어 애매) |
| 22 | bodyParts | `[]` | `["back"]` | **LLM.** 허리가 적혀 있다 |
| 26 | symptoms | `pain` | `[]`(2회차) / `pain`(3회차) | **키워드.** "다쳤다"를 통증으로 보는 것이 맞다. 회차마다 달라 불안정하다 |
| 40 | workRelated | `null` | `yes` | **키워드.** 프레스 기계만 있다. 프롬프트 규칙 위반 |
| 44 | workRelated | `null` | `yes` | **키워드.** 용접만 있다. 프롬프트 규칙 위반 |
| 52 | workType | `null` | `painting` | **키워드.** 시너 냄새로 도장 작업을 추측했다 |
| 52 | symptoms | `dizzy, chemical` | 2회차 같음 / 3회차 `dizzy` | **키워드.** 3회차는 화학물질 노출을 빠뜨렸다 |

오탐 방지 사례
- `"ở nhà máy"`(2번): LLM `workRelated: yes`, `workType: null`. 장소 오탐도 작업 유형 오탐도 없다(키워드는 작업 유형 오탐)
- 영어 `painting`(24번): LLM `symptoms: ["rash"]`, `workType: "painting"`, `workRelated: null`(2·3회차). `painting` 안의 `pain`을 통증으로 잡지 않았다. 1회차는 `workRelated: yes`로 추측했다

정리: LLM은 부위를 키워드보다 잘 찾고(4건), 공장 표현 오탐이 없다. 반면 작업 이름에서 업무 관련을 추측하는 경향이 프롬프트를 고친 뒤에도 3건 남았다. 증상을 더하거나 빼는 경우(18·26·52)도 있고 회차마다 흔들린다.

결정 사항
- **필드 단위로 버림**: 범위대로 필드 하나가 열거값을 벗어나면 그 필드 전체를 비운다. 목록 안에 틀린 원소가 하나라도 있으면 목록 전체를 `[]`로 한다. 원소만 골라 남기지 않는 이유는, 틀린 값을 낸 출력이면 나머지 원소도 믿기 어렵고 비우면 프론트가 버튼 질문으로 되묻기 때문이다
- **출력 스키마 = `Extraction`의 열거값**: `LLMExtraction(Extraction)`에 wrap 검증기를 두어, 공급자에 보내는 JSON 스키마에는 열거값이 그대로 남고 받은 값만 필드별로 관대하게 검증한다. 클래스 docstring은 스키마 `description`으로 LLM에 넘어가므로 두지 않았다
- **열거값 목록은 vocab에서 만든다**: system 프롬프트의 허용값과 영어 설명은 `vocab.py`(`BODY_PARTS`·`SYMPTOMS`·`ONSETS`·`WORK_TYPES`의 `en`)에서 만든다. 프롬프트에 값을 다시 적지 않는다
- **`source` 타입은 `schemas.py`에 둔다**: 프론트 타입에 없는 서버 전용 응답 메타라 `vocab.py`(프론트 `vocab.ts`와 1:1)에 넣지 않았다
- **클라이언트는 lifespan에서 한 번**: 02 메모대로 시작 시 `get_llm_client()`를 `app.state.llm`에 두고 종료 시 `aclose()`한다. 라우터는 `Depends(llm_client)`로 받아, 테스트는 `dependency_overrides`로 가짜를 넣는다. lifespan 밖(`TestClient(app)`를 `with` 없이 쓰는 기존 테스트)에서는 `None`이라 키워드로 동작한다
- 빈 자유 입력은 LLM을 부르지 않는다

남은 문제
- LLM이 키워드보다 나쁜 사례(8·40·44 workRelated, 18·26·52 증상, 52 workType)가 있다. 키워드 결과와 합칠지(예: 목록 필드는 합집합, 단일 값은 LLM 우선) 사용자가 정한다(메모). 정해지면 별도 항목으로 한다

## 메모
- LLM이 키워드보다 나쁘게 나온 사례가 있으면 숨기지 않고 적는다. 그 경우 키워드 결과와 합집합을 쓸지는 사용자가 정한다
- 자유 입력은 로그에 남지 않는다(01). 비교표에도 픽스처 번호만 적고 원문은 옮기지 않는다
