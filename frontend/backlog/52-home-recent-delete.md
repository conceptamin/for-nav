# 52. 홈 최근 메모 카드에서 메모 지우기

상태: 완료
의존: 없음

## 목표
홈 `최근 메모` 카드에 뜬 메모를 지울 방법이 없다. 지금은 `/my`의 `내 데이터 지우기`로 계정 데이터를 통째로 지우는 길뿐이다. 카드에 삭제 버튼을 두어 그 메모 하나를 지울 수 있게 한다(2026-10-31 사용자 요청).

## 결정 (2026-10-31 사용자)
1. 삭제는 홈에서 숨기는 것이 아니라 **메모 자체를 지운다**. 이 계정의 기기 저장소(`memberReports`)에서 빠지므로 `/my` 내 메모 목록과 `/report/:id`에서도 사라진다
2. 지운 뒤 다른 메모가 남아 있으면 그다음 최근 메모가 카드에 뜨고, 없으면 `최근 메모` h2와 카드가 함께 없어진다(backlog 23과 같다)

## 범위
- 하는 것
  - `AppState`에 리포트 하나를 지우는 `deleteReport(id)`를 더한다
  - 홈 최근 메모 카드를 링크 하나에서 "링크 + 삭제 버튼"으로 나눈다(버튼을 링크 안에 넣을 수 없다). 카드 본문을 누르면 지금처럼 `/report/:id`로 간다
  - 삭제 버튼은 카드 안 아래 끝 쪽의 평평한 버튼 `🗑️ 이 메모 삭제`(en `Delete this report`)이고, 누르면 `window.confirm`으로 한 번 묻는다(프로필 지우기·내 데이터 지우기와 같은 방식. 모달을 새로 만들지 않는다)
  - 새 문구 키 `reportDelete`, `reportDeleteConfirm`을 20개 언어에 넣는다
  - `design.md` "홈" 표 4번 줄을 새 모양으로 고친다
- 하지 않는 것
  - `/my` 내 메모 목록·`/report/:id` 화면의 삭제 버튼
  - 지운 메모 되살리기(실행 취소). 토스트를 만들지 않는다
  - 센터로 이미 보낸 요청(`myCaseIds`)은 건드리지 않는다

## 화면·파일
- 화면: S-04 `/home`. 경로·API 변경 없음
- 수정: `src/state/AppState.tsx`(`deleteReport`), `src/pages/worker/Onboarding.tsx`(`HomePage`), `src/styles.css`(`.home-recent`), `src/i18n/*.ts` 20개(`reportDelete`, `reportDeleteConfirm`), `design.md`("홈")
- `Onboarding.tsx`·`AppState`·`styles.css`는 app-front가 공유하므로 `cd app-front && npm run build`도 돌린다

## 완료 기준
- [x] `npm run build` 통과, `cd app-front && npm run build` 통과
- [x] 메모가 둘 있을 때 홈 카드의 삭제 버튼을 누르고 확인하면 첫 메모가 사라지고 둘째 메모가 카드에 뜬다. `/my` 내 메모 목록도 하나 줄어든다
- [x] 확인 창에서 취소하면 아무것도 지워지지 않는다
- [x] 마지막 메모를 지우면 `최근 메모` h2와 카드가 없어진다
- [x] 카드 본문(증상·부위·날짜)을 누르면 지금처럼 `/report/:id`로 간다. 삭제 버튼을 눌러도 리포트로 가지 않는다
- [x] 360px에서 en·vi·ko, 배치 변경이라 ar(RTL)·my·ru도 넘침·겹침이 없다. 삭제 버튼 높이 44px 이상

## 결과
- `npm run build` → 통과(청크 크기 경고만), `cd app-front && npm run build` → 통과
- 단독 모드(`npm run dev -- --port 5195`), 데모 계정 저장소에 메모 두 개를 넣고 360px `/home`에서 확인
  - 확인 창에서 취소 → 저장소 메모 두 개 그대로, 카드도 그대로
  - 확인 → 첫 메모가 저장소(`/my` 내 메모 목록의 출처)에서 빠지고 카드가 둘째 메모(`/report/r1`)로 바뀐다
  - 마지막 메모를 지우면 `최근 메모` h2와 카드가 없어진다
  - 카드 본문을 누르면 `/report/:id`로 간다. 삭제 버튼은 화면을 옮기지 않는다
- 360px en·vi·ko·ar·my·ru: 가로 넘침 없음, 삭제 버튼 높이 44px, 카드 안 끝 쪽(ar은 왼쪽). 가장 긴 my도 한 줄
- 결정: 카드 `a.card.home-recent`를 `div.card.home-recent`(안쪽 여백 0) 안의 본문 링크(안쪽 여백 16·16·4px) + `.btn.ghost` 버튼으로 나눴다. 누르면 들어가는 면은 본문 링크만이다. 버튼 색은 다른 `.btn.ghost`와 같은 `--brand-fg`다
- 문구: ko는 화면 이름에 맞춰 `이 메모 삭제`, 다른 언어는 `homeRecent`가 쓰는 "리포트" 낱말에 맞췄다

## 메모
- 새 문구는 en·vi를 포함해 원어민 검수가 필요하다. en·vi를 뺀 17개 언어는 기계 번역 초안이다(backlog 16)
