# 화면을 그리는 규칙(WebView 덧붙임)

이 앱의 화면은 `frontend/design.md`로 그린다. SEED Design 토큰(색·타이포·간격·둥글기), 컴포넌트, 글래스모피즘, Do's and Don'ts, 모션(스크롤 등장 하나)이 모두 그대로다. 근로자 화면을 가져오면(backlog 02) 스타일도 같은 파일을 쓴다. 이 문서는 **WebView 안에서만 더 지키는 것**이다. 여기에 없는 모양을 새로 그릴 때는 `frontend/design.md`를 먼저 고친다.

## 안전 영역

- `index.html` 뷰포트는 `width=device-width, initial-scale=1, viewport-fit=cover`다. `user-scalable=no`·`maximum-scale=1`을 쓰지 않는다(`CLAUDE.md` "줌을 막지 않는다").
- 안전 영역 값은 두 출처를 합친다. iOS는 `env(safe-area-inset-*)`, Android는 호스트가 `init`·`insets`로 준 `--inset-*`(`src/bridge/`가 `:root`에 넣는다). 스타일은 항상 둘 중 큰 쪽을 쓴다.

```css
:root { --inset-top: 0px; --inset-right: 0px; --inset-bottom: 0px; --inset-left: 0px; }
.w-shell { padding-top: max(env(safe-area-inset-top), var(--inset-top)); }
.bar-119 { padding-bottom: max(env(safe-area-inset-bottom), var(--inset-bottom)); }
```

- 하단 119 띠는 안전 영역 위에 뜨고, 띠의 높이에 안전 영역만큼 더한 값이 본문 아래 여백이다. 홈 인디케이터와 겹치지 않는다.
- 바닥 주 버튼 띠(`.w-footer`)는 화면 바닥까지 내려와 119 독 자리를 함께 덮는다(frontend backlog 35). 그래서 덧붙임은 `bottom`이 아니라 아래 바깥 여백(`-(--bar-119 + 16px + 안전 영역)`)과 아래 안쪽 여백(`--bar-119 + 안전 영역`)에 안전 영역을 더한다. `bottom`을 띄우면 띠가 독 위로 떠서 그 사이로 본문이 비친다.
- 가로 안전 영역(`left`·`right`)은 가로 모드 때만 생긴다. 앱은 세로 고정이지만 값이 와도 깨지지 않게 좌우 여백에 더한다.

## 높이와 스크롤

- 화면 높이는 `100dvh`를 기준으로 한다(`100vh`는 WebView에서 주소창·키보드와 어긋난다). `dvh`가 없는 오래된 WebView를 위해 `min-height: 100vh`를 먼저 쓰고 `100dvh`로 덮는다.
- `body`에 `overscroll-behavior: none`을 두어 당겨서 튕기는 동작과 iOS의 고무줄 효과가 화면 전체를 흔들지 않게 한다. 안쪽 스크롤 목록(채팅)은 `overscroll-behavior: contain`.
- 키보드가 올라오면 WebView가 뷰포트를 줄인다. 입력란이 가려지지 않게 스크롤하는 것은 브라우저 기본 동작에 맡기고 따로 코드를 두지 않는다. 하단 119 띠는 키보드 위에 뜨지 않아도 된다.

## 터치

- 누르는 요소 전체에 `touch-action: manipulation`(두 번 탭 확대 지연 제거)과 `-webkit-tap-highlight-color: transparent`를 둔다. 눌림 표현은 `frontend/design.md`의 "눌림의 예"(배경·그림자 변화)로 한다.
- `:hover` 스타일은 터치에서 눌린 뒤 남는다. 호버만으로 뜻이 바뀌는 표현을 두지 않고, 호버 스타일은 `@media (hover: hover)` 안에 둔다.
- 글 선택이 필요 없는 곳(버튼·칩·앱 바)은 `user-select: none`. 접수 창구 화면(S-09)의 한국어 문장과 리포트는 복사할 수 있어야 하므로 두지 않는다.
- iOS WKWebView의 긴 누름 링크 미리보기는 `tel:`·지도 링크에서 혼란을 주므로 `-webkit-touch-callout: none`을 링크에 둔다.

## 글꼴과 크기

- 시스템 글꼴 규칙은 같다. Android WebView는 Noto Sans CJK, iOS는 Apple SD Gothic Neo가 잡힌다. 웹폰트를 내려받지 않는다.
- OS 글자 크기 배율을 따른다. 크기는 `rem`으로 쓰고 `px`로 고정하지 않는다. 배율 150%에서 360px 폭이 넘치지 않는지 본다(베트남어로 먼저 본다).

## 호스트 확인 화면(`/__host`)

개발 확인용이다. 토큰과 컴포넌트(`.card`, `.btn`, `.notice`)를 쓰되, 근로자 화면에서 쓰지 않는 표(키·값 두 열)를 하나 허용한다. 근로자 화면이 생긴 뒤에도 남겨 두고, 홈 메뉴·네비게이션에 넣지 않는다.
