// 근로자 영역 레이아웃: 첫 진입 스플래시, 앱 바(← + 로고 + 언어 변경 LangMenu),하단 119 고정 버튼, 진입 순서 가드, 스크롤 등장.
// 들어올 때 서버 로그인 상태(api/auth.ts useWorkerAuth)를 한 번 보고 기기의 계정과 맞춘다(backlog 28).
// 앱 안에서는 이 계정의 센터 요청에 푸시 기기를 묶고, 알림으로 열리면 시트를 그 사례로 연다(backlog 48, api/push.ts).
// 화면 이름은 본문 h1 하나다. 앱 바에 다시 쓰지 않는다(심토미 기준, backlog 15). 화면이 useScreenBar로 등록하는
// title은 브라우저 탭 제목에만 쓰고, ← 동작과 숨김(로고 화면)도 거기서 등록한다.

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { Link, Navigate, Outlet, useLocation, useNavigate } from 'react-router';
import { useWorkerAuth } from '../api/auth';
import { useMyCasesFeed } from '../api/center';
import { usePushDevice, usePushOpen } from '../api/push';
import { unreadCount } from '../domain/centerCase';
import { useT } from '../i18n';
import { useApp } from '../state/AppState';
import { markSplashSeen, splashSeen } from '../state/splash';
import { CenterLinkContext, type CenterLink } from './centerLink';
import { CenterSheet, CountBadge } from './CenterSheet';
import { LangMenu } from './LangMenu';
import { useReveal } from './reveal';
import { MenuButton, WorkerDrawer } from './WorkerDrawer';

export interface ScreenBar {
  /** 화면 이름. 브라우저 탭 제목에 쓴다(앱 바에는 보이지 않는다) */
  title?: string;
  /** ←를 눌렀을 때. 없으면 /home */
  onBack?: () => void;
  /** true면 앱 바를 그리지 않는다(로고 화면 S-01·S-03, 분석 중 화면) */
  hidden?: boolean;
}

const ScreenBarContext = createContext<(bar: ScreenBar) => void>(() => {});

/**
 * 화면이 앱 바의 이름·← 동작을 등록한다. 언마운트하면 비운다.
 * onBack은 매 렌더 바뀌어도 되게 ref로 받는다(단계 안에서 되돌아가는 S-05처럼).
 */
export function useScreenBar(bar: ScreenBar) {
  const set = useContext(ScreenBarContext);
  const navigate = useNavigate();
  const ref = useRef(bar);
  ref.current = bar;
  const { title, hidden } = bar;
  useEffect(() => {
    // onBack을 등록하지 않은 화면(S-12, S-13)도 ← 가 /home으로 가야 한다
    set({ title, hidden, onBack: () => (ref.current.onBack ? ref.current.onBack() : navigate('/home')) });
  }, [set, title, hidden, navigate]);
  useEffect(() => () => set({}), [set]);
}

