# 10. 로그인 화면·사진 올리기·분석 중 화면

상태: 완료
의존: 08 (`.w-logo`와 바닥 쌓기, `useScreenBar`의 `hidden`, 자유 입력 화면의 카드 벗기기 위에서 한다), 09 (분석 중 화면은 마지막 질문의 `결과 보기` 뒤에 온다)

## 목표
`design.md` "지금 코드와 다른 점" 9~11번이다. Figma에 있지만 처음에는 "만들지 않는다"였던 셋 — 02 로그인, 19 사진 올리기, 20 분석 중 — 을 사용자가 만들기로 해서 문서가 바뀌었다(PR 66 커밋 94bc8ec). 서버에 인증·사진 API가 없으므로 셋 다 **브라우저 안에서만** 도는 모양이다: 로그인은 데모 버튼, 사진은 메모리, 분석 중은 서버 판정을 기다리는 동안의 화면이다.

## 범위
- 하는 것
  - **9. S-03 로그인 화면**(`Onboarding.tsx`): "회원/비회원 고르기" 대신 S-01과 같은 로고 골격(`.w-logo`: 위를 비우고 가운데 🏥 + 앱 이름 + 한 줄) → 바닥에 `Google 계정으로 로그인`(`.btn.secondary.block.big`, 왼쪽 `.mark` G) → `비회원으로 계속`(`ghost`) → 데모임을 알리는 각주 + 비자·이름을 묻지 않는다는 각주. 앱 바는 `로그인`, ← `/consent`. Google 버튼은 서버에 가지 않고 프로필 화면(단계 4, `간단 프로필`)으로 간다. 프로필을 저장하면 회원 모드(지금의 `signUp`). 순서는 언어 → 동의 → 로그인 → 프로필 → 홈. 비회원 버튼은 지금의 `startGuest`
  - **10. 사진 올리기**(`common.tsx`의 `PhotoPicker`, `.photos*`): S-05 자유 입력 묶음에서 h1·안내 아래, `textarea` 위. 제목 `사진` + `n/3` → `hr.divider` → 타일 한 줄(`+ 사진 추가` 들어간 홈 116px, 고른 사진은 썸네일 + ✕ 44px). 최대 3장(넘치는 파일은 버린다). `URL.createObjectURL`로 브라우저 메모리에만 두고 `Intake`·저장소·서버에 넣지 않는다. 화면을 떠나면 `usePhotoCleanup`이 URL을 해제한다. 타일 아래 각주로 보내거나 저장하지 않음을 알린다
  - **11. 분석 중 화면**(`Intake.tsx`, `.w-wait`): 마지막 질문의 `결과 보기`를 누르면 먼저 브라우저 규칙으로 응급을 보고(응급이면 바로 `/emergency`, 이 화면을 거치지 않는다), 아니면 `analyzing` 상태로 `.w-wait`(🔎 + `분석하고 있어요` + `잠시만 기다려 주세요`)를 보이며 `checkTriage`를 기다린다. 앱 바는 `useScreenBar({ hidden: true })`로 숨기고 바닥 버튼도 없다. 119 띠는 그대로. 서버가 실패하거나 대체되면 `checkTriage`가 브라우저 결과를 돌려주므로 지금처럼 `/result`로 간다. 단독 모드는 즉시 끝나 한 프레임만 보인다
  - `README.md` 화면 구성표의 S-01~S-04·S-05~S-07 줄과 진입 순서 문장을 고친다. `design.md` 컴포넌트 표에 `.w-logo`·`.w-wait`·`PhotoPicker`·`.btn .mark`를 더한다
  - 새 문구 키: `loginTitle`, `profileTitle`, `loginGoogle`, `loginGuest`, `loginDemoNote`, `photosTitle`, `photoAdd`, `photoRemove`, `photosNote`, `analyzingTitle`, `analyzingSub`. 지운 키: `signupTitle`, `guestBtn`, `guestHint`, `memberBtn`, `memberHint`, `consentAgree`, `newIntake`
- 하지 않는 것
  - 실제 OAuth, 서버 세션, Google 로고 이미지·외부 아이콘(글자 G 원으로 대신한다)
  - 사진을 `Intake`에 넣거나 `/api/extract`·`/api/triage`·리포트·센터 요청에 보내기. 백엔드 변경 없음. 사진 압축·회전·미리보기 확대
  - 스피너·진행 막대·애니메이션. 분석 중 화면은 멈춘 그림 하나다
  - 추출(`/api/extract`)을 기다릴 때의 분석 중 화면. 그때는 지금처럼 버튼만 `disabled`다(`design.md` "로딩과 실패를 그리는 법"의 예외는 결과 보기 하나)

