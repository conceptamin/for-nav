// 스플래시를 이 브라우저 세션에서 이미 봤는지(backlog 24). 세션 상태(umn.session)와 따로 둔다.
// "내 정보 모두 지우기"가 세션 상태를 비워도 스플래시가 다시 뜨지 않게 하려는 것이다.

import { readJson, writeJson } from './storage';

const SPLASH_KEY = 'umn.splash';

export function splashSeen(): boolean {
  return readJson(sessionStorage, SPLASH_KEY, false);
}

export function markSplashSeen(): void {
  writeJson(sessionStorage, SPLASH_KEY, true);
}
