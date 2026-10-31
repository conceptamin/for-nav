#!/usr/bin/env bash
# 맥미니에서 지금 클론으로 프론트(frontend)와 앱용 웹(app-front)을 빌드하고 서버(pm2 앱 for-nav)를 다시 띄운다.
# GitHub Actions(.github/workflows/deploy-backend.yml)가 git pull 뒤 SSH로 부른다. 맥미니에서 직접 돌려도 같다.
# 빌드나 의존성 설치가 하나라도 실패하면 떠 있는 서버와 정적 파일(static, static-app)을 건드리지 않고 멈춘다.
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

# backend/.env에서 값 하나를 읽는다. 공백이 든 값(MAIL_FROM 등)이 있어 source하지 않고 그 줄만 읽는다. 없거나 비면 빈 값이다
env_value() {
  [ -f "$ROOT/backend/.env" ] || return 0
  sed -nE "s/^[[:space:]]*(export[[:space:]]+)?$1[[:space:]]*=[[:space:]]*//p" "$ROOT/backend/.env" | tail -n 1 | sed -E "s/[[:space:]]+\$//; s/^[\"'](.*)[\"']\$/\\1/"
}

# 근로자 Google 로그인(backlog 21): 서버가 aud와 비교하는 웹 클라이언트 ID를 두 빌드에도 같은 값으로 넣는다
GOOGLE_CLIENT_ID="$(env_value GOOGLE_CLIENT_ID)"
echo "▶ Google 클라이언트 ID: $([ -n "$GOOGLE_CLIENT_ID" ] && echo 있음 || echo 없음)"

echo "▶ 프론트 빌드(API 모드)"
# 빌드는 새 폴더에 하고 성공한 뒤에 바꿔 끼운다. 실패해도 지금 서빙 중인 static은 그대로다
cd "$ROOT/frontend"
npm ci --no-audit --no-fund
rm -rf "$DEPLOY_DIR/static.next"
VITE_API_BASE=/api VITE_GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID" npm run build -- --outDir "$DEPLOY_DIR/static.next" --emptyOutDir

echo "▶ 앱용 웹 빌드(API 모드, app.for-nav.com에 서빙)"
# frontend/src를 공유 import하지만 react 등은 app-front의 node_modules만 쓴다(app-front backlog 02)
cd "$ROOT/app-front"
npm ci --no-audit --no-fund
rm -rf "$DEPLOY_DIR/static-app.next"
VITE_API_BASE=/api VITE_GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID" npm run build -- --outDir "$DEPLOY_DIR/static-app.next" --emptyOutDir

echo "▶ 서버 의존성"
cd "$ROOT/backend"
uv sync --frozen --no-dev

echo "▶ 정적 파일 교체"
# 두 빌드가 모두 성공한 뒤에만 여기 온다. 둘을 함께 바꿔 끼운다
for name in static static-app; do
  rm -rf "$DEPLOY_DIR/$name.prev"
  if [ -d "$DEPLOY_DIR/$name" ]; then mv "$DEPLOY_DIR/$name" "$DEPLOY_DIR/$name.prev"; fi
  mv "$DEPLOY_DIR/$name.next" "$DEPLOY_DIR/$name"
done

# 푸시 발송(backend 28)이 켜졌는지 Actions 로그에서 보이게, 재시작 전 pm2 로그의 줄 수를 적어 둔다.
# 서버는 PUSH=fcm인데 값이 빠졌거나 키 파일을 못 읽으면 시작할 때 "push off: …" 한 줄(값 이름·예외 종류만)을 남긴다
PM2_LOGS=("$HOME/.pm2/logs/for-nav-out.log" "$HOME/.pm2/logs/for-nav-error.log")
log_lines() { if [ -f "$1" ]; then wc -l <"$1" | tr -d ' '; else echo 0; fi; }
LOG_START=("$(log_lines "${PM2_LOGS[0]}")" "$(log_lines "${PM2_LOGS[1]}")")

# 이번에 띄운 서버의 푸시 발송 상태. .env의 PUSH와, 재시작 뒤 새로 쌓인 로그의 "push off" 줄로 본다
push_status() {
  local mode off=""
  mode="$(env_value PUSH)"
  if [ "$mode" != "fcm" ]; then
    echo "꺼짐(PUSH=${mode:-off})"
    return
  fi
  for i in 0 1; do
    [ -f "${PM2_LOGS[$i]}" ] || continue
    off="$(tail -n +"$((LOG_START[i] + 1))" "${PM2_LOGS[$i]}" | grep -m 1 -o 'push off: .*' || true)"
    [ -n "$off" ] && break
  done
  if [ -n "$off" ]; then echo "꺼짐($off)"; else echo "켜짐(FCM)"; fi
}

echo "▶ 서버 재시작(pm2 for-nav, 포트 $PORT)"
# 설정 파일의 인자·환경 변수가 바뀌어도 반영되게 지우고 새로 띄운다
pm2 delete for-nav >/dev/null 2>&1 || true
UV_BIN="$(command -v uv)" PORT="$PORT" pm2 start "$DEPLOY_DIR/ecosystem.config.cjs"
pm2 save >/dev/null

echo "▶ 상태 확인"
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
    sleep 1 # pm2가 시작 로그를 파일에 쓸 틈
    echo "▶ 푸시 발송: $(push_status)"
    echo "배포 완료: http://127.0.0.1:$PORT/"
    exit 0
  fi
  sleep 1
done
echo "30초 안에 /api/health가 응답하지 않았다"
pm2 logs for-nav --lines 40 --nostream || true
exit 1
