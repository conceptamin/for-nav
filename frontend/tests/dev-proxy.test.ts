// @vitest-environment node
import { createHash } from 'node:crypto';
import { createServer as createHttpServer, type Server } from 'node:http';
import type { AddressInfo } from 'node:net';
import type { Duplex } from 'node:stream';
import { fileURLToPath } from 'node:url';
import { createServer, type ViteDevServer } from 'vite';
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';
import { API_ORIGIN_ENV, DEFAULT_API_ORIGIN, resolveApiOrigin } from '../vite.config';

const root = fileURLToPath(new URL('..', import.meta.url));
const WS_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11';

function port(server: Server | null | undefined): number {
  return (server!.address() as AddressInfo).port;
}

async function listen(server: Server): Promise<number> {
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  return port(server);
}

// 실제 vite.config.ts로 dev server를 띄운다. 대상 origin은 환경 변수로만 바꾼다.
async function startVite(apiOrigin: string): Promise<ViteDevServer> {
  process.env[API_ORIGIN_ENV] = apiOrigin;
  try {
    const vite = await createServer({
      root,
      configFile: `${root}/vite.config.ts`,
      logLevel: 'silent',
      server: { host: '127.0.0.1', port: 0, strictPort: true },
    });
    return await vite.listen();
  } finally {
    delete process.env[API_ORIGIN_ENV];
  }
}

describe('resolveApiOrigin', () => {
  it('기본값은 로컬 loopback이다', () => {
    expect(resolveApiOrigin(undefined)).toBe(DEFAULT_API_ORIGIN);
    expect(resolveApiOrigin('')).toBe(DEFAULT_API_ORIGIN);
    expect(new URL(DEFAULT_API_ORIGIN).hostname).toBe('127.0.0.1');
  });

  it('환경 변수 값을 origin으로 정규화한다', () => {
    expect(resolveApiOrigin('http://10.0.0.5:9000/ignored/path')).toBe('http://10.0.0.5:9000');
  });

  it('http(s)가 아니거나 URL이 아니면 거부한다', () => {
    expect(() => resolveApiOrigin('ws://127.0.0.1:8000')).toThrow(API_ORIGIN_ENV);
    expect(() => resolveApiOrigin('not a url')).toThrow();
  });
});

describe('dev server proxy', () => {
  let vite: ViteDevServer | undefined;

  afterEach(async () => {
    await vite?.close();
    vite = undefined;
  });

  describe('백엔드가 켜져 있을 때', () => {
    const upgrades: string[] = [];
    const sockets: Duplex[] = [];
    const backend = createHttpServer((req, res) => {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ path: req.url, from: 'backend' }));
    });
    backend.on('upgrade', (req, socket) => {
      upgrades.push(req.url ?? '');
      sockets.push(socket);
      const accept = createHash('sha1').update(`${req.headers['sec-websocket-key']}${WS_GUID}`).digest('base64');
      socket.write(`HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ${accept}\r\n\r\n`);
    });
    let origin = '';

    beforeAll(async () => {
      origin = `http://127.0.0.1:${await listen(backend)}`;
    });
    afterAll(async () => {
      // upgrade된 소켓은 closeAllConnections 대상이 아니므로 직접 닫는다.
      sockets.forEach((socket) => socket.destroy());
      backend.closeAllConnections();
      await new Promise((resolve) => backend.close(resolve));
    });

    it('/api HTTP 요청을 백엔드로 전달한다', async () => {
      vite = await startVite(origin);
      const res = await fetch(`http://127.0.0.1:${port(vite.httpServer as Server)}/api/v1/health`);
      expect(res.status).toBe(200);
      expect(await res.json()).toEqual({ path: '/api/v1/health', from: 'backend' });
    });

    it('/api/v1/ws WebSocket upgrade를 백엔드로 전달한다', async () => {
      vite = await startVite(origin);
      const ws = new WebSocket(`ws://127.0.0.1:${port(vite.httpServer as Server)}/api/v1/ws`);
      await new Promise<void>((resolve, reject) => {
        ws.addEventListener('open', () => resolve());
        ws.addEventListener('error', () => reject(new Error('WebSocket open 실패')));
      });
      ws.close();
      expect(upgrades).toEqual(['/api/v1/ws']);
    });
  });

  it('백엔드가 꺼져 있어도 기동되고 /api는 index.html이 아닌 proxy 오류로 응답한다', async () => {
    const closed = createHttpServer();
    const closedPort = await listen(closed);
    await new Promise((resolve) => closed.close(resolve));

    vite = await startVite(`http://127.0.0.1:${closedPort}`);
    const base = `http://127.0.0.1:${port(vite.httpServer as Server)}`;

    const api = await fetch(`${base}/api/v1/health`);
    const apiBody = await api.text();
    expect(api.status).toBe(502);
    expect(api.headers.get('content-type') ?? '').not.toContain('text/html');
    expect(apiBody).not.toContain('<div id="root">');

    // 대조군: 일반 경로는 SPA index.html로 응답한다.
    const spa = await fetch(`${base}/control`);
    expect(spa.headers.get('content-type')).toContain('text/html');
    expect(await spa.text()).toContain('<div id="root">');
  });
});
