// 근로자 메뉴 서랍(backlog 50). 홈 밖의 화면에서 끝 쪽(RTL이면 왼쪽) 가장자리 가운데의 손잡이를 누르거나 안쪽으로 밀면
// 홈의 메뉴(홈 + 아파요/다쳤어요 + 아래 목록 넷)가 끝 쪽에서 0.2초 밀려 들어온다. 지금 화면의 메뉴는 눌린 모양이다.
// 센터 채팅 시트처럼 막이 뒤 화면을 덮고, 119 독은 막 위라 그대로 보이고 눌린다. 서랍은 독 위에서 끝난다.
// Esc·막·✕로 닫으면 초점이 손잡이로 돌아가고, 메뉴를 누르면 그 화면으로 가며 닫힌다(경로가 바뀌면 WorkerLayout이 닫는다).

import { useEffect, useRef } from 'react';
import type { PointerEvent } from 'react';
import { Link, useLocation } from 'react-router';
import { useT } from '../i18n';
import { HOME_MENU, isCurrentMenu, SICK_MENU, type MenuItem } from './workerMenu';

const DRAWER_MENU: Pick<MenuItem, 'to' | 'ico' | 'title' | 'also'>[] = [{ to: '/home', ico: '🏠', title: 'home' }, SICK_MENU, ...HOME_MENU];

/** 손잡이를 안쪽으로 이만큼(px) 밀면 연다 */
const SWIPE_OPEN = 16;

export function WorkerDrawer({
  id,
  open,
  showHandle,
  appName,
  onOpen,
  onClose,
}: {
  id: string;
  open: boolean;
  showHandle: boolean;
  appName: string;
  onOpen: () => void;
  onClose: () => void;
}) {
  const { t } = useT();
  const { pathname } = useLocation();
  const panel = useRef<HTMLDivElement>(null);
  const handle = useRef<HTMLButtonElement>(null);
  const swipeFrom = useRef<number | null>(null);
  // 열려 있는 동안 손잡이는 감춰져 있어 닫는 순간에는 초점을 받지 못한다. 닫힌 뒤 그린 다음에 옮긴다
  const refocus = useRef(false);

  const closeToHandle = () => {
    refocus.current = true;
    onClose();
  };

  useEffect(() => {
    if (open || !refocus.current) return;
    refocus.current = false;
    handle.current?.focus();
  }, [open]);

  // 열면 서랍으로 초점을 옮기고 Esc로 닫는다. 뒤 화면은 스크롤되지 않게 묶는다(센터 채팅 시트와 같다)
  useEffect(() => {
    if (!open) return;
    panel.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return;
      refocus.current = true;
      onClose();
    };
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = overflow;
    };
  }, [open, onClose]);

  // 손잡이를 안쪽(LTR은 왼쪽, RTL은 오른쪽)으로 밀면 연다. 세로 스크롤은 막지 않는다(touch-action: pan-y)
  const onPointerDown = (e: PointerEvent) => {
    swipeFrom.current = e.clientX;
  };
  const onPointerMove = (e: PointerEvent) => {
    if (swipeFrom.current === null) return;
    const inward = document.documentElement.dir === 'rtl' ? e.clientX - swipeFrom.current : swipeFrom.current - e.clientX;
    if (inward < SWIPE_OPEN) return;
    swipeFrom.current = null;
    onOpen();
  };
  const endSwipe = () => {
    swipeFrom.current = null;
  };

  return (
    <>
      <div className={open ? 'drawer-scrim open' : 'drawer-scrim'} onClick={closeToHandle} aria-hidden="true" />
      <div className={open ? 'drawer-layer open' : 'drawer-layer'}>
        {showHandle && (
          <button
            type="button"
            className="drawer-handle"
            aria-label={t('menu')}
            aria-expanded={open}
            aria-controls={id}
            ref={handle}
            onClick={onOpen}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={endSwipe}
            onPointerCancel={endSwipe}
          >
            <span className="drawer-tab" aria-hidden="true" />
          </button>
        )}
        <div id={id} className="drawer" role="dialog" aria-label={t('menu')} ref={panel} tabIndex={-1}>
          <div className="drawer-head">
            <span className="drawer-brand" dir="ltr">
              <img className="logo" src="/mark.png" width="28" height="28" alt="" />
              <img className="wordmark" src="/wordmark.png" width="76" height="20" alt={appName} />
            </span>
            <button type="button" className="sheet-btn" aria-label={t('close')} onClick={closeToHandle}>
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
