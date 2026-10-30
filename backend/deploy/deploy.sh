#!/usr/bin/env bash
# 맥미니에서 지금 클론으로 프론트를 빌드하고 서버(pm2 앱 for-nav)를 다시 띄운다.
# GitHub Actions(.github/workflows/deploy-backend.yml)가 git pull 뒤 SSH로 부른다. 맥미니에서 직접 돌려도 같다.
# 빌드나 의존성 설치가 실패하면 떠 있는 서버와 정적 파일을 건드리지 않고 멈춘다.
set -eo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DEPLOY_DIR/../.." && pwd)"
PORT="${PORT:-8000}"
NODE_VERSION="${NODE_VERSION:-22}"

# SSH 비대화형 셸은 로그인 설정을 읽지 않는다. uv·Homebrew 위치를 직접 더하고 nvm으로 node·pm2를 고른다.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  # nvm.sh는 set -e 아래에서 중간 반환값으로 멈출 수 있어 잠깐 끈다
  set +e
  . "$NVM_DIR/nvm.sh"
  nvm use "$NODE_VERSION" >/dev/null
  rc=$?
  set -e
  [ "$rc" -eq 0 ] || { echo "nvm use $NODE_VERSION 실패(nvm install $NODE_VERSION 필요)"; exit 1; }
fi
for cmd in node npm uv pm2 curl; do
  command -v "$cmd" >/dev/null || { echo "$cmd 를 찾지 못했다(backend/README.md '맥미니 배포' 준비 참고)"; exit 1; }
done

echo "▶ $(git -C "$ROOT" log -1 --format='%h %s')"

echo "▶ 프론트 빌드(API 모드)"
# 빌드는 새 폴더에 하고 성공한 뒤에 바꿔 끼운다. 실패해도 지금 서빙 중인 static은 그대로다
cd "$ROOT/frontend"
npm ci --no-audit --no-fund
rm -rf "$DEPLOY_DIR/static.next"
VITE_API_BASE=/api npm run build -- --outDir "$DEPLOY_DIR/static.next" --emptyOutDir

echo "▶ 서버 의존성"
cd "$ROOT/backend"
uv sync --frozen --no-dev

echo "▶ 정적 파일 교체"
rm -rf "$DEPLOY_DIR/static.prev"
if [ -d "$DEPLOY_DIR/static" ]; then mv "$DEPLOY_DIR/static" "$DEPLOY_DIR/static.prev"; fi
mv "$DEPLOY_DIR/static.next" "$DEPLOY_DIR/static"

echo "▶ 서버 재시작(pm2 for-nav, 포트 $PORT)"
# 설정 파일의 인자·환경 변수가 바뀌어도 반영되게 지우고 새로 띄운다
pm2 delete for-nav >/dev/null 2>&1 || true
UV_BIN="$(command -v uv)" PORT="$PORT" pm2 start "$DEPLOY_DIR/ecosystem.config.cjs"
pm2 save >/dev/null

echo "▶ 상태 확인"
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
    echo "배포 완료: http://127.0.0.1:$PORT/"
    exit 0
  fi
  sleep 1
done
echo "30초 안에 /api/health가 응답하지 않았다"
pm2 logs for-nav --lines 40 --nostream || true
exit 1
