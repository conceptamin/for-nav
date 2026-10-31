// 센터 경로(S-12 전송, C-01~C-03)가 부르는 함수. 단독/API 모드 분기는 여기에만 있다.
// 센터 경로는 실패해도 대체하지 않는다(README "경로별 대체 정책"). localStorage로 대체하면
// 다른 기기에서 보낸 사례가 도착한 것처럼 보이는 가짜 성공이 되므로, 실패는 ApiError를 그대로 던진다.
// 서버가 센터 로그인을 쓸 때(backend 17) 401은 실패가 아니라 세션 끝이다. 받은 목록을 비우고 알린다(auth.ts의 onSessionEnded).

import { useEffect, useState, useSyncExternalStore } from 'react';
import type { CasePatch, CenterCase, CenterStats, MyCaseRef, MyCaseView, NewCaseRequest, NewCaseResponse } from '../domain/centerCase';
import { withCaseDefaults } from '../domain/centerCase';
import type { CenterHours } from '../domain/coverage';
import type { District } from '../domain/vocab';
import { getStatsLocal, loadAllLocal, resetCenterDemoLocal, sendCaseLocal, subscribeLocal, updateCaseLocal } from '../state/centerStore';
import { isSessionEnded, notifySessionEnded } from './auth';
import { ApiError, isApiMode, logFailure, requestJson } from './http';

/** 센터 경로 서버 호출 시간 제한. 넘기면 실패로 보인다 */
export const CENTER_TIMEOUT_MS = 5000;
/** 접수함 다시 읽기 주기. 한 번의 요청이 끝난 뒤부터 잰다(요청이 겹치지 않는다) */
export const CENTER_POLL_MS = 2000;
/** 근로자가 자기 요청 상태를 다시 읽는 주기(backlog 46). 화면이 보이는 동안만 돈다 */
export const MY_CASES_POLL_MS = 15000;
/** 한 번에 읽는 근로자 요청 수(backend 27의 상한). 최근 것부터 */
const MY_CASES_MAX = 20;

const bad = () => new ApiError('BAD_RESPONSE', null, null);
const isCase = (c: Partial<CenterCase> | undefined): boolean => Boolean(c && typeof c.id === 'string' && typeof c.status === 'string');

async function call<T>(path: string, options: { method?: 'GET' | 'POST' | 'PATCH'; body?: unknown } = {}): Promise<T> {
  try {
    return await requestJson<T>(path, { ...options, timeoutMs: CENTER_TIMEOUT_MS });
  } catch (e) {
    if (isSessionEnded(e)) endSession();
    else logFailure(path, e);
    throw e;
  }
}

/**
 * S-12 전송(`POST /api/center/cases`). 요약·긴급도·운영 시간 외 여부는 서버가 계산한 값을 그대로 쓴다.
 * `hours`는 단독 모드에서 운영 시간 외 판정에만 쓴다(API 모드는 서버 설정값).
 * 서버가 근로자 로그인을 쓰면(backend 21) 근로자 세션이 끝났을 때 401이다. 이것은 센터 직원 세션 끝이 아니므로
 * 위 `call`(센터 401 처리)을 거치지 않고 그대로 던진다. 화면이 `isSessionEnded`로 보고 로그인으로 보낸다.
 */
export async function sendCase(req: NewCaseRequest, hours: CenterHours): Promise<NewCaseResponse> {
  if (!isApiMode()) return sendCaseLocal(req, hours);
  let r: Partial<NewCaseResponse>;
  try {
    r = await requestJson<Partial<NewCaseResponse>>('/center/cases', { body: req, timeoutMs: CENTER_TIMEOUT_MS });
  } catch (e) {
    if (!isSessionEnded(e)) logFailure('/center/cases', e);
    throw e;
  }
  if (!isCase(r.case) || typeof r.nextOpenDate !== 'string') throw bad();
  // chatToken은 선택 필드다(backend 14). 문자열이 아니면 채팅 없이 전송 완료로 둔다
  if (typeof r.chatToken !== 'string') delete r.chatToken;
  return r as NewCaseResponse;
}

/** C-01 목록(`GET /api/center/cases`). 최신순 */
export async function listCases(): Promise<CenterCase[]> {
  if (!isApiMode()) return loadAllLocal();
  // 폴링 실패는 연결 띠로 보이므로 매번 기록하지 않는다(useCenterCases가 끊길 때 한 번 남긴다)
  const r = await requestJson<unknown>('/center/cases', { timeoutMs: CENTER_TIMEOUT_MS });
  if (!Array.isArray(r) || !r.every((c) => isCase(c as Partial<CenterCase>))) throw bad();
  // 분야·조치를 아직 돌려주지 않는 서버(backend 24 전)면 규칙 분야와 빈 조치로 채운다
  return (r as CenterCase[]).map(withCaseDefaults);
}

