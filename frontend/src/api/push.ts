// 앱 푸시 알림 자리(backlog 48, backend 28, app-front 07·08). 앱(app-front)이 호스트가 FCM을 알릴 때 setHostPush로 등록하고,
// WorkerLayout이 usePushDevice·usePushOpen으로 이 계정의 사례에 기기를 묶고 알림으로 열린 사례의 시트를 연다.
// 브라우저·단독 모드에서는 자리가 비거나 API를 부르지 않아 아무 일도 없다(웹 푸시는 하지 않는다, app-front 08 결정 4).
// 기기 토큰은 이 파일의 메모리에만 둔다. 저장소에 쓰거나 console에 찍지 않는다. 실패는 다시 시도하지 않고 다음 변경·다음 실행 때 보낸다.

import { useEffect, useMemo, useRef, useSyncExternalStore } from 'react';
import type { MyCaseRef } from '../domain/centerCase';
import { isApiMode, logFailure, requestJson } from './http';

/** 등록 요청 시간 제한. 센터 경로와 같다 */
export const PUSH_TIMEOUT_MS = 5000;
/** 한 번에 묶는 사례 수(backend 28의 상한). 최근 것부터 */
const PUSH_CASES_MAX = 20;

/** 앱 호스트의 푸시. 토큰을 받지 못하면(권한 거부) getToken이 null, 그 밖 실패는 예외다 */
export interface HostPush {
  platform: 'android' | 'ios';
  getToken(): Promise<string | null>;
  /** 요청 없이 바뀐 토큰(FCM 토큰 갱신). 구독을 끊는 함수를 돌려준다 */
  onToken(cb: (token: string) => void): () => void;
  /** 이 기기의 FCM 토큰을 지운다. 응답은 없다 */
  unregister(): void;
  /** 근로자가 센터 알림을 눌러 앱이 열렸다. 구독 전에 온 것은 다리가 하나 들고 있다가 넘긴다 */
  onOpen(cb: (caseId: string) => void): () => void;
}

let hostPush: HostPush | null = null;
const slotListeners = new Set<() => void>();

/** 앱(app-front)이 호스트가 푸시를 알릴 때 등록한다. 호스트의 init은 첫 화면보다 늦게 오므로 화면은 구독해서 읽는다 */
export function setHostPush(push: HostPush | null): void {
  if (hostPush === push) return;
  hostPush = push;
  slotListeners.forEach((l) => l());
}

function subscribeSlot(listener: () => void): () => void {
  slotListeners.add(listener);
  return () => slotListeners.delete(listener);
}

function useHostPush(): HostPush | null {
  return useSyncExternalStore(subscribeSlot, () => hostPush);
}

// 이 페이지에서 받은 기기 토큰과 마지막으로 보낸 등록. 페이지마다(앱을 열 때마다) 처음부터 다시 등록한다(app-front 08 결정 3)
let deviceToken: string | null = null;
let tokenRequest: Promise<string | null> | null = null;
/** 이 페이지에서 권한을 거부했다. 다시 묻지 않는다(OS도 다시 창을 띄우지 않는다) */
let denied = false;
/** 마지막으로 보낸 등록(계정·문구·사례). 같으면 보내지 않는다. 토큰이 바뀌면 비운다 */
let sentKey: string | null = null;
/** 해제할 때마다 올린다. 해제 전에 시작한 등록은 끝나도 보내지 않는다 */
let generation = 0;

function requestToken(push: HostPush): Promise<string | null> {
  tokenRequest ??= push.getToken().finally(() => {
    tokenRequest = null;
  });
  return tokenRequest;
}

