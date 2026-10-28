# 07. 컴포넌트 안 색과 표시 띠 정리

상태: 대기
의존: 06 (클레이모피즘이 적용된 카드 위에서 띠 모양을 정한다)

## 목표
04는 `styles.css`의 `:root` 밖 16진수 색을 없앴지만, `.tsx` 안의 색과 반투명 흰색 두 곳은 범위 밖이라 남았다. 06은 "면에 테두리를 두지 않는다"를 적용했지만, 결과 카드 네 곳(브랜드색 셋, 초록 하나)의 위쪽 색 띠는 인라인 `borderTop`이라 그대로다. 이 남은 것을 토큰과 수식 클래스로 옮겨, "색은 토큰부터, 인라인 `style`에는 색을 쓰지 않는다"가 화면 코드에서도 지켜지게 한다. 화면 모양은 띠의 그리는 방식 외에는 바꾸지 않는다.

## 범위
- 하는 것
  - **통계 도넛 색**(`pages/center/Center.tsx`의 `PIE_COLORS = ['#0f5b78', '#e08a00', '#9aa8b2']`)
    - `:root`에 차트 토큰 세 개를 더한다: `--chart-1`(`var(--brand)`와 같은 값), `--chart-2`(`#e08a00`), `--chart-3`(`#9aa8b2`)
    - 도넛 조각(`circle`)과 범례 점(`.legend i`)은 수식 클래스 `.series-1`~`.series-3`으로 색을 받는다. `circle`은 `stroke`, 범례 점은 `background`. SVG의 `stroke` 속성에는 `var()`가 먹지 않으므로 속성이 아니라 CSS 클래스로 준다
    - `PIE_COLORS` 상수를 지운다
  - **KPI 강조 숫자**(`Center.tsx`의 "긴급도 높음(미완료)" 숫자 `style={{ color: 'var(--danger)' }}`): 수식 클래스 `.kpi .n.danger`로 옮긴다
  - **결과 카드 위쪽 띠**(`style={{ borderTop: '6px solid var(--brand)' }}` 세 곳과 `var(--ok)` 한 곳)
    - 대상: `CenterRequest.tsx` S-12 미리보기, `Visit.tsx` S-09 창구 문장, `Report.tsx` S-11 리포트(브랜드색), `Coverage.tsx` S-08 결과(초록)
    - 수식 클래스 `.card.band`(브랜드색)와 `.card.band.ok`(초록)로 옮긴다
    - 그리는 방식은 아래 "결정할 것"에서 고른다
  - **구분선**(`Visit.tsx` S-10 자주 묻는 질문의 `style={{ padding: '12px 0', borderTop: '1px solid var(--line)' }}`): `.line`과 같은 구분선 클래스로 옮긴다. 이미 있는 `.line`의 위아래 방향이 다르면 `.line.top` 수식 하나를 더한다
  - **반투명 흰색**(`styles.css`의 `.badge` `rgb(255 255 255 / 20%)`, `.menu a.primary .ico` `rgb(255 255 255 / 18%)`): 토큰 `--on-brand-soft`(`rgb(255 255 255 / 20%)`) 하나로 합친다. 18%와 20%의 차이는 허용한다
  - `design.md`
    - 색 토큰 표에 `--chart-1`~`--chart-3`, `--on-brand-soft`를 더한다
    - 센터 컴포넌트 표의 `.bars`, `.donut-wrap`, `.legend` 줄에 `.series-N`을 적는다
    - 근로자 컴포넌트 표에 `.card.band`를 더한다
    - "하지 않는 것"의 "지금 있는 것(버튼 사이 `marginTop` 몇 곳)은 간격만이고 색은 없다"를 사실대로 고친다. 이 항목이 끝나면 남는 인라인 `style`은 간격·너비·정렬뿐이다
- 하지 않는 것
  - 간격·너비·정렬 인라인 `style`(`marginTop`, `marginLeft`, `flex: 1`, 막대 `width` 계산값 등)의 클래스화. 색이 없고, 동적 값이 섞여 있어 별도 판단이 필요하다
  - 막대 채움(`.bar-fill`) 색 변경. 지금처럼 `--brand` 한 색이다
  - 차트 라이브러리 도입, 도넛 모양 변경, 새 차트
  - `.tsx`의 구조·문구·동작 변경. `className`과 `style`만 바꾼다

## 결정할 것
결과 카드 위쪽 띠를 어떻게 그릴지 구현 전에 사용자와 정한다.