/** C-02 상태·분야·조치 변경(`PATCH /api/center/cases/{id}`). 있는 필드만 보낸다. 성공하면 접수함을 바로 다시 읽는다 */
export async function updateCase(id: string, patch: CasePatch): Promise<void> {
  if (isApiMode()) {
    const r = await call<Partial<CenterCase>>(`/center/cases/${encodeURIComponent(id)}`, { method: 'PATCH', body: patch });
    if (!isCase(r)) throw bad();
  } else {
    updateCaseLocal(id, patch);
  }
  await refreshCases();
}

/** C-01 데모 초기화(`POST /api/center/reset`). 실제 전송 사례와 상태 변경을 지운다 */
export async function resetDemo(): Promise<void> {
  if (isApiMode()) await call<void>('/center/reset', { method: 'POST' });
  else resetCenterDemoLocal();
  await refreshCases();
}

/** C-03 익명 집계(`GET /api/center/stats`). 5건 미만 칸은 받는 쪽에서 이미 null이다. 원천 레코드는 받지 않는다 */
export async function getStats(days: 30 | 90 | 180, district: District | null): Promise<CenterStats> {
  if (!isApiMode()) return getStatsLocal(days, district);
  const q = new URLSearchParams({ days: String(days) });
  if (district) q.set('district', district);
  const r = await call<Partial<CenterStats>>(`/center/stats?${q}`);
  const cells = [r.byIndustry, r.byLanguage, r.byInsurance, r.byAfterHours];
  if (!('total' in r) || !cells.every(Array.isArray)) throw bad();
  // 월별·분야별·국적별을 아직 주지 않는 서버(backend 25 전)면 그 칸만 비운다
  return { ...r, byMonth: r.byMonth ?? [], byCategory: r.byCategory ?? [], byNationality: r.byNationality ?? [] } as CenterStats;
}

// ---------------------------------------------------------------------------
// 근로자가 자기 요청의 처리 상태와 센터 메시지 수를 읽는다(backlog 46, backend 27).
// API 모드: `POST /api/center/my-cases`에 채팅 토큰을 실어 보낸다. 토큰이 없는 요청(backlog 46 이전·단독 모드에서 보낸 것)은 읽지 않는다.
// 단독 모드: 같은 브라우저의 센터 접수함(centerStore)에서 상태만 읽는다. 채팅이 없어 메시지 수는 0이다.
// 센터 경로라 실패를 대체하지 않는다. 화면은 마지막으로 받은 값을 그대로 두고 failed만 본다.
// ---------------------------------------------------------------------------

export async function getMyCases(refs: MyCaseRef[]): Promise<MyCaseView[]> {
  if (!isApiMode()) {
    const ids = new Set(refs.map((r) => r.id));
    return loadAllLocal()
      .filter((c) => ids.has(c.id))
      .map((c) => ({ id: c.id, status: c.status, centerMessages: 0, lastCenterAt: null }));
  }
  const cases = refs.filter((r): r is { id: string; token: string } => Boolean(r.token)).slice(0, MY_CASES_MAX);
  if (!cases.length) return [];
  const r = await requestJson<unknown>('/center/my-cases', { body: { cases }, timeoutMs: CENTER_TIMEOUT_MS });
  const ok = (v: Partial<MyCaseView>) => typeof v.id === 'string' && typeof v.status === 'string' && typeof v.centerMessages === 'number';
  if (!Array.isArray(r) || !r.every((v) => ok(v as Partial<MyCaseView>))) throw bad();
  return r as MyCaseView[];
}

export interface MyCasesFeed {
  /** 사례 id → 마지막으로 받은 상태. 서버가 돌려주지 않은 사례(토큰 없음·데모 초기화)는 없다 */
  cases: Record<string, MyCaseView>;
  /** 마지막 읽기가 실패했다. 값은 그 전에 받은 것이다 */
  failed: boolean;
  /** 한 번이라도 받았다. 받은 뒤 `cases`에 없는 사례는 서버가 모르는 것(데모 초기화·서버 재시작)이라 이어 보지 않는다 */
  loaded: boolean;
}

const EMPTY_FEED: MyCasesFeed = { cases: {}, failed: false, loaded: false };

/**
 * 근로자 레이아웃이 한 번 부른다. API 모드는 화면이 보이는 동안 MY_CASES_POLL_MS마다, 다시 보이면 곧바로 읽는다.
 * 단독 모드는 센터 접수함 변경 이벤트로 읽는다. 요청 목록(id·토큰)이 바뀌면 새로 시작한다.
 */
