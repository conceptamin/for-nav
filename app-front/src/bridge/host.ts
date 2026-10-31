// 호스트(Flutter) 계약의 웹 쪽 구현(README "호스트 계약"). 화면은 이 파일을 직접 부르지 않고 HostProvider의 useHost()를 쓴다.
// - 감지: 호스트가 문서 시작 때 넣어 둔 전송 통로(window.ForNav / window.flutter_inappwebview)가 있는지만 본다. UA는 보지 않는다.
// - 웹 → 호스트: send(). 호스트 → 웹: window.fornav.receive(), 동기 window.fornav.onBack().
// - 메시지 본문(openExternal.url 등)을 console에 찍지 않는다. 기록은 type만 남긴다.
// - 호스트가 없으면 send()는 false를 돌려주고 아무 일도 하지 않는다. 화면은 그때 브라우저 기본 동작에 맡긴다.
// - 네이티브 Google 로그인(backlog 06): requestGoogleIdToken()이 googleSignIn을 보내고 googleSignInResult 하나를 기다린다.
//   ID 토큰은 반환값으로만 지나가고 상태·기록·console에 남기지 않는다.
// - 호스트 음성 인식(backlog 04): listenHostSpeech()가 speechStart를 보내고 speech·speechError를 받는다.
//   받아쓴 글은 핸들러로만 지나가고 상태·기록·console에 남기지 않는다.
// - 푸시(backlog 07·08): requestPushToken()이 pushRegister를 보내고 pushToken 하나를 기다린다. 요청 없이 온 pushToken은 토큰 갱신,
//   pushOpen은 알림으로 열린 사례다(구독 전에 온 것은 마지막 하나를 30초 동안 들고 있다). FCM 토큰·caseId는 반환값·콜백으로만 지나간다.

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
  /** 호스트가 init으로 알린 기능(예: googleSignIn). 없으면 빈 배열 */
  features: string[];
  log: LogEntry[];
}

/** 웹 → 호스트 */
export type Outgoing =
  | { type: 'ready'; path: string }
  | { type: 'openExternal'; url: string }
  | { type: 'googleSignIn' }
  | { type: 'speechStart'; lang: string }
  | { type: 'speechStop' }
  | { type: 'pushRegister' }
  | { type: 'pushUnregister' };

/** 호스트가 네이티브 Google 로그인을 할 수 있다는 init.features 값 */
export const FEATURE_GOOGLE_SIGN_IN = 'googleSignIn';

/** 호스트가 네이티브 음성 인식(통화 자막 받아쓰기)을 할 수 있다는 init.features 값 */
export const FEATURE_SPEECH = 'speech';

/** 호스트가 FCM 푸시 알림을 받을 수 있다는 init.features 값(backlog 07) */
export const FEATURE_PUSH = 'push';

/** pushOpen을 구독 전까지 들고 있는 시간. 오래된 알림을 늦게 열지 않는다(backlog 08 결정 2) */
export const PUSH_OPEN_HOLD_MS = 30_000;

/** requestPushToken()의 실패. 권한 거부는 실패가 아니라 null이다 */
export class PushTokenError extends Error {
  constructor() {
    super('pushRegister failed');
  }
}

/** listenHostSpeech()의 핸들러. 받아쓴 글은 기록하지 않는다 */
export interface HostSpeechHandlers {
  onText: (text: string, final: boolean) => void;
  /** denied: 권한 거부, unsupported: 이 기기·언어로 인식할 수 없음. 호스트는 이미 껐다 */
  onError: (error: 'denied' | 'unsupported') => void;
}

/** requestGoogleIdToken()의 실패. canceled는 사용자가 계정 선택을 닫은 것이다 */
export class GoogleSignInError extends Error {
  constructor(readonly kind: 'canceled' | 'failed') {
    super(`googleSignIn ${kind}`);
  }
}

