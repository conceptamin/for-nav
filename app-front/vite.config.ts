import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// 근로자 화면은 frontend/src를 공유 import한다(backlog 02 결정 1-A). 원본이 하나로 남고 frontend/ 수정이 그대로 반영된다.
// - 별칭 @fe → ../frontend/src. tsconfig.json의 paths와 같은 값이다.
// - dedupe: frontend/src 파일이 import하는 react·react-dom·react-router를 이 폴더의 node_modules 하나로 묶는다(React가 둘이면 훅이 깨진다).
// - fs.allow: 개발 서버가 저장소 루트 아래(../frontend)를 서빙할 수 있게 한다.
// - publicDir: 로고·국기(frontend/public)를 같은 절대 경로(/mark.png, /wordmark.png, /flags/*.svg)로 서빙·복사한다.
//
// frontend/와 같은 두 모드로 돈다(README "API 연결").
// - 단독 모드: VITE_API_BASE가 비어 있으면 브라우저 안의 규칙·mock만 쓰고 네트워크 요청이 없다.
// - API 모드: VITE_API_BASE=/api 로 띄우면 아래 프록시가 /api 요청(WebSocket 포함)을 백엔드(:8000)로 넘긴다.
// 포트는 5181이다(frontend/가 5180). 같은 기계에서 둘을 함께 띄워 비교한다.
const root = fileURLToPath(new URL('.', import.meta.url));
const repoRoot = fileURLToPath(new URL('..', import.meta.url));
const frontendSrc = fileURLToPath(new URL('../frontend/src', import.meta.url));

export default defineConfig({
  plugins: [react()],
  root,
  publicDir: fileURLToPath(new URL('../frontend/public', import.meta.url)),
  resolve: {
    alias: { '@fe': frontendSrc },
    dedupe: ['react', 'react-dom', 'react-router'],
  },
  server: {
    port: 5181,
    fs: { allow: [repoRoot] },
    proxy: { '/api': { target: 'http://localhost:8000', ws: true } },
  },
  preview: { port: 5181 },
});
