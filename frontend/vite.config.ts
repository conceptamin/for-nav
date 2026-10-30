import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// 두 모드로 돈다(README "API 연결").
// - 단독 모드: VITE_API_BASE가 비어 있으면 브라우저 안의 규칙·mock만 쓰고 네트워크 요청이 없다.
// - API 모드: VITE_API_BASE=/api 로 띄우면 아래 프록시가 /api 요청을 백엔드(:8000)로 넘긴다.
//   상담 채팅(WS /api/center/cases/{id}/chat)과 통화 신호(…/call)도 같은 프록시를 지나므로 ws: true를 켠다(backlog 25·26).
export default defineConfig({
  plugins: [react()],
  server: { port: 5180, proxy: { '/api': { target: 'http://localhost:8000', ws: true } } },
  preview: { port: 5180 },
});
