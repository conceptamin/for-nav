# 06. 클레이모피즘 적용

상태: 완료
의존: 04 (`:root` 밖에 16진수 색이 없어진 뒤에 한다. 04가 더하는 `--on-brand`·`--accent`·`--info`/`--info-bg`·`*-ink`·`--bg-2`/`--bg-3`·`--live-bg`를 그대로 쓴다)

## 목표
`design.md` "클레이모피즘" 절대로 `styles.css`를 옮긴다. 지금은 흰 카드 + 얇은 테두리 + 2겹 바깥 그림자의 평면 스타일이고, 문서는 떠 있음(`--clay`·`--clay-sm`)·들어감(`--clay-in`)·평평(그림자 없음) 세 면으로 그리라고 한다. 클래스 단위로 한 번에 바꾸고, 화면(`.tsx`)은 손대지 않는다. 문서 끝 "클레이모피즘 적용 항목이 할 일"이 이 항목의 범위이고, 끝나면 그 절을 문서에서 지운다.

## 범위
- 하는 것
  - `:root` 토큰 교체(`design.md` "토큰" 절 값 그대로)
    - 색: `--bg` `#f3f6f8`→`#e6edf2`, `--card` `#ffffff`→`#f8fafc`, `--brand-2`→`#dcebf2`, `--ok-bg`→`#e2f3ea`, `--warn-bg`→`#fff1d6`, `--danger-bg`→`#fbe3e1`
    - 둥글기: `--radius` `14px`→`20px`, `--radius-sm: 16px`·`--radius-lg: 28px` 추가
    - 그림자: `--shadow` 제거. 재료 `--clay-light`·`--clay-dark`·`--clay-drop`와 면 `--clay`·`--clay-sm`·`--clay-in`·`--clay-color`·`--clay-color-sm`·`--clay-color-in` 추가. 값은 `design.md` "그림자" 코드 블록을 그대로 붙인다
    - 04가 더한 `--bg-2`/`--bg-3`(센터 바닥·표 머리·줄무늬) 값을 새 `--bg`와 `--card` 사이로 다시 고른다. `.c-shell` 배경은 `--bg`로 통일한다(점토가 놓이는 바닥은 근로자·센터가 같다)
  - 떠 있음으로 바꿀 클래스(`box-shadow: var(--shadow)` 또는 테두리 → 아래 토큰)
    | 클래스 | 바탕 | 그림자 | 둥글기 |
    |---|---|---|---|
    | `.card`, `.panel`, `.kpi`, `.table-wrap` | `--card` | `--clay` | `--radius` |
    | `.btn`(기본), `.btn.danger` | `--brand` / `--danger` | `--clay-color-sm` | `--radius-sm` |
    | `.btn.secondary` | `--card` | `--clay-sm` | `--radius-sm` |
    | `.btn.ghost` | 투명 | 없음(평평) | `--radius-sm` |
    | `.chip`, `.check`, `.filters button`, `.filters select` | `--card` | `--clay-sm` | `--radius-sm`(필터·select는 12px) |
    | `.menu a` | `--card` | `--clay` | `--radius-lg` |
    | `.menu a.primary` | `--brand` | `--clay-color` | `--radius-lg` |
    | `.dept` | `--brand-2` | `--clay` | `--radius` |
    | `.dept.alt` | `--card` | `--clay-sm` | `--radius` |
    | `.em-hero` | `--danger` | `--clay-color` | `--radius` |
    | `.em-call` | `--card` | `--clay` | `--radius-lg` |
    | `.bar-119 a` | `--danger` | `--clay-color-sm` | `--radius-lg` |
    | `.toggle button[aria-pressed='true']` | `--brand` | `--clay-color-sm` | `--radius-sm` |
  - 들어감으로 바꿀 클래스(`box-shadow: var(--clay-in)`, 테두리 없음)
    | 클래스 | 바탕 | 비고 |
    |---|---|---|
    | `input[type='text'|'date'|'number'|'tel']`, `textarea`, `select.input` | `--card` | 둥글기 `--radius-sm` |
    | `.chip[aria-pressed='true']` | `--brand-2` | ✓ 접두·굵게는 그대로 |
    | `.check:has(:checked)` | `--brand-2` | 새 선택자. 체크된 동의 줄이 들어간다 |
    | `.steps span` | `--line` | `.on`은 `--brand` 채움. 둥글기 999px |
    | `.menu a .ico` | `--brand-2` | `.primary .ico`는 지금의 반투명 흰 바탕 + `--clay-color-in` |
    | `.toggle` | `--card` | 전체가 홈. 둥글기 `--radius-sm`, `overflow: hidden` 유지 |
    | `.native-box`, `.bar-track` | `--bg-2` | `.bar-track`·`.bar-fill` 둥글기 999px |
    | `.c-header nav a.active` | `--brand-2` | 둥글기 12px |
    | `.filters button[aria-pressed='true']` | `--brand` | `--clay-color-in` |
    | 떠 있는 것의 `:active` | 그대로 | `.btn`·`.btn.danger`·`.bar-119 a`·`.menu a.primary`·`.toggle button[aria-pressed='true']`는 `--clay-color-in`, `.btn.secondary`·`.chip`·`.check`·`.menu a`·`.em-call`·`.filters button`은 `--clay-in`. `.btn.ghost`는 `:active`에도 평평 |
  - 테두리 제거: `.btn`(+ `ghost`·`danger`의 `border-color`), `.chip`(+ 눌림의 `border-color`), `.check`, `.dept`·`.dept.alt`, `.toggle`, `.filters button`·`.filters select`(+ 눌림의 `border-color`), 입력란 전부. `border: 0`으로 바꾼다. 남기는 테두리는 `:focus-visible` 윤곽, `table.cases th·td`의 `border-bottom`, `.line`·`.report-row`·`.c-header`의 `border-bottom`(구분선)
  - 둥글기 교체: 위 두 표의 값. 그 밖에 남는 리터럴은 `999px`(`.pill`, `.badge`, `.steps span`, `.bar-track`, `.bar-fill`, `.legend i`)와 `12px`(`.w-header select`, `.c-header nav a`, `.filters button`·`select`)뿐이다. `.notice`는 `--radius-sm`
  - 간격: 떠 있는 면 사이를 16px로. `.card`·`.em-hero`의 `margin-bottom` 12→16, `.menu`의 `gap` 10→16, `.c-grid`의 `gap` 12→16. `.panel`은 이미 16
  - `design.md`: 머리말의 "지금 `styles.css`는 평면 카드 스타일" 단락과 끝의 "클레이모피즘 적용 항목이 할 일" 절을 지우고, 토큰 표의 `--bg-2`/`--bg-3` 값을 최종값으로 고친다
