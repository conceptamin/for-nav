// 근로자 영역 레이아웃: 첫 진입 스플래시, 앱 바(← + 언어 변경), 하단 119 고정 버튼, 진입 순서 가드.
// 화면 이름은 본문 h1 하나다. 앱 바에 다시 쓰지 않는다(심토미 기준, backlog 15). 화면이 useScreenBar로 등록하는
// title은 브라우저 탭 제목에만 쓰고, ← 동작과 숨김(로고 화면)도 거기서 등록한다.

import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { Link, Navigate, Outlet, useLocation, useNavigate } from 'react-router';
import { LANGUAGE_OPTIONS, useT } from '../i18n';
import { useApp } from '../state/AppState';
import { markSplashSeen, splashSeen } from '../state/splash';
import type { Lang } from '../domain/vocab';

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
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [bar, setBar] = useState<ScreenBar>({});
  const setBarStable = useMemo(() => setBar, []);

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

  const appName = app.lang ? t('appName') : 'for nav';

  // 화면 이름은 브라우저 탭 제목으로만 쓴다. 훅은 아래의 이른 return보다 먼저 불러야 한다
  useEffect(() => {
    document.title = bar.title ? `${bar.title} · ${appName}` : appName;
  }, [bar.title, appName]);

  // 119 띠는 스플래시·로딩과 관계없이 보인다(응급 화면은 자기 전화 버튼이 있다)
  const bar119 = pathname !== '/emergency' && (
    <div className="bar-119">
      <a href="tel:119">📞 {app.lang ? t('bar119') : '119 · Emergency · Khẩn cấp'}</a>
    </div>
  );

  if (splash) {
    return (
      <div className="w-shell">
        <main className="w-main w-splash" onClick={endSplash}>
          <img className="mark" src="/logo.png" width="96" height="96" alt="" />
          <h1>{appName}</h1>
        </main>
        {bar119}
      </div>
    );
  }

  // 진입 순서: 언어 → 동의 → 로그인/비회원. 앞 단계를 건너뛰면 되돌린다.
  const consented = app.consents.terms && app.consents.sensitive && app.consents.ai;
  if (!app.lang && pathname !== '/') return <Navigate to="/" replace />;
  if (app.lang && !consented && !['/', '/consent'].includes(pathname)) return <Navigate to="/consent" replace />;
  if (app.lang && consented && !app.mode && !['/', '/consent', '/signup'].includes(pathname)) {
    return <Navigate to="/signup" replace />;
  }

  // 홈은 ← 대신 앱 이름(홈 링크). 그 밖은 ← 하나. S-01은 앱 바를 숨긴다
  const isRoot = pathname === '/' || pathname === '/home';

  return (
    <ScreenBarContext.Provider value={setBarStable}>
      <div className="w-shell">
        {!bar.hidden && (
          <header className="w-header">
            {isRoot ? (
              <>
                <img className="logo" src="/logo.png" width="24" height="24" alt="" />
                <Link to={app.mode ? '/home' : '/'} className="title">
                  {appName}
                </Link>
              </>
            ) : (
              <>
                <button type="button" className="back" aria-label={t('back')} onClick={bar.onBack ?? (() => navigate('/home'))}>
                  ←
                </button>
                <span className="title" />
              </>
            )}
            {app.lang && (
              <select
                aria-label={t('changeLang')}
                value={app.lang}
                onChange={(e) => app.setLang(e.target.value as Lang)}
              >
                {LANGUAGE_OPTIONS.map((o) => (
                  <option key={o.lang} value={o.lang}>
                    {o.native}
                  </option>
                ))}
              </select>
            )}
          </header>
        )}
        <main className="w-main">
          <Outlet />
        </main>
        {bar119}
      </div>
    </ScreenBarContext.Provider>
  );
}
