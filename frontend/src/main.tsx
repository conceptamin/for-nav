import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import type { RouteObject } from 'react-router';
import { createBrowserRouter, Navigate } from 'react-router';
import { RouterProvider } from 'react-router/dom';
import { WorkerLayout } from './components/WorkerLayout';
import { CaseDetailPage, CenterLayout, InboxPage, StatsPage } from './pages/center/Center';
import { CenterLoginPage } from './pages/center/Login';
import { CenterRequestPage, GuidePage, MyPage } from './pages/worker/CenterRequest';
import { CoveragePage } from './pages/worker/Coverage';
import { EmergencyPage, IntakePage, ResultPage } from './pages/worker/Intake';
import { ConsentPage, HomePage, LanguagePage, SignupPage } from './pages/worker/Onboarding';
import { ReportBuilderPage, ReportViewPage } from './pages/worker/Report';
import { CallPage, DeskPage } from './pages/worker/Visit';
import { AppStateProvider } from './state/AppState';
import './styles.css';

// PRD 8장 화면 목록과 같은 경로를 쓴다. 근로자(모바일)와 센터(PC)를 한 웹앱 안에서 경로로 나눈다.
const routes: RouteObject[] = [
  {
    element: <WorkerLayout />,
    children: [
      { path: '/', element: <LanguagePage /> }, // S-01
      { path: '/consent', element: <ConsentPage /> }, // S-02
      { path: '/signup', element: <SignupPage /> }, // S-03
      { path: '/home', element: <HomePage /> }, // S-04
      { path: '/intake', element: <IntakePage /> }, // S-05
      { path: '/emergency', element: <EmergencyPage /> }, // S-06
      { path: '/result', element: <ResultPage /> }, // S-07
      { path: '/coverage', element: <CoveragePage /> }, // S-08
      { path: '/visit/desk', element: <DeskPage /> }, // S-09
      { path: '/visit/call', element: <CallPage /> }, // S-10
      { path: '/report/new', element: <ReportBuilderPage /> }, // S-11 항목 선택
      { path: '/report/:id', element: <ReportViewPage /> }, // S-11 리포트
      { path: '/center-request', element: <CenterRequestPage /> }, // S-12
      { path: '/my', element: <MyPage /> }, // S-13
      { path: '/guide', element: <GuidePage /> },
    ],
  },
  {
    element: <CenterLayout />,
    children: [
      { path: '/center', element: <InboxPage /> }, // C-01
      { path: '/center/cases/:id', element: <CaseDetailPage /> }, // C-02
      { path: '/center/stats', element: <StatsPage /> }, // C-03
    ],
  },
  // 센터 로그인은 CenterLayout 밖이다(로그인 전에는 머리글 메뉴·접수함 폴링이 돌지 않는다, backlog 27)
  { path: '/center/login', element: <CenterLoginPage /> }, // C-00
  { path: '*', element: <Navigate to="/" replace /> },
];

const root = document.getElementById('root');
if (!root) throw new Error('#root 요소가 없습니다');

createRoot(root).render(
  <StrictMode>
    <AppStateProvider>
      <RouterProvider router={createBrowserRouter(routes)} />
    </AppStateProvider>
  </StrictMode>,
);
