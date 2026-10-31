// 내 센터 요청의 처리 상태와 시트 열기(backlog 46). WorkerLayout이 상태를 한 곳에서 읽어(api/center.ts useMyCasesFeed)
// 이 컨텍스트로 S-13 요청 줄과 센터 채팅 시트에 나눠 준다. 시트와 레이아웃이 서로를 import하지 않도록 따로 둔다.

import { createContext, useContext } from 'react';
import type { MyCasesFeed } from '../api/center';

export interface CenterLink {
  /** 내 센터 요청의 처리 상태와 센터 메시지 수 */
  feed: MyCasesFeed;
  /** 센터 채팅 시트를 그 사례로 연다(S-13 요청 줄) */
  openCase: (caseId: string) => void;
}

/** 이 사례에 다시 붙을 수 있는가: 토큰이 있고, 상태를 받은 뒤라면 서버가 아는 사례다 */
export function canResume(feed: MyCasesFeed, caseId: string, token: string | undefined): boolean {
  return Boolean(token) && (!feed.loaded || caseId in feed.cases);
}

export const CenterLinkContext = createContext<CenterLink>({ feed: { cases: {}, failed: false, loaded: false }, openCase: () => {} });

/** S-13·시트가 내 요청 상태를 보고, S-13이 시트를 특정 사례로 연다 */
export function useCenterLink(): CenterLink {
  return useContext(CenterLinkContext);
}
