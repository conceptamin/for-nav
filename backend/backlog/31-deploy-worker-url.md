# 31. 맥미니 프론트 빌드에 근로자 화면 주소 넣기

상태: 완료
의존: frontend 58(`VITE_WORKER_URL`)

## 목표
2026-11-01 사용자 요청: 운영 센터 화면(`www.for-nav.com/center`)의 **근로자 화면 열기 ↗**가 센터 홈으로 돌아왔다. Cloudflare가 `www.for-nav.com/`을 `/center`로 302 리디렉션하기 때문이다. frontend 58이 링크 주소를 `VITE_WORKER_URL`로 받게 했으므로, `deploy.sh`의 프론트 빌드에 앱용 웹 호스트 `https://app.for-nav.com/`을 넣는다.

## 범위
- 하는 것
  - `deploy/deploy.sh`의 프론트 빌드(`static.next`)에 `VITE_WORKER_URL=https://app.for-nav.com/`을 넘긴다
  - `README.md` "deploy.sh 흐름" 문장
- 하지 않는 것
  - 앱용 웹(`app-front`) 빌드. 센터 화면이 없다
  - Cloudflare 리디렉션 규칙, 서버 코드

## 완료 기준
- [x] `bash -n deploy/deploy.sh` 통과
- [x] 같은 값으로 빌드한 프론트 번들의 링크가 `https://app.for-nav.com/`이다(frontend 58에서 확인)
- [ ] 맥미니에서 다시 배포한 뒤 `www.for-nav.com/center`의 링크가 `app.for-nav.com`을 연다(병합·배포 뒤 사용자 확인)

## 결과
- `bash -n backend/deploy/deploy.sh` → 통과
- 서버 코드가 바뀌지 않아 `uv run pytest`는 돌리지 않았다
- 결정: 주소를 `.env`가 아니라 스크립트에 둔다. 같은 호스트가 `ecosystem.config.cjs`의 `APP_HOSTS`에도 고정돼 있다

## 메모
- frontend 58이 병합되기 전에 배포해도 값이 쓰이지 않을 뿐 해가 없다. 둘 다 병합한 뒤 배포해야 링크가 바뀐다.
