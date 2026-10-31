# 51. 통계 mock 원천을 센터 회신 분포로 바꾸기

상태: 완료
의존: 없음(42의 "mock 통계 원천" 부분만 먼저 한다)

## 목표
2026-10-31 사용자 요청: 센터가 보낸 의료 상담실적 엑셀(동구 센터, 2026-05-04 ~ 10-27, 329건)로 목업데이터를 갈아끼운다. 저장소가 공개라 실제 행은 넣지 않고, 엑셀의 분포를 따른 시드 고정 합성값으로 C-03 통계 원천을 바꾼다(사용자 결정). 화면 칸 추가(월별·분야별·국적별)는 42에 남긴다(사용자 결정).

## 범위
- 하는 것
  - `data/mock.ts` 통계 원천: 420건 → 329건. 날짜는 최근 6개월에 월별 16·25·41·85·97·65 비율로(난수 하나로 달과 날을 함께 고른다, 달 경계는 Asia/Seoul), 구군은 `STAT_DISTRICT_W`(동구 196·북구 20·울주 17·남구 8, 구가 적힌 건만), 언어는 `STAT_LANG_W`(42 메모의 국적 비중: 러시아어 44·인도네시아어 25·싱할라어 15·영어 8·필리핀어 4·베트남어 2·한국어 2), 운영 시간 외는 52/329(시간외 25 + 주말 27)
  - 업종·보험·요청 종류·업무 관련은 엑셀에 없어 가중치를 그대로 둔다. 레코드당 뽑는 난수 수도 그대로다
  - mock 사례 24건은 바꾸지 않는다(자유 입력 문장이 vi·en뿐)
  - 언어별 집계를 20개 언어 전부로 센다(`centerStore`). C-03 언어 칸은 5건 이상인 언어만 많은 순으로 보인다(20줄이 대부분 `<5`가 되지 않게)
  - 서버를 같은 PR에서 맞춘다(사용자 결정): `backend/app/data/mock.py`, `/api/center/stats`의 `byLanguage`가 `LANGS` 전부, `tests/test_api.py`·`test_store.py` 건수
- 하지 않는 것
  - 실제 엑셀 행·상담 내용·성별·비자를 저장소에 넣기
  - 월별·분야별·국적별 칸, 프로필 국적(42)

## 화면·파일
- 화면: C-03 `/center/stats`
- 수정: `src/data/mock.ts`, `src/state/centerStore.ts`, `src/pages/center/Center.tsx`, `README.md`, `backend/tests/fixtures/parity.json`(재생성), `backend/app/data/mock.py`, `backend/app/routers/center.py`, `backend/tests/test_api.py`, `backend/tests/test_store.py`, `backend/README.md`
- API: `GET /api/center/stats`의 `byLanguage` 키가 `["vi","en"]` → 20개 언어(`LANGS` 순서). 다른 필드는 그대로

## 완료 기준
- [x] `npm run build` 통과
- [x] parity.json 재생성 후 `cd backend && uv run pytest` 통과, `ruff check`·`ruff format --check` 통과
- [x] 단독 모드 1280px·860px `/center/stats` 180일: 언어 칸이 러시아어가 가장 많고 5건 미만 언어는 줄이 없다

## 결과
- `npm run build` → 통과
- `npx rolldown scripts/dump-fixtures.ts ... && TZ=Asia/Seoul node ...` → `parity.json`의 `statRecords`만 바뀜(329건). 기준 시각 2026-10-26에서 월별 20·23·44·93·90·59, 구군 동구 274·북구 27·울주 18·남구 10, 언어 ru 150·id 85·si 43·en 29·tl 11·ko 6·vi 5, 운영 시간 외 55건
- `cd backend && uv run pytest` → 2986 passed. `ruff check`·`ruff format --check` 통과
- 브라우저(Playwright Chromium, 단독 모드) `/center/stats` 1280px·860px, 최근 180일: 요청 326건, 운영 시간 외 17%, 언어 칸 러시아어 150 → 베트남어 5 일곱 줄
- 결정: 국적 → 언어는 42 메모의 `STAT_LANG_W`를 그대로 쓴다. 구가 없는 "울산" 74건과 울산 밖 14건은 구군 가중치에서 뺀다. 날짜는 `now` 기준 최근 6개월이라 180일 필터에서 첫 달 앞 며칠이 빠질 수 있다(테스트는 300~329건으로 본다)

## 메모
- 원본 엑셀은 저장소에 넣지 않았다(상담 내용·국적·날짜 조합으로 재식별될 수 있다)
- 42를 할 때 `category`·`nationality`는 42 계획대로 두 번째 시드(`rng(78)`)로 뒤에서 채우면 이 항목의 값이 바뀌지 않는다
