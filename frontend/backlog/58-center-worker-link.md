# 58. 센터 "근로자 화면 열기" 링크를 운영 근로자 주소로

상태: 완료
의존: 없음

## 목표
2026-11-01 사용자 요청: 운영(`www.for-nav.com/center`)에서 센터 머리글의 **근로자 화면 열기 ↗**를 누르면 근로자 화면이 아니라 센터 홈이 열렸다. 링크가 같은 출처의 `/`인데 Cloudflare가 `www.for-nav.com/`을 `/center`로 302 리디렉션하기 때문이다(backlog 27 메모). 링크 주소를 빌드 환경 변수로 바꿀 수 있게 해 운영에서는 `https://app.for-nav.com/`을 열게 한다.

## 범위
- 하는 것
  - `VITE_WORKER_URL`을 더하고 센터 머리글 링크가 이 값을 쓴다. 비어 있으면 지금처럼 `/`다(로컬·단독 모드·Vercel은 그대로)
- 하지 않는 것
  - Cloudflare 리디렉션 규칙 바꾸기
  - 맥미니 빌드에 값 넣기(`backend/deploy/deploy.sh`, `backend/` 몫). 메모 참고

## 화면·파일
- C-01~C-03 머리글: `src/pages/center/Center.tsx`
- `src/vite-env.d.ts`(`VITE_WORKER_URL` 타입), `README.md` 실행 안내, `backlog/27-center-login.md` 메모

## 완료 기준
- [x] `npm run build` 통과
- [x] 값 없이 띄운 `/center`에서 링크가 지금처럼 `/`다
- [x] `VITE_WORKER_URL=https://app.for-nav.com/`로 띄운 `/center`에서 링크가 `https://app.for-nav.com/`이다

## 결과
- `npm run build` → 통과(기존 청크 크기 경고만)
- 단독 모드 `http://localhost:5180/center`: **근로자 화면 열기 ↗**의 `href`가 `/`(지금과 같다)
- `VITE_WORKER_URL=https://app.for-nav.com/`로 빌드한 번들: 링크 `href`가 `https://app.for-nav.com/`을 담은 상수다
- 확인한 원인: `curl -I https://www.for-nav.com/` → `302 location: https://www.for-nav.com/center`(Cloudflare)
- 결정: 링크를 빼지 않고 환경 변수로 둔다. 비우면 `/`라 로컬·Vercel 동작은 바뀌지 않는다

## 메모
- 운영에 반영하려면 `backend/deploy/deploy.sh`의 프론트 빌드(`static.next`) 줄에 `VITE_WORKER_URL=https://app.for-nav.com/`을 더하고 맥미니에서 다시 배포해야 한다. `app.for-nav.com`은 `ecosystem.config.cjs`의 `APP_HOSTS`와 같은 호스트다. 앱용 웹(`app-front`) 빌드에는 센터 화면이 없으므로 넣지 않는다.
