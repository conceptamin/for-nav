# 52. 보험과 지원(S-08) 선택을 홈으로 나오면 지운다

상태: 완료
의존: 없음

## 목표
S-08 `/coverage`에서 답을 고르고 홈으로 나갔다가 다시 들어오면 앞서 고른 답과 결과가 그대로 남아 있다. 홈(S-04)으로 나오면 제도 경로 상태를 지워, 다시 들어갈 때 처음부터 고르게 한다(2026-10-31 사용자 요청).

## 범위
- 하는 것
  - S-04 `/home`에 들어올 때 세션의 `coverage`(입력·결과)를 비운다
- 하지 않는 것
  - 업무 관련 질문의 접수 입력(`intake.workRelated`) 미리 채움. 증상 입력에서 받은 답이라 그대로 둔다
  - 다른 세션 상태(접수 입력·판정·동의) 초기화

## 화면·파일
- 화면: S-04 `/home`, S-08 `/coverage`. 경로·API·문구 키 변경 없음
- 수정: `src/pages/worker/Onboarding.tsx`(`HomePage`)

## 완료 기준
- [x] `npm run build` 통과
- [x] `/coverage`에서 세 질문에 답해 결과가 보인 뒤 ← 로 홈에 나왔다가 다시 `/coverage`에 들어가면 보험·울산 질문이 비어 있고 결과 상자가 없다
- [x] `/coverage` → 결과의 센터 요청 버튼 → `/center-request`에서는 제도 경로 결과가 그대로 붙는다(홈을 거치지 않으므로)
- [x] `cd app-front && npm run build` 통과(공유 import)

## 결과
- `cd frontend && npm run build` → 통과(청크 크기 경고만, 기존과 같음)
- `cd app-front && npm run build` → 통과
- 브라우저(375px, ko, 단독 모드 `vite preview`): `/home` → 보험과 지원 → 일하다가 생겼나요 "예"·건강보험증 "예" → 결과 상자가 뜨고 세션 `coverage`에 저장됨 → ← 로 `/home` → 세션 `coverage`가 `null` → 다시 보험과 지원 → 눌린 답 없음, 결과 상자 없음
- 같은 답으로 결과의 "이 내용으로 센터에 문의" → `/center-request?type=policy`에서 세션 `coverage.result.path`가 `industrial`로 남아 있음
- 결정: 지우는 자리를 S-08이 아니라 S-04 홈에 둔다. S-08에서 S-12로 바로 넘어갈 때는 결과를 들고 가야 하기 때문이다
- 배치·문구를 바꾸지 않아 en·vi·ar 등 다른 언어 화면은 따로 보지 않았다

## 메모
- 홈을 거친 뒤에는 플로팅 센터 채팅 시트(`CenterSheet`)의 요청에도 제도 경로 결과가 붙지 않는다. 홈으로 나오면 리셋한다는 요청의 결과로 받아들인다
