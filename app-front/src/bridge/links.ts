// 외부 링크·전화 가로채기(README "외부 링크와 전화").
// 화면은 평소처럼 <a href="tel:119">, <a href="https://map.kakao.com/...">을 쓴다. 호스트가 init을 보낸 뒤에만
// tel:·mailto:·sms:와 앱 출처 밖 http(s) 링크를 openExternal로 넘기고 기본 동작을 막는다.
// 호스트가 없거나 init 전이면 손대지 않아 브라우저(또는 WebView 기본 처리)가 평소대로 연다. 119가 늦어지지 않게 하기 위해서다.

import { getHostState, send } from './host';

const EXTERNAL_SCHEMES = new Set(['tel:', 'mailto:', 'sms:']);

/** 앱 밖에서 열어야 하는 주소인가. 같은 출처의 http(s)와 라우터 링크는 아니다 */
export function isExternalUrl(url: URL): boolean {
  if (EXTERNAL_SCHEMES.has(url.protocol)) return true;
  return (url.protocol === 'http:' || url.protocol === 'https:') && url.origin !== window.location.origin;
}

/** 호스트가 열 수 있으면 넘기고 true. 아니면 false(호출한 쪽이 브라우저 기본 동작에 맡긴다) */
export function openExternal(url: string): boolean {
  if (!getHostState().ready) return false;
  return send({ type: 'openExternal', url });
}

let installed = false;

export function installLinkInterceptor(): void {
  if (installed) return;
  installed = true;
  document.addEventListener(
    'click',
    (e) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const anchor = (e.target as Element | null)?.closest?.('a[href]');
      if (!(anchor instanceof HTMLAnchorElement)) return;
      let url: URL;
      try {
        url = new URL(anchor.href, window.location.href);
      } catch {
        return;
      }
      if (!isExternalUrl(url)) return;
      if (openExternal(url.href)) e.preventDefault();
    },
    true,
  );
}
