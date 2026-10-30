// 센터 직원 로그인(backend 17, backlog 27). 화면은 이 파일만 부른다.
// 단독 모드에는 서버가 없으므로 로그인도 없다(getMe가 바로 `required: false`).
// 이메일·코드는 console에 찍지 않는다. 실패 기록은 경로·code·requestId만 남긴다(logFailure).
// 세션은 서버가 준 HttpOnly 쿠키다. 같은 출처 요청이라 fetch 기본값(same-origin)으로 실린다.

import { ApiError, isApiMode, logFailure, requestJson } from './http';

/** 로그인 경로 시간 제한. 메일 발송을 기다리는 `code`도 이 안에 끝난다 */
export const AUTH_TIMEOUT_MS = 10000;
/** 같은 이메일로 코드를 다시 받기까지 기다리는 시간(서버 제한과 같다) */
export const AUTH_RESEND_MS = 60000;

export interface AuthMe {
  /** 서버가 센터 로그인을 쓰는가(CENTER_AUTH=email). false면 센터 화면은 로그인 없이 열린다 */
  required: boolean;
  /** 로그인한 직원 이메일. 세션이 없으면 null */
  email: string | null;
}

const bad = () => new ApiError('BAD_RESPONSE', null, null);
const isMe = (r: Partial<AuthMe> | undefined): r is AuthMe =>
  Boolean(r && typeof r.required === 'boolean' && (r.email === null || typeof r.email === 'string'));

async function call<T>(path: string, method: 'GET' | 'POST', body?: unknown): Promise<T> {
  try {
    return await requestJson<T>(path, { method, body, timeoutMs: AUTH_TIMEOUT_MS });
  } catch (e) {
    logFailure(path, e);
    throw e;
  }
}

/** 센터 화면에 들어올 때 한 번. 세션이 없어도 실패가 아니라 `email: null`이다 */
export async function getMe(): Promise<AuthMe> {
  if (!isApiMode()) return { required: false, email: null };
  const r = await call<Partial<AuthMe>>('/auth/me', 'GET');
  if (!isMe(r)) throw bad();
  return r;
}

/** 등록된 직원이면 코드 메일이 간다. 등록 여부와 관계없이 성공은 같다. 제한을 넘으면 RATE_LIMITED */
export async function requestCode(email: string): Promise<void> {
  await call<void>('/auth/code', 'POST', { email });
}

/** 맞으면 세션 쿠키가 생기고 로그인한 이메일을 돌려준다. 틀림·만료는 UNAUTHORIZED */
export async function verifyCode(email: string, code: string): Promise<string> {
  const r = await call<Partial<AuthMe>>('/auth/verify', 'POST', { email, code });
  if (!isMe(r) || r.email === null) throw bad();
  return r.email;
}

/** 서버 세션을 지우고 쿠키를 비운다 */
export async function logout(): Promise<void> {
  if (!isApiMode()) return;
  await call<void>('/auth/logout', 'POST');
}

// ---------------------------------------------------------------------------
// 세션이 끝났다는 알림. 센터 경로(center.ts)가 401을 받으면 알리고, 센터 화면(CenterLayout)이 듣고 로그인으로 보낸다.
// ---------------------------------------------------------------------------
const sessionEndedListeners = new Set<() => void>();

export function onSessionEnded(listener: () => void): () => void {
  sessionEndedListeners.add(listener);
  return () => {
    sessionEndedListeners.delete(listener);
  };
}

export function notifySessionEnded(): void {
  sessionEndedListeners.forEach((f) => f());
}

/** 센터 경로 실패가 세션 끝(401)인가 */
export const isSessionEnded = (e: unknown): boolean => e instanceof ApiError && e.status === 401;

/** 로그인 화면 주소. `from`은 로그인 뒤 돌아갈 센터 경로다 */
export function loginPath(from: string): string {
  return `/center/login?${new URLSearchParams({ from })}`;
}

/** 로그인 뒤 돌아갈 곳. 센터 경로(로그인 화면 제외)만 받고 나머지는 접수함이다 */
export function safeFrom(from: string | null): string {
  const center = from === '/center' || from?.startsWith('/center/') || from?.startsWith('/center?');
  if (!from || !center || from.startsWith('/center/login')) return '/center';
  return from;
}
