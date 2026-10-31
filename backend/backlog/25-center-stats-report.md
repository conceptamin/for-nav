# 25. 센터 통계에 월별·분야별·국적별 집계를 더하고 언어를 20개로 세기

상태: 대기
의존: 24(분야), frontend 42(`nationality`, `StatRecord`의 날짜 분포·언어 가중치·분야·국적, `CenterStats` 모양)

## 목표
센터 회신(2026-10-31)은 의료 상담을 월별·분야별·국적별로 보고한다. 프론트 C-03이 그 형식으로 바뀌었으므로(frontend 42) `GET /api/center/stats`가 같은 집계를 돌려준다. 함께 고치는 것: 지금 서버는 언어별 집계를 `["vi", "en"]` 두 값만 세어 다른 18개 언어 사례가 빠진다.

## 범위
- 하는 것
  - `app/schemas.py`: `CenterStats`에 `by_month: list[StatCell]`(`key`는 `YYYY-MM`, 최근 6개월, 오래된 달부터), `by_category`, `by_nationality`(`key`는 ISO 3166-1 alpha-2 또는 `unknown`, 많은 순). `CenterCase`·`POST /api/center/cases` 요청에 `nationality: str | None`(두 글자 대문자 또는 없음, 그 밖 422)
  - `app/routers/center.py` `stats`: 월별은 `days` 필터와 무관하게 서버 시각(Asia/Seoul) 기준 최근 6개월. `by_language`를 `LANGS` 전부로 센다. 5건 미만 칸은 지금처럼 `None`
  - `app/data/mock.py`: 통계 원천 420건을 프론트 `data/mock.ts`와 같은 모양으로 — 같은 난수값으로 날짜를 센터 회신 월별 비율(16·25·41·85·97·65)로 옮기고, 언어는 `STAT_LANG_W`, `category`·`nationality`는 두 번째 시드(`rng(78)`)로 뒤에서 채운다. 첫 10개 난수값 비교 테스트는 그대로 통과해야 한다
  - `app/store.py`·`app/store_sqlite.py`: 사례에 `nationality` 추가. 통계 집계에 live 사례의 `category`·`nationality`도 들어간다(지금 live 사례가 집계에 들어가는 방식과 같게)
  - `tests/test_api.py`: 월별 키 형식과 개수, 분야·국적 칸, 5건 미만 마스킹, 언어 20개, `nationality` 검증
  - `README.md`: `GET /api/center/stats` 응답 예시, `POST /api/center/cases` 요청 예시
- 하지 않는 것
  - 센터 전체 상담 집계, 표 내보내기, 프론트 코드

## API·파일
- `GET /api/center/stats` 응답: `byMonth`, `byCategory`, `byNationality` 추가. `byLanguage`가 20개 언어
- `POST /api/center/cases` 요청과 `CenterCase` 응답: `nationality` 추가(없으면 `null`)
- 수정: `app/schemas.py`, `app/routers/center.py`, `app/data/mock.py`, `app/store.py`, `tests/test_api.py`, `README.md`

## 완료 기준
- [ ] `uv run ruff check . && uv run ruff format --check .` 통과
- [ ] frontend 42가 만든 `parity.json`으로 `uv run pytest` 통과. mock 난수 첫 10개 비교 테스트 그대로 통과
- [ ] `byMonth`가 6칸이고 가장 최근 달이 마지막이다. 서버 시각을 고정한 테스트에서 8~10월 칸이 다른 달보다 크다
- [ ] 러시아어 사례를 넣으면 `byLanguage`의 `ru` 칸에 센다
- [ ] `nationality: "kr"`(소문자), `"KOR"`, `"Korea"`는 422, `"KR"`과 없음은 200

## 결과

## 메모
- 월별 칸은 기간 필터를 따르지 않는다. 센터 보고가 월 단위라 기간을 30일로 좁혀도 추이는 보여야 한다(frontend 42 결정)
- 국적은 통계 집계와 사례 상세에만 쓰고, 목록 응답(`GET /api/center/cases`)에서는 빼는 것을 frontend 42 결정에 맞춘다. 결정 전까지는 `CenterCase`에 넣고 프론트가 목록에서 보이지 않는 것으로 둔다
- 센터 회신 수치(월별 16·25·41·85·97·65, 국적 12개국)는 frontend 42 메모에 있다
