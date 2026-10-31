import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import type { RouteObject } from 'react-router';
import { createBrowserRouter, Navigate } from 'react-router';
import { RouterProvider } from 'react-router/dom';
import { installHost } from './bridge/host';
import { HostProvider } from './bridge/HostProvider';
import { installLinkInterceptor } from './bridge/links';
import { HostCheckPage } from './pages/HostCheck';
import './styles.css';

// 다리는 렌더보다 먼저 선다. 호스트가 있으면 여기서 ready가 나간다(README "호스트 계약").
installHost();
installLinkInterceptor();

// 근로자 화면(S-01~S-13, /guide)은 backlog 02에서 frontend/와 같은 경로로 들어온다. 센터 화면(/center*)은 이 앱에 없다.
const routes: RouteObject[] = [
  { path: '/__host', element: <HostCheckPage /> }, // 호스트 연결 확인(개발용)
  { path: '*', element: <Navigate to="/__host" replace /> },
];

const root = document.getElementById('root');
if (!root) throw new Error('#root 요소가 없습니다');

createRoot(root).render(
  <StrictMode>
    <HostProvider>
      <RouterProvider router={createBrowserRouter(routes)} />
    </HostProvider>
  </StrictMode>,
);
