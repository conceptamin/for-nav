// 맥미니 pm2 앱 설정. backend/deploy/deploy.sh가 UV_BIN·PORT를 넘겨 `pm2 start`로 부른다.
// 프론트 빌드(deploy/static)와 API를 한 주소에서 서빙하고, 모델은 저장소의 modeling/models를 쓴다.
// app.for-nav.com으로 온 요청에는 앱용 웹 빌드(deploy/static-app)를 준다(backlog 22).
const fs = require('node:fs');
const path = require('node:path');

const backend = path.resolve(__dirname, '..');
// LLM 키·DB_PATH 등은 맥미니의 backend/.env에만 둔다. uv run --env-file은 파일이 없으면 실패하므로 있을 때만 넘긴다
const envFile = path.join(backend, '.env');
const envArgs = fs.existsSync(envFile) ? ['--env-file', envFile] : [];

module.exports = {
  apps: [
    {
      name: 'for-nav',
      cwd: backend,
      script: process.env.UV_BIN || 'uv',
      // deploy.sh가 uv sync --no-dev를 마쳤으므로 실행 때는 다시 맞추지 않는다(dev 의존성을 다시 설치하지 않게)
      args: ['run', '--no-sync', ...envArgs, 'fastapi', 'run', 'app/main.py', '--host', '0.0.0.0', '--port', process.env.PORT || '8000'],
      interpreter: 'none',
      env: {
        STATIC_DIR: path.join(__dirname, 'static'),
        // 이 호스트로 온 요청에는 app-front 빌드를 준다. 나머지(www.for-nav.com 등)는 STATIC_DIR
        APP_STATIC_DIR: path.join(__dirname, 'static-app'),
        APP_HOSTS: 'app.for-nav.com',
        MODEL_DIR: path.resolve(backend, '../modeling/models'),
        // LLM 호출 제한(backlog 20). 공개 주소라 .env를 빠뜨려도 켜지게 여기 둔다. 넘으면 LLM 없이 대체 동작으로 응답한다
        LLM_RATE_PER_MIN: '60',
        LLM_DAILY_LIMIT: '3000',
        // Cloudflare 터널(같은 기기, 루프백)이 붙이는 실제 클라이언트 IP
        LLM_CLIENT_IP_HEADER: 'cf-connecting-ip',
      },
      autorestart: true,
      max_restarts: 10,
    },
  ],
};