| 안 | 그리는 법 | 장점 | 단점 |
|---|---|---|---|
| A. 안쪽 그림자 띠(추천) | `.card.band { box-shadow: inset 0 6px 0 var(--brand), var(--clay); }` | 실제 전송 행의 왼쪽 띠(`inset 4px 0 0 var(--accent)`)와 같은 방식이라 "표시 띠는 안쪽 그림자"로 규칙이 하나가 된다. 테두리가 없으니 06의 "면에 테두리 없음"을 지킨다. 둥근 모서리를 그대로 따라간다 | `:root` 밖 그림자 리터럴 예외가 하나 늘어난다(06의 정적 검사 기대값을 두 줄로 고친다) |
| B. 테두리 예외 | `.card.band { border-top: 6px solid var(--brand); }` | 지금 모양과 픽셀까지 같다 | "면에 테두리 없음"에 예외가 생긴다. 06 정적 검사의 테두리 검사에 걸린다 |
| C. 띠 없앰 | 클래스 없이 `.card`만 | 규칙 예외가 없다 | 결과 카드가 다른 카드와 구분되지 않는다. 창구 직원에게 보여 주는 S-09 문장 카드가 눈에 덜 띈다 |

A로 하면 `design.md` "그림자" 절의 예외 문장을 "표시 띠 두 가지(실제 전송 행의 왼쪽 띠, 결과 카드의 위쪽 띠)"로 고친다.

## 화면·파일
- 화면: S-08 `/coverage`, S-09 `/visit/desk`, S-10 `/visit/call`, S-11 `/report/:id`, S-12 `/center-request`, C-01 `/center`, C-03 `/center/stats`. 경로·문구·동작 변경 없음
- 부르는 API·새 문구 키: 없음
- 수정: `src/styles.css`, `src/pages/center/Center.tsx`, `src/pages/worker/{CenterRequest,Visit,Report,Coverage}.tsx`, `design.md`

## 완료 기준
- [ ] `npm run build` 통과
- [ ] `grep -rnE '#[0-9a-fA-F]{3,6}\b' src --include='*.tsx'`의 출력이 비어 있다(컴포넌트 안 16진수 색이 없다)
- [ ] `grep -rn 'style={{' src | grep -E 'color|background|border'`의 출력이 비어 있다(인라인 `style`에 색·테두리가 없다)
- [ ] `awk '/^:root/,/^}/{next} {print NR": "$0}' src/styles.css | grep -E 'rgb\(|#[0-9a-fA-F]{3,6}([^0-9a-fA-F]|$)'`의 출력이 비어 있다(`:root` 밖에 색 값이 없다)
- [ ] 06의 정적 검사가 깨지지 않는다. 안 A를 고르면 그림자 리터럴 검사의 기대값이 두 줄(실제 전송 행 띠, 결과 카드 띠)이 된다
- [ ] 1280px `/center/stats`에서 도넛 조각과 범례 점의 색이 바뀌기 전과 같다(스크린샷 비교, 각 조각에서 픽셀 하나씩 색 값 확인)
- [ ] 1280px `/center`에서 "긴급도 높음(미완료)" 숫자가 빨강이다
- [ ] 360px에서 S-08·S-09·S-11·S-12 결과 카드의 위쪽 띠가 고른 안대로 보이고, en·vi·ko 세 언어에서 띠가 글자를 가리지 않는다
- [ ] 360px `/home` 헤더의 데모 배지와 첫 메뉴 아이콘 칸이 바뀌기 전과 눈으로 구분되지 않는다
- [ ] `design.md`의 토큰 표·컴포넌트 표·"하지 않는 것"이 코드와 맞는다

## 결과

## 메모
- 2026-10-29: 04와 06의 결과에 "범위 밖이라 남김"으로 적힌 것을 모은 항목이다. 04는 `.tsx`를 고치지 않았고, 06은 `.tsx` 수정과 색 토큰 추가를 범위에서 뺐다
- `--chart-2`(`#e08a00`)는 `--accent`(`#f0a500`)와 가깝지만 같은 토큰으로 합치지 않는다. `--accent`는 "포커스·실제 전송" 뜻으로만 쓰기로 했고(`design.md` 색 토큰 표), 차트 색이 그 뜻을 빌리면 안 된다
- 차트 색 세 개는 색만으로 구분하지 않는다는 규칙에 이미 맞다. 범례에 글자와 건수가 있다
- 결과 카드 띠는 S-07 `/result`의 `.dept`처럼 "이 화면의 핵심 결과"를 표시하는 용도다. 결과 화면 유형(`design.md` "화면 유형별 규칙")에 띠를 쓰는 화면을 적어 두면 다음 화면이 같은 방식을 따른다
