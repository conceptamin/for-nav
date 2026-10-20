import react from '@vitejs/plugin-react';
import { loadEnv } from 'vite';
import { defineConfig } from 'vitest/config';

// 백엔드 origin. VITE_ 접두사가 아니므로 클라이언트 번들에 노출되지 않는다.
export const API_ORIGIN_ENV = 'YARDPILOT_API_ORIGIN';
export const DEFAULT_API_ORIGIN = 'http://127.0.0.1:8000';

export function resolveApiOrigin(value: string | undefined): string {
  const url = new URL(value || DEFAULT_API_ORIGIN);
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new Error(`${API_ORIGIN_ENV}는 http(s) origin이어야 합니다: ${value}`);
  }
  return url.origin;
}

export default defineConfig(({ mode }) => {
  const target = resolveApiOrigin(loadEnv(mode, process.cwd(), '')[API_ORIGIN_ENV]);
  // 더 구체적인 WebSocket 경로를 먼저 둔다. 백엔드가 없으면 Vite proxy가 오류 응답을 돌려준다.
  const proxy = {
    '/api/v1/ws': { target, ws: true },
    '/api': { target },
  };
  return {
    plugins: [react()],
    server: { proxy },
    preview: { proxy },
    test: {
      environment: 'jsdom',
      include: ['src/**/*.test.{ts,tsx}', 'tests/**/*.test.ts'],
      setupFiles: ['src/tests/setup.ts'],
    },
  };
});