- 하지 않는 것
  - `.tsx` 수정. 인라인 `style`(`Center.tsx`·`Intake.tsx`·`Report.tsx`의 간격·너비·색 변수 몇 곳)은 그대로 둔다
  - 새 클래스 이름, 클래스 이름 변경. 새 선택자는 `.check:has(:checked)`와 `:active` 규칙뿐이다
  - 글자 크기·굵기·최소 높이·안쪽 여백(`padding`) 변경. 지금 면의 가로 여백은 전부 12px 이상이라 "안쪽 그림자 위에 글자를 두지 않는다" 규칙을 이미 만족한다
  - 애니메이션·`transition`·`:hover` 효과·`transform: scale()`. 눌림은 `:active`에서 그림자만 즉시 바뀐다. `table.cases tbody tr:hover` 행 강조는 지금대로 둔다
  - 색 토큰 추가. 04가 끝난 뒤이므로 `:root` 밖에 16진수 색이 없고, 이 항목은 `:root` 값·`box-shadow`·`border`·`border-radius`·간격만 바꾼다
  - 다크 모드, 고대비 모드 대응, SVG 아이콘

## 화면·파일
- 화면: 전체(S-01~S-13, C-01~C-03). 모양이 바뀌고 동작·경로·문구는 바뀌지 않는다
- 수정: `src/styles.css`, `design.md`
- 부르는 API·새 문구 키: 없음

