// 스크롤 등장(backlog 25). 화면 요소가 보이는 영역에 들어오면 아래에서 16px 올라오며 한 번 나타난다.
// 모양(투명도·이동·시간)은 styles.css의 [data-reveal]이 정하고, 여기서는 언제 보일지만 정한다.
// 함께 들어오는 요소는 data-reveal-i(0~5)로 40ms씩 차례를 준다. 스플래시처럼 꺼야 하는 곳은 enabled=false.

import { useEffect, type RefObject } from 'react';

/**
 * 등장시킬 요소: 화면 뿌리의 덩어리(카드·h1·목록 등)와 목록·격자의 항목.
 * 항목을 따로 등장시키는 목록 자체(.lang-grid, .home-list)와 바닥 주 동작(.w-footer)은 덩어리에서 뺀다.
 */
const TARGETS = [
  ':scope > * > *:not(.w-footer):not(.lang-grid):not(.home-list)',
  '.lang-grid > *',
  '.home-list > *',
].join(', ');

const MAX_STAGGER = 5;

export function useReveal(root: RefObject<HTMLElement | null>, enabled: boolean) {
  useEffect(() => {
    const el = root.current;
    if (!el || !enabled) return;
    // 동작 줄이기 설정이거나 관찰을 못 하는 브라우저는 처음부터 보인다(숨긴 채 멈추지 않는다)
    if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const io = new IntersectionObserver(
      (entries) => {
        let order = 0;
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          const target = entry.target as HTMLElement;
          target.dataset.revealI = String(Math.min(order++, MAX_STAGGER));
          target.dataset.reveal = 'in';
          io.unobserve(target);
        }
      },
      // 아주 긴 요소도 나타나도록 비율 대신 화면 아래 10% 안쪽에 닿는 순간으로 잡는다
      { threshold: 0, rootMargin: '0px 0px -10% 0px' },
    );
    const scan = () => {
      el.querySelectorAll<HTMLElement>(TARGETS).forEach((target) => {
        if (target.dataset.reveal) return;
        target.dataset.reveal = 'wait';
        io.observe(target);
      });
    };
    scan();
    // 단계·화면이 바뀌어 새로 생긴 요소도 잡는다
    const mo = new MutationObserver(scan);
    mo.observe(el, { childList: true, subtree: true });

    return () => {
      io.disconnect();
      mo.disconnect();
      // 꺼질 때 아직 기다리는 요소는 표시를 지워 바로 보이게 한다.
      // 'in'으로 바꾸지 않는다: 다시 켜지면(개발 모드 StrictMode의 두 번 실행 등) 다시 기다리게 해야 한다
      el.querySelectorAll<HTMLElement>('[data-reveal="wait"]').forEach((target) => {
        delete target.dataset.reveal;
      });
    };
  }, [root, enabled]);
}