/** 호스트 → 웹. 모르는 type은 무시한다 */
type Incoming =
  | { type: 'init'; platform?: unknown; appVersion?: unknown; locale?: unknown; insets?: unknown; features?: unknown }
  | { type: 'insets'; insets?: unknown }
  | { type: 'googleSignInResult'; idToken?: unknown; error?: unknown }
  | { type: 'speech'; text?: unknown; final?: unknown }
  | { type: 'speechError'; error?: unknown }
  | { type: 'pushToken'; token?: unknown; error?: unknown }
  | { type: 'pushOpen'; caseId?: unknown };

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
  features: [],
  log: [],
};
const listeners = new Set<() => void>();
let installed = false;
/** 뒤로 가기의 앱 규칙(bridge/back.ts). true·false면 그 값이 답이고, undefined면 아래 기본 동작으로 간다 */
let backHandler: (() => boolean | undefined) | null = null;
/** 기다리는 googleSignIn 요청. 응답(googleSignInResult)은 이것 하나만 끝낸다 */
let pendingSignIn: { promise: Promise<string>; resolve: (idToken: string) => void; reject: (e: GoogleSignInError) => void } | null =
  null;
/** 켜 둔 받아쓰기. speech·speechError는 이것 하나에만 간다 */
let speechListener: HostSpeechHandlers | null = null;
/** 기다리는 pushRegister 요청. 응답(pushToken)은 이것 하나만 끝낸다 */
let pendingPush: { promise: Promise<string | null>; resolve: (token: string | null) => void; reject: (e: PushTokenError) => void } | null =
  null;
const pushTokenListeners = new Set<(token: string) => void>();
const pushOpenListeners = new Set<(caseId: string) => void>();
/** 구독자가 없을 때 온 마지막 pushOpen */
let heldPushOpen: { caseId: string; at: number } | null = null;
/** 이 페이지에서 마지막으로 받은 pushOpen이 있는가(확인 화면용, 값은 두지 않는다) */
let pushOpenSeen = false;

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

function toFeatures(raw: unknown): string[] {
  return Array.isArray(raw) ? raw.filter((v): v is string => typeof v === 'string') : [];
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
        features: toFeatures(m.features),
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
    case 'googleSignInResult': {
      const pending = pendingSignIn;
      pendingSignIn = null;
      if (!pending) break; // 기다리는 요청이 없으면 무시한다
      if (typeof m.idToken === 'string' && m.idToken !== '') pending.resolve(m.idToken);
      else pending.reject(new GoogleSignInError(m.error === 'canceled' ? 'canceled' : 'failed'));
      break;
    }
    case 'speech': {
      if (!speechListener || typeof m.text !== 'string') break; // 켜 둔 받아쓰기가 없으면 무시한다
      const text = m.text.trim();
      if (m.final === true) {
        if (text) speechListener.onText(text, true);
        speechListener.onText('', false);
      } else {
        speechListener.onText(text, false);
      }
      break;
    }
    case 'speechError': {
      const listener = speechListener;
      speechListener = null;
      listener?.onError(m.error === 'denied' ? 'denied' : 'unsupported');
      break;
    }
    case 'pushToken': {
      const token = typeof m.token === 'string' && m.token !== '' ? m.token : null;
      const pending = pendingPush;
      pendingPush = null;
      if (pending) {
        if (token) pending.resolve(token);
        else if (m.error === 'denied') pending.resolve(null);
        else pending.reject(new PushTokenError());
      } else if (token) {
        pushTokenListeners.forEach((l) => l(token)); // 요청 없이 온 것은 토큰 갱신이다
      }
      break;
    }
    case 'pushOpen': {
      if (typeof m.caseId !== 'string' || m.caseId === '') break;
      pushOpenSeen = true;
      if (pushOpenListeners.size) pushOpenListeners.forEach((l) => l(m.caseId as string));
      else heldPushOpen = { caseId: m.caseId, at: Date.now() };
      break;
    }
    default:
      return; // 모르는 type: 기록도 남기지 않는다
  }
  pushLog('in', m.type);
}

/**
 * 호스트의 네이티브 Google 로그인으로 ID 토큰을 받는다(backlog 06). init.features에 googleSignIn이 있을 때만 보낸다.
 * 취소는 GoogleSignInError('canceled'), 그 밖은 'failed'. 시간 제한은 없다(계정 선택 창을 오래 들고 있을 수 있다).
 * 기다리는 중에 또 부르면 같은 요청을 기다린다.
 */
export function requestGoogleIdToken(): Promise<string> {
  if (pendingSignIn) return pendingSignIn.promise;
  if (!state.ready || !state.features.includes(FEATURE_GOOGLE_SIGN_IN)) return Promise.reject(new GoogleSignInError('failed'));
  let resolve!: (idToken: string) => void;
  let reject!: (e: GoogleSignInError) => void;
  const promise = new Promise<string>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  pendingSignIn = { promise, resolve, reject };
  if (!send({ type: 'googleSignIn' })) {
    pendingSignIn = null;
    reject(new GoogleSignInError('failed'));
  }
  return promise;
}

