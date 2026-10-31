import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import type { RouteObject } from 'react-router';
import { createBrowserRouter, Navigate } from 'react-router';
import { RouterProvider } from 'react-router/dom';
import { WorkerLayout } from '@fe/components/WorkerLayout';
import { AfterHoursPage, CenterRequestPage, GuidePage, MyPage } from '@fe/pages/worker/CenterRequest';
import { CoveragePage } from '@fe/pages/worker/Coverage';
import { IntakePage, ResultPage } from '@fe/pages/worker/Intake';
import { ConsentPage, HomePage, LanguagePage, SignupPage } from '@fe/pages/worker/Onboarding';
import { ReportBuilderPage, ReportViewPage } from '@fe/pages/worker/Report';
import { setNativeGoogleSignIn, type NativeGoogleSignIn } from '@fe/api/googleId';
import { setHostSpeech, type HostSpeech } from '@fe/api/speech';
import { CallPage, DeskPage } from '@fe/pages/worker/Visit';
import { AppStateProvider } from '@fe/state/AppState';
import '@fe/styles.css';
import { installBackPolicy } from './bridge/back';
import {
  FEATURE_GOOGLE_SIGN_IN,
  FEATURE_SPEECH,
  getHostState,
  GoogleSignInError,
  installHost,
  listenHostSpeech,
  requestGoogleIdToken,
  subscribeHost,
} from './bridge/host';
import { HostProvider } from './bridge/HostProvider';
import { installLinkInterceptor } from './bridge/links';
import { HostCheckPage } from './pages/HostCheck';
import './styles.css';

// 다리는 렌더보다 먼저 선다. 호스트가 있으면 여기서 ready가 나간다(README "호스트 계약").
installHost();
installLinkInterceptor();
installBackPolicy();

// 앱 안 Google 로그인(backlog 06, frontend 35). WebView 안에서는 GIS가 막히므로, 호스트가 init.features로 알리면
// S-03이 네이티브 로그인을 쓰게 등록한다. 취소는 null(문구 없이 버튼으로), 그 밖은 예외(loginFailed)다. 브라우저에서는 등록하지 않는다
const nativeGoogleSignIn: NativeGoogleSignIn = () =>
  requestGoogleIdToken().catch((e: unknown) => {
    if (e instanceof GoogleSignInError && e.kind === 'canceled') return null;
    throw e;
  });
const syncNativeGoogleSignIn = () => {
  const host = getHostState();
  setNativeGoogleSignIn(host.present && host.features.includes(FEATURE_GOOGLE_SIGN_IN) ? nativeGoogleSignIn : null);
};
subscribeHost(syncNativeGoogleSignIn);
syncNativeGoogleSignIn();

// 통화 자막 받아쓰기(backlog 04, frontend 37). WebView에는 Web Speech API가 없으므로, 호스트가 init.features로 알리면
// 통화가 호스트 음성 인식을 쓰게 등록한다. 오류는 종류와 관계없이 "받아쓰기를 못 함"(onUnsupported)이다. 브라우저에서는 등록하지 않는다
const hostSpeech: HostSpeech = (lang, on) => listenHostSpeech(lang, { onText: on.onText, onError: () => on.onUnsupported() });
const syncHostSpeech = () => {
  const host = getHostState();
  setHostSpeech(host.present && host.features.includes(FEATURE_SPEECH) ? hostSpeech : null);
};
subscribeHost(syncHostSpeech);
syncHostSpeech();

// 근로자 화면은 frontend/src/main.tsx의 근로자 경로와 같은 순서·같은 화면 ID다(공유 import, backlog 02).
// 센터 화면(/center*)은 이 앱에 없다. 알 수 없는 경로는 /로 보낸다.
const routes: RouteObject[] = [
  {
    element: <WorkerLayout />,
    children: [
      { path: '/', element: <LanguagePage /> }, // S-01
      { path: '/consent', element: <ConsentPage /> }, // S-02
      { path: '/signup', element: <SignupPage /> }, // S-03
      { path: '/home', element: <HomePage /> }, // S-04
      { path: '/intake', element: <IntakePage /> }, // S-05
      { path: '/result', element: <ResultPage /> }, // S-07
      { path: '/coverage', element: <CoveragePage /> }, // S-08
      { path: '/visit/desk', element: <DeskPage /> }, // S-09
      { path: '/visit/call', element: <CallPage /> }, // S-10
      { path: '/report/new', element: <ReportBuilderPage /> }, // S-11 항목 선택
      { path: '/report/:id', element: <ReportViewPage /> }, // S-11 리포트
      { path: '/center-request', element: <CenterRequestPage /> }, // S-12
      { path: '/my', element: <MyPage /> }, // S-13
      { path: '/guide', element: <GuidePage /> },
      { path: '/after-hours', element: <AfterHoursPage /> }, // S-07에서 여는 밤·휴일 안내
    ],
  },
  { path: '/__host', element: <HostCheckPage /> }, // 호스트 연결 확인(개발용, 메뉴에 없다)
  { path: '*', element: <Navigate to="/" replace /> },
];

const root = document.getElementById('root');
if (!root) throw new Error('#root 요소가 없습니다');

createRoot(root).render(
  <StrictMode>
    <HostProvider>
      <AppStateProvider>
        <RouterProvider router={createBrowserRouter(routes)} />
      </AppStateProvider>
    </HostProvider>
  </StrictMode>,
);