export function useMyCasesFeed(refs: MyCaseRef[]): MyCasesFeed {
  const [feed, setFeed] = useState<MyCasesFeed>(EMPTY_FEED);
  const key = JSON.stringify(refs);

  useEffect(() => {
    const list = JSON.parse(key) as MyCaseRef[];
    if (!list.length) {
      setFeed(EMPTY_FEED);
      return;
    }
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let inFlight = false;
    let failed = false;

    const read = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const views = await getMyCases(list);
        failed = false;
        if (!disposed) setFeed({ cases: Object.fromEntries(views.map((v) => [v.id, v])), failed: false, loaded: true });
      } catch (e) {
        if (disposed) return;
        // 끊길 때 한 번만 남긴다(접수함 연결 띠와 같다)
        if (!failed) logFailure('/center/my-cases', e);
        failed = true;
        setFeed((f) => ({ ...f, failed: true }));
      } finally {
        inFlight = false;
      }
    };

    if (!isApiMode()) {
      void read();
      const stop = subscribeLocal(() => void read());
      return () => {
        disposed = true;
        stop();
      };
    }

    const visible = () => document.visibilityState === 'visible';
    const loop = () => {
      void read().finally(() => {
        if (!disposed && visible()) timer = setTimeout(loop, MY_CASES_POLL_MS);
      });
    };
    const onVisibility = () => {
      if (timer) clearTimeout(timer);
      timer = null;
      if (visible()) loop();
    };
    loop();
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      disposed = true;
      if (timer) clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [key]);

  return feed;
}

// ---------------------------------------------------------------------------
// 접수함 구독. 센터 화면 여러 곳(헤더의 연결 띠, 목록, 상세)이 요청 하나를 나눠 쓴다.
// API 모드: 구독자가 있는 동안 CENTER_POLL_MS마다 listCases(). storage 이벤트는 듣지 않는다.
// 단독 모드: localStorage 변경 이벤트와 2초 주기로 다시 읽는다. 항상 연결됨이다.
// ---------------------------------------------------------------------------

export interface CenterFeed {
  cases: CenterCase[];
  /** 마지막 요청이 성공했는가. 단독 모드는 항상 true */
  connected: boolean;
  /** 마지막으로 목록을 받은 시각(ISO). API 모드에서 아직 한 번도 받지 못했으면 null */
  lastUpdated: string | null;
}

const localFeed = (): CenterFeed => ({ cases: loadAllLocal(), connected: true, lastUpdated: new Date().toISOString() });
const emptyFeed = (): CenterFeed => ({ cases: [], connected: true, lastUpdated: null });

let feed: CenterFeed = isApiMode() ? emptyFeed() : localFeed();
const subscribers = new Set<() => void>();
let stopLocal: (() => void) | null = null;
let pollTimer: ReturnType<typeof setTimeout> | null = null;
/** 구독을 멈췄다 다시 시작하면 늘어난다. 이전 주기의 예약을 무시하기 위해 쓴다 */
let generation = 0;
/** 늦게 도착한 이전 응답이 새 응답을 덮지 않게 한다 */
let requested = 0;
let applied = 0;

function publish(next: CenterFeed): void {
  feed = next;
  subscribers.forEach((f) => f());
}

/**
 * 로그아웃·세션 끝: 받아 둔 사례를 비운다. 다시 로그인하면 빈 접수함에서 새로 읽는다(다른 직원에게 앞 사람 목록이 보이지 않게).
 * 단독 모드에는 세션이 없다.
 */
export function clearCases(): void {
  if (!isApiMode()) return;
  applied = ++requested;
  publish(emptyFeed());
}

function endSession(): void {
  clearCases();
  notifySessionEnded();
}

/** 접수함을 지금 다시 읽는다. 실패는 연결 상태로만 드러나고 던지지 않는다. 401은 세션 끝으로 알린다 */
export async function refreshCases(): Promise<void> {
  if (!isApiMode()) {
    publish(localFeed());
    return;
  }
  const seq = ++requested;
  try {
    const cases = await listCases();
    if (seq < applied) return;
    applied = seq;
    publish({ cases, connected: true, lastUpdated: new Date().toISOString() });
  } catch (e) {
    if (seq < applied) return;
    applied = seq;
    if (isSessionEnded(e)) {
      endSession();
      return;
    }
    if (feed.connected) {
      logFailure('/center/cases', e);
      publish({ ...feed, connected: false });
    }
  }
}

function poll(gen: number): void {
  void refreshCases().finally(() => {
    if (gen === generation && subscribers.size > 0) pollTimer = setTimeout(() => poll(gen), CENTER_POLL_MS);
  });
}

function subscribe(onChange: () => void): () => void {
  subscribers.add(onChange);
  if (subscribers.size === 1) {
    if (isApiMode()) poll(++generation);
    else stopLocal = subscribeLocal(() => publish(localFeed()));
  }
  return () => {
    subscribers.delete(onChange);
    if (subscribers.size > 0) return;
    generation += 1;
    if (pollTimer) clearTimeout(pollTimer);
    pollTimer = null;
    stopLocal?.();
    stopLocal = null;
  };
}

/** C-01·C-02와 센터 헤더. 실패하면 `connected: false`가 되고 `cases`는 마지막으로 받은 목록을 유지한다 */
export function useCenterCases(): CenterFeed {
  return useSyncExternalStore(subscribe, () => feed);
}
