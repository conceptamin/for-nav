// 맥미니 pm2 앱 설정. backend/deploy/deploy.sh가 UV_BIN·PORT를 넘겨 `pm2 start`로 부른다.
// 프론트 빌드(deploy/static)와 API를 한 주소에서 서빙하고, 모델은 저장소의 modeling/models를 쓴다.
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
        MODEL_DIR: path.resolve(backend, '../modeling/models'),
      },
      autorestart: true,
      max_restarts: 10,
    },
  ],
};
