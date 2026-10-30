# 21. 글래스모피즘 적용

상태: 대기
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
- [ ] `npm run build` 통과
- [ ] `grep -n "clay" src/styles.css`가 비어 있다
- [ ] `awk '/^:root/,/^}/{next} /box-shadow:/ && !/var\(--glass/ && !/box-shadow: none/' src/styles.css`의 출력이 실제 전송 행 띠 한 줄과 고정 띠의 1px 선뿐이다
- [ ] `backdrop-filter`가 붙은 클래스가 `design.md` "흐림은 맨 위 유리에만" 표의 왼쪽 칸과 같다. 유리 안의 조각(버튼·칩·입력란)에는 없다
- [ ] 빛 번짐이 가장 진한 화면 왼쪽 위에서 유리 면 합성색이 `#e6edf2`보다 밝고, 바닥 위 `--ink-2`가 4.5:1 이상이다(합성색을 브라우저에서 찍어 잰 숫자를 `## 결과`에 적는다)
- [ ] 360px에서 `/home`·`/intake`·`/result`·`/emergency`·`/report`를 en·vi·ko로 보고, 스크롤할 때 앱 바·119 띠 아래로 내용이 흐리게 비친다
- [ ] 1280px·900px에서 `/center` 세 화면이 같은 규칙으로 그려진다
- [ ] 개발자 도구에서 `prefers-reduced-transparency: reduce`를 켜면 비침 없이 불투명 면으로 그려진다
- [ ] 119 띠·응급 히어로는 바탕 스크롤과 관계없이 같은 `--danger` 색이다

## 결과
(구현 후 작성)

## 메모
- 클레이모피즘(06)을 대신한다. 06의 결과 기록은 그대로 둔다.
- 반투명 면 위 대비는 바닥에 따라 달라지므로 18·19의 대비 숫자는 "유리 합성색이 옛 `--bg`보다 밝다"는 조건 위에서만 성립한다. 빛 번짐·`--card` 알파를 바꾸는 후속 작업은 이 조건을 다시 잰다.
- `backdrop-filter`는 저가형 안드로이드에서 비싸다. 흐림을 맨 위 유리에만 다는 규칙이 그 대책이다. 시연 기기에서 스크롤이 끊기면 `--glass-blur` 반경을 줄이는 것을 먼저 본다.
- 20(대화형 언어 선택)이 말풍선을 `--clay`로 적었다면, 이 항목이 끝난 뒤 그 클래스도 `design.md` "말풍선" 표대로 `--glass*`를 쓴다(06 치환 표에 말풍선 줄을 더한다).
