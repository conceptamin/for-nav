// 호스트(Flutter) 계약의 웹 쪽 구현(README "호스트 계약"). 화면은 이 파일을 직접 부르지 않고 HostProvider의 useHost()를 쓴다.
// - 감지: 호스트가 문서 시작 때 넣어 둔 전송 통로(window.ForNav / window.flutter_inappwebview)가 있는지만 본다. UA는 보지 않는다.
// - 웹 → 호스트: send(). 호스트 → 웹: window.fornav.receive(), 동기 window.fornav.onBack().
// - 메시지 본문(openExternal.url 등)을 console에 찍지 않는다. 기록은 type만 남긴다.
// - 호스트가 없으면 send()는 false를 돌려주고 아무 일도 하지 않는다. 화면은 그때 브라우저 기본 동작에 맡긴다.

export const PROTOCOL = 1;

export type Platform = 'android' | 'ios';
export type Transport = 'webview_flutter' | 'flutter_inappwebview';

export interface Insets {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

/** 다리가 주고받은 메시지의 type 기록. 본문은 남기지 않는다(확인 화면용) */
export interface LogEntry {
  dir: 'out' | 'in';
  type: string;
  at: string;
}

export interface HostState {
  /** 전송 통로가 있다 = 호스트 안이다 */
  present: boolean;
  transport: Transport | null;
  /** 호스트가 init을 보냈다. 이 뒤에만 tel:·외부 링크를 가로챈다 */
  ready: boolean;
  platform: Platform | null;
  appVersion: string | null;
  /** BCP-47. 없으면 화면이 navigator.language를 쓴다 */
  locale: string | null;
  /** 호스트가 준 안전 영역(CSS px). :root의 --inset-*에도 들어간다 */
  insets: Insets;
  log: LogEntry[];
}

/** 웹 → 호스트 */
export type Outgoing = { type: 'ready'; path: string } | { type: 'openExternal'; url: string };

/** 호스트 → 웹. 모르는 type은 무시한다 */
type Incoming =
  | { type: 'init'; platform?: unknown; appVersion?: unknown; locale?: unknown; insets?: unknown }
  | { type: 'insets'; insets?: unknown };

interface HostWindow {
  ForNav?: { postMessage?: (message: string) => void };
  flutter_inappwebview?: { callHandler?: (name: string, ...args: unknown[]) => unknown };
  fornav?: { protocol: number; receive: (message: unknown) => void; onBack: () => boolean };
}

const ZERO_INSETS: Insets = { top: 0, right: 0, bottom: 0, left: 0 };
const LOG_MAX = 20;

let state: HostState = {
  present: false,
  transport: null,
  ready: false,
  platform: null,
  appVersion: null,
  locale: null,
  insets: ZERO_INSETS,
  log: [],
};
const listeners = new Set<() => void>();
let installed = false;
/** 뒤로 가기를 화면 쪽이 가로챌 때 등록한다(단계가 있는 화면). true를 돌려주면 처리한 것이다 */
let backHandler: (() => boolean) | null = null;

function hostWindow(): HostWindow {
  return window as unknown as HostWindow;
}

function detectTransport(): Transport | null {
  const w = hostWindow();
  if (typeof w.ForNav?.postMessage === 'function') return 'webview_flutter';
  if (typeof w.flutter_inappwebview?.callHandler === 'function') return 'flutter_inappwebview';
  return null;
}

/**
 * 통로를 처음 찾은 순간 present를 켜고 ready를 보낸다. 보통은 installHost()에서 찾지만(호스트는 문서 시작 때 통로를 만든다),
 * 늦게 생긴 통로(브라우저에서 흉내 낼 때)도 첫 send()·receive() 때 같은 길을 탄다.
 */
function ensureTransport(): Transport | null {
  if (state.transport) return state.transport;
  const transport = detectTransport();
  if (!transport) return null;
  update({ present: true, transport });
  send({ type: 'ready', path: window.location.pathname });
  return transport;
}

function update(patch: Partial<HostState>): void {
  state = { ...state, ...patch };
  listeners.forEach((l) => l());
}

function pushLog(dir: LogEntry['dir'], type: string): void {
  const log = [{ dir, type, at: new Date().toISOString() }, ...state.log].slice(0, LOG_MAX);
  update({ log });
}

export function getHostState(): HostState {
  return state;
}

export function subscribeHost(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** 호스트에 메시지를 보낸다. 호스트가 없거나 보내지 못하면 false. 본문은 기록하지 않는다 */
export function send(message: Outgoing): boolean {
  const transport = ensureTransport();
  if (!transport) return false;
  const body = JSON.stringify({ protocol: PROTOCOL, ...message });
  const w = hostWindow();
  try {
    if (transport === 'webview_flutter') w.ForNav!.postMessage!(body);
    else w.flutter_inappwebview!.callHandler!('ForNav', body);
  } catch {
    console.warn(`[host] ${message.type} 전송 실패`);
    return false;
  }
  pushLog('out', message.type);
  return true;
}

function toInsets(raw: unknown): Insets | null {
  if (!raw || typeof raw !== 'object') return null;
  const r = raw as Record<string, unknown>;
  const n = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) && v >= 0 ? v : 0);
  return { top: n(r.top), right: n(r.right), bottom: n(r.bottom), left: n(r.left) };
}

