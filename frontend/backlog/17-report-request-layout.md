# 17. S-11 항목 선택·S-12 센터 요청을 입력 화면 골격으로

상태: 완료
의존: 없음(08·15에서 만든 `.w-screen`·`.w-footer`·`useScreenBar` 위에서 한다)

## 목표
SEED 교체 전 `design.md` "화면 유형별 규칙"은 S-11 항목 선택(`/report/new`)과 S-12 센터 요청(`/center-request`)을 **입력** 화면으로 정했지만, "화면 골격(Figma 기준)" 절이 적어 둔 대로 둘은 "아직 카드 안에 있다". 질문과 고르는 것이 `.card` 안에 묶여 있고, 주 동작 버튼이 본문 끝에 있어 스크롤해야 보인다. S-02 동의·S-03 프로필과 같은 골격(앱 바 ← → h1 → 입력 도구 → 안내 → 바닥에 붙은 버튼 하나)으로 옮겨, 근로자가 어느 입력 화면에서도 "아래 버튼이 다음"이라는 것을 읽지 않고 알게 한다. 모양(클레이모피즘)과 동작(무엇을 보내는지)은 바꾸지 않는다.

## 범위
- 하는 것
  - **S-11 항목 선택** `ReportBuilderPage`
    - 뿌리를 `.w-screen`으로. `useScreenBar({ title: t('repTitle'), onBack: () => navigate('/result') })`(지금은 등록이 없어 ← 가 `/home`이다. 리포트 보기의 되돌아가기와 같이 결과로 간다)
    - h1 `repTitle` → `p.small.muted` `repChooseHint` → 항목 `.check` 목록(`.stack`, 카드 밖) → 복용약 입력란(`meds`를 골랐을 때) → `repNoProfile` 각주 → `hr.divider` → 동의 `.check` → `Worse119` → `.w-footer` 안 `repMakeBtn`(`btn block`)
    - 카드 안 h2 `repChoose`는 h1 아래 묶음 제목이 되므로 h2로 남긴다(칩 묶음의 h2 제목과 같은 자리)
    - `Worse119`를 더한다. 옛 `design.md`는 S-07~S-12 전부에 두라고 했는데 S-11 항목 선택에만 빠져 있다
    - 인라인 `style`(`gap: 8`, `marginTop: 12`, `marginBottom: 12`)을 지운다. 간격은 `.stack`·`.field`·`.w-footer`가 준다
  - **S-12 센터 요청(회원, 보내기 전)** `CenterRequestPage`
    - 뿌리를 `.w-screen`으로. `useScreenBar({ title: t('cenTitle') })`(← 는 지금처럼 `/home`)
    - h1 `cenTitle` → `p.muted` `cenIntro` → (`notice.info` `cenNoIntake`) → 요청 종류 `.field`(레이블 + `SingleSelect`) → 연락 방법 `.field` → 연락처 입력란 → 요약 미리보기 `.card.band`(그대로. 결과 카드 하나) → `hr.divider` → 동의 `.check` → (실패 문구) → `cenHoursNote` 각주 → `Worse119` → `.w-footer` 안 `📨 cenSend`(`btn block`)
    - 필드를 감싼 `.card`를 벗긴다. S-03 프로필처럼 레이블과 선택지가 바닥 위에 놓인다
    - **전송 실패:** 지금은 실패하면 보내기 버튼이 사라지고 그 자리에 `notice.danger.with-retry`(문구 + 다시 시도)가 나온다. 바닥 버튼은 사라지지 않아야 하고 바닥에 버튼을 둘 두지 않으므로, `README.md` "경로별 대체 정책"·"비동기 UX 규칙"(실패 문구 옆에 다시 시도 버튼)대로 동의 줄 아래에 `notice.danger.with-retry`(`role="alert"`, 문구 `sendFailed` + `retry` 버튼)를 두고, 바닥 `cenSend` 버튼도 그대로 남긴다. 다시 시도는 본문에 있으므로 바닥 버튼은 하나다
  - `design.md`: 고치지 않는다. 처음에는 "화면 골격(Figma 기준)"·컴포넌트 표의 관련 행을 고치려 했지만, 작업 중 main에 병합된 PR 76이 `design.md`를 SEED Design 문서로 바꾸면서 그 절이 없어졌다. 화면 골격 규칙은 이제 backlog 08·15 문서에만 있다
- 하지 않는 것
  - S-12를 질문 하나씩 화면으로 나누기(S-05처럼). 요청 종류·연락 방법은 S-03 프로필처럼 한 화면이다
  - S-12 비회원 안내 화면(프로필 만들기 카드), 전송 완료 화면, S-11 리포트 보기(`/report/:id`). 입력 화면이 아니다
  - 문구·보내는 값·미리보기 요청 조건 변경. 선택지 목록 높이·간격(`.options`)도 그대로다
  - 센터 화면의 `.notice.danger.with-retry`(C-01~C-03). 그대로 쓴다

