# 08. Figma 화면 골격 적용

상태: 완료
의존: 07 (클레이모피즘과 색 정리가 끝난 `styles.css` 위에서 배치만 바꾼다). `design.md` "화면 골격(Figma 기준)" 절은 PR conceptamin/for-nav#66(`docs/figma-page-layouts`)이 더한다. 66을 이 브랜치에 병합해 그 문서 위에서 작업했고, 66이 먼저 병합된 뒤에 이 PR을 병합한다

## 목표
`design.md` "화면 골격(Figma 기준)" 절이 정한 **배치**(앱 바 ← + 화면 이름, 질문 h1, 바닥에 붙는 다음 버튼, 줄바꿈 칩 묶음, 숫자 원 단계, 가로 꽉 찬 선택지 목록, 전체 동의 줄)를 온보딩(S-02·S-03)과 증상 입력(S-05)에 옮긴다. 그 절 끝 "지금 코드와 다른 점" 열한 가지 중 1~5·7·8번이 이 항목이고, 6번은 09, 9~11번(로그인·사진·분석 중)은 10이 한다. 셋을 한 브랜치(`frontend/figma-layout`)에서 함께 구현했다. 모양(색·둥글기·그림자)은 바꾸지 않는다. 끝난 줄은 "지금 코드와 다른 점"에서 지운다.

