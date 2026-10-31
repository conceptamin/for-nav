// 근로자 메뉴 표. 홈(S-04) 목록과 메뉴 서랍(backlog 50)이 같이 쓴다.
// also는 그 메뉴에서 이어지는 화면이다. 서랍에서 그 화면에 있을 때도 메뉴가 눌린 모양이다.

import type { MessageKey } from '../i18n';

export interface MenuItem {
  to: string;
  ico: string;
  title: MessageKey;
  sub: MessageKey;
  also?: string[];
}

/** 홈의 시작 카드(아파요/다쳤어요). 홈에서는 큰 카드라 아이콘이 없고, 서랍에서만 ico를 쓴다 */
export const SICK_MENU: MenuItem = { to: '/intake', ico: '🤒', title: 'menuSick', sub: 'menuSickSub', also: ['/emergency', '/result'] };

/** 홈의 아래 목록 */
export const HOME_MENU: MenuItem[] = [
  { to: '/guide', ico: '🏥', title: 'menuGuide', sub: 'menuGuideSub' },
  { to: '/coverage', ico: '💳', title: 'menuCoverage', sub: 'menuCoverageSub' },
  { to: '/center-request', ico: '🤝', title: 'menuCenter', sub: 'menuCenterSub', also: ['/center-chat'] },
  { to: '/my', ico: '👤', title: 'menuMy', sub: 'menuMySub' },
];

export function isCurrentMenu(item: Pick<MenuItem, 'to' | 'also'>, pathname: string): boolean {
  return pathname === item.to || Boolean(item.also?.includes(pathname));
}