## 화면·파일
- 화면: S-03 `/signup`(로그인 → 프로필), S-05 `/intake`(사진, 분석 중). 경로·API 변경 없음
- 수정: `src/pages/worker/Onboarding.tsx`, `src/pages/worker/Intake.tsx`, `src/components/common.tsx`, `src/components/WorkerLayout.tsx`(`hidden`), `src/styles.css`, `src/i18n/{en,vi,ko}.ts`, `README.md`, `design.md`

## 완료 기준
- [x] `npm run build` 통과, 06의 정적 검사가 비어 있다
- [x] 360px en·vi·ko에서 `/signup`이 로고 + Google(데모) + 비회원 버튼이고 가로 스크롤이 없다. Google → 프로필(단계 4), 저장 → `/home`(회원). 비회원 → `/home`(비회원). 프로필에서 ← → 로그인 화면, 로그인에서 ← → `/consent`
- [x] `/intake` 자유 입력 묶음에 사진 타일이 있고, 네 장을 고르면 세 장만 남고 추가 타일이 사라진다. ✕로 지우면 추가 타일이 돌아온다. 사진이 있어도 바닥 버튼과 119 띠가 보이고 가로 스크롤이 없다
- [x] 사진을 고른 뒤 `/result`까지 가도 `sessionStorage`의 `umn.session`에 사진 데이터가 없다(`Intake`에 사진 필드가 없다)
- [x] API 모드(`VITE_API_BASE=/api`)에서 `/api/triage`가 느리면(2.5초 지연 후 500) `결과 보기` 뒤에 앱 바·바닥 버튼 없이 🔎 + 제목 + 부제 + 119 띠만 보이고, 응답(실패) 뒤 `/result`로 간다. 응급 증상은 분석 중 화면 없이 `/emergency`
- [x] `README.md` 화면 구성표 S-03·S-05 줄이 새 흐름과 같다

## 결과

2026-10-29. 08·09와 같은 브랜치·PR. 검사 방법은 08의 `## 결과`와 같다. 스크린샷 `login`, `profile`, `intake-text`, `intake-photos`(en·vi·ko), `vi-analyzing`.

| 점검 | 결과 |
|---|---|
| 로그인 화면 | 로고 + 이름 + 한 줄, 바닥에 G 버튼(60px) + 비회원 ghost + 각주 둘. 앱 바 `로그인`/`Đăng nhập`/`Sign in` + ←. Google → 프로필(숫자 원 4 켜짐, 카드 없음, 성별 선택지 목록) |
| 프로필 | 생년월일·성별 전 `저장하고 계속` `disabled`, 채우면 활성 → `/home`(앱 바에 앱 이름, ← 없음) |
| 사진 | 2×2 png 네 장 → `.photo` 3개, `.photo-add` 0개. ✕ 하나 → 2개 + 추가 타일. 개수 `2/3`. 바닥 버튼·119 띠 그대로 |
| 사진 저장 안 함 | `Intake` 타입에 사진 필드가 없어 `umn.session`에 들어갈 길이 없다(타입 검사) |
| 분석 중 | API 모드 서버(5198)에서 `/api/*`를 가로채 `/api/triage`만 2.5초 지연 → `.w-wait` 보임, `.w-header`·`.w-footer` 없음, `.bar-119` 있음(`vi-analyzing.png`). 500 응답 뒤 `/result`, 앱 바 ← 복귀 |
| 응급 | 가슴 + 호흡 곤란 → 증상 묶음에서 `/emergency`(분석 중 화면 없음) |

정한 것
- Google 버튼은 `signUp`을 바로 부르지 않고 프로필 화면으로만 간다. 회원 모드는 프로필 저장 때 켜진다(지금 `AppState`의 `signUp` 그대로). 프로필 없이 회원이 되는 길을 만들지 않기 위해서다
- 사진 `input[type=file]`은 `multiple`이고 타일 전체를 덮는 투명 입력이다(`label` 안). 포커스 윤곽은 `.photo-add:focus-within`에 그린다
- 분석 중 화면에서 `checkTriage`가 예외를 던지면 `analyzing`을 풀고 다시 던진다(지금 `checkTriage`는 안에서 잡아 브라우저 결과를 돌려주므로 실제로는 오지 않는 길)

## 메모
- 기준 문서: PR conceptamin/for-nav#66의 커밋 94bc8ec("로그인·사진 올리기·분석 중 화면을 만들기로 하고 design.md 화면 골격 절을 고친다")
- 새 문구 11개의 베트남어는 원어민 검수가 필요하다
- 사진을 서버로 보내려면 `backend`에 올리기 API와 보관 정책이 먼저 필요하다. 그때 `Intake`에 사진 필드를 더할지 별도 항목으로
- S-01 로고는 아직 🏥 이모지다. 워드마크 자산이 생기면 `.w-logo .mark`만 바꾼다