## 화면·파일
- 화면: S-11 `/report/new`, S-12 `/center-request`(회원, 보내기 전)
- API: 바뀌지 않는다(`buildClinicianReport`, `useCenterSummary`, `sendCase`)
- 수정: `src/pages/worker/Report.tsx`, `src/pages/worker/CenterRequest.tsx`, `src/components/WorkerLayout.tsx`(`useScreenBar`의 ← 기본값, 결과의 결정 사항)
- `styles.css`: 고치지 않는 것을 목표로 한다. 기존 클래스(`.w-screen`, `.w-footer`, `.stack`, `.field`, `.check`, `hr.divider`, `.notice`)로 그린다
- 새 문구 키: 없음

## 완료 기준
- [x] `npm run build` 통과
- [x] `/report/new`·`/center-request`(회원)에서 주 동작 버튼이 스크롤과 무관하게 119 띠 바로 위에 보인다(360×640)
- [x] 두 화면에서 고르는 것(체크·선택지·입력란)이 `.card` 밖에 있고, `.card`는 S-12 미리보기 하나뿐이다
- [x] 바닥 버튼은 조건 전(항목 0개, 동의 전, 요청 종류 없음, 전송 중) `disabled`로 보이고 사라지지 않는다
- [x] `/report/new`의 ← 가 `/result`로, `/center-request`의 ← 가 `/home`으로 간다
- [x] 두 화면에 `Worse119`가 있다
- [x] API 모드에서 백엔드를 끄고 S-12 보내기 → 동의 줄 아래 실패 문구 + 다시 시도 버튼이 뜨고 입력값이 남으며, 다시 시도와 바닥 버튼 둘 다로 다시 보낼 수 있다
- [x] `VITE_API_BASE` 없이 S-11 만들기 → `/report/:id`, S-12 보내기 → 전송 완료 화면이 지금과 같이 동작
- [x] 360px ko·vi·ar(RTL)에서 가로 넘침 없음
- [x] 두 화면 `.tsx`에 인라인 `style`이 새로 생기지 않는다

## 결과
- 실행(2026-10-30, 브랜치 `frontend/report-request-layout`)
  - `npm run build` → 통과(500kB 넘는 묶음 경고는 전부터 있던 것)
  - 로컬 Playwright Chromium(360×640, 세션·기기 저장소에 회원·증상 입력·판정을 넣어 가드 통과)으로 확인했다
    - `/report/new`·`/center-request`를 ko·vi·ar로: 가로 넘침 없음, 바닥 버튼이 처음부터 119 띠 바로 위에 보임, 바닥 버튼 1개, `.card`는 S-12 미리보기(`card band`) 하나, `Worse119` 있음, 화면 코드의 인라인 `style` 없음
    - 동의 전·요청 종류 전에는 바닥 버튼이 `disabled`이고 사라지지 않음
    - ← : `/report/new` → `/result`, `/center-request` → `/home`, `/my` → `/home`
    - 단독 모드: S-11 만들기 → `/report/:id`, S-12 보내기 → 전송 완료 화면
    - API 모드(`VITE_API_BASE=/api`, 백엔드 꺼짐): S-12 보내기 → 동의 줄 바로 아래 `notice.danger.with-retry`(`role="alert"`), 요청 종류·동의가 그대로 남음. 다시 시도·바닥 버튼 모두 다시 눌러지고 다시 실패해도 문구는 하나
- 바뀐 화면: S-11 `/report/new`, S-12 `/center-request`(회원, 보내기 전). 경로는 그대로
- 결정 사항
  - **`useScreenBar`의 ← 기본값을 고쳤다.** 주석은 "onBack이 없으면 /home"이었지만, 훅이 항상 빈 감싸기 함수를 등록해서 `onBack` 없이 등록한 화면(S-13 `/my`)의 ← 가 아무 일도 하지 않았다. S-12도 같은 방식으로 등록하므로 완료 기준(← → `/home`)을 지키려면 고쳐야 했다. 감싸기 함수가 `onBack`이 없으면 `/home`으로 가게 했고, `/my`도 함께 고쳐졌다
  - S-11 항목 선택에서 `h2 repChoose`를 남겼다. h1(`repTitle`)은 화면 이름이고, 고르라는 질문은 h2가 말한다(칩 묶음의 h2 제목과 같은 자리)
  - 복용약 입력란을 항목 목록 `.stack` 안에 넣어 따로 간격 인라인 `style`을 두지 않았다
  - 바닥 버튼은 `btn block`(48px)이다. 지금까지 쓰던 `big`(60px)은 바닥 골격의 다른 화면(S-02·S-03·S-05)과 높이가 달라 뺐다
  - **S-12 전송 실패는 README대로 다시 시도 버튼을 남겼다.** 처음 문서안은 "바닥에 버튼을 둘 두지 않는다"에 맞춰 문구만 두고 바닥 버튼으로 다시 보내게 했지만, `README.md`가 센터 전송 실패에 "실패 문구 옆 다시 시도 버튼"을 정하고 있어 사용자 확인 뒤(2026-10-30) README를 따랐다. 다시 시도는 본문 안이라 바닥 버튼은 하나 그대로다
  - `design.md`는 고치지 않았다. PR 76이 문서를 SEED Design으로 바꿔 고치려던 절이 없어졌다(범위 참고)
- 남은 문제: 없음

## 메모
- SEED 교체 전 `design.md` "화면 골격(Figma 기준)" 첫 문단이 이 일을 "backlog에 별도 항목"으로 미뤄 두었다. 01~16 중에는 이 항목이 없어 새로 썼다