## 범위
- 하는 것
  - **1. 앱 바에 ←와 화면 이름**(`WorkerLayout.tsx`, `.w-header`)
    - `/`와 `/home`은 지금처럼 앱 이름(홈 링크). 그 밖의 모든 근로자 경로는 왼쪽에 ← 버튼(`.w-header .back`, 아이콘 24px, 누르는 영역 48×48, 평평) + 화면 이름(`.w-header .title`, 한 줄 말줄임). 오른쪽 언어 선택과 Demo 배지는 그대로
    - 화면 이름과 ← 동작은 화면이 정한다. `WorkerLayout.tsx`가 `useScreenBar({ title, onBack })` 훅을 내보내고, 화면은 마운트 때 등록하고 언마운트 때 비운다. 등록하지 않은 화면은 이름 자리에 앱 이름, ←는 `/home`으로 간다(기본값)
    - 등록하는 화면: S-02(`consentTitle`, ← `/`), S-03 로그인(`loginTitle`, ← `/consent`), S-03 프로필(`profileTitle`, ← 로그인 화면으로), S-05(`intakeTitle`, ← 이전 질문·묶음, 첫 묶음에서는 `/home`)
    - 바닥의 되돌아가기를 지운다: S-05 `btn secondary` 되돌아가기, S-03 프로필의 `btn ghost` 되돌아가기, S-06의 `btn ghost` 홈, S-07의 `btn ghost` 새로 입력(← `/home` → 홈 메뉴 "아파요"로 다시 들어가면 새 입력이 시작된다)
  - **2. 입력 화면의 카드를 벗기고 질문을 h1으로**(`Intake.tsx`, `Onboarding.tsx`)
    - S-05: 화면 위 h1 `증상 입력`을 지우고(앱 바 이름이 된다) 단계마다 `.card` 안 h2였던 질문(`stepBody`·`stepSymptom`·`stepText`·`stepMore`)을 카드 밖 h1으로. 안내 문단·`notice`는 h1 아래 평평하게
    - S-02: 항목별 `.card` 세 개를 없앤다(아래 7번의 줄 목록으로)
    - S-03 로그인: 10이 로그인 화면으로 바꾼다(`.w-logo` + 바닥 버튼 둘)
    - S-03 프로필: `.card`를 벗기고 h1 → `.field`들. 입력란은 들어감이므로 바닥 위에서 바로 보인다
  - **3. 바닥에 붙는 주 동작 버튼**(`.w-footer`, `styles.css`·`WorkerLayout.tsx`)
    - `:root`에 크기 토큰 `--bar-119: 72px`(119 띠 높이 = 위아래 10px + 버튼 52px)를 더한다. `.w-main`의 아래 여백은 `calc(var(--bar-119) + 16px + env(safe-area-inset-bottom))`
    - `.w-footer`: `position: sticky; bottom: calc(var(--bar-119) + env(safe-area-inset-bottom)); margin-top: auto; padding: 16px 0; background: var(--bg)`. 안에 `.btn.block` 하나. 본문이 길면 119 띠 바로 위에 떠서 따라오고, 끝까지 내리면 같은 자리에서 멈춘다(여백이 같아 튀지 않는다)
    - 본문이 짧아도 버튼이 올라오지 않게 `.w-main`을 세로 flex로 두고, 바닥 버튼을 쓰는 화면은 뿌리를 `.w-screen`(`flex: 1; display: flex; flex-direction: column`)으로 감싼다. `.w-footer`의 `margin-top: auto`가 버튼을 바닥으로 민다
    - 쓰는 화면: S-02 `다음`(필수 셋 전 `disabled`), S-03 프로필 `저장하고 계속`(`disabled` 규칙 그대로), S-05 `다음`/`건너뛰기`/`결과 보기`(지금 라벨 규칙 그대로, `busy`면 `disabled`)
    - `.btn.big`(60px)은 바닥 버튼에 쓰지 않는다. 골격의 바닥 버튼은 48px이다
  - **4. 칩 묶음**(`.chips`, `.chip-group`, `Intake.tsx`)
    - `.chips`를 2열 격자에서 `display: flex; flex-wrap: wrap; gap: 8px`로. 칩은 내용 너비(`.chip`의 `display: inline-flex`), 긴 베트남어는 한 칩 안에서 줄바꿈한다
    - 묶음: `.chip-group`(h2 제목 + `.chips`), 묶음 사이 24px. S-05 부위는 `머리·얼굴`(head·eye·ent·teeth) / `몸통`(chest·abdomen·back) / `팔·다리`(arm·hand·leg·foot) / `그 밖에`(skin·whole), 증상은 `다침·통증`(pain·swelling·cut·bleeding·burn·numb·cantmove) / `몸 상태`(fever·cough·dizzy·rash·nausea·breath) / `노출·이물`(chemical·foreign). 묶음은 화면(`Intake.tsx`)의 표시 순서일 뿐이고 `domain/vocab.ts`의 열거값·순서는 바꾸지 않는다
    - 새 문구 키 7개: `groupHead`·`groupTrunk`·`groupLimbs`·`groupOther`·`groupInjury`·`groupIllness`·`groupExposure`(en·vi·ko)
    - `.chips`를 쓰는 다른 화면(S-11 항목 선택)은 격자가 줄바꿈으로 바뀌기만 한다. 묶음 제목은 더하지 않는다
  - **5. 단계 숫자 원**(`.steps`, `common.tsx`의 `Steps`)
    - `.steps`를 6px 트랙에서 숫자 원으로: `ol.steps > li` 32×32, 999px, 왼쪽부터 가로로 8px 간격, 아래 여백 16px. 현재 단계(`.on`)는 `--brand` 채움 + `--on-brand` 숫자 + `--clay-color-sm`, 지난·남은 단계는 `--card` 바탕 + `--clay-in` + `--ink-3` 숫자. 트랙 선은 없다
    - `Steps({ count, current })` 조각을 `common.tsx`에 더한다. `aria-hidden`이고 단계 수는 화면 이름 옆 글로도 알려 주지 않는다(지금과 같다. 장식이다)
    - S-05: 묶음 4개(부위·증상·자유 입력·추가 질문) 그대로. 온보딩: 1 언어 · 2 동의 · 3 로그인 · 4 프로필로 세어 S-02에 2, S-03 프로필에 4를 켠다. S-01과 S-03 로그인은 로고 화면이라 단계를 붙이지 않는다
  - **7. S-02 전체 동의 줄과 항목별 전문 펼치기**(`Onboarding.tsx`, `.check-row`)
    - h1 → 전체 동의 줄(`.check` 하나: 체크 + 굵은 `consentAll` + 아래 `consentIntro` 문단. 체크하면 셋 다 켜고, 끄면 셋 다 끈다. 셋이 다 켜지면 저절로 체크) → 구분선(`.line` 빈 줄 대신 `hr.divider`, `--line` 1px) → 항목 줄 셋
    - 항목 줄: `.check-row`(flex, 8px) 안에 `.check`(체크 + `[필수]` + 제목, 높이 48px) + 오른쪽 `btn ghost` › (48×48, `aria-expanded`, `aria-label`은 새 키 `consentReadFull`). 누르면 같은 화면 안에서 그 줄 아래에 전문(`consentXxxBody`)이 `p.small.muted`로 펼쳐진다. 모달·시트가 아니다
    - 지금의 `모두 동의` 보조 버튼과 항목 카드 안 `동의합니다` 체크 줄은 없앤다. `consentCenterLater` 각주와 `consentNeedAll` 안내는 그대로
    - 바닥 `다음`은 3번의 `.w-footer`
  - **8. 선택지 목록**(`.options`, `common.tsx`)
    - `SingleSelect`·`YesNoSeg`가 그리는 묶음을 `.seg`/`.chips`에서 `.options`로: 세로 한 열, 행 사이 16px, 행은 `.chip`에 `width: 100%; min-height: 56px`, 글자 왼쪽 정렬. 고른 행은 칩과 같은 ✓ + 들어감 + 굵게
    - S-03 성별(`Chip` 둘을 `.seg`로 직접 그린 곳)도 `SingleSelect`로 바꾼다
    - `.seg`는 S-09 접수 창구의 첫 방문/재방문 전환에만 남는다. 거기는 질문이 아니라 화면 전환이라 가운데 정렬 칩이 맞다
    - "둘뿐인 예/아니요는 바닥 버튼 위에 붙인다"는 화면 하나에 질문 하나일 때의 규칙이라 09에서 한다
  - **`design.md`**
    - 컴포넌트 표에 한 줄씩 더한다(면 열 포함): `.w-header .back`(평평), `.w-footer`(떠 있음 안의 버튼), `.w-screen`(—), `.chip-group`(평평 제목 + 떠 있는 칩), `Steps`(`.steps`, 들어감/현재는 떠 있음), `.options`(떠 있음 → 들어감), `.check-row`(평평 줄 안의 떠 있는 체크), `hr.divider`(평평)
    - `Chip` 줄의 "`.chips`로 2열 격자"를 "`.chips`로 줄바꿈, `.chip-group`으로 묶음"으로, `YesNoSeg`·`SingleSelect` 줄의 `.seg`를 `.options`로, `.steps` 줄을 숫자 원으로 고친다. 토큰 표에 `--bar-119`를 더한다
    - "지금 코드와 다른 점"에서 1·2·3·4·5·7·8번을 지운다. 6번은 09가 지운다