## 완료 기준
- [x] `npm run build` 통과
- [x] `awk '/^:root/,/^}/{next} {print NR": "$0}' src/styles.css | grep -E '#[0-9a-fA-F]{3,6}([^0-9a-fA-F]|$)'`의 출력이 비어 있다(04의 기준이 깨지지 않았다. macOS awk는 `\b`를 몰라 04에서 grep으로 바꾼 명령을 쓴다)
- [x] `awk '/^:root/,/^}/{next} /box-shadow:/ && !/var\(--clay/ && !/box-shadow: none/' src/styles.css`의 출력이 `table.cases tr.fresh`의 왼쪽 띠(`inset 4px 0 0 var(--accent)`) 한 줄뿐이다(`:root` 밖에 그림자 리터럴이 없다)
- [x] `grep -n 'var(--shadow)' src/styles.css`와 `grep -n -- '--shadow:' src/styles.css`의 출력이 비어 있다(옛 토큰이 남지 않았다)
- [x] `awk '/^:root/,/^}/{next} /border-radius:/ && !/var\(--radius/ && !/999px/ && !/12px/' src/styles.css`의 출력이 비어 있다(`:root` 밖의 둥글기는 토큰·999px·12px뿐이다)
- [x] `awk '/^:root/,/^}/{next} /^[[:space:]]*border(-color|-width)?:/ && !/border: 0;/' src/styles.css`의 출력이 비어 있다(면의 테두리가 없다. `border-bottom`·`border-collapse`는 매치되지 않는다)
- [x] `grep -c 'transition\|transform: scale\|text-shadow\|backdrop-filter' src/styles.css`가 `0`이다
- [x] 360px에서 `/home`, `/intake`, `/result`, `/visit/desk`, `/report/new`, `/report/:id`, `/emergency`를, 1280px과 900px 아래에서 `/center`, `/center/stats`를 en·vi·ko로 스크린샷. 파일 이름을 `## 결과`에 적는다. 베트남어 긴 문구가 칩·버튼·메뉴의 모서리 안쪽 음영에 걸리지 않고, 가로 스크롤이 생기지 않는다
- [x] 스크린샷에서 `design.md` "세 가지 면" 표대로 보인다: 카드·버튼·칩·메뉴·KPI·패널은 왼쪽 위가 밝고 오른쪽 아래가 어둡고 아래로 그림자가 떨어진다. 입력란·선택된 칩·체크된 동의 줄(`/consent`)·단계 점 트랙·막대 트랙은 반대로 안으로 들어가 있다. 안내 상자·`pill`·헤더는 그림자가 없다
- [x] 360×640에서 `/result`의 첫 화면에 h1·1순위 진료과(`.dept`)·첫 행동 버튼이 스크롤 없이 보인다(카드 간격이 16px로 늘어난 뒤 다시 확인)
- [x] `Tab`으로 `/intake`·`/consent`·`/center`를 이동하면 버튼·칩·입력란·필터에 3px `--accent` 포커스 윤곽이 면 바깥(`outline-offset: 2px`)에 보인다. 입력란은 테두리가 없으므로 윤곽이 보이는 것이 "지금 여기" 표시다
- [x] 버튼·칩을 누르고 있는 동안(`:active`) 그림자가 들어감으로 바뀌고 놓으면 돌아온다. `disabled` 버튼은 떠 있음을 유지한 채 흐리기만 하다
- [x] `/center` 표가 900px 아래에서 지금처럼 가로 스크롤되고, 표 상자의 둥근 모서리 밖으로 행이 삐져나오지 않는다
- [x] `design.md`에 "클레이모피즘 적용 항목이 할 일" 절과 "평면 카드 스타일" 단락이 없고, 토큰 표의 `--bg-2`/`--bg-3` 값이 `styles.css`와 같다

