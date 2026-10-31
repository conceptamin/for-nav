import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// frontend/와 같은 두 모드로 돈다(README "API 연결").
// - 단독 모드: VITE_API_BASE가 비어 있으면 브라우저 안의 규칙·mock만 쓰고 네트워크 요청이 없다.
// - API 모드: VITE_API_BASE=/api 로 띄우면 아래 프록시가 /api 요청(WebSocket 포함)을 백엔드(:8000)로 넘긴다.
// 포트는 5181이다(frontend/가 5180). 같은 기계에서 둘을 함께 띄워 비교한다.
export default defineConfig({
  plugins: [react()],
  server: { port: 5181, proxy: { '/api': { target: 'http://localhost:8000', ws: true } } },
  preview: { port: 5181 },
});