- 하지 않는 것
  - 6번(S-05 추가 질문을 질문 하나씩 화면으로 나누기, 예/아니요를 바닥 버튼 위에 붙이기, 통증 점수 슬라이더). 09가 한다. 이 항목에서 S-05 4단계 "추가 질문"은 카드만 벗기고 `field` 여덟 개가 한 화면에 그대로 있다
  - S-11 항목 선택·S-12 센터 요청의 카드 벗기기와 바닥 버튼. `design.md` "화면 유형별 규칙"은 입력 화면으로 분류하지만 이 항목은 온보딩·S-05까지다. 메모에 남긴다
  - 결과·응급 화면(S-06~S-10)의 배치. 1번의 되돌아가기 버튼 제거만 한다
  - 색·둥글기·그림자 토큰 추가·변경. 새 크기 토큰은 `--bar-119` 하나뿐이다
  - 모달·바닥 시트·토스트·애니메이션. 전문 펼치기는 같은 화면 안의 평평한 문단이다
  - `domain/`·`api/`·`state/` 변경, 경로 추가·변경, 백엔드 변경
  - S-01 언어 선택 화면의 로고 배치(아직 워드마크가 없다)

## 화면·파일
- 화면: S-02 `/consent`, S-03 `/signup`, S-05 `/intake`(배치), S-06 `/emergency`·S-07 `/result`(바닥 되돌아가기 제거). 경로·API·동작 변경 없음
- 수정: `src/styles.css`, `src/components/WorkerLayout.tsx`(`useScreenBar`), `src/components/common.tsx`(`Steps`, `SingleSelect`·`YesNoSeg`), `src/pages/worker/Intake.tsx`, `src/pages/worker/Onboarding.tsx`, `src/i18n/{en,vi,ko}.ts`, `design.md`
- 새 문구 키: `consentReadFull`, `groupHead`, `groupTrunk`, `groupLimbs`, `groupOther`, `groupInjury`, `groupIllness`, `groupExposure`

