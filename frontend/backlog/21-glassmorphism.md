# 21. 글래스모피즘 적용

상태: 완료
의존: 06(클레이모피즘. 같은 클래스 표를 그대로 옮긴다), 18(틸 브랜드), 19(SEED 역할 색. 대비 기준값을 쓴다)

## 목표
`design.md` "글래스모피즘" 절대로 `styles.css`를 옮긴다. 지금은 `--clay*` 토큰의 점토 면이고, 문서는 비치는 바닥 위 반투명 유리 면(`--glass`·`--glass-sm`)·들어감(`--glass-in`)·평평 세 면으로 그리라고 한다. 06과 같이 클래스 단위로 한 번에 바꾸고, 화면(`.tsx`)은 손대지 않는다.

## 범위
- 하는 것
  - `:root` 토큰 교체(`design.md` "바탕"·"그림자와 흐림" 절 값 그대로)
    - 색: `--bg` `#e6edf2`→`#e3eff0`, `--card` `#f8fafc`→`rgb(255 255 255 / 62%)`, `--bg-2`→`rgb(18 35 46 / 5%)`, `--bg-3`→`rgb(18 35 46 / 4%)`
    - 새 토큰: `--bg-glow-1`·`--bg-glow-2`·`--bg-paint`·`--card-solid`, `--glass-edge`·`--glass-shine`·`--glass-shade`·`--glass-drop`·`--glass-blur`, 면 `--glass`·`--glass-sm`·`--glass-in`·`--glass-color`·`--glass-color-sm`·`--glass-color-in`
    - `--clay*` 토큰 11개를 지운다
  - 그림자 치환: 06이 정한 클래스 표의 면을 그대로 옮긴다(`--clay`→`--glass`, `--clay-sm`→`--glass-sm`, `--clay-in`→`--glass-in`, `--clay-color*`→`--glass-color*`). `.card.band`의 띠는 `inset 0 6px 0 var(--band), var(--glass)`
  - 바닥: `body`만 `background: var(--bg-paint); background-attachment: fixed`. `:root`·`.w-shell`·`.c-shell`의 `background: var(--bg)`를 지운다
  - 흐림: `design.md` "흐림은 맨 위 유리에만" 표의 왼쪽 칸 클래스에만 `-webkit-backdrop-filter`·`backdrop-filter: var(--glass-blur)`를 단다
  - 고정 띠: `.w-header`·`.w-footer`·`.c-header`는 `--card` + 흐림 + 1px `--glass-edge` 선. `.bar-119`의 `linear-gradient(to top, var(--bg) 70%, transparent)`도 같은 유리 띠로 바꾼다(119 버튼 자체는 `--danger` 불투명 그대로)
  - 입력란(`input`·`textarea`·`select.input`)의 바탕을 `--card`에서 `--bg-2`로
  - 대체: `@supports not (backdrop-filter …) and not (-webkit-backdrop-filter …)`와 `@media (prefers-reduced-transparency: reduce)`에서 `--card: var(--card-solid)`
  - `design.md` 글래스모피즘 절 머리의 "적용 전" 단락을 지운다
- 하지 않는 것
  - 둥글기 값, 색이 있는 면의 색(`--brand`·`--danger`), 글자·상태색 토큰
  - 배치·간격, `.tsx`, 문구
  - 다크 모드, 애니메이션·`transition`

## 화면·파일
- 모든 근로자 화면(S-01~S-13)과 센터 화면(C-01~C-03)의 겉모양. 경로·API·문구 키는 바뀌지 않는다
- `frontend/src/styles.css`, `frontend/design.md`(적용 전 단락 삭제)

## 완료 기준
- [x] `npm run build` 통과
- [x] `grep -n "clay" src/styles.css`가 비어 있다
- [x] `awk '/^:root/,/^}/{next} /box-shadow:/ && !/var\(--glass/ && !/box-shadow: none/' src/styles.css`의 출력이 실제 전송 행 띠 한 줄뿐이다(고정 띠의 1px 선은 `var(--glass-edge)`라 걸리지 않는다)
- [x] `backdrop-filter`가 붙은 클래스가 `design.md` "흐림은 맨 위 유리에만" 표의 왼쪽 칸과 같다. 유리 안의 조각(버튼·칩·입력란)에는 없다
- [x] 빛 번짐이 가장 진한 화면 왼쪽 위에서 유리 면 합성색이 `#e6edf2`보다 밝고, 바닥 위 `--ink-2`가 4.5:1 이상이다(합성색을 브라우저에서 찍어 잰 숫자를 `## 결과`에 적는다)
- [x] 360px에서 `/home`·`/intake`·`/result`·`/emergency`·`/report`를 en·vi·ko로 보고, 스크롤할 때 앱 바·119 띠 아래로 내용이 흐리게 비친다
- [x] 1280px·900px에서 `/center` 세 화면이 같은 규칙으로 그려진다
- [x] 개발자 도구에서 `prefers-reduced-transparency: reduce`를 켜면 비침 없이 불투명 면으로 그려진다
- [x] 119 띠·응급 히어로는 바탕 스크롤과 관계없이 같은 `--danger` 색이다

## 결과
2026-10-30. `frontend/glassmorphism` 브랜치. 문서 PR conceptamin/for-nav#91(`docs/design-glassmorphism`) 위에 쌓았다.

