import type { RouteObject } from 'react-router';
import { ControlPage } from '../features/control/ControlPage';
import { DemoPage } from '../features/demo/DemoPage';
import { DriverPage } from '../features/driver/DriverPage';
import { RunResultPage } from '../features/runs/RunResultPage';
import { AppLayout } from './AppLayout';
import { NotFoundPage } from './NotFoundPage';

// :vehicleId·:runId는 경로 일치에만 쓴다. 권한·조회 근거는 서버 세션이다.
export const routes: RouteObject[] = [
  {
    element: <AppLayout />,
    children: [
      { path: '/driver/:vehicleId', element: <DriverPage /> },
      { path: '/control', element: <ControlPage /> },
      { path: '/demo', element: <DemoPage /> },
      { path: '/runs/:runId', element: <RunResultPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
];
