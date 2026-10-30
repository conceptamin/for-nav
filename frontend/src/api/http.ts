// API 모드 판단과 JSON 요청 한 가지. 화면은 이 파일을 직접 부르지 않고 경로별 함수(worker.ts 등)를 거친다.
// 시간 제한은 AbortController로 걸고, 실패는 종류와 관계없이 ApiError 하나로 던진다.
// 요청 본문·응답 원문은 console에 찍지 않는다. 오류 기록은 code와 requestId만 남긴다.

const API_BASE = (import.meta.env.VITE_API_BASE ?? '').trim().replace(/\/+$/, '');

/** `VITE_API_BASE`가 있으면 API 모드다. 없으면 브라우저 안의 함수만 쓴다. */
export function isApiMode(): boolean {
  return API_BASE !== '';
}

/**
 * WebSocket 주소. `VITE_API_BASE`가 상대(`/api`)든 절대(`https://…/api`)든 지금 페이지 기준으로 풀고
 * `http:`→`ws:`, `https:`→`wss:`로 바꾼다. 단독 모드에서는 부르지 않는다.
 */
export function wsUrl(path: string): string {
  const url = new URL(`${API_BASE}${path}`, window.location.href);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return url.toString();
}

/**
 * 오류 코드. 서버가 준 것(`backend/README.md` "오류 형식")은 그대로 쓰고,
 * 서버 응답이 없는 경우는 클라이언트에서 아래 값을 붙인다.
 */
export type ApiErrorCode =
  | 'NOT_FOUND'
  | 'VALIDATION'
  | 'INTERNAL'
  | 'BAD_REQUEST'
  | 'UNAUTHORIZED' // 센터 직원 세션이 없거나 끝났다, 로그인 코드가 틀렸다(backend 17)
  | 'RATE_LIMITED' // 로그인 코드 요청이 보내기 제한을 넘었다(backend 17)
  | 'TIMEOUT' // 시간 제한을 넘겼다
  | 'NETWORK' // 연결 자체가 안 됐다
  | 'BAD_RESPONSE' // 2xx인데 JSON이 아니거나 필수 필드가 없다
  | (string & {});

export class ApiError extends Error {
  readonly code: ApiErrorCode;
  /** HTTP 상태 코드. 응답을 받지 못했으면 null */
  readonly status: number | null;
  /** 서버가 준 X-Request-Id. 없으면 null */
  readonly requestId: string | null;

  constructor(code: ApiErrorCode, status: number | null, requestId: string | null, message?: string) {
    super(message ?? code);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.requestId = requestId;
  }
}

interface ErrorBody {
  error?: { code?: string; message?: string; requestId?: string };
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH';
  body?: unknown;
  /** 밀리초. 넘기면 `TIMEOUT`으로 실패한다 */
  timeoutMs: number;
}

/** `${VITE_API_BASE}${path}`에 JSON 요청을 보내고 JSON 응답을 돌려준다. 실패는 전부 ApiError다. */
export async function requestJson<T>(path: string, options: RequestOptions): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), options.timeoutMs);
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: options.method ?? (options.body === undefined ? 'GET' : 'POST'),
      headers: options.body === undefined ? { Accept: 'application/json' } : { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: controller.signal,
    });
  } catch {
    throw new ApiError(controller.signal.aborted ? 'TIMEOUT' : 'NETWORK', null, null);
  } finally {
    clearTimeout(timer);
  }

  const requestId = res.headers.get('X-Request-Id');
  if (!res.ok) {
    let body: ErrorBody | null = null;
    try {
      body = (await res.json()) as ErrorBody;
    } catch {
      body = null;
    }
    const code = body?.error?.code ?? (res.status >= 500 ? 'INTERNAL' : 'BAD_REQUEST');
    throw new ApiError(code, res.status, body?.error?.requestId ?? requestId, body?.error?.message);
  }
  // 204(데모 초기화 등)와 202(로그인 코드 요청, backend 17)는 본문이 없다
  if (res.status === 204 || res.status === 202) return undefined as T;
  try {
    return (await res.json()) as T;
  } catch {
    throw new ApiError('BAD_RESPONSE', res.status, requestId);
  }
}

/** 실패를 `ApiError`로 통일한다. 대체 분기에서 code·requestId를 읽기 위해 쓴다. */
export function toApiError(e: unknown): ApiError {
  return e instanceof ApiError ? e : new ApiError('BAD_RESPONSE', null, null);
}

/** 대체했을 때 남기는 한 줄. 경로·code·requestId만 적고 본문은 적지 않는다. */
export function logFallback(path: string, e: unknown): void {
  const err = toApiError(e);
  console.warn(`[api] ${path} ${err.code}${err.status ? ` ${err.status}` : ''}${err.requestId ? ` requestId=${err.requestId}` : ''} → 브라우저 함수로 대체`);
}

/** 대체하지 않는 경로(센터)가 실패했을 때 남기는 한 줄. 화면은 실패를 그대로 보인다 */
export function logFailure(path: string, e: unknown): void {
  const err = toApiError(e);
  console.warn(`[api] ${path} ${err.code}${err.status ? ` ${err.status}` : ''}${err.requestId ? ` requestId=${err.requestId}` : ''} → 실패 표시(대체 없음)`);
}