/**
 * 호스트 음성 인식으로 받아쓴다(backlog 04). init.features에 speech가 있을 때만 보낸다. 끄는 함수를 돌려준다.
 * 다시 켜기는 호스트가 맡는다. 이미 켜 둔 것이 있으면 그것을 대신한다(호스트도 앞 것을 버린다).
 */
export function listenHostSpeech(lang: string, handlers: HostSpeechHandlers): () => void {
  if (!state.ready || !state.features.includes(FEATURE_SPEECH)) {
    handlers.onError('unsupported');
    return () => {};
  }
  const listener = { ...handlers };
  speechListener = listener;
  if (!send({ type: 'speechStart', lang })) {
    speechListener = null;
    handlers.onError('unsupported');
    return () => {};
  }
  return () => {
    if (speechListener !== listener) return; // 이미 오류로 끝났거나 새 받아쓰기가 대신했다
    speechListener = null;
    send({ type: 'speechStop' });
  };
}

/**
 * 호스트의 FCM 토큰을 받는다(backlog 07·08). init.features에 push가 있을 때만 보낸다.
 * 권한 거부는 null, 그 밖 실패는 PushTokenError. 기다리는 중에 또 부르면 같은 요청을 기다린다.
 */
export function requestPushToken(): Promise<string | null> {
  if (pendingPush) return pendingPush.promise;
  if (!state.ready || !state.features.includes(FEATURE_PUSH)) return Promise.reject(new PushTokenError());
  let resolve!: (token: string | null) => void;
  let reject!: (e: PushTokenError) => void;
  const promise = new Promise<string | null>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  pendingPush = { promise, resolve, reject };
  if (!send({ type: 'pushRegister' })) {
    pendingPush = null;
    reject(new PushTokenError());
  }
  return promise;
}

/** 요청 없이 온 pushToken(토큰 갱신). 구독을 끊는 함수를 돌려준다 */
export function listenPushToken(cb: (token: string) => void): () => void {
  pushTokenListeners.add(cb);
  return () => pushTokenListeners.delete(cb);
}

/** 호스트가 FCM 토큰을 지운다. 응답은 없다 */
export function unregisterPush(): void {
  send({ type: 'pushUnregister' });
}

/** 알림으로 열린 사례. 구독 전에 30초 안에 온 마지막 하나는 첫 구독자에게 곧바로 넘기고 비운다 */
export function listenPushOpen(cb: (caseId: string) => void): () => void {
  pushOpenListeners.add(cb);
  const held = heldPushOpen;
  heldPushOpen = null;
  if (held && Date.now() - held.at <= PUSH_OPEN_HOLD_MS) cb(held.caseId);
  return () => pushOpenListeners.delete(cb);
}

/** 이 페이지에서 pushOpen을 받은 적이 있는가(확인 화면용) */
export function hasSeenPushOpen(): boolean {
  return pushOpenSeen;
}

/**
 * Android 뒤로 가기. 호스트가 동기로 부른다.
 * 등록된 앱 규칙이 답을 주면 그대로, 아니면 라우터 이력(react-router가 history.state.idx에 둔다)이 있을 때만 한 화면 뒤로 간다.
 * 갈 곳이 없으면 false — 호스트가 앱을 뒤로 보낸다.
 */
export function onBack(): boolean {
  const decided = backHandler?.();
  if (decided !== undefined) return decided;
  const idx = (window.history.state as { idx?: unknown } | null)?.idx;
  if (typeof idx === 'number' && idx > 0) {
    window.history.back();
    return true;
  }
  return false;
}

export function setBackHandler(handler: (() => boolean | undefined) | null): void {
  backHandler = handler;
}

/** 앱 시작 때 한 번. window.fornav를 만들고, 통로를 감지하고, 호스트가 있으면 ready를 보낸다. 두 번 불러도 한 번만 한다 */
export function installHost(): void {
  if (installed) return;
  installed = true;
  hostWindow().fornav = { protocol: PROTOCOL, receive, onBack };
  ensureTransport();
}