function applyInsets(insets: Insets): void {
  const root = document.documentElement.style;
  root.setProperty('--inset-top', `${insets.top}px`);
  root.setProperty('--inset-right', `${insets.right}px`);
  root.setProperty('--inset-bottom', `${insets.bottom}px`);
  root.setProperty('--inset-left', `${insets.left}px`);
  update({ insets });
}

function toPlatform(raw: unknown): Platform | null {
  return raw === 'android' || raw === 'ios' ? raw : null;
}

function toText(raw: unknown): string | null {
  return typeof raw === 'string' && raw.trim() !== '' ? raw.trim() : null;
}

/** 호스트가 부른다. 객체 또는 JSON 문자열. 형식이 틀리거나 모르는 type이면 무시한다 */
export function receive(raw: unknown): void {
  let msg: unknown = raw;
  if (typeof raw === 'string') {
    try {
      msg = JSON.parse(raw);
    } catch {
      return;
    }
  }
  if (!msg || typeof msg !== 'object' || typeof (msg as { type?: unknown }).type !== 'string') return;
  const m = msg as Incoming;
  switch (m.type) {
    case 'init': {
      ensureTransport();
      update({
        ready: true,
        platform: toPlatform(m.platform),
        appVersion: toText(m.appVersion),
        locale: toText(m.locale),
      });
      const insets = toInsets(m.insets);
      if (insets) applyInsets(insets);
      break;
    }
    case 'insets': {
      const insets = toInsets(m.insets);
      if (insets) applyInsets(insets);
      break;
    }
    default:
      return; // 모르는 type: 기록도 남기지 않는다
  }
  pushLog('in', m.type);
}

/**
 * Android 뒤로 가기. 호스트가 동기로 부른다.
 * 화면이 등록한 처리기가 있으면 그것을 먼저 묻고, 아니면 라우터 이력(react-router가 history.state.idx에 둔다)이 있을 때만 한 화면 뒤로 간다.
 * 갈 곳이 없으면 false — 호스트가 앱을 뒤로 보낸다.
 */
export function onBack(): boolean {
  if (backHandler?.()) return true;
  const idx = (window.history.state as { idx?: unknown } | null)?.idx;
  if (typeof idx === 'number' && idx > 0) {
    window.history.back();
    return true;
  }
  return false;
}

export function setBackHandler(handler: (() => boolean) | null): void {
  backHandler = handler;
}

/** 앱 시작 때 한 번. window.fornav를 만들고, 통로를 감지하고, 호스트가 있으면 ready를 보낸다. 두 번 불러도 한 번만 한다 */
export function installHost(): void {
  if (installed) return;
  installed = true;
  hostWindow().fornav = { protocol: PROTOCOL, receive, onBack };
  ensureTransport();
}
