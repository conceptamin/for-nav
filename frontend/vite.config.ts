import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// 독립 데모 앱: 백엔드 없이 브라우저 안의 규칙·mock으로 동작한다.
export default defineConfig({
  plugins: [react()],
  server: { port: 5180 },
  preview: { port: 5180 },
});
