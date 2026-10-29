# 11. 화면의 "데모" 표시 지우기

상태: 완료(브라우저 확인은 PR 검토에서)
의존: 없음

## 목표
시연 영상을 찍을 때 화면 어디에도 "데모"(Demo, Bản thử)가 보이지 않게 한다. 지금은 근로자 앱 바 배지, 브라우저 탭 제목, S-01 각주 링크, S-03 로그인 각주, 센터 헤더 알약, 센터 초기화 버튼, 통계 각주 일곱 곳에 있다. 표시만 지우고 동작(접수함 초기화, 데모 로그인이 서버에 가지 않는 것)은 그대로 둔다. 빌드 플래그로 켜고 끄지 않고 아예 없앤다. 단독 모드가 데모라는 사실은 `README.md`가 적고 있으므로 화면이 말할 필요가 없다.

## 범위
- 하는 것
  - `index.html` `<title>`: `울산 외국인 의료 내비게이터 (데모)` → `울산 외국인 의료 내비게이터`
  - `WorkerLayout`: 앱 바의 `.badge`(Demo) 삭제. i18n `demoBadge` 키를 en·vi·ko에서 지운다. 쓰는 곳이 없어진 `.badge` 클래스는 `styles.css`에서 지우고 `design.md` 컴포넌트 표(`.footer-note, .muted, .small, .badge` 행)와 `--on-brand-soft` 설명("헤더 데모 배지"), 글자 표의 "예외는 헤더의 Demo 배지(0.72rem)"를 고친다
  - S-01 `/` 각주 링크 `센터 상담원 화면(데모) →` → `센터 상담원 화면 →`(언어를 고르기 전 화면이라 한국어 고정 그대로). 쓰이지 않는 i18n `centerDemoLink` 키는 en·vi·ko에서 지운다
  - S-03 `/signup` 각주 `loginDemoNote`: "데모입니다" 앞머리를 빼고 사실만 남긴다 — ko `이 버튼은 Google에 연결하지 않고, 이 휴대폰에 회원 프로필만 만듭니다.`(en·vi도 같은 뜻). 각주 자체는 남긴다(`design.md` 온보딩 표 "각주로 데모임을 알린다" → "각주로 Google에 연결하지 않음을 알린다")
  - 센터 `CenterLayout` 헤더의 `데모 · 로그인 생략` 알약 삭제
  - C-01 초기화: 버튼 `데모 초기화` → `접수함 초기화`, 확인 문구 `데모로 전송한 사례와 상태 변경을 모두 지울까요?` → `전송된 사례와 상태 변경을 모두 지울까요?`, 실패 문구 `resetFailed` → `접수함을 초기화하지 못했습니다. 서버 연결을 확인해 주세요.`
  - C-03 각주 `데모 mock 익명 집계입니다.` → `익명 집계입니다.`(뒤 문장은 그대로)
  - `README.md` "실행"의 "**데모 초기화** 버튼"과 `design.md`의 "데모 초기화" 언급(`.notice.danger.with-retry` 행, "하지 않는 것"의 `window.confirm` 예)을 새 이름으로 고친다
- 하지 않는 것
  - 코드 주석·함수 이름(`resetDemo`, `resetCenterDemoLocal`)·API 경로 `/api/center/reset`·백엔드. 화면에 보이지 않는다
  - 앱 이름 바꾸기, 로고 넣기. 명칭·로고는 별도 항목이다
  - 단독 모드 자체를 숨기거나 mock 사례를 지우기. 접수함의 mock 24건은 그대로 보인다

## 화면·파일
- 화면: S-01 `/`, S-03 `/signup`, 근로자 전체 앱 바, C-01 `/center`, C-03 `/center/stats`, 브라우저 탭 제목
- 수정: `index.html`, `src/components/WorkerLayout.tsx`, `src/pages/worker/Onboarding.tsx`, `src/pages/center/Center.tsx`, `src/i18n/{en,vi,ko}.ts`, `src/styles.css`, `README.md`, `design.md`
- 지우는 문구 키: `demoBadge`, `centerDemoLink`. 바꾸는 문구 키: `loginDemoNote`. 새 키 없음

## 완료 기준
- [x] `npm run build` 통과
- [x] 브라우저 탭 제목에 `(데모)`가 없다
- [ ] 단독 모드 en·vi·ko에서 `/`, `/consent`, `/signup`, `/home`, `/intake`의 앱 바와 각주에 `데모`·`Demo`·`demo`·`Bản thử`가 없다
- [ ] `/center`, `/center/cases/:id`, `/center/stats`에 `데모` 글자가 없다
- [ ] `접수함 초기화`가 단독 모드와 API 모드(`VITE_API_BASE=/api`) 둘 다에서 지금처럼 전송 사례와 상태 변경을 지운다. API 모드에서 서버를 끄면 `.notice.danger.with-retry`에 새 실패 문구가 뜬다
- [x] `grep -rn "데모\|Demo\|demo\|Bản thử" index.html src/i18n src/pages src/components` 결과가 주석과 함수·변수 이름뿐이다
- [ ] 360px en·vi·ko에서 앱 바 오른쪽(언어 선택)이 배지 없이도 제자리이고 가로 넘침 없음

## 결과
- 실행(2026-10-29, 브랜치 `frontend/demo-label`)
  - `npm run build` → 통과
  - `grep -rn "데모\|Demo\|demo\|Bản thử" index.html src/i18n src/pages src/components` → 주석 3곳, `resetDemo` import·호출, i18n 키 이름 `loginDemoNote`뿐. 화면 문구 없음
  - 빌드 결과물 `dist/assets/*.js`에서 같은 패턴 → 키 이름 `loginDemoNote`만 남음(화면에 보이지 않는다). `접수함 초기화`·`센터 상담원 화면 →`·`익명 집계입니다`는 들어 있음
  - 단독 모드 개발 서버의 `<title>` → `울산 외국인 의료 내비게이터`
- 확인하지 못한 것: Chrome 확장이 연결되지 않고 헤드리스 브라우저도 없어 360px en·vi·ko 앱 바 모양, 센터 화면, API 모드의 초기화 실패 문구는 눈으로 보지 못했다. 완료 기준의 남은 네 칸은 PR 검토 때 브라우저에서 본다. 바뀐 것이 문구 삭제·치환뿐이라 배치는 앱 바 오른쪽의 배지 하나가 빠진 것 외에 같다
- 결정 사항
  - i18n 키 이름 `loginDemoNote`와 함수 `resetDemo`·`resetCenterDemoLocal`, API 경로 `/api/center/reset`은 그대로 둔다. 화면에 보이지 않고, 백엔드를 건드리지 않기 위해서다
  - `.badge`는 쓰는 곳이 없어져 `styles.css`에서 지웠다. `--on-brand-soft`는 홈 첫 메뉴 아이콘 칸이 아직 써서 남긴다
  - `design.md` 온보딩 표의 S-03 설명은 "데모 로그인"이라는 개념 설명은 남기고, 각주가 알리는 내용만 "Google에 연결하지 않음"으로 바꿨다

## 메모
- 2026-10-29 프론트 피드백 4번("데모 표시 삭제(시연 영상 촬영시)")에서 왔다. 1번(명칭)·3번(로고)은 결정이 필요해 별도 항목으로, 2번(홈·개인 화면)은 12번이다
- `loginDemoNote`의 베트남어는 원어민 검수가 필요하다
- 뒤에 로고가 들어오면 앱 바 왼쪽의 앱 이름 자리에 놓인다. 배지가 빠져 자리가 생긴다