async function register(push: HostPush, account: string, cases: { id: string; token: string }[], notice: string): Promise<void> {
  const gen = generation;
  if (!deviceToken) {
    if (denied) return;
    let token: string | null;
    try {
      token = await requestToken(push);
    } catch {
      console.warn('[push] 토큰을 받지 못함');
      return;
    }
    if (gen !== generation) return;
    if (!token) {
      denied = true;
      return;
    }
    deviceToken = token;
  }
  const key = JSON.stringify([account, notice, cases.map((c) => c.id)]);
  if (key === sentKey) return;
  sentKey = key;
  try {
    await requestJson<unknown>('/center/push-devices', {
      body: { deviceToken, platform: push.platform, notice, cases },
      timeoutMs: PUSH_TIMEOUT_MS,
    });
  } catch (e) {
    logFailure('/center/push-devices', e);
  }
}

/** 로그아웃·계정 바꾸기·내 데이터 지우기. 서버에서 기기를 뺀 뒤 호스트가 FCM 토큰을 지운다. 서버가 실패해도 토큰은 지운다 */
async function unregister(push: HostPush): Promise<void> {
  generation += 1;
  sentKey = null;
  const token = deviceToken ?? (tokenRequest ? await tokenRequest.catch(() => null) : null);
  deviceToken = null;
  if (!token) return;
  if (isApiMode()) {
    try {
      await requestJson<void>('/center/push-devices/remove', { body: { deviceToken: token }, timeoutMs: PUSH_TIMEOUT_MS });
    } catch (e) {
      logFailure('/center/push-devices/remove', e);
    }
  }
  push.unregister();
}

/**
 * 이 기기를 이 계정의 사례(채팅 토큰이 있는 것, 최대 20개)에 묶는다. API 모드이고 앱이 푸시를 등록했을 때만 보낸다.
 * 사례 목록·문구(언어)·토큰이 바뀌면 다시 보내고, 계정이 바뀌거나 비면(로그아웃·지우기) 앞 계정의 묶음을 푼다.
 * `notice`는 알림 본문으로 쓰일 근로자 언어의 한 문장이다(backend 28 결정 2). 언어를 아직 고르지 않았으면(앱을 완전히 껐다 켜면
 * 세션의 언어가 사라진다) null을 넘긴다. 그때는 보내지 않아, 서버에 등록된 근로자 언어 문장을 영어로 덮어쓰지 않는다.
 */
export function usePushDevice(account: string | null, refs: MyCaseRef[], notice: string | null): void {
  const push = useHostPush();
  const cases = useMemo(
    () => refs.filter((r): r is { id: string; token: string } => Boolean(r.token)).slice(0, PUSH_CASES_MAX),
    [refs],
  );
  const casesKey = cases.map((c) => `${c.id}:${c.token}`).join(',');

  const prevAccount = useRef(account);
  useEffect(() => {
    const prev = prevAccount.current;
    prevAccount.current = account;
    if (push && prev && prev !== account) void unregister(push);
  }, [push, account]);

  // 토큰이 바뀌면 다음 등록이 새 토큰으로 나가게 한다
  const latest = useRef({ account, cases, notice });
  latest.current = { account, cases, notice };
  useEffect(() => {
    if (!push) return;
    return push.onToken((token) => {
      if (token === deviceToken) return;
      deviceToken = token;
      sentKey = null;
      const { account: a, cases: c, notice: n } = latest.current;
      if (isApiMode() && a && c.length && n) void register(push, a, c, n);
    });
  }, [push]);

  useEffect(() => {
    if (!push || !isApiMode() || !account || !cases.length || !notice) return;
    void register(push, account, cases, notice);
    // cases는 casesKey로 본다(같은 내용의 새 배열로는 다시 보내지 않는다)
  }, [push, account, casesKey, notice]);
}

/** 근로자가 센터 알림을 눌러 앱이 열렸을 때. 받는 쪽이 이 계정의 사례인지 보고 연다 */
export function usePushOpen(onOpen: (caseId: string) => void): void {
  const push = useHostPush();
  const ref = useRef(onOpen);
  ref.current = onOpen;
  useEffect(() => push?.onOpen((caseId) => ref.current(caseId)), [push]);
}