export function WorkerLayout() {
  const app = useApp();
  const { t } = useT();
  const { pathname, search } = useLocation();
  const navigate = useNavigate();
  const [bar, setBar] = useState<ScreenBar>({});
  const setBarStable = useMemo(() => setBar, []);

  // 서버가 Google 로그인을 쓰는데 기기의 계정이 서버 세션과 다르면(세션 만료·데모 계정) 서버를 따른다.
  // 서버를 확인하지 못하면(꺼짐) 기기의 계정으로 계속 쓴다. 처음 로그인만 서버가 있어야 한다(backlog 28 결정 2)
  const workerAuth = useWorkerAuth();
  const { account, loginKind, signIn, endSession } = app;
  useEffect(() => {
    if (workerAuth.status !== 'ready' || !workerAuth.required || !account) return;
    if (workerAuth.account === null) endSession();
    else if (workerAuth.account !== account || loginKind !== 'google') signIn(workerAuth.account, 'google');
  }, [workerAuth, account, loginKind, signIn, endSession]);

  // 스플래시: 이 세션에서 처음 열 때 한 번, 1.2초 또는 누를 때까지(backlog 24). 경로가 아니라 화면 대신 그린다
  const [splash, setSplash] = useState(() => !splashSeen());
  const endSplash = () => {
    markSplashSeen();
    setSplash(false);
  };
  useEffect(() => {
    if (!splash) return;
    const timer = window.setTimeout(endSplash, 1200);
    return () => window.clearTimeout(timer);
  }, [splash]);

  // 화면이 바뀌면 맨 위부터 보이게 한다.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  // 스크롤 등장(backlog 25). 스플래시 동안은 끈다
  const mainRef = useRef<HTMLElement>(null);
  useReveal(mainRef, !splash);

  // 센터 채팅 시트(backlog 39). 한 번 열면 닫아도 숨기기만 해서 채팅 연결·통화가 끊기지 않는다.
  // 로그인이 풀리면(app.ready가 꺼지면) 시트째 사라진다
  const [sheetOpen, setSheetOpen] = useState(false);
  const [sheetMounted, setSheetMounted] = useState(false);
  // S-13·S-12·푸시가 고른 사례. 독 버튼으로 열면 비워 시트가 채팅 목록부터 보인다(backlog 46·52).
  // 여는 차례마다 새 값이라 같은 사례를 다시 골라도 시트가 그 대화로 돌아간다
  const [sheetCase, setSheetCase] = useState<{ id: string | null }>({ id: null });
  const closeSheet = useCallback(() => setSheetOpen(false), []);
  const toggleSheet = () => {
    setSheetMounted(true);
    setSheetCase({ id: null });
    setSheetOpen((o) => !o);
    setDrawerOpen(false);
  };

  // 메뉴 서랍(backlog 50). 센터 채팅 시트와 하나만 열린다. 화면이 바뀌면 닫는다
  const [drawerOpen, setDrawerOpen] = useState(false);
  const openDrawer = useCallback(() => {
    setSheetOpen(false);
    setDrawerOpen(true);
  }, []);
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);
  const menuButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  // 내 센터 요청의 처리 상태(backlog 46). 로그인하고 프로필까지 있을 때만 읽는다
  const refs = useMemo(
    () => (app.ready ? app.myCaseIds.map((id) => ({ id, token: app.chatTokens[id] ?? null })) : []),
    [app.ready, app.myCaseIds, app.chatTokens],
  );
  const feed = useMyCasesFeed(refs);
  // 독 채팅 아이콘의 숫자 배지(backlog 52): 사례마다 아직 보지 않은 센터 메시지 수를 더한다
  const unread = app.ready ? app.myCaseIds.reduce((n, id) => n + unreadCount(feed.cases[id], app.seenCenterMessages[id]), 0) : 0;
  const centerLink = useMemo<CenterLink>(
    () => ({
      feed,
      openCase: (caseId) => {
        setSheetMounted(true);
        setSheetCase({ id: caseId });
        setSheetOpen(true);
      },
    }),
    [feed],
  );

  // 앱 푸시(backlog 48). 브라우저·단독 모드에서는 아무 일도 없다. 알림이 이 계정의 사례가 아니면(다른 계정·지운 사례) 열지 않는다
  usePushDevice(app.account, refs, t('pushNotice'));
  usePushOpen((caseId) => {
    if (app.ready && app.chatTokens[caseId]) centerLink.openCase(caseId);
  });

  const appName = app.lang ? t('appName') : 'for nav';

  // 화면 이름은 브라우저 탭 제목으로만 쓴다. 훅은 아래의 이른 return보다 먼저 불러야 한다
  useEffect(() => {
    document.title = bar.title ? `${bar.title} · ${appName}` : appName;
  }, [bar.title, appName]);

  // 119 버튼은 로딩과 관계없이 보인다. 예외는 1.2초 스플래시(사용자 결정, backlog 24). 응급 여부를 판정하지 않으므로(backlog 43) 늘 같은 자리에 있다
  // 채팅 버튼은 센터 연락(통화·채팅, backlog 29) 시트를 지금 화면 위에 열고 닫는다(backlog 39). 로그인하고 프로필까지 있을 때만 보인다.
  // 두 버튼은 끝 쪽에 뜬 유리 독(.bar-dock) 하나에 담는다(backlog 33)
  const bar119 = (
    <div className="bar-119">
      <div className="bar-dock">
        <a className="call-119" href="tel:119">
          <span className="call-119-icon" aria-hidden="true">
            <svg width="18" height="18" viewBox="0 0 24 24" focusable="false">
              <path d="M6.6 3.5h2.2l1.4 4-2 1.3a11 11 0 0 0 7 7l1.3-2 4 1.4v2.2a2.1 2.1 0 0 1-2.3 2.1A15.6 15.6 0 0 1 4.5 5.8a2.1 2.1 0 0 1 2.1-2.3Z" />
            </svg>
          </span>
          <span className="call-119-text">{app.lang ? t('bar119') : '119 · Korea Emergency · Cấp cứu'}</span>
        </a>
        {app.ready && (
          <button
            type="button"
            className="bar-chat"
            aria-label={unread ? `${t('chatTitle')} · ${t('caseNewMsg')} ${unread}` : t('chatTitle')}
            aria-expanded={sheetOpen}
            aria-controls="center-sheet"
            onClick={toggleSheet}
          >
            <svg className="bar-chat-icon" width="24" height="24" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <path d="M12 4c4.7 0 8.5 3.1 8.5 7s-3.8 7-8.5 7c-1 0-2-.15-2.9-.42L4.5 19.5l1.3-3.6C4.3 14.6 3.5 12.9 3.5 11c0-3.9 3.8-7 8.5-7Z" />
              <circle cx="8.5" cy="11" r="1" />
              <circle cx="12" cy="11" r="1" />
              <circle cx="15.5" cy="11" r="1" />
            </svg>
            {unread > 0 && <CountBadge n={unread} className="bar-chat-badge" />}
          </button>
        )}
      </div>
    </div>
  );

  if (splash) {
    return (
      <div className="w-shell">
        <main className="w-main w-splash" onClick={endSplash}>
          <img className="mark" src="/mark.png" width="96" height="96" alt="" />
          <h1>
            <img className="wordmark" src="/wordmark.png" width="137" height="36" alt={appName} />
          </h1>
        </main>
      </div>
    );
  }

  // 진입 순서: 언어 → 동의 → 로그인 → 프로필. 앞 단계를 건너뛰면 되돌린다. 로그인과 프로필은 둘 다 /signup이고,
  // 가던 화면(세션이 끝난 S-12 등)을 next에 담아 로그인 뒤 그리로 돌아간다
  const consented = app.consents.terms && app.consents.sensitive && app.consents.ai;
  if (!app.lang && pathname !== '/') return <Navigate to="/" replace />;
  if (app.lang && !consented && !['/', '/consent'].includes(pathname)) return <Navigate to="/consent" replace />;
  if (app.lang && consented && !app.ready && !['/', '/consent', '/signup'].includes(pathname)) {
    return <Navigate to={`/signup?${new URLSearchParams({ next: pathname + search })}`} replace />;
  }

  // 앱 바 왼쪽은 언어 버튼과 같은 유리 알약 하나(backlog 32). 홈은 로고 + 앱 이름(통째로 홈 링크, RTL에서도 로고가 앞),
  // 그 밖은 ← + 로고(로그인하고 프로필까지 있으면 로고가 홈 링크).
  // 앱 바를 숨기는 화면(S-01, S-03 로그인, 분석 중)도 좌측 상단에 로고 알약 하나를 둔다(backlog 25)
  const isRoot = pathname === '/' || pathname === '/home';
  // 메뉴 서랍(backlog 50)은 홈 밖에서 로그인하고 프로필까지 있을 때만. 앱 바를 숨긴 화면(분석 중)에는 메뉴 버튼도 없다
  const hasDrawer = app.ready && !isRoot && !bar.hidden;
  const logo = <img className="logo" src="/mark.png" width="28" height="28" alt="" />;

  return (
    <ScreenBarContext.Provider value={setBarStable}>
      <CenterLinkContext.Provider value={centerLink}>
      <div className="w-shell">
        {bar.hidden ? (
          <div className="w-corner-logo">
            <span className="brand-pill">{logo}</span>
          </div>
        ) : (
          <header className="w-header">
            {isRoot ? (
              <Link to={app.ready ? '/home' : '/'} className="brand-pill" dir="ltr">
                {logo}
                <img className="wordmark" src="/wordmark.png" width="76" height="20" alt={appName} />
              </Link>
            ) : (
              <div className="brand-pill">
                <button type="button" className="back" aria-label={t('back')} onClick={bar.onBack ?? (() => navigate('/home'))}>
                  ←
                </button>
                {app.ready ? (
                  <Link to="/home" className="logo-link" aria-label={appName}>
                    {logo}
                  </Link>
                ) : (
                  logo
                )}
              </div>
            )}
            <LangMenu />
            {hasDrawer && <MenuButton ref={menuButton} open={drawerOpen} controls="worker-drawer" onClick={openDrawer} />}
          </header>
        )}
        <main className="w-main" ref={mainRef}>
          <Outlet />
        </main>
        {app.ready && sheetMounted && <CenterSheet id="center-sheet" open={sheetOpen} onClose={closeSheet} focus={sheetCase} />}
        {hasDrawer && <WorkerDrawer id="worker-drawer" open={drawerOpen} appName={appName} trigger={menuButton} onClose={closeDrawer} />}
        {bar119}
      </div>
      </CenterLinkContext.Provider>
    </ScreenBarContext.Provider>
  );
}
