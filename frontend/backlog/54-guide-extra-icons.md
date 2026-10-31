# 54. 병원 이용 방법 5·6번을 번호 대신 아이콘으로

상태: 완료
의존: 없음

## 목표
`/guide`(한국에서 병원 이용하기)의 1~4번은 병원에 가는 차례지만, 5번 `일하다가 생겼다면`과 6번 `밤이나 휴일에는`(backlog 44)은 차례가 아니라 덧붙이는 안내다. 번호가 있으면 5·6단계를 거쳐야 하는 것처럼 읽히므로, 5·6은 번호를 빼고 주제 아이콘을 붙인다(2026-10-31 사용자 요청).

## 결정 (2026-10-31 사용자)
1. 1~4번은 지금처럼 번호를 둔다
2. 5번은 🦺(일하다가 생긴 경우), 6번은 🌙(밤·휴일)를 제목 앞에 둔다

## 범위
- 하는 것
  - 20개 언어의 `guide5t`·`guide6t`에서 `5. `·`6. ` 번호를 뺀다
  - `GuidePage` 항목 표에 5·6의 아이콘을 더하고 제목 앞에 그린다. 아이콘은 문구가 아니므로 다른 화면의 `🗑️ {t(...)}`처럼 코드에 둔다
  - `README.md` 화면 표의 `/guide` 설명을 고친다
- 하지 않는 것
  - 카드 모양·순서·본문 문구, 1~4번 제목
  - 새 클래스·`styles.css`·`design.md` 변경(제목 글자 앞 이모지 하나라 기존 `.card h2` 그대로)

## 화면·파일
- 화면: `/guide`. 경로·API 변경 없음
- 수정: `src/pages/worker/CenterRequest.tsx`(`GuidePage`), `src/i18n/*.ts` 20개(`guide5t`, `guide6t` 값), `README.md`
- 새 문구 키: 없음
- `pages/worker/*`는 app-front가 공유하므로 `cd app-front && npm run build`도 돌린다

## 완료 기준
- [x] `npm run build` 통과, `cd app-front && npm run build` 통과
- [x] 360px `/guide` en·vi·ko에서 1~4번은 번호, 5번은 `🦺`, 6번은 `🌙`로 시작하고 `5.`·`6.`이 보이지 않는다
- [x] ar(RTL)에서 아이콘이 제목의 시작 쪽(오른쪽)에 붙고, 가로 넘침이 없다

## 결과
- `npm run build` → 통과. `cd app-front && npm run build` → 통과
- 단독 모드 360×800 `/guide`(데모 계정 + 프로필)
  - ko: `1. 알맞은 곳 고르기 / 2. 접수 / 3. 진료 / 4. 수납과 약 받기 / 🦺 일하다가 생겼다면 / 🌙 밤이나 휴일에는`, 가로 넘침 0
  - en: `… / 4. Pay and get medicine / 🦺 If it happened at work / 🌙 At night or on a holiday`, 가로 넘침 없음
  - vi: `… / 4. Thanh toán và lấy thuốc / 🦺 Nếu xảy ra khi làm việc / 🌙 Vào ban đêm hoặc ngày nghỉ`, 가로 넘침 없음
  - ar(`dir=rtl`): 🦺·🌙가 제목 오른쪽 끝(x 303~328, h2 끝 328)에 붙고 글자는 그 왼쪽으로 이어진다. 가로 넘침 0
- 결정: 아이콘은 문구 키에 넣지 않고 `GuidePage` 항목 표의 셋째 값으로 둔다. 20개 언어가 같은 아이콘을 쓰고, 다른 화면도 이모지를 코드에서 문구 앞에 붙인다(`🗑️ {t('myDelete')}` 등)

## 메모
- 문구는 번호만 뺐고 뜻은 그대로라 원어민 검수 대상이 늘지 않는다
