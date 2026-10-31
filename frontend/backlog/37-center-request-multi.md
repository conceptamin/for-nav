# 37. 센터 상담 요청의 "무엇이 필요하세요?"를 여러 개 고르게 하기

상태: 완료
의존: 없음

## 목표
2026-10-31 사용자 요청: "지원센터 문의 부분에 '무엇이 필요하세요?' 다중 선택 가능하게 해줘." 근로자는 예약과 통역처럼 한 번에 여러 도움이 필요할 때가 많다. 지금은 하나만 고를 수 있어 나머지를 센터가 알 수 없다. S-12에서 요청 종류를 여러 개 고르고, 고른 것을 모두 센터로 보낸다.

## 범위
- 하는 것
  - S-12 `/center-request`의 요청 종류를 하나 고르기(`SingleSelect`)에서 여러 개 고르기(`Chip` + `toggleIn`, S-04 증상과 같은 방식)로 바꾼다. 하나 이상 골라야 보낼 수 있다
  - `domain/`의 `CenterSummaryInput.requestType: RequestType`과 `CenterCase.requestType`을 `requestTypes: RequestType[]`로 바꾼다(사용자 결정: 프론트 전체를 배열로)
  - 요약 문장의 요청 줄을 고른 순서대로 쉼표로 잇는다(`요청 유형: 예약 지원, 통번역.`)
  - 센터 화면 C-01 목록·C-02 상세의 요청 유형을 여러 개로 보인다
  - `data/mock.ts` 사례는 지금처럼 하나씩 뽑아 배열로 담는다(시드 순서가 바뀌지 않게). `parity.json`을 다시 만든다
  - `?type=` 주소 값은 쉼표로 여러 개를 담는다(`?type=booking,interpret`). 지금 있는 `?type=policy`·`?type=booking` 링크는 그대로 동작한다
  - 고르기 칸 아래에 "해당하는 것을 모두 고르세요" 안내(`cenTypeHint`, 20개 언어)를 둔다
  - 이 브라우저에 이미 저장된 옛 실제 전송 사례(`requestType` 하나)는 읽을 때 배열로 바꾼다
- 하지 않는 것
  - `backend/` 코드. 서버 `schemas.py`·`templates/reports.py`·`data/mock.py`·`routers/center.py`는 `backend/` 브랜치에서 따로 맞춘다(사용자 결정)
  - C-03 통계 원천(`StatRecord.requestType`). 집계에 쓰지 않는 익명 레코드라 그대로 둔다
  - 선택지 종류·선택지 문구 변경

## 화면·파일
- 화면: S-12 `/center-request`, C-01 `/center`, C-02 `/center/cases/:id`. 경로 변경 없음
- 파일: `src/pages/worker/CenterRequest.tsx`, `src/i18n/*.ts`(20개), `src/domain/templates.ts`, `src/domain/centerCase.ts`, `src/state/centerStore.ts`, `src/pages/center/Center.tsx`, `src/data/mock.ts`, `scripts/dump-fixtures.ts`, `backend/tests/fixtures/parity.json`(재생성)
- API: `POST /api/center/cases` 요청의 `requestType` → `requestTypes`(배열), `CenterCase` 응답도 같다. 새 문구 키 `cenTypeHint`

## 완료 기준
- [x] `npm run build` 통과, `cd app-front && npm run build` 통과
- [x] 단독 모드 360px `/center-request`에서 요청 종류를 둘 이상 골랐다 풀 수 있고, 하나도 안 고르면 보내기가 꺼진다
- [x] 고른 종류가 미리보기와 센터 `/center` 목록·상세에 모두 보인다
- [x] `/center-request?type=policy`로 들어오면 제도 상담이 골라져 있다
- [x] en·vi·ko에서 확인

## 결과
- `cd frontend && npm run build` → 통과, `cd app-front && npm run build` → 통과
- `parity.json` 재생성 → 바뀐 것은 센터 요약 입력의 `requestTypes`와 요약의 요청 줄, `generatedAt`뿐. 넷에 하나는 두 종류를 고르게 했다
- `cd backend && uv run pytest` → 이 PC에서는 실행하지 못했다(`pyyaml` 빌드에 Microsoft C++ Build Tools가 필요). 서버가 아직 `requestType` 하나라 parity 테스트는 실패할 것으로 본다(메모)
- 브라우저(단독 모드, 데모 로그인)
  - 360px `/center-request?type=policy` en: 제도 상담이 골라져 있다. 예약·통역을 더 고르면 주소가 `?type=policy,booking,interpret`, 미리보기가 `Request: Insurance & support advice, Booking support, Interpretation.`. 다시 누르면 풀린다. 모두 풀면 동의해도 보내기가 꺼지고 미리보기가 사라진다
  - 예약·통역 둘로 보냄 → 요약 `요청 유형: 예약 지원, 통번역.`
  - 1280px `/center` 목록과 `/center/cases/C-02739` 상세: `예약 지원, 통번역`. 옛 꼴(`requestType: 'referral'`)로 넣은 사례도 `기관 연계`로 보인다
  - 360px vi(`Yêu cầu: Hỗ trợ đặt lịch, Phiên dịch.`)·ko(`요청: 예약 지원, 통번역.`): 가로 넘침 없음
- 결정
  - 고르기는 S-04 증상과 같은 `Chip` + `toggleIn`으로 했다. 새 컴포넌트·클래스 없음
  - 안내 문구를 `stepBodyHint`에서 빌리지 않고 `cenTypeHint`를 새로 두었다. ko(`해당하는 곳을`)·vi(`chỗ`)가 "곳·자리"라 요청 종류에 맞지 않아 ko·vi만 "것·mục"으로 바꾸고, 나머지 18개 언어는 `stepBodyHint`와 같은 말이다
  - mock 사례는 하나씩만 뽑아 배열에 담았다. 여러 개를 뽑으면 시드 순서가 밀려 다른 mock 값이 모두 바뀐다

## 메모
- vi `cenTypeHint`(`Chọn tất cả mục phù hợp.`)는 원어민 검수가 필요하다. 나머지 17개 언어는 기존 기계 번역 초안 문장을 그대로 썼다(backlog 16)
- API 계약이 바뀐다(`requestType` → `requestTypes: RequestType[]`). 서버를 맞출 때까지 API 모드 전송과 `backend`의 `uv run pytest`(parity)는 실패한다. 서버 쪽 일: `schemas.py`의 `CenterSummaryInput`·`CenterCase`, `templates/reports.py`의 요약 요청 줄, `data/mock.py`(프론트와 같은 시드 순서), `routers/center.py`, `backend/README.md`의 `POST /api/center/cases` 요청 예시(`"requestType": "booking"`)
