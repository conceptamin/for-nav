// 근로자 영역 레이아웃: 상단 헤더(언어 변경), 하단 119 고정 버튼, 진입 순서 가드.

import { useEffect } from 'react';
import { Link, Navigate, Outlet, useLocation } from 'react-router';
import { LANGUAGE_OPTIONS, useT } from '../i18n';
import { useApp } from '../state/AppState';
import type { Lang } from '../domain/vocab';

export function WorkerLayout() {
  const app = useApp();
  const { t } = useT();
  const { pathname } = useLocation();

  // 화면이 바뀌면 맨 위부터 보이게 한다.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  // 진입 순서: 언어 → 동의 → 이용 방식. 앞 단계를 건너뛰면 되돌린다.
  const consented = app.consents.terms && app.consents.sensitive && app.consents.ai;
  if (!app.lang && pathname !== '/') return <Navigate to="/" replace />;
  if (app.lang && !consented && !['/', '/consent'].includes(pathname)) return <Navigate to="/consent" replace />;
  if (app.lang && consented && !app.mode && !['/', '/consent', '/signup'].includes(pathname)) {
    return <Navigate to="/signup" replace />;
  }

  const show119Bar = pathname !== '/emergency';

  return (
    <div className="w-shell">
      <header className="w-header">
        <Link to={app.mode ? '/home' : '/'} className="title">
          {app.lang ? t('appName') : '울산 외국인 의료 내비게이터'}
        </Link>
        <span className="badge">{app.lang ? t('demoBadge') : 'Demo'}</span>
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
      <main className="w-main">
        <Outlet />
      </main>
      {show119Bar && (
        <div className="bar-119">
          <a href="tel:119">📞 {app.lang ? t('bar119') : '119 · Emergency · Khẩn cấp'}</a>
        </div>
      )}
    </div>
  );
}
