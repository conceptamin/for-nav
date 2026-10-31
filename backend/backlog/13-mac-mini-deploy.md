# 13. 맥미니 자동 배포

상태: 완료
의존: 08(같은 출처 서빙), 12(모델링 경로 의존성)

## 목표
발표·시연용 서버를 맥미니에 두고, `main`에 병합될 때마다 GitHub Actions가 맥미니에 배포하게 한다. 사용자가 다른 프로젝트에서 쓰는 방식(GitHub 호스트 러너 → `appleboy/ssh-action`으로 맥미니 SSH 2222 → `git pull` → pm2 재시작)을 그대로 따른다(2026-10-30 사용자 요청).

## 범위
- 하는 것
  - `.github/workflows/deploy-backend.yml`: `main` push(백엔드·프론트·모델링 코드·모델 변경, 문서 제외)와 수동 실행. 맥미니 `~/srv/for-nav`(없으면 클론)에서 `git pull --ff-only` 뒤 `deploy.sh`
  - `backend/deploy/deploy.sh`: 프론트 API 모드 빌드를 새 폴더에 → `uv sync --frozen --no-dev` → 정적 파일 교체 → pm2 재시작 → `/api/health` 확인
  - `backend/deploy/ecosystem.config.cjs`: pm2 앱 `for-nav`. `STATIC_DIR`·`MODEL_DIR`을 정하고 `backend/.env`가 있으면 읽는다
  - `backend/README.md` "맥미니 배포": 맥미니 준비와 secrets
- 하지 않는 것
  - 셀프 호스트 러너(공개 저장소라 포크 PR이 맥미니에서 코드를 돌릴 수 있다)
  - 외부 접속(공유기 포트 열기, HTTPS, 도메인)
  - 실패 시 자동 되돌리기. 실패하면 Actions 로그와 `pm2 logs for-nav`를 보고 고친 커밋을 다시 병합한다

## API·파일
API 변경 없음. 위 파일과 `backend/.gitignore`(`deploy/static*/`)

## 완료 기준
- [x] 이 맥북에서 `deploy.sh`를 돌려 pm2 앱이 뜨고 `/api/health`, `/`, `/center`가 응답한다
- [x] secrets 3개를 넣고 Actions에서 "Deploy backend (Mac mini)"를 수동 실행해 성공한다(클론이 없던 맥미니에서 첫 실행)

## 결과
- 이 맥북에서 SSH 비대화형 셸처럼 환경을 비우고 실행: `env -i HOME=$HOME PATH=/usr/bin:/bin NODE_VERSION=24 PORT=8791 bash backend/deploy/deploy.sh` → `배포 완료`. `/api/health`·`/`·`/center` 200, `/assets/nope.js` 404, `POST /api/triage`에 `model`(응급도·진료과 확률)이 붙는다
- 같은 명령을 한 번 더 → pm2 앱을 지우고 다시 띄워 `배포 완료`, 이전 빌드는 `static.prev`로 남는다
- `NODE_VERSION=99`로 실패시킴 → `nvm use 99 실패`로 멈추고(종료 코드 1) 떠 있던 서버는 `/api/health` 그대로 응답
- `uv run ruff check .`, `ruff format --check .` 통과, `uv run pytest` → 2864 passed(서버 코드 변경 없음)
- 맥미니 첫 배포(2026-10-30, secrets 등록 뒤)
  - 첫 실행: 워크플로가 `~/srv/for-nav`를 클론했지만 `uv 를 찾지 못했다`로 멈췄다. 맥미니에 uv를 설치해 풀렸다
  - 다음 실행: 빌드·설치는 끝났지만 서버가 `lightgbm`의 `libomp.dylib`을 찾지 못해 뜨지 않았고, `/api/health` 확인에서 실패해 pm2 로그가 Actions에 찍혔다. Homebrew `libomp`를 설치해 풀렸고 README 준비 목록에 더했다(conceptamin/for-nav#105)
  - 수동 실행 run 41088233141(`a83aa5a`) → 성공. 이후 `main` 병합 5번(#107, #108, #110, #112, #116)의 자동 배포 모두 성공, 마지막 로그 `배포 완료: http://127.0.0.1:8000/`
- 결정
  - 사용자의 다른 프로젝트 워크플로(`appleboy/ssh-action@v1.0.0`, 포트 2222, secrets `MAC_MINI_IP`·`MAC_MINI_USERNAME`·`MAC_MINI_SSH_KEY`)를 그대로 썼다. 같은 secrets 값을 이 저장소에 넣으면 된다
  - `git pull`은 워크플로에서, 빌드·재시작은 `deploy.sh`에서 한다. pull이 실행 중인 스크립트 파일을 바꾸지 않게 하기 위해서다
  - 프론트는 `frontend/dist`가 아니라 `backend/deploy/static.next`에 빌드하고 성공한 뒤 바꿔 끼운다. Vite는 빌드 시작 때 출력 폴더를 비우므로, 그 자리에 바로 빌드하면 실패 시 서빙 중인 화면이 깨진다
  - pm2는 `startOrRestart` 대신 지우고 새로 띄운다. 설정 파일의 인자·환경 변수 변경이 확실히 반영된다
  - 맥미니 경로는 `~/srv/for-nav`로 고정하고 사용자 이름은 쓰지 않는다. 클론이 없으면 워크플로가 공개 HTTPS 주소로 만든다(사용자 요청). 공개 저장소라 pull에 인증이 필요 없다

## 메모
- 맥미니 Node는 nvm 22를 쓴다(Vite 8은 22.12 이상). CI는 Node 24다
