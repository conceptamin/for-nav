# 22. app.for-nav.com에 앱용 웹(app-front) 빌드 서빙

상태: 진행 중
의존: 없음 (app-front 02 완료, PR #117. Flutter 앱 쪽은 app-front 03, PR #119)

## 목표
맥미니는 `frontend/` 빌드 하나(`STATIC_DIR`)를 `www.for-nav.com`과 `app.for-nav.com`에 똑같이 서빙한다. Flutter 앱(app-front 03)이 `app.for-nav.com`을 불러오면 다리(`src/bridge/`)가 없는 화면이라, `init`을 받지 못해 Android에서 상태 표시줄·하단 제스처 바와 겹치고 뒤로 가기가 어느 화면에서든 앱을 닫는다(2026-10-31 에뮬레이터에서 확인). 요청의 호스트가 `app.for-nav.com`이면 `app-front` 빌드를 주고, 나머지(`www.` 등)는 지금처럼 `frontend/` 빌드를 준다. `app-front`는 호스트가 없는 브라우저에서도 같은 근로자 화면이라, 브라우저로 `app.`에 오던 사용자에게는 달라지는 것이 없다.

## 결정이 필요한 것

1. **어느 호스트에서 앱용 빌드를 주나.** → **권장대로 `Host` 헤더로 결정(2026-10-31).** 권장: 요청의 `Host` 헤더(포트를 뗀 소문자)가 `APP_HOSTS` 목록에 있으면. Cloudflare 터널은 기본으로 공개 주소의 `Host`를 그대로 넘긴다(터널 설정에 `httpHostHeader`가 없을 때). 배포 뒤 `curl`로 확인한다. 대안: `X-Forwarded-Host`(터널이 `Host`를 바꾸게 설정돼 있을 때만 필요. 같은 망에서 직접 붙은 클라이언트가 꾸밀 수 있어 `LLM_CLIENT_IP_HEADER`처럼 루프백일 때만 믿어야 한다).
2. **앱용 빌드가 없을 때.** → **권장대로 결정(2026-10-31).** 권장: `APP_STATIC_DIR`이 비어 있으면 지금과 똑같이 모든 호스트에 `STATIC_DIR`을 준다(로컬·테스트 기본값이 바뀌지 않게). `APP_STATIC_DIR`을 주었는데 `index.html`이 없거나 `APP_HOSTS`가 비어 있으면 시작 때 거절한다(`STATIC_DIR`과 같은 방식).
3. **배포 실패의 단위.** → **권장대로 결정(2026-10-31).** 권장: `deploy.sh`가 `frontend/`와 `app-front/`를 둘 다 새 폴더에 빌드하고, **둘 다 성공한 뒤에만** 바꿔 끼운다. 하나라도 실패하면 지금 서빙 중인 두 폴더와 서버를 건드리지 않는다(지금의 "실패해도 static은 그대로"를 두 폴더로 넓힌다).

## 범위
- 하는 것
  - 설정(`app/settings.py`): `APP_STATIC_DIR`(`index.html`이 있는 폴더, 기본 없음), `APP_HOSTS`(쉼표 구분 호스트 이름, 기본 없음). 결정 2의 검증
  - 서빙(`app/main.py` `mount_frontend`): 호스트가 `APP_HOSTS`에 있고 `APP_STATIC_DIR`이 있으면 그 폴더, 아니면 `STATIC_DIR`. 있는 파일·SPA 경로 → `index.html`·확장자 있는 없는 경로 404·폴더 밖 차단·`/api` 우선은 두 폴더 모두 지금 규칙 그대로
  - 배포(`deploy/deploy.sh`): `app-front`도 `VITE_API_BASE=/api`로 `deploy/static-app.next`에 빌드, 결정 3대로 둘 다 성공한 뒤 `static`·`static-app`을 함께 교체
  - pm2(`deploy/ecosystem.config.cjs`): `APP_STATIC_DIR=deploy/static-app`, `APP_HOSTS=app.for-nav.com`
  - 배포 워크플로(`.github/workflows/deploy-backend.yml`): `paths`에 `app-front/**`. 앱용 웹만 바뀐 병합도 맥미니에 배포되게
  - 테스트(`tests/test_static.py`): 호스트별 폴더 선택, 대소문자·포트가 붙은 `Host`, `APP_STATIC_DIR` 없을 때 지금과 같음, 두 폴더 모두 폴더 밖 차단·`/api` 우선, 설정 검증
  - `README.md`: 환경 변수 표, 폴더 구조(`static-app`), "맥미니 배포"
- 하지 않는 것
  - Cloudflare 설정 변경. `app.`·루트의 `/center*` → `www.` 리디렉션 규칙은 그대로 둔다(앱용 빌드에는 센터 경로가 없다)
  - `/app/` 같은 하위 경로 서빙(app-front README 결정 2의 다른 안)
  - Flutter 앱의 배포 주소 설정(`app/env/prod.json` 등). `app/`이 main에 들어온 뒤(PR #119) app 쪽 작업으로 한다
  - `frontend/`·`app-front/` 코드 변경

## API·파일
- API: 변경 없음. `/api/*`는 호스트와 관계없이 같다
- 환경 변수: `APP_STATIC_DIR`, `APP_HOSTS`(새로, 선택)
- 고치는 파일: `app/settings.py`, `app/main.py`, `deploy/deploy.sh`, `deploy/ecosystem.config.cjs`, `.github/workflows/deploy-backend.yml`, `tests/test_static.py`, `README.md`

## 완료 기준
- [x] `uv run ruff check . && uv run ruff format --check .`, `uv run pytest` 통과
- [x] 로컬에서 `STATIC_DIR=../frontend/dist APP_STATIC_DIR=../app-front/dist APP_HOSTS=app.localhost`로 띄우면 `curl -H 'Host: app.localhost' /`의 번들에 `fornav`가 있고, `Host: localhost`의 번들에는 없다. 두 호스트 모두 `/api/health`가 200
- [x] `APP_STATIC_DIR`을 빼고 띄우면 두 호스트 모두 지금과 같은 `frontend/` 빌드
- [x] `deploy.sh`에서 `app-front` 빌드를 일부러 실패시키면(예: 없는 `outDir` 부모) `static`·`static-app`·떠 있는 서버가 그대로다
- [ ] 맥미니 배포 뒤 `https://app.for-nav.com/` 번들에 `fornav`가 있고, `https://www.for-nav.com/center`는 지금처럼 센터 화면이다
- [ ] Flutter 앱(`APP_URL=https://app.for-nav.com`)을 Android 에뮬레이터에서 열면 `/__host`가 "호스트 있음·init 받음"이고, 동의 화면에서 뒤로 가기가 한 화면 뒤로 간다

## 결과

2026-10-31. 브랜치 `backend/app-host-static`. 코드·로컬 확인은 끝났고, **맥미니 배포 뒤 확인(완료 기준 마지막 두 줄)이 남아 상태는 "진행 중"이다.**

실행한 명령
- `uv run ruff check . && uv run ruff format --check .` → 통과
- `uv run pytest` → 3116개 통과(`tests/test_static.py` 29개, 이 항목에서 더한 것: 앱 호스트 3가지 표기 × 경로 3개, 다른 호스트 4개, 자산이 고른 빌드에서만 나옴, 두 빌드 모두 `/api` 우선·폴더 밖 차단, 설정 검증)
- 로컬 서버(`frontend`·`app-front`를 `VITE_API_BASE=/api`로 빌드, 포트 8022)
  - `STATIC_DIR=../frontend/dist APP_STATIC_DIR=../app-front/dist APP_HOSTS=app.localhost`: `Host: app.localhost`·`App.Localhost:8022` → app-front 번들(`fornav` 있음), `Host: localhost`·`www.for-nav.com` → frontend 번들(`fornav` 없음). 모두 `/api/health` 200
  - `STATIC_DIR`만: 두 호스트 모두 frontend 번들. 지금 운영 번들(`index-BIDAbrPk.js`)과 같은 해시다
- `deploy.sh`: 임시 루트에 복사하고 `npm`·`uv`·`pm2`·`curl`을 가짜로 바꿔(`$HOME/.local/bin`이 PATH 맨 앞) 돌렸다
  - app-front 빌드 실패 → 종료 코드 1, `static`·`static-app` 그대로, `uv`·`pm2` 호출 0번
  - 둘 다 성공 → 두 폴더가 함께 새 빌드로, 이전 것은 `static.prev`·`static-app.prev`, `pm2 delete`·`start`·`save` 뒤 "배포 완료"

API: 변경 없음. 환경 변수 `APP_STATIC_DIR`·`APP_HOSTS`를 더했다(선택, 기본 없음).

결정과 이유
- 결정 1~3은 권장대로(위 `## 결정이 필요한 것`)
- 호스트 이름은 Starlette `request.url.hostname`(Host 헤더에서 포트를 떼고 소문자)으로 읽는다. `app.for-nav.com.evil.test` 같은 앞부분만 같은 호스트는 앱용 빌드를 받지 않는다(테스트)
- `APP_STATIC_DIR`은 `STATIC_DIR`이 있어야 쓸 수 있다. 앱 호스트가 아닌 요청에 줄 빌드가 없으면 `/`가 404가 되기 때문이다
- 설정 테스트는 기존 `STATIC_DIR` 검증 테스트가 있는 `tests/test_static.py`에 두었다(`tests/test_settings.py`는 고치지 않음)
- `deploy-backend.yml`의 `paths`에 `app-front/**`를 더했다. `.github/`는 `chore/` 영역이지만 이 항목이 동작하는 데 꼭 필요한 한 줄이라 같은 PR에 넣었다

남은 것(병합·배포 뒤)
- `curl -s https://app.for-nav.com/`의 번들에 `fornav`가 있고 `https://www.for-nav.com/center`가 센터 화면인지. `app.`이 여전히 frontend 번들이면 터널이 `Host`를 바꾸는 것이다(결정 1의 대안)
- Flutter 앱(`APP_URL=https://app.for-nav.com`)을 Android 에뮬레이터에서 열어 `/__host`와 뒤로 가기

## 메모
- 브라우저로 `app.for-nav.com`에 오는 사용자도 앱용 빌드를 받는다. 화면·문구는 같다(`app-front/CLAUDE.md` "호스트가 없어도 똑같이 동작한다"). 다른 점은 `app-front`에 센터 경로가 없어, 앱 안에서 `/center`로 가는 라우터 링크가 `/`로 돌아간다는 것이다(전체 페이지로 열면 Cloudflare가 `www.`으로 보낸다)
- Google 로그인 승인 원본에는 이미 `https://app.for-nav.com`이 있다(README "근로자 Google 로그인"). 출처가 같으므로 바꿀 것이 없다. WebView 안의 Google 로그인은 별도 문제다(app-front 06, PR #123)
