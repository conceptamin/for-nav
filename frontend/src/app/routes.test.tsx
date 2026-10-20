import { render, screen } from '@testing-library/react';
import { createMemoryRouter } from 'react-router';
import { RouterProvider } from 'react-router/dom';
import { describe, expect, it, vi } from 'vitest';
import { routes } from './routes';

function renderAt(path: string) {
  return render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />);
}

const pages = [
  { path: '/driver/vehicle-7', heading: '운전자 안내' },
  { path: '/control', heading: '관제' },
  { path: '/demo', heading: '시연 관리' },
  { path: '/runs/run-42', heading: '실행 결과' },
  { path: '/', heading: '페이지를 찾을 수 없음' },
  { path: '/control/unknown', heading: '페이지를 찾을 수 없음' },
];

describe('라우트 placeholder', () => {
  it.each(pages)('$path → $heading', async ({ path, heading }) => {
    renderAt(path);
    expect(await screen.findByRole('heading', { level: 1, name: heading })).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.getByRole('main')).toContainElement(screen.getByRole('heading', { level: 1 }));
    expect(document.title).toBe(`${heading} · YardPilot`);
    expect(screen.getByRole('link', { name: '본문 바로가기' })).toHaveAttribute('href', '#main');
  });

  it.each([
    ['/driver/vehicle-secret-7', 'vehicle-secret-7'],
    ['/runs/run-secret-42', 'run-secret-42'],
  ])('%s는 URL 파라미터를 표시하거나 조회에 쓰지 않는다', async (path, param) => {
    const fetch = vi.fn();
    const WebSocket = vi.fn();
    vi.stubGlobal('fetch', fetch);
    vi.stubGlobal('WebSocket', WebSocket);
    const { container } = renderAt(path);
    await screen.findByRole('heading', { level: 1 });
    expect(container.textContent).not.toContain(param);
    expect(document.title).not.toContain(param);
    expect(fetch).not.toHaveBeenCalled();
    expect(WebSocket).not.toHaveBeenCalled();
  });
});