## 완료 기준
- [x] `npm run build` 통과
- [x] 06의 정적 검사가 그대로 비어 있다: `:root` 밖 16진수 색, `var(--clay*)` 아닌 `box-shadow`(띠 두 줄 제외), 토큰·999px·12px 아닌 `border-radius`, `border: 0` 아닌 `border`, `transition`·`transform: scale`·`text-shadow`·`backdrop-filter`
- [x] `grep -n 'style={{' src/pages/worker/Intake.tsx src/pages/worker/Onboarding.tsx`의 줄 수가 지금(`origin/main`)보다 늘지 않았다
- [x] 360px에서 `/consent`, `/signup`(로그인·프로필), `/intake`(묶음 4개)를 en·vi·ko로 스크린샷. 파일 이름을 `## 결과`에 적는다. 가로 스크롤이 없고, 어느 단계에서도 바닥 버튼과 119 띠가 같이 보인다
- [x] 360×640에서 `/intake` 1단계(부위 칩 13개)를 끝까지 내려도 바닥 `다음`이 119 띠 위에 그대로 있고, 2단계(증상 칩 15개)도 같다. 본문이 짧은 `/consent`에서도 `다음`이 본문 끝이 아니라 바닥에 있다
- [x] 앱 바: `/`·`/home`은 앱 이름, `/consent`·`/signup`·`/intake`는 ← + 화면 이름. `/intake` 2단계에서 ←를 누르면 1단계로, 1단계에서 누르면 `/home`으로. `/signup` 프로필에서 ←는 선택 화면으로. 베트남어 `Cho chúng tôi biết triệu chứng`이 ←·언어 선택과 한 줄에서 말줄임된다
- [x] `/consent`: 전체 동의를 체크하면 셋이 켜지고 `다음`이 활성, 하나를 끄면 전체 동의가 꺼지고 `다음`이 `disabled`. ›를 누르면 그 줄 아래에 전문이 펼쳐지고 다시 누르면 접힌다. 전문이 펼쳐진 채로도 가로 스크롤이 없다
- [x] `/intake` 1·2단계: 칩이 2열 격자가 아니라 내용 너비로 줄바꿈되고 묶음 제목 h2가 보인다. 베트남어 `Tiếp xúc hóa chất`처럼 긴 칩은 한 칩 안에서 줄바꿈되고 모서리 음영에 글자가 걸리지 않는다
- [x] 단계 숫자 원: `/consent` 2, `/signup` 프로필 4, `/intake` 1~4가 각각 브랜드색으로 켜지고 나머지는 들어간 홈 + 흐린 숫자
- [x] `/intake` 4단계와 `/signup` 프로필의 선택지(`SingleSelect`·`YesNoSeg`)가 가로 꽉 찬 세로 목록이고 고른 행에 ✓ + 들어감 + 굵게
- [x] `/emergency`·`/result`·`/intake`·`/signup` 프로필 바닥에 되돌아가기·홈·새로 입력 버튼이 없다
- [x] 1~4단계 입력 → `/result` 또는 `/emergency` 흐름이 `origin/main`과 같이 동작한다(단독 모드). 응급 칩(호흡 곤란)을 고르고 `다음`을 누르면 바로 `/emergency`
- [x] `Tab`으로 ← 버튼·칩·선택지·전문 보기 ›·바닥 버튼에 포커스 윤곽이 보인다
- [x] `design.md` 컴포넌트 표에 위 새 줄이 있고 "지금 코드와 다른 점" 절이 없다(09·10까지 끝나 절을 지웠다)

