// 앱 바의 언어 변경(backlog 28). 번역 아이콘 + 지금 언어 코드 배지 버튼을 누르면 20개 언어 목록이 아래로 열린다.
// 메뉴 버튼 패턴(WAI-ARIA APG): Enter·Space·↓로 열면 지금 언어에, ↑로 열면 마지막 줄에 포커스.
// 목록에서 ↑↓·Home·End로 옮기고 Esc는 닫고 버튼으로, Tab·바깥 누름은 닫기만 한다.

import { useEffect, useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { LANGUAGE_OPTIONS, useT } from '../i18n';
import { useApp } from '../state/AppState';

/** 두 장의 카드가 겹친 번역 아이콘(앞 카드 A, 뒤 카드 文). 24px 격자 외곽선 */
function TranslateIcon() {
  return (
    <svg className="lang-icon" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" focusable="false">
      <path d="M11.55 6.5h7.95a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H9.5v-4M9.5 21.5l3.5-4" />
      <path d="M4.5 2.5h5.1a1.4 1.4 0 0 1 1.39 1.22L13 17.5H4.5a2 2 0 0 1-2-2v-11a2 2 0 0 1 2-2Z" />
      <path d="M4.4 13.2 6.9 6.4l2.5 6.8M5.3 11h3.2" />
      <path d="M17.25 9.6v1.2M14.6 11.4h5.3M15.4 11.4l3.8 6.4M19.1 11.4l-3.8 6.4" />
    </svg>
  );
}

export function LangMenu() {
  const app = useApp();
  const { t } = useT();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const focusOnOpen = useRef<'current' | 'last'>('current');
  const menuId = useId();

  const currentIndex = Math.max(
    0,
    LANGUAGE_OPTIONS.findIndex((o) => o.lang === app.lang),
  );

  // 열리면 지금 언어(또는 마지막 줄)로 포커스를 옮긴다. 바깥을 누르면 닫는다
  useEffect(() => {
    if (!open) return;
    const i = focusOnOpen.current === 'last' ? LANGUAGE_OPTIONS.length - 1 : currentIndex;
    itemRefs.current[i]?.focus();
    const onDown = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('pointerdown', onDown);
    return () => document.removeEventListener('pointerdown', onDown);
  }, [open, currentIndex]);

  if (!app.lang) return null;
  const current = LANGUAGE_OPTIONS[currentIndex];

  const openWith = (where: 'current' | 'last') => {
    focusOnOpen.current = where;
    setOpen(true);
  };

  const close = (refocus: boolean) => {
    setOpen(false);
    if (refocus) buttonRef.current?.focus();
  };

  const onButtonKey = (e: KeyboardEvent) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      openWith(e.key === 'ArrowUp' ? 'last' : 'current');
    }
  };

  const onMenuKey = (e: KeyboardEvent) => {
    const items = itemRefs.current;
    const at = items.indexOf(document.activeElement as HTMLButtonElement);
    const last = items.length - 1;
    const move = (i: number) => {
      e.preventDefault();
      items[i]?.focus();
    };
    if (e.key === 'ArrowDown') move(at >= last ? 0 : at + 1);
    else if (e.key === 'ArrowUp') move(at <= 0 ? last : at - 1);
    else if (e.key === 'Home') move(0);
    else if (e.key === 'End') move(last);
    else if (e.key === 'Escape') {
      e.preventDefault();
      close(true);
    } else if (e.key === 'Tab') close(false);
  };

  return (
    <div className="lang-pick" ref={rootRef}>
      <button
        ref={buttonRef}
        type="button"
        className="lang-btn"
        aria-label={`${t('changeLang')}: ${current.native}`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => (open ? close(false) : openWith('current'))}
        onKeyDown={onButtonKey}
      >
        <TranslateIcon />
        <span className="lang-code" aria-hidden="true">
          {current.lang.toUpperCase()}
        </span>
      </button>
      {open && (
        <div id={menuId} className="lang-menu" role="menu" aria-label={t('changeLang')} onKeyDown={onMenuKey}>
          {LANGUAGE_OPTIONS.map((o, i) => (
            <button
              key={o.lang}
              ref={(el) => {
                itemRefs.current[i] = el;
              }}
              type="button"
              role="menuitemradio"
              aria-checked={o.lang === app.lang}
              tabIndex={-1}
              onClick={() => {
                app.setLang(o.lang);
                close(true);
              }}
            >
              <span className="name" lang={o.lang}>
                {o.native}
              </span>
              <span className="en" lang="en">
                {o.english}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
