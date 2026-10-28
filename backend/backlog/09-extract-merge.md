# 09. LLM 추출과 키워드 추출 합치기

상태: 완료
의존: 03

## 목표
03의 비교에서 LLM은 부위를 더 잘 찾지만, 증상을 빠뜨리거나 작업 이름만 보고 업무 관련을 `yes`로 추측했다. 필드마다 더 믿을 만한 쪽을 쓰도록 LLM 결과와 키워드 결과를 합친다. 사용자가 03 결과를 보고 정한 규칙이다.

## 범위
- 하는 것
  - `rules/extract_llm.py`: LLM이 성공했을 때만 키워드 결과와 합친다
    - `bodyParts`·`symptoms`: 합집합(vocab 순서)
    - `workRelated`: 키워드 값만 쓴다(산재 경로 안내에 쓰이므로 추측보다 되묻기)
    - `onset`·`workType`: LLM 값
  - LLM이 없거나 실패하면 지금처럼 키워드 결과만 쓴다(`source: "keywords"`)
  - `tests/test_extract_llm.py`: 합치기 규칙 테스트, 03 테스트를 합친 결과에 맞게 고친다
  - `scripts/extract_compare.py`를 다시 돌려 03 표와 비교한 결과를 `## 결과`에 적는다
- 하지 않는 것
  - 프롬프트 변경, `source` 값 추가(합친 결과도 `"llm"`), 키워드 사전 변경

## API·파일
- 변경되는 경로·필드 없음. `source: "llm"`일 때 `extraction` 값이 위 규칙으로 합친 값이 된다
- 수정: `app/rules/extract_llm.py`, `tests/test_extract_llm.py`, `README.md`(`/api/extract`의 `source` 설명)

## 완료 기준
- [x] `uv run pytest` 통과. 키 없는 기본 상태의 `parity.json` extract 비교가 그대로 통과한다
- [x] LLM이 증상을 빠뜨려도 키워드가 찾은 증상이 남는다(합집합)
- [x] LLM이 `workRelated: yes`를 내도 키워드가 `null`이면 `null`이다
- [x] LLM이 열거값 밖 부위를 내면 그 필드는 키워드 결과만 남는다
- [x] 실제 LLM 비교를 다시 돌린 결과가 `## 결과`에 있다(03 표의 어긋난 사례가 어떻게 바뀌었는지)

## 결과

실행한 명령 (`backend/`)

```sh
uv run ruff check . && uv run ruff format --check .      # 통과
env -u LLM_API_KEY -u ANTHROPIC_API_KEY uv run pytest     # 1008 passed (test_extract_llm.py 83)
uv run --env-file .env python scripts/extract_compare.py  # 2회, 아래 표
```

바뀐 API: 경로·필드 변경 없음. `source: "llm"`일 때 `extraction`이 합친 값이다(`README.md`의 `/api/extract` 설명을 고쳤다)

테스트 (`test_extract_llm.py` +10)
- 합치기 규칙: 부위·증상 합집합(vocab 순서), LLM이 빠뜨린 키워드 증상이 남음, `workRelated`는 LLM 값과 관계없이 키워드 값(4가지 조합), `onset`·`workType`은 LLM 값(`"ở nhà máy"` 꼴: 키워드 `machine` → LLM `null`)
- 경로: LLM이 `workRelated: yes`를 내도 키워드가 `null`이면 응답·intake 모두 `null`, 열거값 밖 부위는 버리고 키워드 부위만 남음
- 03 테스트 중 LLM 출력만 보려던 것은 키워드가 아무것도 못 찾는 합성 문장으로 바꿨다(그 문장의 키워드 결과가 비어 있는지도 검사)
- 키 없는 기본 상태의 `parity.json` extract 58건 비교는 그대로 통과

### 실제 LLM 비교 (claude-haiku-5-5, 03과 같은 28문장·같은 프롬프트)

| 회차 | 전체 일치 | bodyParts | symptoms | onset | workRelated | workType |
|---|---|---|---|---|---|---|
| 03 최종(합치기 전) | 18~19/28 | 25/28 | 26/28 | 28/28 | 24/28 | 26/28 |
| 09 1회 | 21/28 | 25/28 | 26/28 | 28/28 | 28/28 | 26/28 |
| 09 2회 | 22/28 | 25/28 | 26/28 | 28/28 | 28/28 | 27/28 |

03에서 어긋났던 사례가 바뀐 결과

| # | 03에서 | 09 결과 | 비고 |
|---|---|---|---|
| 0 | workRelated 키워드 `yes` / LLM `null` | 키워드와 같음(`yes`) | 키워드 값만 쓴다 |
| 2 | workType 키워드 `machine`(오탐) / LLM `null` | `null` 유지 | LLM이 맞는 사례가 그대로 남음 |
| 8 | 부위 LLM이 찾음, workRelated LLM 추측 `yes` | 부위 `hand` 유지, workRelated `null` | 둘 다 맞는 쪽으로 |
| 12·22 | 부위 LLM이 찾음 | 유지 | |
| 18 | 증상 LLM이 `burn`을 더함 | **남음**(합집합이라 LLM 값이 들어감) | 화학물질 접촉 뒤 따끔거림. 예상한 남은 문제 |
| 26 | 증상 LLM이 `pain`을 빠뜨림(회차마다 다름) | 키워드 `pain`이 남아 일치 | 합집합으로 해결 |
| 40·44 | workRelated LLM 추측 `yes` | `null` | 키워드 값만 쓴다 |
| 52 | workType LLM 추측 `painting`, 증상에서 `chemical`을 빠뜨림 | 증상은 키워드 `chemical`이 남아 일치. workType `painting`은 **1회에만 남음** | 시너 냄새로 도장을 추측. 예상한 남은 문제 |
| 28 | (03에서는 일치) | 증상에 LLM `pain`이 더해짐 | "목이 아프다"를 키워드가 통증으로 못 잡았다. **LLM이 맞다** |

LLM 대체(`source: "keywords"`)는 두 회차 모두 0건이었다.

결정 사항
- 합치기는 LLM이 성공했을 때만 한다. 실패·키 없음·빈 입력이면 지금처럼 키워드 결과만 쓴다
- `source`는 합친 결과도 `"llm"`이다. 값을 더하지 않았다(범위대로)
- 합치는 함수(`combine`)는 `rules/extract_llm.py`의 순수 함수로 두어 라우터에 규칙이 들어가지 않게 했다

남은 문제
- 18번(따끔거림 → `burn`), 52번(시너 → `painting`, 회차마다 다름). 합집합·LLM 우선 규칙에서 생기는 LLM 쪽 추가값이다. 고치려면 프롬프트를 바꾸거나 해당 필드 규칙을 바꿔야 해서 이번 범위 밖이다

## 메모