## 결과

2026-10-29. `frontend/claymorphism` 브랜치. 04(PR 62) 위에 쌓았다.

정적 검사

| 검사 | 결과 |
|---|---|
| `npm run build` | 통과 |
| `:root` 밖 16진수 색 | 없음 |
| `:root` 밖 그림자 리터럴 | `table.cases tr.fresh`의 `inset 4px 0 0 var(--accent)` 한 줄 |
| `var(--shadow)`, `--shadow:` | 없음 |
| `:root` 밖 둥글기 | 토큰·`999px`·`12px`뿐. `12px`은 `.w-header select`, `.c-header nav a`, `.filters button`·`select` |
| 면의 테두리 | 없음 |
| `transition`·`transform: scale`·`text-shadow`·`backdrop-filter` | 0 |

화면 확인(Playwright Chromium, 시계 2026-10-29 10:00 KST 고정). 파일은 스크래치 폴더의 `clay/after-<언어>-<폭>-<화면>.png`이고, 비교용 `before-` 같은 이름이 있다.

- 360px, en·vi·ko: `home`, `consent`, `intake`, `intake-text`, `result`, `result-fold`(첫 화면), `visit-desk`, `report-new`, `report-view`, `emergency`, `center-request`, `chip-active`, `focus`
- 1280px·880px, en·vi·ko: `center`, `center-stats`, `center-detail`

| 점검 | 결과 |
|---|---|
| 가로 스크롤 | 세 언어 모든 근로자 화면과 센터 두 폭에서 없음 |
| 세 가지 면 | 카드·버튼·칩·메뉴·KPI·패널은 왼쪽 위가 밝고 아래로 그림자. 입력란·선택된 칩·체크된 동의 줄·단계 점·막대 트랙·원문 상자·센터 활성 탭은 들어감. 안내 상자·`pill`·헤더는 평평 |
| `/result` 첫 화면(360×640) | h1 아래 끝 182px, 첫 행동 버튼 345px, 1순위 진료과 상자 359px(en·vi). ko는 160·299·313px. 모두 640px 안 |
| `:active` | 칩·체크·보조 버튼·필터: 떠 있음 → 누르는 동안 들어감 → 놓으면 떠 있음 |
| `disabled` | `opacity 0.45`, 그림자는 떠 있음 그대로, 눌러도 바뀌지 않음 |
| 포커스 윤곽 | `/intake`·`/consent`·`/center`의 칩·select·체크·버튼·필터·탭에서 `3px rgb(240, 165, 0)`, 오프셋 2px |
| 센터 표 | 1280px은 스크롤 없음, 880px은 표 상자 안에서 가로 스크롤. 둥글기 20px 밖으로 행이 나오지 않음 |
| 베트남어 긴 문구 | 칩·버튼·메뉴 모두 안쪽 여백 12px 이상이라 모서리 음영에 걸리지 않음 |

backlog 표에서 더 정한 것
- `.toggle button`의 바탕을 `--card`에서 투명으로 바꿨다. 토글 전체가 들어간 홈이므로, 버튼이 바탕을 칠하면 홈의 안쪽 그림자를 덮는다. 고른 쪽만 브랜드색으로 떠오른다
- `.menu a .ico`의 둥글기는 표에 없어서 `--radius-sm`(16px)으로 했다. 리터럴 둥글기를 999px·12px로만 제한하는 기준을 지키기 위해서다
- 눌림은 `:not(:disabled):active`로 걸었다. 비활성 버튼은 눌러도 들어가지 않는다
- `.filters button:disabled`(데모 초기화 중)도 근로자 버튼처럼 흐리게 했다. 03에서 이 버튼에 `disabled`가 생겼다
- `--bg-2`는 `#eef3f6`, `--bg-3`은 `#f2f6f9`로 새 `--bg`(`#e6edf2`)와 `--card`(`#f8fafc`) 사이에서 골랐다

