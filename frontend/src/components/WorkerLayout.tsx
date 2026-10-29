// 근로자 영역 레이아웃: 앱 바(← + 화면 이름 + 언어 변경), 하단 119 고정 버튼, 진입 순서 가드.
// 화면 이름과 ← 동작은 화면이 useScreenBar로 등록한다(design.md "화면 골격(Figma 기준)" 앱 바).

import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { Link, Navigate, Outlet, useLocation, useNavigate } from 'react-router';
import { LANGUAGE_OPTIONS, useT } from '../i18n';
import { useApp } from '../state/AppState';
import type { Lang } from '../domain/vocab';

export interface ScreenBar {
  /** 앱 바 가운데 화면 이름. 없으면 앱 이름 */
  title?: string;
  /** ←를 눌렀을 때. 없으면 /home */
  onBack?: () => void;
  /** true면 앱 바를 그리지 않는다(분석 중 화면) */
  hidden?: boolean;
}

const ScreenBarContext = createContext<(bar: ScreenBar) => void>(() => {});

/**
 * 화면이 앱 바의 이름·← 동작을 등록한다. 언마운트하면 비운다.
 * onBack은 매 렌더 바뀌어도 되게 ref로 받는다(단계 안에서 되돌아가는 S-05처럼).
 */
export function useScreenBar(bar: ScreenBar) {
  const set = useContext(ScreenBarContext);
  const ref = useRef(bar);
  ref.current = bar;
  const { title, hidden } = bar;
  useEffect(() => {
    set({ title, hidden, onBack: () => ref.current.onBack?.() });
  }, [set, title, hidden]);
  useEffect(() => () => set({}), [set]);
}

export function WorkerLayout() {
  const app = useApp();
  const { t } = useT();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [bar, setBar] = useState<ScreenBar>({});
  const setBarStable = useMemo(() => setBar, []);

  // 화면이 바뀌면 맨 위부터 보이게 한다.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  // 진입 순서: 언어 → 동의 → 로그인/비회원. 앞 단계를 건너뛰면 되돌린다.
  const consented = app.consents.terms && app.consents.sensitive && app.consents.ai;
  if (!app.lang && pathname !== '/') return <Navigate to="/" replace />;
  if (app.lang && !consented && !['/', '/consent'].includes(pathname)) return <Navigate to="/consent" replace />;
  if (app.lang && consented && !app.mode && !['/', '/consent', '/signup'].includes(pathname)) {
    return <Navigate to="/signup" replace />;
  }

  const show119Bar = pathname !== '/emergency';
  // 홈과 S-01은 ← 대신 앱 이름(홈 링크). 그 밖은 ← + 화면 이름
  const isRoot = pathname === '/' || pathname === '/home';
  const appName = app.lang ? t('appName') : '울산 외국인 의료 내비게이터';

  return (
    <ScreenBarContext.Provider value={setBarStable}>
      <div className="w-shell">
        {!bar.hidden && (
          <header className="w-header">
            {isRoot ? (
              <Link to={app.mode ? '/home' : '/'} className="title">
                {appName}
              </Link>
            ) : (
              <>
                <button type="button" className="back" aria-label={t('back')} onClick={bar.onBack ?? (() => navigate('/home'))}>
                  ←
                </button>
                <span className="title">{bar.title ?? appName}</span>
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
        {show119Bar && (
          <div className="bar-119">
            <a href="tel:119">📞 {app.lang ? t('bar119') : '119 · Emergency · Khẩn cấp'}</a>
          </div>
        )}
      </div>
    </ScreenBarContext.Provider>
  );
}