## 결과

2026-10-29. `frontend/figma-layout` 브랜치. 09·10과 같은 PR이다. 기준 문서는 PR 66의 최신 커밋(94bc8ec)을 이 브랜치에 병합한 `design.md`다.

정적 검사

| 검사 | 결과 |
|---|---|
| `npm run build` | 통과 |
| `:root` 밖 16진수 색 | 없음 |
| `var(--clay*)` 아닌 `box-shadow` | 실제 전송 행 띠 한 줄뿐 |
| 토큰·999px·12px 아닌 `border-radius` | 없음 |
| `border: 0` 아닌 `border` | 없음(`hr.divider`의 `border-top`은 구분선) |
| `transition`·`transform: scale`·`text-shadow`·`backdrop-filter` | 0 |
| 인라인 `style` 줄 수 | `Intake.tsx` 6 → 5, `Onboarding.tsx` 14 → 7 |

화면 확인: Playwright(Chromium, 360×640)로 en·vi·ko 세 언어를 돌리는 스크립트(스크래치 `pw/check.mjs`)가 220개 검사를 통과했다. 스크린샷은 스크래치 `shots/<언어>-<화면>.png`: `consent`, `consent-expanded`, `consent-all`, `login`, `profile`, `profile-bottom`, `intake-body`, `intake-body-bottom`, `intake-symptom`, `intake-text`, `intake-photos`, `intake-onset`, `intake-pain`, `intake-injury`, `intake-work`, `intake-worktype`, `intake-district`, `result`, `emergency`, 그리고 `vi-analyzing`.

| 점검 | 결과 |
|---|---|
| 가로 스크롤 | 세 언어 모든 화면·질문에서 `scrollWidth == clientWidth`(360) |
| 바닥 버튼과 119 띠 | 모든 입력 화면에서 버튼 아래 끝 552px, 띠 위 568px, 띠 아래 640px. 끝까지 내린 뒤에도 같은 자리(`intake-body-bottom`, `profile-bottom`) |
| 앱 바 | `/`·`/home`은 앱 이름만. `/consent`·`/signup`·`/intake`·`/result`·`/emergency`는 ← + 이름. 베트남어 `Cho chúng tôi biết triệu chứng`은 `Cho chúng t…`로 말줄임 |
| ← | `/intake` 2묶음 → 1묶음(고른 칩 유지), 1묶음 → `/home`. 프로필 → 로그인 화면, 로그인 → `/consent` |
| S-02 | 전체 동의 체크 → 셋 켜짐 + 다음 활성. 하나 끄면 전체 동의 꺼짐 + 다음 `disabled`. › → 줄 아래 전문 펼침·접힘, 펼친 채 가로 스크롤 없음 |
| 칩 | 부위 4묶음·증상 3묶음, 칩 너비가 내용마다 다르다(2열 격자 아님). 베트남어 `Tiếp xúc hóa chất`은 한 칩 안에서 줄바꿈 |
| 단계 숫자 원 | `/consent` 2, 프로필 4, `/intake` 묶음 1~4 |
| 선택지 목록 | 발생 시점 4행, 업무 관련 3행, 업무 종류 6행, 나이대 4행, 업종 5행, 구군 5행. 고른 행 ✓ + 들어감 + 굵게 |
| 바닥 되돌아가기 | `/intake`·`/signup`·`/emergency`·`/result`에 `btn ghost`·보조 되돌아가기 없음 |
| 흐름 | 손·부기 → 자유 입력 → 추가 질문 9개 → `/result`. 가슴·호흡 곤란 → 증상 묶음에서 바로 `/emergency` |
| 포커스 | `/intake`에서 첫 `Tab`이 ←에 닿고 `outline` 윤곽이 보인다 |

