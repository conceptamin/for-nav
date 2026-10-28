# 05. 응급도 모델 입력(나이대·성별·손상 여부·통증 점수)을 증상 입력에서 받기

상태: 완료
의존: 없음(backend 10이 같은 필드를 선택으로 받는다. 병합 전이어도 프론트는 답한 값만 보내므로 지금 서버와도 맞다)

## 목표
응급도 모델은 부위·증상만으로 재현율 95%를 맞추면 60%를 응급으로 본다(modeling backlog 10). 나이대·성별·손상 여부·통증 점수를 받으면 훨씬 정확하다. 백엔드 `Intake`가 이 값을 선택 필드로 받게 됐으므로(backend 10), 근로자가 증상 입력 4단계에서 버튼으로 답할 수 있게 한다.

## 범위
- 하는 것
  - `src/domain/vocab.ts`: `AGE_GROUPS`(`under30`/`30to44`/`45to64`/`65plus`), `SEXES`(`female`/`male`) `Term` 표와 타입, `Mental`(`alert`/`verbal`/`pain`/`unresponsive`) 타입. 값과 순서는 `backend/app/vocab.py`의 `AgeGroup`·`Sex`·`Mental`과 같다
  - `src/domain/triage.ts`: `Intake`에 `ageGroup?`, `sex?`, `injury?`, `painScore?`(0–10 정수), `mental?` 선택 필드. 답하지 않으면 키가 없다
  - `src/pages/worker/Intake.tsx`(S-05 4단계): 통증 점수(`select.input`, 0~10), 손상 여부(`YesNoSeg`, 예/아니요), 나이대·성별(`SingleSelect`)
  - `src/i18n/`: `painQ`, `painNone`, `painWorst`, `injuryQ`, `ageGroupQ`(en·vi·ko). 성별 레이블은 기존 `sex` 키를 쓴다
- 하지 않는 것
  - 규칙(`triage()`)이 새 필드를 쓰게 바꾸기. 모델 입력일 뿐이다
  - 의식 상태(`mental`) 질문. 앱을 쓰는 사람은 깨어 있으므로 묻지 않는다. 타입만 둔다
  - 회원 프로필(`Profile.birthDate`·`sex`)로 미리 채우기

## 화면·파일
- 화면: S-05 `/intake` 4단계("몇 가지만 더 물어볼게요")에 질문 4개
- 수정: `src/domain/vocab.ts`, `src/domain/triage.ts`, `src/pages/worker/Intake.tsx`, `src/i18n/{en,vi,ko}.ts`
- 새 문구 키: `painQ`, `painNone`, `painWorst`, `injuryQ`, `ageGroupQ`

## 완료 기준
- [x] `npm run build` 통과
- [x] 새 질문에 답하지 않으면 저장된 `Intake`에 `ageGroup`·`sex`·`injury`·`painScore`·`mental` 키가 없다(en·vi·ko)
- [x] 답하면 `ageGroup: "30to44"`, `sex: "female"`, `injury: true`, `painScore: 7`처럼 백엔드 값 그대로 들어간다(en·vi·ko)
- [x] `parity.json`을 다시 만들어도 `generatedAt` 외에 바뀌지 않고, `backend`에서 `uv run pytest` 통과
- [x] 360px에서 가로 넘침 없음(en·vi·ko)

## 결과
- 실행(2026-10-28)
  - `npm run build` → 통과
  - `npx rolldown scripts/dump-fixtures.ts …`로 `parity.json` 재생성 → `generatedAt` 한 줄만 달라 되돌림(출력 동일)
  - `cd backend && uv run pytest` → `1008 passed`
  - 헤드리스 Chromium(360×800, 단독 모드)으로 `/intake`를 손(Hand)·부기(Swelling)로 끝까지 진행해 세션 저장소의 `intake`를 확인. en·vi·ko 모두 답하지 않으면 새 키 없음, 답하면 `{ageGroup: "30to44", sex: "female", injury: true, painScore: 7}`, `/result`로 이동, 가로 넘침 없음
- 결정 사항
  - 통증 점수는 선택지가 11개라 `design.md`("선택지가 5개를 넘으면 `select`")대로 `select.input`을 쓴다. 0과 10에만 "안 아픔"·"참을 수 없이 아픔"을 붙인다. 처음 값은 비활성 `—`라 고르기 전에는 키가 없다
  - 손상 여부는 예/아니요만 둔다. "모름"은 답하지 않은 것과 같다(서버·모델이 키가 없을 때 최악 조합을 본다)
  - 칩은 다른 질문처럼 다시 눌러도 해제되지 않는다. 한 번 답한 값을 비우는 동작은 없다
- 남은 문제
  - backend 10(conceptamin/for-nav#52)이 병합되기 전 서버는 이 키를 모른다. 단독 모드는 영향 없음

## 메모
- 베트남어 문구(`painQ`, `painNone`, `painWorst`, `injuryQ`, `ageGroupQ`, `AGE_GROUPS`·`SEXES`의 `vi`)와 발음 표기(`roman`, `viPron`)는 원어민 검수가 필요하다
- 열거값을 더한 것(바꾼 것 아님)이다. 순서가 모델 피처 값이므로 `backend/app/vocab.py`, `modeling/src/fornav_modeling/features/buttons.py`와 함께 바꿔야 한다
- 의식 상태를 센터·연계 입력에서 받을지는 정하지 않았다