| 검사 | 결과 |
|---|---|
| `npm run build` | 통과(500 kB 청크 경고는 전부터 있던 것) |
| `grep -n "clay" src/styles.css` | 빈 출력 |
| `:root` 밖 `var(--glass*)` 아닌 `box-shadow` | `table.cases tr.fresh`의 `inset 4px 0 0 var(--accent)` 한 줄 |
| `backdrop-filter`가 붙은 클래스 | 11개: `.w-header`·`.w-footer`·`.bar-119`·`.c-header`·`.card`·`.kpi`·`.table-wrap`·`.panel`·`.menu a`·`.w-chat .ask .bubble`·`.dept.alt`. `.menu a.primary`는 `none`으로 끈다 |

대비(Playwright Chromium, 360×780, `/home` en, 화면을 찍어 픽셀을 읽어 WCAG 2 대비를 계산):

| 자리 | 색 | `--brand` | `--ink-2` |
|---|---|---|---|
| 바닥 빛 번짐 가장 진한 곳(0,0) | `rgb(200 221 222)` | — | 4.68:1 |
| 바닥 오른쪽 아래(359,779) | `rgb(205 221 231)` | — | 4.76:1 |
| 메뉴 카드 유리 합성색(20,300) | `rgb(239 248 249)` | 7.00:1 | 6.13:1 |
| 메뉴 카드 유리 합성색(20,400) | `rgb(242 249 250)` | 7.09:1 | 6.21:1 |
| 비교: 옛 `--bg` `#e6edf2` | | 6.39:1 | 5.60:1 |

유리 합성색은 두 곳 모두 옛 `--bg`보다 밝다. 바닥 위 `--ink-2`는 가장 진한 곳에서도 4.5:1을 넘는다.

화면 확인(Playwright Chromium, 개발 서버, 세션 저장소에 입력을 넣어 진입):
- 360px, en·vi·ko: `/home`, `/intake`, `/result`(vi는 스크롤 후도), `/report/new`, `/emergency`. 앱 바·아래 주 동작 자리·119 띠 아래로 스크롤된 카드가 흐리게 비친다. 응급 히어로와 119 버튼은 불투명 `--danger` 그대로다.
- 1280px·880px: `/center`, `/center/stats`. 센터 헤더가 유리 띠로, KPI·표 상자·패널이 유리 면으로 그려진다.
- CDP `Emulation.setEmulatedMedia`로 `prefers-reduced-transparency: reduce`를 켜면 `--card`가 `#f3f8f9`로 바뀌고 비침이 없어진다(Playwright의 `emulateMedia({ reducedTransparency })`는 이 Chromium에서 적용되지 않아 CDP로 확인했다).

결정 사항:
- **응급 전화 버튼(`.em-call`)은 `--card-solid`.** 불투명한 빨간 히어로 위에 놓여 반투명 흰색이면 분홍으로 비친다. `design.md`에 "색이 있는 면 위의 흰 면은 `--card-solid`" 규칙을 더했다.
- **흐림은 반투명 바탕인 면에만.** 첫 진료과 상자(`.dept`, 불투명 `--brand-2`)와 첫 메뉴(`.menu a.primary`)는 흐릴 것이 보이지 않아 빼고, `design.md` 표를 그에 맞게 고쳤다.
- **`.w-footer`를 화면 폭으로 넓혔다**(`margin: 16px -16px -16px; padding: 16px`). 바닥색일 때는 좌우 여백이 보이지 않았지만, 유리 띠는 본문 폭에서 끊기면 상자처럼 보인다. 버튼 위치는 그대로다.
- **센터 헤더의 아래 `border-bottom: 1px solid var(--line)`을 유리 가장자리 선(`box-shadow: 0 1px 0 var(--glass-edge)`)으로 바꿨다.**
- 입력란·토글 바탕을 `--card`에서 `--bg-2`로 바꿨다(흰 반투명은 떠 있는 면의 색이라 들어간 면으로 읽히지 않는다).

남은 문제:
- ar(RTL)·my·ru는 보지 않았다. 배치는 `.w-footer` 좌우 여백(대칭) 말고 바꾸지 않았다.
- 실제 저가형 안드로이드에서 스크롤 성능은 재지 않았다(메모 참고).

## 메모
- 클레이모피즘(06)을 대신한다. 06의 결과 기록은 그대로 둔다.
- 반투명 면 위 대비는 바닥에 따라 달라지므로 18·19의 대비 숫자는 "유리 합성색이 옛 `--bg`보다 밝다"는 조건 위에서만 성립한다. 빛 번짐·`--card` 알파를 바꾸는 후속 작업은 이 조건을 다시 잰다.
- `backdrop-filter`는 저가형 안드로이드에서 비싸다. 흐림을 맨 위 유리에만 다는 규칙이 그 대책이다. 시연 기기에서 스크롤이 끊기면 `--glass-blur` 반경을 줄이는 것을 먼저 본다.
- 20(대화형 언어 선택)이 말풍선을 `--clay`로 적었다면, 이 항목이 끝난 뒤 그 클래스도 `design.md` "말풍선" 표대로 `--glass*`를 쓴다(06 치환 표에 말풍선 줄을 더한다).