backlog에서 더 정한 것
- `.w-footer`는 `margin: 16px 0 -16px`로 `.w-main`의 아래 여백(`--bar-119` + 16px)과 맞춘다. 흐를 때나 붙어 있을 때나 버튼과 119 띠 사이가 16px이다
- `useScreenBar`는 `onBack`을 ref로 받아 매 렌더 바뀌어도 효과가 다시 돌지 않는다. `hidden`은 10의 분석 중 화면이 쓴다
- 앱 바 제목이 등록되지 않은 화면(S-06~S-13, 안내)은 앱 이름 + ← `/home`이다. 스크린샷 `result`·`emergency`가 그 모양이다
- S-07의 `↺ 새로 입력`을 지웠다. 홈 메뉴 "아파요"로 다시 들어가면 새 입력이다

남은 것
- 발표 기기 브라우저는 확인하지 않았다(Chromium만). `position: sticky`와 `env(safe-area-inset-bottom)`은 iOS Safari 11.2 이상
- 실제 손가락 눌림·키패드가 뜬 상태의 바닥 버튼 위치는 확인하지 않았다

## 메모
- 기준 문서: `design.md` "화면 골격(Figma 기준)"은 PR conceptamin/for-nav#66이 더했다. 이 문서는 그 절 끝 "지금 코드와 다른 점" 1~5·7·8번을 backlog 형식으로 옮긴 것이다. 6번은 `09-intake-one-question.md`
- 문서가 정하지 않아 여기서 정한 것(구현 전에 확인)
  - 화면 이름·← 동작을 화면이 등록하는 방식(`useScreenBar`). 경로 → 이름 표를 `WorkerLayout`에 두면 S-05처럼 단계 안에서 되돌아가는 화면을 못 다룬다. 등록하지 않은 화면은 앱 이름 + ← `/home`
  - S-07의 `↺ 새로 입력` ghost 버튼을 지운다. 홈 메뉴 "아파요"가 같은 일을 한다(`IntakePage`는 들어올 때마다 새 입력으로 시작)
  - 부위·증상 묶음은 화면의 표시 순서이고 `vocab.ts`는 그대로다. 묶음 이름 7개의 베트남어는 원어민 검수가 필요하다
  - 온보딩 단계 수는 4(언어·동의·이용 방식·프로필). 비회원은 3에서 끝나지만 원은 4개를 그린다(사진의 1·2·3·4)
  - S-03 선택 화면은 바닥 버튼이 없다. 비회원/회원 버튼 둘이 선택지이고 누르면 바로 넘어간다
  - `.w-footer`는 `sticky`라 `.w-main` 안에 있다. `.bar-119`는 `fixed`이고 둘의 높이를 `--bar-119` 토큰으로 맞춘다. 119 띠 높이를 바꾸면 토큰만 바꾼다
- 뒤로 미룬 것(별도 항목)
  - S-11 항목 선택(`/report/new`)·S-12 센터 요청(`/center-request`)의 카드 벗기기·바닥 버튼·`useScreenBar` 등록. `design.md`는 입력 화면으로 분류한다
  - 결과 화면(S-07~S-10)·리포트·내 리포트·안내의 앱 바 이름 등록. 지금은 앱 이름 + ← `/home`이고 화면의 h1은 그대로다
  - S-01 로고(워드마크) 배치. 그림 자산이 없다
