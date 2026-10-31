// 근로자 메뉴 서랍(backlog 50). 홈 밖의 화면에서 앱 바 끝 쪽, 언어 버튼 옆의 메뉴 버튼(☰)을 누르면
// 홈의 메뉴(홈 + 아파요/다쳤어요 + 아래 목록 넷)가 끝 쪽(RTL이면 왼쪽)에서 0.2초 밀려 들어온다. 지금 화면의 메뉴는 눌린 모양이다.
// 센터 채팅 시트처럼 막이 뒤 화면을 덮고, 119 독은 막 위라 그대로 보이고 눌린다. 서랍은 독 위에서 끝난다.
// Esc·막·✕로 닫으면 초점이 메뉴 버튼으로 돌아가고, 메뉴를 누르면 그 화면으로 가며 닫힌다(경로가 바뀌면 WorkerLayout이 닫는다).

import { useEffect, useRef } from 'react';
import type { Ref, RefObject } from 'react';
import { Link, useLocation } from 'react-router';
import { useT } from '../i18n';
import { HOME_MENU, isCurrentMenu, SICK_MENU, type MenuItem } from './workerMenu';

const DRAWER_MENU: Pick<MenuItem, 'to' | 'ico' | 'title' | 'also'>[] = [{ to: '/home', ico: '🏠', title: 'home' }, SICK_MENU, ...HOME_MENU];

/** 앱 바의 메뉴 버튼. 언어 버튼과 같은 44px 유리 버튼에 선 세 줄 아이콘 */
export function MenuButton({ ref, open, controls, onClick }: { ref: Ref<HTMLButtonElement>; open: boolean; controls: string; onClick: () => void }) {
  const { t } = useT();
  return (
    <button type="button" className="menu-btn" aria-label={t('menu')} aria-expanded={open} aria-controls={controls} ref={ref} onClick={onClick}>
      <svg className="menu-icon" width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="M4.5 7h15M4.5 12h15M4.5 17h15" />
      </svg>
    </button>
  );
}

export function WorkerDrawer({
  id,
  open,
  appName,
  trigger,
  onClose,
}: {
  id: string;
  open: boolean;
  appName: string;
  /** 닫을 때 초점을 돌려줄 메뉴 버튼 */
  trigger: RefObject<HTMLButtonElement | null>;
  onClose: () => void;
}) {
  const { t } = useT();
  const { pathname } = useLocation();
  const panel = useRef<HTMLDivElement>(null);

  const closeToTrigger = () => {
    onClose();
    trigger.current?.focus();
  };

  // 열면 서랍으로 초점을 옮기고 Esc로 닫는다. 뒤 화면은 스크롤되지 않게 묶는다(센터 채팅 시트와 같다)
  useEffect(() => {
    if (!open) return;
    panel.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return;
      onClose();
      trigger.current?.focus();
    };
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = overflow;
    };
  }, [open, onClose, trigger]);

  return (
    <>
      <div className={open ? 'drawer-scrim open' : 'drawer-scrim'} onClick={closeToTrigger} aria-hidden="true" />
      <div className={open ? 'drawer-layer open' : 'drawer-layer'}>
        <div id={id} className="drawer" role="dialog" aria-label={t('menu')} ref={panel} tabIndex={-1}>
          <div className="drawer-head">
            <span className="drawer-brand" dir="ltr">
              <img className="logo" src="/mark.png" width="28" height="28" alt="" />
              <img className="wordmark" src="/wordmark.png" width="76" height="20" alt={appName} />
            </span>
            <button type="button" className="sheet-btn" aria-label={t('close')} onClick={closeToTrigger}>
              <svg className="sheet-icon" width="24" height="24" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M6 6l12 12M18 6 6 18" />
              </svg>
            </button>
          </div>
          <nav className="drawer-nav" aria-label={t('menu')}>
            {DRAWER_MENU.map((m) => (
              <Link key={m.to} to={m.to} aria-current={isCurrentMenu(m, pathname) ? 'page' : undefined} onClick={onClose}>
                <span className="ico" aria-hidden>
                  {m.ico}
                </span>
                <span className="txt">{t(m.title)}</span>
              </Link>
            ))}
          </nav>
        </div>
      </div>
    </>
  );
}
