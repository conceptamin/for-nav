# 32. 앱 바 띠를 없애고 왼쪽을 유리 알약으로, 로고 파일 이름 바꾸기

상태: 완료
의존: 28(유리 로고·워드마크), 30, 31

## 목표
2026-10-31 사용자 피드백: "배포된 거에서 보니까 글자는 잘 보이는데 로고 자체는 안 바뀌었어 확인해 주고, 위에 네모 박스가 있을 필요가 없을 것 같고, 로고 쪽도 언어 선택 버튼이 있는 쪽처럼 알약과 같은 느낌으로 바꿔 주면 좋을 것 같아." 배포본에서 새 마크가 보이게 하고, 근로자 앱 바의 화면 폭 띠를 걷어 내 왼쪽(← · 로고 · 워드마크)을 오른쪽 언어 버튼과 같은 유리 알약으로 묶는다.

## 범위
- 하는 것
  - **로고가 안 바뀐 것**: 배포 기록상 새 마크는 #124 병합(2026-10-31 02:57 UTC) 배포부터 `/logo.png`로 나가고 있다. 새 파일인 `/wordmark.png`는 바로 보이고 이름이 같은 `/logo.png`만 옛 그림으로 보였으므로, 브라우저·앱 WebView가 캐시한 옛 파일로 본다. `public/logo.png`를 `public/mark.png`로 이름을 바꿔 모든 화면이 새 주소로 받게 한다(`index.html` 파비콘, `WorkerLayout` 스플래시·앱 바, `Onboarding`, 센터 머리글)
  - **띠 없애기**: `.w-header::before`(화면 폭 `--card` 띠 + 흐림 + 아래 1px 선)를 지운다. 앱 바는 투명하고 고정(sticky)은 그대로다
  - **왼쪽 알약 `.brand-pill`**: `.lang-btn`과 같은 유리 버튼 모양(44px, `--radius-sm`, `--card` + 흐림 + `--glass-sm`)
    | 화면 | 알약 안 |
    |---|---|
    | 홈 `/home` | 로고 28px + 워드마크 20px. 알약 통째로 홈 링크, RTL에서도 로고 → 글자(`dir="ltr"`) |
    | 그 밖의 근로자 화면 | ← + 로고(로그인하고 프로필까지 있으면 로고가 홈 링크) |
    | 앱 바를 숨기는 화면(S-01, S-03 로그인, 분석 중) | 로고 하나(누를 수 없음) |
  - 언어 버튼은 `margin-inline-start: auto`로 반대쪽 끝에 붙인다(빈 `.title` 자리 채우기를 지운다)
  - `design.md`(유리 표, 앱 바 규칙, 코드 예시, 브랜드 단락, 스플래시), `README.md`·`CLAUDE.md`의 `public/` 목록, `app-front/vite.config.ts` 주석의 파일 이름
- 하지 않는 것
  - 센터 머리글(`.c-header`) 모양. 파일 이름만 바꾼다
  - 하단 119·채팅 버튼(30), 언어 버튼·목록 모양
  - `.w-header button.back` 선택자(app-front의 Android 뒤로 가기가 누른다). 그대로 둔다

## 화면·파일
- 화면: 근로자 전체 앱 바, S-01·S-03 좌측 상단, 스플래시, 브라우저 탭, 센터 머리글 로고
- 이름 바꿈: `public/logo.png` → `public/mark.png`
- 수정: `index.html`, `src/components/WorkerLayout.tsx`, `src/pages/worker/Onboarding.tsx`, `src/pages/center/Center.tsx`, `src/styles.css`, `design.md`, `README.md`, `CLAUDE.md`, `../app-front/vite.config.ts`(주석)
- 부르는 API·새 문구 키: 없음

## 완료 기준
- [x] `npm run build`·`app-front` `npm run build` 통과. `dist/mark.png`가 있고 `logo.png`를 참조하는 코드가 없다
- [x] 360px `/consent` ko·vi·ar: 화면 폭 띠가 없고, 왼쪽 ← + 로고 알약과 오른쪽 언어 버튼이 같은 모양이다. ar은 좌우가 뒤집힌다. 가로 넘침 없음
- [x] S-01·S-03 좌측 상단 로고가 알약 안에 있다
- [x] 홈 알약(로고 + 워드마크)이 ko·ar에서 로고 → 글자 순서다
- [ ] 배포본에서 새 마크가 보인다 — 병합 뒤 사용자가 확인한다(배포 주소는 Vercel 보호로 이 환경에서 열리지 않는다)

## 결과
- 실행(2026-10-31, 브랜치 `frontend/header-pill`)
  - `npm run build` → 통과, `cd app-front && npm run build` → 통과
  - Tailscale 주소로 띄운 `npm run dev`를 헤드리스 Chromium 360px로 확인
    - `/consent` ko·vi·ar: 띠 없음, ← + 로고 알약과 언어 버튼이 같은 높이·둥글기·유리. 앱 바 이미지는 `mark.png`(`naturalWidth` 384). `scrollWidth` 360
    - `/signup` ko: 좌측 상단 로고 알약, 가운데 마크 + 워드마크
    - 홈 알약: `/home`은 Google 로그인이 있어야 들어가므로 `/consent`의 앱 바에 홈과 같은 마크업(링크 알약 + 로고 + 워드마크)을 끼워 ko·ar을 봤다. ar에서 처음에 글자가 로고 앞으로 넘어가 `dir="ltr"`를 달았다
- 결정 사항
  - ←와 로고를 따로 두지 않고 한 알약에 넣었다. 띠가 없어진 고정 앱 바에서 맨 ←는 스크롤되는 글자 위에 그대로 겹치기 때문이다
  - 캐시 문제는 쿼리(`?v=2`)가 아니라 파일 이름으로 풀었다. 참조가 다섯 곳이라 이름 하나를 바꾸는 쪽이 빠뜨릴 곳이 적고, `wordmark.png`와 짝이 맞는다
- 확인하지 못한 것: 실제 `/home`(로그인 뒤), 실제 휴대폰·앱 WebView, 배포본

## 메모
- 배포 주소(`*.vercel.app`)는 302로 막혀 이 환경에서 응답을 직접 보지 못했다. 캐시가 원인이라는 판단은 "새 이름 파일은 보이고 같은 이름 파일만 옛것"이라는 사용자 관찰과 배포 기록에 기댄다
