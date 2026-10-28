// 서버 설정값(GET /api/meta): 정보 기준일과 센터 운영 시간.
// 단독 모드는 부르지 않고, 실패하면 브라우저 상수(domain/coverage.ts)를 쓴다.

import type { Meta } from '../domain/coverage';
import { DEFAULT_META } from '../domain/coverage';
import { ApiError, isApiMode, logFallback, requestJson } from './http';

/** 앱 시작 시 한 번 부른다. 넘기면 브라우저 상수를 쓴다 */
export const META_TIMEOUT_MS = 3000;

const isHour = (n: unknown): n is number => typeof n === 'number' && Number.isInteger(n) && n >= 0 && n <= 24;

export async function loadMeta(): Promise<Meta> {
  if (!isApiMode()) return DEFAULT_META;
  try {
    const r = await requestJson<Partial<Meta>>('/meta', { timeoutMs: META_TIMEOUT_MS });
    const h = r.centerHours;
    if (
      typeof r.infoDate !== 'string' ||
      !h ||
      !isHour(h.openHour) ||
      !isHour(h.closeHour) ||
      !Array.isArray(h.workdays) ||
      !h.workdays.every((d) => Number.isInteger(d) && d >= 0 && d <= 6)
    ) {
      throw new ApiError('BAD_RESPONSE', null, null);
    }
    return { infoDate: r.infoDate, centerHours: { openHour: h.openHour, closeHour: h.closeHour, workdays: h.workdays } };
  } catch (e) {
    logFallback('/meta', e);
    return DEFAULT_META;
  }
}
