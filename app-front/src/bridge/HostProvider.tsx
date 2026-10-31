// 화면이 호스트 상태를 읽는 유일한 통로. 상태 저장(AppState)에 기대지 않으므로 그 바깥에 둔다.

import { createContext, useContext, useMemo, useSyncExternalStore, type ReactNode } from 'react';
import { getHostState, subscribeHost, type HostState } from './host';
import { openExternal as hostOpenExternal } from './links';

export interface HostContextValue extends HostState {
  /** 호스트가 있으면 호스트가 열고 true. 없으면 같은 탭에서 브라우저가 열고 false */
  openExternal: (url: string) => boolean;
}

const HostContext = createContext<HostContextValue | null>(null);

export function HostProvider({ children }: { children: ReactNode }) {
  const state = useSyncExternalStore(subscribeHost, getHostState, getHostState);
  const value = useMemo<HostContextValue>(
    () => ({
      ...state,
      openExternal: (url) => {
        if (hostOpenExternal(url)) return true;
        window.location.assign(url);
        return false;
      },
    }),
    [state],
  );
  return <HostContext.Provider value={value}>{children}</HostContext.Provider>;
}

export function useHost(): HostContextValue {
  const ctx = useContext(HostContext);
  if (!ctx) throw new Error('HostProvider 안에서만 사용할 수 있습니다');
  return ctx;
}