남은 것
- 발표 기기 브라우저는 확인하지 않았다. Chromium에서만 봤고, `:has()`는 Safari 15.4·Chrome 105·Firefox 121 이상에서 동작한다
- 실제 기기의 손가락 눌림은 확인하지 않았다(마우스 누름으로 대신)
- 컴포넌트 안 색(`Center.tsx`의 도넛 색 세 개, 인라인 `var(--danger)`·`borderTop`)과 `.badge`·`.menu a.primary .ico`의 반투명 흰색은 이 항목 범위(`.tsx` 수정 없음, 색 토큰 추가 없음) 밖이라 그대로다. 별도 항목이 필요하다

## 메모
- 순서: **04(토큰 밖 색상 정리) → 06**. 04가 `:root` 밖 16진수 색을 없애고 `--on-brand`·`--accent` 등을 더한 뒤에 이 항목이 `:root` 값·그림자·테두리·둥글기만 바꾼다. 둘을 한 PR에 섞지 않는다(04는 모양이 같아야 하는 치환이고, 06은 모양을 바꾸는 작업이라 스크린샷 비교 기준이 다르다). 05(응급도 입력)와는 파일이 겹치지 않는다
- 기준 문서: `design.md`의 클레이모피즘 절은 PR conceptamin/for-nav#56(`docs/design-claymorphism`)이 더했다. 이 문서는 그 PR의 "클레이모피즘 적용 항목이 할 일" 절을 backlog 형식으로 옮긴 것이다. 56이 병합되기 전에는 이 항목을 시작하지 않는다
- 문서와 다르게 정한 것(구현 전에 확인)
  - `.table-wrap`은 `design.md`가 `overflow: hidden`이라 적었지만 지금의 `overflow-x: auto`를 둔다. `visible`이 아닌 `overflow`는 둥근 모서리로 똑같이 잘라 주고, 900px 아래에서 표의 가로 스크롤이 필요하다
  - `.c-header`의 `border-bottom`은 평평한 헤더와 바닥의 구분선으로 남긴다. 문서의 "테두리를 남기는 곳"에 구분선이 포함된다고 본다
  - `.bar-119`의 `linear-gradient` 배경은 면의 채움이 아니라 고정 띠 뒤의 페이드이므로 "그라데이션 채움 금지"에 걸리지 않는다고 보고 둔다
  - `.legend i`(도넛 범례 색 칸)는 둥글기 3px→999px로 원이 된다. 사각 칸을 유지하려면 `999px` 대신 토큰이 필요하므로 원으로 가는 쪽을 택했다
  - `.bar-track`·`.bar-fill`·`.steps span`은 얇은 트랙이라 999px로 알약 모양이 된다(`design.md` 둥글기 표의 "단계 점 999px"과 맞춘다)
  - `.native-box`·`.bar-track`의 바탕은 04가 정한 `--bg-2`를 쓴다. 들어간 면이 카드와 같은 색이면 안쪽 그림자만으로 홈이 보여야 하는데, 한 단계 어두운 바탕이 더 분명하다. 입력란은 `design.md`대로 `--card`다
- `.check:has(:checked)`는 `:has()` 선택자를 쓴다. Safari 15.4·Chrome 105·Firefox 121 이상에서 동작하고, 지원하지 않는 브라우저에서는 체크된 줄이 떠 있음으로 남을 뿐 동작은 같다. 발표 기기 브라우저를 `## 결과`에 적는다
- `--clay-light`는 흰색 85%라 `--card`(`#f8fafc`) 위에서만 보인다. `--card`를 다시 순백으로 되돌리면 하이라이트가 사라지므로, 04에서 `#fff` 배경을 `--card`로 치환한 자리를 이 항목에서 다시 흰색으로 돌리지 않는다
- 이 항목이 끝나면 `design.md`의 컴포넌트 표 "면" 열이 코드와 1:1이 된다. 그 뒤 새 조각을 그릴 때는 문서의 "새 스타일을 더하는 절차" 2번(어느 면인지 정하기)을 따른다
