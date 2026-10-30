# 19. 글꼴·글자 크기·역할 색을 design.md(SEED)에 맞춤

상태: 완료(브라우저 확인은 PR 검토에서 한 번 더)
의존: 06(클레이모피즘), 18(틸 브랜드)

## 목표
`design.md`가 SEED Design 문서로 바뀌었지만(PR #76) `styles.css`는 그 전의 글꼴·글자 크기·글자색·상태색을 그대로 쓴다. 클레이모피즘(면·그림자·둥글기·바탕)과 틸 브랜드는 이미 문서와 같으므로 그대로 두고, 아직 어긋난 세 축(글꼴, 글자 크기 사다리, 글자·선·상태색)을 SEED 값으로 맞춘다.

## 결정(2026-10-30 사용자 확인: "SEED 나머지까지 맞춤")
1. **글꼴은 SEED 시스템 폰트 스택.** `design.md` frontmatter `typography`의 `fontFamily` 그대로다. 웹폰트를 들이지 않는다(지금의 `Pretendard`도 불러오지 않아 실제로는 시스템 글꼴로 떨어지고 있었다).
2. **글자 크기는 `t1`~`t14` 사다리 토큰.** `:root`에 `--t1`~`--t14`를 rem으로 둔다(사용자 글자 크기 설정을 따르도록 SEED의 rem 판을 쓴다. `--t5` = 1rem = 16px). 지금의 rem 값은 가장 가까운 단계로 옮긴다. 가운데에 걸리면 큰 쪽으로 간다.
3. **줄 높이는 지금 값(본문 1.5, 제목 1.3)을 둔다.** SEED의 줄 높이(t5 22px ≈ 1.375)는 한국어 기준이고, 이 앱은 미얀마어·태국어·아랍어처럼 위아래로 긴 글자를 쓰는 20개 언어를 보인다.
4. **두께는 SEED 3종(400·500·700).** 600은 500(흐린 라벨) 또는 700(값)으로, 800·900은 700으로 옮긴다.
5. **글자·선·상태색은 SEED 역할 값.** 대비는 `design.md`의 APCA로 잰다. 역할 값이 글자 기준(Lc 75)에 못 미치는 두 곳은 18번(`#12979A` → `#085e60`)처럼 같은 램프의 진한 단계를 쓴다.

## 색 토큰

| 토큰 | 지금 | SEED 역할 | 바꾼 값 | 대비(WCAG / APCA) |
|---|---|---|---|---|
| `--ink` | `#12232e` | `fg-neutral` gray-1000 | `#1a1c20` | `--card` 위 16.31 / Lc 100.8, `--bg` 위 14.43 / Lc 92.6 |
| `--ink-2` | `#4a5a66` | `fg-neutral-muted` gray-800 | `#555d6d` | `--card` 위 6.33 / Lc 79.6(지금 81.6), `--bg` 위 5.60 / Lc 71.4(지금 73.4) |
| `--ink-3` | `#74838e` | `fg-neutral-subtle` gray-700 | **없앤다 → `--ink-2`** | gray-700은 `--card` 위 Lc 58.6으로 지금(63.3)보다도 낮다. 쓰는 곳(각주, 남은 단계 숫자)이 "기관이 최종 결정" 문구를 담으므로 `--ink-2`로 합친다 |
| `--line` | `#d9e1e6` | `stroke-neutral-weak` gray-400 | `#dcdee3` | 선이라 대비 기준 밖 |
| `--danger` | `#c4231b` | `bg-critical-solid` red-700 `#fa342c` | **red-800 `#ca1d13`** | red-700은 흰 글자 3.76 / Lc 68.7이라 119 버튼에 못 쓴다. red-800은 흰 글자 5.68 / Lc 81.7(지금 82.6) |
| `--danger-2` | `#a11a13` | `fg-critical-contrast` red-900 | `#921708` | `--danger-bg` 위 8.05 / Lc 81.6(지금 72.1) |
| `--danger-bg` | `#fbe3e1` | `bg-critical-weak` red-100 | `#fdf0f0` | — |
| `--ok` | `#1f7a4d` | `bg-positive-solid` green-700 | `#079171` | 결과 카드 띠(그래픽) `--card` 위 3.79, 그래픽 기준 3:1 통과. 글자에는 쓰지 않는다 |
| `--ok-bg` | `#e2f3ea` | `bg-positive-weak` green-100 | `#edfaf6` | — |
| `--ok-ink` | `#134d31` | `fg-positive-contrast` green-900 | `#075445` | `--ok-bg` 위 8.30 / Lc 85.2 |
| `--warn` | `#9a5b00` | `fg-warning` yellow-700 | **없앤다 → `--warn-ink`** | yellow-700은 `--warn-bg` 위 3.84 / Lc 63.4. 쓰는 곳(칩·오프라인 띠)이 모두 옅은 노랑 위 글자다 |
| `--warn-bg` | `#fff1d6` | `bg-warning-weak` yellow-100 | `#fff7de` | — |
| `--warn-ink` | `#5c3700` | `fg-warning-contrast` yellow-900 | `#4f3e1f` | `--warn-bg` 위 9.61 / Lc 89.1 |
| `--info` | `#0b4f8a` | `fg-informative` blue-700 `#217cf9` | **`fg-informative-contrast` blue-900 `#0b4596`** | blue-700은 `--info-bg` 위 Lc 60.4. 쓰는 곳이 신규 칩 글자 하나라 contrast 단계를 쓴다. 8.37 / Lc 84.5 |
| `--info-bg` | `#dceeff` | `bg-informative-weak` blue-100 | `#eff6ff` | — |

`pill.done`은 글자를 `--ok` → `--ok-ink`로, `pill.medium`·`pill.progress`·`.c-offline`은 `--warn` → `--warn-ink`로 바꾼다(옅은 바탕 위 글자는 `*-contrast` 단계).

## 범위
- 하는 것
  - `src/styles.css` `:root`: 글꼴 스택, `--t1`~`--t14`, 위 색 토큰
  - `src/styles.css`: 모든 `font-size`를 `var(--tN)`으로, `font-weight` 600·800·900을 SEED 3종으로, 표 칸 여백 11px → 12px(`x3`, 사다리 밖 값 하나)
  - `design.md`: `## Colors`에 "이 프로젝트의 역할 색" 대응 상자, `## Typography`에 "이 프로젝트의 글자" 상자
- 하지 않는 것
  - 클레이모피즘 토큰(`--bg`·`--card`·`--bg-2`·`--bg-3`·`--clay*`·`--radius*`), 틸 브랜드 토큰
  - `--accent`(포커스 윤곽·실제 전송 띠), `--live-bg`, `--chart-*` — 포커스 윤곽 대비는 18번 `## 메모`대로 따로 한다
  - 화면 배치, 컴포넌트 구조, i18n 문구
  - SEED의 `rounded.full` 버튼, elevation `s1`~`s3`, 모션(클레이모피즘이 정한 예외)

## 화면·파일
- 화면: 모든 근로자·센터 화면의 글꼴·글자 크기·글자색, 응급 화면(S-07 `/emergency`)과 하단 119 띠의 빨강, 센터 긴급도·상태 칩
- 추가: `backlog/19-seed-type-color.md`
- 수정: `src/styles.css`, `design.md`
- 부르는 API·새 문구 키: 없음

## 완료 기준
- [x] `npm run build` 통과
- [x] `grep -nE 'font-size: [0-9.]+(rem|px)' src/styles.css`가 `:root` 밖에서 아무것도 내지 않는다
- [x] `grep -nE 'font-weight: (600|800|900)' src/styles.css`가 아무것도 내지 않는다
- [x] `grep -n 'ink-3\|var(--warn)\|Pretendard' src/styles.css`가 아무것도 내지 않는다
- [x] 360px en·vi·ko·ar에서 `/`, `/home`, `/intake`, `/result`, `/emergency`가 가로로 넘치지 않는다
- [x] 1280px·900px에서 `/center`, `/center/stats`가 넘치지 않고 칩 글자가 읽힌다
- [x] `design.md`에 역할 색 대응과 글자 사다리 대응이 있다

## 결과
- `npm run build` → 통과(타입 검사 + 빌드, 기존 500kB 청크 경고만)
- `grep -nE 'font-size: [0-9.]+(rem|px)'`(`:root` 밖), `grep -nE 'font-weight: (600|800|900)'`, `grep -n 'ink-3\|var(--warn)\|Pretendard'` → 모두 결과 없음
- 브라우저 확인(Claude in Chrome 대신 headless Chromium, `vite preview`)
  - 360px en·vi·ko·ar: `/`, `/home`, `/intake`, `/emergency`, `/result`(접수를 끝까지 눌러 들어감). 모든 화면 `scrollWidth` 360으로 가로 넘침 없음
  - 1280px·860px: `/center`, `/center/stats` 넘침 없음. 높음·보통·낮음·신규·진행·완료 칩 글자가 읽힌다
  - 응급 히어로·119 띠는 red-800 바탕에 흰 글자, 응급 전화 버튼은 `--card` 위 red-800 글자
- 결정
  - 글자 크기는 rem 값을 가장 가까운 `t` 단계로 옮겼다(0.8→t3, 0.82→t3, 0.85·0.88·0.9·0.92→t4, 0.95·0.98·1·1.05→t5, 1.1·1.15→t6, 1.2→t7, 1.4→t8, 1.45·1.5→t9, 1.6→t10, 1.7·1.8→t11, 2.6→t13, 4→t14)
  - 두께 600은 흐린 라벨(`.kv dt`, 센터 탭)을 500, 값(`.kv dd`)을 700으로, 800·900은 700으로 옮겼다
  - `--ink-3`·`--warn`은 쓰던 곳을 `--ink-2`·`--warn-ink`로 옮기고 토큰을 없앴다(위 "색 토큰")
- 남은 문제: 포커스 윤곽(`--accent`) 대비는 18번 `## 메모` 그대로 따로 한다. SEED의 `stroke-focus-ring`은 blue-600이다

## 메모
- 글자 크기를 가장 가까운 단계로 옮기면서 화면 몇 곳이 1~2px 커지거나 작아진다(예: 결과 카드 값 18.4 → 18px, 응급 전화 번호 27.2 → 28px, 분석 중 그림 64 → 48px). 문구는 바꾸지 않으므로 원어민 검수 대상은 아니다
